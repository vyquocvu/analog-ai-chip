"""Chapter 0012 — 2×2 current-mode differential crossbar array.

This is the smallest array that proves the physical topology scales from the
single 0007 column to multiple output columns sharing the same input rows.
Weights follow the repository convention ``[output, input]``.

For each output column j:

    Vout_j = RF * GSCALE * sum_i ((x_i - VREF) * W[j, i])

Each signed cell is differential: ``G+ - G- = W * GSCALE``.  The two columns
share the same input voltages but have independent conductance cells and TIA
readouts.  SPICE solves each independent TIA branch separately, matching the
robust decomposition used by chapter 0007.

The current SPICE model is DC operating-point only and uses an ideal high-gain
VCVS op-amp.  Rail/headroom is therefore checked explicitly from the branch
voltages rather than hidden behind a saturation model.
"""

from __future__ import annotations

import os
from typing import Iterable

import numpy as np

VREF = 2.5
VLO = 0.0
VHI = 5.0
G0 = 0.10e-3
GSCALE = 0.10e-3
RF = 10.0e3


def _weights_2x2(weights: Iterable[Iterable[float]]) -> np.ndarray:
    w = np.asarray(weights, dtype=float)
    if w.shape != (2, 2):
        raise ValueError(f"weights must be 2x2 [output,input], got {w.shape}")
    if not np.all(np.isfinite(w)):
        raise ValueError("weights must be finite")
    if np.any(np.abs(w) > 1.0):
        raise ValueError("weights must be within [-1, 1]")
    return w


def _inputs_2(xs: Iterable[float]) -> np.ndarray:
    x = np.asarray(xs, dtype=float)
    if x.shape != (2,):
        raise ValueError(f"expected 2 inputs, got shape {x.shape}")
    if not np.all(np.isfinite(x)):
        raise ValueError("inputs must be finite")
    return x


def conductance_matrices(weights: Iterable[Iterable[float]]) -> tuple[np.ndarray, np.ndarray]:
    """Map a 2×2 signed weight matrix to differential conductances in siemens."""
    w = _weights_2x2(weights)
    gp = G0 + np.maximum(w, 0.0) * GSCALE
    gm = G0 + np.maximum(-w, 0.0) * GSCALE
    return gp, gm


def ideal_mvm(xs: Iterable[float], weights: Iterable[Iterable[float]]) -> np.ndarray:
    """Hand/NumPy reference for the two shared input rows and two output columns."""
    x = _inputs_2(xs)
    w = _weights_2x2(weights)
    return RF * GSCALE * (w @ (x - VREF))


def ideal_branch_voltages(
    xs: Iterable[float], weights: Iterable[Iterable[float]]
) -> tuple[np.ndarray, np.ndarray]:
    """Return ideal TIA branch voltages ``(Vp, Vm)`` for both output columns."""
    x = _inputs_2(xs)
    gp, gm = conductance_matrices(weights)
    u = x - VREF
    vp = VREF - RF * (gp @ u)
    vm = VREF - RF * (gm @ u)
    return vp, vm


def headroom_report(xs: Iterable[float], weights: Iterable[Iterable[float]]) -> dict[str, object]:
    """Report whether all TIA branch outputs remain within the 0–5 V envelope."""
    vp, vm = ideal_branch_voltages(xs, weights)
    branches = np.concatenate((vp, vm))
    low_margin = float(np.min(branches - VLO))
    high_margin = float(np.min(VHI - branches))
    return {
        "vp_v": vp.tolist(),
        "vm_v": vm.tolist(),
        "low_margin_v": low_margin,
        "high_margin_v": high_margin,
        "within_rails": bool(low_margin >= 0.0 and high_margin >= 0.0),
    }


def _configure_ngspice_library() -> None:
    if "NGSPICE_LIBRARY_PATH" in os.environ:
        return
    for path in (
        "/opt/homebrew/lib/libngspice.dylib",
        "/usr/local/lib/libngspice.dylib",
        "/usr/lib/x86_64-linux-gnu/libngspice.so",
    ):
        if os.path.exists(path):
            os.environ["NGSPICE_LIBRARY_PATH"] = path
            return


def _tia(xs: np.ndarray, conductances: np.ndarray) -> float:
    """Solve one independent TIA branch in ngspice and return its output voltage."""
    _configure_ngspice_library()
    try:
        from PySpice.Spice.Netlist import Circuit
        from PySpice.Unit import u_kOhm, u_V
    except ModuleNotFoundError as exc:
        raise ImportError("PySpice is required for run_array; install .[sim]") from exc

    c = Circuit("crossbar_2x2_tia")
    c.V("vr", "vref", c.gnd, VREF @ u_V)
    for i, value in enumerate(xs):
        c.V(f"x{i}", f"x{i}", c.gnd, float(value) @ u_V)
    for i, g in enumerate(conductances):
        c.R(f"w{i}", f"x{i}", "n", (1.0 / float(g) / 1e3) @ u_kOhm)
    c.R("rf", "n", "out", (RF / 1e3) @ u_kOhm)
    c.VCVS("op", "out", c.gnd, "vref", "n", 1e4)
    analysis = c.simulator().operating_point()
    return float(np.ravel(np.asarray(analysis["out"]))[0])


def run_array(xs: Iterable[float], weights: Iterable[Iterable[float]]) -> np.ndarray:
    """Run the 2×2 DC SPICE array, returning one differential voltage per column."""
    x = _inputs_2(xs)
    gp, gm = conductance_matrices(weights)
    outputs = []
    for j in range(2):
        vp = _tia(x, gp[j])
        vm = _tia(x, gm[j])
        outputs.append(vm - vp)
    return np.asarray(outputs)


def main() -> None:
    xs = [3.0, 2.1]
    weights = [[0.50, 0.25], [-0.50, 0.25]]
    ideal = ideal_mvm(xs, weights)
    print(f"x = {xs}")
    print(f"W = {weights}")
    print(f"ideal = {ideal.tolist()} V")
    print(f"headroom = {headroom_report(xs, weights)}")
    try:
        spice = run_array(xs, weights)
    except (ImportError, OSError) as exc:
        print(f"SPICE unavailable: {exc}")
        return
    print(f"spice = {spice.tolist()} V")
    print(f"max |SPICE-ideal| = {float(np.max(np.abs(spice - ideal))):.6g} V")


if __name__ == "__main__":
    main()
