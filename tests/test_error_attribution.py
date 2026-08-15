"""Tests for per-mechanism error attribution and decomposition."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from analog_llm.attribution import (
    ALL_MECHANISM_KEYS,
    attribute_from_profiles,
    attribute_tile_error,
    evaluate_attribution_suite,
)

_REPO = Path(__file__).resolve().parent.parent
_CROSSBAR = _REPO / "device_profiles" / "crossbar-v1.json"
_DAC = _REPO / "device_profiles" / "dac-r2r-v1.json"
_ADC = _REPO / "device_profiles" / "adc-sar-v1.json"


def test_attribution_structure_and_keys() -> None:
    rng = np.random.default_rng(42)
    w = rng.uniform(-1.0, 1.0, size=(16, 16))
    x = rng.uniform(-1.0, 1.0, size=16)

    res = attribute_tile_error(w, x, seed=42)

    assert len(res.ideal_output) == 16
    assert len(res.combined_output) == 16

    for key in ALL_MECHANISM_KEYS:
        assert key in res.standalone
        assert key in res.leave_one_out_residuals
        assert key in res.leave_one_out_contributions
        assert key in res.leave_one_out_shares_pct
        assert key in res.standalone_shares_pct
        m = res.standalone[key]
        assert m.l2_rel_error_pct >= 0.0
        assert m.rms_error >= 0.0
        assert -1.0 <= m.cosine_similarity <= 1.0

    assert "combined_all" in res.standalone
    assert res.summary["combined_rms_error"] > 0.0
    assert res.summary["dominant_mechanism_standalone"] in ALL_MECHANISM_KEYS


def test_attribution_all_ideal() -> None:
    rng = np.random.default_rng(42)
    w = rng.uniform(-1.0, 1.0, size=(8, 8))
    x = rng.uniform(-1.0, 1.0, size=8)

    # When all non-idealities are zero / ideal
    res = attribute_tile_error(
        w,
        x,
        g_bits=16,
        dac_bits=16,
        adc_bits=16,
        sigma_prog_rel=0.0,
        sigma_read_rel=0.0,
        p_stuck_hrs=0.0,
        p_stuck_lrs=0.0,
        drift_time_s=0.0,
        iv_non_linearity_beta=0.0,
        r_wire_ohm=0.0,
        seed=42,
    )

    combined_m = res.standalone["combined_all"]
    assert combined_m.rms_error == pytest.approx(0.0, abs=1e-3)
    assert combined_m.cosine_similarity == pytest.approx(1.0, abs=1e-3)


def test_attribution_leave_one_out_residuals() -> None:
    rng = np.random.default_rng(42)
    w = rng.uniform(-1.0, 1.0, size=(16, 16))
    x = rng.uniform(-1.0, 1.0, size=16)

    res = attribute_tile_error(w, x, seed=42)

    # All LOO shares must sum to 100% (or 0 if zero total contribution)
    total_share = sum(res.leave_one_out_shares_pct.values())
    if total_share > 0.0:
        assert total_share == pytest.approx(100.0, abs=1e-5)

    # All standalone shares must sum to 100%
    total_standalone = sum(res.standalone_shares_pct.values())
    assert total_standalone == pytest.approx(100.0, abs=1e-5)


def test_attribute_from_profiles_deterministic() -> None:
    rng = np.random.default_rng(42)
    w = rng.uniform(-1.0, 1.0, size=(16, 16))
    x = rng.uniform(-1.0, 1.0, size=16)

    res1 = attribute_from_profiles(w, x, _CROSSBAR, _DAC, _ADC, seed=42)
    res2 = attribute_from_profiles(w, x, _CROSSBAR, _DAC, _ADC, seed=42)

    assert res1.ideal_output == res2.ideal_output
    assert res1.combined_output == res2.combined_output
    assert res1.to_dict() == res2.to_dict()


def test_evaluate_attribution_suite() -> None:
    suite = evaluate_attribution_suite(n=8, n_vectors=5, seed=42)

    assert suite["dimension"] == 8
    assert suite["n_vectors"] == 5
    assert set(suite["matrices"].keys()) == {"identity", "mixed_sign", "sparse_80pct", "rank_one"}

    for data in suite["matrices"].values():
        assert "combined_all" in data["mean_l2_rel_error_pct"]
        assert len(data["mean_loo_share_pct"]) == len(ALL_MECHANISM_KEYS)


def test_attribution_loo_unconfounded_stochastic_streams() -> None:
    """Verifies that LOO execution reproduces identical noise on unablated mechanisms."""
    rng = np.random.default_rng(42)
    w = rng.uniform(-1.0, 1.0, size=(16, 16))
    x = rng.uniform(-1.0, 1.0, size=16)

    res = attribute_tile_error(w, x, seed=42)

    # In LOO without stuck_faults, the residual error must be less than combined error
    # since removing defects improves the fidelity
    assert res.leave_one_out_residuals["stuck_faults"] <= res.summary["combined_rms_error"] + 1e-9
    # The contribution of stuck faults is positive
    assert res.leave_one_out_contributions["stuck_faults"] >= 0.0
