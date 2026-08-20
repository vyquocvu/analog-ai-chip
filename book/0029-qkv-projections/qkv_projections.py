r"""Chapter 0029 — Q/K/V Attention Projections Mapping (Gate R7).

Simulates multi-head self-attention linear projections ($W_Q, W_K, W_V, W_O$) mapped
onto physical crossbar tile arrays with multi-head slicing and logit sensitivity evaluation:

1. **Packed QKV Projection Pipeline**:
   - $W_{QKV} \in \mathbb{R}^{3 d_{\text{model}} \times d_{\text{model}}}$ partitioned into $K_r \times K_c$ tiles of size $16\times 16$.
   - For TinyGPT ($d_{\text{model}}=64$): $192 \times 64 \to 12 \times 4 = 48$ physical tiles.
   - Computes query, key, and value vectors in parallel via shared activation broadcast.

2. **Output Projection ($W_O$)**:
   - $W_O \in \mathbb{R}^{d_{\text{model}} \times d_{\text{model}}}$ mapped onto $4 \times 4 = 16$ physical tiles.
   - Total attention projection tiles: $48 + 16 = 64$ physical tiles.

3. **Multi-Head Slicing & Attention Logit Sensitivity**:
   - Slices $Q, K, V$ into $n_{\text{heads}}$ heads of dimension $d_{\text{head}} = d_{\text{model}} / n_{\text{heads}}$.
   - Computes raw attention score matrix:
     $$S_h = \frac{Q_h K_h^T}{\sqrt{d_{\text{head}}}}$$
   - Evaluates cosine similarity, logit perturbation, and post-ADC calibration ($a^* = 0.9795135$).
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
class AttentionProjectionConfig:
    """Configuration parameters for multi-head attention projections."""

    d_model: int
    num_heads: int
    tile_rows: int = 16
    tile_cols: int = 16
    dac_bits: int = 4
    adc_bits: int = 4
    g_bits: int = 4
    vin_max_v: float = 2.34375
    vout_max_v: float = 2.5

    def __post_init__(self) -> None:
        if self.d_model <= 0 or self.num_heads <= 0:
            raise ValueError("d_model and num_heads must be positive")
        if self.d_model % self.num_heads != 0:
            raise ValueError(f"d_model {self.d_model} must be divisible by num_heads {self.num_heads}")
        if self.tile_rows <= 0 or self.tile_cols <= 0:
            raise ValueError("tile dimensions must be positive")

    @property
    def d_head(self) -> int:
        return self.d_model // self.num_heads

    @property
    def qkv_tiles(self) -> int:
        return math.ceil(3 * self.d_model / self.tile_rows) * math.ceil(self.d_model / self.tile_cols)

    @property
    def out_tiles(self) -> int:
        return math.ceil(self.d_model / self.tile_rows) * math.ceil(self.d_model / self.tile_cols)

    @property
    def total_tiles(self) -> int:
        return self.qkv_tiles + self.out_tiles


@dataclass(frozen=True)
class ProjectionMetrics:
    """Evaluation metrics for a multi-head projection."""

    rel_l2_error_pct: float
    mae: float
    max_abs_error: float
    snr_db: float
    cosine_similarity: float


@dataclass(frozen=True)
class AttentionProjectionReport:
    """Complete evaluation report for Multi-Head QKV and Output projections."""

    model_name: str
    d_model: int
    num_heads: int
    d_head: int
    total_physical_tiles: int
    q_metrics: ProjectionMetrics
    k_metrics: ProjectionMetrics
    v_metrics: ProjectionMetrics
    o_metrics: ProjectionMetrics
    logit_relative_error_pct: float
    calibration_recovery_pct: float


class AnalogQKVProjection:
    """Simulates packed multi-tile analog QKV and Out projections for Multi-Head Attention."""

    def __init__(
        self,
        w_qkv: np.ndarray,
        w_out: np.ndarray,
        config: AttentionProjectionConfig,
        nonideality_kwargs: dict[str, Any] | None = None,
        seed: int = 42,
    ) -> None:
        if w_qkv.shape != (3 * config.d_model, config.d_model):
            raise ValueError(f"w_qkv shape {w_qkv.shape} != ({3 * config.d_model}, {config.d_model})")
        if w_out.shape != (config.d_model, config.d_model):
            raise ValueError(f"w_out shape {w_out.shape} != ({config.d_model}, {config.d_model})")

        self.w_qkv = w_qkv.astype(np.float64)
        self.w_out = w_out.astype(np.float64)
        self.config = config
        self.nonideality_kwargs = nonideality_kwargs or {}
        self.seed = seed

        rng_seq = np.random.SeedSequence(seed)
        seeds_qkv, seeds_out = rng_seq.spawn(2)

        # 1. Build Packed QKV Tile Grid (kr_qkv x kc_qkv)
        self.kr_qkv = math.ceil(3 * config.d_model / config.tile_rows)
        self.kc_qkv = math.ceil(config.d_model / config.tile_cols)
        self.tiles_qkv = self._build_tile_grid(
            self.w_qkv, self.kr_qkv, self.kc_qkv, 3 * config.d_model, config.d_model, seeds_qkv
        )

        # 2. Build Output Projection Tile Grid (kr_out x kc_out)
        self.kr_out = math.ceil(config.d_model / config.tile_rows)
        self.kc_out = math.ceil(config.d_model / config.tile_cols)
        self.tiles_out = self._build_tile_grid(
            self.w_out, self.kr_out, self.kc_out, config.d_model, config.d_model, seeds_out
        )

    def _build_tile_grid(
        self,
        w: np.ndarray,
        kr: int,
        kc: int,
        m_out: int,
        m_in: int,
        seed_seq: np.random.SeedSequence,
    ) -> list[list[CrossbarTile]]:
        tiles: list[list[CrossbarTile]] = []
        child_seeds = seed_seq.spawn(kr * kc)
        idx = 0
        for r in range(kr):
            row_tiles: list[CrossbarTile] = []
            for c in range(kc):
                r_start, r_end = r * self.config.tile_rows, min(m_out, (r + 1) * self.config.tile_rows)
                c_start, c_end = c * self.config.tile_cols, min(m_in, (c + 1) * self.config.tile_cols)

                block_w = np.zeros((self.config.tile_rows, self.config.tile_cols), dtype=np.float64)
                block_w[: (r_end - r_start), : (c_end - c_start)] = w[r_start:r_end, c_start:c_end]

                child_rng = np.random.default_rng(child_seeds[idx])
                tile = CrossbarTile(
                    rows=self.config.tile_rows,
                    cols=self.config.tile_cols,
                    gmin=1e-5,
                    gmax=1e-4,
                    g_bits=self.config.g_bits,
                    dac_bits=self.config.dac_bits,
                    adc_bits=self.config.adc_bits,
                    vin_max=self.config.vin_max_v,
                    vout_max=self.config.vout_max_v,
                    rng=child_rng,
                    **self.nonideality_kwargs,
                )
                tile.program(block_w)
                row_tiles.append(tile)
                idx += 1
            tiles.append(row_tiles)
        return tiles

    def _forward_grid(
        self,
        x: np.ndarray,
        tiles: list[list[CrossbarTile]],
        kr: int,
        kc: int,
        m_out: int,
        m_in: int,
        apply_calibration: bool,
    ) -> np.ndarray:
        out_blocks: list[np.ndarray] = []
        for r in range(kr):
            row_sum = np.zeros(self.config.tile_rows, dtype=np.float64)
            for c in range(kc):
                c_start, c_end = c * self.config.tile_cols, min(m_in, (c + 1) * self.config.tile_cols)
                block_x = np.zeros(self.config.tile_cols, dtype=np.float64)
                block_x[: (c_end - c_start)] = x[c_start:c_end]

                tile_out = tiles[r][c].forward(block_x)
                row_sum += tile_out

            if apply_calibration:
                row_sum *= CALIBRATION_GAIN

            out_blocks.append(row_sum)

        return np.concatenate(out_blocks)[:m_out]

    def project_qkv(
        self, x: np.ndarray, apply_calibration: bool = True
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Project input x into Query, Key, and Value vectors."""
        if x.shape != (self.config.d_model,):
            raise ValueError(f"input shape {x.shape} != d_model={self.config.d_model}")

        qkv = self._forward_grid(
            x, self.tiles_qkv, self.kr_qkv, self.kc_qkv, 3 * self.config.d_model, self.config.d_model, apply_calibration
        )
        d = self.config.d_model
        q = qkv[:d]
        k = qkv[d : 2 * d]
        v = qkv[2 * d :]
        return q, k, v

    def project_out(self, context: np.ndarray, apply_calibration: bool = True) -> np.ndarray:
        """Project attention context vector back to d_model."""
        if context.shape != (self.config.d_model,):
            raise ValueError(f"context shape {context.shape} != d_model={self.config.d_model}")
        return self._forward_grid(
            context, self.tiles_out, self.kr_out, self.kc_out, self.config.d_model, self.config.d_model, apply_calibration
        )


