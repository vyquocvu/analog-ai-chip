"""Validate the 0005 build data files (no SPICE engine required)."""

import csv
from pathlib import Path

CH = Path(__file__).resolve().parent.parent / "book" / "0005-one-analog-neuron"


def test_bom_csv_is_well_formed() -> None:
    path = CH / "bom.csv"
    with path.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert rows, "bom.csv must have data rows"
    header = set(rows[0].keys())
    for col in ("id", "designator", "value", "qty", "alternates"):
        assert col in header, f"missing column {col}"
    designators = {r["designator"] for r in rows}
    assert {"R1", "R2", "Rf", "U1"}.issubset(designators)
    for r in rows:
        assert int(r["qty"]) >= 1, f"{r['designator']} qty must be >= 1"


def test_build_doc_files_present() -> None:
    for name in ("breadboard.md", "testpoints.md", "calibration.md", "bom.csv"):
        assert (CH / name).is_file(), f"missing {name}"


def test_testpoints_contain_expected_lines() -> None:
    txt = (CH / "testpoints.md").read_text()
    for token in ("TP5", "TP8", "2.5", "Vout"):
        assert token in txt, f"testpoints.md missing {token!r}"


def test_diagram_svgs_exist() -> None:
    diag = CH / "diagrams"
    for name in ("summer.svg", "sweep.svg", "virtual_ground.svg", "full_schematic.svg"):
        assert (diag / name).is_file(), f"missing diagram {name}"
