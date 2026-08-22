import math

import numpy as np
import pytest

from analog_llm.decoder_primitives import (
    apply_rope,
    cached_attention_step,
    causal_attention,
    layer_norm,
    rms_norm,
    swiglu,
)


def _scalar_attention_reference(query, key, value):
    """Independent loop reference that expands KV heads without einsum."""
    tokens, query_heads, dimension = query.shape
    groups = query_heads // key.shape[1]
    output = np.zeros_like(query)
    for token in range(tokens):
        for head in range(query_heads):
            kv_head = head // groups
            scores = []
            for source in range(token + 1):
                scores.append(
                    sum(query[token, head, d] * key[source, kv_head, d] for d in range(dimension))
                    / math.sqrt(dimension)
                )
            probabilities = np.exp(scores - np.max(scores))
            probabilities /= probabilities.sum()
            for d in range(dimension):
                output[token, head, d] = sum(
                    probabilities[source] * value[source, kv_head, d] for source in range(token + 1)
                )
    return output


def test_norms_and_swiglu_have_hand_computable_values() -> None:
    x = np.array([[3.0, 4.0]])
    # RMS=sqrt((9+16)/2)=sqrt(12.5); epsilon zero is intentionally not allowed,
    # so include the stated dimensionless epsilon in the hand expression.
    np.testing.assert_allclose(
        rms_norm(x, np.array([1.0, 2.0]), epsilon=1e-6),
        x / math.sqrt(12.5 + 1e-6) * np.array([1.0, 2.0]),
    )
    np.testing.assert_allclose(
        layer_norm(np.array([[1.0, 3.0]]), np.ones(2), np.zeros(2)),
        np.array([[-1.0, 1.0]]) / math.sqrt(1.0 + 1e-5),
    )
    np.testing.assert_allclose(
        swiglu(np.array([0.0, math.log(3.0)]), np.array([4.0, 2.0])),
        np.array([0.0, 1.5 * math.log(3.0)]),
    )


def test_rope_rotates_one_pair_by_position_angle() -> None:
    vectors = np.array([[[1.0, 0.0]], [[1.0, 0.0]]])
    rotated = apply_rope(vectors, [0, 1])
    np.testing.assert_allclose(rotated[0, 0], [1.0, 0.0])
    np.testing.assert_allclose(rotated[1, 0], [math.cos(1.0), math.sin(1.0)])


@pytest.mark.parametrize("query_heads,kv_heads", [(4, 4), (4, 2), (4, 1)])
def test_mha_gqa_mqa_full_context_matches_cache_and_scalar_reference(query_heads, kv_heads) -> None:
    rng = np.random.default_rng(17 + kv_heads)
    query = rng.normal(size=(3, query_heads, 2))
    key = rng.normal(size=(3, kv_heads, 2))
    value = rng.normal(size=(3, kv_heads, 2))

    full = causal_attention(query, key, value)
    reference = _scalar_attention_reference(query, key, value)
    cached = np.stack(
        [cached_attention_step(query[t], key[: t + 1], value[: t + 1]) for t in range(3)]
    )
    np.testing.assert_allclose(full, reference, atol=1e-12)
    np.testing.assert_allclose(cached, full, atol=1e-12)


def test_primitives_fail_closed_on_invalid_boundaries() -> None:
    with pytest.raises(ValueError, match="even"):
        apply_rope(np.zeros((1, 2, 3)), [0])
    with pytest.raises(ValueError, match="divisible"):
        causal_attention(np.zeros((1, 3, 2)), np.zeros((1, 2, 2)), np.zeros((1, 2, 2)))
    with pytest.raises(ValueError, match="identical"):
        swiglu(np.zeros(2), np.zeros(3))
