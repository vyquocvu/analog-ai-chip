"""Fail-closed SPICE correlation for representative or imported bench data."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class BenchMeasurementPoint:
    """One SPICE/observation pair with explicit evidence provenance."""

    point_id: str
    vin_volts: float
    spice_vout_volts: float
    measured_vout_volts: float
    tolerance_volts: float = 0.010
    testbench_instrument: str = "representative synthetic instrument model"
    evidence_class: str = "assumed"
    instrument_serial: str = ""
    acquired_at: str = ""
    source_sha256: str = ""


@dataclass(frozen=True)
class BenchCorrelationReport:
    """Numerical correlation plus whether it may support measured evidence."""

    sample_count: int
    r_squared: float
    rmse_volts: float
    max_delta_volts: float
    mae_volts: float
    all_within_tolerance: bool
    is_correlation_passed: bool
    supports_measured_evidence: bool
    measurements: list[BenchMeasurementPoint] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def load_bench_measurements(path: Path) -> list[BenchMeasurementPoint]:
    """Load real measurements only when file and instrument provenance exist."""

    raw = path.read_bytes()
    payload = json.loads(raw)
    instrument = payload.get("instrument", {})
    required = ("manufacturer", "model", "serial_number", "acquired_at")
    missing = [name for name in required if not instrument.get(name)]
    if payload.get("evidence_class") != "measured" or missing:
        detail = ", ".join(missing) or "evidence_class=measured"
        raise ValueError(f"measurement provenance is incomplete: {detail}")
    source_hash = hashlib.sha256(raw).hexdigest()
    rows = payload.get("measurements")
    if not isinstance(rows, list) or not rows:
        raise ValueError("measurement file must contain a non-empty measurements list")
    instrument_name = f"{instrument['manufacturer']} {instrument['model']}"
    return [
        BenchMeasurementPoint(
            point_id=str(row["point_id"]),
            vin_volts=float(row["vin_volts"]),
            spice_vout_volts=float(row["spice_vout_volts"]),
            measured_vout_volts=float(row["measured_vout_volts"]),
            tolerance_volts=float(row.get("tolerance_volts", 0.010)),
            testbench_instrument=instrument_name,
            evidence_class="measured",
            instrument_serial=str(instrument["serial_number"]),
            acquired_at=str(instrument["acquired_at"]),
            source_sha256=source_hash,
        )
        for row in rows
    ]


def compute_bench_correlation(points: list[BenchMeasurementPoint]) -> BenchCorrelationReport:
    """Compute statistics without silently upgrading the evidence class."""

    if not points:
        raise ValueError("Cannot compute correlation on empty measurement list.")
    evidence_classes = {point.evidence_class for point in points}
    if len(evidence_classes) != 1:
        raise ValueError("Cannot mix evidence classes in one correlation report.")

    sim_vals = np.array([point.spice_vout_volts for point in points], dtype=np.float64)
    observed_vals = np.array(
        [point.measured_vout_volts for point in points], dtype=np.float64
    )
    tolerances = np.array([point.tolerance_volts for point in points], dtype=np.float64)
    deltas = np.abs(observed_vals - sim_vals)
    max_delta = float(np.max(deltas))
    mae = float(np.mean(deltas))
    rmse = float(np.sqrt(np.mean(deltas**2)))
    ss_total = np.sum((observed_vals - np.mean(observed_vals)) ** 2)
    ss_residual = np.sum((observed_vals - sim_vals) ** 2)
    r_squared = 1.0 - (ss_residual / max(ss_total, 1e-12)) if ss_total > 1e-12 else 1.0
    r_squared = float(np.clip(r_squared, 0.0, 1.0))
    within_tolerance = bool(np.all(deltas <= tolerances))
    numerical_pass = within_tolerance and r_squared >= 0.990 and rmse <= 0.008
    supports_measured = evidence_classes == {"measured"} and all(
        point.instrument_serial and point.acquired_at and point.source_sha256
        for point in points
    )

    return BenchCorrelationReport(
        sample_count=len(points),
        r_squared=round(r_squared, 5),
        rmse_volts=round(rmse, 5),
        max_delta_volts=round(max_delta, 5),
        mae_volts=round(mae, 5),
        all_within_tolerance=within_tolerance,
        is_correlation_passed=numerical_pass,
        supports_measured_evidence=bool(supports_measured and numerical_pass),
        measurements=points,
        metadata={
            "target_r2_min": 0.990,
            "target_rmse_max_v": 0.008,
            "evidence_class": next(iter(evidence_classes)),
            "may_promote_to_measured": bool(supports_measured and numerical_pass),
        },
    )


def generate_representative_bench_dataset() -> list[BenchMeasurementPoint]:
    """Return deterministic representative points; these are not measurements."""

    observations = (2.5008, 2.3762, 2.2515, 2.1264, 2.0019, 1.8768, 1.7516, 1.6263, 1.5012, 1.3759)
    return [
        BenchMeasurementPoint(
            point_id=f"PT{index + 1:02d}",
            vin_volts=index * 0.25,
            spice_vout_volts=2.5 - index * 0.125,
            measured_vout_volts=observed,
        )
        for index, observed in enumerate(observations)
    ]


generate_representative_synthetic_dataset = generate_representative_bench_dataset
