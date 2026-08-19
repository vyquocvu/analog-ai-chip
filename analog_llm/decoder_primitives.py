"""Reusable digital decoder primitives for architecture-neutral references.

These deterministic NumPy operations establish functional semantics only.
Static projection matrices may later be routed to simulated analog tiles;
normalization, position rotation, activation, and token-token attention remain
explicitly digital in the current hybrid boundary.
"""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray


FloatArray = NDArray[np.float64]


def layer_norm(
    x: FloatArray, weight: FloatArray, bias: FloatArray, epsilon: float = 1e-5
) -> FloatArray:
    """Layer-normalize the final dimension, then apply learned scale and bias."""
    x, weight, bias = _normalization_inputs(x, weight, bias, epsilon)
    mean = x.mean(axis=-1, keepdims=True)
    variance = x.var(axis=-1, keepdims=True)
    return (x - mean) / np.sqrt(variance + epsilon) * weight + bias


def rms_norm(x: FloatArray, weight: FloatArray, epsilon: float = 1e-6) -> FloatArray:
    """RMS-normalize the final dimension without centering or learned bias."""
    x, weight, _ = _normalization_inputs(x, weight, None, epsilon)
    return x * np.reciprocal(np.sqrt(np.mean(x * x, axis=-1, keepdims=True) + epsilon)) * weight


def _normalization_inputs(x, weight, bias, epsilon):
    x = np.asarray(x, dtype=np.float64)
    weight = np.asarray(weight, dtype=np.float64)
    if x.ndim == 0 or weight.shape != (x.shape[-1],):
        raise ValueError("normalization weight must match the final input dimension")
    if bias is not None:
        bias = np.asarray(bias, dtype=np.float64)
        if bias.shape != weight.shape:
            raise ValueError("normalization bias must match weight")
    if not math.isfinite(epsilon) or epsilon <= 0:
        raise ValueError("epsilon must be finite and positive")
    return x, weight, bias


def gelu(x: FloatArray) -> FloatArray:
    """GPT-2's deterministic tanh GELU approximation."""
    x = np.asarray(x, dtype=np.float64)
    return 0.5 * x * (1.0 + np.tanh(math.sqrt(2.0 / math.pi) * (x + 0.044715 * x**3)))


def silu(x: FloatArray) -> FloatArray:
    """SiLU activation, evaluated with a stable sigmoid."""
    x = np.asarray(x, dtype=np.float64)
    sigmoid = np.empty_like(x)
    positive = x >= 0
    sigmoid[positive] = 1.0 / (1.0 + np.exp(-x[positive]))
    exp_x = np.exp(x[~positive])
    sigmoid[~positive] = exp_x / (1.0 + exp_x)
    return x * sigmoid


def swiglu(gate: FloatArray, up: FloatArray) -> FloatArray:
    """Apply the gated ``SiLU(gate) * up`` SwiGLU combination."""
    gate = np.asarray(gate, dtype=np.float64)
    up = np.asarray(up, dtype=np.float64)
    if gate.shape != up.shape:
        raise ValueError("SwiGLU gate and up projections must have identical shapes")
    return silu(gate) * up


