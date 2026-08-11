"""WP2.1 — first SPICE-backed DAC profile: dac-r2r-v1.

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
_PROFILE = _DEVICE_PROFILES / "dac-r2r-v1.json"
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "dac-r2r-v1-extract.json"
_EXTRACTOR = _REPO / "verification" / "circuit" / "extract_dac_r2r.py"

REQUIRED_FIELDS = {
    "bits",
    "r_ohm",
    "vref_v",
    "lsb_v",
    "full_scale_v",
    "offset_v",
    "gain_v_per_v",
    "max_inl_v",
    "max_dnl_v",
    "max_abs_error_v",
    "rth_ohm",
}


def _load_extractor():
    try:
        spec = importlib.util.spec_from_file_location("extract_dac_r2r", _EXTRACTOR)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:  # noqa: BLE001 - missing engine/lib => skip
        return None


extractor = _load_extractor()


def test_dac_profile_exists_and_is_spice_backed() -> None:
    profile = load_device_profile(_PROFILE, physical_claim=True)
    assert profile["name"] == "dac-r2r-v1"
    assert profile["evidence_class"] == "spice"
    assert profile["status"] == "CIRCUIT_SIMULATED"


def test_dac_profile_provenance_is_complete() -> None:
    profile = load_device_profile(_PROFILE)
    for key in ("tool", "analysis", "sources", "command", "conditions", "limitations"):
        assert key in profile["provenance"], f"provenance missing {key}"
    assert any("0009" in source for source in profile["provenance"]["sources"])


def test_dac_profile_fields_carry_evidence_classes() -> None:
    profile = load_device_profile(_PROFILE)
    fields = profile["fields"]
    assert set(fields) == REQUIRED_FIELDS
    for name, field in fields.items():
        for key in ("value", "unit", "evidence_class"):
            assert key in field, f"field {name!r} missing {key}"
        assert field["evidence_class"] in EVIDENCE_CLASSES, name


def test_dac_profile_hand_reference_values() -> None:
    profile = load_device_profile(_PROFILE)
    fields = profile["fields"]
    bits = fields["bits"]["value"]
    vref = fields["vref_v"]["value"]
    assert bits == 4
    assert vref == pytest.approx(2.5)
    assert fields["lsb_v"]["value"] == pytest.approx(vref / (2**bits))
    assert fields["full_scale_v"]["value"] == pytest.approx(vref * (2**bits - 1) / (2**bits))
    assert fields["offset_v"]["value"] == pytest.approx(0.0, abs=1e-15)
    assert fields["gain_v_per_v"]["value"] == pytest.approx(1.0)


def test_dac_profile_rth_is_two_r() -> None:
    profile = load_device_profile(_PROFILE)
    r_ohm = profile["fields"]["r_ohm"]["value"]
    assert profile["fields"]["rth_ohm"]["value"] == pytest.approx(2 * r_ohm)
    assert profile["fields"]["rth_ohm"]["evidence_class"] == "spice"


def test_dac_extract_settling_is_assumed_sensitivity() -> None:
    """The settling study uses an assumed CL, so it lives in the extract JSON
    only and is not a physical profile field."""
    extract = json.loads(_EXTRACT.read_text("utf-8"))
    profile = load_device_profile(_PROFILE)
    assert "settling" in extract
    rows = extract["settling"]
    assert len(rows) == 3
    for row in rows:
        assert row["settle_time_s"] == pytest.approx(row["hand_tau_s"], rel=0.05)
    assert "settling" not in profile
    assert "cl_farad" not in profile["fields"]
    assert any("ASSUMED" in line for line in [profile["provenance"]["limitations"]])


def test_dac_profile_extract_results_are_committed_and_consistent() -> None:
    extract = json.loads(_EXTRACT.read_text("utf-8"))
    assert len(extract["sweep_v"]) == 2 ** extract["bits"]
    profile = load_device_profile(_PROFILE)
    for name in REQUIRED_FIELDS:
        assert extract[name] == pytest.approx(profile["fields"][name]["value"], rel=1e-9), name


@pytest.mark.skipif(extractor is None, reason="PySpice/ngspice not available")
def test_dac_extraction_reproduces_committed_profile() -> None:
    measured = extractor.measure()
    profile = load_device_profile(_PROFILE)
    for name, field in profile["fields"].items():
        assert name in measured, f"committed field {name!r} not produced by extractor"
        assert measured[name] == pytest.approx(field["value"], rel=2e-3, abs=1e-12), name
    # raw sweep must match the committed extract too
    extract = json.loads(_EXTRACT.read_text("utf-8"))
    assert measured["sweep_v"] == pytest.approx(extract["sweep_v"], rel=2e-3, abs=1e-12)
    # settling rows must reproduce within tolerance
    settling = extractor.measure_settling()
    assert settling == pytest.approx(extract["settling"], rel=5e-2, abs=1e-9)
