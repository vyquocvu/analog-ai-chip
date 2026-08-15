"""Profile → analog_llm configuration adapter (WP1.2).

Maps a validated device profile's physical ``fields`` into ``CrossbarTile``
constructor arguments so the architecture simulator consumes extracted
circuit/device evidence instead of hand-chosen constants.

Mapping contract
----------------
Three profile layouts are supported:

- ``fields`` (physical, e.g. ``crossbar-column-v1.json``): the conductance
  window ``[gmin, gmax]`` is the physical cell range realized by the
  differential pair: balanced zero ``g0_s`` for weight 0 and
  ``g0_s + gscale_s_per_w`` for the strongest ``|w| = 1`` cell. The input/output
  converter envelopes are bounded by the linear rail headroom.
- converter ``fields`` profiles (``dac-r2r-v1.json``, ``adc-sar-v1.json``):
  sourced through ``converter_config_from_profiles`` so the tile's converter
  resolution and voltage envelopes come from validated SPICE evidence rather
  than arbitrary normalized defaults.
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

# Fields the validated DAC/ADC converter profiles must provide so the tile can
# be configured from converter evidence instead of normalized defaults.
REQUIRED_DAC_FIELDS = frozenset({"bits", "full_scale_v"})
REQUIRED_ADC_FIELDS = frozenset({"bits", "input_range_v", "quantization_error_v"})


def converter_config_from_profiles(
    dac_profile: dict[str, Any] | str | Path,
    adc_profile: dict[str, Any] | str | Path,
    *,
    physical_claim: bool = True,
) -> dict[str, Any]:
    """Return converter parameters sourced from validated DAC/ADC profiles.

    Reads ``dac_bits``/``adc_bits`` and the voltage envelopes from the
    converter profiles' ``fields`` (``dac-r2r-v1``, ``adc-sar-v1``) so a tile
    can run on SPICE-extracted converter evidence. Fails closed when a required
    converter field is missing or the profile cannot support the claim.
    """
    dac = _load_converter_profile(dac_profile, physical_claim=physical_claim)
    adc = _load_converter_profile(adc_profile, physical_claim=physical_claim)
    dac_fields = dac.get("fields")
    adc_fields = adc.get("fields")
    if physical_claim and (dac_fields is None or adc_fields is None):
        raise ValueError(
            "converter profiles require per-field evidence to configure a tile"
        )
    missing_dac = REQUIRED_DAC_FIELDS - set(dac_fields or {})
    missing_adc = REQUIRED_ADC_FIELDS - set(adc_fields or {})
    if missing_dac or missing_adc:
        raise ValueError(
            f"converter profiles missing required field(s): "
            f"DAC {sorted(missing_dac)}, ADC {sorted(missing_adc)}"
        )
    return {
        "dac_bits": int(dac_fields["bits"]["value"]),
        "adc_bits": int(adc_fields["bits"]["value"]),
        "vin_max": float(dac_fields["full_scale_v"]["value"]),
        "vout_max": float(adc_fields["input_range_v"]["value"]),
    }


def _load_converter_profile(
    profile: dict[str, Any] | str | Path, *, physical_claim: bool
) -> dict[str, Any]:
    """Load a converter profile from a path, or validate an in-memory dict."""
    if isinstance(profile, (str, Path)):
        return load_device_profile(profile, physical_claim=physical_claim)
    validate_device_profile(profile, physical_claim=physical_claim)
    return profile


CROSSBAR_NONIDEALITY_FIELDS = frozenset(
    {
        "sigma_prog_rel",
        "sigma_read_rel",
        "p_stuck_hrs",
        "p_stuck_lrs",
        "drift_exponent_nu_min",
        "drift_exponent_nu_max",
        "iv_non_linearity_beta",
        "r_wire_ohm",
        "v_read_max_v",
    }
)


def nonideality_config_from_profile(
    profile: dict[str, Any] | str | Path,
    *,
    physical_claim: bool = False,
    drift_time_s: float = 0.0,
) -> dict[str, float]:
    """Extract physical crossbar non-ideality parameters from a validated profile.

    Returns a dict with float values for:
    - ``sigma_prog_rel``
    - ``sigma_read_rel``
    - ``p_stuck_hrs``
    - ``p_stuck_lrs``
    - ``drift_exponent_nu_min``
    - ``drift_exponent_nu_max``
    - ``drift_time_s``
    - ``iv_non_linearity_beta``
    - ``v_read_max``
    - ``r_wire_ohm``

    Any field not present in the profile defaults to ``0.0`` (or ``0.25`` for ``v_read_max``).
    """
    if isinstance(profile, (str, Path)):
        p = load_device_profile(profile, physical_claim=physical_claim)
    else:
        validate_device_profile(profile, physical_claim=physical_claim)
        p = profile

    fields = p.get("fields", {})
    cfg: dict[str, float] = {}
    for field_name in sorted(CROSSBAR_NONIDEALITY_FIELDS):
        if field_name == "v_read_max_v":
            cfg["v_read_max"] = float(fields[field_name]["value"]) if field_name in fields else 0.25
        elif field_name in fields:
            cfg[field_name] = float(fields[field_name]["value"])
        else:
            cfg[field_name] = 0.0
    cfg["drift_time_s"] = float(drift_time_s)
    return cfg


def tile_config_from_profile(
    profile: dict[str, Any] | str | Path,
    *,
    g_bits: int,
    dac_bits: int,
    adc_bits: int,
    physical_claim: bool = True,
    include_nonidealities: bool = False,
    drift_time_s: float = 0.0,
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
        cfg = {
            "g_bits": int(g_bits),
            "dac_bits": int(dac_bits),
            "adc_bits": int(adc_bits),
            "gmin": g0,
            "gmax": g0 + gscale,   # strongest |w|=1 cell = balanced zero + scale
            "vin_max": headroom,
            "vout_max": headroom,
        }
        if include_nonidealities:
            cfg.update(
                nonideality_config_from_profile(
                    profile, physical_claim=physical_claim, drift_time_s=drift_time_s
                )
            )
        return cfg

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
    include_nonidealities: bool = False,
    drift_time_s: float = 0.0,
    **extra_tile_kwargs: Any,
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
        include_nonidealities=include_nonidealities,
        drift_time_s=drift_time_s,
    )
    kwargs.update(extra_tile_kwargs)

    def factory() -> CrossbarTile:
        return CrossbarTile(rows, cols, **kwargs)

    return factory


def build_tile_factory_from_converter_profiles(
    column_profile: dict[str, Any] | str | Path,
    dac_profile: dict[str, Any] | str | Path,
    adc_profile: dict[str, Any] | str | Path,
    rows: int,
    cols: int,
    *,
    g_bits: int,
    physical_claim: bool = True,
    include_nonidealities: bool = False,
    drift_time_s: float = 0.0,
    **extra_tile_kwargs: Any,
) -> Callable[[], CrossbarTile]:
    """Return a tile factory whose converter parameters come from the profiles.

    The conductance window ``[gmin, gmax]`` comes from the crossbar-column
    profile (as in ``tile_config_from_profile``); the converter bits and
    voltage envelopes come from the validated DAC/ADC profiles via
    ``converter_config_from_profiles``. Nothing on the converter path is a
    hand-picked normalized default (gate R2 exit).
    """
    base = tile_config_from_profile(
        column_profile,
        g_bits=g_bits,
        dac_bits=1,  # overridden below; only gmin/gmax/g_bits are kept
        adc_bits=1,
        physical_claim=physical_claim,
        include_nonidealities=include_nonidealities,
        drift_time_s=drift_time_s,
    )
    converter = converter_config_from_profiles(
        dac_profile, adc_profile, physical_claim=physical_claim
    )
    kwargs = {"g_bits": base["g_bits"], "gmin": base["gmin"], "gmax": base["gmax"]}
    if include_nonidealities:
        for field_name in (
            "sigma_prog_rel",
            "sigma_read_rel",
            "p_stuck_hrs",
            "p_stuck_lrs",
            "drift_exponent_nu_min",
            "drift_exponent_nu_max",
            "drift_time_s",
            "iv_non_linearity_beta",
            "v_read_max",
            "r_wire_ohm",
        ):
            if field_name in base:
                kwargs[field_name] = base[field_name]
    kwargs.update(converter)
    kwargs.update(extra_tile_kwargs)

    def factory() -> CrossbarTile:
        return CrossbarTile(rows, cols, **kwargs)

    return factory