"""Chapter 0013 — 4×4 current-mode differential crossbar array (SPICE).

Scale the validated 0012 topology to a 4×4 array: four shared input rows and
four independent output columns, each column a differential ``G+/G-`` cell
pair per row with a two-stage TIA readout (exactly the 0007 column, repeated
four times). The array computes

    Vout_j = RF * GSCALE * (W @ u)_j,      u_i = x_i - VREF,

i.e. a full 4x4 matrix-vector product in conductance units, with the same
constants as 0007/0012 (``VREF=2.5 V``, ``G0=GSCALE=0.1 mS``, ``RF=10 kOhm``,
``RF*GSCALE = 1 V per volt per weight``).

This chapter also opens the **behavioral-equivalence** question: the
``analog_llm`` CrossbarTile (configured from the validated
``crossbar-column-v1`` profile) is the architecture simulator's model of this
array. Comparing SPICE vs tile vs the hand reference over deterministic
matrices quantifies how much error the tile abstraction introduces (its 16-bit
conductance/converter quantization) versus the circuit's own VCVS finite-gain
error.

Currents and settling
---------------------
- **Column currents**: each half-column's current is recovered from the SPICE
  half-stage outputs, ``Iplus_j = (VREF - Vp_j)/RF``, and compared to the hand
  ``Iplus_j = sum_i u_i * G+_ij``; the largest cell current (a feasibility
  bound, ``|u|_max * (G0 + GSCALE)``) is recorded.
- **Settling**: a sensitivity study with an *assumed* load capacitance on the
  summing node (no device evidence yet), SPICE transient vs the single-pole
  hand model ``tau = CL / sum_i G_i`` of the half-column, reported in the
  extract JSON only (fails closed under ``physical_claim``).

ngspice note
------------
As in 0007/0012, every TIA stage is an independent linear network sharing only
the ideal input sources and the reference; each is solved in its own netlist
and combined by superposition (8 stages for a 4×4). Columns are uncoupled.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

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

try:  # SPICE engine is optional: the hand model must import engine-free
    from PySpice.Spice.Netlist import Circuit
    from PySpice.Unit import u_kOhm, u_ns, u_pF, u_V

    _PYSPICE_OK = True
except ImportError:  # pragma: no cover - engine-less environment
    _PYSPICE_OK = False


def _require_pyspice() -> None:
    """Raise a clear error when a SPICE solve is requested without PySpice."""
    if not _PYSPICE_OK:
        raise ImportError(
            "PySpice is required for SPICE solves; "
            "install with `pip install -e '.[sim]'`"
        )


VREF = 2.5          # virtual reference (V) -- matches 0005/0007/0009/0010/0012
G0 = 0.10e-3        # balanced zero conductance (S)
GSCALE = 0.10e-3    # weight -> conductance scale (S per weight unit)
RF = 10.0e3         # transimpedance feedback (ohm)
HEADROOM_V = 2.5    # differential output envelope (V), from crossbar-column-v1

# Deterministic weight matrices (4x4, entries in [-1, 1]) and input vectors
# (u = x - VREF) whose outputs stay inside the +/-2.5 V envelope.
W_MIXED = [
    [0.50, 0.25, -0.25, 0.50],
    [-0.50, 0.50, 0.25, 0.25],
    [0.25, -0.25, 0.50, -0.50],
    [0.25, 0.50, -0.50, 0.25],
]
W_SPARSE = [  # one nonzero weight per row (column-aligned)
    [1.0, 0.0, 0.0, 0.0],
    [0.0, 1.0, 0.0, 0.0],
    [0.0, 0.0, 1.0, 0.0],
    [0.0, 0.0, 0.0, 1.0],
]
W_RANK1 = [[0.5 * a * b for b in (0.5, -0.25, 0.25, 0.5)] for a in (0.5, -0.25, 0.25, 0.5)]
W_ZERO = [[0.0] * 4 for _ in range(4)]

U_VECTORS = [
    [0.40, -0.30, 0.25, -0.20],
    [-0.50, -0.50, 0.50, 0.50],
    [0.50, 0.00, -0.50, 0.00],
    [0.25, 0.25, 0.25, 0.25],
]

# (W, u) pairs for the SPICE suite; every |Vout| stays <= 2.5 V.
CASES: list[tuple[list[list[float]], list[float]]] = [
    (W_MIXED, U_VECTORS[0]),
    (W_MIXED, U_VECTORS[1]),
    (W_SPARSE, U_VECTORS[2]),
    (W_RANK1, U_VECTORS[3]),
    (W_ZERO, U_VECTORS[0]),
]


def _check_w(w) -> np.ndarray:
    """Validate a weight matrix is a non-empty finite ``[outputs, inputs]``."""
    w = np.asarray(w, dtype=float)
    if w.ndim != 2 or w.shape[0] == 0 or w.shape[1] == 0:
        raise ValueError(
            f"weights must be a non-empty [outputs, inputs] matrix, got shape {w.shape}"
        )
    if not np.all(np.isfinite(w)):
        raise ValueError("weights must be finite")
    return w


def conductances(w: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(G+, G-)`` [S], shape ``(outputs, inputs)``, so that
    ``G+ - G- = W * GSCALE`` and every cell is balanced at ``G0`` for zero."""
    w = _check_w(w)
    gp = G0 + np.maximum(0.0, w) * GSCALE
    gm = G0 + np.maximum(0.0, -w) * GSCALE
    return gp, gm


