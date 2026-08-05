"""M6 — system latency / energy estimate and sensitivity (measured-input model).

Builds a system-level latency/energy *formula* from the physical ledger and
parameters the designer supplies. All timing/energy parameters are ASSUMPTIONS
(units are relative "tu" time units / "eu" energy units), and there is NO GPU
comparison and no claim that NumPy is physics.

Two studies:
  1. latency + converter/program accounting for one real forward, reported with
     the assumption parameters shown;
  2. sensitivity of the latency estimate to on-board tile parallelism
     (tile_count) and to tile capacity (rows x cols).

Every number is a model estimate whose inputs are stated; energy is only shown
because per-op energies were supplied as assumptions.
"""

import numpy as np

from analog_llm import Accelerator, CrossbarTile, Metrics, TinyGPT, TinyGPTConfig
from analog_llm.latency import PhysicsAssumptions, format_system, system_analysis

# design-supplied assumptions (RELATIVE units, not measured silicon)
ASSUMPTIONS = PhysicsAssumptions(
    mvm_cycle_time=1.0,   # tu per tile MVM cycle
    program_time=0.2,     # tu per tile program
    dac_energy=0.01, adc_energy=0.02, mac_energy=0.001, program_energy=0.1,
)


def build_acc(tile_rows, tile_cols, tile_count, **kw) -> Accelerator:
    def factory() -> CrossbarTile:
        return CrossbarTile(tile_rows, tile_cols, g_bits=14, dac_bits=16,
                            adc_bits=16, vout_max=96.0, **kw)
    return Accelerator(factory, tile_rows, tile_cols, tile_count)


def run_workload(tile_rows, tile_cols, tile_count):
    cfg = TinyGPTConfig(vocab_size=64, n_embd=48, n_layer=1, n_head=4,
                        block_size=8, seed=0)
    model = TinyGPT(cfg)
    acc = build_acc(tile_rows, tile_cols, tile_count)
    model.forward_logits(np.arange(1, 5), accelerator=acc)
    m = Metrics()
    m.update(acc)
    return m


def make_sensitivity_svg(rows, path) -> None:
    X0, X1, Y0, Y1 = 150.0, 870.0, 80.0, 480.0
    xs = [r["tile_count"] for r in rows]
    ys = [r["latency"] for r in rows]
    lo, hi = min(xs), max(xs)

    def px(x): return X0 + (x - lo) / (hi - lo) * (X1 - X0)
    def py(y): return Y1 - (y - 0.0) / (max(ys)) * (Y1 - Y0)

    pts = " ".join(f"{px(r['tile_count']):.1f},{py(r['latency']):.1f}" for r in rows)
    ticks = [f'<text x="{px(x)}" y="{Y0 + 16}" text-anchor="middle" font-size="11" fill="#666">{x}</text>'
             for x in xs]
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540" width="960" height="540" font-family="Menlo,Consolas,monospace">
<rect width="960" height="540" fill="#ffffff"/>
<text x="480" y="30" text-anchor="middle" font-size="18" font-weight="bold" fill="#111">Sensitivity: latency est. vs on-board tile parallelism</text>
<text x="480" y="52" text-anchor="middle" font-size="12" fill="#7f8c8d">relative time units; more tiles cut MVM cycles but add converters (no energy/GPU claim)</text>
<line x1="{X0}" y1="{Y0}" x2="{X1}" y2="{Y0}" stroke="#333" stroke-width="1.5"/>
<line x1="{X0}" y1="{Y0}" x2="{X0}" y2="{Y1}" stroke="#333" stroke-width="1.5"/>
{chr(10).join(ticks)}
<polyline points="{pts}" fill="none" stroke="#1a5276" stroke-width="3"/>
<text x="{X0}" y="{Y1 + 34}" font-size="12" fill="#333">tile_count on board (fixed 48x48 tile)</text>
</svg>"""
    with open(path, "w") as fh:
        fh.write(svg)


def main() -> None:
    tile_rows = tile_cols = 48
    m = run_workload(tile_rows, tile_cols, tile_count=2)
    a = system_analysis(m, tile_rows, tile_cols, 2, ASSUMPTIONS)

    print("=" * 70)
    print("M6 — system estimate + sensitivity")
    print("=" * 70)
    print("workload: 1 forward through a 1L/48D GPT-style model, tile 48x48 x2")
    print(f"ledger: macs={m.macs} cycles={m.cycles} programs={m.programs} "
          f"rewrites={m.rewrites}")
    print("-" * 70)
    print(format_system(a, ASSUMPTIONS))

    print("-" * 70)
    print("Sensitivity: latency est. vs tile_count (48x48 tile, fixed workload)")
    print(f"{'tile_count':<12}{'cycles':<9}{'programs':<10}{'converters':<12}{'latency(tu)':>12}")
    rows = []
    for tc in (1, 2, 4, 8, 16):
        mm = run_workload(tile_rows, tile_cols, tile_count=tc)
        b = system_analysis(mm, tile_rows, tile_cols, tc, ASSUMPTIONS)
        rows.append({"tile_count": tc, **b})
        print(f"{tc:<12}{int(b['mvm_cycles']):<9}{int(b['programs']):<10}"
              f"{int(b['converters']):<12}{b['latency']:>12.3f}")

    # guardrails
    cyc = [r["mvm_cycles"] for r in rows]
    prog = [r["programs"] for r in rows]
    lat = [r["latency"] for r in rows]
    assert all(cyc[i + 1] <= cyc[i] for i in range(len(cyc) - 1)), "more tiles -> fewer cycles"
    assert all(abs(p - prog[0]) < 1e-6 for p in prog), "programs independent of tile_count"
    assert lat[-1] < lat[0], "latency falls with parallelism until converters dominate"

    # tile capacity study
    print("-" * 70)
    print("Sensitivity: latency est. vs tile capacity (fixed tile_count=2)")
    print(f"{'tile size':<12}{'cycles':<9}{'programs':<10}{'macs':<9}{'latency(tu)':>12}")
    for size in (16, 32, 48, 64):
        mm = run_workload(size, size, tile_count=2)
        b = system_analysis(mm, size, size, 2, ASSUMPTIONS)
        print(f"{size:<12}{int(b['mvm_cycles']):<9}{int(b['programs']):<10}"
              f"{int(mm.macs):<9}{b['latency']:>12.3f}")

    make_sensitivity_svg(rows, "scripts/latency_sensitivity.svg")
    print("\nwrote scripts/latency_sensitivity.svg")


if __name__ == "__main__":
    main()
