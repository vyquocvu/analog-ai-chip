from analog_layout.dynamic_power_em import (
    ElectromigrationParameters,
    run_dynamic_power_em_signoff,
)


def test_dynamic_power_resonance_and_ssn_signoff() -> None:
    report = run_dynamic_power_em_signoff()

    # 1. PDN Resonance Frequency (>2.5 GHz, far above 1.0 GHz NoC clock)
    assert report.is_pdn_clean is True
    assert report.resonance_frequency_ghz > 2.50
    assert report.frequency_margin_ratio >= 2.50
    assert report.peak_anti_resonance_impedance_mohm < 100.0

    # 2. Dynamic SSN (L*di/dt + IR) Noise (<50 mV / 5% of VDD)
    assert report.total_dynamic_voltage_drop_mv < 50.0
    assert report.dynamic_drop_pct_of_vdd < 5.0
    assert report.inductive_bounce_mv < 20.0


def test_electromigration_lifetime_signoff() -> None:
    report = run_dynamic_power_em_signoff()

    # 1. Peak Current Density (<1.50 mA/um limit)
    assert report.is_em_clean is True
    assert report.max_current_density_ma_per_um < 1.50
    assert report.em_safety_margin_ratio >= 2.0

    # 2. Black's Equation Projected Lifetime (>= 10.0 Years at 105C)
    assert report.projected_mttf_years >= 10.0


def test_em_catches_excessive_current_density() -> None:
    strict_em = ElectromigrationParameters(
        current_density_limit_ma_per_um=0.30,  # Below operating 0.42 mA/um
        target_lifetime_years=100.0,
    )
    report = run_dynamic_power_em_signoff(em_params=strict_em)
    assert report.is_em_clean is False
