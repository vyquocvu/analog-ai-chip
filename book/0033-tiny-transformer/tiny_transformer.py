r"""Chapter 0033 — Tiny Transformer End-to-End Parity Study (Gate R7).

Deterministic float-reference vs analog-accelerated parity evaluation of the
full TinyGPT model (2 layers, 416 physical crossbar tiles) using the existing
``analog_llm.TinyGPT`` and ``Accelerator`` infrastructure.

Pipeline
--------
1. Construct ``TinyGPT`` with deterministic seed-0 weights.
2. **Float Reference**: ``forward_logits(tokens, accelerator=None)`` → FP64.
3. **Analog Accelerated**: ``forward_logits(tokens, accelerator=acc)`` with
   ``crossbar-v1`` profile, all 9 non-idealities, 4-bit converters.
4. **Parity Metrics**:
   - Logit-level relative L2 error (%) and SNR (dB).
   - Top-1 argmax token agreement (%) across all sequence positions.
   - Cross-entropy loss and perplexity degradation.
   - Autoregressive greedy generation divergence.
5. **Accelerator Ledger**: Total MACs, tile cycles, programs, rewrites.

Physical Hardware Footprint
---------------------------
TinyGPT (n_embd=64, n_layer=2, n_head=4, ffn=256, vocab=128, 16×16 tiles):
  - Per layer: W_QKV (48) + W_O (16) + W_up (64) + W_down (64) = 192 tiles
  - 2 layers: 384 tiles
  - W_head (128×64): 32 tiles
  - **Total: 416 physical crossbar tiles**
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from analog_llm import (
    Accelerator,
    Metrics,
    TinyGPT,
    TinyGPTConfig,
    build_tile_factory,
)

# ── Constants ────────────────────────────────────────────────────────────────

_PROFILE = _REPO / "device_profiles" / "crossbar-v1.json"
_TILE_ROWS = 16
_TILE_COLS = 16
_BITS = {"g_bits": 4, "dac_bits": 4, "adc_bits": 4}


# ── Parity Metrics ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ParityMetrics:
    """End-to-end parity metrics between float reference and analog path."""

    logit_rel_l2_error_pct: float
    logit_snr_db: float
    top1_token_agreement_pct: float
    float_cross_entropy: float
    analog_cross_entropy: float
    float_perplexity: float
    analog_perplexity: float
    perplexity_degradation: float
    generation_token_agreement_pct: float


def compute_cross_entropy(logits: np.ndarray, targets: np.ndarray) -> float:
    """Compute mean cross-entropy loss across sequence positions."""
    # Numerically stable: log_softmax = logits - logsumexp
    shifted = logits - logits.max(axis=-1, keepdims=True)
    log_sum_exp = np.log(np.sum(np.exp(shifted), axis=-1))
    log_probs_stable = shifted - log_sum_exp[:, None]
    # Gather target log-probs
    seq_len = targets.shape[0]
    target_log_probs = log_probs_stable[np.arange(seq_len), targets]
    return float(-np.mean(target_log_probs))


def compute_parity_metrics(
    float_logits: np.ndarray,
    analog_logits: np.ndarray,
    targets: np.ndarray,
    float_gen: np.ndarray,
    analog_gen: np.ndarray,
) -> ParityMetrics:
    """Compute comprehensive parity metrics between float and analog paths."""
    # L2 error and SNR on logits
    diff = analog_logits - float_logits
    ref_norm = float(np.linalg.norm(float_logits))
    diff_norm = float(np.linalg.norm(diff))
    rel_l2 = (diff_norm / ref_norm * 100.0) if ref_norm > 1e-12 else 0.0
    snr_db = (20.0 * math.log10(ref_norm / diff_norm)) if diff_norm > 1e-12 else 100.0

    # Top-1 token agreement across sequence positions
    float_tokens = np.argmax(float_logits, axis=-1)
    analog_tokens = np.argmax(analog_logits, axis=-1)
    seq_len = float_tokens.shape[0]
    agreement = float(np.sum(float_tokens == analog_tokens)) / seq_len * 100.0

    # Cross-entropy and perplexity
    float_ce = compute_cross_entropy(float_logits, targets)
    analog_ce = compute_cross_entropy(analog_logits, targets)
    float_ppl = math.exp(min(float_ce, 20.0))  # cap to avoid overflow
    analog_ppl = math.exp(min(analog_ce, 20.0))

    # Generation token agreement
    min_len = min(len(float_gen), len(analog_gen))
    gen_agree = float(np.sum(float_gen[:min_len] == analog_gen[:min_len])) / min_len * 100.0

    return ParityMetrics(
        logit_rel_l2_error_pct=float(round(rel_l2, 2)),
        logit_snr_db=float(round(snr_db, 2)),
        top1_token_agreement_pct=float(round(agreement, 1)),
        float_cross_entropy=float(round(float_ce, 4)),
        analog_cross_entropy=float(round(analog_ce, 4)),
        float_perplexity=float(round(float_ppl, 2)),
        analog_perplexity=float(round(analog_ppl, 2)),
        perplexity_degradation=float(round(analog_ppl - float_ppl, 2)),
        generation_token_agreement_pct=float(round(gen_agree, 1)),
    )


# ── Tile Count Computation ───────────────────────────────────────────────────

def compute_tile_count(cfg: TinyGPTConfig, tile_rows: int = 16, tile_cols: int = 16) -> dict[str, int]:
    """Compute the exact physical tile count for TinyGPT."""
    d = cfg.n_embd
    ffn = d * cfg.ffn_mult

    qkv_tiles = math.ceil(3 * d / tile_rows) * math.ceil(d / tile_cols)
    out_tiles = math.ceil(d / tile_rows) * math.ceil(d / tile_cols)
    up_tiles = math.ceil(ffn / tile_rows) * math.ceil(d / tile_cols)
    down_tiles = math.ceil(d / tile_rows) * math.ceil(ffn / tile_cols)
    per_layer = qkv_tiles + out_tiles + up_tiles + down_tiles
    head_tiles = math.ceil(cfg.vocab_size / tile_rows) * math.ceil(d / tile_cols)

    return {
        "qkv_tiles_per_layer": qkv_tiles,
        "out_tiles_per_layer": out_tiles,
        "up_tiles_per_layer": up_tiles,
        "down_tiles_per_layer": down_tiles,
        "tiles_per_layer": per_layer,
        "n_layers": cfg.n_layer,
        "total_layer_tiles": per_layer * cfg.n_layer,
        "head_tiles": head_tiles,
        "total_physical_tiles": per_layer * cfg.n_layer + head_tiles,
    }


# ── Main Evaluation ─────────────────────────────────────────────────────────

def evaluate_tiny_transformer(
    seed: int = 2033,
) -> dict[str, Any]:
    """Run full TinyGPT float-vs-analog parity evaluation."""
    rng = np.random.default_rng(seed)

    # 1. Construct TinyGPT
    cfg = TinyGPTConfig(
        vocab_size=128, n_embd=64, n_layer=2, n_head=4,
        block_size=16, ffn_mult=4, seed=0,
    )
    model = TinyGPT(cfg)
    tile_info = compute_tile_count(cfg, _TILE_ROWS, _TILE_COLS)

    # 2. Generate deterministic test prompt
    prompt = rng.integers(0, cfg.vocab_size, size=8).astype(np.int64)
    # Targets for CE: shifted by 1 (next-token prediction)
    targets = np.concatenate([prompt[1:], rng.integers(0, cfg.vocab_size, size=1)])

    # 3. Float reference forward pass
    float_logits = model.forward_logits(prompt, accelerator=None)

    # 4. Analog accelerated forward pass (with all crossbar-v1 non-idealities)
    factory = build_tile_factory(
        _PROFILE, _TILE_ROWS, _TILE_COLS,
        physical_claim=False,
        include_nonidealities=True,
        drift_time_s=1.0,
        rng=42,
        **_BITS,
    )
    # Use enough tiles to avoid temporal reuse for clean parity measurement
    acc = Accelerator(factory, _TILE_ROWS, _TILE_COLS, tile_count=tile_info["total_physical_tiles"])
    analog_logits = model.forward_logits(prompt, accelerator=acc)

    # 5. Accelerator ledger
    metrics = Metrics()
    metrics.update(acc)

    # 6. Greedy autoregressive generation comparison
    gen_prompt = prompt[:4].copy()

    float_gen = model.generate(gen_prompt, max_new=8, greedy=True, accelerator=None)

    acc2 = Accelerator(factory, _TILE_ROWS, _TILE_COLS, tile_count=tile_info["total_physical_tiles"])
    analog_gen = model.generate(gen_prompt, max_new=8, greedy=True, accelerator=acc2)

    # 7. Compute parity metrics
    parity = compute_parity_metrics(float_logits, analog_logits, targets, float_gen, analog_gen)

    return {
        "config": {
            "vocab_size": cfg.vocab_size,
            "n_embd": cfg.n_embd,
            "n_layer": cfg.n_layer,
            "n_head": cfg.n_head,
            "block_size": cfg.block_size,
            "ffn_mult": cfg.ffn_mult,
            "d_ffn": cfg.n_embd * cfg.ffn_mult,
        },
        "tile_breakdown": tile_info,
        "parity_metrics": {
            "logit_rel_l2_error_pct": parity.logit_rel_l2_error_pct,
            "logit_snr_db": parity.logit_snr_db,
            "top1_token_agreement_pct": parity.top1_token_agreement_pct,
            "float_cross_entropy": parity.float_cross_entropy,
            "analog_cross_entropy": parity.analog_cross_entropy,
            "float_perplexity": parity.float_perplexity,
            "analog_perplexity": parity.analog_perplexity,
            "perplexity_degradation": parity.perplexity_degradation,
            "generation_token_agreement_pct": parity.generation_token_agreement_pct,
        },
        "accelerator_ledger": {
            "total_macs": metrics.macs,
            "tile_cycles": metrics.cycles,
            "programs": metrics.programs,
            "rewrites": metrics.rewrites,
        },
        "generation_comparison": {
            "prompt_tokens": gen_prompt.tolist(),
            "float_sequence": float_gen.tolist(),
            "analog_sequence": analog_gen.tolist(),
        },
    }


def generate_tiny_transformer_extract() -> dict[str, Any]:
    """Generate deterministic committed extract for Chapter 0033."""
    result = evaluate_tiny_transformer(seed=2033)

    extract = {
        "schema_version": "0.1.0",
        "chapter": "0033-tiny-transformer",
        "title": "Tiny Transformer End-to-End Parity Study",
        "gate": "R7 — Transformer and LLM validation",
        "provenance": {
            "crossbar_profile": "device_profiles/crossbar-v1.json",
            "claim_level": "SYSTEM_SIMULATED",
            "converter_bits": "4-bit DAC / 4-bit ADC / 4-bit conductance",
            "non_idealities": "all 9 crossbar-v1 mechanisms active",
        },
        **result,
    }

    out_dir = _REPO / "verification" / "circuit" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    extract_path = out_dir / "tiny-transformer-0033-extract.json"
    extract_path.write_text(json.dumps(extract, indent=2, sort_keys=True) + "\n", "utf-8")
    print(f"Wrote {extract_path}")

    # Generate SVG diagram
    svg_path = Path(__file__).resolve().parent / "diagrams" / "tiny-transformer-0033.svg"
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(render_svg(extract), "utf-8")
    print(f"Wrote {svg_path}")

    return extract


def render_svg(extract: dict[str, Any]) -> str:
    """Render an SVG diagram illustrating the TinyGPT parity study."""
    pm = extract["parity_metrics"]
    tb = extract["tile_breakdown"]
    al = extract["accelerator_ledger"]
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
<text x="480" y="35" text-anchor="middle" class="title">Chapter 0033 — Tiny Transformer End-to-End Parity Study</text>
<text x="480" y="55" text-anchor="middle" class="sub">Full TinyGPT (2 layers) on {tb["total_physical_tiles"]} physical crossbar tiles — Float Reference vs Analog Accelerated</text>

<!-- Hardware Footprint Box -->
<rect x="50" y="80" width="410" height="200" rx="12" fill="#eff6ff" stroke="#2563eb" stroke-width="2"/>
<text x="70" y="105" class="box-title" fill="#1d4ed8">1. Physical Hardware Footprint ({tb["total_physical_tiles"]} Tiles)</text>
<text x="70" y="130" class="box-text">Per Layer: W_QKV ({tb["qkv_tiles_per_layer"]}) + W_O ({tb["out_tiles_per_layer"]}) + W_up ({tb["up_tiles_per_layer"]}) + W_down ({tb["down_tiles_per_layer"]}) = {tb["tiles_per_layer"]} tiles</text>
<text x="70" y="155" class="box-text">× {tb["n_layers"]} layers = {tb["total_layer_tiles"]} tiles</text>
<text x="70" y="180" class="box-text">+ Language Model Head W_head: {tb["head_tiles"]} tiles (128×64)</text>
<text x="70" y="205" class="box-title" fill="#15803d">Total: {tb["total_physical_tiles"]} physical 16×16 crossbar tiles</text>
<text x="70" y="230" class="sub">4-bit DAC / 4-bit ADC / 4-bit conductance, all 9 non-idealities active</text>
<text x="70" y="255" class="formula">MACs={al["total_macs"]:,}  Tile Cycles={al["tile_cycles"]}  Programs={al["programs"]}</text>

<!-- Parity Metrics Box -->
<rect x="500" y="80" width="410" height="200" rx="12" fill="#faf5ff" stroke="#9333ea" stroke-width="2"/>
<text x="520" y="105" class="box-title" fill="#7e22ce">2. Float vs Analog Parity Metrics</text>

<rect x="520" y="120" width="370" height="145" rx="8" fill="white" stroke="#d8b4fe"/>
<text x="535" y="143" class="box-text">• Logit L2 Error: {pm["logit_rel_l2_error_pct"]:.1f}% (SNR: {pm["logit_snr_db"]:.1f} dB)</text>
<text x="535" y="168" class="box-text">• Top-1 Token Agreement: {pm["top1_token_agreement_pct"]:.1f}%</text>
<text x="535" y="193" class="box-text">• Float PPL: {pm["float_perplexity"]:.1f} → Analog PPL: {pm["analog_perplexity"]:.1f} (Δ={pm["perplexity_degradation"]:.1f})</text>
<text x="535" y="218" class="box-text">• Float CE: {pm["float_cross_entropy"]:.3f} → Analog CE: {pm["analog_cross_entropy"]:.3f}</text>
<text x="535" y="243" class="box-title" fill="#15803d">• Generation Token Agreement: {pm["generation_token_agreement_pct"]:.1f}%</text>

<!-- TinyGPT Pipeline Diagram -->
<rect x="50" y="310" width="860" height="200" rx="12" fill="#f8fafc" stroke="#94a3b8" stroke-width="2"/>
<text x="70" y="340" class="box-title">3. TinyGPT Hybrid Analog/Digital Execution Pipeline</text>

<rect x="70" y="360" width="120" height="50" rx="6" fill="#dbeafe" stroke="#3b82f6"/>
<text x="130" y="390" text-anchor="middle" class="formula">Embeddings</text>
<text x="130" y="405" text-anchor="middle" class="sub">Digital</text>

<rect x="210" y="360" width="120" height="50" rx="6" fill="#fef3c7" stroke="#f59e0b"/>
<text x="270" y="390" text-anchor="middle" class="formula">Layer 0</text>
<text x="270" y="405" text-anchor="middle" class="sub">{tb["tiles_per_layer"]} Analog Tiles</text>

<rect x="350" y="360" width="120" height="50" rx="6" fill="#fef3c7" stroke="#f59e0b"/>
<text x="410" y="390" text-anchor="middle" class="formula">Layer 1</text>
<text x="410" y="405" text-anchor="middle" class="sub">{tb["tiles_per_layer"]} Analog Tiles</text>

<rect x="490" y="360" width="120" height="50" rx="6" fill="#dbeafe" stroke="#3b82f6"/>
<text x="550" y="390" text-anchor="middle" class="formula">Final LN</text>
<text x="550" y="405" text-anchor="middle" class="sub">Digital</text>

<rect x="630" y="360" width="120" height="50" rx="6" fill="#fef3c7" stroke="#f59e0b"/>
<text x="690" y="390" text-anchor="middle" class="formula">LM Head</text>
<text x="690" y="405" text-anchor="middle" class="sub">{tb["head_tiles"]} Analog Tiles</text>

<rect x="770" y="360" width="120" height="50" rx="6" fill="#dcfce7" stroke="#22c55e"/>
<text x="830" y="390" text-anchor="middle" class="formula">Logits</text>
<text x="830" y="405" text-anchor="middle" class="sub">[8, 128]</text>

<text x="70" y="450" class="box-text">Analog Path: Dense matmuls (QKV, Out, Up, Down, Head) on {tb["total_physical_tiles"]} physical crossbar tiles</text>
<text x="70" y="470" class="box-text">Digital Path: Embeddings, LayerNorm, Softmax, GELU, Residual Adds, Bias Adds</text>
<text x="70" y="490" class="sub">Claim Level: SYSTEM_SIMULATED (Gate R7 evidence) — crossbar-v1 profile with all 9 non-idealities</text>
</svg>
"""


def main() -> None:
    extract = generate_tiny_transformer_extract()
    pm = extract["parity_metrics"]
    tb = extract["tile_breakdown"]
    print(
        f"TinyGPT Parity ({tb['total_physical_tiles']} Tiles): "
        f"L2={pm['logit_rel_l2_error_pct']:.1f}%, "
        f"Top-1 Agree={pm['top1_token_agreement_pct']:.1f}%, "
        f"PPL Float={pm['float_perplexity']:.1f} → Analog={pm['analog_perplexity']:.1f}"
    )


if __name__ == "__main__":
    main()
