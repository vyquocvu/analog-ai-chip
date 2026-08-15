import importlib.util
import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_MODULE = _REPO / "book" / "0024-sram-buffers" / "sram_buffers.py"
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "sram-buffers-0024-extract.json"
_DIAGRAM = _REPO / "book" / "0024-sram-buffers" / "diagrams" / "sram-buffers-0024.svg"


def _load_module():
    spec = importlib.util.spec_from_file_location("sram_buffers_0024", _MODULE)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["sram_buffers_0024"] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()
TileBufferConfig = mod.TileBufferConfig
TileBufferCapacity = mod.TileBufferCapacity
compute_tile_buffer_capacity = mod.compute_tile_buffer_capacity
compute_kv_cache_capacity = mod.compute_kv_cache_capacity
compute_buffer_traffic = mod.compute_buffer_traffic
generate_sram_buffers_extract = mod.generate_sram_buffers_extract


def test_tiny_hand_computable_tile_buffer_capacity() -> None:
    """Hand-check: for 2x2 4-bit tile with Kc=4 (B_acc=4+2=6 bits), double buffered:
    - Act buffer: 2 * 2 * 4 = 16 bits (2 bytes)
    - Acc buffer: 2 * 6 = 12 bits
    - Weight staging: 2 * (2*2) * 4 = 32 bits (4 bytes)
    - Total: 16 + 12 + 32 = 60 bits (7.5 bytes)
    """
    cfg = TileBufferConfig(
        tile_rows=2,
        tile_cols=2,
        dac_bits=4,
        adc_bits=4,
        weight_bits=4,
        kc_max=4,
        double_buffer_inputs=True,
    )
    cap = compute_tile_buffer_capacity(cfg)
    assert cap.activation_buffer_bits == 16
    assert cap.accumulator_word_bits == 6
    assert cap.accumulator_buffer_bits == 12
    assert cap.weight_staging_buffer_bits == 32
    assert cap.total_tile_sram_bits == 60
    assert cap.total_tile_sram_bytes == 7.5


def test_standard_16x16_4bit_tile_buffer_capacity() -> None:
    """16x16 4-bit tile with Kc_max=16 (B_acc=4+4=8 bits):
    - Act buffer: 2 * 16 * 4 = 128 bits (16 bytes)
    - Acc buffer: 16 * 8 = 128 bits (16 bytes)
    - Weight staging: 2 * 256 * 4 = 2048 bits (256 bytes)
    - Total: 2304 bits (288 bytes)
    """
    cfg = TileBufferConfig(
        tile_rows=16,
        tile_cols=16,
        dac_bits=4,
        adc_bits=4,
        weight_bits=4,
        kc_max=16,
        double_buffer_inputs=True,
    )
    cap = compute_tile_buffer_capacity(cfg)
    assert isinstance(cap, TileBufferCapacity)
    assert cap.activation_buffer_bits == 128
    assert cap.accumulator_word_bits == 8
    assert cap.accumulator_buffer_bits == 128
    assert cap.weight_staging_buffer_bits == 2048
    assert cap.total_tile_sram_bits == 2304
    assert cap.total_tile_sram_bytes == 288.0


def test_single_buffered_inputs_reduces_activation_storage() -> None:
    cfg = TileBufferConfig(
        tile_rows=16,
        tile_cols=16,
        dac_bits=4,
        adc_bits=4,
        weight_bits=4,
        kc_max=16,
        double_buffer_inputs=False,
    )
    cap = compute_tile_buffer_capacity(cfg)
    assert cap.activation_buffer_bits == 64
    assert cap.total_tile_sram_bits == 64 + 128 + 2048


def test_invalid_tile_buffer_config_fails_closed() -> None:
    with pytest.raises(ValueError, match="tile rows/cols must be positive"):
        TileBufferConfig(tile_rows=0)
    with pytest.raises(ValueError, match="converter and weight bits must be positive"):
        TileBufferConfig(dac_bits=-1)
    with pytest.raises(ValueError, match="kc_max must be positive"):
        TileBufferConfig(kc_max=0)


def test_kv_cache_capacity_calculation() -> None:
    """TinyGPT: 4 layers, d_model=64, seq_len=128, 16-bit act:
    2 * 128 * 4 * 64 * 16 = 1,048,576 bits = 131,072 bytes = 128 KB
    """
    kv = compute_kv_cache_capacity(seq_len=128, num_layers=4, d_model=64, act_bits=16)
    assert kv.total_kv_bits == 1_048_576
    assert kv.total_kv_bytes == 131_072.0
    assert kv.total_kv_kbytes == 128.0

    with pytest.raises(ValueError, match="positive"):
        compute_kv_cache_capacity(seq_len=0, num_layers=4, d_model=64)


def test_traffic_ledger_distinguishes_weight_stationary_and_temporal() -> None:
    cfg = TileBufferConfig(tile_rows=16, tile_cols=16, dac_bits=4, adc_bits=4, weight_bits=4)

    # 10 MVMs, zero rewrites (stationary)
    stat = compute_buffer_traffic(cfg, num_mvm_operations=10, num_tile_rewrites=0)
    assert stat.input_activation_bytes == 10 * (16 * 4 / 8)  # 80 bytes
    assert stat.output_activation_bytes == 10 * (16 * 4 / 8)  # 80 bytes
    assert stat.weight_load_bytes == 0.0
    assert stat.total_sram_traffic_bytes == 160.0

    # 10 MVMs, 5 rewrites (temporal)
    temp = compute_buffer_traffic(cfg, num_mvm_operations=10, num_tile_rewrites=5)
    assert temp.weight_load_bytes == 5 * (2 * 16 * 16 * 4 / 8)  # 5 * 256 = 1280 bytes
    assert temp.total_sram_traffic_bytes == 160.0 + 1280.0
    assert temp.estimated_sram_energy_nj == (1440.0 * 1.0) / 1000.0


def test_sram_buffers_extract_is_reproducible() -> None:
    extract = generate_sram_buffers_extract()
    assert _EXTRACT.is_file()
    committed = json.loads(_EXTRACT.read_text("utf-8"))
    assert extract == committed
    assert _DIAGRAM.is_file()
