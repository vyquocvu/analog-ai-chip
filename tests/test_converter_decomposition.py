"""WP2.1 — 0011 converter variation: separating error mechanisms.

Always-on tests validate the deterministic decomposition math: the DAC
endpoint-fit split is exact, the ADC error power separates into quantization +
noise, and fail-closed shape checks hold. Engine-gated test re-runs the SPICE
mismatch decomposition and checks it matches the committed extract.
"""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parent.parent
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "converter-variation-0011-extract.json"
_MODULE = _REPO / "book" / "0011-converter-variation" / "decomposition.py"


def _load():
    try:
        spec = importlib.util.spec_from_file_location("decomposition_0011", _MODULE)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:  # noqa: BLE001 - missing engine/lib => skip
        return None


mod = _load()

_VARIATION = _REPO / "book" / "0011-converter-variation" / "variation.py"


def _engine_ok():
    """True when a real ngspice op solve runs through variation.py (SPICE MC)."""
    try:
        spec = importlib.util.spec_from_file_location("variation_0011_decomp", _VARIATION)
        vmod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(vmod)
    except Exception:  # noqa: BLE001 - missing engine/lib => skip
        return False
    if not getattr(vmod, "_PYSPICE_OK", False):
        return False
    try:
        vmod.mismatched_output(0, np.zeros(vmod.resistor_count()))  # one trivial solve
        return True
    except Exception:  # noqa: BLE001 - ngspice library missing => skip
        return False


ENGINE_OK = _engine_ok()


def _ideal_transfers(n_samples=4):
    t = np.tile(np.arange(16, dtype=float) * (mod.VREF / 16.0), (n_samples, 1))
    return t


def test_dac_decomposition_is_exact_on_ideal_transfer() -> None:
    d = mod.decompose_dac_transfer(_ideal_transfers())
    assert d["gain_error_mean"] == pytest.approx(0.0, abs=1e-12)
    assert d["offset_mean_v"] == pytest.approx(0.0, abs=1e-12)
    assert d["rms_total_v"] == pytest.approx(0.0, abs=1e-12)
    assert d["max_inl_v"] == pytest.approx(0.0, abs=1e-12)
    assert d["reconstruct_max_v"] == 0.0


def test_dac_decomposition_gain_error_and_exactness() -> None:
    # +5% gain on every sample
    t = _ideal_transfers() * 1.05
    d = mod.decompose_dac_transfer(t)
    assert d["gain_error_mean"] == pytest.approx(0.05)
    assert d["gain_error_std"] == pytest.approx(0.0, abs=1e-12)
    assert d["rms_inl_v"] == pytest.approx(0.0, abs=1e-12)  # pure gain, no INL
    assert d["reconstruct_max_v"] == 0.0  # V == line + INL exactly


def test_dac_decomposition_offset_only() -> None:
    t = _ideal_transfers() + 0.1
    d = mod.decompose_dac_transfer(t)
    assert d["offset_mean_v"] == pytest.approx(0.1)
    assert d["gain_error_mean"] == pytest.approx(0.0, abs=1e-12)
    assert d["rms_inl_v"] == pytest.approx(0.0, abs=1e-12)


def test_dac_decomposition_captures_nonlinearity() -> None:
    # single-code bump at code 8: pure INL of +0.05 V
    t = _ideal_transfers()
    t[:, 8] += 0.05
    d = mod.decompose_dac_transfer(t)
    assert d["max_inl_v"] == pytest.approx(0.05, rel=1e-6)
    assert d["reconstruct_max_v"] == 0.0
    assert d["rms_inl_v"] > 0.0


def test_dac_decomposition_shape_checks_fail_closed() -> None:
    with pytest.raises(ValueError):
        mod.decompose_dac_transfer(np.zeros((4, 15)))
    with pytest.raises(ValueError):
        mod.decompose_dac_transfer(np.zeros((0, 16)))


def test_adc_quantization_power_is_lsb_sq_over_12() -> None:
    r = mod.separate_adc_error(0.0)
    assert r["p_quant_v2"] == pytest.approx((mod.VREF / 16.0) ** 2 / 12.0)
    assert r["p_noise_v2"] == 0.0


def test_adc_error_power_separates_quantization_plus_noise() -> None:
    for noise_std in (0.0, 0.01, 0.05):
        r = mod.separate_adc_error(noise_std)
        assert r["p_hand_v2"] == pytest.approx(r["p_quant_v2"] + r["p_noise_v2"])
        # measured total must track the hand sum within sampling tolerance
        assert abs(r["p_total_v2"] - r["p_hand_v2"]) <= 0.25 * r["p_hand_v2"] + 1e-6
    # more noise => more total error power (monotone)
    p0 = mod.separate_adc_error(0.0)["p_total_v2"]
    p2 = mod.separate_adc_error(0.05)["p_total_v2"]
    assert p2 > p0


def test_adc_separation_is_deterministic() -> None:
    assert mod.separate_adc_error(0.01) == mod.separate_adc_error(0.01)


@pytest.mark.skipif(not ENGINE_OK, reason="PySpice/ngspice not available")
def test_spice_mismatch_decomposition_matches_committed_extract() -> None:
    spec = importlib.util.spec_from_file_location(
        "variation_0011_engine",
        _VARIATION,
    )
    vmod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vmod)
    extract = json.loads(_EXTRACT.read_text("utf-8"))
    deltas = vmod.draw_deltas()
    t = vmod.transfers_spice(deltas)
    d = mod.decompose_dac_transfer(t)
    stats = vmod.mismatch_stats(t)
    # decomposition fields are the same quantities the extract reports
    assert d["gain_error_mean"] == pytest.approx(extract["gain_error_mean"], rel=1e-9)
    assert d["gain_error_std"] == pytest.approx(extract["gain_error_std"], rel=1e-9)
    assert d["offset_mean_v"] == pytest.approx(extract["offset_mean_v"], abs=1e-12)
    assert d["max_inl_v"] >= extract["max_inl_mean_v"]  # max >= mean-of-max
    assert stats["max_inl_mean_v"] == pytest.approx(extract["max_inl_mean_v"], rel=1e-9)
