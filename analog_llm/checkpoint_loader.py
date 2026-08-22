"""Architecture-neutral HuggingFace checkpoint ingestion engine.

Loads single-file and multi-shard safetensors checkpoints for GPT-2 and LLaMA
families, validating layout, transpositions, SHA256 provenance, and emitting
deterministic model inventories without duplicating full-model arrays.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .generalized_decoder import GeneralizedDecoder
from .model_manifest import ModelManifest


@dataclass(frozen=True)
class FileProvenance:
    filename: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class CheckpointInventory:
    model_family: str
    total_parameters: int
    analog_eligible_parameters: int
    digital_parameters: int
    total_bytes: int
    layer_projection_shapes: dict[str, tuple[int, ...]]
    provenance: list[FileProvenance]


@dataclass(frozen=True)
class CheckpointIngestionResult:
    manifest: ModelManifest
    weights: dict[str, np.ndarray]
    inventory: CheckpointInventory
    decoder: GeneralizedDecoder


def compute_file_sha256(path: Path) -> str:
    """Compute deterministic SHA256 digest of a file in streaming chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def read_safetensors_file(path: Path) -> dict[str, np.ndarray]:
    """Read a single safetensors file into numpy float64 arrays."""
    from safetensors import safe_open

    tensors: dict[str, np.ndarray] = {}
    with safe_open(str(path), framework="numpy") as f:
        for key in f.keys():  # noqa: SIM118
            tensors[key] = f.get_tensor(key).astype(np.float64)
    return tensors


def load_raw_checkpoint_tensors(model_dir: Path) -> tuple[dict[str, np.ndarray], list[FileProvenance]]:
    """Load tensors from single-file or sharded safetensors checkpoints."""
    provenance: list[FileProvenance] = []
    tensors: dict[str, np.ndarray] = {}

    index_path = model_dir / "model.safetensors.index.json"
    single_path = model_dir / "model.safetensors"

    if index_path.exists():
        provenance.append(
            FileProvenance(index_path.name, compute_file_sha256(index_path), index_path.stat().st_size)
        )
        with open(index_path, encoding="utf-8") as fh:
            index_data: dict[str, Any] = json.load(fh)
        weight_map: dict[str, str] = index_data.get("weight_map", {})
        shard_files = sorted(set(weight_map.values()))
        for shard_file in shard_files:
            shard_path = model_dir / shard_file
            if not shard_path.exists():
                raise FileNotFoundError(f"Missing safetensors shard: {shard_path}")
            provenance.append(
                FileProvenance(shard_file, compute_file_sha256(shard_path), shard_path.stat().st_size)
            )
            shard_tensors = read_safetensors_file(shard_path)
            for k, v in shard_tensors.items():
                if k in tensors:
                    raise ValueError(f"Duplicate tensor {k!r} across shards")
                tensors[k] = v
    elif single_path.exists():
        provenance.append(
            FileProvenance(single_path.name, compute_file_sha256(single_path), single_path.stat().st_size)
        )
        tensors = read_safetensors_file(single_path)
    else:
        raise FileNotFoundError(f"No safetensors checkpoint found in {model_dir}")

    return tensors, provenance


def _infer_gpt2_manifest(config: dict[str, Any], context_override: int | None = None) -> ModelManifest:
    """Build ModelManifest from HuggingFace GPT-2 config.json."""
    vocab_size = config.get("vocab_size", 50257)
    hidden_size = config.get("n_embd") or config.get("hidden_size", 768)
    num_layers = config.get("n_layer") or config.get("num_hidden_layers", 12)
    num_heads = config.get("n_head") or config.get("num_attention_heads", 12)
    intermediate_size = config.get("n_inner") or (4 * hidden_size)
    context_length = context_override or config.get("n_positions") or config.get("max_position_embeddings", 1024)
    tied = config.get("tie_word_embeddings", True)

    return ModelManifest(
        vocab_size=vocab_size,
        hidden_size=hidden_size,
        num_layers=num_layers,
        num_attention_heads=num_heads,
        num_key_value_heads=num_heads,
        intermediate_size=intermediate_size,
        context_length=context_length,
        dtype="float32",
        norm_type="layernorm",
        position_type="learned",
        activation_type="gelu",
        attention_type="mha",
        linear_bias=True,
        tied_embeddings=tied,
        tensor_layout="out_in",
    )


