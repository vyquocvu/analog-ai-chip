r"""Chapter 0031 — Key-Value (KV) Cache Capacity and Traffic Model (Gate R7).

Models the dynamic token state memory capacity, autoregressive traffic scaling,
paging policies, and memory energy ledger for Transformer attention:

1. **Memory Capacity & Footprint Scaling**:
   - For an $n_{\text{layers}}$-layer model with hidden size $d_{\text{model}}$ and sequence length $L$:
     $$S_{\text{KV}}(L) = 2 \cdot n_{\text{layers}} \cdot L \cdot d_{\text{model}} \cdot \frac{B_{\text{act}}}{8}\text{ bytes}$$
   - Quantifies memory requirements across precisions ($B_{\text{act}} \in \{4, 8, 16\}$ bits).

2. **Autoregressive Traffic Ledger & Bandwidth**:
   - Write traffic per token step: $T_{\text{write}} = 2 \cdot n_{\text{layers}} \cdot d_{\text{model}} \cdot \frac{B_{\text{act}}}{8}\text{ bytes/token}$ ($O(1)$).
   - Read traffic at step $t$: $T_{\text{read}}(t) = 2 \cdot n_{\text{layers}} \cdot t \cdot d_{\text{model}} \cdot \frac{B_{\text{act}}}{8}\text{ bytes/token}$ ($O(t)$).
   - Cumulative read traffic over $L$ tokens:
     $$T_{\text{read,total}}(L) = 2 \cdot n_{\text{layers}} \cdot d_{\text{model}} \cdot \frac{B_{\text{act}}}{8} \cdot \frac{L(L+1)}{2}\text{ bytes} \quad (O(L^2))$$

3. **Paging Policies & Memory Tiers**:
   - Evaluates contiguous static allocation vs paged dynamic block allocation ($B_{\text{block}} = 16\text{ tokens}$).
   - Computes internal/external fragmentation and energy across On-Chip SRAM ($1.0\text{ pJ/byte}$) and Off-Chip DRAM ($20.0\text{ pJ/byte}$).
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))


@dataclass(frozen=True)
class KVCacheConfig:
    """Configuration for KV cache simulation."""

    num_layers: int = 4
    d_model: int = 64
    num_heads: int = 4
    act_bits: int = 4
    max_context_len: int = 128
    block_size_tokens: int = 16
    energy_sram_byte_pj: float = 1.0  # 1.0 pJ/byte on-chip SRAM (assumed)
    energy_dram_byte_pj: float = 20.0  # 20.0 pJ/byte off-chip LPDDR5/HBM (assumed)

    def __post_init__(self) -> None:
        if self.num_layers <= 0 or self.d_model <= 0 or self.num_heads <= 0:
            raise ValueError("model architecture parameters must be positive")
        if self.max_context_len <= 0 or self.block_size_tokens <= 0:
            raise ValueError("context and block size must be positive")
        if self.act_bits not in (4, 8, 16, 32):
            raise ValueError("act_bits must be 4, 8, 16, or 32")

    @property
    def d_head(self) -> int:
        return self.d_model // self.num_heads

    @property
    def bytes_per_token_per_layer(self) -> float:
        # 2 tensors (Key, Value) * d_model * (act_bits / 8)
        return 2.0 * self.d_model * (self.act_bits / 8.0)

    @property
    def bytes_per_token_all_layers(self) -> float:
        return self.num_layers * self.bytes_per_token_per_layer


@dataclass(frozen=True)
class StepTrafficRecord:
    """Traffic metrics for a single token decoding step."""

    step_t: int
    write_bytes: int
    read_bytes: int
    sram_energy_pj: float
    dram_energy_pj: float


@dataclass(frozen=True)
class GenerationLedgerSummary:
    """Summary of KV cache capacity, traffic, and memory fragmentation across a prompt/generation run."""

    prompt_len: int
    gen_len: int
    total_seq_len: int
    peak_kv_cache_bytes: int
    total_write_bytes: int
    total_read_bytes: int
    total_kv_traffic_bytes: int
    sram_total_energy_nj: float
    dram_total_energy_nj: float
    contiguous_allocated_bytes: int
    paged_allocated_bytes: int
    contiguous_fragmentation_pct: float
    paged_fragmentation_pct: float


class KVCacheSimulator:
    """Simulates dynamic Key-Value state accumulation and traffic scaling."""

    def __init__(self, config: KVCacheConfig) -> None:
        self.config = config

    def capacity_bytes(self, context_len: int, act_bits: int | None = None) -> int:
        """Compute exact KV cache memory footprint for context length L."""
        bits = act_bits or self.config.act_bits
        return math.ceil(2 * self.config.num_layers * context_len * self.config.d_model * (bits / 8.0))

    def simulate_generation(self, prompt_len: int, gen_tokens: int) -> GenerationLedgerSummary:
        """Simulate autoregressive decode generation from prompt_len to prompt_len + gen_tokens."""
        if prompt_len < 1:
            raise ValueError("prompt_len must be at least 1")
        if gen_tokens < 0:
            raise ValueError("gen_tokens cannot be negative")

        total_seq_len = prompt_len + gen_tokens
        if total_seq_len > self.config.max_context_len:
            raise ValueError(
                f"total sequence length {total_seq_len} exceeds max_context_len {self.config.max_context_len}"
            )

        bytes_per_step_write = int(self.config.bytes_per_token_all_layers)

        # Prefill prompt write
        total_write_bytes = prompt_len * bytes_per_step_write
        total_read_bytes = 0

        # Autoregressive generation steps
        for step in range(gen_tokens):
            current_context = prompt_len + step
            # Write new token KV
            total_write_bytes += bytes_per_step_write
            # Read all previous context KV
            step_read = current_context * bytes_per_step_write
            total_read_bytes += step_read

        total_traffic = total_write_bytes + total_read_bytes
        peak_bytes = self.capacity_bytes(total_seq_len)

        sram_energy_nj = (total_traffic * self.config.energy_sram_byte_pj) / 1000.0
        dram_energy_nj = (total_traffic * self.config.energy_dram_byte_pj) / 1000.0

        # Contiguous allocation assumes reserving full max_context_len
        contiguous_alloc = self.capacity_bytes(self.config.max_context_len)
        contiguous_frag = ((contiguous_alloc - peak_bytes) / contiguous_alloc) * 100.0

        # Paged allocation allocates ceil(total_seq_len / block_size) blocks
        num_blocks = math.ceil(total_seq_len / self.config.block_size_tokens)
        paged_alloc = num_blocks * self.capacity_bytes(self.config.block_size_tokens)
        paged_frag = max(0.0, ((paged_alloc - peak_bytes) / paged_alloc) * 100.0)

        return GenerationLedgerSummary(
            prompt_len=prompt_len,
            gen_len=gen_tokens,
            total_seq_len=total_seq_len,
            peak_kv_cache_bytes=peak_bytes,
            total_write_bytes=total_write_bytes,
            total_read_bytes=total_read_bytes,
            total_kv_traffic_bytes=total_traffic,
            sram_total_energy_nj=float(round(sram_energy_nj, 4)),
            dram_total_energy_nj=float(round(dram_energy_nj, 4)),
            contiguous_allocated_bytes=contiguous_alloc,
            paged_allocated_bytes=paged_alloc,
            contiguous_fragmentation_pct=float(round(contiguous_frag, 2)),
            paged_fragmentation_pct=float(round(paged_frag, 2)),
        )


def generate_kv_cache_extract() -> dict[str, Any]:
    """Generate deterministic extract dictionary for committed artifact."""
    cfg = KVCacheConfig(
        num_layers=4,
        d_model=64,
        num_heads=4,
        act_bits=4,
        max_context_len=128,
        block_size_tokens=16,
    )
    sim = KVCacheSimulator(cfg)

    # Workload 1: Short decode (Prompt=16, Gen=16 -> 32 tokens)
    run_short = sim.simulate_generation(prompt_len=16, gen_tokens=16)

    # Workload 2: Medium decode (Prompt=32, Gen=32 -> 64 tokens)
    run_med = sim.simulate_generation(prompt_len=32, gen_tokens=32)

    # Workload 3: Full Context decode (Prompt=32, Gen=96 -> 128 tokens)
    run_full = sim.simulate_generation(prompt_len=32, gen_tokens=96)

    # Precision sensitivity comparison for full context (128 tokens)
    precisions = {
        "4bit_bytes": sim.capacity_bytes(128, act_bits=4),
        "8bit_bytes": sim.capacity_bytes(128, act_bits=8),
        "16bit_fp16_bytes": sim.capacity_bytes(128, act_bits=16),
        "32bit_fp32_bytes": sim.capacity_bytes(128, act_bits=32),
    }

    return {
        "schema_version": "0.1.0",
        "chapter": "0031-kv-cache",
        "title": "KV Cache Capacity and Traffic Model",
        "gate": "R7 — Transformer and LLM validation",
        "provenance": {
            "sram_buffers_model": "Chapter 0024 sram_buffers.py",
            "architecture_ledger": "Chapter 0026 architecture_ledger.py",
            "claim_level": "SYSTEM_SIMULATED",
        },
        "formulas": {
            "kv_capacity": "S_KV = 2 * n_layers * L * d_model * (B_act / 8) bytes",
            "per_step_write": "T_write = 2 * n_layers * d_model * (B_act / 8) bytes/token",
            "per_step_read": "T_read(t) = 2 * n_layers * t * d_model * (B_act / 8) bytes/token",
            "cumulative_read": "T_read_total = T_write * sum(t=prompt_len)^(L-1) t",
        },
        "precision_comparison_128_ctx": precisions,
        "evaluations": {
            "short_sequence_32": asdict(run_short),
            "medium_sequence_64": asdict(run_med),
            "full_context_128": asdict(run_full),
        },
    }


def render_svg(extract: dict[str, Any]) -> str:
    """Render an SVG diagram illustrating the KV cache memory model and traffic scaling."""
    full = extract["evaluations"]["full_context_128"]
    prec = extract["precision_comparison_128_ctx"]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540" width="960" height="540">
<style>
text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: #0f172a; }}
.title {{ font-size: 20px; font-weight: 700; }}
.sub {{ font-size: 12px; fill: #475569; }}
.box-title {{ font-size: 14px; font-weight: 700; }}
.box-text {{ font-size: 12px; fill: #334155; }}
.formula {{ font: 12px ui-monospace, monospace; fill: #1e293b; }}
</style>
<rect width="960" height="540" fill="white"/>
<text x="480" y="35" text-anchor="middle" class="title">Chapter 0031 — Key-Value (KV) Cache Memory &amp; Traffic</text>
<text x="480" y="55" text-anchor="middle" class="sub">Dynamic token state capacity, autoregressive traffic scaling, and paging efficiency</text>

<!-- Capacity & Precision Box -->
<rect x="50" y="85" width="410" height="420" rx="12" fill="#eff6ff" stroke="#2563eb" stroke-width="2"/>
<text x="70" y="115" class="box-title" fill="#1d4ed8">1. KV Cache Footprint &amp; Precision Scaling</text>
<text x="70" y="135" class="sub">TinyGPT: 4 layers, d_model=64, Context L=128 tokens</text>

<rect x="70" y="155" width="370" height="150" rx="8" fill="white" stroke="#93c5fd"/>
<text x="85" y="180" class="box-title" fill="#1e40af">Footprint Across Bit-Widths (128 Tokens)</text>
<text x="85" y="202" class="box-text">• 4-bit Quantized: {prec["4bit_bytes"] / 1024:.1f} KB ({prec["4bit_bytes"]} bytes) [Baseline]</text>
<text x="85" y="222" class="box-text">• 8-bit Quantized: {prec["8bit_bytes"] / 1024:.1f} KB ({prec["8bit_bytes"]} bytes) [2.0× footprint]</text>
<text x="85" y="242" class="box-text">• 16-bit FP16: {prec["16bit_fp16_bytes"] / 1024:.1f} KB ({prec["16bit_fp16_bytes"]} bytes) [4.0× footprint]</text>
<text x="85" y="262" class="box-text">• 32-bit FP32: {prec["32bit_fp32_bytes"] / 1024:.1f} KB ({prec["32bit_fp32_bytes"]} bytes) [8.0× footprint]</text>
<text x="85" y="282" class="sub">S_KV = 2 · n_layers · L · d_model · (B_act / 8)</text>

<rect x="70" y="320" width="370" height="165" rx="8" fill="#f8fafc" stroke="#cbd5e1"/>
<text x="85" y="345" class="box-title">Paging Efficiency (Prompt=32, Gen=96)</text>
<text x="85" y="370" class="box-text">• Contiguous Pre-alloc: {full["contiguous_allocated_bytes"] / 1024:.1f} KB (Frag: {full["contiguous_fragmentation_pct"]:.1f}%)</text>
<text x="85" y="392" class="box-text">• Paged Alloc (Block=16): {full["paged_allocated_bytes"] / 1024:.1f} KB (Frag: {full["paged_fragmentation_pct"]:.1f}%)</text>
<text x="85" y="415" class="box-title" fill="#15803d">• Paged KV eliminates external memory fragmentation</text>
<text x="85" y="440" class="formula">B_per_step = 4 layers · 2 · 64 · 0.5 B = 256 B/tok</text>

<!-- Traffic & Energy Box -->
<rect x="500" y="85" width="410" height="420" rx="12" fill="#faf5ff" stroke="#9333ea" stroke-width="2"/>
<text x="520" y="115" class="box-title" fill="#7e22ce">2. Autoregressive Traffic &amp; Memory Tiers</text>
<text x="520" y="135" class="sub">Quadratic cumulative read bandwidth demands O(L²)</text>

<!-- Traffic Breakdown -->
<rect x="520" y="155" width="370" height="150" rx="8" fill="white" stroke="#d8b4fe"/>
<text x="535" y="180" class="box-title" fill="#6b21a8">Generation Traffic (Prompt=32, Gen=96)</text>
<text x="535" y="202" class="box-text">• Total Write Traffic: {full["total_write_bytes"] / 1024:.1f} KB (256 B / token)</text>
<text x="535" y="222" class="box-text">• Total Read Traffic: {full["total_read_bytes"] / 1024:.1f} KB (quadratic read)</text>
<text x="535" y="242" class="box-title" fill="#1e40af">• Cumulative KV Traffic: {full["total_kv_traffic_bytes"] / 1024:.1f} KB ({full["total_kv_traffic_bytes"]} bytes)</text>
<text x="535" y="262" class="sub">Read traffic dominates write traffic by {full["total_read_bytes"] / full["total_write_bytes"]:.1f}×</text>

<!-- Memory Tiers Energy -->
<rect x="520" y="320" width="370" height="165" rx="8" fill="#f0fdf4" stroke="#86efac"/>
<text x="535" y="345" class="box-title" fill="#166534">Memory Hierarchy Energy Ledger</text>
<text x="535" y="370" class="box-text">• Local On-Chip SRAM (1.0 pJ/B): {full["sram_total_energy_nj"]:.1f} nJ</text>
<text x="535" y="392" class="box-text">• Off-Chip DRAM / HBM (20.0 pJ/B): {full["dram_total_energy_nj"]:.1f} nJ</text>
<text x="535" y="415" class="box-title" fill="#15803d">• On-Chip SRAM saves 20.0× memory access energy</text>
<text x="535" y="440" class="formula">E_SRAM = {full["sram_total_energy_nj"]:.1f} nJ vs E_DRAM = {full["dram_total_energy_nj"]:.1f} nJ</text>
</svg>
"""


def main() -> None:
    extract = generate_kv_cache_extract()
    out_dir = Path(__file__).resolve().parents[2] / "verification" / "circuit" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    extract_path = out_dir / "kv-cache-0031-extract.json"
    extract_path.write_text(json.dumps(extract, indent=2, sort_keys=True) + "\n", "utf-8")

    diagram_dir = Path(__file__).resolve().parent / "diagrams"
    diagram_dir.mkdir(parents=True, exist_ok=True)
    svg_path = diagram_dir / "kv-cache-0031.svg"
    svg_path.write_text(render_svg(extract), "utf-8")

    print(f"Wrote {extract_path}")
    print(f"Wrote {svg_path}")
    full = extract["evaluations"]["full_context_128"]
    print(
        f"TinyGPT KV Cache (128 ctx): Peak={full['peak_kv_cache_bytes'] / 1024:.1f} KB, "
        f"Total Traffic={full['total_kv_traffic_bytes'] / 1024:.1f} KB, SRAM Energy={full['sram_total_energy_nj']:.2f} nJ"
    )


if __name__ == "__main__":
    main()