def apply_rope(
    x: FloatArray, positions: NDArray[np.int64] | list[int] | tuple[int, ...], base: float = 10000.0
) -> FloatArray:
    """Apply non-interleaved rotary positions to ``[..., heads, head_dim]``.

    Adjacent values form each rotary pair. ``positions`` must have one entry for
    the first (token) dimension. Angles are dimensionless; ``base`` is the
    conventional RoPE frequency base.
    """
    x = np.asarray(x, dtype=np.float64)
    positions = np.asarray(positions)
    if x.ndim < 2 or x.shape[-1] % 2:
        raise ValueError("RoPE requires an even final head dimension")
    if positions.ndim != 1 or positions.shape[0] != x.shape[0]:
        raise ValueError("RoPE positions must match the token dimension")
    if not np.issubdtype(positions.dtype, np.integer) or np.any(positions < 0):
        raise ValueError("RoPE positions must be non-negative integers")
    if not math.isfinite(base) or base <= 0:
        raise ValueError("RoPE base must be finite and positive")
    frequencies = base ** (-np.arange(0, x.shape[-1], 2, dtype=np.float64) / x.shape[-1])
    angles = positions.astype(np.float64)[:, None] * frequencies[None, :]
    shape = (x.shape[0],) + (1,) * (x.ndim - 2) + (x.shape[-1] // 2,)
    cosine, sine = np.cos(angles).reshape(shape), np.sin(angles).reshape(shape)
    even, odd = x[..., 0::2], x[..., 1::2]
    result = np.empty_like(x)
    result[..., 0::2] = even * cosine - odd * sine
    result[..., 1::2] = even * sine + odd * cosine
    return result


def causal_attention(query: FloatArray, key: FloatArray, value: FloatArray) -> FloatArray:
    """Causal MHA/GQA/MQA for Q ``[T,QH,D]`` and K/V ``[T,KVH,D]``."""
    query, key, value, groups = _attention_inputs(query, key, value)
    tokens, query_heads, dimension = query.shape
    key_for_query = np.repeat(key, groups, axis=1)
    value_for_query = np.repeat(value, groups, axis=1)
    scores = np.einsum("mhd,nhd->mhn", query, key_for_query) / math.sqrt(dimension)
    causal = np.tril(np.ones((tokens, tokens), dtype=bool))
    scores = np.where(causal[:, None, :], scores, -np.inf)
    probabilities = _softmax(scores)
    return np.einsum("mhn,nhd->mhd", probabilities, value_for_query).reshape(
        tokens, query_heads, dimension
    )


def cached_attention_step(query: FloatArray, key: FloatArray, value: FloatArray) -> FloatArray:
    """Attend one query ``[QH,D]`` over cached K/V ``[T,KVH,D]``."""
    query = np.asarray(query, dtype=np.float64)
    if query.ndim != 2:
        raise ValueError("cached attention query must have shape [query_heads, head_dim]")
    key = np.asarray(key, dtype=np.float64)
    value = np.asarray(value, dtype=np.float64)
    if key.ndim != 3 or value.shape != key.shape or key.shape[0] == 0:
        raise ValueError("cached attention requires non-empty matching K/V [T,KVH,D]")
    if query.shape[1] != key.shape[2] or key.shape[1] == 0 or query.shape[0] % key.shape[1]:
        raise ValueError("cached query heads must group evenly over K/V heads with matching dimensions")
    groups = query.shape[0] // key.shape[1]
    key_for_query = np.repeat(key, groups, axis=1)
    value_for_query = np.repeat(value, groups, axis=1)
    scores = np.einsum("hd,thd->ht", query, key_for_query) / math.sqrt(
        query.shape[-1]
    )
    return np.einsum("ht,thd->hd", _softmax(scores), value_for_query)


def _attention_inputs(query, key, value):
    query = np.asarray(query, dtype=np.float64)
    key = np.asarray(key, dtype=np.float64)
    value = np.asarray(value, dtype=np.float64)
    if query.ndim != 3 or key.ndim != 3 or value.shape != key.shape:
        raise ValueError("attention expects Q [T,QH,D] and matching K/V [T,KVH,D]")
    if query.shape[0] != key.shape[0] or query.shape[2] != key.shape[2]:
        raise ValueError("attention Q/K/V token counts and head dimensions must match")
    if key.shape[1] == 0 or query.shape[1] % key.shape[1]:
        raise ValueError("query heads must be divisible by key/value heads")
    return query, key, value, query.shape[1] // key.shape[1]


def _softmax(x: FloatArray) -> FloatArray:
    shifted = x - np.max(x, axis=-1, keepdims=True)
    exponent = np.exp(shifted)
    return exponent / exponent.sum(axis=-1, keepdims=True)
