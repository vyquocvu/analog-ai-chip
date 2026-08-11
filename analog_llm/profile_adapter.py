"""Profile → analog_llm configuration adapter (WP1.2).

Maps a validated device profile's physical ``fields`` into ``CrossbarTile``
constructor arguments so the architecture simulator consumes extracted
circuit/device evidence instead of hand-chosen constants.

Mapping contract
----------------
Two profile layouts are supported:

- ``fields`` (physical, e.g. ``crossbar-column-v1.json``): the conductance
  window ``[gmin, gmax]`` is the physical cell range realized by the
  differential pair: balanced zero ``g0_s`` for weight 0 and
  ``g0_s + gscale_s_per_w`` for the strongest ``|w| = 1`` cell. The input/output
  converter envelopes are bounded by the linear rail headroom.
- legacy sections (``dac``/``crossbar``/``adc``, e.g. ``ideal.json``): the
  functional reference maps sections directly onto converter bits, ranges and
  the conductance window.

Fail-closed rules
-----------------
- A ``physical_claim`` profile must pass ``validate_device_profile`` and every
  required physical field must be present in ``fields``.
- Bits (``g_bits``, ``dac_bits``, ``adc_bits``) are programming/converter
  design choices, not device-profile fields: they must be passed explicitly and
  cannot be silently defaulted.
- A legacy-section profile (``ideal.json``) is functional-only and cannot
  support a physical claim.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .device_profile import load_device_profile, validate_device_profile
from .tile import CrossbarTile

# Fields the crossbar-column physics requires to configure a tile.
REQUIRED_FIELDS = frozenset(
    {
        "g0_s",
        "gscale_s_per_w",
        "output_headroom_up_v",
        "output_headroom_down_v",
    }
)


def tile_config_from_profile(
    profile: dict[str, Any] | str | Path,
    *,
    g_bits: int,
    dac_bits: int,
    adc_bits: int,
    physical_claim: bool = True,
) -> dict[str, Any]:
    """Return ``CrossbarTile`` kwargs derived from a validated profile.

    ``profile`` may be a profile dict or a path to a JSON profile. Raises
    ``ValueError`` when required physical fields are missing and when the
    profile cannot support the requested claim (e.g. functional-only).
    """
    if isinstance(profile, (str, Path)):
        profile = load_device_profile(profile, physical_claim=physical_claim)
    else:
        validate_device_profile(profile, physical_claim=physical_claim)

    if physical_claim and "fields" not in profile:
        raise ValueError(
            f"profile {profile.get('name')!r} has no per-field evidence; "
            "a physical tile configuration requires a fields map"
        )

    fields = profile.get("fields")
    if fields is not None:
        missing = REQUIRED_FIELDS - fields.keys()
        if missing:
            raise ValueError(
                f"profile {profile.get('name')!r} missing required physical field(s): "
                f"{sorted(missing)}"
            )
        g0 = float(fields["g0_s"]["value"])
        gscale = float(fields["gscale_s_per_w"]["value"])
        headroom = min(
            float(fields["output_headroom_up_v"]["value"]),
            float(fields["output_headroom_down_v"]["value"]),
        )
        return {
            "g_bits": int(g_bits),
            "dac_bits": int(dac_bits),
            "adc_bits": int(adc_bits),
            "gmin": g0,
            "gmax": g0 + gscale,   # strongest |w|=1 cell = balanced zero + scale
            "vin_max": headroom,
            "vout_max": headroom,
        }

    # Functional reference layout (dac/crossbar/adc sections, ideal.json).
    return _config_from_sections(profile, g_bits=g_bits, dac_bits=dac_bits, adc_bits=adc_bits)


def _config_from_sections(
    profile: dict[str, Any], *, g_bits: int, dac_bits: int, adc_bits: int
) -> dict[str, Any]:
    """Map legacy dac/crossbar/adc sections to tile kwargs (functional)."""
    sections = ("dac", "crossbar", "adc")
    missing = [name for name in sections if name not in profile]
    if missing:
        raise ValueError(f"profile {profile.get('name')!r} missing section(s): {missing}")

    dac_sec, xbar, adc_sec = profile["dac"], profile["crossbar"], profile["adc"]
    adc_kwargs = {}
    if "noise_rms_v" in adc_sec:
        adc_kwargs["adc_noise_std"] = float(adc_sec["noise_rms_v"])
    if "gain" in adc_sec:
        adc_kwargs["adc_gain"] = float(adc_sec["gain"])
    if "offset_v" in adc_sec:
        adc_kwargs["adc_offset"] = float(adc_sec["offset_v"])

    return {
        "g_bits": int(g_bits or xbar["g_bits"]),
        "dac_bits": int(dac_bits or dac_sec["bits"]),
        "adc_bits": int(adc_bits or adc_sec["bits"]),
        "gmin": float(xbar["g_min_s"]),
        "gmax": float(xbar["g_max_s"]),
        "vin_max": float(dac_sec["input_range_v"]),
        "vout_max": float(adc_sec["input_range_v"]),
        **adc_kwargs,
    }


def build_tile_factory(
    profile: dict[str, Any] | str | Path,
    rows: int,
    cols: int,
    *,
    g_bits: int,
    dac_bits: int,
    adc_bits: int,
    physical_claim: bool = True,
) -> Callable[[], CrossbarTile]:
    """Return a deterministic ``() -> CrossbarTile`` factory for the accelerator.

    The factory carries the physical parameters as defaults; runtime tuning
    (seeds, noise) is applied at tile construction by the caller if needed.
    """
    kwargs = tile_config_from_profile(
        profile,
        g_bits=g_bits,
        dac_bits=dac_bits,
        adc_bits=adc_bits,
        physical_claim=physical_claim,
    )

    def factory() -> CrossbarTile:
        return CrossbarTile(rows, cols, **kwargs)

    return factory