def compute_projection_metrics(ref: np.ndarray, pred: np.ndarray) -> ProjectionMetrics:
    diff = pred - ref
    ref_norm = float(np.linalg.norm(ref))
    diff_norm = float(np.linalg.norm(diff))

    rel_l2 = (diff_norm / ref_norm * 100.0) if ref_norm > 1e-12 else 0.0
    mae = float(np.mean(np.abs(diff)))
    max_err = float(np.max(np.abs(diff)))
    snr_db = (20.0 * math.log10(ref_norm / diff_norm)) if diff_norm > 1e-12 else 100.0

    dot = float(np.dot(ref, pred))
    pred_norm = float(np.linalg.norm(pred))
    cos_sim = (dot / (ref_norm * pred_norm)) if (ref_norm > 1e-12 and pred_norm > 1e-12) else 1.0

    return ProjectionMetrics(
        rel_l2_error_pct=rel_l2,
        mae=mae,
        max_abs_error=max_err,
        snr_db=snr_db,
        cosine_similarity=cos_sim,
    )


def evaluate_attention_projections(
    model_name: str,
    w_qkv: np.ndarray,
    w_out: np.ndarray,
    config: AttentionProjectionConfig,
    x_test: np.ndarray,
    crossbar_profile_path: Path | str,
    seed: int = 42,
) -> AttentionProjectionReport:
    """Evaluate packed QKV and Out projections against float32 reference."""
    # Floating-Point Reference
    ref_qkv = w_qkv @ x_test
    d = config.d_model
    ref_q, ref_k, ref_v = ref_qkv[:d], ref_qkv[d : 2 * d], ref_qkv[2 * d :]
    ref_o = w_out @ ref_v

    cb_profile = load_device_profile(crossbar_profile_path, physical_claim=False)
    nonideal_cfg = nonideality_config_from_profile(cb_profile, drift_time_s=1.0)

    # 1. Raw Non-Ideal
    proj_raw = AnalogQKVProjection(w_qkv, w_out, config, nonideality_kwargs=nonideal_cfg, seed=seed)
    q_raw, _k_raw, _v_raw = proj_raw.project_qkv(x_test, apply_calibration=False)

    # 2. Calibrated Non-Ideal
    proj_cal = AnalogQKVProjection(w_qkv, w_out, config, nonideality_kwargs=nonideal_cfg, seed=seed)
    q_cal, k_cal, v_cal = proj_cal.project_qkv(x_test, apply_calibration=True)
    o_cal = proj_cal.project_out(v_cal, apply_calibration=True)

    metrics_q = compute_projection_metrics(ref_q, q_cal)
    metrics_k = compute_projection_metrics(ref_k, k_cal)
    metrics_v = compute_projection_metrics(ref_v, v_cal)
    metrics_o = compute_projection_metrics(ref_o, o_cal)

    # Logit sensitivity across heads: S_h = (Q_h K_h^T) / sqrt(d_head)
    scale = 1.0 / math.sqrt(config.d_head)
    ref_logits: list[float] = []
    cal_logits: list[float] = []
    for h in range(config.num_heads):
        h_start, h_end = h * config.d_head, (h + 1) * config.d_head
        ref_s = float(np.dot(ref_q[h_start:h_end], ref_k[h_start:h_end])) * scale
        cal_s = float(np.dot(q_cal[h_start:h_end], k_cal[h_start:h_end])) * scale
        ref_logits.append(ref_s)
        cal_logits.append(cal_s)

    ref_arr, cal_arr = np.array(ref_logits), np.array(cal_logits)
    logit_err = float(np.linalg.norm(cal_arr - ref_arr) / np.linalg.norm(ref_arr) * 100.0) if np.linalg.norm(ref_arr) > 1e-12 else 0.0

    raw_q_err = compute_projection_metrics(ref_q, q_raw).rel_l2_error_pct
    cal_q_err = metrics_q.rel_l2_error_pct
    impr = max(0.0, (raw_q_err - cal_q_err) / raw_q_err * 100.0) if raw_q_err > 1e-12 else 0.0

    return AttentionProjectionReport(
        model_name=model_name,
        d_model=config.d_model,
        num_heads=config.num_heads,
        d_head=config.d_head,
        total_physical_tiles=config.total_tiles,
        q_metrics=metrics_q,
        k_metrics=metrics_k,
        v_metrics=metrics_v,
        o_metrics=metrics_o,
        logit_relative_error_pct=logit_err,
        calibration_recovery_pct=impr,
    )


