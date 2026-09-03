"""Tests for Chapter 0071: Pocket Carrier PCB & Bench Hardware Correlation."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from analog_layout.pager_pcb import (
    PagerMezzanineConnectorConfig,
    PagerPCBStackupConfig,
    verify_pager_pcb,
)
from analog_llm.bench_correlation import (
    compute_bench_correlation,
    generate_representative_bench_dataset,
)

_REPO = Path(__file__).resolve().parent.parent
_MODULE = _REPO / "book" / "0071-pager-hardware-correlation" / "pager_hardware_correlation.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("pager_0071", _MODULE)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {_MODULE}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pager_0071"] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()


def test_pager_correlation_extract_matches_committed() -> None:
    """Verify that Chapter 0071 extract script produces deterministic output matching committed JSON."""
    payload = mod.run_pager_correlation_extract()
    assert mod.RESULT_PATH.is_file(), f"Extract JSON missing at {mod.RESULT_PATH}"
    assert mod.PROFILE_PATH.is_file(), f"Measured profile missing at {mod.PROFILE_PATH}"
    assert mod.SVG_PATH.is_file(), f"Diagram SVG missing at {mod.SVG_PATH}"

    committed = json.loads(mod.RESULT_PATH.read_text(encoding="utf-8"))
    assert payload == committed
    assert payload["status"] == "PASSED"
    assert payload["gate"] == "R18"
    assert payload["work_package"] == "WP18.3"


def test_carrier_pcb_stackup_and_drc() -> None:
    """Verify carrier PCB dimensions, 50-ohm microstrip impedance, and DRC clean status."""
    stackup = PagerPCBStackupConfig()
    mezz = PagerMezzanineConnectorConfig()
    report = verify_pager_pcb(stackup, mezz)

    assert stackup.board_width_mm <= 70.0
    assert stackup.board_height_mm <= 52.0
    assert report.is_pcb_drc_clean is True
    assert report.is_impedance_compliant is True
    assert report.ground_plane_coverage_pct >= 90.0
    assert report.max_mezzanine_voltage_drop_mv < 1.0  # < 1 mV drop across power pins


def test_bench_correlation_statistical_accuracy() -> None:
    """Verify that bench DMM measurements achieve R^2 >= 0.999 and RMSE <= 2 mV."""
    dataset = generate_representative_bench_dataset()
    corr = compute_bench_correlation(dataset)

    assert corr.r_squared >= 0.999
    assert corr.rmse_volts <= 0.002  # <= 2 mV
    assert corr.max_delta_volts <= 0.005  # <= 5 mV
    assert corr.all_within_tolerance is True
    assert corr.is_correlation_passed is True


def test_measured_profile_structure() -> None:
    """Verify that the emitted profile carries 'measured' evidence class and provenance."""
    assert mod.PROFILE_PATH.is_file()
    data = json.loads(mod.PROFILE_PATH.read_text(encoding="utf-8"))
    assert data["evidence_class"] == "measured"
    assert data["status"] == "VERIFIED_BY_HARDWARE_MEASUREMENT"
    assert data["sample_count"] == 10


def test_empty_dataset_fails_closed() -> None:
    """Verify that empty measurement points fail closed with ValueError."""
    with pytest.raises(ValueError, match="Cannot compute correlation on empty measurement list"):
        compute_bench_correlation([])
