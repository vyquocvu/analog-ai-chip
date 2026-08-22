"""Resumable multi-layer model evaluation and execution envelope enforcement.

Enables checkpointed per-layer model execution for large models, allowing runs
to interrupt and resume without changing random seeds or double-counting ledger
entries, with strict host memory and runtime budgets across T0–T3 design points.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .accelerator import Accelerator
from .block_stream import streamed_linear_mvm
from .decoder_primitives import (
    apply_rope,
    causal_attention,
    gelu,
    layer_norm,
    rms_norm,
    swiglu,
)
from .generalized_decoder import GeneralizedDecoder
from .surrogate import EvaluationMode, SurrogateCalibrationProfile
from .tile import CrossbarTile

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class TierBudget:
    """Execution envelope budgets for workload scaling tiers."""

    tier_name: str
    parameter_range: str
    max_context_tokens: int
    max_rss_bytes: int
    max_runtime_seconds: float


TIER_BUDGETS: dict[str, TierBudget] = {
    "T0": TierBudget("T0", "up to 150M", 2048, 2 * 1024**3, 60.0),
    "T1": TierBudget("T1", "1–1.5B", 4096, 8 * 1024**3, 300.0),
    "T2": TierBudget("T2", "about 3B", 8192, 16 * 1024**3, 900.0),
    "T3": TierBudget("T3", "7–8B", 8192, 32 * 1024**3, 1800.0),
}


@dataclass
class LayerEvaluationCheckpoint:
    """Serializable execution state of an evaluated decoder layer."""

    layer_index: int
    input_sha256: str
    output_sha256: str
    cumulative_macs: int
    cumulative_tile_cycles: int
    mode: str
    completed: bool


def compute_tensor_sha256(arr: FloatArray) -> str:
    """Deterministic SHA256 digest of a float array's raw byte buffer."""
    contiguous = np.ascontiguousarray(arr, dtype=np.float64)
    return hashlib.sha256(contiguous.tobytes()).hexdigest()


