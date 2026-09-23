"""Analytical single-pole crossbar settling estimate using averaged RC totals.

The 1.18 ns baseline and 0.40 ns increment are assumed, not SPICE or measured
parameters. This is not a distributed transient solve or physical verification.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .pex import SPEFNetlist


@dataclass(frozen=True)
class PostLayoutSettlingConfig:
    """Assumed design parameters for an analytical settling estimate."""

    sampling_window_ns: float = 5.0  # 5.0 ns ADC conversion aperture (200 MSPS)
    nominal_source_resistance_ohm: float = 50.0  # DAC driver output impedance
    reram_on_resistance_kohm: float = 10.0  # 10 kOhm HRS/LRS effective impedance
    target_accuracy_pct: float = 99.9  # 99.9% settling for 8-bit precision (<0.1% error)


    def __post_init__(self) -> None:
        if not math.isfinite(self.target_accuracy_pct) or not 0 < self.target_accuracy_pct < 100:
            raise ValueError("target_accuracy_pct must be finite and strictly between 0 and 100")
        if not math.isfinite(self.sampling_window_ns) or self.sampling_window_ns <= 0:
            raise ValueError("sampling_window_ns must be finite and positive")


@dataclass(frozen=True)
class SettlingReport:
    """Post-layout transient settling evaluation report."""

    cell_name: str
    pre_layout_tau_ns: float
    post_layout_tau_ns: float
    settling_90_time_ns: float
    settling_99_9_time_ns: float
    target_accuracy_pct: float
    target_settling_time_ns: float
    settling_degradation_pct: float
    sampling_window_ns: float
    timing_margin_ratio: float
    is_settling_clean: bool
    metadata: dict[str, Any]


def simulate_crossbar_post_layout_settling(
    spef: SPEFNetlist,
    config: PostLayoutSettlingConfig | None = None,
) -> SettlingReport:
    """Estimate single-pole settling; a clean result is not physical signoff."""
    cfg = config or PostLayoutSettlingConfig()

    # Pre-layout baseline RC parameters (intrinsic device capacitance only)
    # C_intrinsic ~ 20 fF per bitline, R_driver ~ 50 Ohm
    c_intrinsic_ff = 20.0
    r_driver_ohm = cfg.nominal_source_resistance_ohm
    pre_layout_tau_ns = 1.18  # 1.18 ns pre-layout baseline DAC + intrinsic settling

    # Post-layout extracted wire and coupling parasitics from SPEF
    avg_wire_r = (spef.total_parasitic_res_ohm / max(1, len(spef.nets)))
    avg_wire_c = (spef.total_parasitic_cap_ff / max(1, len(spef.nets)))

    # Total post-layout effective capacitance (wire + fringe coupling + vias)
    c_eff_total_ff = c_intrinsic_ff + (avg_wire_c * 1.5)

    # Elmore-inspired lumped estimate from averages, not a distributed solve.
    # tau_post = tau_pre + R_driver*C_wire + 0.5*R_wire*C_total + 0.40 ns (assumed)
    delta_elmore_ns = (
        (r_driver_ohm * ((c_eff_total_ff - c_intrinsic_ff) * 1e-15))
        + (0.5 * avg_wire_r * (c_eff_total_ff * 1e-15))
    ) * 1e9 + 0.40

    post_layout_tau_ns = pre_layout_tau_ns + delta_elmore_ns

    # y(t) = 1 - exp(-t/tau), hence t(f) = -tau * log(1-f).
    settle_90_ns = -post_layout_tau_ns * math.log1p(-0.90)
    settle_99_9_ns = -post_layout_tau_ns * math.log1p(-99.9 / 100.0)
    target_settle_ns = -post_layout_tau_ns * math.log1p(-cfg.target_accuracy_pct / 100.0)

    degradation_pct = ((post_layout_tau_ns - pre_layout_tau_ns) / pre_layout_tau_ns) * 100.0
    timing_margin_ratio = cfg.sampling_window_ns / target_settle_ns
    is_settling_clean = target_settle_ns <= cfg.sampling_window_ns

    return SettlingReport(
        cell_name=spef.cell_name,
        pre_layout_tau_ns=pre_layout_tau_ns,
        post_layout_tau_ns=post_layout_tau_ns,
        settling_90_time_ns=settle_90_ns,
        settling_99_9_time_ns=settle_99_9_ns,
        target_accuracy_pct=cfg.target_accuracy_pct,
        target_settling_time_ns=target_settle_ns,
        settling_degradation_pct=degradation_pct,
        sampling_window_ns=cfg.sampling_window_ns,
        timing_margin_ratio=timing_margin_ratio,
        is_settling_clean=is_settling_clean,
        metadata={
            "model": "analytical_single_pole",
            "evidence_class": "assumed",
            "physical_verified": False,
            "assumed_pre_layout_tau_ns": 1.18,
            "assumed_tau_increment_ns": 0.40,
            "avg_wire_resistance_ohm": avg_wire_r,
            "avg_wire_capacitance_ff": avg_wire_c,
            "total_extracted_cap_ff": spef.total_parasitic_cap_ff,
            "total_extracted_res_ohm": spef.total_parasitic_res_ohm,
            "sampling_frequency_mhz": (1.0 / (cfg.sampling_window_ns * 1e-9)) / 1e6,
        },
    )
