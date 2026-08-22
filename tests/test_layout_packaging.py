from analog_layout.packaging import (
    ThermalSpreaderConfig,
    run_package_thermal_signoff,
)


def test_fcbga676_ball_map_and_substrate() -> None:
    report = run_package_thermal_signoff()

    # 1. BGA Ball Map Allocations
    assert report.is_package_compliant is True
    assert report.ball_map.total_balls == 676
    assert report.ball_map.vss_ground_balls == 230
    assert report.ball_map.vdd_dig_core_balls == 140
    assert report.ball_map.vdd_ana_analog_balls == 90
    assert report.ball_map.pcie_gen5_serdes_balls == 64

    # 2. 4-2-4 Organic Substrate Stackup
    assert report.substrate_config.layer_count == 10
    assert report.substrate_config.single_ended_impedance_ohm == 50.0
    assert report.substrate_config.differential_impedance_pcie_ohm == 85.0


def test_thermal_heat_spreader_and_junction_temperature() -> None:
    report = run_package_thermal_signoff()

    # 1. Thermal Resistance Metrics
    assert report.is_thermal_compliant is True
    assert report.theta_ja_c_per_w < 1.80
    assert report.theta_jc_c_per_w < 0.15

    # 2. Peak Junction Temperature (<85C at 23.2W TDP)
    assert report.peak_junction_temp_c < 85.0
    assert report.peak_junction_temp_c < 70.0  # ~67.5°C
    assert report.thermal_margin_c > 15.0


def test_thermal_catches_insufficient_cooling() -> None:
    hot_config = ThermalSpreaderConfig(
        tim1_conductivity_w_per_mk=0.50,  # Poor thermal paste
        chip_tdp_w=150.0,  # Extreme power overload
    )
    report = run_package_thermal_signoff(thm_cfg=hot_config)
    assert report.is_thermal_compliant is False
    assert report.peak_junction_temp_c > 85.0
