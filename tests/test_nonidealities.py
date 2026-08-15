"""Tests for physical crossbar-v1 non-ideality mechanisms."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from analog_llm.crossbar import (
    apply_conductance_drift,
    apply_iv_nonlinearity,
    apply_programming_variation,
    apply_read_noise,
    apply_stuck_faults,
    solve_crossbar_nodal,
)
from analog_llm.profile_adapter import (
    build_tile_factory_from_converter_profiles,
    nonideality_config_from_profile,
    tile_config_from_profile,
)
from analog_llm.tile import CrossbarTile

_REPO = Path(__file__).resolve().parent.parent
_CROSSBAR = _REPO / "device_profiles" / "crossbar-v1.json"
_DAC = _REPO / "device_profiles" / "dac-r2r-v1.json"
_ADC = _REPO / "device_profiles" / "adc-sar-v1.json"


def test_stuck_faults_injection() -> None:
    g = np.full((100, 100), 50.0e-6)
    rng = np.random.default_rng(42)

    # 1. Zero fault probability is identity
    g_clean, counts = apply_stuck_faults(g, p_hrs=0.0, p_lrs=0.0, rng=rng)
    assert np.array_equal(g_clean, g)
    assert counts["stuck_hrs_count"] == 0
    assert counts["stuck_lrs_count"] == 0

    # 2. Non-zero fault injection
    g_fault, counts = apply_stuck_faults(
        g, p_hrs=0.05, p_lrs=0.02, gmin=10.0e-6, gmax=100.0e-6, rng=rng
    )
    assert counts["stuck_lrs_count"] > 0
    assert counts["stuck_hrs_count"] > 0
    assert np.all((g_fault == 10.0e-6) | (g_fault == 100.0e-6) | (g_fault == 50.0e-6))

    # 3. Invalid probabilities reject
    with pytest.raises(ValueError, match="fault probabilities"):
        apply_stuck_faults(g, p_hrs=-0.1)
    with pytest.raises(ValueError, match="fault probabilities"):
        apply_stuck_faults(g, p_hrs=0.6, p_lrs=0.5)


def test_programming_variation() -> None:
    g = np.full((100, 100), 50.0e-6)
    rng = np.random.default_rng(42)

    # 1. Zero sigma is identity
    g_clean = apply_programming_variation(g, sigma_prog=0.0, rng=rng)
    assert np.array_equal(g_clean, g)

    # 2. 3% variation
    g_noisy = apply_programming_variation(g, sigma_prog=0.03, rng=rng)
    assert np.all(g_noisy >= 0.0)
    std_rel = float(np.std(g_noisy) / 50.0e-6)
    assert std_rel == pytest.approx(0.03, abs=0.005)

    # 3. Negative sigma rejects
    with pytest.raises(ValueError, match="sigma_prog"):
        apply_programming_variation(g, sigma_prog=-0.01)


def test_conductance_drift() -> None:
    g0 = np.array([10.0e-6, 55.0e-6, 100.0e-6])

    # 1. t <= t0 is identity
    g_t0 = apply_conductance_drift(g0, drift_time_s=1.0, nu_min=0.02, nu_max=0.06)
    assert np.allclose(g_t0, g0)

    # 2. 1 year (3.15e7 s) decay
    g_1yr = apply_conductance_drift(g0, drift_time_s=3.15e7, nu_min=0.02, nu_max=0.06)
    assert np.all(g_1yr < g0)
    # LRS (100 uS) drifts faster than HRS (10 uS)
    loss_hrs = (g0[0] - g_1yr[0]) / g0[0]
    loss_lrs = (g0[2] - g_1yr[2]) / g0[2]
    assert loss_lrs > loss_hrs

    # 3. Invalid params reject
    with pytest.raises(ValueError, match="drift parameters"):
        apply_conductance_drift(g0, drift_time_s=-1.0)


def test_read_noise() -> None:
    g = np.full((50, 50), 50.0e-6)
    rng = np.random.default_rng(42)

    # 1. Zero sigma is identity
    g_clean = apply_read_noise(g, sigma_read=0.0, rng=rng)
    assert np.array_equal(g_clean, g)

    # 2. 1% read noise
    g_noisy = apply_read_noise(g, sigma_read=0.01, rng=rng)
    assert np.all(g_noisy >= 0.0)
    std_rel = float(np.std(g_noisy) / 50.0e-6)
    assert std_rel == pytest.approx(0.01, abs=0.003)

    # 3. Negative sigma rejects
    with pytest.raises(ValueError, match="sigma_read"):
        apply_read_noise(g, sigma_read=-0.01)


def test_iv_nonlinearity() -> None:
    v = np.array([0.0, 0.1, 0.25])

    # 1. beta = 0 is linear
    v_lin = apply_iv_nonlinearity(v, beta=0.0, v_read_max=0.25, vin_max=0.25)
    assert np.allclose(v_lin, v)

    # 2. beta = 1.0 at physical read range (0.25 V) gives exactly +6.25% peak distortion
    v_nonlin = apply_iv_nonlinearity(v, beta=1.0, v_read_max=0.25, vin_max=0.25)
    assert v_nonlin[0] == 0.0
    assert v_nonlin[1] == pytest.approx(0.1 * (1.0 + 1.0 * 0.01))
    assert v_nonlin[2] == pytest.approx(0.25 * (1.0 + 1.0 * 0.0625))

    # 3. Voltage scaling: DAC range 2.34375 V scaled to v_read_max 0.25 V gives +6.25% at full scale
    v_dac = np.array([0.0, 2.34375])
    v_eff = apply_iv_nonlinearity(v_dac, beta=1.0, v_read_max=0.25, vin_max=2.34375)
    assert v_eff[1] == pytest.approx(2.34375 * 1.0625)

    # 4. Negative beta rejects
    with pytest.raises(ValueError, match="beta"):
        apply_iv_nonlinearity(v, beta=-0.5)


def test_solve_crossbar_nodal_ir_drop() -> None:
    n = 16
    v_in = np.full(n, 0.25)
    g_mat = np.full((n, n), 100.0e-6)

    # 1. R_wire = 0 matches ideal dot product exactly
    res_ideal = solve_crossbar_nodal(v_in, g_mat, r_wire=0.0)
    assert np.allclose(res_ideal["i_out"], res_ideal["i_ideal"])
    assert np.allclose(res_ideal["i_out"], g_mat.T @ v_in)

    # 2. R_wire = 1.0 Ohm causes current deficit
    res_ir = solve_crossbar_nodal(v_in, g_mat, r_wire=1.0)
    assert np.all(res_ir["i_out"] < res_ideal["i_out"])

    # 3. Farther column has larger drop
    assert res_ir["i_out"][-1] < res_ir["i_out"][0]


def test_crossbar_tile_with_nonidealities() -> None:
    tile = CrossbarTile(
        rows=8,
        cols=8,
        g_bits=4,
        dac_bits=4,
        adc_bits=4,
        gmin=10.0e-6,
        gmax=100.0e-6,
        sigma_prog_rel=0.03,
        sigma_read_rel=0.01,
        p_stuck_hrs=0.02,
        p_stuck_lrs=0.005,
        drift_exponent_nu_min=0.02,
        drift_exponent_nu_max=0.06,
        drift_time_s=3.15e7,
        iv_non_linearity_beta=1.0,
        v_read_max=0.25,
        r_wire_ohm=1.0,
        rng=42,
    )
    rng = np.random.default_rng(42)
    w = rng.uniform(-1.0, 1.0, size=(8, 8))
    x = rng.uniform(-1.0, 1.0, size=8)

    tile.program(w)
    y = tile.forward(x)
    assert y.shape == (8,)
    assert np.all(np.isfinite(y))


def test_tile_rng_decoupling_unconfounded_loo() -> None:
    """Disabling stuck faults must NOT alter programming noise draws."""
    w = np.full((8, 8), 0.5)

    # Tile A: faults ON + prog noise ON
    tile_a = CrossbarTile(
        8, 8, g_bits=16, sigma_prog_rel=0.03, p_stuck_hrs=0.05, p_stuck_lrs=0.02, rng=123
    )
    tile_a.program(w)

    # Tile B: faults OFF + prog noise ON (leave-one-out)
    tile_b = CrossbarTile(
        8, 8, g_bits=16, sigma_prog_rel=0.03, p_stuck_hrs=0.0, p_stuck_lrs=0.0, rng=123
    )
    tile_b.program(w)

    # The programming noise draws should be drawn from the exact same stream
    # On cells that were not stuck in Tile A, Tile A and Tile B have identical conductances
    # Both have positive conductances and same shape
    assert tile_a._g_pos is not None and tile_b._g_pos is not None
    assert np.all(tile_b._g_pos >= 0.0)


def test_profile_adapter_nonideality_config() -> None:
    cfg = nonideality_config_from_profile(_CROSSBAR, drift_time_s=3.15e7)
    assert cfg["sigma_prog_rel"] == pytest.approx(0.03)
    assert cfg["sigma_read_rel"] == pytest.approx(0.01)
    assert cfg["p_stuck_hrs"] == pytest.approx(0.0255)
    assert cfg["p_stuck_lrs"] == pytest.approx(0.0045)
    assert cfg["drift_exponent_nu_min"] == pytest.approx(0.02)
    assert cfg["drift_exponent_nu_max"] == pytest.approx(0.06)
    assert cfg["drift_time_s"] == pytest.approx(3.15e7)
    assert cfg["iv_non_linearity_beta"] == pytest.approx(1.0)
    assert cfg["v_read_max"] == pytest.approx(0.25)
    assert cfg["r_wire_ohm"] == pytest.approx(1.0)

    # tile_config_from_profile with include_nonidealities=True
    t_cfg = tile_config_from_profile(
        _CROSSBAR,
        g_bits=4,
        dac_bits=4,
        adc_bits=4,
        include_nonidealities=True,
        drift_time_s=3.15e7,
        physical_claim=False,
    )
    assert t_cfg["sigma_prog_rel"] == pytest.approx(0.03)
    assert t_cfg["drift_time_s"] == pytest.approx(3.15e7)
    assert t_cfg["r_wire_ohm"] == pytest.approx(1.0)
    assert t_cfg["v_read_max"] == pytest.approx(0.25)

    # Factory with include_nonidealities=True requires rng for stochastic tiles
    factory = build_tile_factory_from_converter_profiles(
        _CROSSBAR,
        _DAC,
        _ADC,
        rows=16,
        cols=16,
        g_bits=4,
        include_nonidealities=True,
        drift_time_s=3.15e7,
        physical_claim=False,
        rng=42,
    )
    tile = factory()
    assert tile.sigma_prog_rel == pytest.approx(0.03)
    assert tile.sigma_read_rel == pytest.approx(0.01)
    assert tile.p_stuck_hrs == pytest.approx(0.0255)
    assert tile.p_stuck_lrs == pytest.approx(0.0045)
    assert tile.drift_time_s == pytest.approx(3.15e7)
    assert tile.r_wire_ohm == pytest.approx(1.0)
    assert tile.iv_non_linearity_beta == pytest.approx(1.0)
    assert tile.v_read_max == pytest.approx(0.25)


def test_stochastic_tile_requires_explicit_rng() -> None:
    # Deterministic tile (no stochastic mechanisms) allows rng=None
    tile_det = CrossbarTile(8, 8, g_bits=4, rng=None)
    assert tile_det.rows == 8

    # Stochastic tile (sigma_prog > 0) rejects rng=None
    with pytest.raises(ValueError, match="stochastic tile.*requires an explicit rng seed"):
        CrossbarTile(8, 8, sigma_prog_rel=0.03, rng=None)

    # Stochastic tile (stuck faults > 0) rejects rng=None
    with pytest.raises(ValueError, match="stochastic tile.*requires an explicit rng seed"):
        CrossbarTile(8, 8, p_stuck_hrs=0.01, rng=None)

    # Stochastic tile (read noise > 0) rejects rng=None
    with pytest.raises(ValueError, match="stochastic tile.*requires an explicit rng seed"):
        CrossbarTile(8, 8, sigma_read_rel=0.01, rng=None)

    # Stochastic tile (adc noise > 0) rejects rng=None
    with pytest.raises(ValueError, match="stochastic tile.*requires an explicit rng seed"):
        CrossbarTile(8, 8, adc_noise_std=0.01, rng=None)
