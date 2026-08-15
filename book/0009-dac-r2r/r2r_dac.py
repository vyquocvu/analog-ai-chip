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
    from PySpice.Unit import u_kOhm, u_ns, u_pF, u_uA, u_V

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


BITS = 4               # prototype ladder width
VREF = 2.5             # reference voltage (V)
R_OHM = 10.0e3         # ladder unit resistor R (ohm); 2R = 20 kOhm


def ideal_output(code: int, bits: int = BITS, vref: float = VREF) -> float:
    """Hand reference: Vout = VREF * code / 2^bits."""
    if not 0 <= int(code) < 2**bits:
        raise ValueError(f"code {code} out of range for {bits} bits")
    return vref * int(code) / (2**bits)


def _ladder_netlist(
    code: int,
    bits: int = BITS,
    r_ohm: float = R_OHM,
    vref: float = VREF,
    *,
    cl_farad: float | None = None,
    from_code: int | None = None,
) -> Circuit:
    """Build the R-2R ladder netlist; output node is named ``out``.

    Bit switches are ideal voltage sources (0 V or VREF) for a DC solve. With
    ``from_code`` set, each switch is a pulse source stepping from the
    ``from_code`` bit value to the ``code`` bit value (0.1 ns edges, held high
    for the whole 1 ms window) so a transient solve can measure settling;
    ``dc_offset`` is set to the ``from_code`` value so the operating point (and
    thus the transient t=0 state) starts at the initial code.
    ``cl_farad`` adds the assumed load capacitance on the output node.
    """
    _require_pyspice()
    c = Circuit("dac_r2r_0009")
    c.V("vref", "vref", c.gnd, vref @ u_V)
    nodes = [f"n{i}" for i in range(bits)]  # n0 (LSB end) .. n{b-1}
    out = "out"
    for i in range(bits):
        nxt = out if i == bits - 1 else nodes[i + 1]
        c.R(f"s{i}", nodes[i], nxt, (r_ohm / 1e3) @ u_kOhm)
    c.R("term", nodes[0], c.gnd, (2 * r_ohm / 1e3) @ u_kOhm)
    if cl_farad is not None:
        c.C("load", out, c.gnd, (cl_farad / 1e-12) @ u_pF)
    for i in range(bits):
        to_bit = (int(code) >> i) & 1
        if from_code is None:
            c.V(f"sw{i}", f"sw{i}", c.gnd, (vref if to_bit else 0.0) @ u_V)
        else:
            from_bit = (int(from_code) >> i) & 1
            from_v = vref if from_bit else 0.0
            c.PulseVoltageSource(
                f"sw{i}",
                f"sw{i}",
                c.gnd,
                initial_value=from_v @ u_V,
                pulsed_value=(vref if to_bit else 0.0) @ u_V,
                delay_time=0 @ u_ns,
                rise_time=0.1 @ u_ns,
                fall_time=0.1 @ u_ns,
                pulse_width=1e6 @ u_ns,
                period=2e6 @ u_ns,
                dc_offset=from_v @ u_V,
            )
        c.R(f"l{i}", nodes[i], f"sw{i}", (2 * r_ohm / 1e3) @ u_kOhm)
    return c


def ladder_output(
    code: int, bits: int = BITS, vref: float = VREF, r_ohm: float = R_OHM
) -> float:
    """SPICE output voltage for ``code`` on the R-2R ladder (unloaded)."""
    if not 0 <= int(code) < 2**bits:
        raise ValueError(f"code {code} out of range for {bits} bits")
    a = _ladder_netlist(code, bits, r_ohm, vref).simulator().operating_point()
    return float(np.ravel(np.asarray(a["out"]))[0])


def sweep(bits: int = BITS, vref: float = VREF, r_ohm: float = R_OHM) -> list[float]:
    """SPICE outputs for every code of an ``bits``-bit ladder, in code order."""
    return [ladder_output(code, bits, vref, r_ohm) for code in range(2**bits)]


def output_resistance_ohm(
    code: int, bits: int = BITS, r_ohm: float = R_OHM, vref: float = VREF
) -> float:
    """Thevenin output resistance of the ladder seen at the output node.

    Measured by a two-point DC load line (1 uA and 20 uA pulled from the
    output) and independent of ``code``. For this ladder orientation
    (termination at the LSB end, output at the MSB end) the recursion gives
    ``Rth = R + Z`` with ``Z = 2R || (R + Z)``, i.e. ``Rth = 2R``.
    """
    vs = []
    for i_ua in (1.0, 20.0):
        c2 = _ladder_netlist(code, bits, r_ohm, vref)
        c2.I("load", "out", c2.gnd, i_ua @ u_uA)
        a = c2.simulator().operating_point()
        vs.append(float(np.ravel(np.asarray(a["out"]))[0]))
    return abs((vs[0] - vs[1]) / (1e-6 - 20e-6))


