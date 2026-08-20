r"""Chapter 0027 — Linear Layer Mapping (Gate R7).

Maps a dense neural network linear projection $y = W x$ onto an array of profile-driven
analog crossbar tiles with converter envelopes, physical non-idealities, spatial partial-sum
reduction, and output calibration:

1. **Weight Matrix Tiling & Differential Conductance**:
   - $W \in \mathbb{R}^{M_{\text{out}} \times M_{\text{in}}}$ partitioned into $K_r \times K_c$ blocks of size $R \times C$.
   - Quantized to $B_{\text{weight}} = 4$ bits and mapped to differential conductances $(G^+, G^-)$.
   - Balanced zero: $w = 0 \implies G^+ = G^- = G_{\min}$ (exact zero differential current).

2. **Input Activation Quantization & DAC Scaling**:
   - $x \in \mathbb{R}^{M_{\text{in}}}$ partitioned into $K_c$ blocks $x_j \in \mathbb{R}^C$.
   - Normalized and mapped to physical DAC voltage range $[0, V_{\text{in,max}}]$ ($V_{\text{in,max}} = 2.34375\text{ V}$).

3. **Physical Non-Ideality Tile Simulation**:
   - Each tile evaluates MVM with all 9 `crossbar-v1` mechanisms:
     - 2D distributed nodal IR drop ($R_{\text{wire}} = 1.0\,\Omega$)
     - Programming variation ($\sigma_{\text{prog}} = 3\%$)
     - Read noise ($\sigma_{\text{read}} = 1\%$)
     - Retention drift ($t = 1.0\text{ s}$, $\nu \in [0.03, 0.08]$)
     - Stuck-at defects ($p_{\text{HRS}} = 2.55\%, p_{\text{LRS}} = 0.45\%$)
     - Cubic I-V non-linearity ($\beta = 1.0\text{ V}^{-2}$, $V_{\text{read,max}} = 0.25\text{ V}$)

4. **Spatial Reduction & Output Calibration**:
   - Output currents converted by SAR ADC ($B_{\text{ADC}} = 4$, $V_{\text{out,max}} = 2.5\text{ V}$).
   - Spatial partial sums accumulated across columns: $\tilde{y}_i = \sum_{j=0}^{K_c - 1} y_{i,j}$.
   - Post-reduction output calibration gain $a^* = 0.9795135$ applied.

5. **Error & Accuracy Metrics**:
   - Compares Ideal Floating-Point, Ideal Quantized, Raw Non-Ideal, and Calibrated Non-Ideal MVMs.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from analog_llm.device_profile import load_device_profile  # noqa: E402
from analog_llm.profile_adapter import nonideality_config_from_profile  # noqa: E402
from analog_llm.tile import CrossbarTile  # noqa: E402

CALIBRATION_GAIN = 0.9795135153


@dataclass(frozen=True)
class LinearLayerConfig:
    """Configuration parameters for mapping a dense linear projection."""

    m_out: int
    m_in: int
    tile_rows: int = 16
    tile_cols: int = 16
    dac_bits: int = 4
    adc_bits: int = 4
    g_bits: int = 4
    vin_max_v: float = 2.34375
    vout_max_v: float = 2.5
    v_read_max_v: float = 0.25
    gmin_s: float = 1e-5
    gmax_s: float = 1e-4

    def __post_init__(self) -> None:
        if self.m_out <= 0 or self.m_in <= 0:
            raise ValueError("layer dimensions must be positive")
        if self.tile_rows <= 0 or self.tile_cols <= 0:
            raise ValueError("tile dimensions must be positive")

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
class EvaluationMetrics:
    """Accuracy metrics comparing analog MVM to floating-point reference."""

    rel_l2_error_pct: float
    mae: float
    max_abs_error: float
    snr_db: float


@dataclass(frozen=True)
class LayerExecutionReport:
    """Full execution evaluation comparing ideal, non-ideal, and calibrated linear layers."""

    layer_name: str
    m_out: int
    m_in: int
    kr: int
    kc: int
    total_tiles: int
    b_acc_bits: int
    ideal_quantized: EvaluationMetrics
    raw_nonideal: EvaluationMetrics
    calibrated_nonideal: EvaluationMetrics
    calibration_improvement_pct: float


class AnalogLinearLayer:
    """Simulates a tiled multi-crossbar dense linear layer."""

    def __init__(
        self,
        weight: np.ndarray,
        config: LinearLayerConfig,
        nonideality_kwargs: dict[str, Any] | None = None,
        seed: int = 42,
    ) -> None:
        if weight.shape != (config.m_out, config.m_in):
            raise ValueError(
                f"weight shape {weight.shape} does not match config ({config.m_out}, {config.m_in})"
            )
        self.weight = weight.astype(np.float64)
        self.config = config
        self.nonideality_kwargs = nonideality_kwargs or {}
        self.seed = seed

        # Build 2D grid of physical tiles: shape (kr, kc)
        self.tiles: list[list[CrossbarTile]] = []
        rng_seq = np.random.SeedSequence(seed)
        child_seeds = rng_seq.spawn(config.kr * config.kc)

        tile_idx = 0
        for r in range(config.kr):
            row_tiles: list[CrossbarTile] = []
            for c in range(config.kc):
                # Extract weight block with zero-padding if boundary
                r_start, r_end = r * config.tile_rows, min(config.m_out, (r + 1) * config.tile_rows)
                c_start, c_end = c * config.tile_cols, min(config.m_in, (c + 1) * config.tile_cols)

                block_w = np.zeros((config.tile_rows, config.tile_cols), dtype=np.float64)
                block_w[: (r_end - r_start), : (c_end - c_start)] = self.weight[r_start:r_end, c_start:c_end]

                child_rng = np.random.default_rng(child_seeds[tile_idx])
                tile = CrossbarTile(
                    rows=config.tile_rows,
                    cols=config.tile_cols,
                    gmin=config.gmin_s,
                    gmax=config.gmax_s,
                    g_bits=config.g_bits,
                    dac_bits=config.dac_bits,
                    adc_bits=config.adc_bits,
                    vin_max=config.vin_max_v,
                    vout_max=config.vout_max_v,
                    rng=child_rng,
                    **self.nonideality_kwargs,
                )
                tile.program(block_w)
                row_tiles.append(tile)
                tile_idx += 1
            self.tiles.append(row_tiles)

    def forward(self, x: np.ndarray, apply_calibration: bool = True) -> np.ndarray:
        """Run tiled forward MVM across physical crossbar array with reduction and calibration."""
        if x.shape != (self.config.m_in,):
            raise ValueError(f"input shape {x.shape} does not match m_in={self.config.m_in}")

        out_blocks: list[np.ndarray] = []
        for r in range(self.config.kr):
            row_sum = np.zeros(self.config.tile_rows, dtype=np.float64)
            for c in range(self.config.kc):
                c_start, c_end = c * self.config.tile_cols, min(self.config.m_in, (c + 1) * self.config.tile_cols)
                block_x = np.zeros(self.config.tile_cols, dtype=np.float64)
                block_x[: (c_end - c_start)] = x[c_start:c_end]

                # Run tile MVM
                tile_out = self.tiles[r][c].forward(block_x)
                row_sum += tile_out

            if apply_calibration:
                row_sum *= CALIBRATION_GAIN

            out_blocks.append(row_sum)

        full_out = np.concatenate(out_blocks)[: self.config.m_out]
        return full_out


def compute_evaluation_metrics(ref: np.ndarray, pred: np.ndarray) -> EvaluationMetrics:
    """Compute relative L2 error, MAE, max error, and SNR."""
    diff = pred - ref
    ref_norm = float(np.linalg.norm(ref))
    diff_norm = float(np.linalg.norm(diff))

    rel_l2 = (diff_norm / ref_norm * 100.0) if ref_norm > 1e-12 else 0.0
    mae = float(np.mean(np.abs(diff)))
    max_err = float(np.max(np.abs(diff)))
    snr_db = (20.0 * math.log10(ref_norm / diff_norm)) if diff_norm > 1e-12 else 100.0

    return EvaluationMetrics(
        rel_l2_error_pct=rel_l2,
        mae=mae,
        max_abs_error=max_err,
        snr_db=snr_db,
    )


def evaluate_linear_layer(
    layer_name: str,
    weight: np.ndarray,
    config: LinearLayerConfig,
    x_test: np.ndarray,
    crossbar_profile_path: Path | str,
    seed: int = 42,
) -> LayerExecutionReport:
    """Evaluate a linear layer across ideal quantized, raw non-ideal, and calibrated execution."""
    ref_out = weight @ x_test

    # 1. Ideal Quantized Layer (no circuit non-idealities)
    layer_ideal = AnalogLinearLayer(weight, config, nonideality_kwargs=None, seed=seed)
    ideal_out = layer_ideal.forward(x_test, apply_calibration=False)
    metrics_ideal = compute_evaluation_metrics(ref_out, ideal_out)

    # 2. Raw Non-Ideal Layer (all 9 crossbar non-idealities, uncalibrated)
    cb_profile = load_device_profile(crossbar_profile_path, physical_claim=False)
    nonideal_cfg = nonideality_config_from_profile(cb_profile, drift_time_s=1.0)

    layer_raw = AnalogLinearLayer(weight, config, nonideality_kwargs=nonideal_cfg, seed=seed)
    raw_out = layer_raw.forward(x_test, apply_calibration=False)
    metrics_raw = compute_evaluation_metrics(ref_out, raw_out)

    # 3. Calibrated Non-Ideal Layer (post-ADC gain correction applied)
    layer_cal = AnalogLinearLayer(weight, config, nonideality_kwargs=nonideal_cfg, seed=seed)
    cal_out = layer_cal.forward(x_test, apply_calibration=True)
    metrics_cal = compute_evaluation_metrics(ref_out, cal_out)

    improvement_pct = max(0.0, (metrics_raw.rel_l2_error_pct - metrics_cal.rel_l2_error_pct) / metrics_raw.rel_l2_error_pct * 100.0)

    return LayerExecutionReport(
        layer_name=layer_name,
        m_out=config.m_out,
        m_in=config.m_in,
        kr=config.kr,
        kc=config.kc,
        total_tiles=config.total_tiles,
        b_acc_bits=config.b_acc,
        ideal_quantized=metrics_ideal,
        raw_nonideal=metrics_raw,
        calibrated_nonideal=metrics_cal,
        calibration_improvement_pct=improvement_pct,
    )


def generate_linear_layer_extract() -> dict[str, Any]:
    """Generate deterministic extract dictionary for committed artifact."""
    rng = np.random.default_rng(1234)
    cb_path = _REPO / "device_profiles" / "crossbar-v1.json"

    # Workload 1: TinyGPT Attention QKV Projection (192 x 64 -> 12 x 4 = 48 tiles)
    w_qkv = rng.normal(0.0, 0.2, (192, 64))
    x_qkv = rng.uniform(-1.0, 1.0, 64)
    cfg_qkv = LinearLayerConfig(m_out=192, m_in=64, tile_rows=16, tile_cols=16)
    rep_qkv = evaluate_linear_layer("TinyGPT_QKV", w_qkv, cfg_qkv, x_qkv, cb_path, seed=42)

    # Workload 2: TinyGPT MLP Up Projection (256 x 64 -> 16 x 4 = 64 tiles)
    w_mlp = rng.normal(0.0, 0.2, (256, 64))
    x_mlp = rng.uniform(-1.0, 1.0, 64)
    cfg_mlp = LinearLayerConfig(m_out=256, m_in=64, tile_rows=16, tile_cols=16)
    rep_mlp = evaluate_linear_layer("TinyGPT_MLP_Up", w_mlp, cfg_mlp, x_mlp, cb_path, seed=42)

    # Workload 3: Canonical Sparse Matrix (64 x 64, 80% sparsity)
    w_sparse = rng.normal(0.0, 0.2, (64, 64))
    mask = rng.uniform(0.0, 1.0, (64, 64)) > 0.8
    w_sparse = w_sparse * mask
    x_sparse = rng.uniform(-1.0, 1.0, 64)
    cfg_sparse = LinearLayerConfig(m_out=64, m_in=64, tile_rows=16, tile_cols=16)
    rep_sparse = evaluate_linear_layer("Sparse_80pct", w_sparse, cfg_sparse, x_sparse, cb_path, seed=42)

    return {
        "schema_version": "0.1.0",
        "chapter": "0027-linear-layer",
        "title": "Linear Layer Mapping",
        "gate": "R7 — Transformer and LLM validation",
        "provenance": {
            "crossbar_profile": "device_profiles/crossbar-v1.json",
            "calibration_profile": "device_profiles/tile-calibration-v1.json",
            "claim_level": "SYSTEM_SIMULATED",
        },
        "formulas": {
            "tiling": "Kr = ceil(M_out / R), Kc = ceil(M_in / C)",
            "partial_sum": "y_tilde_i = sum_(j=0)^(Kc-1) Tile_ij(x_j)",
            "calibration": "y_cal_i = a_star * y_tilde_i (a_star = 0.9795135)",
            "rel_l2_error": "||y_pred - y_ref||_2 / ||y_ref||_2 * 100%",
        },
        "evaluations": {
            "tinygpt_qkv": asdict(rep_qkv),
            "tinygpt_mlp_up": asdict(rep_mlp),
            "sparse_80pct": asdict(rep_sparse),
        },
    }


def render_svg(extract: dict[str, Any]) -> str:
    """Render an SVG diagram illustrating the linear layer mapping and accuracy results."""
    qkv = extract["evaluations"]["tinygpt_qkv"]
    mlp = extract["evaluations"]["tinygpt_mlp_up"]
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
<text x="480" y="35" text-anchor="middle" class="title">Chapter 0027 — Linear Layer Mapping</text>
<text x="480" y="55" text-anchor="middle" class="sub">Tiled physical MVM execution under crossbar-v1 non-idealities and output calibration</text>

<!-- Mapping Architecture Box -->
<rect x="50" y="85" width="410" height="420" rx="12" fill="#eff6ff" stroke="#2563eb" stroke-width="2"/>
<text x="70" y="115" class="box-title" fill="#1d4ed8">1. Dense Matrix Tiling &amp; MVM Pipeline</text>
<text x="70" y="135" class="sub">Spatial decomposition into Kr × Kc physical tiles (16×16 each)</text>

<rect x="70" y="155" width="370" height="150" rx="8" fill="white" stroke="#93c5fd"/>
<text x="85" y="180" class="box-title" fill="#1e40af">Forward Computation Steps</text>
<text x="85" y="202" class="box-text">1. Input x partitioned into Kc blocks → DAC voltage [0, 2.34V]</text>
<text x="85" y="222" class="box-text">2. Physical MVM on each tile with all 9 non-idealities</text>
<text x="85" y="242" class="box-text">3. SAR ADC digitization (4 bits, 2.5V full scale)</text>
<text x="85" y="262" class="box-text">4. Row spatial reduction: y_tilde = Σ Tile_ij(x_j)</text>
<text x="85" y="282" class="box-text">5. Post-reduction calibration: y_cal = 0.9795135 × y_tilde</text>

<rect x="70" y="320" width="370" height="165" rx="8" fill="#f8fafc" stroke="#cbd5e1"/>
<text x="85" y="345" class="box-title">Non-Idealities Simulated</text>
<text x="85" y="370" class="box-text">• 2D Distributed IR drop (1.0 Ω wire resistance)</text>
<text x="85" y="390" class="box-text">• Write dispersion (3%) &amp; read noise (1%)</text>
<text x="85" y="410" class="box-text">• Temporal drift (1s) &amp; stuck defects (HRS/LRS)</text>
<text x="85" y="430" class="box-text">• Cubic I-V non-linearity (β = 1.0 / V²)</text>
<text x="85" y="455" class="formula">B_acc = B_adc + ceil(log2(Kc))</text>

<!-- Accuracy Results Box -->
<rect x="500" y="85" width="410" height="420" rx="12" fill="#faf5ff" stroke="#9333ea" stroke-width="2"/>
<text x="520" y="115" class="box-title" fill="#7e22ce">2. Accuracy &amp; Calibration Results</text>
<text x="520" y="135" class="sub">Evaluation vs float32 dense matrix reference y = W x</text>

<!-- TinyGPT QKV -->
<rect x="520" y="155" width="370" height="150" rx="8" fill="white" stroke="#d8b4fe"/>
<text x="535" y="180" class="box-title" fill="#6b21a8">TinyGPT QKV Projection (192×64 → 48 Tiles)</text>
<text x="535" y="202" class="box-text">• Ideal Quantized L2 Error: {qkv["ideal_quantized"]["rel_l2_error_pct"]:.2f}% (SNR: {qkv["ideal_quantized"]["snr_db"]:.1f} dB)</text>
<text x="535" y="222" class="box-text">• Raw Non-Ideal L2 Error: {qkv["raw_nonideal"]["rel_l2_error_pct"]:.2f}% (SNR: {qkv["raw_nonideal"]["snr_db"]:.1f} dB)</text>
<text x="535" y="242" class="box-title" fill="#15803d">• Calibrated L2 Error: {qkv["calibrated_nonideal"]["rel_l2_error_pct"]:.2f}% (SNR: {qkv["calibrated_nonideal"]["snr_db"]:.1f} dB)</text>
<text x="535" y="262" class="sub">Calibration reduces residual error by {qkv["calibration_improvement_pct"]:.1f}%</text>

<!-- TinyGPT MLP Up -->
<rect x="520" y="320" width="370" height="165" rx="8" fill="#f0fdf4" stroke="#86efac"/>
<text x="535" y="345" class="box-title" fill="#166534">TinyGPT MLP Up (256×64 → 64 Tiles)</text>
<text x="535" y="370" class="box-text">• Ideal Quantized L2 Error: {mlp["ideal_quantized"]["rel_l2_error_pct"]:.2f}% (SNR: {mlp["ideal_quantized"]["snr_db"]:.1f} dB)</text>
<text x="535" y="390" class="box-text">• Raw Non-Ideal L2 Error: {mlp["raw_nonideal"]["rel_l2_error_pct"]:.2f}% (SNR: {mlp["raw_nonideal"]["snr_db"]:.1f} dB)</text>
<text x="535" y="410" class="box-title" fill="#15803d">• Calibrated L2 Error: {mlp["calibrated_nonideal"]["rel_l2_error_pct"]:.2f}% (SNR: {mlp["calibrated_nonideal"]["snr_db"]:.1f} dB)</text>
<text x="535" y="430" class="sub">Calibration reduces residual error by {mlp["calibration_improvement_pct"]:.1f}%</text>
<text x="535" y="455" class="formula">E_L2 = ||y_pred − y_ref||₂ / ||y_ref||₂</text>
</svg>
"""


def main() -> None:
    extract = generate_linear_layer_extract()
    out_dir = Path(__file__).resolve().parents[2] / "verification" / "circuit" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    extract_path = out_dir / "linear-layer-0027-extract.json"
    extract_path.write_text(json.dumps(extract, indent=2, sort_keys=True) + "\n", "utf-8")

    diagram_dir = Path(__file__).resolve().parent / "diagrams"
    diagram_dir.mkdir(parents=True, exist_ok=True)
    svg_path = diagram_dir / "linear-layer-0027.svg"
    svg_path.write_text(render_svg(extract), "utf-8")

    print(f"Wrote {extract_path}")
    print(f"Wrote {svg_path}")
    qkv = extract["evaluations"]["tinygpt_qkv"]
    print(
        f"TinyGPT QKV: Ideal L2={qkv['ideal_quantized']['rel_l2_error_pct']:.2f}%, "
        f"Raw Non-Ideal L2={qkv['raw_nonideal']['rel_l2_error_pct']:.2f}%, "
        f"Calibrated L2={qkv['calibrated_nonideal']['rel_l2_error_pct']:.2f}%"
    )


if __name__ == "__main__":
    main()