def _tia(xs, gs) -> tuple[float, float]:
    """One transimpedance stage. Returns ``(Vout, Vn)``: the stage output and
    the summing-node (virtual ground) voltage."""
    _require_pyspice()
    c = Circuit("tia_0013")
    c.V("vr", "vref", c.gnd, VREF @ u_V)
    for i, x in enumerate(xs):
        c.V(f"x{i}", f"x{i}", c.gnd, x @ u_V)
    for i, g in enumerate(gs):
        c.R(f"w{i}", f"x{i}", "n", (1.0 / g / 1e3) @ u_kOhm)
    c.R("rf", "n", "out", (RF / 1e3) @ u_kOhm)
    c.VCVS("op", "out", c.gnd, "vref", "n", 1e4)
    a = c.simulator().operating_point()
    return (
        float(np.ravel(np.asarray(a["out"]))[0]),
        float(np.ravel(np.asarray(a["n"]))[0]),
    )


def run_array(xs, w) -> tuple[np.ndarray, np.ndarray]:
    """SPICE MVM: ``(Vout [outputs], virtual-ground |Vn - VREF| [per stage])``.

    Each output column solves its ``G+`` and ``G-`` half-columns as independent
    TIA stages and combines them differentially (superposition).
    """
    gp, gm = conductances(w)
    outs = np.zeros(gp.shape[0], dtype=float)
    vg = np.zeros(2 * gp.shape[0], dtype=float)
    for j in range(gp.shape[0]):
        vp, vn_p = _tia(xs, gp[j])
        vm, vn_m = _tia(xs, gm[j])
        outs[j] = vm - vp
        vg[2 * j] = abs(vn_p - VREF)
        vg[2 * j + 1] = abs(vn_m - VREF)
    return outs, vg


def half_stage_outputs(xs, w) -> list[float]:
    """All ``2*outputs`` half-column TIA outputs ``(Vp_j, Vm_j)`` in order."""
    gp, gm = conductances(w)
    halves = []
    for j in range(gp.shape[0]):
        vp, _ = _tia(xs, gp[j])
        vm, _ = _tia(xs, gm[j])
        halves.extend([vp, vm])
    return halves


def ideal_out(xs, w) -> np.ndarray:
    """Hand reference: ``Vout = RF*GSCALE * W @ (x - VREF)`` (RF*GSCALE = 1)."""
    u = np.asarray(xs, dtype=float) - VREF
    if u.ndim != 1 or not np.all(np.isfinite(u)):
        raise ValueError("xs must be a finite 1-D input vector")
    w = _check_w(w)
    if w.shape[1] != u.shape[0]:
        raise ValueError(
            f"weights inputs {w.shape[1]} must match xs length {u.shape[0]}"
        )
    return RF * GSCALE * (w @ u)