def _map_gpt2_tensors(raw: dict[str, np.ndarray], manifest: ModelManifest) -> dict[str, np.ndarray]:
    """Map HuggingFace GPT-2 tensors to canonical ModelManifest layout."""
    w: dict[str, np.ndarray] = {}
    h = manifest.hidden_size
    ctx = manifest.context_length

    # Embeddings
    w["token_embedding.weight"] = raw["transformer.wte.weight"][: manifest.vocab_size]
    w["position_embedding.weight"] = raw["transformer.wpe.weight"][:ctx]
    w["final_norm.weight"] = raw["transformer.ln_f.weight"]
    w["final_norm.bias"] = raw["transformer.ln_f.bias"]

    if not manifest.tied_embeddings:
        w["lm_head.weight"] = raw.get("lm_head.weight", w["token_embedding.weight"])

    for i in range(manifest.num_layers):
        p_hf = f"transformer.h.{i}."
        p_out = f"layers.{i}."

        w[f"{p_out}attention_norm.weight"] = raw[f"{p_hf}ln_1.weight"]
        w[f"{p_out}attention_norm.bias"] = raw[f"{p_hf}ln_1.bias"]

        # Conv1D attention projection [hidden, 3*hidden] -> transpose to [3*hidden, hidden]
        c_attn_w = raw[f"{p_hf}attn.c_attn.weight"].T
        c_attn_b = raw[f"{p_hf}attn.c_attn.bias"]
        w[f"{p_out}attention.q_proj.weight"] = c_attn_w[:h, :]
        w[f"{p_out}attention.q_proj.bias"] = c_attn_b[:h]
        w[f"{p_out}attention.k_proj.weight"] = c_attn_w[h : 2 * h, :]
        w[f"{p_out}attention.k_proj.bias"] = c_attn_b[h : 2 * h]
        w[f"{p_out}attention.v_proj.weight"] = c_attn_w[2 * h :, :]
        w[f"{p_out}attention.v_proj.bias"] = c_attn_b[2 * h :]

        # Out projection [hidden, hidden] -> transpose to [hidden, hidden]
        w[f"{p_out}attention.out_proj.weight"] = raw[f"{p_hf}attn.c_proj.weight"].T
        w[f"{p_out}attention.out_proj.bias"] = raw[f"{p_hf}attn.c_proj.bias"]

        # MLP
        w[f"{p_out}mlp_norm.weight"] = raw[f"{p_hf}ln_2.weight"]
        w[f"{p_out}mlp_norm.bias"] = raw[f"{p_hf}ln_2.bias"]

        # c_fc [hidden, intermediate] -> transpose to [intermediate, hidden]
        w[f"{p_out}mlp.up_proj.weight"] = raw[f"{p_hf}mlp.c_fc.weight"].T
        w[f"{p_out}mlp.up_proj.bias"] = raw[f"{p_hf}mlp.c_fc.bias"]

        # c_proj [intermediate, hidden] -> transpose to [hidden, intermediate]
        w[f"{p_out}mlp.down_proj.weight"] = raw[f"{p_hf}mlp.c_proj.weight"].T
        w[f"{p_out}mlp.down_proj.bias"] = raw[f"{p_hf}mlp.c_proj.bias"]

    return w


def _infer_llama_manifest(config: dict[str, Any], context_override: int | None = None) -> ModelManifest:
    """Build ModelManifest from HuggingFace LLaMA / Mistral config.json."""
    vocab_size = config.get("vocab_size", 32000)
    hidden_size = config.get("hidden_size", 4096)
    num_layers = config.get("num_hidden_layers", 32)
    num_heads = config.get("num_attention_heads", 32)
    num_kv_heads = config.get("num_key_value_heads") or num_heads
    intermediate_size = config.get("intermediate_size", 11008)
    context_length = context_override or config.get("max_position_embeddings", 4096)
    tied = config.get("tie_word_embeddings", False)

    if num_kv_heads == num_heads:
        attn_type = "mha"
    elif num_kv_heads == 1:
        attn_type = "mqa"
    else:
        attn_type = "gqa"

    return ModelManifest(
        vocab_size=vocab_size,
        hidden_size=hidden_size,
        num_layers=num_layers,
        num_attention_heads=num_heads,
        num_key_value_heads=num_kv_heads,
        intermediate_size=intermediate_size,
        context_length=context_length,
        dtype="float16",
        norm_type="rmsnorm",
        position_type="rope",
        activation_type="swiglu",
        attention_type=attn_type,
        linear_bias=False,
        tied_embeddings=tied,
        tensor_layout="out_in",
    )


