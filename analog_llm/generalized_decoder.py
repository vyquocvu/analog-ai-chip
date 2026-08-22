"""Architecture-neutral generalized decoder reference model.

Consumes a validated ModelManifest and canonical weights dictionary, executing
full-sequence and single-step cached forward passes under a strict hybrid
analog/digital boundary.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .accelerator import Accelerator
from .decoder_primitives import (
    apply_rope,
    cached_attention_step,
    causal_attention,
    gelu,
    layer_norm,
    rms_norm,
    swiglu,
)
from .model_manifest import ModelManifest

FloatArray = NDArray[np.float64]


@dataclass
class GeneralizedDecoder:
    """Architecture-neutral decoder execution engine driven by a ModelManifest."""

    manifest: ModelManifest
    weights: dict[str, FloatArray] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.weights:
            inventory = {k: v.shape for k, v in self.weights.items()}
            self.manifest.validate_tensors(inventory)
        else:
            self._init_random_weights()

    def _init_random_weights(self, seed: int = 42, std: float = 0.02) -> None:
        """Initialize deterministic float64 weights matching the manifest specs."""
        rng = np.random.default_rng(seed)
        specs = self.manifest.tensor_specs()
        for name, spec in specs.items():
            if name.endswith(".bias"):
                self.weights[name] = np.zeros(spec.shape, dtype=np.float64)
            elif "norm" in name and name.endswith(".weight"):
                self.weights[name] = np.ones(spec.shape, dtype=np.float64)
            else:
                self.weights[name] = rng.normal(0.0, std, spec.shape).astype(np.float64)

    # -- Linear projection dispatcher ----------------------------------------
    def _linear(
        self,
        x: FloatArray,
        weight_name: str,
        accelerator: Accelerator | None = None,
    ) -> FloatArray:
        """Evaluate linear projection y = x @ W.T + b with optional analog routing."""
        weight = self.weights[weight_name]
        bias_name = weight_name.removesuffix(".weight") + ".bias"
        bias = self.weights.get(bias_name)

        if accelerator is None:
            out = x @ weight.T
            if bias is not None:
                out = out + bias
            return out

        # Route matrix-vector multiplications through analog accelerator
        is_1d = x.ndim == 1
        x_2d = x[None, :] if is_1d else x
        out_2d = np.empty((x_2d.shape[0], weight.shape[0]), dtype=np.float64)
        for i in range(x_2d.shape[0]):
            out_2d[i] = accelerator.mvm(weight, x_2d[i])
            if bias is not None:
                out_2d[i] += bias
        return out_2d[0] if is_1d else out_2d

    def _norm(
        self,
        x: FloatArray,
        prefix: str,
    ) -> FloatArray:
        """Apply configured normalization (LayerNorm or RMSNorm)."""
        weight = self.weights[f"{prefix}.weight"]
        if self.manifest.norm_type == "rmsnorm":
            return rms_norm(x, weight)
        bias = self.weights[f"{prefix}.bias"]
        return layer_norm(x, weight, bias)

    # -- Forward pass (full context) -----------------------------------------
    def forward_logits(
        self,
        tokens: Sequence[int] | NDArray[np.int64],
        accelerator: Accelerator | None = None,
    ) -> FloatArray:
        """Execute full sequence forward pass and return logits [tokens, vocab_size]."""
        tokens_arr = np.asarray(tokens, dtype=np.int64).reshape(-1)
        seq_len = tokens_arr.size
        if seq_len == 0 or seq_len > self.manifest.context_length:
            raise ValueError(f"sequence length must be in [1, {self.manifest.context_length}]")

        # 1. Embedding lookup
        x = self.weights["token_embedding.weight"][tokens_arr]  # [seq_len, hidden_size]
        if self.manifest.position_type == "learned":
            x = x + self.weights["position_embedding.weight"][:seq_len]

        qh = self.manifest.num_attention_heads
        kvh = self.manifest.num_key_value_heads
        d = self.manifest.head_dimension
        positions = np.arange(seq_len, dtype=np.int64)

        # 2. Layer stack
        for layer in range(self.manifest.num_layers):
            p = f"layers.{layer}"

            # Attention block
            h_norm = self._norm(x, f"{p}.attention_norm")
            q = self._linear(h_norm, f"{p}.attention.q_proj.weight", accelerator)
            k = self._linear(h_norm, f"{p}.attention.k_proj.weight", accelerator)
            v = self._linear(h_norm, f"{p}.attention.v_proj.weight", accelerator)

            q = q.reshape(seq_len, qh, d)
            k = k.reshape(seq_len, kvh, d)
            v = v.reshape(seq_len, kvh, d)

            if self.manifest.position_type == "rope":
                q = apply_rope(q, positions)
                k = apply_rope(k, positions)

            attn = causal_attention(q, k, v).reshape(seq_len, qh * d)
            attn_out = self._linear(attn, f"{p}.attention.out_proj.weight", accelerator)
            x = x + attn_out

            # MLP block
            h_mlp = self._norm(x, f"{p}.mlp_norm")
            if self.manifest.activation_type == "gelu":
                up = self._linear(h_mlp, f"{p}.mlp.up_proj.weight", accelerator)
                act = gelu(up)
            else:  # swiglu
                gate = self._linear(h_mlp, f"{p}.mlp.gate_proj.weight", accelerator)
                up = self._linear(h_mlp, f"{p}.mlp.up_proj.weight", accelerator)
                act = swiglu(gate, up)

            down = self._linear(act, f"{p}.mlp.down_proj.weight", accelerator)
            x = x + down

        # 3. Final normalization & LM Head
        x = self._norm(x, "final_norm")
        if self.manifest.tied_embeddings:
            logits = self._linear(x, "token_embedding.weight", accelerator)
        else:
            logits = self._linear(x, "lm_head.weight", accelerator)

        return logits

    # -- KV-cache step execution ---------------------------------------------
    def _init_kv_cache(self) -> dict[str, list[FloatArray | None]]:
        return {
            "k": [None] * self.manifest.num_layers,
            "v": [None] * self.manifest.num_layers,
        }

    def _forward_step(
        self,
        token: int,
        position: int,
        cache: dict[str, list[Any]],
        accelerator: Accelerator | None = None,
    ) -> FloatArray:
        """Execute single-token step reusing cached K/V history; returns 1D logits [vocab]."""
        if position >= self.manifest.context_length:
            raise ValueError(
                f"position {position} exceeds context_length {self.manifest.context_length}"
            )

        x = self.weights["token_embedding.weight"][token]  # [hidden_size]
        if self.manifest.position_type == "learned":
            x = x + self.weights["position_embedding.weight"][position]

        qh = self.manifest.num_attention_heads
        kvh = self.manifest.num_key_value_heads
        d = self.manifest.head_dimension

        for layer in range(self.manifest.num_layers):
            p = f"layers.{layer}"

            h_norm = self._norm(x, f"{p}.attention_norm")
            q = self._linear(h_norm, f"{p}.attention.q_proj.weight", accelerator)
            k = self._linear(h_norm, f"{p}.attention.k_proj.weight", accelerator)
            v = self._linear(h_norm, f"{p}.attention.v_proj.weight", accelerator)

            q = q.reshape(qh, d)
            k = k.reshape(kvh, d)
            v = v.reshape(kvh, d)

            if self.manifest.position_type == "rope":
                q = apply_rope(q[None, ...], [position])[0]
                k = apply_rope(k[None, ...], [position])[0]

            if cache["k"][layer] is None:
                cache["k"][layer] = k[None, :, :]
                cache["v"][layer] = v[None, :, :]
            else:
                cache["k"][layer] = np.concatenate([cache["k"][layer], k[None, :, :]], axis=0)
                cache["v"][layer] = np.concatenate([cache["v"][layer], v[None, :, :]], axis=0)

            k_hist = cache["k"][layer]
            v_hist = cache["v"][layer]

            attn = cached_attention_step(q, k_hist, v_hist).reshape(qh * d)
            attn_out = self._linear(attn, f"{p}.attention.out_proj.weight", accelerator)
            x = x + attn_out

            h_mlp = self._norm(x, f"{p}.mlp_norm")
            if self.manifest.activation_type == "gelu":
                up = self._linear(h_mlp, f"{p}.mlp.up_proj.weight", accelerator)
                act = gelu(up)
            else:  # swiglu
                gate = self._linear(h_mlp, f"{p}.mlp.gate_proj.weight", accelerator)
                up = self._linear(h_mlp, f"{p}.mlp.up_proj.weight", accelerator)
                act = swiglu(gate, up)

            down = self._linear(act, f"{p}.mlp.down_proj.weight", accelerator)
            x = x + down

        x = self._norm(x, "final_norm")
        if self.manifest.tied_embeddings:
            logits = self._linear(x, "token_embedding.weight", accelerator)
        else:
            logits = self._linear(x, "lm_head.weight", accelerator)

        return logits

    # -- Autoregressive generation -------------------------------------------
    def generate(
        self,
        prompt: Sequence[int] | NDArray[np.int64],
        max_new: int = 8,
        greedy: bool = True,
        accelerator: Accelerator | None = None,
        rng: np.random.Generator | None = None,
    ) -> list[int]:
        """Autoregressive generation without KV cache (full-context recompute)."""
        prompt_list = list(np.asarray(prompt, dtype=np.int64).reshape(-1).tolist())
        out = list(prompt_list)
        for _ in range(max_new):
            ctx = out[-self.manifest.context_length :]
            logits = self.forward_logits(ctx, accelerator=accelerator)
            last_logit = logits[-1]
            if greedy:
                next_tok = int(np.argmax(last_logit))
            else:
                if rng is None:
                    raise ValueError("rng required for sampling")
                probs = np.exp(last_logit - np.max(last_logit))
                probs /= probs.sum()
                next_tok = int(rng.choice(len(probs), p=probs))
            out.append(next_tok)
        return out

    def generate_kvcache(
        self,
        prompt: Sequence[int] | NDArray[np.int64],
        max_new: int = 8,
        greedy: bool = True,
        accelerator: Accelerator | None = None,
        rng: np.random.Generator | None = None,
    ) -> list[int]:
        """Autoregressive generation with incremental step-by-step KV-cache."""
        prompt_arr = np.asarray(prompt, dtype=np.int64).reshape(-1)
        if prompt_arr.size == 0 or prompt_arr.size > self.manifest.context_length:
            raise ValueError(f"prompt length must be in [1, {self.manifest.context_length}]")

        cache = self._init_kv_cache()
        out = list(prompt_arr.tolist())
        pos = 0
        logits: FloatArray = np.zeros(self.manifest.vocab_size, dtype=np.float64)

        for tok in prompt_arr:
            logits = self._forward_step(int(tok), pos, cache, accelerator)
            pos += 1

        for _ in range(max_new):
            if greedy:
                next_tok = int(np.argmax(logits))
            else:
                if rng is None:
                    raise ValueError("rng required for sampling")
                probs = np.exp(logits - np.max(logits))
                probs /= probs.sum()
                next_tok = int(rng.choice(len(probs), p=probs))
            out.append(next_tok)
            if pos < self.manifest.context_length:
                logits = self._forward_step(next_tok, pos, cache, accelerator)
                pos += 1

        return out
