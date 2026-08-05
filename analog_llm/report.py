"""Text report for an analog-LLM simulation run."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from .transformer import Metrics


def token_agreement(
    ideal: Sequence[int], measured: Sequence[int]
) -> float:
    """Fraction of positions where the measured tokens match the float baseline."""
    i = np.asarray(ideal, dtype=int)
    m = np.asarray(measured, dtype=int)
    if i.size == 0:
        return 1.0
    return float(np.mean(i[-m.size:] == m))


def max_abs_logit_error(
    float_logits: np.ndarray, analog_logits: np.ndarray
) -> float:
    if float_logits.shape != analog_logits.shape:
        raise ValueError("logits shapes must match")
    return float(np.max(np.abs(analog_logits - float_logits)))


def format_report(
    config_desc: dict[str, object],
    metrics: Metrics | None,
    accuracy: dict[str, float] | None,
    tiles_used: int | None = None,
) -> str:
    """Render a plain-text report showing architecture, metrics, accuracy."""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("ANALOG LLM ACCELERATOR - SIMULATION REPORT")
    lines.append("=" * 60)
    lines.append("Configuration")
    for k, v in config_desc.items():
        lines.append(f"  {k}: {v}")
    if metrics is not None:
        lines.append("")
        lines.append("Physical ledger (per run)")
        lines.append(f"  analog MACs executed : {metrics.macs}")
        lines.append(f"  tile MVM cycles      : {metrics.cycles}")
        lines.append(f"  tile rewrites        : {metrics.rewrites}")
        lines.append(f"  tile programs        : {metrics.programs}")
    if tiles_used is not None:
        lines.append(f"  tiles used           : {tiles_used}")
    if accuracy:
        lines.append("")
        lines.append("Accuracy vs float baseline")
        for k, v in accuracy.items():
            lines.append(f"  {k}: {v:.4f}")
    lines.append("=" * 60)
    return "\n".join(lines)
