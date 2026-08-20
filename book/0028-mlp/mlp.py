r"""Chapter 0028 — Multi-Layer Perceptron (MLP) Block Mapping (Gate R7).

Simulates a complete Transformer Feed-Forward Network (MLP) block combining two
analog matrix projections with intermediate digital non-linear activation:

1. **Two-Stage Projection Pipeline**:
   - **Up-Projection**: $h_1 = W_{\text{up}} x$ ($d_{\text{model}} \to d_{\text{ffn}}$)
   - **Digital Activation**: $h_{\text{act}} = \text{GELU}(h_{1,\text{cal}})$
   - **Down-Projection**: $y = W_{\text{down}} h_{\text{act}}$ ($d_{\text{ffn}} \to d_{\text{model}}$)
   - **Digital Residual Connection**: $y_{\text{out}} = x + y_{\text{cal}}$

2. **Physical Tile Mapping**:
   - Both $W_{\text{up}}$ and $W_{\text{down}}$ are partitioned into physical $R \times C$ tiles ($16\times 16$).
   - 4-bit weights mapped to differential conductances $(G^+, G^-)$ with balanced zero.
   - Evaluated under all 9 `crossbar-v1` non-idealities with post-ADC output calibration ($a^* = 0.9795135$).

3. **Compound Error Propagation**:
   - Analyzes error cascade across the analog-digital boundary and quantifies end-to-end SNR and relative $L_2$ error.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from analog_llm.device_profile import load_device_profile  # noqa: E402
from analog_llm.profile_adapter import nonideality_config_from_profile  # noqa: E402
from analog_llm.tile import CrossbarTile  # noqa: E402

CALIBRATION_GAIN = 0.9795135153


class ActivationFunction(str, Enum):
    GELU = "gelu"
    RELU = "relu"
    SILU = "silu"


def gelu(x: np.ndarray) -> np.ndarray:
    """Exact Gaussian Error Linear Unit (GELU) activation."""
    return 0.5 * x * (1.0 + np.tanh(np.sqrt(2.0 / np.pi) * (x + 0.044715 * np.power(x, 3))))


def silu(x: np.ndarray) -> np.ndarray:
    """Sigmoid Linear Unit (SiLU / Swish) activation."""
    return x / (1.0 + np.exp(-np.clip(x, -30.0, 30.0)))


def apply_activation(x: np.ndarray, fn: ActivationFunction) -> np.ndarray:
    if fn == ActivationFunction.GELU:
        return gelu(x)
    elif fn == ActivationFunction.RELU:
        return np.maximum(0.0, x)
    elif fn == ActivationFunction.SILU:
        return silu(x)
    else:
        raise ValueError(f"unknown activation function {fn}")


@dataclass(frozen=True)
class MLPConfig:
    """Configuration for an analog Transformer MLP block."""

    d_model: int
    d_ffn: int
    tile_rows: int = 16
    tile_cols: int = 16
    dac_bits: int = 4
    adc_bits: int = 4
    g_bits: int = 4
    vin_max_v: float = 2.34375
    vout_max_v: float = 2.5
    activation: ActivationFunction = ActivationFunction.GELU
    include_residual: bool = True

    def __post_init__(self) -> None:
        if self.d_model <= 0 or self.d_ffn <= 0:
            raise ValueError("d_model and d_ffn must be positive")
        if self.tile_rows <= 0 or self.tile_cols <= 0:
            raise ValueError("tile dimensions must be positive")

    @property
    def up_tiles(self) -> int:
        return math.ceil(self.d_ffn / self.tile_rows) * math.ceil(self.d_model / self.tile_cols)

    @property
    def down_tiles(self) -> int:
        return math.ceil(self.d_model / self.tile_rows) * math.ceil(self.d_ffn / self.tile_cols)

    @property
    def total_tiles(self) -> int:
        return self.up_tiles + self.down_tiles


@dataclass(frozen=True)
class MLPEvaluationMetrics:
    """Accuracy evaluation metrics for an MLP block."""

    rel_l2_error_pct: float
    mae: float
    max_abs_error: float
    snr_db: float


@dataclass(frozen=True)
class MLPBlockReport:
    """Report comparing ideal, raw non-ideal, and calibrated MLP execution."""

    block_name: str
    d_model: int
    d_ffn: int
    total_physical_tiles: int
    activation: str
    ideal_quantized: MLPEvaluationMetrics
    raw_nonideal: MLPEvaluationMetrics
    calibrated_nonideal: MLPEvaluationMetrics
    calibration_improvement_pct: float


class AnalogMLPBlock:
    """Simulates a complete two-projection analog MLP block with intermediate activation."""

    def __init__(
        self,
        w_up: np.ndarray,
        w_down: np.ndarray,
        config: MLPConfig,
        nonideality_kwargs: dict[str, Any] | None = None,
        seed: int = 42,
    ) -> None:
        if w_up.shape != (config.d_ffn, config.d_model):
            raise ValueError(f"w_up shape {w_up.shape} != ({config.d_ffn}, {config.d_model})")
        if w_down.shape != (config.d_model, config.d_ffn):
            raise ValueError(f"w_down shape {w_down.shape} != ({config.d_model}, {config.d_ffn})")

        self.w_up = w_up.astype(np.float64)
        self.w_down = w_down.astype(np.float64)
        self.config = config
        self.nonideality_kwargs = nonideality_kwargs or {}
        self.seed = seed

        rng_seq = np.random.SeedSequence(seed)
        seeds_up, seeds_down = rng_seq.spawn(2)

        # 1. Build Up-Projection Tile Grid: shape (kr_up, kc_up)
        self.kr_up = math.ceil(config.d_ffn / config.tile_rows)
        self.kc_up = math.ceil(config.d_model / config.tile_cols)
        self.tiles_up = self._build_tile_grid(
            self.w_up, self.kr_up, self.kc_up, config.d_ffn, config.d_model, seeds_up
        )

        # 2. Build Down-Projection Tile Grid: shape (kr_down, kc_down)
        self.kr_down = math.ceil(config.d_model / config.tile_rows)
        self.kc_down = math.ceil(config.d_ffn / config.tile_cols)
        self.tiles_down = self._build_tile_grid(
            self.w_down, self.kr_down, self.kc_down, config.d_model, config.d_ffn, seeds_down
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

    def _forward_projection(
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

    def forward(self, x: np.ndarray, apply_calibration: bool = True) -> np.ndarray:
        """Execute full MLP block: Up -> GELU -> Down -> Residual."""
        if x.shape != (self.config.d_model,):
            raise ValueError(f"input shape {x.shape} != d_model={self.config.d_model}")

        # 1. Analog Up-Projection
        h_up = self._forward_projection(
            x, self.tiles_up, self.kr_up, self.kc_up, self.config.d_ffn, self.config.d_model, apply_calibration
        )

        # 2. Digital Non-Linear Activation
        h_act = apply_activation(h_up, self.config.activation)

        # 3. Analog Down-Projection
        y_down = self._forward_projection(
            h_act, self.tiles_down, self.kr_down, self.kc_down, self.config.d_model, self.config.d_ffn, apply_calibration
        )

        # 4. Residual Addition (if enabled)
        if self.config.include_residual:
            return x + y_down
        return y_down


def compute_mlp_metrics(ref: np.ndarray, pred: np.ndarray) -> MLPEvaluationMetrics:
    diff = pred - ref
    ref_norm = float(np.linalg.norm(ref))
    diff_norm = float(np.linalg.norm(diff))

    rel_l2 = (diff_norm / ref_norm * 100.0) if ref_norm > 1e-12 else 0.0
    mae = float(np.mean(np.abs(diff)))
    max_err = float(np.max(np.abs(diff)))
    snr_db = (20.0 * math.log10(ref_norm / diff_norm)) if diff_norm > 1e-12 else 100.0

    return MLPEvaluationMetrics(
        rel_l2_error_pct=rel_l2,
        mae=mae,
        max_abs_error=max_err,
        snr_db=snr_db,
    )


def evaluate_mlp_block(
    block_name: str,
    w_up: np.ndarray,
    w_down: np.ndarray,
    config: MLPConfig,
    x_test: np.ndarray,
    crossbar_profile_path: Path | str,
    seed: int = 42,
) -> MLPBlockReport:
    """Evaluate an MLP block across ideal quantized, raw non-ideal, and calibrated execution."""
    # Floating-Point Reference
    ref_h = apply_activation(w_up @ x_test, config.activation)
    ref_out = (x_test + w_down @ ref_h) if config.include_residual else (w_down @ ref_h)

    # 1. Ideal Quantized
    block_ideal = AnalogMLPBlock(w_up, w_down, config, nonideality_kwargs=None, seed=seed)
    out_ideal = block_ideal.forward(x_test, apply_calibration=False)
    metrics_ideal = compute_mlp_metrics(ref_out, out_ideal)

    # 2. Raw Non-Ideal
    cb_profile = load_device_profile(crossbar_profile_path, physical_claim=False)
    nonideal_cfg = nonideality_config_from_profile(cb_profile, drift_time_s=1.0)

    block_raw = AnalogMLPBlock(w_up, w_down, config, nonideality_kwargs=nonideal_cfg, seed=seed)
    out_raw = block_raw.forward(x_test, apply_calibration=False)
    metrics_raw = compute_mlp_metrics(ref_out, out_raw)

    # 3. Calibrated Non-Ideal
    block_cal = AnalogMLPBlock(w_up, w_down, config, nonideality_kwargs=nonideal_cfg, seed=seed)
    out_cal = block_cal.forward(x_test, apply_calibration=True)
    metrics_cal = compute_mlp_metrics(ref_out, out_cal)

    impr = max(0.0, (metrics_raw.rel_l2_error_pct - metrics_cal.rel_l2_error_pct) / metrics_raw.rel_l2_error_pct * 100.0)

    return MLPBlockReport(
        block_name=block_name,
        d_model=config.d_model,
        d_ffn=config.d_ffn,
        total_physical_tiles=config.total_tiles,
        activation=config.activation.value,
        ideal_quantized=metrics_ideal,
        raw_nonideal=metrics_raw,
        calibrated_nonideal=metrics_cal,
        calibration_improvement_pct=impr,
    )


def generate_mlp_extract() -> dict[str, Any]:
    """Generate deterministic extract dictionary for committed artifact."""
    rng = np.random.default_rng(2026)
    cb_path = _REPO / "device_profiles" / "crossbar-v1.json"

    # Workload 1: TinyGPT MLP Block (d_model=64, d_ffn=256 -> 64+64 = 128 tiles)
    w_up_tg = rng.normal(0.0, 0.15, (256, 64))
    w_down_tg = rng.normal(0.0, 0.15, (64, 256))
    x_tg = rng.uniform(-1.0, 1.0, 64)
    cfg_tg = MLPConfig(d_model=64, d_ffn=256, activation=ActivationFunction.GELU)
    rep_tg = evaluate_mlp_block("TinyGPT_MLP_GELU", w_up_tg, w_down_tg, cfg_tg, x_tg, cb_path, seed=42)

    # Workload 2: TinyGPT MLP Block with SiLU / Swish Activation
    cfg_silu = MLPConfig(d_model=64, d_ffn=256, activation=ActivationFunction.SILU)
    rep_silu = evaluate_mlp_block("TinyGPT_MLP_SiLU", w_up_tg, w_down_tg, cfg_silu, x_tg, cb_path, seed=42)

    return {
        "schema_version": "0.1.0",
        "chapter": "0028-mlp",
        "title": "Multi-Layer Perceptron (MLP) Block Mapping",
        "gate": "R7 — Transformer and LLM validation",
        "provenance": {
            "crossbar_profile": "device_profiles/crossbar-v1.json",
            "calibration_profile": "device_profiles/tile-calibration-v1.json",
            "claim_level": "SYSTEM_SIMULATED",
        },
        "formulas": {
            "up_projection": "h1 = a_star * sum(Tile_up(x))",
            "activation": "h_act = GELU(h1) or SiLU(h1)",
            "down_projection": "y = a_star * sum(Tile_down(h_act))",
            "residual": "y_out = x + y",
        },
        "evaluations": {
            "tinygpt_mlp_gelu": asdict(rep_tg),
            "tinygpt_mlp_silu": asdict(rep_silu),
        },
    }


def render_svg(extract: dict[str, Any]) -> str:
    """Render an SVG diagram illustrating the MLP mapping pipeline and results."""
    gelu_rep = extract["evaluations"]["tinygpt_mlp_gelu"]
    silu_rep = extract["evaluations"]["tinygpt_mlp_silu"]
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
<text x="480" y="35" text-anchor="middle" class="title">Chapter 0028 — Multi-Layer Perceptron (MLP) Mapping</text>
<text x="480" y="55" text-anchor="middle" class="sub">Two-stage analog projection pipeline with digital non-linear activation and residual sum</text>

<!-- Flow Diagram Box -->
<rect x="50" y="85" width="410" height="420" rx="12" fill="#eff6ff" stroke="#2563eb" stroke-width="2"/>
<text x="70" y="115" class="box-title" fill="#1d4ed8">1. Hybrid Analog-Digital Pipeline</text>
<text x="70" y="135" class="sub">TinyGPT MLP Block: d_model=64, d_ffn=256 (128 Tiles)</text>

<rect x="70" y="155" width="370" height="75" rx="8" fill="white" stroke="#93c5fd"/>
<text x="85" y="180" class="box-title" fill="#1e40af">Stage 1: Analog Up-Projection (W_up)</text>
<text x="85" y="202" class="box-text">• Matrix 256×64 → 64 physical 16×16 tiles</text>
<text x="85" y="220" class="sub">• MVM under crossbar-v1 non-idealities + calibration</text>

<rect x="70" y="245" width="370" height="75" rx="8" fill="#fefce8" stroke="#ca8a04"/>
<text x="85" y="270" class="box-title" fill="#a16207">Stage 2: Digital Activation (GELU / SiLU)</text>
<text x="85" y="292" class="box-text">• Non-linear activation evaluated on digital unit</text>
<text x="85" y="310" class="sub">• Output quantized to 4 bits for down-stage DACs</text>

<rect x="70" y="335" width="370" height="75" rx="8" fill="white" stroke="#93c5fd"/>
<text x="85" y="360" class="box-title" fill="#1e40af">Stage 3: Analog Down-Projection (W_down)</text>
<text x="85" y="382" class="box-text">• Matrix 64×256 → 64 physical 16×16 tiles</text>
<text x="85" y="400" class="sub">• MVM + calibration + digital residual sum (x + y)</text>

<rect x="70" y="425" width="370" height="60" rx="8" fill="#f8fafc" stroke="#cbd5e1"/>
<text x="85" y="450" class="formula">y_out = x + a* · W_down @ GELU(a* · W_up @ x)</text>
<text x="85" y="470" class="sub">Total Tiles: 64 Up + 64 Down = 128 tiles</text>

<!-- Accuracy Results Box -->
<rect x="500" y="85" width="410" height="420" rx="12" fill="#faf5ff" stroke="#9333ea" stroke-width="2"/>
<text x="520" y="115" class="box-title" fill="#7e22ce">2. End-to-End MLP Accuracy &amp; SNR</text>
<text x="520" y="135" class="sub">Compound error propagation across two analog stages</text>

<!-- GELU Result -->
<rect x="520" y="155" width="370" height="150" rx="8" fill="white" stroke="#d8b4fe"/>
<text x="535" y="180" class="box-title" fill="#6b21a8">TinyGPT MLP (GELU Activation)</text>
<text x="535" y="202" class="box-text">• Ideal Quantized L2 Error: {gelu_rep["ideal_quantized"]["rel_l2_error_pct"]:.2f}% (SNR: {gelu_rep["ideal_quantized"]["snr_db"]:.1f} dB)</text>
<text x="535" y="222" class="box-text">• Raw Non-Ideal L2 Error: {gelu_rep["raw_nonideal"]["rel_l2_error_pct"]:.2f}% (SNR: {gelu_rep["raw_nonideal"]["snr_db"]:.1f} dB)</text>
<text x="535" y="242" class="box-title" fill="#15803d">• Calibrated L2 Error: {gelu_rep["calibrated_nonideal"]["rel_l2_error_pct"]:.2f}% (SNR: {gelu_rep["calibrated_nonideal"]["snr_db"]:.1f} dB)</text>
<text x="535" y="262" class="sub">Residual connection dampens error: SNR = {gelu_rep["calibrated_nonideal"]["snr_db"]:.1f} dB</text>

<!-- SiLU Result -->
<rect x="520" y="320" width="370" height="165" rx="8" fill="#f0fdf4" stroke="#86efac"/>
<text x="535" y="345" class="box-title" fill="#166534">TinyGPT MLP (SiLU / Swish Activation)</text>
<text x="535" y="370" class="box-text">• Ideal Quantized L2 Error: {silu_rep["ideal_quantized"]["rel_l2_error_pct"]:.2f}% (SNR: {silu_rep["ideal_quantized"]["snr_db"]:.1f} dB)</text>
<text x="535" y="390" class="box-text">• Raw Non-Ideal L2 Error: {silu_rep["raw_nonideal"]["rel_l2_error_pct"]:.2f}% (SNR: {silu_rep["raw_nonideal"]["snr_db"]:.1f} dB)</text>
<text x="535" y="410" class="box-title" fill="#15803d">• Calibrated L2 Error: {silu_rep["calibrated_nonideal"]["rel_l2_error_pct"]:.2f}% (SNR: {silu_rep["calibrated_nonideal"]["snr_db"]:.1f} dB)</text>
<text x="535" y="430" class="sub">Calibration reduces compound error by {silu_rep["calibration_improvement_pct"]:.1f}%</text>
<text x="535" y="455" class="formula">E_L2 = ||y_pred − y_ref||₂ / ||y_ref||₂</text>
</svg>
"""


def main() -> None:
    extract = generate_mlp_extract()
    out_dir = Path(__file__).resolve().parents[2] / "verification" / "circuit" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    extract_path = out_dir / "mlp-0028-extract.json"
    extract_path.write_text(json.dumps(extract, indent=2, sort_keys=True) + "\n", "utf-8")

    diagram_dir = Path(__file__).resolve().parent / "diagrams"
    diagram_dir.mkdir(parents=True, exist_ok=True)
    svg_path = diagram_dir / "mlp-0028.svg"
    svg_path.write_text(render_svg(extract), "utf-8")

    print(f"Wrote {extract_path}")
    print(f"Wrote {svg_path}")
    gelu_rep = extract["evaluations"]["tinygpt_mlp_gelu"]
    print(
        f"TinyGPT MLP (GELU): Ideal L2={gelu_rep['ideal_quantized']['rel_l2_error_pct']:.2f}%, "
        f"Raw Non-Ideal L2={gelu_rep['raw_nonideal']['rel_l2_error_pct']:.2f}%, "
        f"Calibrated L2={gelu_rep['calibrated_nonideal']['rel_l2_error_pct']:.2f}%"
    )


if __name__ == "__main__":
    main()
