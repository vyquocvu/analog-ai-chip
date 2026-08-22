from analog_layout.pex import PEXTechnologyProfile, extract_spef_from_cell
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

    # 1. Settling time check (<2.5 ns for 99.9% settling)
    assert report.settling_99_9_time_ns < 2.50
    assert report.is_settling_clean is True

    # 2. Timing margin check (>2.0x against 5.0 ns ADC window)
    assert report.timing_margin_ratio >= 2.0
    assert report.sampling_window_ns == 5.0

    # 3. Degradation quantification (+10% to +50% due to post-layout parasitics)
    assert 10.0 <= report.settling_degradation_pct <= 50.0
