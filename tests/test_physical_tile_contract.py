"""Tests for Chapter 0021 — Physical Tile Contract."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

from analog_llm.profile_adapter import build_tile_factory_from_converter_profiles

_REPO = Path(__file__).resolve().parent.parent
_MODULE = _REPO / "book" / "0021-physical-tile-contract" / "physical_tile_contract.py"
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "physical-tile-0021-extract.json"
_CROSSBAR = _REPO / "device_profiles" / "crossbar-v1.json"
_DAC = _REPO / "device_profiles" / "dac-r2r-v1.json"
_ADC = _REPO / "device_profiles" / "adc-sar-v1.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("physical_tile_0021", _MODULE)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["physical_tile_0021"] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()


def test_module_loaded() -> None:
    assert mod is not None, "Failed to load book/0021-physical-tile-contract/physical_tile_contract.py"


def test_physical_tile_factory_instantiation() -> None:
    """Verify that tile factory correctly consumes the 3 validated profiles."""
    factory = build_tile_factory_from_converter_profiles(
        _CROSSBAR,
        _DAC,
        _ADC,
        rows=16,
        cols=16,
        g_bits=4,
        physical_claim=False,
    )
    tile = factory()
    assert tile.rows == 16
    assert tile.cols == 16
    assert tile.gmin == pytest.approx(10.0e-6)
    assert tile.gmax == pytest.approx(100.0e-6)
    assert tile.dac_bits == 4
    assert tile.adc_bits == 4


def test_zero_matrix_differential_cancellation() -> None:
    """Zero weight matrix must yield exact 0 output due to balanced differential cancellation."""
    factory = build_tile_factory_from_converter_profiles(
        _CROSSBAR,
        _DAC,
        _ADC,
        rows=16,
        cols=16,
        g_bits=4,
        physical_claim=False,
    )
    tile = factory()
    w_zero = np.zeros((16, 16))
    tile.program(w_zero)

    rng = np.random.default_rng(42)
    x = rng.uniform(-1.0, 1.0, size=16)
    y = tile.forward(x)

    assert np.all(y == 0.0)


def test_zero_vector_input() -> None:
    """Zero input vector must yield exact zero output."""
    factory = build_tile_factory_from_converter_profiles(
        _CROSSBAR,
        _DAC,
        _ADC,
        rows=8,
        cols=8,
        g_bits=4,
        physical_claim=False,
    )
    tile = factory()
    w = np.eye(8)
    tile.program(w)

    x_zero = np.zeros(8)
    y = tile.forward(x_zero)
    assert np.all(y == 0.0)


def test_high_cosine_similarity() -> None:
    """Profile-driven tile must maintain high directional cosine similarity (> 0.95)."""
    factory = build_tile_factory_from_converter_profiles(
        _CROSSBAR,
        _DAC,
        _ADC,
        rows=16,
        cols=16,
        g_bits=4,
        physical_claim=False,
    )
    tile = factory()
    rng = np.random.default_rng(42)
    w = rng.uniform(-1.0, 1.0, size=(16, 16))
    tile.program(w)

    for _ in range(20):
        x = rng.uniform(-1.0, 1.0, size=16)
        y_ideal = w @ x
        y_actual = tile.forward(x)

        cos_sim = np.dot(y_actual, y_ideal) / (np.linalg.norm(y_actual) * np.linalg.norm(y_ideal) + 1e-12)
        assert cos_sim > 0.95


def test_committed_extract_integrity() -> None:
    """Validate structure and metrics of committed extract JSON."""
    assert _EXTRACT.exists(), f"Missing extract artifact at {_EXTRACT}"
    with open(_EXTRACT, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["schema_version"] == "0.1.0"
    assert data["chapter"] == "0021-physical-tile-contract"
    assert data["summary"]["mixed_sign_cosine_sim_4b"] > 0.98
    assert data["summary"]["zero_matrix_error"] == pytest.approx(0.0)


def test_diagram_svgs_exist() -> None:
    """Verify presence of Chapter 0021 SVG diagrams."""
    diag_dir = _REPO / "book" / "0021-physical-tile-contract" / "diagrams"
    assert (diag_dir / "physical_tile_architecture.svg").is_file(), "Missing physical_tile_architecture.svg"
    assert (diag_dir / "physical_tile_linearity.svg").is_file(), "Missing physical_tile_linearity.svg"
