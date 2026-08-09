"""Validation for circuit/device profiles consumed by the architecture simulator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

EVIDENCE_CLASSES = {"measured", "spice", "derived", "assumed"}
STATUSES = {
    "FUNCTIONAL_ONLY",
    "CIRCUIT_SIMULATED",
    "VARIATION_SIMULATED",
    "SYSTEM_SIMULATED",
    "HARDWARE_MEASURED",
}


def validate_device_profile(profile: dict[str, Any], *, physical_claim: bool = False) -> None:
    """Fail closed when a profile is incomplete or cannot support the requested claim."""
    required = {"schema_version", "name", "version", "evidence_class", "status", "provenance"}
    missing = required - profile.keys()
    if missing:
        raise ValueError(f"device profile missing required fields: {sorted(missing)}")

    evidence_class = profile["evidence_class"]
    if evidence_class not in EVIDENCE_CLASSES:
        raise ValueError(f"invalid evidence_class: {evidence_class!r}")
    if profile["status"] not in STATUSES:
        raise ValueError(f"invalid status: {profile['status']!r}")

    provenance = profile["provenance"]
    if not isinstance(provenance, dict):
        raise ValueError("provenance must be an object")
    for field in ("tool", "analysis", "sources", "conditions", "limitations"):
        if field not in provenance:
            raise ValueError(f"provenance missing required field: {field}")
    if not isinstance(provenance["sources"], list) or not provenance["sources"]:
        raise ValueError("provenance.sources must contain at least one source")

    if physical_claim and evidence_class == "assumed":
        raise ValueError("assumed profiles cannot support physical claims")
    if physical_claim and profile["status"] == "FUNCTIONAL_ONLY":
        raise ValueError("FUNCTIONAL_ONLY profiles cannot support physical claims")


def load_device_profile(path: str | Path, *, physical_claim: bool = False) -> dict[str, Any]:
    """Load and validate one JSON device profile."""
    profile_path = Path(path)
    with profile_path.open("r", encoding="utf-8") as handle:
        profile = json.load(handle)
    if not isinstance(profile, dict):
        raise ValueError("device profile root must be an object")
    validate_device_profile(profile, physical_claim=physical_claim)
    return profile
