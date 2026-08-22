from analog_layout.carrier_pcb import (
    PCIeSignalIntegrityConfig,
    run_carrier_pcb_signoff,
)


def test_carrier_pcb_stackup_and_vrm() -> None:
    report = run_carrier_pcb_signoff()

    # 1. PCB Stackup & Form Factor
    assert report.is_pcb_compliant is True
    assert report.stackup_config.layer_count == 12
    assert report.stackup_config.single_ended_impedance_ohm == 50.0
    assert report.stackup_config.differential_impedance_pcie_ohm == 85.0

    # 2. Multi-Phase VRM Power Delivery
    assert report.is_vrm_compliant is True
    assert report.vrm_config.output_voltage_ripple_mv_pp < 10.0
    assert report.vrm_config.transient_step_response_mv < 25.0
    assert report.vrm_config.vrm_efficiency_pct >= 90.0


def test_pcie_gen5_signal_integrity_and_eye_diagram() -> None:
    report = run_carrier_pcb_signoff()

    # 1. Insertion Loss Margin
    assert report.is_signal_integrity_compliant is True
    assert report.pcie_config.insertion_loss_db > report.pcie_config.insertion_loss_limit_db
    assert report.insertion_loss_margin_db > 15.0  # >15 dB margin

    # 2. Eye Opening Compliance (32 GT/s at BER = 1e-12)
    assert report.pcie_config.eye_height_mv >= 30.0
    assert report.eye_height_margin_mv > 150.0
    assert report.pcie_config.eye_width_ui >= 0.30
    assert report.eye_width_margin_ui > 0.25

    # 3. Full Carrier Readiness
    assert report.is_carrier_ready is True


def test_pcie_catches_excessive_channel_loss() -> None:
    lossy_pcie = PCIeSignalIntegrityConfig(
        insertion_loss_db=-35.0,  # Below -28 dB specification limit
        eye_height_mv=15.0,  # Below 30 mV minimum
    )
    report = run_carrier_pcb_signoff(pcie_cfg=lossy_pcie)
    assert report.is_signal_integrity_compliant is False
    assert report.is_carrier_ready is False
