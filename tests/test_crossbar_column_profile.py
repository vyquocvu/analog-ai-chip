"""WP1.1 — first SPICE-backed device profile: crossbar-column-v1.

Always-on tests validate the committed profile and the fail-closed field-level
evidence rules. The engine-gated test re-runs the deterministic extraction and
checks it reproduces the committed profile within tolerance.
"""

import importlib.util
from pathlib import Path

import pytest

from analog_llm.device_profile import EVIDENCE_CLASSES, load_device_profile

_DEVICE_PROFILES = Path(__file__).resolve().parent.parent / "device_profiles"
_PROFILE = _DEVICE_PROFILES / "crossbar-column-v1.json"
_EXTRACTOR = (
    Path(__file__).resolve().parent.parent / "verification" / "circuit" / "extract_crossbar_column.py"
)

# Fields the profile must carry to support the physical claim.
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


def _load_extractor():
    try:
        spec = importlib.util.spec_from_file_location("extract_crossbar_column", _EXTRACTOR)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:  # noqa: BLE001 - missing engine/lib => skip
        return None


extractor = _load_extractor()


def _engine_ok():
    """True when a real ngspice operating-point solve runs through the extractor."""
    if extractor is None:
        return False
    try:
        extractor.run_column([extractor.VREF, extractor.VREF], [0.0, 0.0])
        return True
    except Exception:  # noqa: BLE001 - ngspice library missing => skip
        return False


ENGINE_OK = _engine_ok()


def test_crossbar_column_profile_exists_and_is_spice_backed() -> None:
    profile = load_device_profile(_PROFILE, physical_claim=True)
    assert profile["name"] == "crossbar-column-v1"
    assert profile["evidence_class"] == "spice"
    assert profile["status"] == "CIRCUIT_SIMULATED"


def test_crossbar_column_profile_provenance_is_complete() -> None:
    profile = load_device_profile(_PROFILE)
    for key in ("tool", "analysis", "sources", "command", "conditions", "limitations"):
        assert key in profile["provenance"], f"provenance missing {key}"
    assert any("0007" in source for source in profile["provenance"]["sources"])


def test_crossbar_column_profile_fields_carry_evidence_classes() -> None:
    profile = load_device_profile(_PROFILE)
    fields = profile["fields"]
    assert set(fields) >= REQUIRED_FIELDS, f"missing fields: {REQUIRED_FIELDS - set(fields)}"
    for name, field in fields.items():
        for key in ("value", "unit", "evidence_class"):
            assert key in field, f"field {name!r} missing {key}"
        assert field["evidence_class"] in EVIDENCE_CLASSES, name


@pytest.mark.skipif(extractor is None or not ENGINE_OK, reason="PySpice/ngspice not available")
def test_extraction_reproduces_committed_profile() -> None:
    measured = extractor.measure()
    profile = load_device_profile(_PROFILE)
    for name, field in profile["fields"].items():
        assert name in measured, f"committed field {name!r} not produced by extractor"
        assert measured[name] == pytest.approx(field["value"], rel=2e-3, abs=1e-12), name