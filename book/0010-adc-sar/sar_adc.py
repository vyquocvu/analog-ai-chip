"""Chapter 0010 — SAR ADC for the TIA output path (SPICE).

The first ADC design candidate for the converter signal path (R2). The 0007
differential crossbar column produces a *differential* output

    Vout = Vm - Vp = RF * GSCALE * sum_i (x_i - VREF) * w_i

with an envelope of +/- 2.5 V around the virtual reference (the crossbar-column
profile headroom). The ADC must digitize this signed, reference-relative signal
into the code space the simulator's functional ``converters.adc`` consumes.

Architecture
------------
A **successive-approximation register (SAR)** converter built from:

  * the R-2R reference ladder of chapter 0009 (unipolar 0 .. VREF),
  * one ideal comparator (VCVS gain 1e4, the same ideal-opamp idealization
    chapter 0007 uses for its transimpedance stages),
  * a differential-to-single-ended input front: ``Vin = VREF/2 + Vdiff/2`` so
    the signed +/-2.5 V envelope maps onto the ladder's unipolar [0, VREF] range.

Transfer (hand reference)
-------------------------
    code     = floor(Vin / LSB),            clipped to [0, 2^N - 1]
    V_hat    = (code + 0.5) * LSB            (mid-rise reconstruction)
    LSB      = VREF / 2^N

The SAR search itself is a deterministic algorithm (a comparator decision per
bit); the *circuit* evidence is that each comparator decision - the R-2R
reference ladder node voltage versus the level-shifted input - reproduces the
hand comparison ``Vin >= Vref(code)`` in SPICE. The search logic is functional,
the reference and comparator are circuit-level; the boundary is stated in the
README so the two never get conflated.
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

BITS = 4               # prototype ADC width (matches 0009 ladder)
VREF = 2.5             # reference voltage (V); matches 0005/0007/0009
R_OHM = 10.0e3         # R-2R reference ladder unit resistor (ohm)
LSB = VREF / (2**BITS)  # voltage per code


def reference_v(code: int, bits: int = BITS, vref: float = VREF) -> float:
    """Hand reference: R-2R ladder output voltage ``Vref = code * LSB``."""
    if not 0 <= int(code) < 2**bits:
        raise ValueError(f"code {code} out of range for {bits} bits")
    return vref * int(code) / (2**bits)


def vin_from_differential(vdiff: float, vref: float = VREF) -> float:
    """Level-shift the signed differential output into the ladder's [0, VREF]."""
    return vref / 2.0 + vdiff / 2.0


def vdiff_from_code(code: int, bits: int = BITS, vref: float = VREF) -> float:
    """Differential-domain reconstruction ``Vdiff_hat`` from an ADC code."""
    if not 0 <= int(code) < 2**bits:
        raise ValueError(f"code {code} out of range for {bits} bits")
    return 2.0 * ((int(code) + 0.5) * (vref / (2**bits)) - vref / 2.0)


def ideal_code(v_in: float, bits: int = BITS, vref: float = VREF) -> int:
    """Hand reference: ``floor(Vin / LSB)`` clipped to the code range."""
    if not np.isfinite(v_in):
        raise ValueError(f"v_in must be finite, got {v_in}")
    lsb = vref / (2**bits)
    return int(np.clip(np.floor(v_in / lsb), 0, 2**bits - 1))


def _reference_netlist(code: int, bits: int = BITS, r_ohm: float = R_OHM,
                       vref: float = VREF) -> Circuit:
    """R-2R reference ladder (0009 topology); ladder output node is ``ref``."""
    c = Circuit("adc_sar_0010")
    c.V("vref", "vref", c.gnd, vref @ u_V)
    nodes = [f"n{i}" for i in range(bits)]
    for i in range(bits):
        nxt = "ref" if i == bits - 1 else nodes[i + 1]
        c.R(f"s{i}", nodes[i], nxt, (r_ohm / 1e3) @ u_kOhm)
    c.R("term", nodes[0], c.gnd, (2 * r_ohm / 1e3) @ u_kOhm)
    for i in range(bits):
        bit = (int(code) >> i) & 1
        c.V(f"sw{i}", f"sw{i}", c.gnd, (vref if bit else 0.0) @ u_V)
        c.R(f"l{i}", nodes[i], f"sw{i}", (2 * r_ohm / 1e3) @ u_kOhm)
    return c


