r"""Chapter 0024 — SRAM & Buffer Capacity Model (Gate R6).

Models deterministic on-chip SRAM storage, staging buffers, and traffic ledgers
for analog crossbar accelerators executing Transformer inference workloads:

1. **Per-Tile Buffer Sizing ($R \times C$ tile)**:
   - **Activation Input Buffer (double-buffered)**:
     $$S_{\text{act}} = 2 \times C \times B_{\text{DAC}}\text{ bits}$$
   - **Accumulator & Partial-Sum Buffer**:
     $$S_{\text{acc}} = R \times B_{\text{acc}}\text{ bits}, \quad B_{\text{acc}} = B_{\text{ADC}} + \lceil \log_2 K_c \rceil$$
   - **Weight Shadow / Staging Buffer**:
     $$S_{\text{weight}} = 2 \times R \times C \times B_{\text{weight}}\text{ bits}$$
     (stores digital programming levels for differential $(G^+, G^-)$ cell pairs).

2. **System-Level / Global Buffers**:
   - **Activation Scratchpad / FIFO**: Holds intermediate activation vectors across layer boundaries.
   - **KV Cache Buffer**:
     $$S_{\text{KV}}(L) = 2 \times L \times n_{\text{layers}} \times d_{\text{model}} \times B_{\text{act}}\text{ bits}$$

3. **Traffic & Memory Access Ledger**:
   - Input activation traffic per MVM.
   - Output digitized traffic per MVM.
   - Weight reprogram bandwidth under temporal reuse.
   - Memory access energy accounting ($e_{\text{sram\_byte}} \approx 1.0\text{ pJ/byte}$, explicitly assumed).
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# Provenance / sensitivity constants (explicitly marked ASSUMED)
ASSUMED_SRAM_ENERGY_PJ_PER_BYTE = 1.0  # ~28nm/45nm planar SRAM read/write energy
ASSUMED_SRAM_BITCELL_AREA_UM2 = 0.12   # ~28nm 6T SRAM cell area


@dataclass(frozen=True)
class TileBufferConfig:
    """Configuration parameters for sizing tile-level buffers."""

    tile_rows: int = 16
    tile_cols: int = 16
    dac_bits: int = 4
    adc_bits: int = 4
    weight_bits: int = 4
    kc_max: int = 16  # max spatial tile columns contributing to partial sums
    double_buffer_inputs: bool = True

    def __post_init__(self) -> None:
        if self.tile_rows <= 0 or self.tile_cols <= 0:
            raise ValueError("tile rows/cols must be positive")
        if self.dac_bits <= 0 or self.adc_bits <= 0 or self.weight_bits <= 0:
            raise ValueError("converter and weight bits must be positive")
        if self.kc_max <= 0:
            raise ValueError("kc_max must be positive")


@dataclass(frozen=True)
class TileBufferCapacity:
    """Calculated bit and byte capacities for a single physical tile."""

    activation_buffer_bits: int
    accumulator_buffer_bits: int
    weight_staging_buffer_bits: int
    total_tile_sram_bits: int
    total_tile_sram_bytes: float
    accumulator_word_bits: int
    sram_area_estimate_um2: float


@dataclass(frozen=True)
class KVCacheCapacity:
    """Calculated memory requirements for multi-head attention Key-Value caching."""

    seq_len: int
    num_layers: int
    d_model: int
    act_bits: int
    total_kv_bits: int
    total_kv_bytes: float
    total_kv_kbytes: float


@dataclass
class BufferTrafficLedger:
    """Data movement and memory energy ledger for an execution run."""

    num_mvm_operations: int
    num_tile_rewrites: int
    input_activation_bytes: float
    output_activation_bytes: float
    weight_load_bytes: float
    total_sram_traffic_bytes: float
    estimated_sram_energy_nj: float


def compute_tile_buffer_capacity(config: TileBufferConfig) -> TileBufferCapacity:
    """Compute exact bit/byte storage requirements for one physical crossbar tile."""
    # 1. Activation buffer (double buffered if enabled)
    num_input_buffers = 2 if config.double_buffer_inputs else 1
    act_bits = num_input_buffers * config.tile_cols * config.dac_bits

    # 2. Accumulator buffer: B_acc = B_adc + ceil(log2(kc_max))
    acc_word_bits = config.adc_bits + math.ceil(math.log2(config.kc_max))
    acc_bits = config.tile_rows * acc_word_bits

    # 3. Weight staging buffer: differential pairs (G+, G-) -> 2 cells per crosspoint
    weight_bits = 2 * config.tile_rows * config.tile_cols * config.weight_bits

    total_bits = act_bits + acc_bits + weight_bits
    total_bytes = total_bits / 8.0
    area_um2 = total_bits * ASSUMED_SRAM_BITCELL_AREA_UM2

    return TileBufferCapacity(
        activation_buffer_bits=act_bits,
        accumulator_buffer_bits=acc_bits,
        weight_staging_buffer_bits=weight_bits,
        total_tile_sram_bits=total_bits,
        total_tile_sram_bytes=total_bytes,
        accumulator_word_bits=acc_word_bits,
        sram_area_estimate_um2=area_um2,
    )


def compute_kv_cache_capacity(
    seq_len: int,
    num_layers: int,
    d_model: int,
    act_bits: int = 16,
) -> KVCacheCapacity:
    """Compute Key-Value cache storage for autoregressive Transformer inference."""
    if seq_len <= 0 or num_layers <= 0 or d_model <= 0 or act_bits <= 0:
        raise ValueError("all KV cache dimensions and precisions must be positive")

    # 2 vectors (Key + Value) per token, per layer, with d_model elements of act_bits
    total_bits = 2 * seq_len * num_layers * d_model * act_bits
    total_bytes = total_bits / 8.0
    total_kb = total_bytes / 1024.0

    return KVCacheCapacity(
        seq_len=seq_len,
        num_layers=num_layers,
        d_model=d_model,
        act_bits=act_bits,
        total_kv_bits=total_bits,
        total_kv_bytes=total_bytes,
        total_kv_kbytes=total_kb,
    )


def compute_buffer_traffic(
    tile_config: TileBufferConfig,
    num_mvm_operations: int,
    num_tile_rewrites: int,
) -> BufferTrafficLedger:
    """Calculate total data movement volume and memory energy for a schedule."""
    if num_mvm_operations < 0 or num_tile_rewrites < 0:
        raise ValueError("operation counts must be non-negative")

    # Bytes transferred per MVM
    in_bytes = (tile_config.tile_cols * tile_config.dac_bits / 8.0) * num_mvm_operations
    out_bytes = (tile_config.tile_rows * tile_config.adc_bits / 8.0) * num_mvm_operations

    # Weight load bytes during rewrites
    weight_bytes_per_tile = (2 * tile_config.tile_rows * tile_config.tile_cols * tile_config.weight_bits) / 8.0
    weight_bytes = weight_bytes_per_tile * num_tile_rewrites

    total_bytes = in_bytes + out_bytes + weight_bytes
    energy_nj = (total_bytes * ASSUMED_SRAM_ENERGY_PJ_PER_BYTE) / 1000.0

    return BufferTrafficLedger(
        num_mvm_operations=num_mvm_operations,
        num_tile_rewrites=num_tile_rewrites,
        input_activation_bytes=in_bytes,
        output_activation_bytes=out_bytes,
        weight_load_bytes=weight_bytes,
        total_sram_traffic_bytes=total_bytes,
        estimated_sram_energy_nj=energy_nj,
    )


def generate_sram_buffers_extract() -> dict[str, Any]:
    """Generate deterministic extract dictionary for committed artifact."""
    cfg_16x16_4bit = TileBufferConfig(
        tile_rows=16,
        tile_cols=16,
        dac_bits=4,
        adc_bits=4,
        weight_bits=4,
        kc_max=16,
        double_buffer_inputs=True,
    )
    cap_16x16 = compute_tile_buffer_capacity(cfg_16x16_4bit)

    cfg_32x32_4bit = TileBufferConfig(
        tile_rows=32,
        tile_cols=32,
        dac_bits=4,
        adc_bits=4,
        weight_bits=4,
        kc_max=32,
        double_buffer_inputs=True,
    )
    cap_32x32 = compute_tile_buffer_capacity(cfg_32x32_4bit)

    # Workload traffic examples: TinyGPT (d_model=64, 4 layers) and LLaMA-7B projection
    traffic_tinygpt_1token = compute_buffer_traffic(
        cfg_16x16_4bit,
        num_mvm_operations=64,
        num_tile_rewrites=0,  # weight-stationary
    )
    traffic_tinygpt_reprogrammed = compute_buffer_traffic(
        cfg_16x16_4bit,
        num_mvm_operations=64,
        num_tile_rewrites=48,  # temporal multiplexed
    )

    kv_cache_tinygpt = compute_kv_cache_capacity(
        seq_len=128,
        num_layers=4,
        d_model=64,
        act_bits=16,
    )
    kv_cache_llama7b = compute_kv_cache_capacity(
        seq_len=2048,
        num_layers=32,
        d_model=4096,
        act_bits=16,
    )

    return {
        "schema_version": "0.1.0",
        "chapter": "0024-sram-buffers",
        "title": "SRAM & Buffer Capacity Model",
        "provenance": {
            "sram_energy_model": "assumed_1.0_pj_per_byte",
            "sram_cell_area_model": "assumed_0.12_um2_per_bit",
            "physical_claim": False,
        },
        "formulas": {
            "activation_buffer": "S_act = 2 * C * B_dac",
            "accumulator_word": "B_acc = B_adc + ceil(log2(K_c))",
            "accumulator_buffer": "S_acc = R * (B_adc + ceil(log2(K_c)))",
            "weight_staging_buffer": "S_weight = 2 * R * C * B_weight",
            "kv_cache": "S_kv = 2 * L * n_layers * d_model * B_act",
            "sram_energy": "E_sram = Bytes_total * e_byte",
        },
        "tile_capacities": {
            "16x16_4bit": {
                "config": asdict(cfg_16x16_4bit),
                "capacity": asdict(cap_16x16),
            },
            "32x32_4bit": {
                "config": asdict(cfg_32x32_4bit),
                "capacity": asdict(cap_32x32),
            },
        },
        "kv_cache_capacities": {
            "tinygpt_128ctx": asdict(kv_cache_tinygpt),
            "llama7b_2048ctx": asdict(kv_cache_llama7b),
        },
        "traffic_ledgers": {
            "tinygpt_weight_stationary": asdict(traffic_tinygpt_1token),
            "tinygpt_temporal_multiplexed": asdict(traffic_tinygpt_reprogrammed),
        },
    }


def render_svg(extract: dict[str, Any]) -> str:
    """Render an SVG diagram illustrating the tile buffer hierarchy and data flow."""
    cap16 = extract["tile_capacities"]["16x16_4bit"]["capacity"]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540" width="960" height="540">
<style>
text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: #0f172a; }}
.title {{ font-size: 20px; font-weight: 700; }}
.sub {{ font-size: 12px; fill: #475569; }}
.box-title {{ font-size: 14px; font-weight: 700; }}
.box-text {{ font-size: 12px; fill: #334155; }}
.formula {{ font: 12px ui-monospace, monospace; fill: #1e293b; }}
.arrow {{ stroke: #64748b; stroke-width: 2; marker-end: url(#arrow); }}
</style>
<defs>
<marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
  <path d="M0,0 L8,4 L0,8 Z" fill="#64748b"/>
</marker>
</defs>
<rect width="960" height="540" fill="white"/>
<text x="480" y="35" text-anchor="middle" class="title">Chapter 0024 — SRAM &amp; Buffer Capacity Hierarchy</text>
<text x="480" y="55" text-anchor="middle" class="sub">Storage sizing and data movement across tile registers, accumulators, and KV cache</text>

<!-- Tile SRAM Box -->
<rect x="50" y="85" width="400" height="420" rx="12" fill="#f8fafc" stroke="#334155" stroke-width="2"/>
<text x="70" y="115" class="box-title" fill="#0f172a">Per-Tile SRAM Buffers (16×16 Tile, 4-bit)</text>
<text x="70" y="135" class="sub">Total Tile SRAM: {cap16["total_tile_sram_bits"]} bits ({cap16["total_tile_sram_bytes"]:.1f} bytes)</text>

<!-- Input Buffer -->
<rect x="70" y="155" width="360" height="85" rx="8" fill="#eff6ff" stroke="#2563eb"/>
<text x="90" y="180" class="box-title" fill="#1d4ed8">1. Input Activation Buffer (Double-Buffered)</text>
<text x="90" y="202" class="box-text">Capacity: 2 × 16 cols × 4 bits = {cap16["activation_buffer_bits"]} bits (16 bytes)</text>
<text x="90" y="222" class="sub">Ping-pong buffer for continuous pipelined DAC driving</text>

<!-- Weight Buffer -->
<rect x="70" y="255" width="360" height="85" rx="8" fill="#fefce8" stroke="#ca8a04"/>
<text x="90" y="280" class="box-title" fill="#a16207">2. Weight Shadow Buffer (Differential Pairs)</text>
<text x="90" y="302" class="box-text">Capacity: 2 × (16×16) × 4 bits = {cap16["weight_staging_buffer_bits"]} bits (256 bytes)</text>
<text x="90" y="322" class="sub">Holds target programming levels during temporal multiplexing</text>

<!-- Accumulator Buffer -->
<rect x="70" y="355" width="360" height="85" rx="8" fill="#f0fdf4" stroke="#16a34a"/>
<text x="90" y="380" class="box-title" fill="#15803d">3. Partial-Sum Accumulator Buffer</text>
<text x="90" y="402" class="box-text">Wordlength: B_acc = 4 + ceil(log2(16)) = {cap16["accumulator_word_bits"]} bits</text>
<text x="90" y="422" class="box-text">Capacity: 16 rows × 8 bits = {cap16["accumulator_buffer_bits"]} bits (16 bytes)</text>

<!-- Global KV Cache Box -->
<rect x="490" y="85" width="420" height="230" rx="12" fill="#faf5ff" stroke="#9333ea" stroke-width="2"/>
<text x="510" y="115" class="box-title" fill="#7e22ce">Global / Layer KV Cache Buffer</text>
<text x="510" y="135" class="sub">Formula: S_kv = 2 × L × n_layers × d_model × B_act</text>
<rect x="510" y="150" width="380" height="65" rx="6" fill="#f3e8ff" stroke="#a855f7"/>
<text x="525" y="173" class="box-title" fill="#6b21a8">TinyGPT (4L, d=64, L=128, 16-bit)</text>
<text x="525" y="195" class="box-text">Total KV Cache: 1,048,576 bits = 128 KB</text>
<rect x="510" y="225" width="380" height="65" rx="6" fill="#f3e8ff" stroke="#a855f7"/>
<text x="525" y="248" class="box-title" fill="#6b21a8">LLaMA-7B (32L, d=4096, L=2048, 16-bit)</text>
<text x="525" y="270" class="box-text">Total KV Cache: 8,589,934,592 bits = 1.00 GB</text>

<!-- Traffic & Energy Box -->
<rect x="490" y="330" width="420" height="175" rx="12" fill="#fff7ed" stroke="#ea580c" stroke-width="2"/>
<text x="510" y="360" class="box-title" fill="#c2410c">Data Movement &amp; Energy Ledger</text>
<text x="510" y="385" class="box-text">• Weight-Stationary: SRAM traffic is purely input/output activations</text>
<text x="510" y="405" class="box-text">• Temporal-Multiplexed: Incurs 256 B weight traffic per tile reprogram</text>
<text x="510" y="430" class="formula">E_sram = Bytes_total × 1.0 pJ/B (assumed)</text>
<text x="510" y="455" class="sub">• TinyGPT Weight-Stationary: 1.02 KB / token (1.02 nJ)</text>
<text x="510" y="475" class="sub">• TinyGPT Temporal-Multiplexed: 13.31 KB / token (13.31 nJ)</text>
</svg>
"""


def main() -> None:
    extract = generate_sram_buffers_extract()
    out_dir = Path(__file__).resolve().parents[2] / "verification" / "circuit" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    extract_path = out_dir / "sram-buffers-0024-extract.json"
    extract_path.write_text(json.dumps(extract, indent=2, sort_keys=True) + "\n", "utf-8")

    diagram_dir = Path(__file__).resolve().parent / "diagrams"
    diagram_dir.mkdir(parents=True, exist_ok=True)
    svg_path = diagram_dir / "sram-buffers-0024.svg"
    svg_path.write_text(render_svg(extract), "utf-8")

    print(f"Wrote {extract_path}")
    print(f"Wrote {svg_path}")
    cap = extract["tile_capacities"]["16x16_4bit"]["capacity"]
    print(
        f"16x16 4-bit tile SRAM: {cap['total_tile_sram_bits']} bits "
        f"({cap['total_tile_sram_bytes']} bytes)"
    )


if __name__ == "__main__":
    main()
