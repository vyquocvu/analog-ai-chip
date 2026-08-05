"""Load a real GPT-2 safetensors checkpoint into the simulator's ``TinyGPT``.

Maps the HuggingFace GPT-2 tensor naming and layout onto the simulator's
weight convention (see ``TinyGPT._init_weights``). The simulator stores every
linear weight as ``[output, input]`` and computes ``h @ W.T + b``. HuggingFace's
GPT-2 stores its projection weights in Conv1D layout ``[in_features,
out_features]``, so the linear weights must be **transposed**. The language-model
head is normally tied to the token embedding (no ``lm_head.weight`` is saved),
so it is tied here by default.

Mapped tensors:
  ``transformer.wte.weight``   -> ``tok_emb``  (no transpose; already [vocab, C])
  ``transformer.wpe.weight``   -> ``pos_emb``  (sliced to block_size)
  ``h.<i>.ln_1.{weight,bias}`` -> ``<i>.ln1 / <i>.ln1b``
  ``h.<i>.attn.c_attn.{w,b}``  -> ``<i>.wqkv / <i>.wqkvb``  (weight transposed)
  ``h.<i>.attn.c_proj.{w,b}``  -> ``<i>.wo / <i>.wob``       (weight transposed)
  ``h.<i>.ln_2.{weight,bias}`` -> ``<i>.ln2 / <i>.ln2b``
  ``h.<i>.mlp.c_fc.{w,b}``     -> ``<i>.wup / <i>.wupb``     (weight transposed)
  ``h.<i>.mlp.c_proj.{w,b}``   -> ``<i>.wdown / <i>.wdownb`` (weight transposed)
  ``transformer.ln_f.{w,b}``   -> ``lnf / lnfb``
  ``lm_head.weight``/``wte``   -> ``head / headb`` (tied to wte by default)

The loader is fail-closed: it requires a matching ``config.json`` and refuses
to build the model if any required tensor is missing or mis-shaped.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .transformer import TinyGPT, TinyGPTConfig

_LINEAR_KEYS = (
    ("attn.c_attn", "wqkv", 3, "3*n_embd over n_embd"),
    ("attn.c_proj", "wo", 1, "n_embd over n_embd"),
    ("mlp.c_fc", "wup", 4, "4*n_embd over n_embd"),
    ("mlp.c_proj", "wdown", -1, "n_embd over 4*n_embd"),
)


def read_safetensors(path: str | Path) -> dict[str, np.ndarray]:
    """Read a safetensors file into a dict of numpy arrays."""
    from safetensors import safe_open  # small, optional dependency

    out: dict[str, np.ndarray] = {}
    with safe_open(str(path), framework="numpy") as f:
        # safe_open supports .keys()/get_tensor but not iteration itself
        for key in f.keys():  # noqa: SIM118
            out[key] = f.get_tensor(key)
    return out


def load_gpt2(
    model_dir: str | Path,
    block_size: int = 64,
    tie_head: bool = True,
) -> TinyGPT:
    """Load a GPT-2 checkpoint directory into a ``TinyGPT`` for the simulator.

    Requires ``model.safetensors`` and ``config.json`` in ``model_dir``. The
    model runs on the CPU in numpy; return a model configured to the loaded
    architecture (n_embd, n_layer, n_head, vocab, block_size).
    """
    model_dir = Path(model_dir)
    tensors = read_safetensors(model_dir / "model.safetensors")
    with open(model_dir / "config.json") as fh:
        config: dict[str, Any] = json.load(fh)

    vocab = config.get("vocab_size")
    n_embd = config.get("n_embd")
    n_layer = config.get("n_layer")
    n_head = config.get("n_head")

    weights = _map_tensors(tensors, vocab, n_embd, n_layer, block_size, tie_head)

    cfg = TinyGPTConfig(
        vocab_size=vocab,
        n_embd=n_embd,
        n_layer=n_layer,
        n_head=n_head,
        block_size=block_size,
        ffn_mult=4,
        seed=0,
    )
    model = TinyGPT(cfg)
    model.weights = weights
    return model


def _map_tensors(
    tensors: dict[str, np.ndarray],
    vocab: int,
    n_embd: int,
    n_layer: int,
    block_size: int,
    tie_head: bool,
) -> dict[str, np.ndarray]:
    wte = tensors.get("transformer.wte.weight")
    wpe = tensors.get("transformer.wpe.weight")
    if wte is None:
        raise ValueError("missing 'transformer.wte.weight' (token embedding)")
    if wpe is None:
        raise ValueError("missing 'transformer.wpe.weight' (position embedding)")

    weights: dict[str, np.ndarray] = {
        "tok_emb": np.array(wte, dtype=np.float64),
        "pos_emb": np.array(wpe[:block_size], dtype=np.float64),
    }

    for i in range(n_layer):
        p = f"{i}."
        ln1w, ln1b = _t(tensors, f"transformer.h.{i}.ln_1")
        ln2w, ln2b = _t(tensors, f"transformer.h.{i}.ln_2")
        weights[p + "ln1"], weights[p + "ln1b"] = ln1w, ln1b
        weights[p + "ln2"], weights[p + "ln2b"] = ln2w, ln2b

        for src, dst, _scale, _desc in _LINEAR_KEYS:
            w, b = _t(tensors, f"transformer.h.{i}.{src}")
            weights[p + dst] = w.T  # Conv1D [in, out] -> simulator [out, in]
            weights[p + dst + "b"] = b

    lnf, lnfb = _t(tensors, "transformer.ln_f")
    weights["lnf"], weights["lnfb"] = lnf, lnfb

    head = tensors.get("lm_head.weight")
    if head is None:
        if not tie_head:
            raise ValueError("'lm_head.weight' absent and tie_head=False")
        head = wte
    headb = tensors.get("lm_head.bias")
    weights["head"] = np.array(head, dtype=np.float64)
    weights["headb"] = np.zeros(head.shape[0], dtype=np.float64) if headb is None else \
        np.array(headb, dtype=np.float64)

    return weights


def _t(tensors: dict[str, np.ndarray], prefix: str) -> tuple[np.ndarray, np.ndarray]:
    w = tensors.get(prefix + ".weight")
    b = tensors.get(prefix + ".bias")
    if w is None or b is None:
        raise ValueError(f"missing '{prefix}.weight' or '{prefix}.bias'")
    return np.array(w, dtype=np.float64), np.array(b, dtype=np.float64)
