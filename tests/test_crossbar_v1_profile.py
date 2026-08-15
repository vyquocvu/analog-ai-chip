"""Tests for Chapter 0020 — Crossbar-v1 Profile Publication & Gate R4 Close."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from analog_llm.device_profile import load_device_profile, validate_device_profile
from analog_llm.profile_adapter import tile_config_from_profile

_REPO = Path(__file__).resolve().parent.parent
_PROFILE_PATH = _REPO / "device_profiles" / "crossbar-v1.json"
_MODULE = _REPO / "book" / "0020-crossbar-v1" / "crossbar_v1.py"
_SUMMARY_JSON = _REPO / "verification" / "reports" / "crossbar-v1-summary.json"
_SUMMARY_MD = _REPO / "verification" / "reports" / "crossbar-v1-summary.md"


def _load_module():
    spec = importlib.util.spec_from_file_location("crossbar_v1_0020", _MODULE)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["crossbar_v1_0020"] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()


def test_module_loaded() -> None:
    assert mod is not None, "Failed to load book/0020-crossbar-v1/crossbar_v1.py"


def test_crossbar_v1_profile_schema() -> None:
    """Validate crossbar-v1 profile schema and status."""
    profile = load_device_profile(_PROFILE_PATH, physical_claim=False)
    validate_device_profile(profile, physical_claim=False)

    assert profile["name"] == "crossbar-v1"
    assert profile["version"] == "0.1.0"
    assert profile["status"] == "VARIATION_SIMULATED"
    assert profile["evidence_class"] == "spice"
    assert "fields" in profile
    assert len(profile["fields"]) >= 30


def test_crossbar_v1_adapter_integration() -> None:
    """Test that profile_adapter cleanly constructs tile kwargs from crossbar-v1."""
    tile_cfg = tile_config_from_profile(
        _PROFILE_PATH,
        g_bits=4,
        dac_bits=4,
        adc_bits=4,
        physical_claim=False,
    )
    assert tile_cfg["gmin"] == pytest.approx(10.0e-6)
    assert tile_cfg["gmax"] == pytest.approx(100.0e-6)
    assert tile_cfg["vin_max"] == pytest.approx(2.5)
    assert tile_cfg["vout_max"] == pytest.approx(2.5)


def test_profile_crosscheck_with_extracts() -> None:
    """Run full verification script crosschecking 0015-0019 extracts."""
    assert mod is not None
    res = mod.verify_crossbar_v1_profile()
    assert res["status"] == "VALIDATED"
    assert res["profile_name"] == "crossbar-v1"


def test_verification_summary_reports() -> None:
    """Validate committed summary JSON and Markdown reports."""
    assert _SUMMARY_JSON.exists(), f"Missing {_SUMMARY_JSON}"
    assert _SUMMARY_MD.exists(), f"Missing {_SUMMARY_MD}"

    with open(_SUMMARY_JSON, "r", encoding="utf-8") as f:
        summary = json.load(f)

    assert summary["name"] == "crossbar-v1-verification-summary"
    assert len(summary["evidence_ledger"]) >= 8


def test_diagram_svgs_exist() -> None:
    """Verify presence of Chapter 0020 SVG diagrams."""
    diag_dir = _REPO / "book" / "0020-crossbar-v1" / "diagrams"
    assert (diag_dir / "crossbar_v1_summary.svg").is_file(), "Missing crossbar_v1_summary.svg"
    assert (diag_dir / "error_budget_breakdown.svg").is_file(), "Missing error_budget_breakdown.svg"
