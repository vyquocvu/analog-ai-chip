"""0010 — SAR ADC for the TIA output path.

Always-on tests validate the hand reference, the differential-to-unipolar
mapping, and the fail-closed boundary behavior. Engine-gated tests check that
the SPICE comparator and SAR transfer reproduce the hand model.
"""

import importlib.util
import inspect
from pathlib import Path

import numpy as np
import pytest

_MODULE = Path(__file__).resolve().parent.parent / "book" / "0010-adc-sar" / "sar_adc.py"


def _load(path):
    try:
        spec = importlib.util.spec_from_file_location("sar_adc_" + path.stem, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:  # noqa: BLE001 - missing engine/lib => skip
        return None


mod = _load(_MODULE)


def test_reference_v_hand_model() -> None:
    # always-on: Vref(code) = code * VREF / 2^N
    assert mod.reference_v(0) == 0.0
    assert mod.reference_v(8) == pytest.approx(mod.VREF / 2)
    assert mod.reference_v(15) == pytest.approx(mod.VREF * 15 / 16)


def test_reference_v_rejects_out_of_range_code() -> None:
    with pytest.raises(ValueError):
        mod.reference_v(16)
    with pytest.raises(ValueError):
        mod.reference_v(-1)


def test_input_front_maps_envelope_onto_unipolar_range() -> None:
    # always-on: +/-VREF differential maps onto [0, VREF]
    assert mod.vin_from_differential(-mod.VREF) == pytest.approx(0.0)
    assert mod.vin_from_differential(mod.VREF) == pytest.approx(mod.VREF)
    assert mod.vin_from_differential(0.0) == pytest.approx(mod.VREF / 2)


def test_ideal_code_round_trip() -> None:
    # always-on: floor(Vin / LSB) clipped to [0, 2^N - 1]
    lsb = mod.VREF / (2**mod.BITS)
    assert mod.ideal_code(0.0) == 0
    assert mod.ideal_code(lsb) == 1
    assert mod.ideal_code(mod.VREF) == 2**mod.BITS - 1
    assert mod.ideal_code(1.0) == int(1.0 // lsb)


def test_ideal_code_clips_and_rejects_invalid() -> None:
    assert mod.ideal_code(100.0) == 2**mod.BITS - 1
    assert mod.ideal_code(-100.0) == 0
    with pytest.raises(ValueError):
        mod.ideal_code(float("nan"))
    with pytest.raises(ValueError):
        mod.ideal_code(float("inf"))


def test_reconstruction_error_bound() -> None:
    # always-on: |Vdiff_hat - Vdiff| <= diffLSB/2 over a fine grid.
    # The input front scales by 1/2, so one differential code spans 2*LSB and
    # the differential-domain error bound is LSB (VREF/2^N), not LSB/2.
    bound = mod.VREF / (2**mod.BITS)
    for vdiff in [v / 100 for v in range(-250, 251)]:
        v_in = mod.vin_from_differential(vdiff)
        code = mod.ideal_code(v_in)
        v_hat_diff = mod.vdiff_from_code(code)
        assert abs(v_hat_diff - vdiff) <= bound + 1e-12


def test_vdiff_from_code_hand_example() -> None:
    # always-on: the README worked example
    assert mod.vdiff_from_code(14) == pytest.approx(2 * (14.5 * mod.VREF / 16 - mod.VREF / 2))


@pytest.mark.skipif(mod is None, reason="PySpice/ngspice not available")
def test_spice_comparator_matches_hand() -> None:
    assert inspect.isfunction(mod.comparator_decision)
    for v_in, code in ((1.5, 8), (1.5, 9), (0.5, 3), (0.5, 4), (2.5, 15), (2.5, 16)):
        code = min(code, 2**mod.BITS - 1)
        hand = v_in >= mod.reference_v(code)
        assert mod.comparator_decision(v_in, code) == hand, (v_in, code)


@pytest.mark.skipif(mod is None, reason="PySpice/ngspice not available")
def test_spice_sar_transfer_reproduces_hand() -> None:
    rows = mod.transfer_sweep()
    assert len(rows) == 129
    for row in rows:
        assert row["code_spice"] == pytest.approx(row["code_hand"])


@pytest.mark.skipif(mod is None, reason="PySpice/ngspice not available")
def test_spice_sar_example() -> None:
    # README worked example: Vdiff = +2.0 V -> code 14
    v_in = mod.vin_from_differential(2.0)
    code = mod.sar_search(v_in)
    assert code == 14
    bound = mod.VREF / (2**mod.BITS)  # differential-domain error bound
    assert mod.vdiff_from_code(code) == pytest.approx(2.0, abs=bound)


@pytest.mark.skipif(mod is None, reason="PySpice/ngspice not available")
def test_spice_reference_settling_matches_hand() -> None:
    cl = 1e-12
    band = 0.5 * mod.LSB
    for code in (8, 4, 2, 1):
        ts = mod.reference_settle_time(0, code, band, cl)
        th = mod.reference_settle_time_hand(mod.reference_v(code), band, cl)
        assert ts == pytest.approx(th, abs=10e-9), f"settle 0->{code}"


@pytest.mark.skipif(mod is None, reason="PySpice/ngspice not available")
def test_spice_conversion_time_matches_hand() -> None:
    t_spice, t_hand = mod.conversion_time(1e-12)
    assert t_spice == pytest.approx(t_hand, abs=40e-9)
    assert 100e-9 < t_spice < 200e-9  # 4 trials, CL = 1 pF


def test_conversion_time_hand_is_deterministic_sum() -> None:
    # always-on: the hand sum is tau*ln(dV/band) over each bit trial
    cl, r, band_frac = 1e-12, mod.R_OHM, 0.5
    band = band_frac * mod.LSB
    tau = 2 * r * cl
    expected = sum(
        tau * np.log(mod.VREF / (2.0 ** (mod.BITS - i)) / band)
        for i in range(mod.BITS - 1, -1, -1)
    )
    _, hand = mod.conversion_time(cl)
    assert hand == pytest.approx(expected)
