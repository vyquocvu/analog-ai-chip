"""Tests for Chapter 0016 — Non-Volatile Memory Programming & Read Variation."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_MODULE = _REPO / "book" / "0016-variation" / "variation.py"
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "variation-0016-extract.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("variation_0016", _MODULE)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["variation_0016"] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()


def test_module_loaded() -> None:
    assert mod is not None, "Failed to load book/0016-variation/variation.py"


def test_variation_config_parameters() -> None:
    """Validate default variation parameters and combined standard deviation."""
    assert mod is not None
    cfg = mod.VariationConfig()
    assert cfg.sigma_prog == pytest.approx(0.03)
    assert cfg.sigma_read == pytest.approx(0.01)
    assert cfg.sigma_total == pytest.approx((0.03**2 + 0.01**2) ** 0.5)


def test_theoretical_weight_std() -> None:
    """Validate closed-form weight error bounds."""
    assert mod is not None
    cfg = mod.VariationConfig()
    sig_tot = cfg.sigma_total

    # Zero weight noise floor
    std_0 = mod.theoretical_weight_std(0.0, sig_tot)
    expected_0 = (2**0.5) * 10e-6 * sig_tot / 90e-6
    assert std_0 == pytest.approx(expected_0)
    assert std_0 == pytest.approx(0.004969, rel=1e-3)

    # Full scale weight
    std_1 = mod.theoretical_weight_std(1.0, sig_tot)
    expected_1 = ((100e-6**2 + 10e-6**2) ** 0.5) * sig_tot / 90e-6
    assert std_1 == pytest.approx(expected_1)
    assert std_1 == pytest.approx(0.035311, rel=1e-3)

    # Monotonicity with |w|
    assert std_1 > std_0
    assert mod.theoretical_weight_std(0.5, sig_tot) > std_0
    assert mod.theoretical_weight_std(0.5, sig_tot) < std_1
    assert mod.theoretical_weight_std(-0.5, sig_tot) == pytest.approx(mod.theoretical_weight_std(0.5, sig_tot))


def test_monte_carlo_conductance_sampling() -> None:
    """Monte Carlo sample mean and std converge to theoretical distributions."""
    assert mod is not None
    g_target = 55.0e-6  # midpoint state
    cfg = mod.VariationConfig(seed=42)
    samples = mod.sample_conductance_monte_carlo(g_target, n_samples=1000, config=cfg)

    assert len(samples) == 1000
    assert all(samples >= 0.0)

    # Sample mean within 1% of target
    emp_mean = float(samples.mean())
    assert emp_mean == pytest.approx(g_target, rel=1e-2)

    # Sample std within 10% of theoretical
    emp_std = float(samples.std())
    expected_std = g_target * cfg.sigma_total
    assert emp_std == pytest.approx(expected_std, rel=0.10)


def test_monte_carlo_differential_weight_sampling() -> None:
    """Monte Carlo differential pair w_eff matches closed form."""
    assert mod is not None
    cfg = mod.VariationConfig(seed=42)
    _gp, _gm, w_eff = mod.sample_differential_weight_monte_carlo(0.50, n_samples=1000, config=cfg)

    assert len(w_eff) == 1000
    assert float(w_eff.mean()) == pytest.approx(0.50, rel=2e-2)

    emp_std = float(w_eff.std())
    th_std = mod.theoretical_weight_std(0.50, cfg.sigma_total)
    assert emp_std == pytest.approx(th_std, rel=0.10)


def test_invalid_variation_parameters_raise() -> None:
    """Fail-closed on negative standard deviations."""
    assert mod is not None
    with pytest.raises(ValueError, match="non-negative"):
        mod.VariationConfig(sigma_prog=-0.01)
    with pytest.raises(ValueError, match="non-negative"):
        mod.VariationConfig(sigma_read=-0.05)


def test_committed_extract_integrity() -> None:
    """Validate structure and metrics of the committed extract JSON."""
    assert _EXTRACT.exists(), f"Missing extract artifact at {_EXTRACT}"
    with open(_EXTRACT) as f:
        data = json.load(f)

    assert data["schema_version"] == "0.1.0"
    assert data["chapter"] == "0016-variation"
    assert data["assumptions"]["sigma_prog_rel"] == pytest.approx(0.03)
    assert data["assumptions"]["sigma_read_rel"] == pytest.approx(0.01)
    assert data["summary"]["zero_weight_noise_floor_std"] == pytest.approx(0.004969, rel=1e-3)
    assert data["summary"]["full_scale_weight_std"] == pytest.approx(0.035311, rel=1e-3)


def test_diagram_svgs_exist() -> None:
    """Verify presence of Chapter 0016 SVG diagrams."""
    diag_dir = _REPO / "book" / "0016-variation" / "diagrams"
    assert (diag_dir / "variation_mechanisms.svg").is_file(), "Missing variation_mechanisms.svg"
    assert (diag_dir / "monte_carlo_distribution.svg").is_file(), "Missing monte_carlo_distribution.svg"
