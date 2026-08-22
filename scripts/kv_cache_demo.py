"""B5 — KV-cache path in the transformer (ROADMAP M3).

``TinyGPT.generate`` recomputes attention over the full context at every
generation step (no KV cache). ``generate_kvcache`` caches per-layer keys and
values so each new token runs a single-position forward that reuses the cached
K/V instead of re-embedding and re-attending over the whole sequence.

This demo:
  1. confirms the KV-cache path is numerically identical to the baseline
     (greedy and sampling) — same math, just not recomputed;
  2. reports a redundancy ledger: how many attention query-rows each path
     computes, and the reduction factor of the KV cache.

The redundancy is a *logical work* ledger (rows of forward pass), not wall-clock
or energy; no GPU comparison is claimed.
"""

import numpy as np

from analog_llm import TinyGPT, TinyGPTConfig


def attn_rows_contextual(prompt_len: int, max_new: int) -> tuple[int, int]:
    """Total attention query-rows: no-cache vs KV-cache."""
    no_cache = sum(prompt_len + s for s in range(max_new))
    kv_cache = prompt_len + max_new
    return no_cache, kv_cache


def main() -> None:
    cfg = TinyGPTConfig(vocab_size=128, n_embd=32, n_layer=2, n_head=4, block_size=16, seed=0)
    model = TinyGPT(cfg)
    prompt = np.array([3, 9, 14, 22, 5])
    max_new = 6
    assert prompt.size + max_new <= cfg.block_size

    base = model.generate(prompt, max_new=max_new, greedy=True)
    cached = model.generate_kvcache(prompt, max_new=max_new, greedy=True)

    n_rows, k_rows = attn_rows_contextual(prompt.size, max_new)
    reduction = n_rows / k_rows

    print("=" * 70)
    print("B5 — KV-cache path in the transformer")
    print("=" * 70)
    print(f"prompt length P = {prompt.size}, generated G = {max_new}")
    print(f"base  (no cache): {base.tolist()}")
    print(f"cached    (KV)  : {cached.tolist()}")
    print("-" * 70)
    print("attention query-rows computed per generation:")
    print(f"  no KV cache : {n_rows}   (sum over steps of growing context)")
    print(f"  with KV     : {k_rows}   (1 new position per step + prompt warmup)")
    print(f"  reduction   : {reduction:.2f}x")
    print("-" * 70)
    print(f"greedy parity : {np.array_equal(base, cached)}")

    # sampling parity under identical RNG draws
    r1 = np.random.default_rng(11)
    r2 = np.random.default_rng(11)
    sbase = model.generate(prompt, max_new=max_new, greedy=False, rng=r1)
    scache = model.generate_kvcache(prompt, max_new=max_new, greedy=False, rng=r2)
    print(f"sampling parity (same seed): {np.array_equal(sbase, scache)}")

    assert np.array_equal(base, cached), "KV-cache greedy must match baseline"
    assert np.array_equal(sbase, scache), "KV-cache sampling must match baseline"
    assert reduction > 1.0, "KV cache must reduce forward work"

    # simple reduction bar SVG
    rows = max(n_rows, k_rows)
    bar = (f'<rect x="160" y="120" width="{n_rows / rows * 700:.0f}" height="46" '
           f'fill="#922b21"/><text x="170" y="149" font-size="13" fill="#fff">no KV cache: {n_rows} rows</text>'
           f'<rect x="160" y="190" width="{k_rows / rows * 700:.0f}" height="46" '
           f'fill="#1a5276"/><text x="170" y="219" font-size="13" fill="#fff">with KV cache: {k_rows} rows</text>')
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 340" width="960" height="340" font-family="Menlo,Consolas,monospace">
<rect width="960" height="340" fill="#ffffff"/>
<text x="480" y="40" text-anchor="middle" font-size="18" font-weight="bold" fill="#111">KV cache removes redundant attention recompute</text>
<text x="480" y="64" text-anchor="middle" font-size="12" fill="#7f8c8d">total attention query-rows over {max_new} generated tokens, prompt length {prompt.size} (logical work ledger)</text>
{bar}
<text x="160" y="280" font-size="13" fill="#111">reduction: {reduction:.2f}x fewer query-rows ({n_rows} -> {k_rows})</text>
</svg>"""
    with open("scripts/kv_cache.svg", "w") as fh:
        fh.write(svg)
    print("\nwrote scripts/kv_cache.svg")


if __name__ == "__main__":
    main()
