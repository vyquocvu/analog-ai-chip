"""Parametric physical ledger for large-model analog accelerator evaluation.

Calculates end-to-end latency, energy, area, power density, and thermal envelope
for T0–T3 prefill and decode with provenance-tagged physical coefficients.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .kv_hierarchy import calculate_kv_cache_bytes
from .model_manifest import ModelManifest
from .residency import HardwareTopologyConfig, analyze_model_residency


@dataclass(frozen=True)
class PhysicalLedgerConfig:
    """Provenance-tagged physical energy and timing coefficients."""

    # 1. Analog Compute & Converters
    energy_per_mvm_mac_pj: float = 0.12  # SPICE extracted 28nm ReRAM cell array
    energy_per_adc_conv_pj: float = 0.45  # 8-bit SAR ADC (measured/SPICE correlated)
    energy_per_dac_conv_pj: float = 0.08  # 8-bit R-2R / capacitive DAC
    analog_tile_cycle_ns: float = 20.0  # 50 MHz crossbar tile execution cycle

    # 2. Data Movement & Memory
    energy_per_sram_byte_pj: float = 0.25  # Local tile SRAM buffer read/write
    energy_per_noc_byte_pj: float = 0.80  # On-chip 2D mesh NoC router hop
    energy_per_ucie_byte_pj: float = 12.0  # 2.5D interposer UCIe link (1.5 pJ/bit)
    energy_per_hbm_byte_pj: float = 28.0  # Package HBM3e stack transfer (3.5 pJ/bit)

    # 3. Digital Co-Processor
    energy_per_digital_flop_pj: float = 0.85  # FP16 vector attention MAC
    digital_attention_tflops: float = 64.0  # Digital SIMD/systolic unit throughput

    # 4. Thermal Envelopes
    max_air_cooled_power_density_w_cm2: float = 150.0
    max_liquid_cooled_power_density_w_cm2: float = 350.0


@dataclass(frozen=True)
class SubsystemEnergyBreakdown:
    """Breakdown of energy consumption across accelerator subsystems in microjoules (uJ)."""

    analog_mvm_uj: float
    adc_dac_conversion_uj: float
    sram_and_noc_uj: float
    inter_die_ucie_uj: float
    package_hbm_uj: float
    digital_attention_uj: float
    total_energy_uj: float


@dataclass(frozen=True)
class TierPhysicalMetrics:
    """Complete hardware ledger report for a model tier."""

    model_name: str
    batch_size: int
    context_length: int
    ttft_ms: float  # Time-to-first-token during prefill
    prefill_throughput_tok_s: float
    decode_tokens_per_second: float
    decode_latency_per_token_ms: float
    prefill_energy_per_token_uj: float
    decode_energy_per_token_uj: float
    decode_breakdown: SubsystemEnergyBreakdown
    active_power_w: float
    power_density_w_cm2: float
    die_count: int
    total_silicon_area_mm2: float
    thermal_classification: str
    provenance: dict[str, str]


def compute_tier_physical_ledger(
    manifest: ModelManifest,
    batch_size: int = 1,
    context_length: int = 512,
    config: PhysicalLedgerConfig | None = None,
    topology: HardwareTopologyConfig | None = None,
    model_name: str = "custom",
) -> TierPhysicalMetrics:
    """Calculate parametric prefill and decode ledger across all physical subsystems."""
    cfg = config or PhysicalLedgerConfig()
    topo = topology or HardwareTopologyConfig()

    res_summary = analyze_model_residency(manifest, topology=topo, model_name=model_name)
    analog_params = res_summary.analog_projection_parameters
    num_layers = manifest.num_layers
    hidden = manifest.hidden_size

    # --- 1. Decode Latency & Computation ---
    # In decode (batch_size B, sequence length 1 token):
    # Total projection MACs per decode token = analog_params
    decode_macs = analog_params * batch_size

    # Analog MVM time (assuming parallel layer or pipeline with tile cycle)
    # Total sequential projection passes per layer = 6 projections (q, k, v, out, up, down)
    passes_per_layer = 6
    decode_mvm_time_s = num_layers * passes_per_layer * (cfg.analog_tile_cycle_ns * 1e-9)

    # Digital attention compute & memory read at step T = context_length
    kv_bytes = calculate_kv_cache_bytes(manifest, context_length, dtype_bytes=2) * batch_size
    attn_macs = 2 * context_length * hidden * num_layers * batch_size
    attn_compute_time_s = (attn_macs * 2) / (cfg.digital_attention_tflops * 1e12)

    # KV memory transfer time
    sram_cap_bytes = int(topo.sram_kv_capacity_mb * 1024 * 1024) if hasattr(topo, "sram_kv_capacity_mb") else 64 * 1024 * 1024
    if kv_bytes <= sram_cap_bytes:
        mem_bw = topo.sram_bandwidth_tb_s * 1e12
        is_hbm = False
    else:
        mem_bw = topo.hbm3e_bandwidth_tb_s * 1e12
        is_hbm = True
    attn_mem_time_s = kv_bytes / max(1.0, mem_bw)

    # Inter-die communication time if multi-chiplet
    chiplets = res_summary.chiplets_required_for_full_residency
    if chiplets > 1:
        inter_die_bytes_per_layer = hidden * 2 * batch_size  # activation pass
        ucie_bw = topo.inter_die_ucie_bandwidth_gb_s * 1e9
        inter_die_time_s = (inter_die_bytes_per_layer * num_layers) / max(1.0, ucie_bw)
    else:
        inter_die_bytes_per_layer = 0
        inter_die_time_s = 0.0

    total_decode_time_per_token_s = decode_mvm_time_s + attn_compute_time_s + attn_mem_time_s + inter_die_time_s
    decode_tps = batch_size / max(1e-9, total_decode_time_per_token_s)
    decode_latency_ms = total_decode_time_per_token_s * 1000.0

    # --- 2. Decode Energy Breakdown ---
    # a. Analog MVM
    e_mvm_uj = (decode_macs * cfg.energy_per_mvm_mac_pj) * 1e-6
    # b. ADC/DAC Conversions: input conversions + output conversions
    # Tile activations: inputs = hidden, outputs = hidden across 6 projections per layer
    activations_count = num_layers * passes_per_layer * hidden * batch_size
    e_adc_dac_uj = (
        activations_count * cfg.energy_per_dac_conv_pj
        + activations_count * cfg.energy_per_adc_conv_pj
    ) * 1e-6
    # c. SRAM & NoC
    activation_bytes = activations_count * 2
    e_sram_noc_uj = (
        activation_bytes * cfg.energy_per_sram_byte_pj
        + activation_bytes * cfg.energy_per_noc_byte_pj
    ) * 1e-6
    # d. Inter-die UCIe
    e_ucie_uj = (
        (inter_die_bytes_per_layer * num_layers) * cfg.energy_per_ucie_byte_pj
    ) * 1e-6 if chiplets > 1 else 0.0
    # e. Package HBM
    e_hbm_uj = (kv_bytes * cfg.energy_per_hbm_byte_pj) * 1e-6 if is_hbm else 0.0
    # f. Digital Attention
    e_attn_uj = (attn_macs * 2 * cfg.energy_per_digital_flop_pj) * 1e-6

    total_decode_uj = e_mvm_uj + e_adc_dac_uj + e_sram_noc_uj + e_ucie_uj + e_hbm_uj + e_attn_uj
    decode_energy_per_token_uj = total_decode_uj / batch_size

    # --- 3. Prefill Latency & Energy ---
    # Prefill processes context_length tokens
    prefill_macs = decode_macs * context_length
    prefill_attn_macs = 2 * (context_length**2) * hidden * num_layers * batch_size
    prefill_time_s = (
        (decode_mvm_time_s * math.ceil(context_length / 16))
        + ((prefill_attn_macs * 2) / (cfg.digital_attention_tflops * 1e12))
        + ((kv_bytes * context_length) / max(1.0, mem_bw))
    )
    ttft_ms = prefill_time_s * 1000.0
    prefill_tps = (context_length * batch_size) / max(1e-9, prefill_time_s)

    prefill_energy_total_uj = (
        (prefill_macs * cfg.energy_per_mvm_mac_pj * 1e-6)
        + (e_adc_dac_uj * context_length)
        + (e_sram_noc_uj * context_length)
        + (prefill_attn_macs * 2 * cfg.energy_per_digital_flop_pj * 1e-6)
    )
    prefill_energy_per_token_uj = prefill_energy_total_uj / (context_length * batch_size)

    # --- 4. Power & Thermal Classification ---
    # Power = Energy / Time (Watts)
    active_power_w = (total_decode_uj * 1e-6) / max(1e-9, total_decode_time_per_token_s)
    total_area_cm2 = max(0.01, res_summary.total_silicon_area_mm2 / 100.0)
    power_density_w_cm2 = active_power_w / total_area_cm2

    if power_density_w_cm2 <= cfg.max_air_cooled_power_density_w_cm2:
        thermal_cls = "PASS_AIR_COOLED"
    elif power_density_w_cm2 <= cfg.max_liquid_cooled_power_density_w_cm2:
        thermal_cls = "PASS_LIQUID_COOLED"
    else:
        thermal_cls = "THERMAL_THROTTLE"

    return TierPhysicalMetrics(
        model_name=model_name,
        batch_size=batch_size,
        context_length=context_length,
        ttft_ms=ttft_ms,
        prefill_throughput_tok_s=prefill_tps,
        decode_tokens_per_second=decode_tps,
        decode_latency_per_token_ms=decode_latency_ms,
        prefill_energy_per_token_uj=prefill_energy_per_token_uj,
        decode_energy_per_token_uj=decode_energy_per_token_uj,
        decode_breakdown=SubsystemEnergyBreakdown(
            analog_mvm_uj=e_mvm_uj,
            adc_dac_conversion_uj=e_adc_dac_uj,
            sram_and_noc_uj=e_sram_noc_uj,
            inter_die_ucie_uj=e_ucie_uj,
            package_hbm_uj=e_hbm_uj,
            digital_attention_uj=e_attn_uj,
            total_energy_uj=total_decode_uj,
        ),
        active_power_w=active_power_w,
        power_density_w_cm2=power_density_w_cm2,
        die_count=res_summary.chiplets_required_for_full_residency,
        total_silicon_area_mm2=res_summary.total_silicon_area_mm2,
        thermal_classification=thermal_cls,
        provenance={
            "analog_mvm": "spice_extracted (28nm BEOL ReRAM)",
            "adc_dac": "measured/spice_correlated (8-bit SAR)",
            "sram_noc": "derived (28nm digital standard cell)",
            "ucie_link": "derived (UCIe standard specification)",
            "hbm3e": "derived (JEDEC HBM3e specification)",
            "thermal_limits": "assumed (standard air/liquid cooling boundaries)",
        },
    )
