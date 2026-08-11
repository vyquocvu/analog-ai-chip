"""WP2.1 — 0011 converter variation: R-2R resistor mismatch (Monte Carlo).

Always-on tests validate the deterministic hand model (the closed-form 1-bit
anchor, the NumPy network solver, the statistics function and fail-closed
parameter checks). Engine-gated tests re-run the SPICE mismatch and check it
agrees with the hand solver and the committed extract.
"""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parent.parent
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "converter-variation-0011-extract.json"
_MODULE = _REPO / "book" / "0011-converter-variation" / "variation.py"


def _load():
    try:
        spec = importlib.util.spec_from_file_location("variation_0011", _MODULE)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:  # noqa: BLE001 - missing engine/lib => skip
        return None


mod = _load()

R = 1e4


def _zero_deltas():
    return np.zeros(mod.resistor_count())


def test_one_bit_anchor_closed_form() -> None:
    # always-on: Vout = VREF * a / (a + c) for the 1-bit ladder, code 1.
    # termination a and leg c both nominally 2R, so ideal Vout = VREF/2.
    d = np.array([0.0, 0.0, 0.0])
    assert mod.one_bit_anchor(d) == pytest.approx(mod.VREF / 2.0)
    d = np.array([0.0, 0.05, -0.05])  # a up 5%, c down 5%
    expected = mod.VREF * (2 * R * 1.05) / (2 * R * 1.05 + 2 * R * 0.95)
    assert mod.one_bit_anchor(d) == pytest.approx(expected)


def test_one_bit_anchor_rejects_wrong_shape() -> None:
    with pytest.raises(ValueError):
        mod.one_bit_anchor(np.zeros(4))


def test_hand_output_zero_mismatch_is_ideal() -> None:
    # always-on: the NumPy solver with zero mismatch reproduces Vout = code*LSB.
    for code in range(16):
        assert mod.hand_output(code, _zero_deltas()) == pytest.approx(
            code * mod.VREF / (2**mod.BITS), abs=1e-12
        )


def test_hand_output_1bit_matches_closed_form() -> None:
    d = np.array([0.0, 0.03, -0.02])
    assert mod.hand_output(1, d, bits=1) == pytest.approx(mod.one_bit_anchor(d), abs=1e-12)
    # series resistor b carries no load current in code 1, so it drops out:
    d2 = np.array([0.99, 0.03, -0.02])
    assert mod.hand_output(1, d2, bits=1) == pytest.approx(mod.one_bit_anchor(d2), abs=1e-12)


def test_deltas_validation_fails_closed() -> None:
    n = mod.resistor_count()
    with pytest.raises(ValueError):
        mod.hand_output(0, np.zeros(n - 1))
    with pytest.raises(ValueError):
        mod.hand_output(0, np.array([-1.5] * n))
    with pytest.raises(ValueError):
        mod.hand_output(0, np.array([np.nan] * n))
    with pytest.raises(ValueError):
        mod.mismatched_output(0, np.zeros(n), bits=0)


def test_draw_deltas_is_deterministic_and_shaped() -> None:
    a = mod.draw_deltas(32, 0.01, seed=7)
    b = mod.draw_deltas(32, 0.01, seed=7)
    assert np.array_equal(a, b)
    assert a.shape == (32, mod.resistor_count())
    assert np.allclose(np.mean(a, axis=0), 0.0, atol=4e-3)  # sampling error ~0.01/sqrt(32)
    assert np.std(a) == pytest.approx(0.01, abs=2e-3)
    with pytest.raises(ValueError):
        mod.draw_deltas(0, 0.01)
    with pytest.raises(ValueError):
        mod.draw_deltas(8, -0.1)


def test_mismatch_stats_shape_and_sanity() -> None:
    t = np.zeros((4, 16))
    stats = mod.mismatch_stats(t)
    assert stats["gain_error_mean"] == pytest.approx(-1.0)  # slope 0 => gain -1
    t2 = np.arange(16, dtype=float) * (mod.VREF / 16.0)
    t2 = np.tile(t2, (4, 1))
    stats2 = mod.mismatch_stats(t2)
    assert stats2["gain_error_mean"] == pytest.approx(0.0, abs=1e-12)
    assert stats2["max_inl_mean_v"] == pytest.approx(0.0, abs=1e-12)
    with pytest.raises(ValueError):
        mod.mismatch_stats(np.zeros((4, 15)))
    with pytest.raises(ValueError):
        mod.mismatch_stats(np.zeros((0, 16)))


@pytest.mark.skipif(mod is None, reason="PySpice/ngspice not available")
def test_spice_mismatch_matches_hand_solver() -> None:
    deltas = mod.draw_deltas(8)
    t_spice = mod.transfers_spice(deltas)
    t_hand = mod.transfers_hand(deltas)
    assert t_spice.shape == t_hand.shape == (8, 16)
    assert np.max(np.abs(t_spice - t_hand)) <= 1e-9


@pytest.mark.skipif(mod is None, reason="PySpice/ngspice not available")
def test_spice_zero_mismatch_is_ideal() -> None:
    nominal = mod.transfers_spice(np.zeros((1, mod.resistor_count())))
    ideal = np.array([code * mod.VREF / (2**mod.BITS) for code in range(16)])
    assert np.max(np.abs(nominal[0] - ideal)) <= 1e-9


@pytest.mark.skipif(mod is None, reason="PySpice/ngspice not available")
def test_extract_is_committed_and_reproducible() -> None:
    extract = json.loads(_EXTRACT.read_text("utf-8"))
    assert extract["bits"] == mod.BITS
    assert extract["seed"] == mod.SEED_DEFAULT
    assert extract["sigma"] == mod.SIGMA_DEFAULT
    assert extract["max_abs_deviation_v"] <= 1e-9
    assert len(extract["transfers_spice"]) == extract["n_samples"]
    assert len(extract["transfers_spice"][0]) == 16
    # statistics must reproduce deterministically
    deltas = mod.draw_deltas()
    t_spice = mod.transfers_spice(deltas)
    stats = mod.mismatch_stats(t_spice)
    for key in ("gain_error_mean", "gain_error_std", "max_inl_mean_v", "max_dnl_mean_v"):
        assert extract[key] == pytest.approx(stats[key], rel=1e-9)