def _map_llama_tensors(raw: dict[str, np.ndarray], manifest: ModelManifest) -> dict[str, np.ndarray]:
    """Map HuggingFace LLaMA tensors to canonical ModelManifest layout."""
    w: dict[str, np.ndarray] = {
        "token_embedding.weight": raw["model.embed_tokens.weight"][: manifest.vocab_size],
        "final_norm.weight": raw["model.norm.weight"],
    }

    if not manifest.tied_embeddings:
        w["lm_head.weight"] = raw["lm_head.weight"]

    for i in range(manifest.num_layers):
        p_hf = f"model.layers.{i}."
        p_out = f"layers.{i}."

        w[f"{p_out}attention_norm.weight"] = raw[f"{p_hf}input_layernorm.weight"]
        w[f"{p_out}attention.q_proj.weight"] = raw[f"{p_hf}self_attn.q_proj.weight"]
        w[f"{p_out}attention.k_proj.weight"] = raw[f"{p_hf}self_attn.k_proj.weight"]
        w[f"{p_out}attention.v_proj.weight"] = raw[f"{p_hf}self_attn.v_proj.weight"]
        w[f"{p_out}attention.out_proj.weight"] = raw[f"{p_hf}self_attn.o_proj.weight"]

        w[f"{p_out}mlp_norm.weight"] = raw[f"{p_hf}post_attention_layernorm.weight"]
        w[f"{p_out}mlp.gate_proj.weight"] = raw[f"{p_hf}mlp.gate_proj.weight"]
        w[f"{p_out}mlp.up_proj.weight"] = raw[f"{p_hf}mlp.up_proj.weight"]
        w[f"{p_out}mlp.down_proj.weight"] = raw[f"{p_hf}mlp.down_proj.weight"]

    return w


def load_hf_checkpoint(
    model_dir: str | Path,
    context_length: int | None = None,
) -> CheckpointIngestionResult:
    """Ingest a HuggingFace checkpoint directory with strict schema & provenance validation."""
    model_dir = Path(model_dir)
    config_path = model_dir / "config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Missing config.json in {model_dir}")

    config_prov = FileProvenance(
        config_path.name, compute_file_sha256(config_path), config_path.stat().st_size
    )
    with open(config_path, encoding="utf-8") as fh:
        config: dict[str, Any] = json.load(fh)

    raw_tensors, shard_prov = load_raw_checkpoint_tensors(model_dir)
    all_prov = [config_prov] + shard_prov

    model_type = config.get("model_type", "").lower()
    if "gpt2" in model_type or "n_embd" in config or "transformer.wte.weight" in raw_tensors:
        manifest = _infer_gpt2_manifest(config, context_override=context_length)
        weights = _map_gpt2_tensors(raw_tensors, manifest)
        family = "gpt2"
    elif "llama" in model_type or "mistral" in model_type or "model.embed_tokens.weight" in raw_tensors:
        manifest = _infer_llama_manifest(config, context_override=context_length)
        weights = _map_llama_tensors(raw_tensors, manifest)
        family = "llama"
    else:
        raise ValueError(f"Unsupported model architecture in {config_path}")

    # Validate mapped tensors against manifest
    manifest.validate_tensors({k: v.shape for k, v in weights.items()})

    # Generate analytical inventory
    specs = manifest.tensor_specs()
    analog_params = sum(spec.parameters for spec in specs.values() if spec.analog_eligible)
    digital_params = sum(spec.parameters for spec in specs.values() if not spec.analog_eligible)
    total_params = analog_params + digital_params
    total_bytes = sum(v.nbytes for v in weights.values())

    layer_shapes = {
        "attention.q_proj": specs["layers.0.attention.q_proj.weight"].shape,
        "attention.k_proj": specs["layers.0.attention.k_proj.weight"].shape,
        "attention.v_proj": specs["layers.0.attention.v_proj.weight"].shape,
        "attention.out_proj": specs["layers.0.attention.out_proj.weight"].shape,
        "mlp.up_proj": specs["layers.0.mlp.up_proj.weight"].shape,
        "mlp.down_proj": specs["layers.0.mlp.down_proj.weight"].shape,
    }
    if manifest.activation_type == "swiglu":
        layer_shapes["mlp.gate_proj"] = specs["layers.0.mlp.gate_proj.weight"].shape

    inventory = CheckpointInventory(
        model_family=family,
        total_parameters=total_params,
        analog_eligible_parameters=analog_params,
        digital_parameters=digital_params,
        total_bytes=total_bytes,
        layer_projection_shapes=layer_shapes,
        provenance=all_prov,
    )

    decoder = GeneralizedDecoder(manifest, weights=weights)

    return CheckpointIngestionResult(
        manifest=manifest,
        weights=weights,
        inventory=inventory,
        decoder=decoder,
    )
