
from analog_llm import Metrics
from analog_llm.report import format_report

REQUIRED_LEDGER = ("macs", "cycles", "rewrites", "programs")


def test_frozen_report_has_all_required_fields() -> None:
    m = Metrics(macs=1000, cycles=7, rewrites=3, programs=12)
    report = format_report(
        {"model": "tiny"}, m,
        {"token agreement": 0.9, "max |logit error|": 0.01},
        tiles_used=2,
    )
    low = report.lower()
    for k in ("analog macs", "tile mvm cycles", "tile rewrites", "tile programs"):
        assert k in low, f"report missing frozen ledger field {k!r}"
    for k in ("token agreement", "max |logit error|"):
        assert k in report, f"report missing frozen accuracy field {k!r}"


def test_no_metrics_report_still_has_accuracy() -> None:
    report = format_report({"model": "tiny"}, None, {"token agreement": 1.0})
    assert "token agreement" in report