def comparator_decision(v_in: float, code: int, bits: int = BITS,
                        r_ohm: float = R_OHM, vref: float = VREF) -> bool:
    """SPICE comparator: is ``Vin >= Vref(code)``?

    The comparator is a VCVS of gain 1e4 (the chapter-0007 ideal-opamp model):
    ``out = 1e4 * (V(vin) - V(ref))``. A non-negative output is the '1'
    decision. This is the circuit-level evidence for the ADC transfer.
    """
    c = _reference_netlist(code, bits, r_ohm, vref)
    c.V("vin", "vin", c.gnd, v_in @ u_V)
    c.VCVS("cmp", "out", c.gnd, "vin", "ref", 1e4)
    a = c.simulator().operating_point()
    return float(np.ravel(np.asarray(a["out"]))[0]) >= 0.0


def sar_search(v_in: float, bits: int = BITS, r_ohm: float = R_OHM,
               vref: float = VREF) -> int:
    """Successive-approximation code using SPICE comparator decisions.

    Standard MSB-first search: try each bit high, keep it only if the SPICE
    comparator reports ``Vin >= Vref(trial)``. The search is functional logic;
    the decisions are circuit solves.
    """
    if not np.isfinite(v_in):
        raise ValueError(f"v_in must be finite, got {v_in}")
    code = 0
    for i in range(bits - 1, -1, -1):
        trial = code | (1 << i)
        if comparator_decision(v_in, trial, bits, r_ohm, vref):
            code = trial
    return code


def quantize(v_in: float, bits: int = BITS, r_ohm: float = R_OHM,
             vref: float = VREF) -> tuple[int, float]:
    """Full conversion: code and mid-rise reconstruction (unipolar V_hat)."""
    code = sar_search(v_in, bits, r_ohm, vref)
    return code, (code + 0.5) * (vref / (2**bits))


def transfer_sweep(bits: int = BITS, r_ohm: float = R_OHM,
                   vref: float = VREF, n_samples: int = 129) -> list[dict[str, float]]:
    """SPICE transfer curve: SAR code vs hand ``ideal_code`` over the envelope."""
    rows = []
    for v_in in np.linspace(0.0, vref, n_samples):
        code = sar_search(v_in, bits, r_ohm, vref)
        rows.append({
            "v_in_v": float(v_in),
            "code_spice": float(code),
            "code_hand": float(ideal_code(v_in, bits, vref)),
        })
    return rows


def main() -> None:
    print(f"SAR ADC, {BITS} bits, VREF = {VREF} V, R = {R_OHM/1e3:.0f} kOhm, "
          f"LSB = {LSB:.6f} V")
    vdiff = 2.0
    v_in = vin_from_differential(vdiff)
    code = sar_search(v_in)
    v_hat_diff = vdiff_from_code(code)
    print(f"Vdiff = {vdiff:+.3f} V  ->  Vin = {v_in:.4f} V  ->  code {code}")
    print(f"  Vdiff_hat = {v_hat_diff:+.4f} V   (err {abs(vdiff - v_hat_diff):.4f} V "
          f"<= LSB = {LSB:.5f} V in the differential domain)")

    print("\nSPICE comparator vs hand comparison, representative trials:")
    for v_in, code in ((1.5, 8), (1.5, 9), (0.5, 3), (0.5, 4)):
        hand = v_in >= reference_v(code)
        spice = comparator_decision(v_in, code)
        print(f"  Vin={v_in:.2f} V  code={code:2d}  hand {hand}  spice {spice}")
        assert spice == hand, f"comparator must match hand for Vin={v_in}, code={code}"

    rows = transfer_sweep()
    worst = max(abs(r["code_spice"] - r["code_hand"]) for r in rows)
    print(f"\ntransfer sweep: {len(rows)} samples, "
          f"worst |code_spice - code_hand| = {worst:.0f}")
    assert worst <= 0, "SPICE SAR must reproduce the hand transfer code-for-code"
    print("OK")


if __name__ == "__main__":
    main()
