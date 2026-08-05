"""B6 — per-token ledger trace through a full layer (ROADMAP M3).

For each generated token, run one complete forward and capture the physical
ledger the tile accelerator accumulates *for that token*: MACs (tile MVM
work), tile_cycles (sequential block-MVM lower bound), and rewrites (temporal
reuse). We trace two paths:

  - **no KV cache**: each step re-runs the full context forward, so per-token
    MACs grow linearly with context length (the redundancy B5 removes);
  - **with KV cache**: each new token is a single-position forward, so the
    per-token MACs stay constant (one position of tile MVM work).

The ledger counts tile MVM MACs only (not the digital softmax/attention scores),
which is exactly what the crossbar accelerates. This is a *logical work* ledger,
not wall-clock time or energy; no GPU comparison is claimed.
"""

import numpy as np

from analog_llm import Accelerator, CrossbarTile, Metrics, TinyGPT, TinyGPTConfig
from analog_llm.latency import PhysicsAssumptions, system_analysis

TILE_ROWS, TILE_COLS, TILE_COUNT = 32, 32, 4

# designer-supplied relative timings (assumptions, not measured)
_ASSUME = PhysicsAssumptions(mvm_cycle_time=1.0, program_time=0.2)


def latency_est(ledger: dict) -> float:
    m = Metrics(macs=ledger["macs"], cycles=ledger["cycles"],
                rewrites=ledger["rewrites"], programs=ledger.get("programs", ledger["rewrites"]))
    return system_analysis(m, TILE_ROWS, TILE_COLS, TILE_COUNT, _ASSUME)["latency"]


def build_acc() -> Accelerator:
    def factory() -> CrossbarTile:
        return CrossbarTile(TILE_ROWS, TILE_COLS, g_bits=14, dac_bits=16,
                            adc_bits=16, vout_max=96.0)
    return Accelerator(factory, TILE_ROWS, TILE_COLS, TILE_COUNT)


def trace_full_forward(model, out, step, acc) -> dict:
    """Ledger delta for a *full-context* forward (no KV cache)."""
    ctx = np.asarray(out[: step + 1], dtype=np.int64)[-model.cfg.block_size:]
    acc.reset_ledger()
    model.forward_logits(ctx, accelerator=acc)
    return {"macs": acc.macs, "cycles": acc.tile_cycles, "rewrites": acc.rewrites,
            "programs": acc.programs}


def trace_single_position(model, token, acc) -> dict:
    """Ledger delta for a *single-position* forward (KV-cache step)."""
    acc.reset_ledger()
    model.forward_logits(np.asarray([token], dtype=np.int64), accelerator=acc)
    return {"macs": acc.macs, "cycles": acc.tile_cycles, "rewrites": acc.rewrites,
            "programs": acc.programs}