# ---- column currents ------------------------------------------------------
def column_currents_hand(xs, w) -> dict[str, np.ndarray]:
    """Hand column currents [A]: ``Iplus_j = sum_i u_i*G+_ij`` etc."""
    u = np.asarray(xs, dtype=float) - VREF
    gp, gm = conductances(w)
    return {"iplus": gp @ u, "iminus": gm @ u}


def column_currents_spice(xs, w) -> dict[str, np.ndarray]:
    """Column currents recovered from the SPICE half-stage outputs:
    ``Iplus_j = (VREF - Vp_j)/RF`` (the current through the feedback path)."""
    halves = np.asarray(half_stage_outputs(xs, w))
    vp = halves[0::2]
    vm = halves[1::2]
    return {"iplus": (VREF - vp) / RF, "iminus": (VREF - vm) / RF}


def max_cell_current_a(u: np.ndarray) -> float:
    """Largest cell current in the array: ``|u|_max * (G0 + GSCALE)`` [A]."""
    return float(np.max(np.abs(np.asarray(u)))) * (G0 + GSCALE)


# ---- settling (assumed CL, sensitivity study) ------------------------------
def half_stage_rc_tau_s(cl_farad: float, gs) -> float:
    """Single-pole hand model for the summing node: ``tau = CL / sum_i G_i``.

    The summing node sees the parallel cell conductances (inputs are ideal
    voltage sources, small-signal ground) and the feedback path; for the
    large-gain VCVS the dominant time constant is ``CL / sum(G_i)``.
    """
    return cl_farad / float(np.sum(gs))


def settle_time(xs_from, xs_to, gs, band_v: float, cl_farad: float,
                *, t_end_ns: float = 2000.0) -> float:
    """SPICE settling time (s) of a half-stage output after an input step.

    ``cl_farad`` is the *assumed* summing-node capacitance (no device evidence
    yet -- sensitivity parameter). Input ``i0`` steps from ``xs_from[0]`` to
    ``xs_to[0]`` (0.1 ns edge); returns the first time after which the output
    stays within ``+/- band_v`` of its final value.
    """
    _require_pyspice()
    c = Circuit("settle_0013")
    c.V("vr", "vref", c.gnd, VREF @ u_V)
    c.PulseVoltageSource(
        "x0", "x0", c.gnd,
        initial_value=xs_from[0] @ u_V,
        pulsed_value=xs_to[0] @ u_V,
        delay_time=0 @ u_ns,
        rise_time=0.1 @ u_ns,
        fall_time=0.1 @ u_ns,
        pulse_width=1e6 @ u_ns,
        period=2e6 @ u_ns,
        dc_offset=xs_from[0] @ u_V,
    )
    for i, x in enumerate(xs_to[1:], start=1):
        c.V(f"x{i}", f"x{i}", c.gnd, x @ u_V)
    for i, g in enumerate(gs):
        c.R(f"w{i}", f"x{i}", "n", (1.0 / g / 1e3) @ u_kOhm)
    c.R("rf", "n", "out", (RF / 1e3) @ u_kOhm)
    c.C("cl", "n", c.gnd, (cl_farad / 1e-12) @ u_pF)
    c.VCVS("op", "out", c.gnd, "vref", "n", 1e4)
    a = c.simulator().transient(step_time=(1 @ u_ns), end_time=(t_end_ns @ u_ns))
    t = np.asarray(a.time) * 1e9  # ns
    v = np.asarray(a["out"])
    final = float(v[-1])
    ok = np.abs(v - final) <= band_v
    for i in range(len(t)):
        if np.all(ok[i:]):
            return float(t[i]) * 1e-9
    return float("nan")


def settle_time_hand(dv: float, band_v: float, tau_s: float) -> float:
    """Single-pole hand settle: ``tau * ln(dV/band)``."""
    return tau_s * np.log(dv / band_v)


# ---- behavioral (analog_llm tile) comparison --------------------------------
def tile_output(xs, w, tile) -> np.ndarray:
    """The ``analog_llm`` CrossbarTile's MVM output for the same (xs, W)."""
    return np.asarray(tile.forward(np.asarray(xs, dtype=float) - VREF), dtype=float)


