r"""Chapter 0019 — Conductance Drift, Stuck-at Faults & I-V Non-Linearity.

Models three distinct long-term and physical non-idealities in non-volatile memory crossbars:

1. **Temporal Conductance Drift (Retention Relaxation)**:
   In PCM and ReRAM devices, structural relaxation causes conductance to decay over time:
       G(t) = G(t_0) \cdot \left(\frac{t}{t_0}\right)^{-\nu(G_0)}, \quad t \ge t_0 = 1\text{ s}
   where the drift exponent $\nu(G_0) \in [0.02, 0.06]$ depends on the programmed state.
   Over retention times ($1\text{ s} \to 10^7\text{ s} \approx 1\text{ year}$), weights
   systematically decay towards lower conductance states.

2. **Stuck-at Faults (Defect Distributions & Yield)**:
   Manufacturing defects lock certain cells into permanent conductance states:
   - **Stuck-at-HRS ($p_{HRS} \approx 1\% \dots 5\%$)**: Cell fixed at $G_{min} = 10.0\,\mu\text{S}$ (open defect).
   - **Stuck-at-LRS ($p_{LRS} \approx 0.1\% \dots 1\%$)**: Cell fixed at $G_{max} = 100.0\,\mu\text{S}$ (short defect).
   Stuck-at-LRS defects inject massive static current offsets into affected columns.

3. **I-V Non-Linearity (Poole-Frenkel / Sub-Ohmic Conduction)**:
   At finite read voltages ($|V_{read}| \le 0.25\text{ V}$), conduction deviates from pure Ohm's law:
       I(V) = G_0 \cdot V \cdot (1 + \beta \cdot |V|^2)
   where $\beta \approx 1.0\text{ V}^{-2}$ introduces voltage-dependent cubic current distortion.

Provenance:
- All variation, fault rate, and drift parameters are labeled 'assumed' sensitivity parameters.
- Fixed random seeds ensure deterministic reproducibility.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

# Nominal parameters from Chapter 0015
G_MIN_S = 10.0e-6        # 10 uS (HRS)
G_MAX_S = 100.0e-6       # 100 uS (LRS)
SPAN_S = G_MAX_S - G_MIN_S  # 90 uS
V_READ_MAX = 0.25        # 0.25 V
DEFAULT_SEED = 42


@dataclass(frozen=True)
class DriftConfig:
    """Configuration for temporal conductance drift."""

    nu_min: float = 0.02   # drift exponent at G_min
    nu_max: float = 0.06   # drift exponent at G_max
    t0_s: float = 1.0      # reference programming time (1 s)

    def nu_for_conductance(self, g0: float) -> float:
        """Calculate state-dependent drift exponent."""
        frac = (np.clip(g0, G_MIN_S, G_MAX_S) - G_MIN_S) / SPAN_S
        return float(self.nu_min + frac * (self.nu_max - self.nu_min))

    def evaluate_drift(self, g0: float, t_seconds: float) -> float:
        """Evaluate drifted conductance at time t (seconds)."""
        t = max(t_seconds, self.t0_s)
        nu = self.nu_for_conductance(g0)
        return float(g0 * (t / self.t0_s) ** (-nu))


@dataclass(frozen=True)
class FaultConfig:
    """Configuration for spatial stuck-at-fault defect injection."""

    p_hrs: float = 0.03    # probability of stuck-at-HRS (3%)
    p_lrs: float = 0.005   # probability of stuck-at-LRS (0.5%)
    seed: int = DEFAULT_SEED

    def inject_faults(self, g_matrix: np.ndarray, rng: np.random.Generator | None = None) -> tuple[np.ndarray, dict[str, int]]:
        """Apply stuck-at faults to a conductance matrix."""
        if rng is None:
            rng = np.random.default_rng(self.seed)

        g_faulty = g_matrix.copy()
        n_total = g_matrix.size
        rand_draws = rng.random(size=g_matrix.shape)

        mask_lrs = rand_draws < self.p_lrs
        mask_hrs = (rand_draws >= self.p_lrs) & (rand_draws < (self.p_lrs + self.p_hrs))

        g_faulty[mask_lrs] = G_MAX_S
        g_faulty[mask_hrs] = G_MIN_S

        counts = {
            "total_cells": int(n_total),
            "stuck_lrs_count": int(np.sum(mask_lrs)),
            "stuck_hrs_count": int(np.sum(mask_hrs)),
        }
        return g_faulty, counts


@dataclass(frozen=True)
class NonLinearConfig:
    """Configuration for I-V non-linearity."""

    beta: float = 1.0  # cubic non-linearity coefficient (1/V^2)

    def current(self, g0: float, v: float) -> float:
        """Calculate non-linear current I(V) = G0 * V * (1 + beta * V^2)."""
        return float(g0 * v * (1.0 + self.beta * (v**2)))


def run_drift_faults_extract() -> dict[str, Any]:
    """Run comprehensive characterization across drift, stuck faults, and non-linearity."""
    drift_cfg = DriftConfig()
    nonlin_cfg = NonLinearConfig()

    # 1. Temporal Drift Characterization across 7 decades of time
    time_points = [1.0, 10.0, 60.0, 3600.0, 86400.0, 1.0e6, 3.15e7]  # 1s to 1 year
    time_labels = ["1s", "10s", "1min", "1hour", "1day", "11.5days", "1year"]

    states_16 = np.linspace(G_MIN_S, G_MAX_S, 16)
    drift_trajectories = []
    for g0 in states_16:
        nu = drift_cfg.nu_for_conductance(g0)
        conductances_t = [drift_cfg.evaluate_drift(g0, t) * 1e6 for t in time_points]
        drift_trajectories.append({
            "initial_uS": float(g0 * 1e6),
            "nu_exponent": float(nu),
            "conductance_over_time_uS": conductances_t,
            "loss_1year_pct": float((g0 * 1e6 - conductances_t[-1]) / (g0 * 1e6) * 100.0),
        })

    # Differential weight decay over time for w in [-1.0, -0.5, 0.0, 0.5, 1.0]
    weights = [-1.0, -0.5, 0.0, 0.5, 1.0]
    weight_drift = []
    for w in weights:
        w_abs = abs(w)
        g_plus_0 = G_MIN_S + w_abs * SPAN_S if w >= 0 else G_MIN_S
        g_minus_0 = G_MIN_S if w >= 0 else G_MIN_S + w_abs * SPAN_S
        w_over_time = []
        for t in time_points:
            gp_t = drift_cfg.evaluate_drift(g_plus_0, t)
            gm_t = drift_cfg.evaluate_drift(g_minus_0, t)
            w_eff_t = (gp_t - gm_t) / SPAN_S
            w_over_time.append(float(w_eff_t))
        weight_drift.append({
            "target_w": float(w),
            "w_over_time": w_over_time,
            "w_error_1year_pct": float(abs(w_over_time[-1] - w) * 100.0),
        })

    # 2. Stuck-at Fault Sweep on 32x32 Crossbar Array
    rng = np.random.default_rng(DEFAULT_SEED)
    N = 32
    v_in = rng.uniform(0.0, V_READ_MAX, size=N)
    w_mat = rng.uniform(-1.0, 1.0, size=(N, N))

    # Map target weights to physical (G+, G-) matrices
    g_plus = np.where(w_mat >= 0, G_MIN_S + w_mat * SPAN_S, G_MIN_S)
    g_minus = np.where(w_mat < 0, G_MIN_S + abs(w_mat) * SPAN_S, G_MIN_S)

    i_plus_ideal = g_plus.T @ v_in
    i_minus_ideal = g_minus.T @ v_in
    y_ideal = (i_plus_ideal - i_minus_ideal) / SPAN_S

    fault_rate_sweeps = []
    for p_tot in [0.001, 0.005, 0.01, 0.02, 0.05, 0.10]:
        # 85% HRS faults, 15% LRS faults
        p_hrs = p_tot * 0.85
        p_lrs = p_tot * 0.15
        cfg_f = FaultConfig(p_hrs=p_hrs, p_lrs=p_lrs, seed=DEFAULT_SEED)

        g_p_fault, _ = cfg_f.inject_faults(g_plus, rng)
        g_m_fault, _ = cfg_f.inject_faults(g_minus, rng)

        i_p_fault = g_p_fault.T @ v_in
        i_m_fault = g_m_fault.T @ v_in
        y_fault = (i_p_fault - i_m_fault) / SPAN_S

        mvm_error = float(np.linalg.norm(y_fault - y_ideal) / np.linalg.norm(y_ideal) * 100.0)
        fault_rate_sweeps.append({
            "total_fault_prob": p_tot,
            "p_hrs": p_hrs,
            "p_lrs": p_lrs,
            "mvm_rel_error_pct": mvm_error,
        })

    # 3. Non-Linear I-V Characterization
    voltages = np.linspace(-V_READ_MAX, V_READ_MAX, 25)
    iv_curves = []
    for v in voltages:
        i_lin = G_MAX_S * v
        i_nonlin = nonlin_cfg.current(G_MAX_S, v)
        iv_curves.append({
            "voltage_v": float(v),
            "ideal_ohmic_uA": float(i_lin * 1e6),
            "actual_current_uA": float(i_nonlin * 1e6),
            "distortion_pct": float((i_nonlin - i_lin) / (abs(i_lin) + 1e-15) * 100.0) if abs(v) > 1e-6 else 0.0,
        })

    extract = {
        "schema_version": "0.1.0",
        "chapter": "0019-drift-faults",
        "title": "Conductance Drift, Stuck-at Faults and I-V Non-Linearity",
        "drift_parameters": {
            "nu_min": drift_cfg.nu_min,
            "nu_max": drift_cfg.nu_max,
            "t0_s": drift_cfg.t0_s,
            "time_points_s": time_points,
            "time_labels": time_labels,
        },
        "drift_trajectories_16states": drift_trajectories,
        "weight_drift": weight_drift,
        "fault_parameters": {
            "fault_rate_sweeps": fault_rate_sweeps,
        },
        "non_linear_iv": {
            "beta_v_inv2": nonlin_cfg.beta,
            "iv_curves": iv_curves,
            "max_distortion_at_vread_max_pct": float(nonlin_cfg.beta * (V_READ_MAX**2) * 100.0),
        },
        "summary": {
            "max_drift_loss_1year_pct": max(t["loss_1year_pct"] for t in drift_trajectories),
            "mvm_error_at_1pct_faults_pct": fault_rate_sweeps[2]["mvm_rel_error_pct"],
            "max_iv_distortion_pct": float(nonlin_cfg.beta * (V_READ_MAX**2) * 100.0),
            "evidence_class": "assumed",
            "provenance": "Isolated mathematical compact models for temporal drift, stuck defects, and sub-Ohmic I-V non-linearity",
        },
    }
    return extract


def main() -> None:
    print("Running Chapter 0019 Drift, Stuck-at Faults & Non-Linearity Extraction...")
    extract = run_drift_faults_extract()
    out_dir = Path(__file__).resolve().parent.parent.parent / "verification" / "circuit" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "drift-faults-0019-extract.json"
    with open(out_file, "w") as f:
        json.dump(extract, f, indent=2)
    print(f"Committed extract written to {out_file}")
    s = extract["summary"]
    print(f"  Max Conductance Loss (1 year): {s['max_drift_loss_1year_pct']:.2f}%")
    print(f"  MVM Error @ 1.0% Fault Rate: {s['mvm_error_at_1pct_faults_pct']:.2f}%")
    print(f"  Max I-V Non-Linear Distortion: {s['max_iv_distortion_pct']:.2f}%")


if __name__ == "__main__":
    main()
