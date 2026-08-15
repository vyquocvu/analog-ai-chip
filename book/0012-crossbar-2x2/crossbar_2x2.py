"""Chapter 0012 — 2×2 current-mode differential crossbar array (SPICE).

Scale the 0007 single-column design to a small *array*: two input rows shared
by two independent output columns. Each cell is a differential conductance
pair ``(G+, G-)`` realizing the signed weight

    w_ij * GSCALE = G+_ij - G-_ij,        balanced zero at G0,

and each output column ``j`` sums its cell currents at two virtual-ground
nodes (one for ``G+``, one for ``G-``) and converts them with a
transimpedance stage. With inputs ``u_i = x_i - VREF``,

    Iplus_j  = sum_i u_i * G+_ij
    Iminus_j = sum_i u_i * G-_ij
    Vout_j   = Vm_j - Vp_j
             = RF * GSCALE * sum_i u_i * w_ij
             = (RF * GSCALE) * (W @ u)_j

i.e. the array computes the full matrix-vector product ``y = W @ u`` (one row
per output column) in conductance units. Orientation follows the simulator
convention: ``W`` is ``[outputs, inputs]``.

ngspice note
------------
Each of the four TIA stages (``Vp_0, Vm_0, Vp_1, Vm_1``) is an independent
linear network sharing only the ideal input sources and the reference, so
``Vout_j = Vm_j - Vp_j`` by superposition -- exactly as in 0007, where two
ideal/OTA gain loops in one netlist collapsed toward a degenerate DC
solution. Each stage is therefore solved in its own netlist (robust) and the
half-column outputs are combined. The two output columns are also uncoupled:
a column's cells connect only to that column's summing node, so changing one
column's weights cannot change the other column's output (asserted as the
column-independence check).
"""

from __future__ import annotations

import os

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
    from PySpice.Unit import u_kOhm, u_V

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


VREF = 2.5          # virtual reference (V) -- matches 0005/0007/0009/0010
G0 = 0.10e-3        # balanced zero conductance (S)
GSCALE = 0.10e-3    # weight -> conductance scale (S per weight unit)
RF = 10.0e3         # transimpedance feedback (ohm)
HEADROOM_V = 2.5    # differential output envelope (V), from crossbar-column-v1