def main() -> None:
    print(f"4x4 differential crossbar, VREF = {VREF} V, G0 = {G0:.2e} S, "
          f"GSCALE = {GSCALE:.2e} S, RF = {RF/1e3:.0f} kOhm, headroom +/-{HEADROOM_V} V")

    from analog_llm import build_tile_factory

    tile = build_tile_factory(
        "device_profiles/crossbar-column-v1.json",
        4, 4,
        g_bits=16, dac_bits=16, adc_bits=16,
    )()

    worst_sh = 0.0
    worst_t = 0.0
    for w, u in CASES:
        xs = [ui + VREF for ui in u]
        vout, vg = run_array(xs, w)
        ideal = ideal_out(xs, w)
        tile.program(w)
        vtile = tile_output(xs, w, tile)
        err_sh = float(np.max(np.abs(vout - ideal)))
        err_t = float(np.max(np.abs(vtile - ideal)))
        worst_sh = max(worst_sh, err_sh)
        worst_t = max(worst_t, err_t)
        print(f"  u={u}  Vout_spice={np.round(vout, 5).tolist()}")
        print(f"    |spice-hand| {err_sh:.2e}  |tile-hand| {err_t:.2e}  "
              f"max|Vn-VREF| {vg.max():.2e} V")
        assert err_sh <= 2e-3, f"SPICE array must match hand MVM, err {err_sh}"
        assert np.max(np.abs(vout)) <= HEADROOM_V + 1e-3, "outputs must stay in headroom"
        assert vg.max() <= 0.05, "virtual ground loading bound"
        assert err_t <= 2e-3, f"behavioral tile must match hand MVM, err {err_t}"
    print(f"  worst |spice-hand| = {worst_sh:.2e} V, worst |tile-hand| = {worst_t:.2e} V")

    # column currents: SPICE-recovered vs hand sum u*G
    worst_i = 0.0
    for w, u in CASES:
        xs = [ui + VREF for ui in u]
        ic = column_currents_spice(xs, w)
        ih = column_currents_hand(xs, w)
        d = max(float(np.max(np.abs(ic["iplus"] - ih["iplus"]))),
                float(np.max(np.abs(ic["iminus"] - ih["iminus"]))))
        worst_i = max(worst_i, d)
    print(f"  worst |I_spice - I_hand| over all half-columns = {worst_i:.2e} A")
    assert worst_i <= 5e-6, "SPICE column currents must match hand u*G sums"

    # 2x2 regression: the scaled module reproduces the committed 0012 results
    ext12 = json.loads(
        (Path(__file__).resolve().parents[2] / "verification" / "circuit" / "results"
         / "crossbar-2x2-0012-extract.json").read_text("utf-8")
    )
    for row in ext12["cases"]:
        vout, _ = run_array(row["xs"], row["w"])
        assert np.max(np.abs(vout - np.asarray(row["vout_spice"]))) <= 1e-6, (
            "4x4 module must reproduce the committed 0012 results"
        )
    print("  2x2 regression: 4x4 module reproduces the committed 0012 extract")

    # settling (assumed CL, sensitivity study -- recorded, not a physical claim)
    cl = 1e-12
    gs = conductances(W_MIXED)[0][0]  # column 0 G+ cells
    tau = half_stage_rc_tau_s(cl, gs)
    band = 1e-3
    dv = 1.0
    ts = settle_time([VREF + 0.0, VREF, VREF, VREF], [VREF + 1.0, VREF, VREF, VREF],
                     gs, band, cl)
    ts2 = settle_time([VREF + 0.0, VREF, VREF, VREF], [VREF + 1.0, VREF, VREF, VREF],
                      gs, band, cl)
    th = settle_time_hand(dv, band, tau)
    print(f"  settling (assumed CL = {cl*1e12:.0f} pF, band = {band} V): "
          f"spice {ts*1e9:.1f} ns, single-pole lower bound tau*ln(dV/band) = "
          f"{th*1e9:.1f} ns (tau = {tau*1e9:.1f} ns)")
    print("    NOTE: the ideal VCVS has no bandwidth model; the transient is "
          "model-dominated (ringing, no physical op-amp pole), so this is a "
          "recorded data point, not a settling claim. A real op-amp bandwidth "
          "model is required (0014 / R4).")
    assert ts == ts2, "settling study must be deterministic"
    print("OK")


if __name__ == "__main__":
    main()
