"""Tests for Chapter 0037 Hardware-Aware Recovery."""

from __future__ import annotations

import json
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "hardware-recovery-0037-extract.json"
_DIAGRAM_DIR = _REPO / "book" / "0037-hardware-recovery" / "diagrams"


def test_recovery_stages_structure() -> None:
    """Verifies that all 4 recovery stages exist with complete metrics."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    stages = data["recovery_stages"]
    assert len(stages) == 4

    names = [s["stage_name"] for s in stages]
    assert "Stage 0: Raw Analog Baseline" in names[0]
    assert "Stage 1: Post-ADC Affine Calibration" in names[1]
    assert "Stage 2: Defect-Aware Column Remapping" in names[2]
    assert "Stage 3: Closed-Loop Weight Adaptation" in names[3]

    for s in stages:
        assert len(s["active_mitigations"]) >= 1
        assert s["perplexity"] > 0.0
        assert s["cross_entropy"] > 0.0


def test_perplexity_recovery_trend() -> None:
    """Verifies that full 3-stage recovery achieves lower perplexity than raw analog."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    s0 = data["recovery_stages"][0]
    s3 = data["recovery_stages"][3]

    assert s3["perplexity"] < s0["perplexity"], "Stage 3 should recover lower perplexity than uncalibrated Stage 0"
    assert data["recovery_summary"]["perplexity_recovery_delta"] > 0.0


def test_extract_and_all_4_diagrams_exist() -> None:
    """Verifies extract schema and all 4 SVG diagram files exist."""
    assert _EXTRACT.is_file()
    extract = json.loads(_EXTRACT.read_text("utf-8"))
    assert extract["gate"] == "R7 — Transformer and LLM validation"
    assert extract["chapter"] == "0037-hardware-recovery"
    assert extract["model_config"]["total_physical_tiles"] == 416

    assert (_DIAGRAM_DIR / "hardware-recovery-0037.svg").is_file()
    assert (_DIAGRAM_DIR / "hardware-recovery-pipeline-0037.svg").is_file()
    assert (_DIAGRAM_DIR / "hardware-recovery-parity-0037.svg").is_file()
    assert (_DIAGRAM_DIR / "hardware-recovery-hardware-0037.svg").is_file()
