"""Tests for Chapter 0022 — Partial Sums & Multi-Tile Spatial Partitioning."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parent.parent
_MODULE = _REPO / "book" / "0022-partial-sums" / "partial_sums.py"
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "partial-sums-0022-extract.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("partial_sums_0022", _MODULE)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["partial_sums_0022"] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()


def test_module_loaded() -> None:
    assert mod is not None, "Failed to load book/0022-partial-sums/partial_sums.py"


def test_tiled_executor_exact_dimensions() -> None:
    """TiledMatrixExecutor correctly handles exact multiple dimensions (32x32 on 16x16 tiles)."""
    assert mod is not None
    executor = mod.TiledMatrixExecutor(tile_rows=16, tile_cols=16, g_bits=4)

    rng = np.random.default_rng(42)
    w = rng.uniform(-1.0, 1.0, size=(32, 32))
    x = rng.uniform(-1.0, 1.0, size=32)

    res = executor.execute_mvm(w, x)
    assert res.y_actual.shape == (32,)
    assert res.num_tiles_used == 4
    assert res.partial_sums_per_output == 2
    assert res.cosine_similarity > 0.98


def test_tiled_executor_non_multiple_dimensions() -> None:
    """TiledMatrixExecutor correctly pads non-multiple matrix dimensions (37x53 on 16x16 tiles)."""
    assert mod is not None
    executor = mod.TiledMatrixExecutor(tile_rows=16, tile_cols=16, g_bits=4)

    rng = np.random.default_rng(42)
    w = rng.uniform(-1.0, 1.0, size=(37, 53))
    x = rng.uniform(-1.0, 1.0, size=53)

    res = executor.execute_mvm(w, x)
    assert res.y_actual.shape == (37,)
    assert res.num_tiles_used == 3 * 4  # ceil(37/16)=3, ceil(53/16)=4 -> 12 tiles
    assert res.cosine_similarity > 0.98


def test_tiled_zero_matrix_output() -> None:
    """Tiled executor on zero matrix must produce exact zeros across all partial sums."""
    assert mod is not None
    executor = mod.TiledMatrixExecutor(tile_rows=16, tile_cols=16, g_bits=4)

    w_zero = np.zeros((64, 64))
    rng = np.random.default_rng(42)
    x = rng.uniform(-1.0, 1.0, size=64)

    res = executor.execute_mvm(w_zero, x)
    assert np.all(res.y_actual == 0.0)
    assert res.rel_error_pct == pytest.approx(0.0)


def test_accumulator_bit_width_bounds() -> None:
    """Validate accumulator precision bit-width rules."""
    assert mod is not None
    # 4-bit ADC + ceil(log2(Kc))
    def calc_bits(b_adc: int, kc: int) -> int:
        return b_adc + int(np.ceil(np.log2(max(kc, 1))))

    assert calc_bits(4, 1) == 4
    assert calc_bits(4, 2) == 5
    assert calc_bits(4, 4) == 6
    assert calc_bits(4, 16) == 8
    assert calc_bits(4, 64) == 10


def test_committed_extract_integrity() -> None:
    """Validate structure and metrics of committed extract JSON."""
    assert _EXTRACT.exists(), f"Missing extract artifact at {_EXTRACT}"
    with open(_EXTRACT, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["schema_version"] == "0.1.0"
    assert data["chapter"] == "0022-partial-sums"
    assert len(data["partial_sum_scaling_kc"]) == 6
    assert data["summary"]["tiled_64_16x16_error_pct"] < data["summary"]["monolithic_64_ir_error_pct"]


def test_diagram_svgs_exist() -> None:
    """Verify presence of Chapter 0022 SVG diagrams."""
    diag_dir = _REPO / "book" / "0022-partial-sums" / "diagrams"
    assert (diag_dir / "partial_sums_architecture.svg").is_file(), "Missing partial_sums_architecture.svg"
    assert (diag_dir / "partial_sums_scaling.svg").is_file(), "Missing partial_sums_scaling.svg"
