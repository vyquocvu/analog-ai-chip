"""WP1.2 — profile → analog_llm tile/system configuration adapter.

The adapter maps a validated device profile's physical fields into
``CrossbarTile`` configuration. It is fail-closed: required physical fields
must be present and a functional-only profile cannot drive a physical tile
configuration. Same profile in -> same configuration out, deterministically.
"""

from pathlib import Path

import pytest

from analog_llm.profile_adapter import (
    REQUIRED_FIELDS,
    build_tile_factory,
    tile_config_from_profile,
)

_DEVICE_PROFILES = Path(__file__).resolve().parent.parent / "device_profiles"
_PROFILE = _DEVICE_PROFILES / "crossbar-column-v1.json"
_FUNCTIONAL = _DEVICE_PROFILES / "ideal.json"

_BITS = {"g_bits": 8, "dac_bits": 8, "adc_bits": 8}


def _config(**bits) -> dict:
    return tile_config_from_profile(_PROFILE, **{**_BITS, **bits})


def test_same_profile_produces_same_config_deterministically() -> None:
    first = _config()
    second = _config()
    assert first == second
    assert isinstance(second["gmin"], float)
    assert isinstance(second["gmax"], float)


def test_config_maps_profile_fields_to_tile_parameters() -> None:
    config = _config()
    # gmin/gmax trace straight to the 0007 conductance window:
    # gmin = balanced zero G0, gmax = G0 + GSCALE (strongest |w|=1 cell).
    assert config["gmin"] == pytest.approx(1.0e-4, rel=1e-6)
    assert config["gmax"] == pytest.approx(2.0e-4, rel=1e-6)
    # the linear output envelope is bounded by the rail headroom
    assert config["vin_max"] == pytest.approx(2.5, rel=1e-6)
    assert config["vout_max"] == pytest.approx(2.5, rel=1e-6)


def test_same_profile_config_builds_matching_tiles() -> None:
    w = [[1.0, 0.5], [-0.25, 1.0]]

    ta = build_tile_factory(_PROFILE, 2, 2, **_BITS)()
    ta.program(w)
    a = ta.forward([0.6, -0.8])

    tb = build_tile_factory(_PROFILE, 2, 2, **_BITS)()
    tb.program(w)
    b = tb.forward([0.6, -0.8])

    assert (a == b).all()
    assert a.shape == (2,)


def test_profile_requires_all_physical_fields_present() -> None:
    from analog_llm.device_profile import load_device_profile

    profile = load_device_profile(_PROFILE)
    del profile["fields"]["g0_s"]
    with pytest.raises(ValueError, match="missing required physical field"):
        tile_config_from_profile(profile, **_BITS)


def test_profile_adapter_requires_explicit_bits() -> None:
    with pytest.raises(TypeError):
        tile_config_from_profile(_PROFILE)


def test_functional_only_profile_cannot_drive_physical_tile() -> None:
    with pytest.raises(ValueError, match="assumed profiles|FUNCTIONAL_ONLY|per-field evidence"):
        tile_config_from_profile(_FUNCTIONAL, **_BITS)


def test_required_field_contract_is_exposed() -> None:
    assert "g0_s" in REQUIRED_FIELDS
    assert "gscale_s_per_w" in REQUIRED_FIELDS
    assert "output_headroom_up_v" in REQUIRED_FIELDS
    assert "output_headroom_down_v" in REQUIRED_FIELDS