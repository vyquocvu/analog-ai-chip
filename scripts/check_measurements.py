"""Validate the physical-build measurements for the 0005 analog neuron.

Reads ``book/0005-one-analog-neuron/measurements.csv`` (fill the ``measured``
column on real hardware with a multimeter) and, for every filled row, compares
the measured value against the hand-calculated ideal within the allowed
tolerance. Rows left blank are reported as "unfilled" and skipped (so you can
incrementally fill and re-run).

Prints a summary ledger (rows, passed, failed, unfilled, max/mean error) and a
fitted output slope, and fails (raises) if any *filled* row is out of tolerance.
This turns the breadboard readings into a measured physical ledger that can be
checked against the simulator's ideal predictions.
"""

import csv
import sys
from pathlib import Path

import numpy as np

VREF = 2.5
WEIGHTS = [0.50, 0.25]
DEFAULT_CSV = (Path(__file__).resolve().parent.parent
               / "book" / "0005-one-analog-neuron" / "measurements.csv")


def expected_for(kind, x1, x2):
    if kind == "vref":
        return VREF
    if kind == "vgnd":
        return VREF  # virtual ground sits at the reference
    if kind == "vout":
        return VREF - (WEIGHTS[0] * (x1 - VREF) + WEIGHTS[1] * (x2 - VREF))
    raise ValueError(f"unknown measurement kind {kind!r}")


def load_rows(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def check(path=DEFAULT_CSV):
    rows = load_rows(path)
    total = len(rows)
    filled = unfilled = passed = failed = 0
    errs = []
    sweep = []

    print(f"{'id':<7}{'kind':<7}{'x1':<6}{'x2':<6}{'exp':>8}{'meas':>8}{'err':>8}{'tol':>6}  status")
    for r in rows:
        kind = r["kind"]
        x1 = float(r["x1"]) if r["x1"] else None
        x2 = float(r["x2"]) if r["x2"] else None
        expected = float(r["expected"])
        tol = float(r["tol"])
        meas_raw = (r["measured"] or "").strip()
        if not meas_raw:
            unfilled += 1
            print(f"{r['id']:<7}{kind:<7}{x1!s:<6}{x2!s:<6}{expected:>8.3f}"
                  f"{'':>8}{'':>8}{tol:>6.2f}  UNFILLED")
            continue
        filled += 1
        measured = float(meas_raw)
        err = abs(measured - expected)
        errs.append(err)
        status = "OK" if err <= tol else "FAIL"
        if err <= tol:
            passed += 1
        else:
            failed += 1
        print(f"{r['id']:<7}{kind:<7}{x1!s:<6}{x2!s:<6}{expected:>8.3f}{measured:>8.3f}"
              f"{err:>8.3f}{tol:>6.2f}  {status}")
        if kind == "vout" and x1 is not None and x2 is not None and abs(x2 - VREF) < 1e-9:
            sweep.append((x1, measured))

    print("-" * 74)
    print(f"summary: {filled} measured, {passed} passed, {failed} failed, {unfilled} unfilled")
    if errs:
        print(f"max |err| = {max(errs):.3f} V, mean |err| = {np.mean(errs):.3f} V")

    if len(sweep) >= 2:
        sweep.sort()
        xs = np.array([p[0] for p in sweep])
        ys = np.array([p[1] for p in sweep])
        slope = float(np.polyfit(xs, ys, 1)[0])
        print(f"fitted slope dVout/dx1 = {slope:.3f} (ideal -{WEIGHTS[0]:.2f})")

    if failed:
        raise SystemExit(f"FAILED: {failed} measurement(s) out of tolerance")

    return {"total": total, "filled": filled, "passed": passed,
            "failed": failed, "unfilled": unfilled}


if __name__ == "__main__":
    check(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV)
    print("measurement check OK")