def generate_qkv_extract() -> dict[str, Any]:
    """Generate deterministic extract dictionary for committed artifact."""
    rng = np.random.default_rng(2026)
    cb_path = _REPO / "device_profiles" / "crossbar-v1.json"

    # Workload 1: TinyGPT Attention (d_model=64, 4 heads of dim 16 -> 48 QKV + 16 Out = 64 tiles)
    w_qkv_tg = rng.normal(0.0, 0.15, (192, 64))
    w_out_tg = rng.normal(0.0, 0.15, (64, 64))
    x_tg = rng.uniform(-1.0, 1.0, 64)
    cfg_tg = AttentionProjectionConfig(d_model=64, num_heads=4)
    rep_tg = evaluate_attention_projections("TinyGPT_Attention", w_qkv_tg, w_out_tg, cfg_tg, x_tg, cb_path, seed=42)

    # Workload 2: 8-Head Attention Variant (d_model=64, 8 heads of dim 8)
    cfg_8h = AttentionProjectionConfig(d_model=64, num_heads=8)
    rep_8h = evaluate_attention_projections("TinyGPT_8Heads", w_qkv_tg, w_out_tg, cfg_8h, x_tg, cb_path, seed=42)

    return {
        "schema_version": "0.1.0",
        "chapter": "0029-qkv-projections",
        "title": "Q/K/V Attention Projections Mapping",
        "gate": "R7 — Transformer and LLM validation",
        "provenance": {
            "crossbar_profile": "device_profiles/crossbar-v1.json",
            "calibration_profile": "device_profiles/tile-calibration-v1.json",
            "claim_level": "SYSTEM_SIMULATED",
        },
        "formulas": {
            "fused_qkv": "[q; k; v] = a_star * sum(Tile_qkv(x))",
            "out_projection": "o = a_star * sum(Tile_out(context))",
            "multi_head_slice": "Q_h = q[h*d_head : (h+1)*d_head]",
            "attention_score": "S_h = (Q_h * K_h^T) / sqrt(d_head)",
        },
        "evaluations": {
            "tinygpt_attention_4heads": asdict(rep_tg),
            "tinygpt_attention_8heads": asdict(rep_8h),
        },
    }


