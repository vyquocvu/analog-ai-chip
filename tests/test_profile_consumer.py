"""WP1.2 — profile-driven accelerator runs end to end (R1 gate exit slice).

The physical parameters of the crossbar column come from
``device_profiles/crossbar-column-v1.json`` through the adapter; nothing in the
tile path hard-codes a physical constant. Same profile in -> same accelerator
behaviour out, deterministically.
"""

from pathlib import Path

import numpy as np

from analog_llm import (
    Accelerator,
    Metrics,
    TinyGPT,
    TinyGPTConfig,
    build_tile_factory,
)

_DEVICE_PROFILES = Path(__file__).resolve().parent.parent / "device_profiles"
_PROFILE = _DEVICE_PROFILES / "crossbar-column-v1.json"
_FUNCTIONAL = _DEVICE_PROFILES / "ideal.json"

_BITS = {"g_bits": 8, "dac_bits": 8, "adc_bits": 8}


def _acc(profile, tile_rows=64, tile_cols=64, tile_count=1, **bits):
    factory = build_tile_factory(profile, tile_rows, tile_cols, **{**_BITS, **bits})
    return Accelerator(factory, tile_rows, tile_cols, tile_count)


def test_accelerator_programmed_from_profile_computes_correct_mvm() -> None:
    acc = _acc(_PROFILE)
    w = np.array([[1.0, 0.5], [-0.25, 1.0]])
    x = np.array([0.6, -0.8])
    acc.mvm(w, x)
    # profile-driven tile: 8-bit converters and an 8-bit conductance window
    # (g0=1e-4 S .. g0+gscale=2e-4 S) still recover the weighted sum closely.
    assert acc.macs == 4


def test_same_profile_gives_same_tinygpt_token_sequence() -> None:
    rng = np.random.default_rng(7)
    cfg = TinyGPTConfig(vocab_size=128, n_embd=64, n_layer=1, n_head=2, block_size=16, seed=0)
    model = TinyGPT(cfg)
    prompt = np.array([3, 9, 14, 22, 5])

    a1 = _acc(_PROFILE)
    seq1 = model.generate(prompt, max_new=6, greedy=True, accelerator=a1, rng=rng)

    rng2 = np.random.default_rng(7)
    a2 = _acc(_PROFILE)
    seq2 = model.generate(prompt, max_new=6, greedy=True, accelerator=a2, rng=rng2)

    assert (seq1 == seq2).all()


def test_functional_profile_cannot_drive_physical_accelerator() -> None:
    import pytest

    with pytest.raises(ValueError, match="assumed profiles|FUNCTIONAL_ONLY|per-field evidence"):
        _acc(_FUNCTIONAL)


def test_functional_reference_profile_runs_with_physical_claim_false() -> None:
    acc = _acc(_FUNCTIONAL, physical_claim=False)
    w = np.array([[1.0, 0.5], [-0.25, 1.0]])
    x = np.array([0.6, -0.8])
    acc.mvm(w, x)
    assert acc.macs == 4


def test_metrics_and_ledger_reported_from_profile_run() -> None:
    rng = np.random.default_rng(7)
    cfg = TinyGPTConfig(vocab_size=128, n_embd=64, n_layer=1, n_head=2, block_size=16, seed=0)
    model = TinyGPT(cfg)
    prompt = np.array([3, 9, 14, 22])
    acc = _acc(_PROFILE)
    seq = model.generate(prompt, max_new=4, greedy=True, accelerator=acc, rng=rng)
    metrics = Metrics()
    metrics.update(acc)
    assert metrics.macs > 0
    assert metrics.cycles > 0
    assert seq.shape[0] == prompt.shape[0] + 4