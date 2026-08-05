"""Chapter 0007 — current-mode differential crossbar column (SPICE).

Upgrade from the 0005/0006 voltage-mode resistor summer to the architecture the
simulator actually models: a *current-mode* crossbar column with differential
conductance cells `G+`/`G-` and a transimpedance readout.

Architecture
------------
Each signed weight `w_i` is realized by two conductances so that
`w_i*GSCALE = G+_i - G-_i` (balanced zero at `G0`). Each input `x_i` drives both
cells; current sums at two virtual-ground nodes:

    Iplus  = sum_i (x_i - VREF) * G+_i
    Iminus = sum_i (x_i - VREF) * G-_i

Two transimpedance (op-amp) stages convert them to `Vp`, `Vm` (each an
inverting summer through `RF`), and a differential stage gives

    Vout = Vm - Vp = RF * (Iplus - Iminus)
                  = RF * GSCALE * sum_i (x_i - VREF) * w_i

i.e. the column computes the dot product of the reference-relative inputs with
the signed weights — `y = w @ x` for one row — in conductance units.

ngspice note
------------
The two TIA stages are independent linear networks (separate summing nodes and
outputs, sharing only the inputs and reference), so `Vout = Vm - Vp` by
superposition. ngspice's DC operating point is numerically fragile when two
ideal/OTA gain loops share a netlist, collapsing toward a degenerate solution,
so each stage is solved in its own netlist (robust) and combined. Physically
the two stages are uncoupled, so this is exact, not an approximation.
"""

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

from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import u_kOhm, u_V

VREF = 2.5          # virtual reference (V)
G0 = 0.10e-3        # balanced zero conductance (S)
GSCALE = 0.10e-3    # weight -> conductance scale (S per weight unit)
RF = 10.0e3         # transimpedance feedback (ohm)


def conductances(weights, g0=G0, gscale=GSCALE):
    """Return (G+, G-) [S] per weight so that w*GSCALE = G+ - G-."""
    gp, gm = [], []
    for w in weights:
        gp.append(g0 + max(0.0, w) * gscale)
        gm.append(g0 + max(0.0, -w) * gscale)
    return gp, gm


def _tia(xs, gs):
    """One transimpedance stage: VREF - RF * sum (x_i - VREF) * G_i."""
    c = Circuit("tia_0007")
    c.V("vr", "vref", c.gnd, VREF @ u_V)
    for i, x in enumerate(xs):
        c.V(f"x{i}", f"x{i}", c.gnd, x @ u_V)
    for i, g in enumerate(gs):
        c.R(f"w{i}", f"x{i}", "n", (1.0 / g / 1e3) @ u_kOhm)
    c.R("rf", "n", "out", (RF / 1e3) @ u_kOhm)
    c.VCVS("op", "out", c.gnd, "vref", "n", 1e4)
    a = c.simulator().operating_point()
    return float(np.ravel(np.asarray(a["out"]))[0])


def run_column(xs, weights):
    gp, gm = conductances(weights)
    vp = _tia(xs, gp)
    vm = _tia(xs, gm)
    return vm - vp   # differential stage Vout = Vm - Vp (superposition)


def ideal_out(xs, weights):
    u = np.asarray(xs) - VREF
    return RF * GSCALE * float(np.dot(u, weights))


def main():
    weights = [0.50, 0.25]   # signed, in [-1, 1]
    xs = [3.0, 2.1]          # input voltages around VREF = 2.5
    vout = run_column(xs, weights)
    ideal = ideal_out(xs, weights)
    print(f"weights = {weights}")
    print(f"x       = {xs}   (u = x - VREF = {[round(x - VREF, 2) for x in xs]})")
    print(f"  Vout  = {vout:.4f} V")
    print(f"  ideal = {ideal:.4f} V   (Rf*Gscale*sum u_i*w_i)")
    print(f"  err   = {abs(vout - ideal):.4f} V")

    # cross-check the differential realization: G+_i - G-_i == w_i * GSCALE
    # (the same differential-conductance principle the simulator programs,
    # which is itself validated in chapter 0007 / the M1 g_bits study).
    gp, gm = conductances(weights)
    err_g = max(abs((gp[i] - gm[i]) - weights[i] * GSCALE) for i in range(len(weights)))
    print(f"  differential |(G+ - G-) - w*GSCALE| max = {err_g:.2e} S")

    assert abs(vout - ideal) <= 2e-2, "SPICE column must match the hand calc"
    assert err_g <= 1e-12, "differential conductances must realize w*GSCALE exactly"
    print("OK")


if __name__ == "__main__":
    main()
