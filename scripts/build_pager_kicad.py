"""Validate and export the Pager-1 Rev A KiCad release deterministically."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROJECT = REPO / "kicad" / "pager-carrier-rev-a"
STEM = PROJECT / "pager-carrier-rev-a"
DEFAULT_OUTPUT = REPO / "build" / "kicad" / "pager-carrier-rev-a"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(cli: Path, args: list[str], cwd: Path) -> None:
    subprocess.run([str(cli), *args], cwd=cwd, check=True)


def resolve_cli(value: str | None) -> Path:
    candidate = value or os.environ.get("KICAD_CLI") or shutil.which("kicad-cli")
    if not candidate:
        raise SystemExit("KiCad CLI not found; pass --kicad-cli or set KICAD_CLI")
    path = Path(candidate).resolve()
    version = subprocess.run(
        [str(path), "version", "--format", "plain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not version.startswith("10.0."):
        raise SystemExit(f"KiCad 10.0.x required, found {version!r}")
    return path


def validate_bom(path: Path) -> None:
    manifest = json.loads((PROJECT / "hardware-manifest.json").read_text())
    expected = {item["reference"]: item for item in manifest["bom"]}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    refs: list[str] = []
    for row in rows:
        row_refs = row["Reference"].split(",")
        refs.extend(row_refs)
        for ref in row_refs:
            if ref not in expected:
                raise ValueError(f"unexpected BOM reference {ref}")
            item = expected[ref]
            if not item["mpn"] or not item["footprint"]:
                raise ValueError(f"manifest BOM metadata incomplete for {ref}")
            if row.get("MPN") != item["mpn"] or row.get("Manufacturer") != item["manufacturer"]:
                raise ValueError(f"exported manufacturer metadata differs for {ref}")
        if row.get("DNP", "").strip().lower() in {"1", "true", "yes"}:
            raise ValueError(f"unexplained DNP item: {row['Reference']}")
    if len(refs) != len(set(refs)):
        raise ValueError("duplicate BOM references")
    missing = sorted(set(expected) - set(refs))
    if missing:
        raise ValueError(f"BOM is missing references: {', '.join(missing)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kicad-cli")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    cli = resolve_cli(args.kicad_cli)
    output = args.output.resolve()
    if output.exists():
        shutil.rmtree(output)
    (output / "gerbers").mkdir(parents=True)
    staged_project = output / "project"
    shutil.copytree(PROJECT, staged_project)

    sch = f"{STEM.name}.kicad_sch"
    pcb = f"{STEM.name}.kicad_pcb"
    run(cli, ["sch", "erc", "--format", "json", "--severity-all", "--exit-code-violations", "--output", str(output / "erc.json"), sch], staged_project)
    run(cli, ["pcb", "drc", "--schematic-parity", "--refill-zones", "--save-board", "--format", "json", "--severity-all", "--exit-code-violations", "--output", str(output / "drc.json"), pcb], staged_project)
    run(cli, ["sch", "export", "bom", "--fields", "Reference,Value,Footprint,Manufacturer,MPN,DNP", "--labels", "Reference,Value,Footprint,Manufacturer,MPN,DNP", "--output", str(output / "bom.csv"), sch], staged_project)
    validate_bom(output / "bom.csv")
    run(cli, ["sch", "export", "pdf", "--output", str(output / "schematic.pdf"), sch], staged_project)
    run(cli, ["pcb", "export", "gerbers", "--check-zones", "--layers", "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts", "--output", str(output / "gerbers"), pcb], staged_project)
    run(cli, ["pcb", "export", "drill", "--output", str(output / "gerbers"), pcb], staged_project)
    run(cli, ["pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both", "--output", str(output / "positions.csv"), pcb], staged_project)
    run(cli, ["pcb", "export", "pdf", "--layers", "F.Cu,In1.Cu,In2.Cu,B.Cu,Edge.Cuts", "--output", str(output / "pcb.pdf"), pcb], staged_project)
    run(cli, ["pcb", "export", "step", "--subst-models", "--output", str(output / "board.step"), pcb], staged_project)
    run(cli, ["pcb", "render", "--side", "top", "--quality", "high", "--output", str(output / "board-top.png"), pcb], staged_project)
    run(cli, ["pcb", "render", "--side", "bottom", "--quality", "high", "--output", str(output / "board-bottom.png"), pcb], staged_project)

    files = sorted(
        path for path in output.rglob("*") if path.is_file() and staged_project not in path.parents
    )
    relative_paths = {path.relative_to(output).as_posix() for path in files}
    required_paths = {
        "board-bottom.png",
        "board-top.png",
        "board.step",
        "bom.csv",
        "drc.json",
        "erc.json",
        "pcb.pdf",
        "positions.csv",
        "schematic.pdf",
        "gerbers/pager-carrier-rev-a-Edge_Cuts.gm1",
        "gerbers/pager-carrier-rev-a.drl",
    }
    missing_outputs = sorted(required_paths - relative_paths)
    if missing_outputs:
        raise ValueError(f"manufacturing release is incomplete: {', '.join(missing_outputs)}")
    release = {
        "schema_version": 1,
        "design": "pager-carrier-rev-a",
        "evidence_class": "kicad_design_erc_drc_verified",
        "limitations": [
            "not fabricated or assembled",
            "controlled impedance is assumed pending fabricator stackup or coupon measurement",
            "no bench-correlation or hardware-measured evidence",
        ],
        "files": [
            {
                "path": path.relative_to(output).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in files
        ],
    }
    release_path = output / "release-manifest.json"
    release_path.write_text(
        json.dumps(release, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    recorded = json.loads(release_path.read_text(encoding="utf-8"))["files"]
    if any(sha256(output / item["path"]) != item["sha256"] for item in recorded):
        raise ValueError("release-manifest hash verification failed")
    print(f"Pager KiCad release written to {output}")


if __name__ == "__main__":
    main()
