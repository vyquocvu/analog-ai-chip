import json
import math
import runpy
from pathlib import Path

import pytest

from analog_layout.pex import PEXTechnologyProfile, SPEFNetlist, extract_spef_from_cell
from analog_layout.post_layout_sim import (
    PostLayoutSettlingConfig,
    simulate_crossbar_post_layout_settling,
)
from analog_layout.reram_macro import ReRAMArrayConfig, generate_reram_macro_cell


def test_spef_parasitic_extraction() -> None:
    cell = generate_reram_macro_cell(ReRAMArrayConfig(rows=16, cols=16))
    profile = PEXTechnologyProfile()
    spef = extract_spef_from_cell(cell, profile)

    assert spef.cell_name == "reram_macro_16x16"
    assert len(spef.nets) > 30  # Wordlines, Bitlines, Dummy nets
    assert spef.total_parasitic_cap_ff > 10.0
    assert spef.total_parasitic_res_ohm > 50.0

    spef_text = spef.to_spef_string()
    assert "*SPEF" in spef_text
    assert "*D_NET" in spef_text
    assert "*DESIGN \"reram_macro_16x16\"" in spef_text


def test_post_layout_crossbar_settling_and_margin() -> None:
    cell = generate_reram_macro_cell(ReRAMArrayConfig(rows=16, cols=16))
    spef = extract_spef_from_cell(cell)
    cfg = PostLayoutSettlingConfig(sampling_window_ns=5.0)

    report = simulate_crossbar_post_layout_settling(spef, cfg)

    # First-order 99.9% settling takes ln(1000) tau, not 1.55 tau.
    assert report.settling_99_9_time_ns == pytest.approx(10.9146, abs=0.001)
    assert report.is_settling_clean is False

    assert report.timing_margin_ratio == pytest.approx(5.0 / report.settling_99_9_time_ns)
    assert report.sampling_window_ns == 5.0

    # 3. Degradation quantification (+10% to +50% due to post-layout parasitics)
    assert 10.0 <= report.settling_degradation_pct <= 50.0


def test_single_pole_settling_identity() -> None:
    # Zero wire RC leaves the assumed 1.18 + 0.40 = 1.58 ns tau.
    report = simulate_crossbar_post_layout_settling(SPEFNetlist("zero_rc"))
    assert report.post_layout_tau_ns == pytest.approx(1.58)
    assert report.settling_90_time_ns == pytest.approx(1.58 * math.log(10))
    assert report.settling_99_9_time_ns == pytest.approx(1.58 * math.log(1000))
    for fraction, time in [(0.9, report.settling_90_time_ns),
                           (0.999, report.settling_99_9_time_ns)]:
        assert 1 - math.exp(-time / report.post_layout_tau_ns) == pytest.approx(fraction)


@pytest.mark.parametrize("accuracy", [50.0, 90.0, 99.9, 99.99])
def test_configured_target_controls_margin(accuracy: float) -> None:
    report = simulate_crossbar_post_layout_settling(
        SPEFNetlist("zero_rc"), PostLayoutSettlingConfig(target_accuracy_pct=accuracy)
    )
    expected = -1.58 * math.log1p(-accuracy / 100)
    assert report.target_settling_time_ns == pytest.approx(expected)
    assert report.target_accuracy_pct == accuracy
    assert report.timing_margin_ratio == pytest.approx(5 / expected)
    assert report.is_settling_clean is (expected <= 5)
    assert report.settling_90_time_ns == pytest.approx(1.58 * math.log(10))
    assert report.settling_99_9_time_ns == pytest.approx(1.58 * math.log(1000))


@pytest.mark.parametrize("factor, clean", [(1.0, True), (0.999, False), (1.001, True)])
def test_sampling_aperture_boundary(factor: float, clean: bool) -> None:
    spef = SPEFNetlist("zero_rc")
    target = simulate_crossbar_post_layout_settling(spef).settling_99_9_time_ns
    report = simulate_crossbar_post_layout_settling(
        spef, PostLayoutSettlingConfig(sampling_window_ns=target * factor)
    )
    assert report.is_settling_clean is clean
    assert report.timing_margin_ratio == pytest.approx(factor)


@pytest.mark.parametrize("accuracy", [0, -1, 100, 101, math.nan, math.inf, -math.inf])
def test_config_rejects_invalid_accuracy(accuracy: float) -> None:
    with pytest.raises(ValueError, match="target_accuracy_pct"):
        PostLayoutSettlingConfig(target_accuracy_pct=accuracy)


@pytest.mark.parametrize("aperture", [0, -1, math.nan, math.inf, -math.inf])
def test_config_rejects_invalid_aperture(aperture: float) -> None:
    with pytest.raises(ValueError, match="sampling_window_ns"):
        PostLayoutSettlingConfig(sampling_window_ns=aperture)


def test_chapter_extract_is_assumed_and_deterministic(tmp_path: Path, monkeypatch) -> None:
    chapter = Path(__file__).resolve().parents[1] / "book/0063-post-layout-parasitic-extraction"
    extract = runpy.run_path(str(chapter / "parasitic_extraction.py"))[
        "run_parasitic_extraction_extract"
    ]
    monkeypatch.setitem(extract.__globals__, "RESULTS_DIR", tmp_path)
    monkeypatch.setitem(extract.__globals__, "RESULT_PATH", tmp_path / "extract.json")
    first = extract()
    assert first == extract() == json.loads((tmp_path / "extract.json").read_text())
    assert first["status"] == "FAILED"
    assert first["claim_level"] == "analytical_single_pole"
    assert first["evidence_class"] == "assumed"
    assert first["physical_verified"] is False
    result = first["transient_settling_signoff"]
    assert result["target_accuracy_pct"] == 99.9
    assert result["target_settling_time_ns"] == result["settling_99_9_time_ns"]
