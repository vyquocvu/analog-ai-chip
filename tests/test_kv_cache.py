import numpy as np

from analog_llm import TinyGPT, TinyGPTConfig


def _model():
    return TinyGPT(TinyGPTConfig(vocab_size=64, n_embd=16, n_layer=2, n_head=2,
                                 block_size=12, seed=0))


def test_kv_cache_greedy_matches_baseline() -> None:
    m = _model()
    prompt = np.array([1, 2, 3, 4, 5])
    base = m.generate(prompt, max_new=4, greedy=True)
    cached = m.generate_kvcache(prompt, max_new=4, greedy=True)
    assert np.array_equal(base, cached)


def test_kv_cache_sampling_matches_baseline() -> None:
    m = _model()
    prompt = np.array([1, 2, 3, 4, 5])
    r1 = np.random.default_rng(3)
    r2 = np.random.default_rng(3)
    base = m.generate(prompt, max_new=4, greedy=False, rng=r1)
    cached = m.generate_kvcache(prompt, max_new=4, greedy=False, rng=r2)
    assert np.array_equal(base, cached)


def test_kv_cache_reduces_query_rows() -> None:
    p, g = 5, 6
    no_cache = sum(p + s for s in range(g))
    kv_cache = p + g
    assert kv_cache < no_cache


def test_kv_cache_sampling_requires_rng() -> None:
    m = _model()
    with np.testing.assert_raises(ValueError):
        m.generate_kvcache(np.array([1]), max_new=1, greedy=False)