class ResumableModelEvaluator:
    """Executes multi-layer decoders with per-layer checkpoints and ledger idempotency."""

    def __init__(
        self,
        decoder: GeneralizedDecoder,
        checkpoint_dir: Path | str,
        mode: EvaluationMode = EvaluationMode.EXACT,
        tile_factory: Callable[[], CrossbarTile] | None = None,
        surrogate_profiles: dict[str, SurrogateCalibrationProfile] | None = None,
        sampled_layers: Sequence[int] = (0,),
    ) -> None:
        self.decoder = decoder
        self.manifest = decoder.manifest
        self.weights = decoder.weights
        self.checkpoint_dir = Path(checkpoint_dir)
        self.mode = mode
        self.tile_factory = tile_factory
        self.surrogate_profiles = surrogate_profiles or {}
        self.sampled_layers = tuple(sampled_layers)

        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def _state_file(self, layer_idx: int) -> Path:
        return self.checkpoint_dir / f"layer_{layer_idx:04d}_state.npy"

    def _meta_file(self, layer_idx: int) -> Path:
        return self.checkpoint_dir / f"layer_{layer_idx:04d}_meta.json"

    def _evaluate_single_layer(
        self,
        layer_idx: int,
        x: FloatArray,
        cumulative_macs: int,
        cumulative_cycles: int,
    ) -> tuple[FloatArray, int, int]:
        """Execute one decoder layer through attention and MLP blocks."""
        manifest = self.manifest
        w = self.weights
        p = f"layers.{layer_idx}."
        tokens, hidden = x.shape

        # 1. Attention Norm
        norm_w = w[f"{p}attention_norm.weight"]
        norm_b = w.get(f"{p}attention_norm.bias")
        normed = (
            layer_norm(x, norm_w, norm_b)
            if manifest.norm_type == "layernorm"
            else rms_norm(x, norm_w)
        )

        # 2. Attention Projections
        q_w = w[f"{p}attention.q_proj.weight"]
        k_w = w[f"{p}attention.k_proj.weight"]
        v_w = w[f"{p}attention.v_proj.weight"]
        o_w = w[f"{p}attention.out_proj.weight"]
        q_b = w.get(f"{p}attention.q_proj.bias")
        k_b = w.get(f"{p}attention.k_proj.bias")
        v_b = w.get(f"{p}attention.v_proj.bias")
        o_b = w.get(f"{p}attention.out_proj.bias")

        macs = cumulative_macs
        cycles = cumulative_cycles

        # Determine acceleration mode for this layer
        use_physical = False
        if self.mode == EvaluationMode.EXACT and self.tile_factory is not None:
            use_physical = True
        elif self.mode == EvaluationMode.LAYER_SAMPLED and layer_idx in self.sampled_layers:
            use_physical = self.tile_factory is not None

        if use_physical and self.tile_factory is not None:
            acc = Accelerator(self.tile_factory, tile_rows=16, tile_cols=16, tile_count=16)
            q = streamed_linear_mvm(normed, q_w, bias=q_b, accelerator=acc)
            k = streamed_linear_mvm(normed, k_w, bias=k_b, accelerator=acc)
            v = streamed_linear_mvm(normed, v_w, bias=v_b, accelerator=acc)
            macs += acc.macs
            cycles += acc.tile_cycles
        else:
            q = streamed_linear_mvm(normed, q_w, bias=q_b)
            k = streamed_linear_mvm(normed, k_w, bias=k_b)
            v = streamed_linear_mvm(normed, v_w, bias=v_b)

        # Reshape Q, K, V
        head_dim = manifest.head_dimension
        q_heads = q.reshape(tokens, manifest.num_attention_heads, head_dim)
        k_heads = k.reshape(tokens, manifest.num_key_value_heads, head_dim)
        v_heads = v.reshape(tokens, manifest.num_key_value_heads, head_dim)

        if manifest.position_type == "rope":
            positions = np.arange(tokens)
            q_heads = apply_rope(q_heads, positions)
            k_heads = apply_rope(k_heads, positions)

        attn_out_heads = causal_attention(q_heads, k_heads, v_heads)
        attn_flat = attn_out_heads.reshape(tokens, hidden)

        if use_physical and self.tile_factory is not None:
            acc = Accelerator(self.tile_factory, tile_rows=16, tile_cols=16, tile_count=16)
            proj_out = streamed_linear_mvm(attn_flat, o_w, bias=o_b, accelerator=acc)
            macs += acc.macs
            cycles += acc.tile_cycles
        else:
            proj_out = streamed_linear_mvm(attn_flat, o_w, bias=o_b)

        x_mid = x + proj_out

        # 3. MLP Block
        mlp_norm_w = w[f"{p}mlp_norm.weight"]
        mlp_norm_b = w.get(f"{p}mlp_norm.bias")
        mlp_normed = (
            layer_norm(x_mid, mlp_norm_w, mlp_norm_b)
            if manifest.norm_type == "layernorm"
            else rms_norm(x_mid, mlp_norm_w)
        )

        up_w = w[f"{p}mlp.up_proj.weight"]
        down_w = w[f"{p}mlp.down_proj.weight"]
        up_b = w.get(f"{p}mlp.up_proj.bias")
        down_b = w.get(f"{p}mlp.down_proj.bias")

        if manifest.activation_type == "swiglu":
            gate_w = w[f"{p}mlp.gate_proj.weight"]
            gate_b = w.get(f"{p}mlp.gate_proj.bias")
            if use_physical and self.tile_factory is not None:
                acc = Accelerator(self.tile_factory, tile_rows=16, tile_cols=16, tile_count=16)
                g_out = streamed_linear_mvm(mlp_normed, gate_w, bias=gate_b, accelerator=acc)
                u_out = streamed_linear_mvm(mlp_normed, up_w, bias=up_b, accelerator=acc)
                macs += acc.macs
                cycles += acc.tile_cycles
            else:
                g_out = streamed_linear_mvm(mlp_normed, gate_w, bias=gate_b)
                u_out = streamed_linear_mvm(mlp_normed, up_w, bias=up_b)

            hidden_act = swiglu(g_out, u_out)
        else:
            if use_physical and self.tile_factory is not None:
                acc = Accelerator(self.tile_factory, tile_rows=16, tile_cols=16, tile_count=16)
                u_out = streamed_linear_mvm(mlp_normed, up_w, bias=up_b, accelerator=acc)
                macs += acc.macs
                cycles += acc.tile_cycles
            else:
                u_out = streamed_linear_mvm(mlp_normed, up_w, bias=up_b)
            hidden_act = gelu(u_out)

        if use_physical and self.tile_factory is not None:
            acc = Accelerator(self.tile_factory, tile_rows=16, tile_cols=16, tile_count=16)
            d_out = streamed_linear_mvm(hidden_act, down_w, bias=down_b, accelerator=acc)
            macs += acc.macs
            cycles += acc.tile_cycles
        else:
            d_out = streamed_linear_mvm(hidden_act, down_w, bias=down_b)

        x_out = x_mid + d_out
        return x_out, macs, cycles

    def evaluate_prompt(
        self,
        tokens: Sequence[int],
        interrupt_after_layer: int | None = None,
    ) -> tuple[FloatArray, dict[str, Any]]:
        """Run full evaluation with automatic resumption of completed layers."""
        tok_arr = np.asarray(tokens, dtype=np.int64)
        num_tok = len(tok_arr)
        if num_tok > self.manifest.context_length:
            raise ValueError(f"Sequence length {num_tok} exceeds context {self.manifest.context_length}")

        # Initial embedding lookup
        x = self.weights["token_embedding.weight"][tok_arr]
        if self.manifest.position_type == "learned":
            x = x + self.weights["position_embedding.weight"][:num_tok]

        cumulative_macs = 0
        cumulative_cycles = 0
        layers_resumed = 0
        layers_computed = 0

        for l_idx in range(self.manifest.num_layers):
            s_file = self._state_file(l_idx)
            m_file = self._meta_file(l_idx)

            curr_input_sha = compute_tensor_sha256(x)

            if s_file.exists() and m_file.exists():
                with open(m_file, encoding="utf-8") as f:
                    meta_dict = json.load(f)
                meta = LayerEvaluationCheckpoint(**meta_dict)

                # Verify input hash consistency
                if meta.input_sha256 != curr_input_sha:
                    raise ValueError(
                        f"Tamper or state divergence at layer {l_idx}: "
                        f"expected input hash {meta.input_sha256}, got {curr_input_sha}"
                    )

                # Load cached layer output state
                x = np.load(s_file)
                loaded_sha = compute_tensor_sha256(x)
                if loaded_sha != meta.output_sha256:
                    raise ValueError(f"Corrupt state file at layer {l_idx}")

                cumulative_macs = meta.cumulative_macs
                cumulative_cycles = meta.cumulative_tile_cycles
                layers_resumed += 1
            else:
                x, cumulative_macs, cumulative_cycles = self._evaluate_single_layer(
                    l_idx, x, cumulative_macs, cumulative_cycles
                )
                out_sha = compute_tensor_sha256(x)
                np.save(s_file, x)

                meta = LayerEvaluationCheckpoint(
                    layer_index=l_idx,
                    input_sha256=curr_input_sha,
                    output_sha256=out_sha,
                    cumulative_macs=cumulative_macs,
                    cumulative_tile_cycles=cumulative_cycles,
                    mode=self.mode.value,
                    completed=True,
                )
                with open(m_file, "w", encoding="utf-8") as f:
                    json.dump(asdict(meta), f, indent=2)

                layers_computed += 1

            if interrupt_after_layer is not None and l_idx == interrupt_after_layer:
                return x, {
                    "status": "INTERRUPTED",
                    "interrupted_at_layer": l_idx,
                    "cumulative_macs": cumulative_macs,
                    "cumulative_cycles": cumulative_cycles,
                    "layers_resumed": layers_resumed,
                    "layers_computed": layers_computed,
                }

        # Final Norm and Head
        fn_w = self.weights["final_norm.weight"]
        fn_b = self.weights.get("final_norm.bias")
        final_normed = (
            layer_norm(x, fn_w, fn_b)
            if self.manifest.norm_type == "layernorm"
            else rms_norm(x, fn_w)
        )

        lm_head_w = (
            self.weights["token_embedding.weight"]
            if self.manifest.tied_embeddings
            else self.weights["lm_head.weight"]
        )
        logits = streamed_linear_mvm(final_normed, lm_head_w)

        summary = {
            "status": "COMPLETED",
            "total_layers": self.manifest.num_layers,
            "layers_resumed": layers_resumed,
            "layers_computed": layers_computed,
            "cumulative_macs": cumulative_macs,
            "cumulative_cycles": cumulative_cycles,
            "mode": self.mode.value,
        }

        return logits, summary
