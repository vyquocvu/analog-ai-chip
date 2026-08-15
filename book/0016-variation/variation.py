r"""Chapter 0016 — Non-Volatile Memory Programming & Read Variation (Monte Carlo).

Models the stochastic variability of physical analog memory cells (ReRAM / PCM / Flash):

1. **Programming (Write) Variation**:
   Due to discrete atomic filament growth and pulse-verify tolerances, programmed
   conductance exhibits a relative dispersion $\sigma_{prog}$ (assumed 3%):
       G_{prog} = G_{target} \cdot (1 + \delta_{prog}), \quad \delta_{prog} \sim \mathcal{N}(0, \sigma_{prog}^2)

2. **Read (Temporal) Noise**:
   Random telegraph noise (RTN) and thermal read fluctuations during MVM execution
   introduce short-term read noise $\sigma_{read}$ (assumed 1%):
       G_{read} = G_{prog} \cdot (1 + \delta_{read}), \quad \delta_{read} \sim \mathcal{N}(0, \sigma_{read}^2)

3. **Combined Differential Weight Error**:
   Total variance combines in quadrature: $\sigma_{tot} = \sqrt{\sigma_{prog}^2 + \sigma_{read}^2}$.
   For a differential pair $(G^+, G^-)$ representing target weight $w \in [-1, 1]$:
       \sigma_w^2(w) = \frac{(G^+ \cdot \sigma_{tot})^2 + (G^- \cdot \sigma_{tot})^2}{(G_{max} - G_{min})^2}
   - At $w = 0$: \sigma_w(0) = \frac{\sqrt{2} \cdot G_{min} \cdot \sigma_{tot}}{Span} \approx 0.50%
   - At $|w| = 1$: \sigma_w(1) = \frac{\sqrt{G_{max}^2 + G_{min}^2} \cdot \sigma_{tot}}{Span} \approx 3.53%

Deterministic simulation:
Uses a fixed random seed (seed = 42) for reproducible 1000-draw Monte Carlo sweeps.
All variation parameters are sensitivity assumptions ('assumed') and fail closed
under physical claim verification.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

# Nominal parameters from Chapter 0015
G_MIN_S = 10.0e-6        # 10 uS
G_MAX_S = 100.0e-6       # 100 uS
SPAN_S = G_MAX_S - G_MIN_S  # 90 uS
BITS = 4                 # 16 states
DEFAULT_SEED = 42

# Assumed sensitivity variation parameters
SIGMA_PROG = 0.03        # 3% relative programming dispersion
SIGMA_READ = 0.01        # 1% relative read noise


@dataclass(frozen=True)
class VariationConfig:
    """Configuration for NVM cell programming and read variability."""

    sigma_prog: float = SIGMA_PROG
    sigma_read: float = SIGMA_READ
    seed: int = DEFAULT_SEED

    def __post_init__(self) -> None:
        if self.sigma_prog < 0 or self.sigma_read < 0:
            raise ValueError("variation standard deviations must be non-negative")

    @property
    def sigma_total(self) -> float:
        return float(np.sqrt(self.sigma_prog**2 + self.sigma_read**2))


def theoretical_weight_std(w: float, sigma_tot: float = 0.0316227766, g_min: float = G_MIN_S, span: float = SPAN_S) -> float:
    """Closed-form standard deviation of effective signed weight w_eff."""
    w_abs = abs(float(w))
    g_active = g_min + w_abs * span
    g_inactive = g_min
    var_w = ((g_active * sigma_tot) ** 2 + (g_inactive * sigma_tot) ** 2) / (span**2)
    return float(np.sqrt(var_w))


def sample_conductance_monte_carlo(
    g_target: float,
    n_samples: int = 1000,
    config: VariationConfig | None = None,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Generate n_samples of noisy conductance draws around g_target."""
    if config is None:
        config = VariationConfig()
    if rng is None:
        rng = np.random.default_rng(config.seed)

    # 1. Programming noise
    delta_prog = rng.normal(0.0, config.sigma_prog, size=n_samples)
    g_prog = g_target * (1.0 + delta_prog)

    # 2. Read noise
    delta_read = rng.normal(0.0, config.sigma_read, size=n_samples)
    g_read = g_prog * (1.0 + delta_read)

    return np.clip(g_read, 0.0, None)  # conductance must remain non-negative


