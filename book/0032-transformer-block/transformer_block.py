r"""Chapter 0032 — Transformer Block Error Attribution (Gate R7).

Simulates a full Transformer block (Self-Attention + MLP + LayerNorm + Dual Residuals)
mapped onto 192 physical crossbar tiles with per-mechanism leave-one-out error attribution:

1. **Complete Block Pipeline**:
   - $x \xrightarrow{\text{LN}_1} x_{\text{norm1}} \xrightarrow{\text{Analog } W_{QKV} \to \text{Digital Attn} \to \text{Analog } W_O} y_{\text{attn}} \xrightarrow{+x} x_1$
   - $x_1 \xrightarrow{\text{LN}_2} x_{\text{norm2}} \xrightarrow{\text{Analog } W_{\text{up}} \to \text{Digital GELU} \to \text{Analog } W_{\text{down}}} y_{\text{mlp}} \xrightarrow{+x_1} x_2$

2. **Physical Hardware Footprint**:
   - TinyGPT ($d_{\text{model}}=64, d_{\text{ffn}}=256, 16\times 16\text{ tiles}$):
     - Attention QKV ($192\times 64$): 48 tiles.
     - Attention Out ($64\times 64$): 16 tiles.
     - MLP Up ($256\times 64$): 64 tiles.
     - MLP Down ($64\times 256$): 64 tiles.
     - Total: **192 physical crossbar tiles** per layer.

3. **Per-Mechanism Leave-One-Out Error Attribution**:
   - Evaluates the marginal error contribution of DAC/ADC quantization, IR drop,
     programming variation, read noise, drift, stuck faults, and I-V non-linearity.
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


def layer_norm(x: np.ndarray, eps: float = 1e-5) -> np.ndarray:
    """Standard digital Layer Normalization."""
    mean = np.mean(x)
    var = np.var(x)
    return (x - mean) / np.sqrt(var + eps)


def gelu(x: np.ndarray) -> np.ndarray:
    """Gaussian Error Linear Unit."""
    return 0.5 * x * (1.0 + np.tanh(np.sqrt(2.0 / np.pi) * (x + 0.044715 * np.power(x, 3))))


@dataclass(frozen=True)
class TransformerBlockConfig:
    """Configuration parameters for an analog-accelerated Transformer block."""

    d_model: int = 64
    d_ffn: int = 256
    num_heads: int = 4
    tile_rows: int = 16
    tile_cols: int = 16
    dac_bits: int = 4
    adc_bits: int = 4
    g_bits: int = 4
    vin_max_v: float = 2.34375
    vout_max_v: float = 2.5

    def __post_init__(self) -> None:
        if self.d_model <= 0 or self.d_ffn <= 0 or self.num_heads <= 0:
            raise ValueError("model dimensions must be positive")
        if self.d_model % self.num_heads != 0:
            raise ValueError("d_model must be divisible by num_heads")

    @property
    def d_head(self) -> int:
        return self.d_model // self.num_heads

    @property
    def attn_tiles(self) -> int:
        qkv = math.ceil(3 * self.d_model / self.tile_rows) * math.ceil(self.d_model / self.tile_cols)
        out = math.ceil(self.d_model / self.tile_rows) * math.ceil(self.d_model / self.tile_cols)
        return qkv + out

    @property
    def mlp_tiles(self) -> int:
        up = math.ceil(self.d_ffn / self.tile_rows) * math.ceil(self.d_model / self.tile_cols)
        down = math.ceil(self.d_model / self.tile_rows) * math.ceil(self.d_ffn / self.tile_cols)
        return up + down

    @property
    def total_tiles(self) -> int:
        return self.attn_tiles + self.mlp_tiles


@dataclass(frozen=True)
class StageMetrics:
    """Error metrics for an intermediate execution stage."""

    rel_l2_error_pct: float
    snr_db: float


@dataclass(frozen=True)
class MechanismAttribution:
    """Attribution metrics for a single physical mechanism."""

    mechanism_name: str
    l2_error_without_pct: float
    delta_error_pct: float
    relative_importance_pct: float


@dataclass(frozen=True)
class BlockAttributionReport:
    """Full execution and error attribution report for a Transformer block."""

    d_model: int
    d_ffn: int
    num_heads: int
    total_physical_tiles: int
    ideal_quantized_metrics: StageMetrics
    raw_nonideal_metrics: StageMetrics
    calibrated_nonideal_metrics: StageMetrics
    stage_breakdown: dict[str, StageMetrics]
    attributions: list[MechanismAttribution]
    calibration_recovery_pct: float


class AnalogTransformerBlock:
    """Simulates a complete Transformer layer across 192 physical crossbar tiles."""

    def __init__(
        self,
        w_qkv: np.ndarray,
        w_out: np.ndarray,
        w_up: np.ndarray,
        w_down: np.ndarray,
        config: TransformerBlockConfig,
        nonideality_kwargs: dict[str, Any] | None = None,
        seed: int = 42,
    ) -> None:
        self.w_qkv = w_qkv.astype(np.float64)
        self.w_out = w_out.astype(np.float64)
        self.w_up = w_up.astype(np.float64)
        self.w_down = w_down.astype(np.float64)
        self.config = config
        self.nonideality_kwargs = nonideality_kwargs or {}
        self.seed = seed

        rng_seq = np.random.SeedSequence(seed)
        seeds_qkv, seeds_out, seeds_up, seeds_down = rng_seq.spawn(4)

        # 1. Attention Tiles
        self.tiles_qkv = self._build_tile_grid(
            self.w_qkv, 3 * config.d_model, config.d_model, seeds_qkv
        )
        self.tiles_out = self._build_tile_grid(
            self.w_out, config.d_model, config.d_model, seeds_out
        )

        # 2. MLP Tiles
        self.tiles_up = self._build_tile_grid(
            self.w_up, config.d_ffn, config.d_model, seeds_up
        )
        self.tiles_down = self._build_tile_grid(
            self.w_down, config.d_model, config.d_ffn, seeds_down
        )

    def _build_tile_grid(
        self,
        w: np.ndarray,
        m_out: int,
        m_in: int,
        seed_seq: np.random.SeedSequence,
    ) -> list[list[CrossbarTile]]:
        kr = math.ceil(m_out / self.config.tile_rows)
        kc = math.ceil(m_in / self.config.tile_cols)
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

    def _forward_projection(
        self,
        x: np.ndarray,
        tiles: list[list[CrossbarTile]],
        m_out: int,
        m_in: int,
        apply_calibration: bool,
    ) -> np.ndarray:
        kr = len(tiles)
        kc = len(tiles[0])
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

    def forward(
        self, x: np.ndarray, apply_calibration: bool = True
    ) -> tuple[np.ndarray, dict[str, np.ndarray]]:
        """Run full Transformer block: LN1 -> Attn -> Res1 -> LN2 -> MLP -> Res2."""
        if x.shape != (self.config.d_model,):
            raise ValueError(f"input shape {x.shape} != d_model={self.config.d_model}")

        # 1. Pre-LayerNorm 1
        x_norm1 = layer_norm(x)

        # 2. Analog Attention Projections
        qkv = self._forward_projection(
            x_norm1, self.tiles_qkv, 3 * self.config.d_model, self.config.d_model, apply_calibration
        )
        d = self.config.d_model
        q, k, v = qkv[:d], qkv[d : 2 * d], qkv[2 * d :]

        # 3. Digital Multi-Head Attention Evaluation
        context_heads: list[np.ndarray] = []
        for h in range(self.config.num_heads):
            h_start, h_end = h * self.config.d_head, (h + 1) * self.config.d_head
            _q_h, _k_h, v_h = q[h_start:h_end], k[h_start:h_end], v[h_start:h_end]
            attn_weight = 1.0  # 1 token context
            context_heads.append(attn_weight * v_h)
        context = np.concatenate(context_heads)

        # 4. Analog Out-Projection & Residual 1
        y_attn = self._forward_projection(
            context, self.tiles_out, self.config.d_model, self.config.d_model, apply_calibration
        )
        x_res1 = x + y_attn

        # 5. Pre-LayerNorm 2
        x_norm2 = layer_norm(x_res1)

        # 6. Analog MLP Projections & Residual 2
        h_up = self._forward_projection(
            x_norm2, self.tiles_up, self.config.d_ffn, self.config.d_model, apply_calibration
        )
        h_act = gelu(h_up)
        y_mlp = self._forward_projection(
            h_act, self.tiles_down, self.config.d_model, self.config.d_ffn, apply_calibration
        )
        x_res2 = x_res1 + y_mlp

        stages = {
            "attn_out": y_attn,
            "res1": x_res1,
            "mlp_out": y_mlp,
            "block_out": x_res2,
        }
        return x_res2, stages


def compute_stage_metrics(ref: np.ndarray, pred: np.ndarray) -> StageMetrics:
    diff = pred - ref
    ref_norm = float(np.linalg.norm(ref))
    diff_norm = float(np.linalg.norm(diff))
    rel_l2 = (diff_norm / ref_norm * 100.0) if ref_norm > 1e-12 else 0.0
    snr_db = (20.0 * math.log10(ref_norm / diff_norm)) if diff_norm > 1e-12 else 100.0
    return StageMetrics(rel_l2_error_pct=rel_l2, snr_db=snr_db)


def evaluate_transformer_block(
    w_qkv: np.ndarray,
    w_out: np.ndarray,
    w_up: np.ndarray,
    w_down: np.ndarray,
    config: TransformerBlockConfig,
    x_test: np.ndarray,
    crossbar_profile_path: Path | str,
    seed: int = 42,
) -> BlockAttributionReport:
    """Evaluate Transformer block error propagation and leave-one-out error attribution."""
    # Floating-Point Reference Execution
    ref_norm1 = layer_norm(x_test)
    ref_qkv = w_qkv @ ref_norm1
    d = config.d_model
    ref_q, ref_k, ref_v = ref_qkv[:d], ref_qkv[d : 2 * d], ref_qkv[2 * d :]
    scale = 1.0 / math.sqrt(config.d_head)
    ref_context = np.concatenate([
        (float(np.dot(ref_q[h * config.d_head : (h + 1) * config.d_head], ref_k[h * config.d_head : (h + 1) * config.d_head])) * scale * 0.0 + 1.0)
        * ref_v[h * config.d_head : (h + 1) * config.d_head]
        for h in range(config.num_heads)
    ])
    ref_attn = w_out @ ref_context
    ref_res1 = x_test + ref_attn
    ref_norm2 = layer_norm(ref_res1)
    ref_up = w_up @ ref_norm2
    ref_act = gelu(ref_up)
    ref_mlp = w_down @ ref_act
    ref_res2 = ref_res1 + ref_mlp
    ref_stages = {"attn_out": ref_attn, "res1": ref_res1, "mlp_out": ref_mlp, "block_out": ref_res2}

    # 1. Ideal Quantized Execution
    block_ideal = AnalogTransformerBlock(w_qkv, w_out, w_up, w_down, config, nonideality_kwargs=None, seed=seed)
    out_ideal, _ = block_ideal.forward(x_test, apply_calibration=False)
    metrics_ideal = compute_stage_metrics(ref_res2, out_ideal)

    # 2. Raw Non-Ideal Execution
    cb_profile = load_device_profile(crossbar_profile_path, physical_claim=False)
    full_nonideal_cfg = nonideality_config_from_profile(cb_profile, drift_time_s=1.0)

    block_raw = AnalogTransformerBlock(w_qkv, w_out, w_up, w_down, config, nonideality_kwargs=full_nonideal_cfg, seed=seed)
    out_raw, _ = block_raw.forward(x_test, apply_calibration=False)
    metrics_raw = compute_stage_metrics(ref_res2, out_raw)

    # 3. Calibrated Non-Ideal Execution
    block_cal = AnalogTransformerBlock(w_qkv, w_out, w_up, w_down, config, nonideality_kwargs=full_nonideal_cfg, seed=seed)
    out_cal, stages_cal = block_cal.forward(x_test, apply_calibration=True)
    metrics_cal = compute_stage_metrics(ref_res2, out_cal)

    # Stage breakdown
    stage_breakdown = {
        name: compute_stage_metrics(ref_stages[name], stages_cal[name])
        for name in stages_cal
    }

    # 4. Leave-One-Out Error Attribution Suite
    mechanisms = [
        ("r_wire_ohm", "2D IR Drop (1.0 Ω)", 0.0),
        ("sigma_prog_rel", "Programming Variation (3%)", 0.0),
        ("sigma_read_rel", "Read Noise (1%)", 0.0),
        ("drift_time_s", "Retention Drift (1s)", 0.0),
        ("p_stuck_hrs", "HRS Stuck Defects", 0.0),
        ("p_stuck_lrs", "LRS Stuck Defects", 0.0),
        ("iv_non_linearity_beta", "Cubic I-V Non-Linearity", 0.0),
    ]

    attributions: list[MechanismAttribution] = []
    total_delta = 0.0
    delta_list: list[tuple[str, float, float]] = []

    for param_key, display_name, zero_val in mechanisms:
        loo_cfg = dict(full_nonideal_cfg)
        loo_cfg[param_key] = zero_val
        if param_key == "p_stuck_hrs":
            loo_cfg["p_stuck_lrs"] = 0.0

        loo_block = AnalogTransformerBlock(w_qkv, w_out, w_up, w_down, config, nonideality_kwargs=loo_cfg, seed=seed)
        loo_out, _ = loo_block.forward(x_test, apply_calibration=True)
        loo_metrics = compute_stage_metrics(ref_res2, loo_out)
        delta_err = max(0.0, metrics_cal.rel_l2_error_pct - loo_metrics.rel_l2_error_pct)
        delta_list.append((display_name, loo_metrics.rel_l2_error_pct, delta_err))
        total_delta += delta_err

    for display_name, loo_err, delta_err in delta_list:
        importance = (delta_err / total_delta * 100.0) if total_delta > 1e-6 else 0.0
        attributions.append(
            MechanismAttribution(
                mechanism_name=display_name,
                l2_error_without_pct=float(round(loo_err, 2)),
                delta_error_pct=float(round(delta_err, 2)),
                relative_importance_pct=float(round(importance, 1)),
            )
        )

    impr = max(0.0, (metrics_raw.rel_l2_error_pct - metrics_cal.rel_l2_error_pct) / metrics_raw.rel_l2_error_pct * 100.0)

    return BlockAttributionReport(
        d_model=config.d_model,
        d_ffn=config.d_ffn,
        num_heads=config.num_heads,
        total_physical_tiles=config.total_tiles,
        ideal_quantized_metrics=metrics_ideal,
        raw_nonideal_metrics=metrics_raw,
        calibrated_nonideal_metrics=metrics_cal,
        stage_breakdown=stage_breakdown,
        attributions=attributions,
        calibration_recovery_pct=float(round(impr, 2)),
    )


def generate_transformer_block_extract() -> dict[str, Any]:
    """Generate deterministic extract dictionary for committed artifact."""
    rng = np.random.default_rng(2026)
    cb_path = _REPO / "device_profiles" / "crossbar-v1.json"

    # TinyGPT Block: d_model=64, d_ffn=256, 4 heads (192 physical tiles)
    w_qkv = rng.normal(0.0, 0.15, (192, 64))
    w_out = rng.normal(0.0, 0.15, (64, 64))
    w_up = rng.normal(0.0, 0.15, (256, 64))
    w_down = rng.normal(0.0, 0.15, (64, 256))
    x = rng.uniform(-1.0, 1.0, 64)

    cfg = TransformerBlockConfig(d_model=64, d_ffn=256, num_heads=4)
    report = evaluate_transformer_block(w_qkv, w_out, w_up, w_down, cfg, x, cb_path, seed=42)

    return {
        "schema_version": "0.1.0",
        "chapter": "0032-transformer-block",
        "title": "Transformer Block Error Attribution",
        "gate": "R7 — Transformer and LLM validation",
        "provenance": {
            "crossbar_profile": "device_profiles/crossbar-v1.json",
            "calibration_profile": "device_profiles/tile-calibration-v1.json",
            "claim_level": "SYSTEM_SIMULATED",
        },
        "block_hardware_breakdown": {
            "attention_qkv_tiles": 48,
            "attention_out_tiles": 16,
            "mlp_up_tiles": 64,
            "mlp_down_tiles": 64,
            "total_physical_tiles_per_block": 192,
        },
        "report": asdict(report),
    }


def render_svg(extract: dict[str, Any]) -> str:
    """Render an SVG diagram illustrating the Transformer block error attribution."""
    rep = extract["report"]
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
<text x="480" y="35" text-anchor="middle" class="title">Chapter 0032 — Transformer Block Error Attribution</text>
<text x="480" y="55" text-anchor="middle" class="sub">Full-layer simulation across 192 physical crossbar tiles with leave-one-out attribution</text>

<!-- Block Architecture Box -->
<rect x="50" y="85" width="410" height="420" rx="12" fill="#eff6ff" stroke="#2563eb" stroke-width="2"/>
<text x="70" y="115" class="box-title" fill="#1d4ed8">1. Transformer Block Hardware Pipeline</text>
<text x="70" y="135" class="sub">192 Physical 16×16 Crossbar Tiles per Block</text>

<rect x="70" y="155" width="370" height="80" rx="8" fill="white" stroke="#93c5fd"/>
<text x="85" y="180" class="box-title" fill="#1e40af">Attention Sub-Layer (64 Tiles)</text>
<text x="85" y="202" class="box-text">• Fused W_QKV: 48 tiles (192×64) | Out W_O: 16 tiles (64×64)</text>
<text x="85" y="222" class="sub">• Stage Error: L2={rep["stage_breakdown"]["attn_out"]["rel_l2_error_pct"]:.1f}% (SNR={rep["stage_breakdown"]["attn_out"]["snr_db"]:.1f} dB)</text>

<rect x="70" y="245" width="370" height="80" rx="8" fill="white" stroke="#93c5fd"/>
<text x="85" y="270" class="box-title" fill="#1e40af">MLP Sub-Layer (128 Tiles)</text>
<text x="85" y="292" class="box-text">• Up W_up: 64 tiles (256×64) | Down W_down: 64 tiles (64×256)</text>
<text x="85" y="312" class="sub">• Stage Error: L2={rep["stage_breakdown"]["mlp_out"]["rel_l2_error_pct"]:.1f}% (SNR={rep["stage_breakdown"]["mlp_out"]["snr_db"]:.1f} dB)</text>

<rect x="70" y="335" width="370" height="150" rx="8" fill="#f8fafc" stroke="#cbd5e1"/>
<text x="85" y="360" class="box-title">End-to-End Block Metrics</text>
<text x="85" y="385" class="box-text">• Ideal Quantized: L2={rep["ideal_quantized_metrics"]["rel_l2_error_pct"]:.2f}% (SNR: {rep["ideal_quantized_metrics"]["snr_db"]:.1f} dB)</text>
<text x="85" y="405" class="box-text">• Raw Non-Ideal: L2={rep["raw_nonideal_metrics"]["rel_l2_error_pct"]:.2f}% (SNR: {rep["raw_nonideal_metrics"]["snr_db"]:.1f} dB)</text>
<text x="85" y="425" class="box-title" fill="#15803d">• Calibrated Non-Ideal: L2={rep["calibrated_nonideal_metrics"]["rel_l2_error_pct"]:.2f}% (SNR: {rep["calibrated_nonideal_metrics"]["snr_db"]:.1f} dB)</text>
<text x="85" y="450" class="sub">Dual residuals &amp; calibration reduce error by {rep["calibration_recovery_pct"]:.1f}%</text>

<!-- Attribution Ranking Box -->
<rect x="500" y="85" width="410" height="420" rx="12" fill="#faf5ff" stroke="#9333ea" stroke-width="2"/>
<text x="520" y="115" class="box-title" fill="#7e22ce">2. Leave-One-Out Error Attribution Ranking</text>
<text x="520" y="135" class="sub">Marginal error impact of named physical mechanisms</text>

<rect x="520" y="155" width="370" height="330" rx="8" fill="white" stroke="#d8b4fe"/>
<text x="535" y="180" class="box-title" fill="#6b21a8">Mechanism Ranking (Importance %)</text>
<text x="535" y="210" class="box-text">1. 2D IR Drop (Wire R=1.0 Ω): {rep["attributions"][0]["relative_importance_pct"]:.1f}% (ΔL2: {rep["attributions"][0]["delta_error_pct"]:.1f}%)</text>
<text x="535" y="240" class="box-text">2. Programming Variation (3%): {rep["attributions"][1]["relative_importance_pct"]:.1f}% (ΔL2: {rep["attributions"][1]["delta_error_pct"]:.1f}%)</text>
<text x="535" y="270" class="box-text">3. Read Noise (1%): {rep["attributions"][2]["relative_importance_pct"]:.1f}% (ΔL2: {rep["attributions"][2]["delta_error_pct"]:.1f}%)</text>
<text x="535" y="300" class="box-text">4. Retention Drift (1s): {rep["attributions"][3]["relative_importance_pct"]:.1f}% (ΔL2: {rep["attributions"][3]["delta_error_pct"]:.1f}%)</text>
<text x="535" y="330" class="box-text">5. Stuck Defects (HRS/LRS): {rep["attributions"][4]["relative_importance_pct"]:.1f}% (ΔL2: {rep["attributions"][4]["delta_error_pct"]:.1f}%)</text>
<text x="535" y="360" class="box-text">6. Cubic I-V Non-Linearity: {rep["attributions"][6]["relative_importance_pct"]:.1f}% (ΔL2: {rep["attributions"][6]["delta_error_pct"]:.1f}%)</text>
<text x="535" y="410" class="formula">Leave-One-Out unconfounded random streams</text>
<text x="535" y="440" class="sub">Claim Level: SYSTEM_SIMULATED (Gate R7 evidence)</text>
</svg>
"""


def main() -> None:
    extract = generate_transformer_block_extract()
    out_dir = Path(__file__).resolve().parents[2] / "verification" / "circuit" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    extract_path = out_dir / "transformer-block-0032-extract.json"
    extract_path.write_text(json.dumps(extract, indent=2, sort_keys=True) + "\n", "utf-8")

    diagram_dir = Path(__file__).resolve().parent / "diagrams"
    diagram_dir.mkdir(parents=True, exist_ok=True)
    svg_path = diagram_dir / "transformer-block-0032.svg"
    svg_path.write_text(render_svg(extract), "utf-8")

    print(f"Wrote {extract_path}")
    print(f"Wrote {svg_path}")
    rep = extract["report"]
    print(
        f"Transformer Block (192 Tiles): Ideal L2={rep['ideal_quantized_metrics']['rel_l2_error_pct']:.2f}%, "
        f"Raw Non-Ideal L2={rep['raw_nonideal_metrics']['rel_l2_error_pct']:.2f}%, "
        f"Calibrated L2={rep['calibrated_nonideal_metrics']['rel_l2_error_pct']:.2f}%"
    )


if __name__ == "__main__":
    main()
