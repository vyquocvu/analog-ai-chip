r"""Chapter 0025 — NoC / Interconnect Traffic Model (Gate R6).

Models deterministic on-chip Network-on-Chip (NoC) traffic, spatial reduction trees,
and interconnect latency/energy ledgers for multi-tile analog compute-in-memory arrays:

1. **Spatial Reduction Trees**:
   - For a tiled matrix of shape $K_r \times K_c$ physical tiles ($R \times C$ each):
   - $K_c$ partial sums along each row are reduced via a binary adder tree:
     $$\text{Tree Levels: } L_{\text{tree}} = \lceil \log_2 K_c \rceil$$
     $$\text{Total Transferred Vectors / Row: } N_{\text{xfer\_row}} = K_c - 1$$
     $$\text{Total Transferred Bytes: } T_{\text{reduct}} = K_r \times (K_c - 1) \times (R \cdot B_{\text{acc}} / 8)$$

2. **Activation Multicast / Broadcast**:
   - Input activation vector of length $K_c \times C$ is delivered to $K_r$ tile rows:
     $$T_{\text{act}} = K_c \times (C \cdot B_{\text{DAC}} / 8)\text{ bytes}$$

3. **Topology Comparisons**:
   - **Binary H-Tree Reduction**: $H_{\text{avg}} = O(\log_2 K_c)$ hops, bounded hop latency.
   - **2D Mesh NoC (X-Y Routing)**: Average Manhattan distance $\bar{H}_{\text{mesh}} = \frac{1}{3}(N_{\text{rows}} + N_{\text{cols}})$.
   - **Shared Ring Bus**: $H_{\text{avg}} = N_{\text{tiles}} / 4$ hops.

4. **Interconnect Energy & Latency Ledgers**:
   - Energy per byte-hop: $e_{\text{noc\_byte\_hop}} \approx 0.5\text{ pJ/(byte}\cdot\text{hop)}$ (`assumed`).
   - Hop latency: $t_{\text{hop}} \approx 1.0\text{ ns/hop}$ (`assumed`).
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any

# Sensitivity / provenance constants (explicitly ASSUMED)
ASSUMED_NOC_ENERGY_PJ_PER_BYTE_HOP = 0.5  # Router + link energy per byte-hop on 28nm
ASSUMED_NOC_HOP_LATENCY_NS = 1.0         # 1-cycle router traversal at 1 GHz


class NoCTopology(str, Enum):
    BINARY_TREE = "binary_tree"
    MESH_2D = "mesh_2d"
    RING_BUS = "ring_bus"


@dataclass(frozen=True)
class MatrixTilingConfig:
    """Tiling parameters for a matrix multiplication MVM workload."""

    m_out: int
    m_in: int
    tile_rows: int = 16
    tile_cols: int = 16
    dac_bits: int = 4
    adc_bits: int = 4

    def __post_init__(self) -> None:
        if self.m_out <= 0 or self.m_in <= 0:
            raise ValueError("matrix dimensions must be positive")
        if self.tile_rows <= 0 or self.tile_cols <= 0:
            raise ValueError("tile dimensions must be positive")
        if self.dac_bits <= 0 or self.adc_bits <= 0:
            raise ValueError("converter precision must be positive")

    @property
    def kr(self) -> int:
        return math.ceil(self.m_out / self.tile_rows)

    @property
    def kc(self) -> int:
        return math.ceil(self.m_in / self.tile_cols)

    @property
    def total_tiles(self) -> int:
        return self.kr * self.kc

    @property
    def b_acc(self) -> int:
        return self.adc_bits + math.ceil(math.log2(max(1, self.kc)))


@dataclass(frozen=True)
class ReductionNetworkMetrics:
    """Calculated traffic volume, latency, and energy for partial sum reduction."""

    topology: NoCTopology
    kr: int
    kc: int
    total_tiles: int
    b_acc_bits: int
    activation_broadcast_bytes: float
    reduction_traffic_bytes: float
    total_traffic_bytes: float
    avg_hops_per_transfer: float
    total_byte_hops: float
    critical_path_latency_ns: float
    estimated_noc_energy_nj: float


def compute_reduction_network_metrics(
    config: MatrixTilingConfig,
    topology: NoCTopology = NoCTopology.BINARY_TREE,
) -> ReductionNetworkMetrics:
    """Compute exact data movement volume, hop counts, latency, and energy."""
    kr, kc = config.kr, config.kc
    b_acc = config.b_acc

    # 1. Activation broadcast bytes (input vector of length m_in delivered to tiles)
    act_bytes = kc * (config.tile_cols * config.dac_bits / 8.0)

    # 2. Reduction traffic bytes along the column dimension
    # In each of the kr rows, kc partial sums are reduced, requiring (kc - 1) vector transfers
    bytes_per_psum_vector = config.tile_rows * b_acc / 8.0
    num_transfers = kr * max(0, kc - 1)
    reduct_bytes = num_transfers * bytes_per_psum_vector

    total_bytes = act_bytes + reduct_bytes

    # 3. Topology-specific hop calculation and critical path latency
    if topology == NoCTopology.BINARY_TREE:
        tree_levels = math.ceil(math.log2(max(1, kc)))
        avg_hops = float(tree_levels) if kc > 1 else 0.0
        critical_latency_ns = tree_levels * ASSUMED_NOC_HOP_LATENCY_NS
    elif topology == NoCTopology.MESH_2D:
        # Mesh layout of dimensions kr x kc
        avg_hops = (kr + kc) / 3.0 if config.total_tiles > 1 else 0.0
        critical_latency_ns = (kr + kc) * ASSUMED_NOC_HOP_LATENCY_NS
    elif topology == NoCTopology.RING_BUS:
        avg_hops = config.total_tiles / 4.0 if config.total_tiles > 1 else 0.0
        critical_latency_ns = (config.total_tiles / 2.0) * ASSUMED_NOC_HOP_LATENCY_NS
    else:
        raise ValueError(f"unknown topology {topology}")

    total_byte_hops = reduct_bytes * avg_hops + act_bytes * (avg_hops / 2.0 if avg_hops > 0 else 0.0)
    energy_nj = (total_byte_hops * ASSUMED_NOC_ENERGY_PJ_PER_BYTE_HOP) / 1000.0

    return ReductionNetworkMetrics(
        topology=topology,
        kr=kr,
        kc=kc,
        total_tiles=config.total_tiles,
        b_acc_bits=b_acc,
        activation_broadcast_bytes=act_bytes,
        reduction_traffic_bytes=reduct_bytes,
        total_traffic_bytes=total_bytes,
        avg_hops_per_transfer=avg_hops,
        total_byte_hops=total_byte_hops,
        critical_path_latency_ns=critical_latency_ns,
        estimated_noc_energy_nj=energy_nj,
    )


def generate_noc_interconnect_extract() -> dict[str, Any]:
    """Generate deterministic extract dictionary for committed artifact."""
    # Workload 1: TinyGPT Projection (64x64 mapped onto 16x16 tiles -> 4x4 = 16 tiles)
    tinygpt_cfg = MatrixTilingConfig(m_out=64, m_in=64, tile_rows=16, tile_cols=16)
    tinygpt_tree = compute_reduction_network_metrics(tinygpt_cfg, NoCTopology.BINARY_TREE)
    tinygpt_mesh = compute_reduction_network_metrics(tinygpt_cfg, NoCTopology.MESH_2D)
    tinygpt_ring = compute_reduction_network_metrics(tinygpt_cfg, NoCTopology.RING_BUS)

    # Workload 2: LLaMA-7B Projection (4096x4096 mapped onto 32x32 tiles -> 128x128 = 16,384 tiles)
    llama_cfg = MatrixTilingConfig(m_out=4096, m_in=4096, tile_rows=32, tile_cols=32)
    llama_tree = compute_reduction_network_metrics(llama_cfg, NoCTopology.BINARY_TREE)
    llama_mesh = compute_reduction_network_metrics(llama_cfg, NoCTopology.MESH_2D)

    return {
        "schema_version": "0.1.0",
        "chapter": "0025-noc-interconnect",
        "title": "NoC / Interconnect Traffic Model",
        "provenance": {
            "noc_energy_model": "assumed_0.5_pj_per_byte_hop",
            "noc_hop_latency": "assumed_1.0_ns_per_hop",
            "physical_claim": False,
        },
        "formulas": {
            "grid_dimensions": "Kr = ceil(M_out / Tile_R), Kc = ceil(M_in / Tile_C)",
            "accumulator_word": "B_acc = B_adc + ceil(log2(K_c))",
            "reduction_transfers": "N_transfers = Kr * (Kc - 1)",
            "reduction_traffic": "T_reduct = Kr * (Kc - 1) * (Tile_R * B_acc / 8)",
            "tree_hop_latency": "T_tree = ceil(log2(Kc)) * t_hop",
            "mesh_avg_hops": "H_mesh = (Kr + Kc) / 3",
            "noc_energy": "E_noc = sum(Bytes * Hops) * e_byte_hop",
        },
        "workloads": {
            "tinygpt_64x64_tile16": {
                "tiling": asdict(tinygpt_cfg),
                "topologies": {
                    "binary_tree": asdict(tinygpt_tree),
                    "mesh_2d": asdict(tinygpt_mesh),
                    "ring_bus": asdict(tinygpt_ring),
                },
            },
            "llama7b_4096x4096_tile32": {
                "tiling": asdict(llama_cfg),
                "topologies": {
                    "binary_tree": asdict(llama_tree),
                    "mesh_2d": asdict(llama_mesh),
                },
            },
        },
    }


def render_svg(extract: dict[str, Any]) -> str:
    """Render an SVG diagram illustrating the spatial reduction tree and NoC topologies."""
    tg_tree = extract["workloads"]["tinygpt_64x64_tile16"]["topologies"]["binary_tree"]
    tg_mesh = extract["workloads"]["tinygpt_64x64_tile16"]["topologies"]["mesh_2d"]
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
<text x="480" y="35" text-anchor="middle" class="title">Chapter 0025 — NoC &amp; Spatial Reduction Network</text>
<text x="480" y="55" text-anchor="middle" class="sub">Partial-sum spatial reduction tree vs 2D mesh data movement and energy ledgers</text>

<!-- Binary Tree Reduction Box -->
<rect x="50" y="85" width="410" height="420" rx="12" fill="#eff6ff" stroke="#2563eb" stroke-width="2"/>
<text x="70" y="115" class="box-title" fill="#1d4ed8">1. Spatial Binary Adder Tree (H-Tree)</text>
<text x="70" y="135" class="sub">Optimized for logarithmic latency across column tile reductions</text>

<rect x="70" y="155" width="370" height="155" rx="8" fill="white" stroke="#93c5fd"/>
<text x="85" y="180" class="box-title" fill="#1e40af">Reduction Characteristics (TinyGPT 4×4 Tiles)</text>
<text x="85" y="202" class="box-text">• Column tiles per row: Kc = 4 (Log2 levels = {tg_tree["avg_hops_per_transfer"]:.0f})</text>
<text x="85" y="222" class="box-text">• Partial-sum vector transfers: 4 rows × (4−1) = 12 transfers</text>
<text x="85" y="242" class="box-text">• Reduction traffic: {tg_tree["reduction_traffic_bytes"]:.0f} Bytes</text>
<text x="85" y="262" class="box-text">• Critical path latency: {tg_tree["critical_path_latency_ns"]:.1f} ns ({tg_tree["avg_hops_per_transfer"]:.0f} hops @ 1.0 ns/hop)</text>
<text x="85" y="282" class="box-text">• Interconnect energy: {tg_tree["estimated_noc_energy_nj"]:.4f} nJ</text>

<rect x="70" y="325" width="370" height="160" rx="8" fill="#f8fafc" stroke="#cbd5e1"/>
<text x="85" y="350" class="box-title">Key Architectural Properties</text>
<text x="85" y="375" class="box-text">✔ O(log2 Kc) hop latency minimizes pipeline delay</text>
<text x="85" y="395" class="box-text">✔ Localized adder nodes sum partials in-flight</text>
<text x="85" y="415" class="box-text">✔ Dedicated point-to-point tree wires eliminate contention</text>
<text x="85" y="440" class="formula">T_tree = ceil(log2(Kc)) × t_hop</text>

<!-- 2D Mesh & Ring Comparison Box -->
<rect x="500" y="85" width="410" height="420" rx="12" fill="#faf5ff" stroke="#9333ea" stroke-width="2"/>
<text x="520" y="115" class="box-title" fill="#7e22ce">2. 2D Mesh NoC &amp; Network Comparison</text>
<text x="520" y="135" class="sub">General-purpose packet-switched routing vs dedicated trees</text>

<rect x="520" y="155" width="370" height="155" rx="8" fill="white" stroke="#d8b4fe"/>
<text x="535" y="180" class="box-title" fill="#6b21a8">2D Mesh Characteristics (TinyGPT 4×4 Grid)</text>
<text x="535" y="202" class="box-text">• Average Manhattan hops: (4+4)/3 = {tg_mesh["avg_hops_per_transfer"]:.2f} hops</text>
<text x="535" y="222" class="box-text">• Critical path latency: {tg_mesh["critical_path_latency_ns"]:.1f} ns ({tg_mesh["critical_path_latency_ns"]:.0f} hops)</text>
<text x="535" y="242" class="box-text">• Total traffic: {tg_mesh["total_traffic_bytes"]:.0f} Bytes</text>
<text x="535" y="262" class="box-text">• Interconnect energy: {tg_mesh["estimated_noc_energy_nj"]:.4f} nJ</text>
<text x="535" y="282" class="sub">Higher latency and energy than dedicated tree due to router hops</text>

<rect x="520" y="325" width="370" height="160" rx="8" fill="#fff7ed" stroke="#fdba74"/>
<text x="535" y="350" class="box-title" fill="#c2410c">Network Scaling Comparison</text>
<text x="535" y="375" class="box-text">• Binary Tree: Best latency ({tg_tree["critical_path_latency_ns"]:.0f} ns) &amp; energy ({tg_tree["estimated_noc_energy_nj"]:.4f} nJ)</text>
<text x="535" y="395" class="box-text">• 2D Mesh: High flexibility, 4× latency ({tg_mesh["critical_path_latency_ns"]:.0f} ns)</text>
<text x="535" y="415" class="box-text">• Ring Bus: Serial bottleneck, O(N) latency</text>
<text x="535" y="440" class="formula">E_noc = sum(Bytes × Hops) × 0.5 pJ/(B·hop)</text>
</svg>
"""


def main() -> None:
    extract = generate_noc_interconnect_extract()
    out_dir = Path(__file__).resolve().parents[2] / "verification" / "circuit" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    extract_path = out_dir / "noc-interconnect-0025-extract.json"
    extract_path.write_text(json.dumps(extract, indent=2, sort_keys=True) + "\n", "utf-8")

    diagram_dir = Path(__file__).resolve().parent / "diagrams"
    diagram_dir.mkdir(parents=True, exist_ok=True)
    svg_path = diagram_dir / "noc-interconnect-0025.svg"
    svg_path.write_text(render_svg(extract), "utf-8")

    print(f"Wrote {extract_path}")
    print(f"Wrote {svg_path}")
    tg_tree = extract["workloads"]["tinygpt_64x64_tile16"]["topologies"]["binary_tree"]
    print(
        f"TinyGPT Binary Tree: {tg_tree['reduction_traffic_bytes']} B reduction traffic, "
        f"{tg_tree['critical_path_latency_ns']} ns latency, "
        f"{tg_tree['estimated_noc_energy_nj']:.4f} nJ energy"
    )


if __name__ == "__main__":
    main()
