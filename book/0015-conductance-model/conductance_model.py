r"""Chapter 0015 — Programmable Conductance Compact Model (SPICE / Analytical).

The first chapter of Gate R4 (Device Realism). Replaces the ideal continuous
resistors with a realistic non-volatile memory (NVM / ReRAM / PCM / 1T1R)
compact model:

Physical properties modeled:
----------------------------
1. **Finite Conductance Dynamic Range**:
   Conductance is bounded between a high-resistance state (HRS / $G_{min}$)
   and a low-resistance state (LRS / $G_{max}$):
       G_{min} = 10.0 uS (100 kOhm)
       G_{max} = 100.0 uS (10 kOhm)
       Dynamic range = G_{max} / G_{min} = 10x

2. **Finite State Discretization**:
   Pulse-and-verify programming produces $K = 2^B$ discrete conductance levels:
       G_k = G_{min} + \frac{k}{2^B - 1} (G_{max} - G_{min}), \quad k \in \{0, \dots, 2^B - 1\}
   For 4-bit cells: 16 states, step = 6.0 uS (6.67% of full-scale).
   For 6-bit cells: 64 states, step = 1.428 uS (1.58% of full-scale).

3. **Read Voltage Limits & Linearity Envelope**:
   To prevent state disturb or switching during inference, read voltage $|V_{read}|$
   must satisfy $|V_{read}| \le V_{read,max} = 0.25 V$. Within this envelope,
   the cell exhibits ohmic I-V behavior ($I = V \cdot G$).

4. **Differential Signed Weight Resolution**:
   Signed weights $w \in [-1, 1]$ are stored on a physical $(G^+, G^-)$ cell pair:
       w_{eff} = \frac{G^+ - G^-}{G_{max} - G_{min}}
   A weight of zero maps to balanced $G^+ = G^- = G_{min}$ ($w_{eff} = 0$).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

if "NGSPICE_LIBRARY_PATH" not in os.environ:
    for path in (
        "/opt/homebrew/lib/libngspice.dylib",
        "/usr/local/lib/libngspice.dylib",
        "/usr/lib/x86_64-linux-gnu/libngspice.so",
    ):
        if os.path.exists(path):
            os.environ["NGSPICE_LIBRARY_PATH"] = path
            break

try:
    from PySpice.Spice.Netlist import Circuit
    from PySpice.Unit import u_kOhm, u_V

    _PYSPICE_OK = True
except ImportError:  # pragma: no cover - engine-free environment
    _PYSPICE_OK = False


def _require_pyspice() -> None:
    if not _PYSPICE_OK:
        raise ImportError(
            "PySpice is required for SPICE solves; "
            "install with `pip install -e '.[sim]'`"
        )


G_MIN_S = 10.0e-6        # HRS conductance = 10 uS (100 kOhm)
G_MAX_S = 100.0e-6       # LRS conductance = 100 uS (10 kOhm)
V_READ_MAX_V = 0.25      # maximum non-disturb read voltage (V)
DEFAULT_BITS = 4         # default prototype state resolution (16 levels)


@dataclass(frozen=True)
class ConductanceCellModel:
    """Compact model parameters for a programmable NVM conductance cell."""

    g_min: float = G_MIN_S
    g_max: float = G_MAX_S
    v_read_max: float = V_READ_MAX_V
    bits: int = DEFAULT_BITS

    def __post_init__(self) -> None:
        if self.g_min <= 0 or self.g_max <= self.g_min:
            raise ValueError("requires 0 < g_min < g_max")
        if self.v_read_max <= 0:
            raise ValueError("v_read_max must be positive")
        if self.bits < 1:
            raise ValueError("bits must be >= 1")

    @property
    def span(self) -> float:
        return self.g_max - self.g_min

    @property
    def num_states(self) -> int:
        return 2**self.bits

    @property
    def conductance_levels(self) -> np.ndarray:
        return np.linspace(self.g_min, self.g_max, self.num_states)

    def quantize_conductance(self, g_target: float) -> tuple[int, float]:
        """Quantize continuous conductance to closest discrete programmed level."""
        g_clamped = np.clip(g_target, self.g_min, self.g_max)
        idx = int(np.rint((g_clamped - self.g_min) / self.span * (self.num_states - 1)))
        idx = max(0, min(self.num_states - 1, idx))
        return idx, float(self.conductance_levels[idx])

    def map_signed_weight(self, w: float) -> tuple[float, float, float, int, int]:
        """Map signed weight w in [-1, 1] to (G+, G-, w_eff, state_p, state_m)."""
        w_clamped = float(np.clip(w, -1.0, 1.0))
        if w_clamped >= 0:
            target_p = self.g_min + w_clamped * self.span
            idx_p, g_p = self.quantize_conductance(target_p)
            idx_m, g_m = 0, self.g_min
        else:
            target_m = self.g_min + abs(w_clamped) * self.span
            idx_p, g_p = 0, self.g_min
            idx_m, g_m = self.quantize_conductance(target_m)

        w_eff = (g_p - g_m) / self.span
        return g_p, g_m, w_eff, idx_p, idx_m


def spice_cell_iv(g_val: float, v_sweep: list[float]) -> list[float]:
    """Solve DC OP for a single cell across read voltages v_sweep in SPICE."""
    _require_pyspice()
    currents = []
    for v in v_sweep:
        c = Circuit("cell_iv")
        c.V("in", "top", c.gnd, v @ u_V)
        r_kohm = (1.0 / g_val / 1e3) @ u_kOhm
        c.R("cell", "top", c.gnd, r_kohm)
        sim = c.simulator()
        res = sim.operating_point()
        v_top = float(np.ravel(np.asarray(res["top"]))[0])
        i_cell = v_top * g_val  # current flowing top -> gnd
        currents.append(i_cell)
    return currents


def run_conductance_model_extract() -> dict[str, Any]:
    """Run characterization sweeps and emit structured extract report."""
    cell_4b = ConductanceCellModel(bits=4)
    cell_6b = ConductanceCellModel(bits=6)

    # 1. State levels table
    states_4b = []
    for k, g in enumerate(cell_4b.conductance_levels):
        states_4b.append({
            "state_index": k,
            "conductance_uS": g * 1e6,
            "resistance_kOhm": 1.0 / (g * 1e3),
            "current_at_vread_uA": g * cell_4b.v_read_max * 1e6,
        })

    # 2. Weight quantization sweep over [-1.0 .. 1.0]
    w_test = np.linspace(-1.0, 1.0, 21)
    weight_mappings = []
    for w in w_test:
        gp, gm, weff, ip, im = cell_4b.map_signed_weight(float(w))
        weight_mappings.append({
            "w_target": float(w),
            "w_effective": float(weff),
            "w_abs_error": abs(float(weff) - float(w)),
            "g_plus_uS": gp * 1e6,
            "g_minus_uS": gm * 1e6,
            "state_plus": ip,
            "state_minus": im,
        })

    # 3. SPICE I-V linearity sweep on 4 representative states
    v_sweep = list(np.linspace(0.0, V_READ_MAX_V, 11))
    iv_curves = {}
    rep_states = [0, 5, 10, 15]
    for st in rep_states:
        g = float(cell_4b.conductance_levels[st])
        if _PYSPICE_OK:
            i_spice = spice_cell_iv(g, v_sweep)
        else:
            i_spice = [v * g for v in v_sweep]
        iv_curves[f"state_{st}"] = {
            "conductance_uS": g * 1e6,
            "voltages_v": v_sweep,
            "currents_uA": [i * 1e6 for i in i_spice],
            "max_linearity_deviation_uA": float(np.max(np.abs(np.array(i_spice) - np.array(v_sweep) * g))) * 1e6,
        }

    extract = {
        "schema_version": "0.1.0",
        "chapter": "0015-conductance-model",
        "title": "Programmable Conductance Compact Model and State Discretization",
        "model_parameters": {
            "g_min_uS": G_MIN_S * 1e6,
            "g_max_uS": G_MAX_S * 1e6,
            "span_uS": (G_MAX_S - G_MIN_S) * 1e6,
            "dynamic_range_ratio": G_MAX_S / G_MIN_S,
            "v_read_max_v": V_READ_MAX_V,
            "bits_4b_step_uS": cell_4b.span / (cell_4b.num_states - 1) * 1e6,
            "bits_6b_step_uS": cell_6b.span / (cell_6b.num_states - 1) * 1e6,
        },
        "states_4bit": states_4b,
        "weight_mappings": weight_mappings,
        "iv_linearity": iv_curves,
        "summary": {
            "max_weight_quantization_error": max(r["w_abs_error"] for r in weight_mappings),
            "max_read_current_uA": G_MAX_S * V_READ_MAX_V * 1e6,
            "min_read_current_uA": G_MIN_S * V_READ_MAX_V * 1e6,
            "evidence_class": "spice" if _PYSPICE_OK else "derived",
            "provenance": "Compact model with deterministic pulse-verify discrete levels",
        },
    }
    return extract


def main() -> None:
    print("Running Chapter 0015 Conductance Compact Model extraction...")
    extract = run_conductance_model_extract()
    out_dir = Path(__file__).resolve().parent.parent.parent / "verification" / "circuit" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "conductance-model-0015-extract.json"
    with open(out_file, "w") as f:
        json.dump(extract, f, indent=2)
    print(f"Committed extract written to {out_file}")
    p = extract["model_parameters"]
    print(f"  G_min={p['g_min_uS']:.1f} uS | G_max={p['g_max_uS']:.1f} uS | Span={p['span_uS']:.1f} uS | Range={p['dynamic_range_ratio']:.1f}x")
    print(f"  4-bit step={p['bits_4b_step_uS']:.3f} uS | 6-bit step={p['bits_6b_step_uS']:.3f} uS")
    print(f"  Max read current @ {p['v_read_max_v']}V: {extract['summary']['max_read_current_uA']:.1f} uA")


if __name__ == "__main__":
    main()
