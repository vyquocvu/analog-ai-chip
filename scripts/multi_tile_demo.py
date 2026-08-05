"""B3 — multi-tile demo: a matrix larger than one physical tile.

Runs a dense matrix-vector multiply through ``analog_llm.Accelerator`` where
the logical matrix is larger than one ``tile_rows x tile_cols`` crossbar, so
the matrix must be split into multiple physical tile blocks and the block
results accumulated digitally (partial sums). This closes ROADMAP M2's
"report a matrix larger than one physical tile" item.

Two scenarios show the physical ledger for the SAME matrix:
  1. **parallel**  - enough tiles on board (tile_count == #blocks): all blocks
                      run together, rewrites == 0, tile_cycles == 1.
  2. **temporal reuse** - fewer tiles than blocks (tile_count < #blocks): tiles
                      are re-programmed and reused, rewrites > 0 and
                      tile_cycles grow.

Ledger (PERSPECTIVE: simulation metrics, not wall-clock or energy):
  - macs        : resolved differential cells executed (== logical cells)
  - tile_cycles : lower bound on sequential block-MVM cycles
  - rewrites    : how many times a physical tile had to be reprogrammed
  - tiles_used  : physical tile instances on board

Every scenario is checked against the dense float reference within a small
tolerance (validates correct tiling + partial sums, not a fabrication claim).
"""

import numpy as np

from analog_llm import Accelerator, CrossbarTile

TILE_ROWS, TILE_COLS = 8, 8
MATRIX_ROWS, MATRIX_COLS = 24, 16  # larger than one 8x8 tile -> 3x2 = 6 blocks


def build_acc(tile_count: int, seed: int = 0) -> Accelerator:
    def factory() -> CrossbarTile:
        return CrossbarTile(
            TILE_ROWS, TILE_COLS,
            g_bits=14, dac_bits=16, adc_bits=16, vout_max=16.0,
            rng=np.random.default_rng(seed),
        )
    return Accelerator(factory, TILE_ROWS, TILE_COLS, tile_count)


def run_scenario(matrix: np.ndarray, vector: np.ndarray, tile_count: int) -> tuple[np.ndarray, dict]:
    acc = build_acc(tile_count)
    out = acc.mvm(matrix, vector)
    ledger = {
        "tile_count": acc.tile_count,
        "macs": acc.macs,
        "tile_cycles": acc.tile_cycles,
        "rewrites": acc.rewrites,
    }
    return out, ledger


