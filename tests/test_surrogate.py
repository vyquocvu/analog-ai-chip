import numpy as np
import pytest

from analog_llm.surrogate import (
    EvaluationMode,
    SurrogateCalibrationProfile,
    calibrate_surrogate,
    evaluate_projection_nonideality,
)
from analog_llm.tile import CrossbarTile


def _tile_factory() -> CrossbarTile:
    return CrossbarTile(
        rows=16,
        cols=16,
        g_bits=8,
        dac_bits=8,
        adc_bits=8,
        vout_max=4.0,
        sigma_prog_rel=0.01,
        sigma_read_rel=0.005,
        rng=42,
    )


def test_surrogate_calibration_produces_consistent_error_distribution() -> None:
    profile = calibrate_surrogate(
        tile_factory=_tile_factory,
        layer_family="attention.q_proj",
        in_features=32,
        out_features=32,
        tile_rows=16,
        tile_cols=16,
        num_samples=5,
        weight_max=0.5,
        seed=42,
    )

    assert profile.layer_family == "attention.q_proj"
    assert profile.snr_db > 10.0
    assert profile.error_std > 0.0
    assert profile.max_abs_error > 0.0
    assert profile.calibrated_weight_max == 0.5


def test_evaluation_modes_distinguish_physical_from_surrogate() -> None:
    profile = calibrate_surrogate(
        tile_factory=_tile_factory,
        layer_family="mlp.up_proj",
        in_features=16,
        out_features=16,
        tile_rows=16,
        tile_cols=16,
        num_samples=3,
    )

    W = np.random.default_rng(10).normal(0.0, 0.1, (16, 16))
    x = np.random.default_rng(20).normal(0.0, 1.0, (16,))

    # 1. Exact Mode
    res_exact = evaluate_projection_nonideality(
        x, W, mode=EvaluationMode.EXACT, tile_factory=_tile_factory, tile_rows=16, tile_cols=16
    )
    assert res_exact.mode == EvaluationMode.EXACT
    assert res_exact.is_physical_simulation is True
    assert res_exact.metadata["macs"] > 0

    # 2. Surrogate Mode
    res_surr = evaluate_projection_nonideality(
        x, W, mode=EvaluationMode.STATISTICAL_SURROGATE, surrogate_profile=profile
    )
    assert res_surr.mode == EvaluationMode.STATISTICAL_SURROGATE
    assert res_surr.is_physical_simulation is False
    assert "snr_db" in res_surr.metadata

    # 3. Layer Sampled Mode
    res_sampled = evaluate_projection_nonideality(
        x, W, mode=EvaluationMode.LAYER_SAMPLED, tile_factory=_tile_factory, layer_index=0, sampled_layer_indices=(0, 2)
    )
    assert res_sampled.is_physical_simulation is True

    res_unsampled = evaluate_projection_nonideality(
        x, W, mode=EvaluationMode.LAYER_SAMPLED, layer_index=1, sampled_layer_indices=(0, 2)
    )
    assert res_unsampled.is_physical_simulation is False


def test_surrogate_fails_closed_outside_calibrated_domain() -> None:
    profile = SurrogateCalibrationProfile(
        layer_family="test",
        error_mean=0.0,
        error_std=0.01,
        snr_db=30.0,
        max_abs_error=0.05,
        relative_l2_error_pct=1.0,
        calibrated_weight_max=0.2,
        tile_rows=16,
        tile_cols=16,
        num_samples=10,
        profile_name="crossbar-v1",
    )

    # Exceeding maximum weight
    W_large = np.full((16, 16), 0.5)
    x = np.ones(16)
    with pytest.raises(ValueError, match="exceeds calibrated domain limit"):
        evaluate_projection_nonideality(
            x, W_large, mode=EvaluationMode.STATISTICAL_SURROGATE, surrogate_profile=profile
        )

    # Tile dimension mismatch
    with pytest.raises(ValueError, match="Tile dimension mismatch"):
        profile.validate_domain(np.zeros((8, 8)), tile_rows=8, tile_cols=8)
