import json
from pathlib import Path

import numpy as np
import pytest
from safetensors.numpy import save_file

from analog_llm.checkpoint_loader import load_hf_checkpoint


def _create_gpt2_fixture(tmp_path: Path) -> Path:
    """Create a minimal synthetic GPT-2 checkpoint fixture."""
    vocab_size, hidden_size, num_layers, num_heads = 16, 8, 2, 2
    context_length = 6

    config = {
        "model_type": "gpt2",
        "vocab_size": vocab_size,
        "n_embd": hidden_size,
        "n_layer": num_layers,
        "n_head": num_heads,
        "n_inner": 16,
        "n_positions": context_length,
        "tie_word_embeddings": True,
    }
    with open(tmp_path / "config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    rng = np.random.default_rng(100)
    tensors: dict[str, np.ndarray] = {
        "transformer.wte.weight": rng.normal(0, 0.02, (vocab_size, hidden_size)).astype(np.float32),
        "transformer.wpe.weight": rng.normal(0, 0.02, (context_length, hidden_size)).astype(np.float32),
        "transformer.ln_f.weight": np.ones((hidden_size,), dtype=np.float32),
        "transformer.ln_f.bias": np.zeros((hidden_size,), dtype=np.float32),
    }
    for i in range(num_layers):
        p = f"transformer.h.{i}."
        tensors[f"{p}ln_1.weight"] = np.ones((hidden_size,), dtype=np.float32)
        tensors[f"{p}ln_1.bias"] = np.zeros((hidden_size,), dtype=np.float32)
        # Conv1D weights stored as [in_features, out_features]
        tensors[f"{p}attn.c_attn.weight"] = rng.normal(0, 0.02, (hidden_size, 3 * hidden_size)).astype(np.float32)
        tensors[f"{p}attn.c_attn.bias"] = np.zeros((3 * hidden_size,), dtype=np.float32)
        tensors[f"{p}attn.c_proj.weight"] = rng.normal(0, 0.02, (hidden_size, hidden_size)).astype(np.float32)
        tensors[f"{p}attn.c_proj.bias"] = np.zeros((hidden_size,), dtype=np.float32)
        tensors[f"{p}ln_2.weight"] = np.ones((hidden_size,), dtype=np.float32)
        tensors[f"{p}ln_2.bias"] = np.zeros((hidden_size,), dtype=np.float32)
        tensors[f"{p}mlp.c_fc.weight"] = rng.normal(0, 0.02, (hidden_size, 16)).astype(np.float32)
        tensors[f"{p}mlp.c_fc.bias"] = np.zeros((16,), dtype=np.float32)
        tensors[f"{p}mlp.c_proj.weight"] = rng.normal(0, 0.02, (16, hidden_size)).astype(np.float32)
        tensors[f"{p}mlp.c_proj.bias"] = np.zeros((hidden_size,), dtype=np.float32)

    save_file(tensors, str(tmp_path / "model.safetensors"))
    return tmp_path


def _create_sharded_llama_fixture(tmp_path: Path) -> Path:
    """Create a minimal synthetic 2-shard LLaMA GQA checkpoint fixture."""
    vocab_size, hidden_size, num_layers = 32, 16, 2
    num_heads, num_kv_heads = 4, 2
    intermediate_size = 32
    head_dim = hidden_size // num_heads

    config = {
        "model_type": "llama",
        "vocab_size": vocab_size,
        "hidden_size": hidden_size,
        "num_hidden_layers": num_layers,
        "num_attention_heads": num_heads,
        "num_key_value_heads": num_kv_heads,
        "intermediate_size": intermediate_size,
        "max_position_embeddings": 16,
        "tie_word_embeddings": False,
    }
    with open(tmp_path / "config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    rng = np.random.default_rng(200)

    # Shard 1: Embeddings, Layer 0
    shard1: dict[str, np.ndarray] = {
        "model.embed_tokens.weight": rng.normal(0, 0.02, (vocab_size, hidden_size)).astype(np.float32),
        "model.layers.0.input_layernorm.weight": np.ones((hidden_size,), dtype=np.float32),
        "model.layers.0.self_attn.q_proj.weight": rng.normal(0, 0.02, (hidden_size, hidden_size)).astype(np.float32),
        "model.layers.0.self_attn.k_proj.weight": rng.normal(0, 0.02, (num_kv_heads * head_dim, hidden_size)).astype(np.float32),
        "model.layers.0.self_attn.v_proj.weight": rng.normal(0, 0.02, (num_kv_heads * head_dim, hidden_size)).astype(np.float32),
        "model.layers.0.self_attn.o_proj.weight": rng.normal(0, 0.02, (hidden_size, hidden_size)).astype(np.float32),
        "model.layers.0.post_attention_layernorm.weight": np.ones((hidden_size,), dtype=np.float32),
        "model.layers.0.mlp.gate_proj.weight": rng.normal(0, 0.02, (intermediate_size, hidden_size)).astype(np.float32),
        "model.layers.0.mlp.up_proj.weight": rng.normal(0, 0.02, (intermediate_size, hidden_size)).astype(np.float32),
        "model.layers.0.mlp.down_proj.weight": rng.normal(0, 0.02, (hidden_size, intermediate_size)).astype(np.float32),
    }

    # Shard 2: Layer 1, Final Norm, LM Head
    shard2: dict[str, np.ndarray] = {
        "model.layers.1.input_layernorm.weight": np.ones((hidden_size,), dtype=np.float32),
        "model.layers.1.self_attn.q_proj.weight": rng.normal(0, 0.02, (hidden_size, hidden_size)).astype(np.float32),
        "model.layers.1.self_attn.k_proj.weight": rng.normal(0, 0.02, (num_kv_heads * head_dim, hidden_size)).astype(np.float32),
        "model.layers.1.self_attn.v_proj.weight": rng.normal(0, 0.02, (num_kv_heads * head_dim, hidden_size)).astype(np.float32),
        "model.layers.1.self_attn.o_proj.weight": rng.normal(0, 0.02, (hidden_size, hidden_size)).astype(np.float32),
        "model.layers.1.post_attention_layernorm.weight": np.ones((hidden_size,), dtype=np.float32),
        "model.layers.1.mlp.gate_proj.weight": rng.normal(0, 0.02, (intermediate_size, hidden_size)).astype(np.float32),
        "model.layers.1.mlp.up_proj.weight": rng.normal(0, 0.02, (intermediate_size, hidden_size)).astype(np.float32),
        "model.layers.1.mlp.down_proj.weight": rng.normal(0, 0.02, (hidden_size, intermediate_size)).astype(np.float32),
        "model.norm.weight": np.ones((hidden_size,), dtype=np.float32),
        "lm_head.weight": rng.normal(0, 0.02, (vocab_size, hidden_size)).astype(np.float32),
    }

    save_file(shard1, str(tmp_path / "model-00001-of-00002.safetensors"))
    save_file(shard2, str(tmp_path / "model-00002-of-00002.safetensors"))

    weight_map = {k: "model-00001-of-00002.safetensors" for k in shard1}
    weight_map.update({k: "model-00002-of-00002.safetensors" for k in shard2})

    index_data = {
        "metadata": {"total_size": sum(v.nbytes for v in shard1.values()) + sum(v.nbytes for v in shard2.values())},
        "weight_map": weight_map,
    }
    with open(tmp_path / "model.safetensors.index.json", "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2)

    return tmp_path


def test_gpt2_single_file_checkpoint_ingestion(tmp_path: Path) -> None:
    model_dir = _create_gpt2_fixture(tmp_path)
    result = load_hf_checkpoint(model_dir)

    assert result.manifest.attention_type == "mha"
    assert result.manifest.norm_type == "layernorm"
    assert result.manifest.position_type == "learned"
    assert result.manifest.activation_type == "gelu"
    assert result.manifest.tied_embeddings is True

    # Provenance verification
    assert len(result.inventory.provenance) == 2  # config.json + model.safetensors
    for prov in result.inventory.provenance:
        assert len(prov.sha256) == 64
        assert prov.size_bytes > 0

    # Inference test
    prompt = [2, 5, 1]
    logits = result.decoder.forward_logits(prompt)
    assert logits.shape == (3, 16)

    tokens = result.decoder.generate_kvcache(prompt, max_new=2)
    assert len(tokens) == 5


def test_sharded_llama_gqa_checkpoint_ingestion(tmp_path: Path) -> None:
    model_dir = _create_sharded_llama_fixture(tmp_path)
    result = load_hf_checkpoint(model_dir)

    assert result.manifest.attention_type == "gqa"
    assert result.manifest.norm_type == "rmsnorm"
    assert result.manifest.position_type == "rope"
    assert result.manifest.activation_type == "swiglu"
    assert result.manifest.tied_embeddings is False

    # 4 files recorded: config.json + index.json + 2 shards
    assert len(result.inventory.provenance) == 4

    prompt = [1, 4, 10, 2]
    full_logits = result.decoder.forward_logits(prompt)
    assert full_logits.shape == (4, 32)

    cache_gen = result.decoder.generate_kvcache(prompt, max_new=3)
    full_gen = result.decoder.generate(prompt, max_new=3)
    assert cache_gen == full_gen


def test_checkpoint_loader_fails_closed_on_missing_or_corrupt_files(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Missing config.json"):
        load_hf_checkpoint(tmp_path)

    # Shard index pointing to non-existent shard
    with open(tmp_path / "config.json", "w") as f:
        json.dump({"model_type": "llama", "vocab_size": 10, "hidden_size": 4}, f)
    with open(tmp_path / "model.safetensors.index.json", "w") as f:
        json.dump({"weight_map": {"foo": "missing_shard.safetensors"}}, f)

    with pytest.raises(FileNotFoundError, match="Missing safetensors shard"):
        load_hf_checkpoint(tmp_path)