# Deterministic operating points and weight matrices spanning signed weights,
# zero/balanced cells, one zero per row, and the boundary envelope.
# W is [outputs, inputs]; xs are absolute input voltages around VREF.
CASES: list[tuple[list[float], list[list[float]]]] = [
    ([3.0, 2.1], [[0.50, 0.25], [-0.25, 0.50]]),   # mixed signs, partial scale
    ([3.5, 1.5], [[1.0, -1.0], [-1.0, 1.0]]),      # full-scale differential
    ([2.5, 2.5], [[0.0, 0.0], [0.0, 0.0]]),        # balanced zero everywhere
    ([2.5, 3.0], [[0.0, 0.50], [0.50, 0.0]]),      # one zero weight per row
    ([5.0, 2.5], [[1.0, 0.0], [0.0, 1.0]]),        # boundary: |Vout| = 2.5 V
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
    c = Circuit("tia_0012")
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


def half_stage_outputs(xs, w) -> list[float]:
    """All four half-column TIA outputs ``(Vp_0, Vm_0, Vp_1, Vm_1)``.

    Used for the output-stage rail check: the differential output stays in
    ``+/-2.5 V`` but each single-rail (0..5 V) half-stage can swing outside it.
    """
    gp, gm = conductances(w)
    halves = []
    for j in range(gp.shape[0]):
        vp, _ = _tia(xs, gp[j])
        vm, _ = _tia(xs, gm[j])
        halves.extend([vp, vm])
    return halves


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


def ideal_out(xs, w) -> np.ndarray:
    """Hand reference: ``Vout = RF*GSCALE * W @ (x - VREF)``."""
    u = np.asarray(xs, dtype=float) - VREF
    if u.ndim != 1 or not np.all(np.isfinite(u)):
        raise ValueError("xs must be a finite 1-D input vector")
    w = _check_w(w)
    if w.shape[1] != u.shape[0]:
        raise ValueError(
            f"weights inputs {w.shape[1]} must match xs length {u.shape[0]}"
        )
    return RF * GSCALE * (w @ u)


def half_stage_rail_envelope_v() -> float:
    """Per-input envelope that keeps every half-stage inside the 0..5 V rail.

    The strongest G+ cell is ``G0 + GSCALE``; the half-stage output is
    ``VREF - RF * sum u_i * G_i``, so a single full-scale input must satisfy
    ``RF * |u| * (G0 + GSCALE) <= VREF``, i.e. ``|u| <= VREF/(RF*(G0+GSCALE))``.
    """
    return VREF / (RF * (G0 + GSCALE))


def independence_error(xs, w_a, w_b) -> float:
    """|Vout_0(A) - Vout_0(B)| when only column 1 differs: the two output
    columns share the input rows but are uncoupled networks, so changing one
    column's weights must not change the other column's output."""
    va, _ = run_array(xs, w_a)
    vb, _ = run_array(xs, w_b)
    return float(abs(va[0] - vb[0]))


def main() -> None:
    print(f"2x2 differential crossbar, VREF = {VREF} V, G0 = {G0:.2e} S, "
          f"GSCALE = {GSCALE:.2e} S, RF = {RF/1e3:.0f} kOhm, "
          f"headroom +/-{HEADROOM_V} V")
    worst = 0.0
    for xs, w in CASES:
        vout, vg = run_array(xs, w)
        ideal = ideal_out(xs, w)
        err = float(np.max(np.abs(vout - ideal)))
        worst = max(worst, err)
        print(f"  xs={xs}  W={w}")
        print(f"    Vout = {np.round(vout, 6).tolist()}  ideal = "
              f"{np.round(ideal, 6).tolist()}  max|err| = {err:.2e} V")
        print(f"    max |Vn - VREF| = {vg.max():.2e} V")
        assert err <= 2e-3, f"SPICE array must match hand MVM, err {err}"
        assert np.max(np.abs(vout)) <= HEADROOM_V + 1e-3, "outputs must stay in headroom"
        assert vg.max() <= 0.05, "virtual ground must sit near VREF (loading check)"
    print(f"  worst |SPICE - hand| over {len(CASES)} cases = {worst:.2e} V")

    # balanced zero: all G+ = G- = G0 -> outputs exactly 0. The summing node
    # still sits ~ |Vhalf|/Aol away from VREF (finite 1e4 VCVS gain), so the
    # loading bound (0.05 V) applies, not machine precision.
    vout, vg = run_array([2.5, 2.5], [[0.0, 0.0], [0.0, 0.0]])
    assert np.all(np.abs(vout) <= 1e-12), "balanced zero must give exactly 0"
    assert vg.max() <= 0.05, "balanced zero keeps virtual ground near VREF"

    # column independence: change only column 1's weights
    ind = independence_error(
        [3.0, 2.1], [[0.50, 0.25], [0.25, 0.50]], [[0.50, 0.25], [-1.0, 0.0]]
    )
    print(f"  column-independence: |d Vout_0| when only column 1 changes = {ind:.2e} V")
    assert ind <= 2e-3, "columns must be independent (shared rows, uncoupled networks)"

    # Output-stage headroom finding: the differential output is bounded by
    # +/-2.5 V, but each half-stage is a single-rail (0..5 V) inverting summer.
    # With a full-scale weight at the input envelope edge the G+ half-stage of
    # the boundary column reaches -2.5 V -- below the 0 V rail. The ideal VCVS
    # model has no clipping, so the differential output stays exact; a real
    # single-rail TIA would clip there. Reported as a finding, not hidden:
    #   usable per-input envelope for |w| = 1 is set by the half-stage rail,
    #   |u| <= VREF / (RF*(G0 + GSCALE)) = 1.25 V, not by the +/-2.5 V
    #   differential headroom.
    violations = []
    names = ("Vp_0", "Vm_0", "Vp_1", "Vm_1")
    for xs, w in CASES:
        for name, half in zip(names, half_stage_outputs(xs, w)):
            if not (0.0 <= half <= 5.0):
                violations.append((xs, name, half))
    print(f"  half-stage rail violations (single 0..5 V rail): {len(violations)}")
    for xs, name, half in violations:
        print(f"    {name} = {half:.4f} V at xs={xs} (boundary envelope edge)")
    print(f"  half-stage rail envelope: |u| <= {half_stage_rail_envelope_v():.2f} V")
    assert len(violations) == 1, (
        "expected exactly the boundary-case G+ half-stage below the 0 V rail"
    )
    print("OK")


if __name__ == "__main__":
    main()
