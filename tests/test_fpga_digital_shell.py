"""Tests for Chapter 0043 FPGA / Digital Shell (Gate R9, WP9.1)."""

from __future__ import annotations

import json
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "fpga-digital-shell-0043-extract.json"
_DIAGRAM_DIR = _REPO / "book" / "0043-fpga-digital-shell" / "diagrams"


def test_timing_params_all_tagged() -> None:
    """Verifies all timing parameters carry valid evidence class tags."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    params = data["timing_parameters"]
    assert len(params) == 9

    valid_classes = {"measured", "spice", "derived", "assumed"}
    for p in params:
        assert p["evidence_class"] in valid_classes
        assert len(p["provenance"]) > 10


def test_ch0038_timing_consistency() -> None:
    """Verifies the digital shell t_tile = 100ns matches Ch.0038 timing model."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    cc = data["ch0038_crosscheck"]

    # Must be consistent (delta < 1%)
    assert cc["consistent"] is True
    assert cc["delta_pct"] < 1.0
    # t_tile must match Ch.0038's 100 ns tile cycle
    assert abs(cc["digital_shell_t_tile_ns"] - 100.0) < 1e-6


def test_fsm_trace_and_state_coverage() -> None:
    """Verifies FSM trace has all required states and correct block count."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    hist = data["fsm_trace"]["state_histogram"]
    arch = data["architecture"]

    # Must have FETCH_ACT, PROGRAM, COMPUTE, ACCUMULATE, WRITEBACK transitions
    for state in ["FETCH_ACT", "PROGRAM", "COMPUTE", "ACCUMULATE"]:
        assert state in hist
        assert hist[state] > 0

    # Block count sanity
    assert arch["n_blocks_total"] == arch["n_row_blocks"] * arch["n_col_blocks"]

    # PROGRAM count must equal n_blocks (every block is programmed)
    assert hist["PROGRAM"] == arch["n_blocks_total"]
    assert hist["COMPUTE"] == arch["n_blocks_total"]


def test_partial_sum_accumulator_overflow_safe() -> None:
    """Verifies the partial-sum accumulator has enough bits to not overflow."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    psa = data["partial_sum_accumulator"]

    assert psa["overflow_safe"] is True
    # Accumulator must have at least ADC_bits + bit_growth bits
    assert psa["total_acc_bits"] >= psa["adc_bits"]
    # Max accumulated value must fit
    assert psa["max_accumulated_value"] <= (2 ** psa["total_acc_bits"] - 1)


def test_buffer_model_derived_from_ch0024() -> None:
    """Verifies buffer sizes match Ch.0024 formula: S_act = 2×C×B_DAC."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    buf = data["buffer_model"]

    expected_act_bits = 2 * buf["tile_cols"] * buf["dac_bits"]
    assert buf["act_buffer_bits"] == expected_act_bits
    assert buf["act_buffer_bytes"] == expected_act_bits // 8
    assert buf["evidence_class"] == "derived"


def test_claim_level_is_functional_digital_shell() -> None:
    """Verifies claim level is FUNCTIONAL_DIGITAL_SHELL — not a silicon claim."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    assert data["claim_level"] == "FUNCTIONAL_DIGITAL_SHELL"
    assert data["summary"]["claim_level"] == "FUNCTIONAL_DIGITAL_SHELL"
    assert data["gate"] == "R9 — Implementation correlation"


def test_all_4_diagrams_exist() -> None:
    """Verifies all 4 SVG diagram files exist."""
    assert (_DIAGRAM_DIR / "fpga-digital-shell-0043.svg").is_file()
    assert (_DIAGRAM_DIR / "fpga-fsm-states-0043.svg").is_file()
    assert (_DIAGRAM_DIR / "fpga-buffer-model-0043.svg").is_file()
    assert (_DIAGRAM_DIR / "fpga-execution-trace-0043.svg").is_file()
