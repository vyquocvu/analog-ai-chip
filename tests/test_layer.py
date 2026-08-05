import numpy as np

from analog_llm import Accelerator, CrossbarTile

TILE = 64
M = 16
NS = [10, 100, 1000]


def _make_tile():
    return CrossbarTile(TILE, TILE, g_bits=14, dac_bits=16, adc_bits=16, vout_max=32.0)


def _summary(n):
    rng = np.random.default_rng(0)
    w = rng.normal(0.0, 1.0 / np.sqrt(M), (n, M))
    x = rng.normal(0.0, 1.0, M)
    ref = w @ x
    acc = Accelerator(_make_tile, TILE, TILE, 64)
    y = acc.mvm(w, x)
    return {
        "cells": n * M,
        "signed": 2 * n * M,
        "macs": acc.macs,
        "tiles": (-(-n // TILE)) * (-(-M // TILE)),
        "err": float(np.max(np.abs(y - ref))),
    }


def test_layer_scaling_numbers() -> None:
    for n in NS:
        s = _summary(n)
        assert s["cells"] == n * M
        assert s["signed"] == 2 * n * M
        assert s["macs"] == n * M, f"N={n} macs {s['macs']}"
        assert s["tiles"] == (-(-n // TILE)), f"N={n} tiles {s['tiles']}"


def test_layer_matches_float_reference() -> None:
    for n in NS:
        assert _summary(n)["err"] < 1e-1, f"N={n} tiled layer err too large"


def test_scaling_is_linear_in_n() -> None:
    cells = [_summary(n)["cells"] for n in NS]
    assert np.allclose(cells, [n * M for n in NS])