def render_svg(extract: dict[str, Any]) -> str:
    """Render an SVG diagram illustrating the multi-head attention projection mapping."""
    tg = extract["evaluations"]["tinygpt_attention_4heads"]
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
<text x="480" y="35" text-anchor="middle" class="title">Chapter 0029 — Q/K/V Attention Projections Mapping</text>
<text x="480" y="55" text-anchor="middle" class="sub">Fused packed QKV and output projections under crossbar-v1 non-idealities</text>

<!-- Architecture Box -->
<rect x="50" y="85" width="410" height="420" rx="12" fill="#eff6ff" stroke="#2563eb" stroke-width="2"/>
<text x="70" y="115" class="box-title" fill="#1d4ed8">1. Fused QKV &amp; Multi-Head Slicing</text>
<text x="70" y="135" class="sub">TinyGPT Attention: d_model=64, 4 heads (d_head=16)</text>

<rect x="70" y="155" width="370" height="95" rx="8" fill="white" stroke="#93c5fd"/>
<text x="85" y="180" class="box-title" fill="#1e40af">Fused W_QKV Projection (192×64)</text>
<text x="85" y="202" class="box-text">• 48 physical 16×16 tiles in 12×4 grid</text>
<text x="85" y="222" class="box-text">• Shared activation broadcast to Query, Key, Value rows</text>
<text x="85" y="240" class="sub">• Post-ADC calibration gain a* = 0.9795135</text>

<rect x="70" y="265" width="370" height="95" rx="8" fill="#fefce8" stroke="#ca8a04"/>
<text x="85" y="290" class="box-title" fill="#a16207">Output Projection W_O (64×64)</text>
<text x="85" y="312" class="box-text">• 16 physical 16×16 tiles in 4×4 grid</text>
<text x="85" y="332" class="box-text">• Maps concatenated context back to hidden state</text>
<text x="85" y="350" class="sub">• Total static attention tiles: 48 + 16 = 64 tiles</text>