def make_layout_svg(matrix_rows: int, matrix_cols: int, tr: int, tc: int, path: str) -> None:
    """Draw the logical matrix partitioned into tile-size blocks with IDs."""
    blocks_rows = (matrix_rows + tr - 1) // tr
    blocks_cols = (matrix_cols + tc - 1) // tc
    m = blocks_rows * blocks_cols

    # layout: tile a grid of (blocks_cols) wide x (blocks_rows) tall cells
    cell = 40
    gap = 34
    X0, Y0 = 150.0, 100.0
    W = blocks_cols * cell + (blocks_cols - 1) * gap
    H = blocks_rows * cell + (blocks_rows - 1) * gap

    def center(br: int, bc: int):
        x = X0 + bc * (cell + gap) + cell / 2
        y = Y0 + br * (cell + gap) + cell / 2
        return x, y

    tiles_svg = []
    for br in range(blocks_rows):
        for bc in range(blocks_cols):
            x = X0 + bc * (cell + gap)
            y = Y0 + br * (cell + gap)
            blk = br * blocks_cols + bc
            tiles_svg.append(
                f'<g><rect x="{x}" y="{y}" width="{cell}" height="{cell}" '
                f'fill="#eaf2f8" stroke="#1a5276" stroke-width="2" rx="4"/>'
                f'<text x="{x + cell / 2}" y="{y + cell / 2 - 4}" text-anchor="middle" '
                f'font-size="11" fill="#1a5276">block {blk}</text>'
                f'<text x="{x + cell / 2}" y="{y + cell / 2 + 12}" text-anchor="middle" '
                f'font-size="10" fill="#666">tile ({br},{bc})</text></g>'
            )
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 {Y0 + H + 160}" width="960" height="{Y0 + H + 160}" font-family="Menlo,Consolas,monospace">
<rect width="960" height="{Y0 + H + 160}" fill="#ffffff"/>
<text x="480" y="34" text-anchor="middle" font-size="18" font-weight="bold" fill="#111">Multi-tile mapping: {matrix_rows}x{matrix_cols} matrix over {tr}x{tc} tiles</text>
<text x="480" y="56" text-anchor="middle" font-size="12" fill="#7f8c8d">{blocks_rows} x {blocks_cols} blocks ({m} total); groups of (rows, cols) blocks accumulate partial sums digitally</text>
<line x1="{X0 - 8}" y1="{Y0}" x2="{X0 - 8}" y2="{Y0 + H}" stroke="#333" stroke-width="1.5"/>
<line x1="{X0 - 8}" y1="{Y0 + H}" x2="{X0 + W}" y2="{Y0 + H}" stroke="#333" stroke-width="1.5"/>
{chr(10).join(tiles_svg)}
<text x="{X0 + W / 2}" y="{Y0 + H + 30}" text-anchor="middle" font-size="13" fill="#333">partitions: rows into {blocks_rows} groups, columns into {blocks_cols} groups</text>
<text x="{X0 + W / 2}" y="{Y0 + H + 52}" text-anchor="middle" font-size="12" fill="#7f8c8d">physical ledger: macs = cells = {matrix_rows * matrix_cols};  cycles & rewrites depend on tile_count</text>
</svg>"""
    with open(path, "w") as fh:
        fh.write(svg)


def main() -> None:
    rng = np.random.default_rng(0)
    matrix = rng.normal(size=(MATRIX_ROWS, MATRIX_COLS))
    vector = rng.normal(size=MATRIX_COLS)
    dense = matrix @ vector
    blocks_rows = (MATRIX_ROWS + TILE_ROWS - 1) // TILE_ROWS
    blocks_cols = (MATRIX_COLS + TILE_COLS - 1) // TILE_COLS
    n_blocks = blocks_rows * blocks_cols

    parallel = n_blocks           # enough tiles on board
    constrained = 2               # temporal reuse

    out_p, ledger_p = run_scenario(matrix, vector, parallel)
    out_c, ledger_c = run_scenario(matrix, vector, constrained)

    print("=" * 68)
    print("B3 — multi-tile demo: a matrix larger than one physical tile")
    print("=" * 68)
    print(f"logical matrix  : {MATRIX_ROWS}x{MATRIX_COLS}  (tile {TILE_ROWS}x{TILE_COLS})")
    print(f"blocks          : {blocks_rows}x{blocks_cols} = {n_blocks}")
    print("-" * 68)
    print(f"{'ledger':<14}{'parallel':>14}{'temporal reuse':>16}")
    for k in ("tile_count", "macs", "tile_cycles", "rewrites"):
        print(f"{k:<14}{ledger_p[k]:>14}{ledger_c[k]:>16}")
    print("-" * 68)
    print(f"max |err| vs dense (parallel)        : {np.max(np.abs(out_p - dense)):.2e}")
    print(f"max |err| vs dense (temporal reuse)  : {np.max(np.abs(out_c - dense)):.2e}")

    np.testing.assert_allclose(out_p, dense, atol=0.02, err_msg="parallel multi-tile must match dense")
    np.testing.assert_allclose(out_c, dense, atol=0.02, err_msg="temporal-reuse multi-tile must match dense")

    assert ledger_p["macs"] == MATRIX_ROWS * MATRIX_COLS, "MACs == logical cells"
    assert ledger_p["tile_cycles"] == 1, "parallel: all blocks in one cycle"
    assert ledger_p["rewrites"] == 0, "parallel: no rewrites"
    assert ledger_c["rewrites"] == n_blocks - constrained, "reuse: rewrites == blocks - tile_count"
    assert ledger_c["tile_cycles"] == int(np.ceil(n_blocks / constrained)), "reuse cycles"
    assert ledger_c["macs"] == ledger_p["macs"], "same work, independent of tile_count"

    make_layout_svg(MATRIX_ROWS, MATRIX_COLS, TILE_ROWS, TILE_COLS, "scripts/multi_tile_layout.svg")
    print("\nwrote scripts/multi_tile_layout.svg")


if __name__ == "__main__":
    main()
