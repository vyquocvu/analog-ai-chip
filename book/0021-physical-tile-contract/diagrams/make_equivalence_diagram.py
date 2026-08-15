"""Generate the deterministic R5 small-array SPICE-equivalence diagram."""

from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_EXTRACT = _ROOT / "verification" / "circuit" / "results" / "physical-tile-0021-extract.json"
_OUTPUT = Path(__file__).with_name("physical_tile_spice_equivalence.svg")

WIDTH = 960
HEIGHT = 540
PLOT_X = 565
PLOT_Y = 125
PLOT_WIDTH = 330
PLOT_HEIGHT = 280


def _x(error_v: float, budget_v: float) -> float:
    return PLOT_X + error_v / budget_v * PLOT_WIDTH


data = json.loads(_EXTRACT.read_text("utf-8"))
equivalence = data["small_array_spice_equivalence"]
budget_v = equivalence["frozen_budget"]["value"]
rows = [
    ("2×2", equivalence["arrays"]["2x2"]["max_abs_error_v"], "#2563eb"),
    ("4×4", equivalence["arrays"]["4x4"]["max_abs_error_v"], "#0f766e"),
    ("All", equivalence["max_abs_error_v"], "#7c3aed"),
]

elements: list[str] = []
for index, (label, error_v, color) in enumerate(rows):
    y = PLOT_Y + 65 + index * 72
    width = _x(error_v, budget_v) - PLOT_X
    elements.append(
        f'<text x="{PLOT_X - 15}" y="{y + 18}" text-anchor="end" class="label">{label}</text>'
    )
    elements.append(
        f'<rect x="{PLOT_X}" y="{y}" width="{width:.1f}" height="28" rx="4" fill="{color}"/>'
    )
    elements.append(
        f'<text x="{PLOT_X + width - 7:.1f}" y="{y + 19}" text-anchor="end" class="bar-value">{error_v:.6f} V</text>'
    )

for fraction in (0.0, 0.25, 0.5, 0.75, 1.0):
    value = fraction * budget_v
    x = _x(value, budget_v)
    elements.append(
        f'<line x1="{x:.1f}" y1="{PLOT_Y + 40}" x2="{x:.1f}" y2="{PLOT_Y + PLOT_HEIGHT}" class="grid"/>'
    )
    elements.append(
        f'<text x="{x:.1f}" y="{PLOT_Y + PLOT_HEIGHT + 22}" text-anchor="middle" class="tick">{value:.3f}</text>'
    )

budget_x = _x(budget_v, budget_v)
elements.append(
    f'<line x1="{budget_x:.1f}" y1="{PLOT_Y + 35}" x2="{budget_x:.1f}" y2="{PLOT_Y + PLOT_HEIGHT}" class="budget"/>'
)
elements.append(
    f'<text x="{budget_x:.1f}" y="{PLOT_Y + 22}" text-anchor="end" class="budget-label">ADC budget = {budget_v:.5f} V</text>'
)

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}">
<style>
  text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: #0f172a; }}
  .title {{ font-size: 22px; font-weight: 700; }}
  .subtitle {{ font-size: 13px; fill: #475569; }}
  .box-title {{ font-size: 14px; font-weight: 700; }}
  .box-text {{ font-size: 12px; fill: #334155; }}
  .formula {{ font-size: 13px; font-family: ui-monospace, SFMono-Regular, monospace; }}
  .arrow {{ stroke: #64748b; stroke-width: 2; fill: none; marker-end: url(#arrow); }}
  .label {{ font-size: 13px; font-weight: 700; }}
  .bar-value {{ font-size: 11px; font-weight: 700; fill: white; }}
  .grid {{ stroke: #cbd5e1; stroke-width: 1; stroke-dasharray: 4 4; }}
  .tick {{ font-size: 10px; fill: #64748b; }}
  .budget {{ stroke: #dc2626; stroke-width: 3; }}
  .budget-label {{ font-size: 12px; font-weight: 700; fill: #b91c1c; }}
</style>
<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#64748b"/></marker></defs>
<rect width="{WIDTH}" height="{HEIGHT}" fill="#ffffff"/>
<text x="480" y="38" text-anchor="middle" class="title">R5 Physical Tile ↔ Small-Array SPICE Equivalence</text>
<text x="480" y="62" text-anchor="middle" class="subtitle">Committed 0012/0013 SPICE outputs compared with the 4-bit three-profile CrossbarTile</text>
<rect x="55" y="115" width="185" height="95" rx="10" fill="#eff6ff" stroke="#2563eb"/>
<text x="147" y="143" text-anchor="middle" class="box-title">SPICE evidence</text>
<text x="147" y="167" text-anchor="middle" class="box-text">2×2: 5 cases</text>
<text x="147" y="188" text-anchor="middle" class="box-text">4×4: 5 cases</text>
<path d="M240 162 H300" class="arrow"/>
<rect x="305" y="105" width="195" height="115" rx="10" fill="#ecfdf5" stroke="#0f766e"/>
<text x="402" y="133" text-anchor="middle" class="box-title">Profile-driven tile</text>
<text x="402" y="157" text-anchor="middle" class="box-text">crossbar-v1</text>
<text x="402" y="178" text-anchor="middle" class="box-text">dac-r2r-v1 + adc-sar-v1</text>
<text x="402" y="199" text-anchor="middle" class="box-text">G/DAC/ADC = 4 bits</text>
<rect x="55" y="270" width="445" height="135" rx="10" fill="#f8fafc" stroke="#64748b"/>
<text x="75" y="300" class="box-title">Frozen acceptance formula</text>
<text x="75" y="329" class="formula">e_c = max_j |V_tile[c,j] − V_spice[c,j]|</text>
<text x="75" y="355" class="formula">E_max = max_c e_c</text>
<text x="75" y="381" class="formula">PASS ⇔ E_max ≤ adc.quantization_error_v</text>
<text x="{PLOT_X + PLOT_WIDTH / 2}" y="105" text-anchor="middle" class="box-title">Maximum absolute voltage residual</text>
{"".join(elements)}
<text x="{PLOT_X + PLOT_WIDTH / 2}" y="{PLOT_Y + PLOT_HEIGHT + 47}" text-anchor="middle" class="subtitle">Error (V); red line is the frozen profile-derived threshold</text>
<rect x="55" y="450" width="840" height="55" rx="8" fill="#fff7ed" stroke="#ea580c"/>
<text x="475" y="474" text-anchor="middle" class="box-text">SYSTEM_SIMULATED regression only: crossbar-v1 assumed parameters and unconsumed IR-drop/variation/drift/fault/I-V fields</text>
<text x="475" y="493" text-anchor="middle" class="box-text">prevent promotion to a verified physical-tile claim.</text>
</svg>
'''

_OUTPUT.write_text(svg, "utf-8")
print(f"Generated physical-tile SPICE equivalence SVG: {_OUTPUT}")
