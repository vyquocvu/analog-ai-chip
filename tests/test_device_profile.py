import copy
from pathlib import Path

import pytest

from analog_llm.device_profile import load_device_profile, validate_device_profile

PROFILE = {
    "schema_version": 1,
    "name": "adc-v1",
    "version": "0.1.0",
    "evidence_class": "spice",
    "status": "CIRCUIT_SIMULATED",
    "provenance": {
        "tool": "ngspice",
        "analysis": "tran",
        "sources": ["circuits/adc-v1.cir"],
        "command": "python verification/circuit/extract_adc.py",
        "conditions": {"temperature_c": 27, "supply_v": 1.8},
        "limitations": "Nominal model only.",
    },
    "fields": {
        "enob_bits": {"value": 7.5, "unit": "bits", "evidence_class": "spice"},
        "input_range_v": {"value": 1.0, "unit": "V", "evidence_class": "derived"},
    },
}


def test_spice_profile_can_support_physical_claim() -> None:
    validate_device_profile(PROFILE, physical_claim=True)


def test_assumed_profile_cannot_support_physical_claim() -> None:
    profile = copy.deepcopy(PROFILE)
    profile["evidence_class"] = "assumed"
    with pytest.raises(ValueError, match="assumed profiles"):
        validate_device_profile(profile, physical_claim=True)


def test_physical_claim_requires_field_level_evidence() -> None:
    profile = copy.deepcopy(PROFILE)
    del profile["fields"]
    with pytest.raises(ValueError, match="per-field evidence"):
        validate_device_profile(profile, physical_claim=True)


def test_assumed_field_fails_physical_claim() -> None:
    profile = copy.deepcopy(PROFILE)
    profile["fields"]["enob_bits"]["evidence_class"] = "assumed"
    with pytest.raises(ValueError, match="assumed evidence cannot support physical claims"):
        validate_device_profile(profile, physical_claim=True)


def test_field_missing_unit_fails_closed() -> None:
    profile = copy.deepcopy(PROFILE)
    del profile["fields"]["enob_bits"]["unit"]
    with pytest.raises(ValueError, match="missing required key"):
        validate_device_profile(profile)


def test_invalid_field_evidence_class_fails() -> None:
    profile = copy.deepcopy(PROFILE)
    profile["fields"]["enob_bits"]["evidence_class"] = "measured_readings 2026"
    with pytest.raises(ValueError, match="invalid evidence_class"):
        validate_device_profile(profile)


def test_missing_provenance_fails_closed() -> None:
    profile = copy.deepcopy(PROFILE)
    del profile["provenance"]["sources"]
    with pytest.raises(ValueError, match="sources"):
        validate_device_profile(profile)


def test_repository_ideal_profile_is_valid_but_functional_only() -> None:
    path = Path(__file__).parents[1] / "device_profiles" / "ideal.json"
    profile = load_device_profile(path)
    assert profile["status"] == "FUNCTIONAL_ONLY"
    with pytest.raises(ValueError, match="assumed profiles|FUNCTIONAL_ONLY"):
        load_device_profile(path, physical_claim=True)
