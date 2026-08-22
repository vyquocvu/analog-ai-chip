from analog_llm.decision_report import (
    FeasibilityStatus,
    generate_integrated_decision_report,
)


def test_integrated_architecture_report_decisions() -> None:
    report = generate_integrated_decision_report()
    decisions = report.tier_decisions

    assert "T0" in decisions
    assert "T1" in decisions
    assert "T2" in decisions
    assert "T3" in decisions

    # T0 must be FEASIBLE with GO verdict
    t0 = decisions["T0"]
    assert t0.status == FeasibilityStatus.FEASIBLE
    assert t0.verdict == "GO"
    assert t0.die_count == 1
    assert t0.decode_tokens_per_second > 100000.0

    # T1 must be CONDITIONAL
    t1 = decisions["T1"]
    assert t1.status == FeasibilityStatus.CONDITIONAL
    assert t1.verdict == "CONDITIONAL_GO"
    assert len(t1.required_evidence_for_promotion) > 0

    # T2 & T3 must be INFEASIBLE for stationary analog IMC
    t2 = decisions["T2"]
    assert t2.status == FeasibilityStatus.INFEASIBLE
    assert t2.verdict == "NO_GO"

    t3 = decisions["T3"]
    assert t3.status == FeasibilityStatus.INFEASIBLE
    assert t3.verdict == "NO_GO"


def test_tapeout_target_recommendation_specification() -> None:
    report = generate_integrated_decision_report()
    target = report.tapeout_target

    assert target.target_tier == "T0_GPT2_124M"
    assert "28nm" in target.process_technology
    assert target.die_size_mm2 <= 400.0  # Fits within single reticle limit
    assert target.decode_energy_uj_per_token > 0.0
    assert len(target.risk_assessment) >= 3