<rect x="70" y="375" width="370" height="110" rx="8" fill="#f8fafc" stroke="#cbd5e1"/>
<text x="85" y="400" class="box-title">Multi-Head Slicing Equation</text>
<text x="85" y="425" class="formula">Q_h = q[h·16 : (h+1)·16], K_h = k[h·16 : (h+1)·16]</text>
<text x="85" y="450" class="formula">S_h = (Q_h · K_h^T) / sqrt(16)</text>
<text x="85" y="472" class="sub">Logit Error Sensitivity: {tg["logit_relative_error_pct"]:.2f}%</text>

<!-- Projection Accuracy Box -->
<rect x="500" y="85" width="410" height="420" rx="12" fill="#faf5ff" stroke="#9333ea" stroke-width="2"/>
<text x="520" y="115" class="box-title" fill="#7e22ce">2. Projection Accuracy &amp; Cosine Similarity</text>
<text x="520" y="135" class="sub">Per-head metrics under full crossbar-v1 non-idealities</text>

<!-- Query & Key -->
<rect x="520" y="155" width="370" height="150" rx="8" fill="white" stroke="#d8b4fe"/>
<text x="535" y="180" class="box-title" fill="#6b21a8">Query &amp; Key Projection Accuracy</text>
<text x="535" y="202" class="box-text">• Query L2 Error: {tg["q_metrics"]["rel_l2_error_pct"]:.2f}% (SNR: {tg["q_metrics"]["snr_db"]:.1f} dB)</text>
<text x="535" y="222" class="box-text">• Query Cosine Similarity: {tg["q_metrics"]["cosine_similarity"]:.4f}</text>
<text x="535" y="242" class="box-text">• Key L2 Error: {tg["k_metrics"]["rel_l2_error_pct"]:.2f}% (SNR: {tg["k_metrics"]["snr_db"]:.1f} dB)</text>
<text x="535" y="262" class="box-text">• Key Cosine Similarity: {tg["k_metrics"]["cosine_similarity"]:.4f}</text>
<text x="535" y="282" class="sub">Calibration reduces residual projection error by {tg["calibration_recovery_pct"]:.1f}%</text>

<!-- Value & Out -->
<rect x="520" y="320" width="370" height="165" rx="8" fill="#f0fdf4" stroke="#86efac"/>
<text x="535" y="345" class="box-title" fill="#166534">Value &amp; Output Projection Accuracy</text>
<text x="535" y="370" class="box-text">• Value L2 Error: {tg["v_metrics"]["rel_l2_error_pct"]:.2f}% (SNR: {tg["v_metrics"]["snr_db"]:.1f} dB)</text>
<text x="535" y="390" class="box-text">• Value Cosine Similarity: {tg["v_metrics"]["cosine_similarity"]:.4f}</text>
<text x="535" y="410" class="box-title" fill="#15803d">• Output L2 Error: {tg["o_metrics"]["rel_l2_error_pct"]:.2f}% (SNR: {tg["o_metrics"]["snr_db"]:.1f} dB)</text>
<text x="535" y="430" class="box-text">• Output Cosine Similarity: {tg["o_metrics"]["cosine_similarity"]:.4f}</text>
<text x="535" y="455" class="formula">cos_sim = (y_pred · y_ref) / (||y_pred|| · ||y_ref||)</text>
</svg>
"""


def main() -> None:
    extract = generate_qkv_extract()
    out_dir = Path(__file__).resolve().parents[2] / "verification" / "circuit" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    extract_path = out_dir / "qkv-projections-0029-extract.json"
    extract_path.write_text(json.dumps(extract, indent=2, sort_keys=True) + "\n", "utf-8")

    diagram_dir = Path(__file__).resolve().parent / "diagrams"
    diagram_dir.mkdir(parents=True, exist_ok=True)
    svg_path = diagram_dir / "qkv-projections-0029.svg"
    svg_path.write_text(render_svg(extract), "utf-8")

    print(f"Wrote {extract_path}")
    print(f"Wrote {svg_path}")
    tg = extract["evaluations"]["tinygpt_attention_4heads"]
    print(
        f"TinyGPT Attention: Query L2={tg['q_metrics']['rel_l2_error_pct']:.2f}% (cos={tg['q_metrics']['cosine_similarity']:.4f}), "
        f"Key L2={tg['k_metrics']['rel_l2_error_pct']:.2f}%, Logit Error={tg['logit_relative_error_pct']:.2f}%"
    )


if __name__ == "__main__":
    main()
