"""R5 profile-driven tile calibration evidence tests."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

from analog_llm import output_calibration_from_profile
from analog_llm.device_profile import load_device_profile

_REPO = Path(__file__).resolve().parent.parent
_GENERATOR = _REPO / "verification" / "calibration" / "extract_tile_calibration.py"
_PROFILE = _REPO / "device_profiles" / "tile-calibration-v1.json"
_RESULT = _REPO / "verification" / "calibration" / "results" / "tile-calibration-v1-extract.json"
_DIAGRAM = _REPO / "verification" / "calibration" / "diagrams" / "tile-calibration-v1.svg"


def _load_generator():
    spec = importlib.util.spec_from_file_location("tile_calibration_extract", _GENERATOR)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules["tile_calibration_extract"] = module
    spec.loader.exec_module(module)
    return module


generator = _load_generator()


def _minimal_profile(*, gain: float = 2.0, offset_v: float = 1.0) -> dict:
    return {
        "schema_version": 1,
        "name": "hand-calibration",
        "version": "0.1.0",
        "evidence_class": "derived",
        "status": "SYSTEM_SIMULATED",
        "fields": {
            "correction_gain": {"value": gain, "unit": "1", "evidence_class": "derived"},
            "correction_offset_v": {
                "value": offset_v,
                "unit": "V",
                "evidence_class": "derived",
            },
        },
        "provenance": {
            "tool": "hand",
            "analysis": "tiny affine example",
            "sources": ["tests/test_tile_calibration.py"],
            "conditions": {},
            "limitations": "test-only profile",
        },
    }


def test_tiny_hand_computable_profile_correction() -> None:
    """For gain=2 and offset=1 V, [0,1] V corrects to [1,3] V."""
    calibration = output_calibration_from_profile(_minimal_profile())
    assert calibration.apply([0.0, 1.0]) == pytest.approx([1.0, 3.0])


def test_committed_profile_is_consumed_downstream() -> None:
    profile = load_device_profile(_PROFILE)
    result = json.loads(_RESULT.read_text("utf-8"))["calibration"]
    calibration = output_calibration_from_profile(profile)
    corrected = calibration.apply(result["raw_outputs_v"])

    assert calibration.profile_name == "tile-calibration-v1"
    assert calibration.offset_v == 0.0
    assert corrected == pytest.approx(result["calibrated_outputs_v"], abs=1e-15)
    assert np.all(calibration.apply(np.zeros(4)) == 0.0)


def test_calibration_improves_rms_without_degrading_max_error() -> None:
    result = json.loads(_RESULT.read_text("utf-8"))["calibration"]
    assert result["calibrated_rms_error_v"] < result["raw_rms_error_v"]
    assert result["rms_improvement_pct"] > 5.0
    assert result["calibrated_max_abs_error_v"] <= result["raw_max_abs_error_v"] + 1e-12
    assert result["calibrated_max_abs_error_v"] <= result["frozen_budget_v"]
    assert result["preserves_balanced_zero"] is True
    assert result["passes_frozen_budget"] is True


def test_artifacts_are_deterministically_reproducible() -> None:
    assert generator is not None
    expected_profile = json.loads(_PROFILE.read_text("utf-8"))
    expected_result = json.loads(_RESULT.read_text("utf-8"))
    profile, result = generator.build_artifacts()
    assert profile == expected_profile
    assert result == expected_result


def test_system_calibration_fails_closed_for_physical_claim() -> None:
    with pytest.raises(ValueError, match="cannot support a physical claim"):
        output_calibration_from_profile(_PROFILE, physical_claim=True)


def test_invalid_calibration_profile_fails_closed() -> None:
    missing = _minimal_profile()
    missing["fields"].pop("correction_gain")
    with pytest.raises(ValueError, match="missing required field"):
        output_calibration_from_profile(missing)

    with pytest.raises(ValueError, match="finite and positive"):
        output_calibration_from_profile(_minimal_profile(gain=0.0))

    calibration = output_calibration_from_profile(_minimal_profile())
    with pytest.raises(ValueError, match="finite"):
        calibration.apply([float("nan")])


def test_degenerate_calibration_evidence_fails_closed() -> None:
    assert generator is not None
    evidence = {
        "frozen_budget": {"value": 0.1},
        "arrays": {
            "tiny": {
                "cases": [
                    {"tile_output_v": [0.0], "spice_output_v": [0.0]},
                ]
            }
        },
    }
    with pytest.raises(ValueError, match="non-zero raw output"):
        generator.derive_calibration(evidence)


def test_calibration_formula_and_diagram_are_committed() -> None:
    result = json.loads(_RESULT.read_text("utf-8"))["calibration"]
    assert "least_squares_gain" in result["formula"]
    assert "max_constraint" in result["formula"]
    assert "correction" in result["formula"]
    assert _DIAGRAM.is_file()


def test_held_out_cross_validation_recorded() -> None:
    result = json.loads(_RESULT.read_text("utf-8"))["calibration"]
    assert "held_out_validation" in result
    cv = result["held_out_validation"]
    assert "array_split_2x2_train_4x4_test" in cv
    assert "array_split_4x4_train_2x2_test" in cv
    assert "leave_one_case_out_cv" in cv
    assert cv["leave_one_case_out_cv"]["k_folds"] == 10