def settle_time(
    code_from: int,
    code_to: int,
    band_v: float,
    cl_farad: float,
    bits: int = BITS,
    r_ohm: float = R_OHM,
    vref: float = VREF,
    *,
    t_end_ns: float = 500.0,
) -> float:
    """SPICE settling time (s) for a code step ``code_from`` -> ``code_to``.

    ``cl_farad`` is the assumed output load capacitance (ADC input / parasitics,
    no device evidence yet — sensitivity parameter). ``band_v`` is the settling
    tolerance band around the final value. Returns the first time after which
    the output stays within ``+/- band_v`` of its final value.
    """
    if not 0 <= int(code_from) < 2**bits or not 0 <= int(code_to) < 2**bits:
        raise ValueError("code out of range")

    c = _ladder_netlist(code_to, bits, r_ohm, cl_farad=cl_farad, from_code=code_from)
    a = c.simulator().transient(step_time=(1 @ u_ns), end_time=(t_end_ns @ u_ns))
    t = np.asarray(a.time) * 1e9  # ns
    v = np.asarray(a["out"])
    final = ideal_output(code_to, bits, vref)
    ok = np.abs(v - final) <= band_v
    for i in range(len(t)):
        if np.all(ok[i:]):
            return float(t[i]) * 1e-9
    return float("nan")


def settle_time_hand(
    code_from: int,
    code_to: int,
    band_v: float,
    cl_farad: float,
    r_ohm: float = R_OHM,
    vref: float = VREF,
) -> float:
    """Hand reference: single-pole settle ``tau * ln(dV/band)``, tau = 2R*CL."""
    dv = abs(ideal_output(code_to, vref=vref) - ideal_output(code_from, vref=vref))
    tau = 2.0 * r_ohm * cl_farad
    return tau * np.log(dv / band_v)


def supply_sensitivity(
    bits: int = BITS,
    vref: float = VREF,
    r_ohm: float = R_OHM,
    deviations: tuple[float, ...] = (-0.10, -0.05, 0.0, 0.05, 0.10),
) -> list[dict[str, float]]:
    """VREF supply sensitivity: does a VREF shift translate into gain error?

    The ladder is ratio-based -- the output depends only on resistor ratios
    and ``VREF`` -- so the transfer scales linearly with the reference:

        Vout(code, VREF') = VREF' * code / 2^N,   VREF' = VREF * (1 + dev)

    Offset stays exactly 0 (code 0 grounds every leg) and the full-scale and
    LSB scale with VREF, i.e. a *pure gain error* ``gain_error = dVREF/VREF``.
    Each row sweeps the full transfer at the deviated VREF in SPICE and checks
    it against the hand model ``ideal_output`` at that VREF. Temperature and
    process corner have no effect on the ideal resistor/switch model by
    construction -- documented, not swept as fake evidence.

    Reported in the extract JSON only: a supply deviation on an ideal model is
    a design condition, not new device evidence, so it is not a profile field
    (it stays out of the fail-closed ``physical_claim`` path).
    """
    _require_pyspice()
    nominal = vref / (2**bits)
    rows = []
    for dev in deviations:
        vs = vref * (1.0 + dev)
        volts = sweep(bits, vs, r_ohm)
        lsb = (volts[-1] - volts[0]) / (2**bits - 1)
        max_abs_err = max(
            abs(v - ideal_output(code, bits, vs)) for code, v in enumerate(volts)
        )
        rows.append({
            "deviation": float(dev),
            "vref_v": float(vs),
            "offset_v": float(volts[0]),
            "full_scale_v": float(volts[-1]),
            "lsb_v": float(lsb),
            "gain_error": float((lsb - nominal) / nominal),
            "gain_error_hand": float(dev),
            "max_abs_error_v": float(max_abs_err),
        })
    return rows


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

    print("\noutput resistance Rth (two-point DC load line)")
    for code in (0, 1, 8, 15):
        rth = output_resistance_ohm(code)
        print(f"  code={code:2d}  Rth = {rth:.0f} ohm (2R = {2*R_OHM:.0f})")
        assert abs(rth - 2 * R_OHM) / (2 * R_OHM) < 1e-6, "Rth must equal 2R"

    print("\ntransient settling (assumed load CL = 1 pF, band = 0.5 LSB)")
    cl = 1e-12
    band = VREF / (2 ** (BITS + 1))
    for code_from, code_to in ((0, 8), (8, 15), (0, 15)):
        ts = settle_time(code_from, code_to, band, cl)
        th = settle_time_hand(code_from, code_to, band, cl)
        print(
            f"  {code_from}->{code_to}: spice = {ts*1e9:6.1f} ns, "
            f"hand tau*ln(dV/band) = {th*1e9:6.1f} ns"
        )
        assert abs(ts - th) <= 10e-9, "transient settle must match single-pole hand"

    print("\nVREF supply sensitivity (pure gain error on a ratio ladder):")
    for row in supply_sensitivity():
        print(f"  dVREF/VREF = {row['gain_error_hand']:+.0%}  "
              f"gain_err = {row['gain_error']:+.2e}  "
              f"offset = {row['offset_v']:.1e} V  "
              f"max_abs_err = {row['max_abs_error_v']:.2e} V")
        assert abs(row["gain_error"] - row["gain_error_hand"]) <= 1e-9, (
            f"gain error must equal dVREF/VREF for VREF = {row['vref_v']}"
        )
        assert row["offset_v"] == 0.0, "offset must stay zero under VREF deviation"
        assert row["max_abs_error_v"] <= 1e-9, (
            "deviated transfer must match the hand model VREF'*code/2^N"
        )
    print("OK")


if __name__ == "__main__":
    main()