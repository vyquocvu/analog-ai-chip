"""Chapter 0012 — 2×2 current-mode differential crossbar array.

This is the smallest array that proves the physical topology scales from the
single 0007 column to multiple output columns sharing the same input rows.
Weights follow the repository convention ``[output, input]``.

For each output column j:

    Vout_j = RF * GSCALE * sum_i ((x_i - VREF) * W[j, i])

Each signed cell is differential: ``G+ - G- = W * GSCALE``. The two columns
share the same input voltages but have independent conductance cells and TIA
readouts. SPICE solves each independent TIA branch separately, matching the
robust decomposition used by chapter 0007.

The current SPICE model is DC operating-point only and uses an ideal high-gain
VCVS op-amp. Rail/headroom is therefore checked explicitly from the branch
voltages rather than hidden behind a saturation model.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from collections.abc import Iterable
from pathlib import Path

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


def _tia_netlist(xs: np.ndarray, conductances: np.ndarray) -> str:
    """Return the deterministic ngspice netlist for one TIA branch."""
    r0 = 1.0 / float(conductances[0])
    r1 = 1.0 / float(conductances[1])
    return f"""* 0012 2x2 differential crossbar TIA branch
VREF vref 0 {VREF:.17g}
VX0 x0 0 {float(xs[0]):.17g}
VX1 x1 0 {float(xs[1]):.17g}
RW0 x0 n {r0:.17g}
RW1 x1 n {r1:.17g}
RRF n out {RF:.17g}
EOP out 0 vref n 1e4
.op
.control
set noaskquit
op
print v(out)
quit
.endc
.end
"""


def _parse_vout(stdout: str) -> float:
    """Parse the explicit ``print v(out)`` scalar from ngspice batch output."""
    matches = re.findall(
        r"(?im)^\s*v\(out\)\s*=\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)\s*$",
        stdout,
    )
    if not matches:
        raise RuntimeError("ngspice output did not contain a scalar v(out)")
    return float(matches[-1])


def _tia(xs: np.ndarray, conductances: np.ndarray) -> float:
    """Solve one independent TIA branch by invoking the ngspice CLI directly."""
    executable = shutil.which("ngspice")
    if executable is None:
        raise OSError("ngspice executable is required for run_array")

    netlist = _tia_netlist(xs, conductances)
    path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".cir", delete=False) as handle:
            handle.write(netlist)
            path = Path(handle.name)
        result = subprocess.run(
            [executable, "-b", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        if path is not None:
            path.unlink(missing_ok=True)

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"ngspice failed with exit {result.returncode}: {detail}")
    return _parse_vout(result.stdout + "\n" + result.stderr)


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
    except (OSError, RuntimeError) as exc:
        print(f"SPICE unavailable/failed: {exc}")
        return
    print(f"spice = {spice.tolist()} V")
    print(f"max |SPICE-ideal| = {float(np.max(np.abs(spice - ideal))):.6g} V")


if __name__ == "__main__":
    main()
