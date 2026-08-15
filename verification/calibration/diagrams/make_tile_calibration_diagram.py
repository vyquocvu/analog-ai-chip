"""Generate the deterministic profile-driven tile calibration diagram."""

from __future__ import annotations

import json
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_RESULT = _REPO / "verification" / "calibration" / "results" / "tile-calibration-v1-extract.json"
_OUTPUT = Path(__file__).with_name("tile-calibration-v1.svg")

data = json.loads(_RESULT.read_text("utf-8"))
cal = data["calibration"]

raw_rms = cal["raw_rms_error_v"]
cal_rms = cal["calibrated_rms_error_v"]
raw_max = cal["raw_max_abs_error_v"]
cal_max = cal["calibrated_max_abs_error_v"]
budget = cal["frozen_budget_v"]
gain = cal["correction_gain"]

bar_x = 610
bar_width = 280


def width(value: float) -> float:
    return value / budget * bar_width


svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 570" width="960" height="570">
<style>
  text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: #0f172a; }}
  .title {{ font-size: 22px; font-weight: 700; }}
  .subtitle {{ font-size: 13px; fill: #475569; }}
  .box-title {{ font-size: 14px; font-weight: 700; }}
  .box-text {{ font-size: 12px; fill: #334155; }}
  .formula {{ font-size: 12px; font-family: ui-monospace, SFMono-Regular, monospace; }}
  .arrow {{ stroke: #64748b; stroke-width: 2; fill: none; marker-end: url(#arrow); }}
  .metric {{ font-size: 12px; font-weight: 700; }}
  .value {{ font-size: 11px; font-weight: 700; fill: white; }}
  .budget {{ stroke: #dc2626; stroke-width: 3; stroke-dasharray: 5 4; }}
</style>
<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#64748b"/></marker></defs>
<rect width="960" height="570" fill="#ffffff"/>
<text x="480" y="38" text-anchor="middle" class="title">R5 Profile-Driven Tile Calibration</text>
<text x="480" y="62" text-anchor="middle" class="subtitle">Zero-preserving constrained gain fit over 30 committed 2×2/4×4 SPICE outputs</text>
<rect x="45" y="105" width="180" height="92" rx="10" fill="#eff6ff" stroke="#2563eb"/>
<text x="135" y="134" text-anchor="middle" class="box-title">Raw evidence</text>
<text x="135" y="158" text-anchor="middle" class="box-text">Profile-driven tile</text>
<text x="135" y="179" text-anchor="middle" class="box-text">↔ SPICE outputs</text>
<path d="M225 151 H275" class="arrow"/>
<rect x="280" y="95" width="250" height="112" rx="10" fill="#f5f3ff" stroke="#7c3aed"/>
<text x="405" y="124" text-anchor="middle" class="box-title">Calibration extraction</text>
<text x="405" y="149" text-anchor="middle" class="formula">a_ls = Σ(y_raw y_spice) / Σ(y_raw²)</text>
<text x="405" y="172" text-anchor="middle" class="formula">a* = clip(a_ls, [a_min, a_max])</text>
<text x="405" y="193" text-anchor="middle" class="box-text">max error may not degrade</text>
<path d="M530 151 H580" class="arrow"/>
<rect x="585" y="105" width="195" height="92" rx="10" fill="#ecfdf5" stroke="#0f766e"/>
<text x="682" y="134" text-anchor="middle" class="box-title">Calibration profile</text>
<text x="682" y="158" text-anchor="middle" class="box-text">tile-calibration-v1</text>
<text x="682" y="179" text-anchor="middle" class="formula">gain = {gain:.9f}</text>
<path d="M780 151 H825" class="arrow"/>
<rect x="830" y="115" width="85" height="72" rx="10" fill="#fff7ed" stroke="#ea580c"/>
<text x="872" y="143" text-anchor="middle" class="box-title">Apply</text>
<text x="872" y="166" text-anchor="middle" class="formula">y=a*y</text>
<rect x="45" y="245" width="500" height="190" rx="10" fill="#f8fafc" stroke="#64748b"/>
<text x="65" y="275" class="box-title">Acceptance formulas</text>
<text x="65" y="308" class="formula">E_constraint = min(E_raw,max, E_ADC,budget)</text>
<text x="65" y="338" class="formula">[a_min,a_max] = ∩ᵢ &#123;a : |a y_raw,i − y_SPICE,i| ≤ E_constraint&#125;</text>
<text x="65" y="368" class="formula">y_cal = a* y_raw</text>
<text x="65" y="398" class="formula">PASS ⇔ RMS_cal &lt; RMS_raw ∧ E_cal,max ≤ E_raw,max</text>
<text x="65" y="421" class="box-text">Offset = 0 V preserves balanced-zero differential cancellation.</text>
<text x="{bar_x}" y="267" class="box-title">Error evidence (V)</text>
<line x1="{bar_x + bar_width}" y1="280" x2="{bar_x + bar_width}" y2="430" class="budget"/>
<text x="{bar_x + bar_width}" y="267" text-anchor="end" class="metric" fill="#b91c1c">ADC budget {budget:.6f}</text>
<text x="{bar_x - 12}" y="312" text-anchor="end" class="metric">Raw RMS</text>
<rect x="{bar_x}" y="292" width="{width(raw_rms):.1f}" height="27" rx="4" fill="#64748b"/>
<text x="{bar_x + width(raw_rms) - 7:.1f}" y="310" text-anchor="end" class="value">{raw_rms:.6f}</text>
<text x="{bar_x - 12}" y="352" text-anchor="end" class="metric">Cal RMS</text>
<rect x="{bar_x}" y="332" width="{width(cal_rms):.1f}" height="27" rx="4" fill="#0f766e"/>
<text x="{bar_x + width(cal_rms) - 7:.1f}" y="350" text-anchor="end" class="value">{cal_rms:.6f}</text>
<text x="{bar_x - 12}" y="392" text-anchor="end" class="metric">Raw max</text>
<rect x="{bar_x}" y="372" width="{width(raw_max):.1f}" height="27" rx="4" fill="#64748b"/>
<text x="{bar_x + width(raw_max) - 7:.1f}" y="390" text-anchor="end" class="value">{raw_max:.6f}</text>
<text x="{bar_x - 12}" y="432" text-anchor="end" class="metric">Cal max</text>
<rect x="{bar_x}" y="412" width="{width(cal_max):.1f}" height="27" rx="4" fill="#0f766e"/>
<text x="{bar_x + width(cal_max) - 7:.1f}" y="430" text-anchor="end" class="value">{cal_max:.6f}</text>
<rect x="45" y="475" width="870" height="58" rx="8" fill="#fff7ed" stroke="#ea580c"/>
<text x="480" y="499" text-anchor="middle" class="box-text">SYSTEM_SIMULATED: RMS improves {cal["rms_improvement_pct"]:.2f}% and maximum error does not degrade.</text>
<text x="480" y="519" text-anchor="middle" class="box-text">Same-sample fit/evaluation; no held-out corners or hardware measurements, so physical claims fail closed.</text>
</svg>
'''

_OUTPUT.write_text(svg, "utf-8")
print(f"Generated tile calibration SVG: {_OUTPUT}")
