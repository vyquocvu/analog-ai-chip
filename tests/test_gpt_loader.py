import json

import numpy as np
import pytest
from safetensors.numpy import save_file

from analog_llm.gpt_loader import _map_tensors, load_gpt2, read_safetensors
from analog_llm.reference_gpt2 import reference_forward

VOCAB, N_EMBD, N_LAYER, N_HEAD, N_POS = 8, 4, 1, 2, 16
BLOCK = 16


def _weights(rng):
    return {
        "transformer.wte.weight": rng.normal(size=(VOCAB, N_EMBD)),
        "transformer.wpe.weight": rng.normal(size=(N_POS, N_EMBD)),
        "transformer.ln_f.weight": rng.normal(size=N_EMBD),
        "transformer.ln_f.bias": rng.normal(size=N_EMBD),
        "transformer.h.0.ln_1.weight": rng.normal(size=N_EMBD),
        "transformer.h.0.ln_1.bias": rng.normal(size=N_EMBD),
        "transformer.h.0.ln_2.weight": rng.normal(size=N_EMBD),
        "transformer.h.0.ln_2.bias": rng.normal(size=N_EMBD),
        # Conv1D [in, out]
        "transformer.h.0.attn.c_attn.weight": rng.normal(size=(N_EMBD, 3 * N_EMBD)),
        "transformer.h.0.attn.c_attn.bias": rng.normal(size=3 * N_EMBD),
        "transformer.h.0.attn.c_proj.weight": rng.normal(size=(N_EMBD, N_EMBD)),
        "transformer.h.0.attn.c_proj.bias": rng.normal(size=N_EMBD),
        "transformer.h.0.mlp.c_fc.weight": rng.normal(size=(N_EMBD, 4 * N_EMBD)),
        "transformer.h.0.mlp.c_fc.bias": rng.normal(size=4 * N_EMBD),
        "transformer.h.0.mlp.c_proj.weight": rng.normal(size=(4 * N_EMBD, N_EMBD)),
        "transformer.h.0.mlp.c_proj.bias": rng.normal(size=N_EMBD),
    }


CONFIG = {
    "vocab_size": VOCAB, "n_embd": N_EMBD, "n_layer": N_LAYER,
    "n_head": N_HEAD, "n_positions": N_POS,
}


def _write_ckpt(tmp_path, weights, drop=None):
    data = {k: v for k, v in weights.items() if k != drop}
    tensors = {k: np.ascontiguousarray(v.astype(np.float32)) for k, v in data.items()}
    save_file(tensors, str(tmp_path / "model.safetensors"))
    with open(tmp_path / "config.json", "w") as fh:
        json.dump(CONFIG, fh)
    return weights


def test_loader_maps_and_ties_head(tmp_path) -> None:
    rng = np.random.default_rng(0)
    weights = _write_ckpt(tmp_path, _weights(rng))
    model = load_gpt2(tmp_path, block_size=BLOCK)
    mw = model.weights
    np.testing.assert_allclose(mw["head"], weights["transformer.wte.weight"])
    # Conv1D [in,out] -> simulator [out,in]
    np.testing.assert_allclose(
        mw["0.wqkv"], weights["transformer.h.0.attn.c_attn.weight"].T)
    np.testing.assert_allclose(
        mw["0.wdown"], weights["transformer.h.0.mlp.c_proj.weight"].T)
    np.testing.assert_allclose(
        mw["pos_emb"], weights["transformer.wpe.weight"][:BLOCK])


def test_loader_forward_matches_reference(tmp_path) -> None:
    rng = np.random.default_rng(7)
    _write_ckpt(tmp_path, _weights(rng))
    model = load_gpt2(tmp_path, block_size=BLOCK)
    tensors = read_safetensors(tmp_path / "model.safetensors")
    tokens = np.array([1, 3, 5, 7])
    ref = reference_forward(tensors, tokens, N_EMBD, N_LAYER, N_HEAD, BLOCK)
    sim = model.forward_logits(tokens)
    np.testing.assert_allclose(sim, ref, atol=1e-5)


def test_loader_fails_closed_on_missing_tensor(tmp_path) -> None:
    rng = np.random.default_rng(1)
    _write_ckpt(tmp_path, _weights(rng), drop="transformer.wte.weight")
    with pytest.raises(ValueError, match="wte"):
        load_gpt2(tmp_path, block_size=BLOCK)


def test_map_rejects_missing_bias(tmp_path) -> None:
    w = _weights(np.random.default_rng(2))
    del w["transformer.h.0.ln_1.bias"]
    with pytest.raises(ValueError, match="ln_1"):
        _map_tensors(w, VOCAB, N_EMBD, N_LAYER, BLOCK, tie_head=True)
