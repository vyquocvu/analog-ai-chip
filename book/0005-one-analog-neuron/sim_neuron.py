"""Design and verify (before building) the 0005 analog-neuron circuit in SPICE.

Circuit: a two-input inverting summing amplifier on a 5 V single supply.

                Rf = 1 k
   x1 ── R1=2k ──┬── out
                 │    │
   x2 ── R2=4k ──(+)  (op-amp)
                 │
                0V (virtual ground / inverting input)

Hand contract (from book/0005):  y = w1*x1 + w2*x2,  with
    w1 = Rf/R1 = 1k/2k = 0.50
    w2 = Rf/R2 = 1k/4k = 0.25
For x = [0.5, 1.0]:  y = 0.5*0.5 + 0.25*1.0 = 0.25 + 0.25 = 0.5 V (magnitude;
the physical output is inverted: Vout = −y).

This is a *functional* SPICE verification of the summing relation. It uses an
ideal op-amp model, so it deliberately does not yet model output saturation,
input common-mode limits, offset, or finite gain-bandwidth of a real device
(those are the chapter's later "bring-up" non-idealities).

To run you need the `ngspice` engine. On macOS with Homebrew this is typically:
    brew install ngspice
    pip install -e '.[sim]'
Point PySpice at the shared library (only if it cannot auto-find it):
    export NGSPICE_LIBRARY_PATH="$(brew --prefix)/lib/libngspice.dylib"
"""

import os

import numpy as np

# Must be set before importing PySpice.
if "NGSPICE_LIBRARY_PATH" not in os.environ:
    candidates = [
        "/opt/homebrew/lib/libngspice.dylib",
        "/usr/local/lib/libngspice.dylib",
        "/usr/lib/x86_64-linux-gnu/libngspice.so",
    ]
    for path in candidates:
        if os.path.exists(path):
            os.environ["NGSPICE_LIBRARY_PATH"] = path
            break

from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import u_kOhm, u_V

RF = 1.0  # kOhm
R1 = 2.0  # kOhm  -> w1 = Rf/R1 = 0.5
R2 = 4.0  # kOhm  -> w2 = Rf/R2 = 0.25
W1 = RF / R1
W2 = RF / R2
VDD = 5.0  # V, single supply (rails not coupled to ideal model)


def build_parallel_sum(x1: float, x2: float) -> Circuit:
    c = Circuit("analog_neuron_0005")
    c.V("dd", "vdd", c.gnd, VDD @ u_V)
    c.V("1", "x1", c.gnd, x1 @ u_V)
    c.V("2", "x2", c.gnd, x2 @ u_V)
    c.R("1", "x1", "n", R1 @ u_kOhm)
    c.R("2", "x2", "n", R2 @ u_kOhm)
    c.R("f", "n", "out", RF @ u_kOhm)
    # ideal op-amp: out = A * (gnd - n), A large -> n is a virtual ground
    c.VCVS("op", "out", c.gnd, "n", c.gnd, 100000)
    return c


def measure(x1: float, x2: float) -> float:
    circuit = build_parallel_sum(x1, x2)
    analysis = circuit.simulator().operating_point()
    return float(np.ravel(analysis["out"])[0])


def main() -> None:
    cases = [
        (0.5, 1.0, 0.50),
        (0.2, 0.8, 0.30),
        (1.0, 0.0, 0.50),
        (0.0, 2.0, 0.50),
        (0.6, 1.2, 0.60),
        (0.8, 0.4, 0.50),
    ]
    tol = 5e-3  # 5 mV
    print("  x1     x2    |Vout|(sim)  y(hand)   match")
    for x1, x2, y in cases:
        vout = measure(x1, x2)
        mag = abs(vout)
        ok = abs(mag - y) <= tol
        print(f"  {x1:5.2f} {x2:5.2f}   {mag:8.4f}   {y:6.2f}    {'OK' if ok else 'FAIL'}")
        assert ok, f"|Vout|={mag:.4f} did not match y={y:.2f} (x={[x1, x2]})"
    print("\nAll cases match W@x = w1*x1 + w2*x2 within", tol, "V.")
    print("Design: Rf=1k, R1=2k, R2=4k  =>  w = [0.50, 0.25],  Vout = -(W@x)")


if __name__ == "__main__":
    main()
