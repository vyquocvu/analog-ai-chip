"""WP2.1 — R2 gate exit: analog_llm runs on validated converter profiles.

The gate exit requires that ``analog_llm`` can run with converter parameters
sourced from the validated DAC/ADC profiles rather than arbitrary normalized
defaults. These always-on tests prove the end-to-end path:

    crossbar-column-v1 + dac-r2r-v1 + adc-sar-v1 profiles
        -> adapter -> CrossbarTile -> Accelerator -> TinyGPT

``build_tile_factory_from_converter_profiles`` takes the conductance window
from the crossbar-column profile and the converter bits/voltage envelopes from
the two SPICE-verified converter profiles; ``converter_config_from_profiles``
is the field-level mapping and fails closed when a required field is missing.
"""

from pathlib import Path

import numpy as np
import pytest

from analog_llm import (
    Accelerator,
    CrossbarTile,
    Metrics,
    TinyGPT,
    TinyGPTConfig,
    build_tile_factory_from_converter_profiles,
    converter_config_from_profiles,
)
from analog_llm.profile_adapter import REQUIRED_ADC_FIELDS, REQUIRED_DAC_FIELDS

_DEVICE_PROFILES = Path(__file__).resolve().parent.parent / "device_profiles"
_COLUMN = _DEVICE_PROFILES / "crossbar-column-v1.json"
_DAC = _DEVICE_PROFILES / "dac-r2r-v1.json"
_ADC = _DEVICE_PROFILES / "adc-sar-v1.json"


def _acc(tile_rows=16, tile_cols=16, tile_count=1, **g_bits):
    factory = build_tile_factory_from_converter_profiles(
        _COLUMN, _DAC, _ADC, tile_rows, tile_cols,
        g_bits=g_bits.get("g_bits", 6),
    )
    return Accelerator(factory, tile_rows, tile_cols, tile_count)


def test_converter_config_comes_from_profiles() -> None:
    cfg = converter_config_from_profiles(_DAC, _ADC)
    # dac-r2r-v1: 4 bits, full-scale 2.34375 V
    assert cfg["dac_bits"] == 4
    assert cfg["vin_max"] == pytest.approx(2.34375, rel=1e-12)
    # adc-sar-v1: 4 bits, input envelope +/-VREF
    assert cfg["adc_bits"] == 4
    assert cfg["vout_max"] == pytest.approx(2.5, rel=1e-12)
    # no normalized 1.0 defaults anywhere on the converter path
    assert cfg["vin_max"] != 1.0
    assert cfg["vout_max"] != 1.0


def test_converter_config_fails_closed_on_missing_fields() -> None:
    import json

    profile = json.loads(_DAC.read_text("utf-8"))
    profile["fields"].pop("full_scale_v")
    with pytest.raises(ValueError, match="missing required field"):
        converter_config_from_profiles(profile, _ADC)
    assert REQUIRED_DAC_FIELDS and REQUIRED_ADC_FIELDS  # contract is explicit


def test_converter_config_fails_closed_on_functional_only() -> None:
    with pytest.raises(ValueError, match="assumed profiles|cannot support"):
        converter_config_from_profiles(_DEVICE_PROFILES / "ideal.json", _ADC)


def test_accelerator_runs_with_profile_sourced_converters() -> None:
    acc = _acc()
    w = np.array([[1.0, 0.5], [-0.25, 1.0]])
    x = np.array([0.6, -0.8])
    acc.mvm(w, x)
    assert acc.macs == 4
    assert acc.programs == 1


def test_profile_sourced_tinygpt_generation_is_deterministic() -> None:
    rng = np.random.default_rng(7)
    cfg = TinyGPTConfig(vocab_size=128, n_embd=32, n_layer=1, n_head=2, block_size=16, seed=0)
    model = TinyGPT(cfg)
    prompt = np.array([3, 9, 14, 22])

    a1 = _acc(tile_rows=32, tile_cols=32)
    seq1 = model.generate(prompt, max_new=4, greedy=True, accelerator=a1, rng=rng)

    rng2 = np.random.default_rng(7)
    a2 = _acc(tile_rows=32, tile_cols=32)
    seq2 = model.generate(prompt, max_new=4, greedy=True, accelerator=a2, rng=rng2)

    assert (seq1 == seq2).all()


def test_tile_ledger_reported_from_profile_run() -> None:
    acc = _acc()
    w = np.array([[1.0, 0.5], [-0.25, 1.0]])
    x = np.array([0.6, -0.8])
    acc.mvm(w, x)
    metrics = Metrics()
    metrics.update(acc)
    assert metrics.macs > 0
    assert metrics.cycles > 0


def test_factory_builds_crossbar_tiles_with_converter_envelopes() -> None:
    factory = build_tile_factory_from_converter_profiles(
        _COLUMN, _DAC, _ADC, 8, 8, g_bits=6
    )
    tile: CrossbarTile = factory()
    assert tile.dac_bits == 4
    assert tile.adc_bits == 4
    assert tile.vin_max == pytest.approx(2.34375, rel=1e-12)
    assert tile.vout_max == pytest.approx(2.5, rel=1e-12)
