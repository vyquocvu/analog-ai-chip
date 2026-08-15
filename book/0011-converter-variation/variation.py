"""Chapter 0011 — converter variation: R-2R resistor mismatch (Monte Carlo).

The 0009/0010 chapters verified the *nominal* R-2R ladder against the hand
reference ``Vout = VREF*code/2^N``. Real silicon resistors are not exact: each
resistor carries a relative mismatch ``delta ~ N(0, sigma)``. This chapter
measures how mismatch propagates into the converter transfer as gain error,
INL and DNL, and proves the SPICE Monte Carlo against an independent hand
reference.

Two solvers, one set of deterministic draws
--------------------------------------------
A fixed random seed draws one set of relative mismatch vectors (one entry per
ladder resistor). Each vector drives BOTH solvers:

* **SPICE** (``mismatched_output``): a copy of the 0009 ladder netlist whose
  resistor values are ``nominal * (1 + delta)``, solved with ngspice.
* **hand** (``hand_output``): the same resistive network solved directly as a
  conductance matrix ``G V = b`` in NumPy. The bit switches are ideal sources
  (``VREF`` or ``0``), exactly as in the SPICE netlist.

Because the network is linear, both solvers must return identical voltages for
every (code, sample) pair -- that equality is the chapter's core assertion: the
SPICE mismatched ladder and the hand model agree to machine precision, so the
Monte Carlo statistics computed from SPICE transfers are trustworthy.

Monte Carlo statistics
----------------------
Per sample, over all ``2^N`` codes, measured from the endpoint-fit line:

  * offset (``Vout(0)``),
  * gain error (endpoint slope / ideal LSB - 1),
  * INL(code) = ``Vout - line``, DNL(code) = step - ideal LSB.

Reported as means/std across samples. For ``sigma = 0`` the study reproduces
the ideal ladder (fail-closed sanity check).

Tiny hand-computable anchor
---------------------------
For a 1-bit ladder (one series R ``b``, termination ``a``, leg ``c``) with
code 1 the exact output is ``Vout = VREF * a / (a + c)``: node ``n0`` sits at
``Vout`` and KCL at ``n0`` gives ``Vout(1/c + 1/a) = VREF/c``. This closed
form is asserted in ``tests`` as the anchor for the whole mismatch model.
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


BITS = 4                 # prototype ladder width (matches 0009)
VREF = 2.5               # reference voltage (V)
R_OHM = 10.0e3           # ladder unit resistor R (ohm); 2R = 20 kOhm
SIGMA_DEFAULT = 0.01     # relative resistor mismatch (1%)
N_SAMPLES_DEFAULT = 64   # Monte Carlo sample count (deterministic seed)
SEED_DEFAULT = 7


def resistor_count(bits: int = BITS) -> int:
    """Number of resistors in the ladder: bits series + 1 termination + bits legs."""
    return 2 * bits + 1


def _check_params(bits: int, r_ohm: float, vref: float, deltas) -> np.ndarray:
    if int(bits) != bits or bits < 1:
        raise ValueError(f"bits must be an integer >= 1, got {bits}")
    if r_ohm <= 0 or vref <= 0:
        raise ValueError("r_ohm and vref must be positive")
    d = np.asarray(deltas, dtype=float)
    if d.ndim != 1 or d.shape[0] != resistor_count(bits):
        raise ValueError(
            f"deltas must be a 1-D array of {resistor_count(bits)} relative "
            f"mismatch values, got shape {d.shape}"
        )
    if np.any(d <= -1.0):
        raise ValueError("deltas must be > -1 (resistor values stay positive)")
    if not np.all(np.isfinite(d)):
        raise ValueError("deltas must be finite")
    return d


def _mismatched_netlist(code: int, deltas, bits: int = BITS,
                        r_ohm: float = R_OHM, vref: float = VREF) -> Circuit:
    """0009 R-2R ladder with per-resistor mismatch: R_i = nominal*(1 + delta).

    Delta ordering (matches ``hand_output``): indices ``0..bits-1`` are the
    series ``R`` resistors, index ``bits`` is the ``2R`` termination, indices
    ``bits+1..2*bits`` are the ``2R`` bit-switch legs.
    """
    d = _check_params(bits, r_ohm, vref, deltas)
    if not 0 <= int(code) < 2**bits:
        raise ValueError(f"code {code} out of range for {bits} bits")

    _require_pyspice()
    c = Circuit("dac_r2r_variation_0011")
    c.V("vref", "vref", c.gnd, vref @ u_V)
    nodes = [f"n{i}" for i in range(bits)]
    out = "out"
    for i in range(bits):
        nxt = out if i == bits - 1 else nodes[i + 1]
        c.R(f"s{i}", nodes[i], nxt, (r_ohm * (1.0 + d[i]) / 1e3) @ u_kOhm)
    c.R("term", nodes[0], c.gnd, (2 * r_ohm * (1.0 + d[bits]) / 1e3) @ u_kOhm)
    for i in range(bits):
        to_bit = (int(code) >> i) & 1
        c.V(f"sw{i}", f"sw{i}", c.gnd, (vref if to_bit else 0.0) @ u_V)
        c.R(f"l{i}", nodes[i], f"sw{i}", (2 * r_ohm * (1.0 + d[bits + 1 + i]) / 1e3) @ u_kOhm)
    return c


def mismatched_output(code: int, deltas, bits: int = BITS,
                      r_ohm: float = R_OHM, vref: float = VREF) -> float:
    """SPICE output voltage for ``code`` on the mismatched ladder."""
    a = _mismatched_netlist(code, deltas, bits, r_ohm, vref).simulator().operating_point()
    return float(np.ravel(np.asarray(a["out"]))[0])


def hand_output(code: int, deltas, bits: int = BITS,
                r_ohm: float = R_OHM, vref: float = VREF) -> float:
    """Hand reference: solve the same resistive network as ``G V = b`` in NumPy.

    Free nodes are ``n0..n_{bits-1}`` plus ``out``. Bit switches are ideal
    sources ``VREF`` (bit=1) or ``0`` (bit=0) into each ``2R`` leg, identical
    to the SPICE netlist. Returns the ``out`` node voltage.
    """
    d = _check_params(bits, r_ohm, vref, deltas)
    if not 0 <= int(code) < 2**bits:
        raise ValueError(f"code {code} out of range for {bits} bits")

    nfree = bits + 1  # n0..n_{bits-1}, out
    out_idx = bits
    g = np.zeros((nfree, nfree))
    b = np.zeros(nfree)

    for i in range(bits):
        # series R between nodes[i] and (out if last else nodes[i+1])
        gser = 1.0 / (r_ohm * (1.0 + d[i]))
        a, c = i, out_idx if i == bits - 1 else i + 1
        g[a, a] += gser
        g[c, c] += gser
        g[a, c] -= gser
        g[c, a] -= gser
    # 2R termination from n0 to ground
    g[0, 0] += 1.0 / (2 * r_ohm * (1.0 + d[bits]))
    # 2R legs from nodes[i] to the bit-switch source
    for i in range(bits):
        gle = 1.0 / (2 * r_ohm * (1.0 + d[bits + 1 + i]))
        g[i, i] += gle
        if (int(code) >> i) & 1:
            b[i] += gle * vref

    v = np.linalg.solve(g, b)
    return float(v[out_idx])


def draw_deltas(n_samples: int = N_SAMPLES_DEFAULT, sigma: float = SIGMA_DEFAULT,
                seed: int = SEED_DEFAULT, bits: int = BITS) -> np.ndarray:
    """Deterministic mismatch draws, shape ``(n_samples, resistor_count)``."""
    if int(n_samples) != n_samples or n_samples <= 0:
        raise ValueError("n_samples must be a positive integer")
    if sigma < 0:
        raise ValueError("sigma must be non-negative")
    rng = np.random.default_rng(seed)
    return rng.normal(0.0, sigma, size=(int(n_samples), resistor_count(bits)))


def _sweep(solver, deltas, bits: int, r_ohm: float, vref: float) -> np.ndarray:
    return np.array([solver(code, deltas, bits, r_ohm, vref) for code in range(2**bits)])


def transfers_spice(deltas: np.ndarray, bits: int = BITS,
                    r_ohm: float = R_OHM, vref: float = VREF) -> np.ndarray:
    """SPICE Monte Carlo: ``(n_samples, 2^bits)`` transfer for every draw."""
    return np.array([_sweep(mismatched_output, d, bits, r_ohm, vref) for d in deltas])


def transfers_hand(deltas: np.ndarray, bits: int = BITS,
                   r_ohm: float = R_OHM, vref: float = VREF) -> np.ndarray:
    """Hand Monte Carlo: same draws through the NumPy network solver."""
    return np.array([_sweep(hand_output, d, bits, r_ohm, vref) for d in deltas])


def mismatch_stats(transfers: np.ndarray, bits: int = BITS,
                   vref: float = VREF) -> dict[str, float]:
    """Monte Carlo statistics from a ``(n_samples, 2^bits)`` transfer matrix.

    Per sample: offset ``Vout(0)``; endpoint-fit gain error
    ``(slope/LSB - 1)``; INL = ``Vout - line``; DNL = step - ideal LSB.
    Reported as mean/std across samples plus worst-case max values.
    """
    t = np.asarray(transfers, dtype=float)
    if t.ndim != 2 or t.shape[1] != 2**bits:
        raise ValueError(f"expected shape (n_samples, {2**bits}), got {t.shape}")
    if t.shape[0] == 0:
        raise ValueError("transfers must contain at least one sample")

    lsb = vref / (2**bits)
    offset = t[:, 0]
    slope = (t[:, -1] - t[:, 0]) / (2**bits - 1)
    gain_error = slope / lsb - 1.0
    line = t[:, 0, None] + slope[:, None] * np.arange(2**bits)
    inl = t - line
    dnl = np.diff(t, axis=1) - lsb
    return {
        "offset_mean_v": float(np.mean(offset)),
        "offset_std_v": float(np.std(offset)),
        "gain_error_mean": float(np.mean(gain_error)),
        "gain_error_std": float(np.std(gain_error)),
        "max_inl_mean_v": float(np.mean(np.max(np.abs(inl), axis=1))),
        "max_inl_std_v": float(np.std(np.max(np.abs(inl), axis=1))),
        "max_dnl_mean_v": float(np.mean(np.max(np.abs(dnl), axis=1))),
        "max_dnl_std_v": float(np.std(np.max(np.abs(dnl), axis=1))),
    }


def one_bit_anchor(deltas, vref: float = VREF) -> float:
    """Tiny hand-computable case: 1-bit ladder output for code 1.

    With series ``b``, termination ``a``, leg ``c`` the exact result is
    ``Vout = VREF * a / (a + c)`` (KCL at ``n0`` with ``Vout = Vn0``).
    """
    d = np.asarray(deltas, dtype=float)
    if d.shape != (3,):
        raise ValueError("one_bit_anchor expects the 3 resistor deltas of a 1-bit ladder")
    a = 2 * R_OHM * (1.0 + d[1])   # termination
    c = 2 * R_OHM * (1.0 + d[2])   # leg
    return vref * a / (a + c)


def main() -> None:
    print(f"0011 converter variation: R-2R mismatch, {BITS} bits, VREF = {VREF} V, "
          f"sigma = {SIGMA_DEFAULT}, seed = {SEED_DEFAULT}")
    deltas = draw_deltas()
    print(f"  {len(deltas)} draws x {resistor_count(BITS)} resistors "
          f"({len(deltas)*resistor_count(BITS)} values), deterministic")

    t_spice = transfers_spice(deltas)
    t_hand = transfers_hand(deltas)
    max_dev = float(np.max(np.abs(t_spice - t_hand)))
    print(f"  max |spice - hand| over {t_spice.size} (sample, code) pairs = {max_dev:.2e} V")
    assert max_dev <= 1e-9, "SPICE mismatched ladder must match the NumPy network solver"

    stats = mismatch_stats(t_spice)
    hand_stats = mismatch_stats(t_hand)
    print(f"  offset  mean {stats['offset_mean_v']:+.2e} V, "
          f"std {stats['offset_std_v']:.2e} V")
    print(f"  gain    mean {stats['gain_error_mean']:+.2e}, "
          f"std {stats['gain_error_std']:.2e}")
    print(f"  max|INL|  mean {stats['max_inl_mean_v']:.2e} V, "
          f"std {stats['max_inl_std_v']:.2e} V")
    print(f"  max|DNL|  mean {stats['max_dnl_mean_v']:.2e} V, "
          f"std {stats['max_dnl_std_v']:.2e} V")
    for key in stats:
        assert abs(stats[key] - hand_stats[key]) <= max(1e-6 * abs(hand_stats[key]), 1e-12), key

    nominal = transfers_spice(np.zeros((1, resistor_count(BITS))))
    assert float(np.max(np.abs(nominal[0] - np.array(
        [code * VREF / (2**BITS) for code in range(2**BITS)])))) <= 1e-9, (
        "sigma=0 must reproduce the ideal ladder"
    )

    print("\n  one-bit anchor: Vout = VREF * a / (a + c)")
    d1 = deltas[0][:3]
    spice = mismatched_output(1, d1, bits=1)
    hand = hand_output(1, d1, bits=1)
    closed = one_bit_anchor(d1)
    print(f"    deltas = {np.round(d1, 4).tolist()}")
    print(f"    spice  = {spice:.6f} V, hand = {hand:.6f} V, "
          f"closed form = {closed:.6f} V")
    assert abs(spice - hand) <= 1e-9
    assert abs(spice - closed) <= 1e-9
    print("OK")


if __name__ == "__main__":
    main()
