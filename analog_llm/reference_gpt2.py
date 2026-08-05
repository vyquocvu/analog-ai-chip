"""Independent pure-numpy GPT-2 forward used as a numeric-parity reference.

Takes the *raw* HuggingFace GPT-2 tensors (Conv1D layout, ``[in, out]``
weights, ``gelu_new`` activation) and computes logits directly, without going
through ``TinyGPT``. Comparing this to ``TinyGPT`` after ``load_gpt2`` verifies
that the loader's weight mapping (transpose, bias, head-tying) is correct.

This duplicates the forward in an intentionally different style on purpose: the
point is an independent reference for the loader, not a shared implementation.
"""

from __future__ import annotations

import math

import numpy as np

_EPS = 1e-5


def gelu_new(x: np.ndarray) -> np.ndarray:
    return 0.5 * x * (1.0 + np.tanh(math.sqrt(2.0 / math.pi) * (x + 0.044715 * x**3)))


def layernorm(x: np.ndarray, g: np.ndarray, b: np.ndarray) -> np.ndarray:
    mean = x.mean(axis=-1, keepdims=True)
    var = x.var(axis=-1, keepdims=True)
    return (x - mean) / np.sqrt(var + _EPS) * g + b


def _linear(x: np.ndarray, w: np.ndarray, bias: np.ndarray) -> np.ndarray:
    """Conv1D: x [B, in] @ w [in, out] + bias [out] -> [B, out]."""
    return x @ w + bias


def reference_forward(
    tensors: dict[str, np.ndarray],
    tokens: np.ndarray,
    n_embd: int,
    n_layer: int,
    n_head: int,
    block_size: int,
    tie_head: bool = True,
) -> np.ndarray:
    """Return logits ``[B, vocab]`` for ``tokens`` using raw GPT-2 tensors."""
    tokens = np.asarray(tokens, dtype=np.int64).reshape(-1)
    B = tokens.size
    if B > block_size:
        raise ValueError(f"sequence length {B} > block_size {block_size}")

    wte = tensors["transformer.wte.weight"]
    wpe = tensors["transformer.wpe.weight"]
    x = wte[tokens] + wpe[:B].astype(np.float64)
    hd = n_embd // n_head

    for i in range(n_layer):
        pre = f"transformer.h.{i}."
        x_in = x
        h = layernorm(x_in, tensors[pre + "ln_1.weight"], tensors[pre + "ln_1.bias"])
        qkv = _linear(h, tensors[pre + "attn.c_attn.weight"], tensors[pre + "attn.c_attn.bias"])
        C = n_embd
        q, k, v = qkv[:, :C], qkv[:, C:2 * C], qkv[:, 2 * C:]
        q = q.reshape(B, n_head, hd)
        k = k.reshape(B, n_head, hd)
        v = v.reshape(B, n_head, hd)
        scores = np.einsum("mhd,nhd->mhn", q, k) / math.sqrt(hd)
        mask = np.tril(np.ones((B, B), dtype=bool))
        scores = np.where(mask[:, None, :], scores, -1e4)
        probs = np.exp(scores - scores.max(axis=-1, keepdims=True))
        probs = probs / probs.sum(axis=-1, keepdims=True)
        attn = np.einsum("mhn,nhd->mhd", probs, v).reshape(B, C)
        x = x_in + _linear(attn, tensors[pre + "attn.c_proj.weight"], tensors[pre + "attn.c_proj.bias"])

        x_in = x
        h = layernorm(x_in, tensors[pre + "ln_2.weight"], tensors[pre + "ln_2.bias"])
        up = _linear(h, tensors[pre + "mlp.c_fc.weight"], tensors[pre + "mlp.c_fc.bias"])
        down = _linear(gelu_new(up), tensors[pre + "mlp.c_proj.weight"], tensors[pre + "mlp.c_proj.bias"])
        x = x_in + down

    x = layernorm(x, tensors["transformer.ln_f.weight"], tensors["transformer.ln_f.bias"])
    head = tensors.get("lm_head.weight", wte if tie_head else None)
    if head is None:
        raise ValueError("no lm_head.weight and tie_head=False")
    return x @ head.T
