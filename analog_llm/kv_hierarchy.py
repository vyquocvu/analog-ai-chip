"""KV-cache hierarchy, paged allocation, and digital attention bottleneck analysis.

Models GQA/MQA KV-cache memory scaling, SRAM vs HBM tier placement, and calculates
the Attention Wall crossover point where digital attention bandwidth and computation
surpass analog projection latency.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .model_manifest import ModelManifest


class KVCachePlacement(str, Enum):
    """Memory tier where KV cache pages reside."""

    ON_CHIP_SRAM = "on_chip_sram"
    PACKAGE_HBM = "package_hbm"
    HOST_DRAM = "host_dram"


@dataclass(frozen=True)
class KVHierarchyConfig:
    """Hardware hierarchy and digital attention accelerator constraints."""

    paged_block_size: int = 16  # Tokens per paged allocation block
    kv_dtype_bytes: int = 2  # 2 bytes for FP16 / BF16 KV cache
    sram_kv_capacity_mb: float = 64.0  # On-chip SRAM dedicated to KV cache
    package_hbm_capacity_gb: float = 32.0  # Package HBM3e capacity
    sram_bandwidth_tb_s: float = 8.0  # Ultra-wide on-chip SRAM bandwidth
    hbm_bandwidth_tb_s: float = 1.2  # HBM3e stack bandwidth
    digital_attention_tflops: float = 64.0  # FP16 vector/systolic attention unit
    analog_projection_latency_us_per_token: float = 2.5  # Stationary MVM latency per token


@dataclass(frozen=True)
class AttentionWorkloadStep:
    """Attention memory and computation metrics at a specific context length."""

    context_length: int
    kv_cache_bytes: int
    gqa_reduction_factor: float
    paged_blocks_count: int
    placement: KVCachePlacement
    prefill_attention_macs: int
    decode_attention_macs_per_token: int
    decode_kv_read_bytes_per_token: int
    analog_projection_latency_us: float
    digital_attention_latency_us: float
    is_digital_attention_bottleneck: bool


@dataclass(frozen=True)
class KVHierarchySummary:
    """Complete KV cache scaling and bottleneck crossover analysis."""

    model_name: str
    attention_type: str
    num_layers: int
    num_attention_heads: int
    num_key_value_heads: int
    head_dimension: int
    gqa_compression_ratio: float
    crossover_context_length: int | None  # Context where digital attention exceeds analog MVM
    steps: dict[int, AttentionWorkloadStep]
    metadata: dict[str, Any]


def calculate_kv_cache_bytes(
    manifest: ModelManifest,
    context_length: int,
    dtype_bytes: int = 2,
) -> int:
    """Exact KV-cache byte footprint across all layers for a given context length."""
    # 2 tensors (K and V) per layer
    return int(
        2
        * manifest.num_layers
        * manifest.num_key_value_heads
        * manifest.head_dimension
        * context_length
        * dtype_bytes
    )


def analyze_kv_hierarchy(
    manifest: ModelManifest,
    config: KVHierarchyConfig | None = None,
    context_sweep: Sequence[int] = (128, 512, 1024, 2048, 4096, 8192),
    model_name: str = "custom",
) -> KVHierarchySummary:
    """Evaluate KV cache scaling, placement, and digital attention crossover wall."""
    cfg = config or KVHierarchyConfig()
    gqa_ratio = manifest.num_attention_heads / max(1, manifest.num_key_value_heads)

    steps: dict[int, AttentionWorkloadStep] = {}
    crossover_len: int | None = None

    for ctx in context_sweep:
        kv_bytes = calculate_kv_cache_bytes(manifest, ctx, cfg.kv_dtype_bytes)
        paged_blocks = math.ceil(ctx / cfg.paged_block_size)

        # Placement logic
        sram_limit_bytes = int(cfg.sram_kv_capacity_mb * 1024 * 1024)
        hbm_limit_bytes = int(cfg.package_hbm_capacity_gb * 1024 * 1024 * 1024)

        if kv_bytes <= sram_limit_bytes:
            placement = KVCachePlacement.ON_CHIP_SRAM
            active_bw = cfg.sram_bandwidth_tb_s * 1e12
        elif kv_bytes <= hbm_limit_bytes:
            placement = KVCachePlacement.PACKAGE_HBM
            active_bw = cfg.hbm_bandwidth_tb_s * 1e12
        else:
            placement = KVCachePlacement.HOST_DRAM
            active_bw = 64.0 * 1e9  # PCIe Gen5

        # Digital Attention MACs:
        # Prefill: QK^T + AttnV = 2 * ctx^2 * hidden_size * layers
        # Decode: QK^T + AttnV at step ctx = 2 * ctx * hidden_size * layers
        hidden = manifest.hidden_size
        layers = manifest.num_layers
        prefill_macs = 2 * (ctx**2) * hidden * layers
        decode_macs = 2 * ctx * hidden * layers

        # Decode digital attention latency:
        # 1. Compute time: (decode_macs * 2 FLOPs) / digital_flops
        compute_time_s = (decode_macs * 2) / (cfg.digital_attention_tflops * 1e12)
        # 2. Memory read time: kv_bytes / active_bw
        memory_time_s = kv_bytes / max(1.0, active_bw)
        # Digital attention latency is dominated by memory traffic + compute
        digital_lat_us = (compute_time_s + memory_time_s) * 1e6
        analog_lat_us = cfg.analog_projection_latency_us_per_token

        is_bottleneck = digital_lat_us > analog_lat_us
        if is_bottleneck and crossover_len is None:
            crossover_len = ctx

        steps[ctx] = AttentionWorkloadStep(
            context_length=ctx,
            kv_cache_bytes=kv_bytes,
            gqa_reduction_factor=gqa_ratio,
            paged_blocks_count=paged_blocks,
            placement=placement,
            prefill_attention_macs=prefill_macs,
            decode_attention_macs_per_token=decode_macs,
            decode_kv_read_bytes_per_token=kv_bytes,
            analog_projection_latency_us=analog_lat_us,
            digital_attention_latency_us=digital_lat_us,
            is_digital_attention_bottleneck=is_bottleneck,
        )

    return KVHierarchySummary(
        model_name=model_name,
        attention_type=manifest.attention_type,
        num_layers=manifest.num_layers,
        num_attention_heads=manifest.num_attention_heads,
        num_key_value_heads=manifest.num_key_value_heads,
        head_dimension=manifest.head_dimension,
        gqa_compression_ratio=gqa_ratio,
        crossover_context_length=crossover_len,
        steps=steps,
        metadata={
            "sram_kv_capacity_mb": cfg.sram_kv_capacity_mb,
            "hbm_capacity_gb": cfg.package_hbm_capacity_gb,
            "digital_tflops": cfg.digital_attention_tflops,
        },
    )
