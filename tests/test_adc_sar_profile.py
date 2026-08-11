"""WP2.1 — second SPICE-backed converter profile: adc-sar-v1.

Always-on tests validate the committed profile and the fail-closed field-level
evidence rules. The engine-gated test re-runs the deterministic extraction and
checks it reproduces the committed profile within tolerance.
"""

import importlib.util
import json
from pathlib import Path

import pytest

from analog_llm.device_profile import EVIDENCE_CLASSES, load_device_profile

_REPO = Path(__file__).resolve().parent.parent
_DEVICE_PROFILES = _REPO / "device_profiles"
_PROFILE = _DEVICE_PROFILES / "adc-sar-v1.json"
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "adc-sar-v1-extract.json"
_EXTRACTOR = _REPO / "verification" / "circuit" / "extract_adc_sar.py"

REQUIRED_FIELDS = {
    "bits",
    "r_ohm",
    "vref_v",
    "lsb_v",
    "input_range_v",
    "quantization_error_v",
    "max_code_error_codes",
    "max_abs_error_v",
}


def _load_extractor():
    try:
        spec = importlib.util.spec_from_file_location("extract_adc_sar", _EXTRACTOR)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:  # noqa: BLE001 - missing engine/lib => skip
        return None


extractor = _load_extractor()


def test_adc_profile_exists_and_is_spice_backed() -> None:
    profile = load_device_profile(_PROFILE, physical_claim=True)
    assert profile["name"] == "adc-sar-v1"
    assert profile["evidence_class"] == "spice"
    assert profile["status"] == "CIRCUIT_SIMULATED"


def test_adc_profile_provenance_is_complete() -> None:
    profile = load_device_profile(_PROFILE)
    for key in ("tool", "analysis", "sources", "command", "conditions", "limitations"):
        assert key in profile["provenance"], f"provenance missing {key}"
    assert any("0010" in source for source in profile["provenance"]["sources"])


def test_adc_profile_fields_carry_evidence_classes() -> None:
    profile = load_device_profile(_PROFILE)
    fields = profile["fields"]
    assert set(fields) == REQUIRED_FIELDS
    for name, field in fields.items():
        for key in ("value", "unit", "evidence_class"):
            assert key in field, f"field {name!r} missing {key}"
        assert field["evidence_class"] in EVIDENCE_CLASSES, name


def test_adc_profile_hand_reference_values() -> None:
    profile = load_device_profile(_PROFILE)
    fields = profile["fields"]
    bits = fields["bits"]["value"]
    vref = fields["vref_v"]["value"]
    assert bits == 4
    assert vref == pytest.approx(2.5)
    assert fields["lsb_v"]["value"] == pytest.approx(vref / (2**bits))
    assert fields["input_range_v"]["value"] == pytest.approx(vref)
    assert fields["quantization_error_v"]["value"] == pytest.approx(vref / (2**bits))


def test_adc_profile_spice_evidence_shows_exact_transfer() -> None:
    profile = load_device_profile(_PROFILE)
    fields = profile["fields"]
    assert fields["max_code_error_codes"]["evidence_class"] == "spice"
    assert fields["max_abs_error_v"]["evidence_class"] == "spice"
    assert fields["max_code_error_codes"]["value"] == 0
    assert fields["max_abs_error_v"]["value"] == pytest.approx(
        fields["lsb_v"]["value"], abs=1e-12
    )


def test_adc_extract_studies_are_not_profile_fields() -> None:
    """Assumed-CL settling, functional ENOB and supply deviation are extract-only
    sensitivity/functional studies, not physical profile fields."""
    extract = json.loads(_EXTRACT.read_text("utf-8"))
    profile = load_device_profile(_PROFILE)
    assert "settling" in extract
    assert "enob" in extract
    assert "supply_sensitivity" in extract
    assert "settling" not in profile
    assert "enob" not in profile
    assert "cl_farad" not in profile["fields"]
    assert any("ASSUMED" in line for line in [profile["provenance"]["limitations"]])


def test_adc_extract_transfer_matches_hand_reference() -> None:
    extract = json.loads(_EXTRACT.read_text("utf-8"))
    transfer = extract["transfer"]
    assert len(transfer) == 129
    for row in transfer:
        assert row["code_spice"] == row["code_hand"]
    assert extract["max_code_error_codes"] == 0
    assert extract["max_abs_error_v"] <= extract["lsb_v"] + 1e-12


def test_adc_profile_extract_results_are_committed_and_consistent() -> None:
    extract = json.loads(_EXTRACT.read_text("utf-8"))
    profile = load_device_profile(_PROFILE)
    for name in REQUIRED_FIELDS:
        assert extract[name] == pytest.approx(profile["fields"][name]["value"], rel=1e-9), name


@pytest.mark.skipif(extractor is None, reason="PySpice/ngspice not available")
def test_adc_extraction_reproduces_committed_profile() -> None:
    measured = extractor.measure()
    profile = load_device_profile(_PROFILE)
    for name, field in profile["fields"].items():
        assert name in measured, f"committed field {name!r} not produced by extractor"
        assert measured[name] == pytest.approx(field["value"], rel=2e-3, abs=1e-12), name
    # raw transfer must match the committed extract too
    extract = json.loads(_EXTRACT.read_text("utf-8"))
    assert measured["transfer"] == pytest.approx(extract["transfer"], rel=2e-3, abs=1e-12)
    # settling rows must reproduce within tolerance
    settling = extractor.measure_settling()
    assert settling == pytest.approx(extract["settling"], rel=5e-2, abs=1e-9)
