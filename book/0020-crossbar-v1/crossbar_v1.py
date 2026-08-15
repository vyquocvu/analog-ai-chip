r"""Chapter 0020 — Crossbar-v1 Profile Publication & Gate R4 Close.

Cross-validates `device_profiles/crossbar-v1.json` against the underlying
circuit extracts (0015 through 0019) and verifies adapter compliance with `analog_llm`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from analog_llm.device_profile import load_device_profile, validate_device_profile
from analog_llm.profile_adapter import tile_config_from_profile

_REPO = Path(__file__).resolve().parents[2]
_PROFILE_PATH = _REPO / "device_profiles" / "crossbar-v1.json"
_EXTRACT_0015 = _REPO / "verification" / "circuit" / "results" / "conductance-model-0015-extract.json"
_EXTRACT_0016 = _REPO / "verification" / "circuit" / "results" / "variation-0016-extract.json"
_EXTRACT_0017 = _REPO / "verification" / "circuit" / "results" / "ir-drop-0017-extract.json"
_EXTRACT_0018 = _REPO / "verification" / "circuit" / "results" / "parasitics-0018-extract.json"
_EXTRACT_0019 = _REPO / "verification" / "circuit" / "results" / "drift-faults-0019-extract.json"


def verify_crossbar_v1_profile() -> dict[str, Any]:
    """Load profile, assert schema validity, crosscheck with extract ledger, and verify adapter."""
    # 1. Load and validate profile schema
    profile = load_device_profile(_PROFILE_PATH, physical_claim=False)
    validate_device_profile(profile, physical_claim=False)

    fields = profile["fields"]

    # 2. Crosscheck 0015 extract
    with open(_EXTRACT_0015, "r", encoding="utf-8") as f:
        e15 = json.load(f)
    assert abs(fields["gmin_s"]["value"] - e15["model_parameters"]["g_min_uS"] * 1e-6) < 1e-12
    assert abs(fields["gmax_s"]["value"] - e15["model_parameters"]["g_max_uS"] * 1e-6) < 1e-12
    assert abs(fields["span_s"]["value"] - e15["model_parameters"]["span_uS"] * 1e-6) < 1e-12
    assert abs(fields["dynamic_range_ratio"]["value"] - e15["model_parameters"]["dynamic_range_ratio"]) < 1e-9

    # 3. Crosscheck 0016 extract
    with open(_EXTRACT_0016, "r", encoding="utf-8") as f:
        e16 = json.load(f)
    assert abs(fields["sigma_prog_rel"]["value"] - e16["assumptions"]["sigma_prog_rel"]) < 1e-9
    assert abs(fields["sigma_read_rel"]["value"] - e16["assumptions"]["sigma_read_rel"]) < 1e-9
    assert abs(fields["zero_weight_noise_floor_std"]["value"] - e16["summary"]["zero_weight_noise_floor_std"]) < 1e-9

    # 4. Crosscheck 0017 extract
    with open(_EXTRACT_0017, "r", encoding="utf-8") as f:
        e17 = json.load(f)
    assert abs(fields["mvm_error_32x32_1ohm_pct"]["value"] - e17["summary"]["error_at_32x32_1ohm_pct"]) < 1e-6

    # 5. Crosscheck 0018 extract
    with open(_EXTRACT_0018, "r", encoding="utf-8") as f:
        e18 = json.load(f)
    assert abs(fields["t_settle_1pct_ps"]["value"] - e18["summary"]["settling_time_16x16_ps"]) < 1e-6
    assert abs(fields["f_max_ghz"]["value"] - e18["summary"]["f_max_16x16_ghz"]) < 1e-6

    # 6. Crosscheck 0019 extract
    with open(_EXTRACT_0019, "r", encoding="utf-8") as f:
        e19 = json.load(f)
    assert abs(fields["max_drift_loss_1year_pct"]["value"] - e19["summary"]["max_drift_loss_1year_pct"]) < 1e-6
    assert abs(fields["max_iv_distortion_pct"]["value"] - e19["summary"]["max_iv_distortion_pct"]) < 1e-6

    # 7. Test adapter consumption
    tile_kwargs = tile_config_from_profile(_PROFILE_PATH, g_bits=4, dac_bits=4, adc_bits=4, physical_claim=False)
    assert tile_kwargs["gmin"] == fields["gmin_s"]["value"]
    assert tile_kwargs["gmax"] == fields["gmax_s"]["value"]

    return {
        "status": "VALIDATED",
        "profile_name": profile["name"],
        "num_fields": len(fields),
        "tile_kwargs": tile_kwargs,
    }


def main() -> None:
    print("Verifying Chapter 0020 crossbar-v1 profile and extracts...")
    res = verify_crossbar_v1_profile()
    print(f"  Profile Name: {res['profile_name']}")
    print(f"  Total Fields: {res['num_fields']}")
    print(f"  Status: {res['status']}")


if __name__ == "__main__":
    main()
