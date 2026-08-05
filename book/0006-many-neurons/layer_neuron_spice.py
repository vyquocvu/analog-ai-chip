"""SPICE sanity check for chapter 0006: a 2-neuron layer on one LM358.

Both neurons are inverting summers that share the 2.5 V virtual reference, as
built in 0005. Each neuron has 2 inputs (M = 2); the layer is a 2×2 weight
matrix. Both op-amps come from the same dual LM358.

    neuron0: Vout0 = VREF − (w00·(x1−VREF) + w01·(x2−VREF))
    neuron1: Vout1 = VREF − (w10·(x1−VREF) + w11·(x2−VREF))

with w = [[0.50, 0.25], [0.50, 0.25]] (Rf/R = 1k/2k, 1k/4k for both).
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

VREF = 2.5
W = [[0.50, 0.25], [0.50, 0.25]]


def _kohm(w):
    return 1.0 / w  # Rf = 1 kOhm


def run_layer(x1, x2, aol=1e4):
    c = Circuit("layer_0006")
    c.V("vr", "vref", c.gnd, VREF @ u_V)
    c.V("1", "x1", c.gnd, x1 @ u_V)
    c.V("2", "x2", c.gnd, x2 @ u_V)
    # neuron 0
    c.R("n0_i0", "x1", "n0", _kohm(W[0][0]) @ u_kOhm)
    c.R("n0_i1", "x2", "n0", _kohm(W[0][1]) @ u_kOhm)
    c.R("n0_f", "n0", "out0", 1.0 @ u_kOhm)
    c.VCVS("op0", "out0", c.gnd, "vref", "n0", aol)
    # neuron 1 (shares inputs and reference)
    c.R("n1_i0", "x1", "n1", _kohm(W[1][0]) @ u_kOhm)
    c.R("n1_i1", "x2", "n1", _kohm(W[1][1]) @ u_kOhm)
    c.R("n1_f", "n1", "out1", 1.0 @ u_kOhm)
    c.VCVS("op1", "out1", c.gnd, "vref", "n1", aol)

    a = c.simulator().operating_point()
    v0 = float(np.ravel(np.asarray(a["out0"]))[0])
    v1 = float(np.ravel(np.asarray(a["out1"]))[0])
    return v0, v1


def ideal_out(x1, x2, w0, w1):
    return VREF - (w0 * (x1 - VREF) + w1 * (x2 - VREF))


def main():
    x1, x2 = 3.0, 2.1
    v0, v1 = run_layer(x1, x2)
    i0 = ideal_out(x1, x2, W[0][0], W[0][1])
    i1 = ideal_out(x1, x2, W[1][0], W[1][1])
    print(f"x = [{x1}, {x2}]  VREF = {VREF}")
    print(f"  neuron0: sim={v0:.4f}  ideal={i0:.4f}  err={abs(v0-i0):.4f}")
    print(f"  neuron1: sim={v1:.4f}  ideal={i1:.4f}  err={abs(v1-i1):.4f}")
    assert abs(v0 - i0) <= 5e-3 and abs(v1 - i1) <= 5e-3, "layer mismatch"


if __name__ == "__main__":
    main()
