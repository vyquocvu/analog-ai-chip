"""Frozen R5 tile-level validation report tests."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_GENERATOR = _REPO / "verification" / "reports" / "generate_tile_v1_summary.py"
_JSON = _REPO / "verification" / "reports" / "tile-v1-r5-validation-summary.json"
_MARKDOWN = _REPO / "verification" / "reports" / "tile-v1-r5-validation-summary.md"
_SVG = _REPO / "verification" / "reports" / "tile-v1-r5-validation-summary.svg"


def _load_generator():
    spec = importlib.util.spec_from_file_location("generate_tile_v1_summary", _GENERATOR)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules["generate_tile_v1_summary"] = module
    spec.loader.exec_module(module)
    return module


generator = _load_generator()


def test_report_artifacts_are_deterministically_reproducible() -> None:
    assert generator is not None
    summary = generator.build_summary()
    assert summary == generator.build_summary()
    assert summary == json.loads(_JSON.read_text("utf-8"))
    assert generator.render_markdown(summary) == _MARKDOWN.read_text("utf-8")
    assert generator.render_svg(summary) == _SVG.read_text("utf-8")


def test_report_crosschecks_profile_driven_tile_configuration() -> None:
    summary = json.loads(_JSON.read_text("utf-8"))
    tile = summary["tile_configuration"]
    assert tile == {
        "gmin_s": pytest.approx(10e-6),
        "gmax_s": pytest.approx(100e-6),
        "g_bits": 4,
        "dac_bits": 4,
        "adc_bits": 4,
        "vin_max_v": pytest.approx(2.34375),
        "vout_max_v": pytest.approx(2.5),
        "physical_claim": False,
    }
    assert summary["sources"]["crosscheck"].startswith("passed")


def test_report_freezes_formula_and_test_evidence() -> None:
    summary = json.loads(_JSON.read_text("utf-8"))
    formulas = summary["formulas"]
    assert "max_(c,j)" in formulas["tile_spice_error"]
    assert "sum(y_raw*y_spice)" in formulas["calibration_gain"]
    assert formulas["accumulator_bits"] == "B_acc >= B_ADC + ceil(log2(K_c))"

    evidence = summary["evidence"]
    assert evidence["small_array_spice"]["case_count"] == 10
    assert evidence["small_array_spice"]["output_sample_count"] == 30
    assert evidence["small_array_spice"]["passed"] is True
    assert (
        evidence["calibration"]["calibrated_rms_error_v"]
        < evidence["calibration"]["raw_rms_error_v"]
    )
    assert evidence["partial_sums"]["examples"] == {"kc_4": 6, "kc_16": 8, "kc_64": 10}


def test_report_verifies_consumed_nonidealities_and_gate_status() -> None:
    summary = json.loads(_JSON.read_text("utf-8"))
    assert summary["gate_status"] == "MET"
    assert summary["claim_level"] == "SYSTEM_SIMULATED"
    assert summary["criteria"]["all_required_crossbar_nonidealities_consumed"] is True
    assert summary["criteria"]["per_mechanism_error_attribution_verified"] is True
    assert summary["criteria"]["profile_driven_calibration"] is True
    assert len(summary["profile_coverage"]["required_unconsumed_nonidealities"]) == 0
    assert len(summary["limitations"]) == 1
    assert summary["limitations"][0]["kind"] == "assumed_profile_parameters"


def test_report_fails_closed_when_source_value_diverges(tmp_path: Path) -> None:
    assert generator is not None
    tile = json.loads(generator.TILE_EXTRACT.read_text("utf-8"))
    tile["tile_parameters"]["gmin_s"] *= 2
    divergent = tmp_path / "tile.json"
    divergent.write_text(json.dumps(tile), "utf-8")
    with pytest.raises(ValueError, match="tile gmin diverged"):
        generator.build_summary(tile_extract=divergent)


def test_report_rejects_non_object_artifact(tmp_path: Path) -> None:
    assert generator is not None
    invalid = tmp_path / "invalid.json"
    invalid.write_text("[]", "utf-8")
    with pytest.raises(TypeError, match="JSON object"):
        generator.build_summary(partial_sum_extract=invalid)


def test_report_generator_writes_json_markdown_and_diagram(tmp_path: Path) -> None:
    assert generator is not None
    generator.OUT_DIR = tmp_path
    generator.main()
    assert json.loads((tmp_path / _JSON.name).read_text("utf-8")) == generator.build_summary()
    assert (tmp_path / _MARKDOWN.name).read_text("utf-8").startswith("# tile-v1")
    assert "<svg" in (tmp_path / _SVG.name).read_text("utf-8")


def test_readable_report_states_verdict_and_limitations() -> None:
    markdown = _MARKDOWN.read_text("utf-8")
    assert "Gate verdict: `MET`" in markdown
    assert "## Formulas" in markdown
    assert "## Limitations" in markdown
    assert "assumed_profile_parameters" in markdown
