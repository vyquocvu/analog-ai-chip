"""WP1.3 — reproducible verification summary: R1 gate exit.

Always-on tests validate the committed artifacts end to end:

    extract results -> validated profile -> profile_adapter -> tile config -> summary

The gate-exit condition is that the summary is *reproducible*: every committed
profile value must be traceable to the raw extract result, the tile
configuration must be derived by the adapter (no manual constants), and the
generated report must be deterministic.
"""

import importlib.util
import json
from pathlib import Path

import pytest

from analog_llm.device_profile import load_device_profile
from analog_llm.profile_adapter import tile_config_from_profile

_REPO = Path(__file__).resolve().parent.parent
_SUMMARY = _REPO / "verification" / "reports" / "generate_crossbar_column_summary.py"
_PROFILE = _REPO / "device_profiles" / "crossbar-column-v1.json"
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "crossbar-column-v1-extract.json"

REQUIRED_FIELDS = {
    "transimpedance_gain_ohm",
    "rf_nominal_ohm",
    "gain_v_per_v_per_unit_weight",
    "dc_error_v_max",
    "vref_v",
    "g0_s",
    "gscale_s_per_w",
    "output_headroom_up_v",
    "output_headroom_down_v",
    "differential_mapping_error_s_max",
}


def _load_summary_module():
    spec = importlib.util.spec_from_file_location("generate_crossbar_column_summary", _SUMMARY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_profile_is_traceable_to_extract_results() -> None:
    """Every committed profile value must match the raw SPICE extract."""
    profile = load_device_profile(_PROFILE, physical_claim=True)
    measured = json.loads(_EXTRACT.read_text("utf-8"))
    for name, field in profile["fields"].items():
        assert name in measured, f"field {name!r} not extracted"
        assert field["value"] == pytest.approx(measured[name], rel=0, abs=1e-12), name
    assert set(profile["fields"]) == REQUIRED_FIELDS


def test_adapter_derives_tile_config_from_profile_fields() -> None:
    """The gate forbids manual copy-paste of constants in the proof path."""
    profile = load_device_profile(_PROFILE, physical_claim=True)
    fields = profile["fields"]
    cfg = tile_config_from_profile(profile, g_bits=6, dac_bits=8, adc_bits=8)
    assert cfg["gmin"] == pytest.approx(fields["g0_s"]["value"])
    assert cfg["gmax"] == pytest.approx(fields["g0_s"]["value"] + fields["gscale_s_per_w"]["value"])
    headroom = min(
        fields["output_headroom_up_v"]["value"], fields["output_headroom_down_v"]["value"]
    )
    assert cfg["vin_max"] == pytest.approx(headroom)
    assert cfg["vout_max"] == pytest.approx(headroom)
    # No hand equations elsewhere: values enter the summary only via the adapter.
    assert "gmin" in cfg and "gmax" in cfg


def test_summary_is_deterministic() -> None:
    mod = _load_summary_module()
    first = mod.build_summary()
    second = mod.build_summary()
    assert first == second
    assert first["name"] == "crossbar-column-v1-verification-summary"
    assert first["profile"]["validation"].startswith("passed")


def test_summary_classifies_evidence_by_bucket_and_component() -> None:
    mod = _load_summary_module()
    summary = mod.build_summary()
    counts = summary["coverage"]["counts"]
    assert counts["VERIFIED_BY_SPICE"] == 3  # transimpedance gain, gain, dc_error
    assert counts["DERIVED"] == 7
    assert counts["ASSUMED"] == 0
    # Every field is bucketed and assigned to a component.
    all_fields = {
        e["field"] for label in ("VERIFIED_BY_SPICE", "DERIVED", "ASSUMED") for e in summary["evidence"][label]
    }
    assert all_fields == REQUIRED_FIELDS
    components = set(summary["coverage"]["by_component"])
    assert components == {"readout", "differential_mapping", "conductance_cell", "rail_headroom"}


def test_summary_values_link_to_profile_artifacts() -> None:
    mod = _load_summary_module()
    summary = mod.build_summary()
    for label in ("VERIFIED_BY_SPICE", "DERIVED", "ASSUMED"):
        for entry in summary["evidence"][label]:
            assert entry["source"].startswith("device_profiles/crossbar-column-v1.json")
            field = load_device_profile(_PROFILE)["fields"][entry["field"]]
            assert entry["value"] == pytest.approx(field["value"])
            assert entry["evidence_class"] == field["evidence_class"]


def test_summary_tile_config_links_to_adapter() -> None:
    mod = _load_summary_module()
    summary = mod.build_summary()
    profile = load_device_profile(_PROFILE, physical_claim=True)
    cfg = tile_config_from_profile(profile, g_bits=mod.G_BITS, dac_bits=mod.DAC_BITS, adc_bits=mod.ADC_BITS)
    for key in ("g_bits", "dac_bits", "adc_bits", "gmin", "gmax", "vin_max", "vout_max"):
        assert summary["tile_config"]["kwargs"][key] == pytest.approx(cfg[key]), key
    deriv = summary["tile_config"]["derivation"]
    assert deriv["gmin"]["from_fields"] == ["g0_s"]
    assert deriv["gmax"]["from_fields"] == ["g0_s", "gscale_s_per_w"]


def test_summary_fails_closed_on_functional_only_profile() -> None:
    """A functional-only (ideal) profile cannot produce a physical summary."""
    mod = _load_summary_module()
    ideal = _REPO / "device_profiles" / "ideal.json"
    with pytest.raises(ValueError):
        mod.build_summary(profile_path=ideal)


def test_readable_report_is_deterministic_and_covers_all_sections() -> None:
    mod = _load_summary_module()
    markdown = mod.render_markdown(mod.build_summary())
    assert markdown == mod.render_markdown(mod.build_summary())
    for section in ("## Profile", "## Coverage", "## Evidence", "## Adapter-derived tile configuration"):
        assert section in markdown


def test_generator_script_writes_expected_artifacts(tmp_path: Path) -> None:
    """The CLI writes machine-readable + readable report with stable JSON."""
    mod = _load_summary_module()
    mod.OUT_DIR = tmp_path
    mod.main()
    json_path = tmp_path / "crossbar-column-v1-summary.json"
    md_path = tmp_path / "crossbar-column-v1-summary.md"
    assert json_path.exists() and md_path.exists()
    summary = json.loads(json_path.read_text("utf-8"))
    assert summary == mod.build_summary()