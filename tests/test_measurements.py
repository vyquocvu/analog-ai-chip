"""Always-on data checks for the 0005 physical-build measurements CSV."""

import csv
import os
import subprocess
import sys
import tempfile
from pathlib import Path

CSV = (Path(__file__).resolve().parent.parent
       / "book" / "0005-one-analog-neuron" / "measurements.csv")
SCRIPT = (Path(__file__).resolve().parent.parent / "scripts" / "check_measurements.py")
VREF = 2.5
WEIGHTS = [0.50, 0.25]


def test_csv_structure_and_expected() -> None:
    with open(CSV, newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert rows, "measurements.csv must not be empty"
    fields = {"id", "kind", "x1", "x2", "expected", "tol", "measured", "note"}
    for r in rows:
        assert fields <= set(r.keys()), f"row {r['id']} missing fields"
        kind = r["kind"]
        if kind == "vout":
            expected = VREF - (WEIGHTS[0] * (float(r["x1"]) - VREF)
                               + WEIGHTS[1] * (float(r["x2"]) - VREF))
            assert abs(float(r["expected"]) - expected) < 1e-9
        else:
            assert abs(float(r["expected"]) - VREF) < 1e-9


def test_checker_runs_on_unfilled_without_failing() -> None:
    # the committed file has blank 'measured' -> skipped, never a hard failure
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parent.parent)
    r = subprocess.run([sys.executable, str(SCRIPT), str(CSV)],
                       capture_output=True, text=True, env=env, check=False)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "unfilled" in r.stdout.lower()


def test_checker_passes_a_filled_in_tolerance_run() -> None:
    with open(CSV, newline="") as fh:
        rows = list(csv.DictReader(fh))
    vals = {"REF": 2.50, "VNODE": 2.50, "OUT0": 2.50, "OUTP": 2.35,
            "OUTN": 2.73, "SW1": 2.25, "SW2": 2.75}
    filled = {r["id"]: vals[r["id"]] for r in rows}
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        for r in rows:
            r["measured"] = str(filled[r["id"]])
            w.writerow(r)
        path = f.name
    try:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(Path(__file__).resolve().parent.parent)
        r = subprocess.run([sys.executable, str(SCRIPT), path],
                           capture_output=True, text=True, env=env, check=False)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "0 failed" in r.stdout
    finally:
        os.unlink(path)
