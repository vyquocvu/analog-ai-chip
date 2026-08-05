"""A1 — verify the 0005 neuron with a NON-IDEAL op-amp model (PySpice + ngspice).

The chapter warns: do not copy a dual-supply textbook inverting summer onto a
5 V breadboard. This script makes that warning measurable.

The op-amp is modelled in SPICE as a voltage-controlled voltage source (VCVS)
with a **finite open-loop gain Aol** and a **series input offset voltage Vos**.
Because the ideal VCVS has no rails, rail-to-rail saturation is applied at the
reporting boundary with explicit rail limits `[0 V, 5 V]` — the same result a
rail-limited chip gives (linear below the rail, clipped at the rail beyond it).
Every number is printed; nothing is hidden.

Scenarios
  1. LINEAR region around a 2.5 V virtual reference: matches the ideal
     weighted-sum swing inside the 0..5 V rails (finite-gain error is tiny).
  2. SATURATION: an input needing an output past the 5 V rail clips at 5 V
     instead of the ideal (larger) value.
  3. GND-reference on a single 5 V supply: a positive input needs a negative
     output -> clips at 0 V (the chapter's exact warning).
  4. OFFSET: a 10 mV Vos measurably shifts the operating point.

Run with the ngspice engine available (see: `brew install ngspice`; on this
machine set NGSPICE_LIBRARY_PATH to libngspice.dylib if auto-detection fails).
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

RF, R1, R2 = 1.0, 2.0, 4.0  # kOhm  -> w = [Rf/R1, Rf/R2] = [0.5, 0.25]
W1, W2 = RF / R1, RF / R2
VHI, VLO = 5.0, 0.0
VREF = 2.5
AOL = 1e4


def run_linear(x1, x2, vref, vos=0.0, aol=AOL):
    """Solve the closed-loop inverting summer; return (Vout, V(n))."""
    c = Circuit("analog_neuron_0005_nonideal")
    c.V("vr", "vref", c.gnd, vref @ u_V)
    c.V("os", "vp", "vref", vos @ u_V)  # vp = vref + vos
    c.V("1", "x1", c.gnd, x1 @ u_V)
    c.V("2", "x2", c.gnd, x2 @ u_V)
    c.R("1", "x1", "n", R1 @ u_kOhm)
    c.R("2", "x2", "n", R2 @ u_kOhm)
    c.R("f", "n", "out", RF @ u_kOhm)
    # out = aol * (V(vp) - V(n))
    c.VCVS("op", "out", c.gnd, "vp", "n", aol)
    a = c.simulator().operating_point()
    out = float(np.ravel(np.asarray(a["out"]))[0])
    n = float(np.ravel(np.asarray(a["n"]))[0])
    return out, n


def clamp(v):
    return min(max(v, VLO), VHI)


def ideal_delta(x1, x2, vref):
    return vref - (W1 * (x1 - vref) + W2 * (x2 - vref))


def main():
    tol = 5e-3

    print("Scenario 1 — LINEAR region around a 2.5 V virtual reference")
    x1, x2 = VREF + 0.5, VREF - 0.4
    out, n = run_linear(x1, x2, VREF)
    ideal = ideal_delta(x1, x2, VREF)
    err = abs(out - ideal)
    print(f"  x=[{x1:.2f},{x2:.2f}]  out={out:.4f}  ideal={ideal:.4f}  "
          f"n={n:.2e}  err={err:.4f}  {'OK' if err <= tol else 'FAIL'}")
    assert err <= tol, f"linear region mismatch err={err:.4f}"

    print("Scenario 2 — SATURATION (output would pass the 5 V rail)")
    x1, x2 = -2.0, -2.0
    out, _ = run_linear(x1, x2, VREF)
    ideal = ideal_delta(x1, x2, VREF)
    chip = clamp(out)
    print(f"  x=[{x1:.2f},{x2:.2f}]  ideal={ideal:.4f}  SPICE(linear)={out:.4f}  "
          f"chip(clamped)={chip:.4f}")
    assert abs(chip - VHI) <= tol, f"expected clip at {VHI} V, got {chip:.4f}"
    assert abs(out - ideal) <= 0.05, "linear solve should match ideal before clamp"

    print("Scenario 3 — GND-reference on single 5 V supply (chapter warning)")
    x1, x2 = 0.5, 1.0
    out, _ = run_linear(x1, x2, 0.0)
    chip = clamp(out)
    mag_ideal = W1 * x1 + W2 * x2
    print(f"  x=[{x1:.2f},{x2:.2f}]  ideal |out|={mag_ideal:.2f} V (negative); "
          f"chip output={chip:.4f} (clipped at 0 V rail)")
    assert abs(chip - VLO) <= tol, f"expected clip at {VLO} V, got {chip:.4f}"

    print("Scenario 4 — OFFSET shifts the operating point")
    o0, _ = run_linear(VREF, VREF, VREF, vos=0.0)
    ov, _ = run_linear(VREF, VREF, VREF, vos=10e-3)
    shift = ov - o0
    print(f"  vos=0.0   -> out={o0:.4f}")
    print(f"  vos=10 mV -> out={ov:.4f}   shift={shift:+.4f} V")
    assert abs(shift) > 1e-3, "offset should measurably shift the output"

    print("\nA1 OK: finite gain, input offset, and rail saturation are explicit "
          "and measured.")


if __name__ == "__main__":
    main()
