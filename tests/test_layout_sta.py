from analog_layout.sta import (
    TimingPath,
    run_static_timing_analysis,
)


def test_multi_corner_sta_signoff() -> None:
    report = run_static_timing_analysis()

    # 1. PVT Corner Coverage
    assert len(report.corners_evaluated) == 3
    assert "TT_1p0V_25C" in report.corners_evaluated
    assert "SS_0p9V_125C" in report.corners_evaluated
    assert "FF_1p1V_m40C" in report.corners_evaluated

    # 2. Timing Slack Signoff (Zero Violations)
    assert report.is_timing_clean is True
    assert report.wns_setup_ps == 0.0
    assert report.wns_hold_ps == 0.0
    assert report.tns_setup_ps == 0.0
    assert report.tns_hold_ps == 0.0

    # 3. Minimum Slacks across worst corners
    assert report.worst_setup_slack_ps > 100.0  # >100 ps setup slack on NoC 1GHz
    assert report.worst_hold_slack_ps > 10.0  # >10 ps hold slack on fast corner

    # 4. CDC Reliability Check
    assert report.metadata["cdc_synchronizer_mtbf_years"] > 1e8


def test_sta_catches_setup_violation() -> None:
    # Inject a failing path with 1200 ps delay on a 1000 ps clock period
    violating_path = TimingPath(
        name="INJECTED_FAILING_ARBITER",
        clock_domain="CLK_NOC",
        start_point="REG_A",
        end_point="REG_B",
        logic_depth=20,
        comb_delay_nominal_ps=1200.0,
        cell_setup_time_ps=50.0,
        cell_hold_time_ps=20.0,
    )

    report = run_static_timing_analysis(paths=[violating_path])
    assert report.is_timing_clean is False
    assert report.wns_setup_ps > 0.0
    assert report.tns_setup_ps > 0.0
