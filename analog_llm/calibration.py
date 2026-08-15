"""Profile-driven output calibration for behavioral crossbar tiles."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .device_profile import load_device_profile, validate_device_profile

REQUIRED_CALIBRATION_FIELDS = frozenset({"correction_gain", "correction_offset_v"})


@dataclass(frozen=True)
class OutputCalibration:
    """Affine digital correction ``y_cal = gain * y_raw + offset_v``."""

    gain: float
    offset_v: float
    profile_name: str
    profile_version: str

    def apply(self, values: ArrayLike) -> NDArray[np.float64]:
        raw = np.asarray(values, dtype=np.float64)
        if np.any(~np.isfinite(raw)):
            raise ValueError("calibration inputs must be finite")
        return self.gain * raw + self.offset_v


def output_calibration_from_profile(
    profile: dict[str, Any] | str | Path,
    *,
    physical_claim: bool = False,
) -> OutputCalibration:
    """Load an affine output correction from a validated evidence profile.

    ``SYSTEM_SIMULATED`` calibration can close a system regression gate but
    cannot support a physical calibration claim. Such a request fails closed.
    """
    if isinstance(profile, (str, Path)):
        loaded = load_device_profile(profile, physical_claim=False)
    else:
        validate_device_profile(profile, physical_claim=False)
        loaded = profile

    if physical_claim and loaded["status"] in {"FUNCTIONAL_ONLY", "SYSTEM_SIMULATED"}:
        raise ValueError(f"{loaded['status']} calibration profile cannot support a physical claim")
    if physical_claim:
        validate_device_profile(loaded, physical_claim=True)

    fields = loaded.get("fields")
    if not isinstance(fields, dict):
        raise TypeError("calibration profile requires a fields map")
    missing = REQUIRED_CALIBRATION_FIELDS - fields.keys()
    if missing:
        raise ValueError(f"calibration profile missing required field(s): {sorted(missing)}")

    gain = float(fields["correction_gain"]["value"])
    offset_v = float(fields["correction_offset_v"]["value"])
    if not np.isfinite(gain) or gain <= 0.0:
        raise ValueError("calibration correction_gain must be finite and positive")
    if not np.isfinite(offset_v):
        raise ValueError("calibration correction_offset_v must be finite")

    return OutputCalibration(
        gain=gain,
        offset_v=offset_v,
        profile_name=str(loaded["name"]),
        profile_version=str(loaded["version"]),
    )
