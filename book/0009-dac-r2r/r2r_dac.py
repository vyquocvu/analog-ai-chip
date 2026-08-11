"""Chapter 0009 — R-2R ladder DAC (SPICE).

The first physically-motivated DAC design candidate for the converter signal
path (R2). A binary-weighted **R-2R ladder** turns a digital code into a
voltage using only two resistor values, `R` and `2R`:

    n0 --R-- n1 --R-- ... --R-- nN        (series chain)
    |         |              |
   2R        2R              2R           (each node: 2R leg to a bit switch)
    |         |              |
   GND      sw(bit0)        sw(bit_{N-1})
    ^
    2R termination to ground at the LSB end

Bit `i` connects its `2R` leg to `VREF` (bit = 1) or ground (bit = 0). The
ladder's exponential current division makes the unloaded output

    Vout(code) = VREF * code / 2^N ,   code = sum bit_i * 2^i

with `Vout(0) = 0` and full scale `VREF*(2^N - 1)/2^N`. Only `R` and `2R`
appear, so the gain, offset and range are set by resistor ratios plus `VREF`
-- no exotic components. Real silicon would add switch resistance, mismatch and
settling; those are deferred to later converter chapters.

The netlist uses ideal voltage sources for the bit switches (0 V or VREF), which
is the DC operating-point model of a perfect switch. All solves are ngspice DC
operating points; transient settling is a separate study.
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

BITS = 4               # prototype ladder width
VREF = 2.5             # reference voltage (V)
R_OHM = 10.0e3         # ladder unit resistor R (ohm); 2R = 20 kOhm


def ideal_output(code: int, bits: int = BITS, vref: float = VREF) -> float:
    """Hand reference: Vout = VREF * code / 2^bits."""
    if not 0 <= int(code) < 2**bits:
        raise ValueError(f"code {code} out of range for {bits} bits")
    return vref * int(code) / (2**bits)


def ladder_output(
    code: int, bits: int = BITS, vref: float = VREF, r_ohm: float = R_OHM
) -> float:
    """SPICE output voltage for ``code`` on the R-2R ladder (unloaded)."""
    if not 0 <= int(code) < 2**bits:
        raise ValueError(f"code {code} out of range for {bits} bits")

    c = Circuit("dac_r2r_0009")
    c.V("vref", "vref", c.gnd, vref @ u_V)
    nodes = [f"n{i}" for i in range(bits + 1)]  # n0 (LSB end) .. nN (output)
    for i in range(bits):
        c.R(f"s{i}", nodes[i], nodes[i + 1], (r_ohm / 1e3) @ u_kOhm)
    c.R("term", nodes[0], c.gnd, (2 * r_ohm / 1e3) @ u_kOhm)
    for i in range(bits):
        bit = (int(code) >> i) & 1
        sw = vref if bit else 0.0
        c.V(f"sw{i}", f"sw{i}", c.gnd, sw @ u_V)
        c.R(f"l{i}", nodes[i], f"sw{i}", (2 * r_ohm / 1e3) @ u_kOhm)
    a = c.simulator().operating_point()
    return float(np.ravel(np.asarray(a[nodes[bits]]))[0])


def sweep(bits: int = BITS, vref: float = VREF, r_ohm: float = R_OHM) -> list[float]:
    """SPICE outputs for every code of an ``bits``-bit ladder, in code order."""
    return [ladder_output(code, bits, vref, r_ohm) for code in range(2**bits)]


def main() -> None:
    print(f"R-2R ladder DAC, {BITS} bits, VREF = {VREF} V, R = {R_OHM/1e3:.0f} kOhm")
    print(f"{'code':>4} {'spice (V)':>10} {'ideal (V)':>10} {'err (V)':>10}")
    worst = 0.0
    for code in range(2**BITS):
        v = ladder_output(code)
        ideal = ideal_output(code)
        err = abs(v - ideal)
        worst = max(worst, err)
        print(f"{code:4d} {v:10.6f} {ideal:10.6f} {err:10.2e}")
    print(f"worst |spice - ideal| = {worst:.2e} V")
    assert worst <= 1e-9, f"R-2R ladder must match hand reference, worst err {worst}"
    print("OK")


if __name__ == "__main__":
    main()