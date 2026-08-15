"""Tests for Chapter 0025 NoC / Interconnect Traffic Model."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_MODULE = _REPO / "book" / "0025-noc-interconnect" / "noc_interconnect.py"
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "noc-interconnect-0025-extract.json"
_DIAGRAM = _REPO / "book" / "0025-noc-interconnect" / "diagrams" / "noc-interconnect-0025.svg"


def _load_module():
    spec = importlib.util.spec_from_file_location("noc_interconnect_0025", _MODULE)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["noc_interconnect_0025"] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()
NoCTopology = mod.NoCTopology
MatrixTilingConfig = mod.MatrixTilingConfig
ReductionNetworkMetrics = mod.ReductionNetworkMetrics
compute_reduction_network_metrics = mod.compute_reduction_network_metrics
generate_noc_interconnect_extract = mod.generate_noc_interconnect_extract


def test_single_tile_matrix_has_zero_reduction_traffic() -> None:
    """Hand-check: 16x16 matrix on 16x16 tile has Kr=1, Kc=1: zero reduction transfers."""
    cfg = MatrixTilingConfig(m_out=16, m_in=16, tile_rows=16, tile_cols=16)
    assert cfg.kr == 1
    assert cfg.kc == 1
    assert cfg.total_tiles == 1
    metrics = compute_reduction_network_metrics(cfg, NoCTopology.BINARY_TREE)
    assert metrics.reduction_traffic_bytes == 0.0
    assert metrics.activation_broadcast_bytes == 16 * 4 / 8.0  # 8 bytes
    assert metrics.critical_path_latency_ns == 0.0


def test_tiny_hand_computable_reduction_tree() -> None:
    """Hand-check: 32x32 matrix on 16x16 tiles (4-bit ADC, 4-bit DAC):
    - Kr = 2, Kc = 2 -> 4 tiles
    - B_acc = 4 + ceil(log2(2)) = 5 bits
    - Bytes per psum vector = 16 * 5 / 8 = 10 bytes
    - Reduction transfers = Kr * (Kc - 1) = 2 * 1 = 2 transfers
    - Total reduction traffic = 2 * 10 = 20 bytes
    - Activation broadcast = 2 * (16 * 4 / 8) = 16 bytes
    - Total traffic = 36 bytes
    - Binary tree latency: ceil(log2(2)) * 1.0 = 1.0 ns
    """
    cfg = MatrixTilingConfig(m_out=32, m_in=32, tile_rows=16, tile_cols=16, dac_bits=4, adc_bits=4)
    assert cfg.kr == 2
    assert cfg.kc == 2
    assert cfg.b_acc == 5
    metrics = compute_reduction_network_metrics(cfg, NoCTopology.BINARY_TREE)
    assert metrics.reduction_traffic_bytes == 20.0
    assert metrics.activation_broadcast_bytes == 16.0
    assert metrics.total_traffic_bytes == 36.0
    assert metrics.critical_path_latency_ns == 1.0


def test_topology_comparison_properties() -> None:
    """For 64x64 on 16x16 tiles (Kr=4, Kc=4):
    Binary tree should have strictly lower latency and energy than 2D mesh and ring.
    """
    cfg = MatrixTilingConfig(m_out=64, m_in=64, tile_rows=16, tile_cols=16)
    tree = compute_reduction_network_metrics(cfg, NoCTopology.BINARY_TREE)
    mesh = compute_reduction_network_metrics(cfg, NoCTopology.MESH_2D)
    ring = compute_reduction_network_metrics(cfg, NoCTopology.RING_BUS)

    assert tree.critical_path_latency_ns < mesh.critical_path_latency_ns
    assert tree.critical_path_latency_ns < ring.critical_path_latency_ns
    assert tree.estimated_noc_energy_nj < mesh.estimated_noc_energy_nj
    assert mesh.estimated_noc_energy_nj < ring.estimated_noc_energy_nj


def test_invalid_matrix_tiling_fails_closed() -> None:
    with pytest.raises(ValueError, match="positive"):
        MatrixTilingConfig(m_out=0, m_in=64)
    with pytest.raises(ValueError, match="positive"):
        MatrixTilingConfig(m_out=64, m_in=-1)
    with pytest.raises(ValueError, match="positive"):
        MatrixTilingConfig(m_out=64, m_in=64, tile_rows=0)


def test_noc_interconnect_extract_is_reproducible() -> None:
    extract = generate_noc_interconnect_extract()
    assert _EXTRACT.is_file()
    committed = json.loads(_EXTRACT.read_text("utf-8"))
    assert extract == committed
    assert _DIAGRAM.is_file()