def sample_differential_weight_monte_carlo(
    w_target: float,
    n_samples: int = 1000,
    config: VariationConfig | None = None,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Sample noisy (G+, G-) and resolved w_eff across Monte Carlo trials."""
    if config is None:
        config = VariationConfig()
    if rng is None:
        rng = np.random.default_rng(config.seed)

    w_clamped = float(np.clip(w_target, -1.0, 1.0))
    if w_clamped >= 0:
        target_p = G_MIN_S + w_clamped * SPAN_S
        target_m = G_MIN_S
    else:
        target_p = G_MIN_S
        target_m = G_MIN_S + abs(w_clamped) * SPAN_S

    g_plus_samples = sample_conductance_monte_carlo(target_p, n_samples, config, rng)
    g_minus_samples = sample_conductance_monte_carlo(target_m, n_samples, config, rng)
    w_eff_samples = (g_plus_samples - g_minus_samples) / SPAN_S

    return g_plus_samples, g_minus_samples, w_eff_samples


def run_variation_extract() -> dict[str, Any]:
    """Run deterministic statistical characterization and emit extract JSON."""
    cfg = VariationConfig(seed=DEFAULT_SEED)
    rng = np.random.default_rng(cfg.seed)

    # 1. Sweep across 16 discrete states: evaluate empirical vs theoretical mean & std
    levels = np.linspace(G_MIN_S, G_MAX_S, 2**BITS)
    state_stats = []
    for k, g_nom in enumerate(levels):
        draws = sample_conductance_monte_carlo(g_nom, n_samples=1000, config=cfg, rng=rng)
        empirical_mean = float(np.mean(draws))
        empirical_std = float(np.std(draws))
        expected_std = g_nom * cfg.sigma_total
        state_stats.append({
            "state_index": k,
            "nominal_uS": g_nom * 1e6,
            "empirical_mean_uS": empirical_mean * 1e6,
            "empirical_std_uS": empirical_std * 1e6,
            "expected_std_uS": expected_std * 1e6,
            "mean_error_pct": abs(empirical_mean - g_nom) / g_nom * 100.0,
            "std_error_pct": abs(empirical_std - expected_std) / expected_std * 100.0,
        })

    # 2. Sweep across target signed weights w in [-1.0 .. 1.0]
    weights = np.linspace(-1.0, 1.0, 21)
    weight_stats = []
    for w in weights:
        _, _, w_draws = sample_differential_weight_monte_carlo(float(w), n_samples=1000, config=cfg, rng=rng)
        emp_mean = float(np.mean(w_draws))
        emp_std = float(np.std(w_draws))
        th_std = theoretical_weight_std(float(w), cfg.sigma_total)
        snr_db = 20.0 * np.log10(abs(w) / emp_std) if abs(w) > 1e-4 else 0.0

        weight_stats.append({
            "w_target": float(w),
            "empirical_mean_w": emp_mean,
            "empirical_std_w": emp_std,
            "theoretical_std_w": th_std,
            "std_error_pct": abs(emp_std - th_std) / th_std * 100.0,
            "snr_db": float(snr_db),
        })

    extract = {
        "schema_version": "0.1.0",
        "chapter": "0016-variation",
        "title": "NVM Programming and Read Variation (Monte Carlo)",
        "assumptions": {
            "sigma_prog_rel": cfg.sigma_prog,
            "sigma_read_rel": cfg.sigma_read,
            "sigma_total_rel": cfg.sigma_total,
            "num_monte_carlo_draws": 1000,
            "seed": cfg.seed,
        },
        "state_variation_statistics": state_stats,
        "weight_variation_statistics": weight_stats,
        "summary": {
            "zero_weight_noise_floor_std": theoretical_weight_std(0.0, cfg.sigma_total),
            "full_scale_weight_std": theoretical_weight_std(1.0, cfg.sigma_total),
            "max_sample_mean_error_pct": max(s["mean_error_pct"] for s in state_stats),
            "evidence_class": "assumed",
            "provenance": "1000-trial Monte Carlo sensitivity study with Gaussian programming and read noise",
        },
    }
    return extract


def main() -> None:
    print("Running Chapter 0016 Variation & Monte Carlo Extraction...")
    extract = run_variation_extract()
    out_dir = Path(__file__).resolve().parent.parent.parent / "verification" / "circuit" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "variation-0016-extract.json"
    with open(out_file, "w") as f:
        json.dump(extract, f, indent=2)
    print(f"Committed extract written to {out_file}")
    a = extract["assumptions"]
    s = extract["summary"]
    print(f"  sigma_prog={a['sigma_prog_rel']*100:.1f}% | sigma_read={a['sigma_read_rel']*100:.1f}% | sigma_total={a['sigma_total_rel']*100:.2f}%")
    print(f"  Zero-weight std: {s['zero_weight_noise_floor_std']*100:.3f}% | Full-scale std: {s['full_scale_weight_std']*100:.3f}%")
    print(f"  Max sample mean error: {s['max_sample_mean_error_pct']:.2f}%")


if __name__ == "__main__":
    main()
