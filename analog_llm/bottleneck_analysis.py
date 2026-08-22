"""Bottleneck identification, multi-parameter Pareto sweeps, and digital break-even analysis.

Identifies the primary limiting physical resource across model tiers, sweeps
architectural design parameters (tile geometry, converter sharing, precision),
and generates deterministic Pareto frontiers with honest digital baseline comparisons.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .model_manifest import ModelManifest
from .physical_ledger import PhysicalLedgerConfig, compute_tier_physical_ledger
from .residency import HardwareTopologyConfig


class LimitingResource(str, Enum):
    """Primary physical bottleneck constraining accelerator performance."""

    ADC_AREA_BANDWIDTH_LIMIT = "adc_area_bandwidth_limit"
    INTER_DIE_UCIE_LIMIT = "inter_die_ucie_limit"
    SRAM_HBM_BANDWIDTH_LIMIT = "sram_hbm_bandwidth_limit"
    DIGITAL_ATTENTION_COMPUTE_LIMIT = "digital_attention_compute_limit"
    CROSSBAR_CAPACITY_LIMIT = "crossbar_capacity_limit"
    THERMAL_POWER_LIMIT = "thermal_power_limit"


@dataclass(frozen=True)
class ParetoPoint:
    """Design point in the architectural Pareto sweep."""

    tile_rows: int
    tile_cols: int
    adc_sharing_factor: int
    precision_bits: int
    total_silicon_area_mm2: float
    decode_energy_per_token_uj: float
    decode_tokens_per_second: float
    energy_delay_product_pj_s: float
    is_pareto_optimal: bool
    limiting_resource: LimitingResource
    digital_28nm_speedup: float
    digital_28nm_energy_reduction_factor: float


@dataclass(frozen=True)
class TierBottleneckReport:
    """Comprehensive bottleneck identification and Pareto frontier report."""

    model_name: str
    primary_limiting_resource: LimitingResource
    resource_utilization_pct: dict[str, float]
    pareto_points: list[ParetoPoint]
    optimal_point: ParetoPoint
    claim_level: str
    metadata: dict[str, Any]


def identify_primary_bottleneck(
    manifest: ModelManifest,
    context_length: int = 512,
    topology: HardwareTopologyConfig | None = None,
) -> tuple[LimitingResource, dict[str, float]]:
    """Determine the first limiting resource and percentage breakdown for a given model tier."""
    topo = topology or HardwareTopologyConfig()
    cfg = PhysicalLedgerConfig()
    metrics = compute_tier_physical_ledger(
        manifest,
        batch_size=1,
        context_length=context_length,
        config=cfg,
        topology=topo,
    )

    b = metrics.decode_breakdown
    total_e = max(1e-9, b.total_energy_uj)

    # Share of energy / delay
    adc_share = (b.adc_dac_conversion_uj / total_e) * 100.0
    mvm_share = (b.analog_mvm_uj / total_e) * 100.0
    attn_share = (b.digital_attention_uj / total_e) * 100.0
    mem_share = ((b.sram_and_noc_uj + b.package_hbm_uj) / total_e) * 100.0
    ucie_share = (b.inter_die_ucie_uj / total_e) * 100.0

    utilization = {
        "adc_dac_conversion_pct": adc_share,
        "analog_mvm_pct": mvm_share,
        "digital_attention_pct": attn_share,
        "memory_transfer_pct": mem_share,
        "inter_die_link_pct": ucie_share,
    }

    # Classification logic based on physical bottleneck dominance
    if metrics.die_count > topo.max_chiplets_per_package:
        bottleneck = LimitingResource.CROSSBAR_CAPACITY_LIMIT
    elif context_length >= 2048 or (attn_share > 50.0 and attn_share > adc_share):
        bottleneck = LimitingResource.DIGITAL_ATTENTION_COMPUTE_LIMIT
    elif metrics.die_count > 1 and ucie_share > 20.0:
        bottleneck = LimitingResource.INTER_DIE_UCIE_LIMIT
    elif b.package_hbm_uj > 0 and mem_share > 30.0:
        bottleneck = LimitingResource.SRAM_HBM_BANDWIDTH_LIMIT
    else:
        bottleneck = LimitingResource.ADC_AREA_BANDWIDTH_LIMIT

    return bottleneck, utilization


def evaluate_bottleneck_and_pareto(
    manifest: ModelManifest,
    context_length: int = 512,
    model_name: str = "custom",
    claim_level: str = "system/architecture-exploration",
) -> TierBottleneckReport:
    """Execute architectural Pareto sweep across tile geometries, ADC sharing, and bit depths."""
    primary_bn, util_map = identify_primary_bottleneck(manifest, context_length=context_length)

    # Digital 28nm ASIC baseline reference:
    # 28nm digital standard-cell FP16/INT8 MAC = ~15.0 pJ/MAC, single core throughput ~10k TPS
    digital_mac_pj = 15.0
    digital_energy_uj_per_token = (manifest.hidden_size * manifest.num_layers * 6 * manifest.hidden_size * digital_mac_pj) * 1e-6
    digital_tps = 8500.0

    # Sweep parameters:
    # Tile geometries: (16x16), (32x32), (64x64)
    # ADC column sharing: 1 (dedicated), 4 (1 ADC per 4 cols), 8 (1 ADC per 8 cols)
    # Precision bits: 4, 6, 8
    sweep_configs = [
        (16, 16, 1, 8),
        (16, 16, 4, 8),
        (16, 16, 8, 8),
        (32, 32, 1, 8),
        (32, 32, 4, 8),
        (32, 32, 4, 6),
        (32, 32, 8, 4),
        (64, 64, 4, 8),
        (64, 64, 8, 6),
    ]

    points: list[ParetoPoint] = []
    cfg = PhysicalLedgerConfig()

    for r_dim, c_dim, sharing, bits in sweep_configs:
        # Scale peripheral area and energy based on sharing and tile size
        # Sharing reduces peripheral area per tile by sharing SAR ADCs across columns
        periph_area = (1000.0 / sharing) * (c_dim / 16.0)
        topo_sw = HardwareTopologyConfig(
            tile_rows=r_dim,
            tile_cols=c_dim,
            peripheral_area_um2_per_tile=periph_area,
        )
        # Scaled ADC energy for bit precision
        adc_scale = (bits / 8.0) * (1.0 + 0.1 * (sharing - 1))
        cfg_sw = PhysicalLedgerConfig(
            energy_per_adc_conv_pj=cfg.energy_per_adc_conv_pj * adc_scale,
            analog_tile_cycle_ns=cfg.analog_tile_cycle_ns * (sharing ** 0.5),
        )

        metrics = compute_tier_physical_ledger(
            manifest,
            batch_size=1,
            context_length=context_length,
            config=cfg_sw,
            topology=topo_sw,
        )

        energy_pj = metrics.decode_energy_per_token_uj * 1e6
        delay_s = 1.0 / max(1.0, metrics.decode_tokens_per_second)
        edp = energy_pj * delay_s  # Energy-Delay Product

        speedup = metrics.decode_tokens_per_second / max(1.0, digital_tps)
        energy_red = digital_energy_uj_per_token / max(1e-9, metrics.decode_energy_per_token_uj)

        points.append(
            ParetoPoint(
                tile_rows=r_dim,
                tile_cols=c_dim,
                adc_sharing_factor=sharing,
                precision_bits=bits,
                total_silicon_area_mm2=metrics.total_silicon_area_mm2,
                decode_energy_per_token_uj=metrics.decode_energy_per_token_uj,
                decode_tokens_per_second=metrics.decode_tokens_per_second,
                energy_delay_product_pj_s=edp,
                is_pareto_optimal=False,  # Evaluated below
                limiting_resource=primary_bn,
                digital_28nm_speedup=speedup,
                digital_28nm_energy_reduction_factor=energy_red,
            )
        )

    # Determine Pareto-optimal points: A point is Pareto optimal if no other point has both lower energy AND higher TPS
    pareto_evaluated: list[ParetoPoint] = []
    for p in points:
        dominated = False
        for other in points:
            if (other.decode_energy_per_token_uj <= p.decode_energy_per_token_uj and
                other.decode_tokens_per_second >= p.decode_tokens_per_second and
                (other.decode_energy_per_token_uj < p.decode_energy_per_token_uj or
                 other.decode_tokens_per_second > p.decode_tokens_per_second)):
                dominated = True
                break
        pareto_evaluated.append(
            ParetoPoint(
                tile_rows=p.tile_rows,
                tile_cols=p.tile_cols,
                adc_sharing_factor=p.adc_sharing_factor,
                precision_bits=p.precision_bits,
                total_silicon_area_mm2=p.total_silicon_area_mm2,
                decode_energy_per_token_uj=p.decode_energy_per_token_uj,
                decode_tokens_per_second=p.decode_tokens_per_second,
                energy_delay_product_pj_s=p.energy_delay_product_pj_s,
                is_pareto_optimal=(not dominated),
                limiting_resource=p.limiting_resource,
                digital_28nm_speedup=p.digital_28nm_speedup,
                digital_28nm_energy_reduction_factor=p.digital_28nm_energy_reduction_factor,
            )
        )

    # Select point with minimal EDP
    optimal = min(pareto_evaluated, key=lambda x: x.energy_delay_product_pj_s)

    return TierBottleneckReport(
        model_name=model_name,
        primary_limiting_resource=primary_bn,
        resource_utilization_pct=util_map,
        pareto_points=pareto_evaluated,
        optimal_point=optimal,
        claim_level=claim_level,
        metadata={
            "digital_baseline_technology": "28nm standard-cell ASIC (15.0 pJ/MAC)",
            "context_length": context_length,
        },
    )