def make_svg(rows: list, kv_row: dict, path: str) -> None:
    X0, X1, Y0, Y1 = 120.0, 880.0, 90.0, 300.0
    xs = [r["step"] for r in rows]
    ys = [r["macs"] for r in rows]
    ymax = max(max(ys), kv_row["macs"]) * 1.05 or 1.0

    def px(x): return X0 + (x - xs[0]) / (xs[-1] - xs[0]) * (X1 - X0)
    def py(y): return Y1 - y / ymax * (Y1 - Y0)

    line = " ".join(f"{px(r['step']):.1f},{py(r['macs']):.1f}" for r in rows)
    pts = [f'<circle cx="{px(r["step"]):.1f}" cy="{py(r["macs"]):.1f}" r="3.5" fill="#922b21"/>'
           for r in rows]
    kv_y = py(kv_row["macs"])
    ticks = [f'<text x="{px(r["step"]):.1f}" y="{Y0 + 16}" text-anchor="middle" font-size="11" fill="#666">{r["step"]}</text>'
             for r in rows]
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 400" width="960" height="400" font-family="Menlo,Consolas,monospace">
<rect width="960" height="400" fill="#ffffff"/>
<text x="480" y="34" text-anchor="middle" font-size="18" font-weight="bold" fill="#111">Per-token tile-MVM ledger through a full layer</text>
<text x="480" y="56" text-anchor="middle" font-size="12" fill="#7f8c8d">MACs per generated token: no KV cache grows with context; KV cache stays constant</text>
<line x1="{X0}" y1="{Y0}" x2="{X1}" y2="{Y0}" stroke="#333" stroke-width="1.5"/>
<line x1="{X0}" y1="{Y0}" x2="{X0}" y2="{Y1}" stroke="#333" stroke-width="1.5"/>
{chr(10).join(ticks)}
<polyline points="{line}" fill="none" stroke="#922b21" stroke-width="2.5"/>
{chr(10).join(pts)}
<line x1="{X0}" y1="{kv_y}" x2="{X1}" y2="{kv_y}" stroke="#1a5276" stroke-width="2" stroke-dasharray="6 5"/>
<rect x="150" y="330" width="12" height="12" fill="#922b21"/><text x="168" y="341" font-size="12" fill="#333">no KV cache (full-context forward)</text>
<rect x="150" y="356" width="12" height="12" fill="#1a5276"/><text x="168" y="367" font-size="12" fill="#333">with KV cache (single-position forward)</text>
</svg>"""
    with open(path, "w") as fh:
        fh.write(svg)


def main() -> None:
    cfg = TinyGPTConfig(vocab_size=128, n_embd=64, n_layer=2, n_head=4,
                        block_size=16, ffn_mult=4, seed=0)
    model = TinyGPT(cfg)
    acc = build_acc()
    prompt = np.array([3, 9, 14, 22])
    max_new = 5
    assert prompt.size + max_new <= cfg.block_size

    out = list(prompt.tolist())
    rows = []
    for s in range(max_new):
        # full-context forward for this generated token
        r = trace_full_forward(model, out, prompt.size + s - 1, acc)
        rows.append({"step": s, **r})
        # next token = argmax from a forward, to keep the context coherent
        ctx = np.asarray(out, dtype=np.int64)[-cfg.block_size:]
        logits = model.forward_logits(ctx, accelerator=acc)
        nxt = int(np.argmax(logits[-1]))
        out.append(nxt)

    kv_row = trace_single_position(model, out[-1], acc)

    print("=" * 70)
    print("B6 — per-token ledger trace through a full layer")
    print("=" * 70)
    print(f"model: {cfg.n_layer}L {cfg.n_embd}D {cfg.n_head}H; tile {TILE_ROWS}x{TILE_COLS} x{TILE_COUNT}")
    print("latency est. = cycles*1.0 tu + programs*0.2 tu (assumptions, not measured)")
    print(f"{'token':<7}{'ctx':<7}{'MACs':>10}{'cycles':>9}{'rewrites':>10}{'latency(tu)':>13}")
    for i, r in enumerate(rows):
        ctx_len = prompt.size + i
        rows[i]["latency"] = latency_est(r)
        print(f"{i:<7}{ctx_len:<7}{r['macs']:>10}{r['cycles']:>9}"
              f"{r['rewrites']:>10}{r['latency']:>13.3f}")
    kv_row["latency"] = latency_est(kv_row)
    print("-" * 70)
    print(f"KV-cache single-position forward  : MACs={kv_row['macs']} "
          f"cycles={kv_row['cycles']} rewrites={kv_row['rewrites']} "
          f"latency={kv_row['latency']:.3f} tu")
    print(f"0th authentic token full-forward  : MACs={rows[0]['macs']} "
          f"cycles={rows[0]['cycles']} rewrites={rows[0]['rewrites']} "
          f"latency={rows[0]['latency']:.3f} tu")
    last = rows[-1]
    print("-" * 70)
    print(f"last-token MACs, no KV vs KV: {last['macs']} vs {kv_row['macs']} "
          f"({last['macs'] / kv_row['macs']:.1f}x at ctx {prompt.size + max_new - 1}); "
          f"latency {last['latency']:.1f} vs {kv_row['latency']:.1f} tu")

    # guardrails: per-token no-KV MACs grow with context; KV is constant & lower
    assert all(rows[i + 1]["macs"] > rows[i]["macs"] for i in range(len(rows) - 1)), \
        "no-KV per-token MACs must grow with context length"
    assert kv_row["macs"] <= rows[0]["macs"], "KV single-position must not exceed first full forward"
    assert rows[0]["cycles"] <= rows[-1]["cycles"], "cycles grow with context"

    make_svg(rows, kv_row, "scripts/token_trace.svg")
    print("\nwrote scripts/token_trace.svg")


if __name__ == "__main__":
    main()
