# Pager-1 Carrier Rev A

This directory contains the editable KiCad 10 source for the 70 mm × 52 mm,
four-layer Pager-1 main carrier. The display, keypad, protected Li-Po pack, and
analog accelerator are external assemblies.

## Evidence boundary

Status: `INCOMPLETE_CARRIER_DESIGN`. Do not fabricate this placeholder as a
working product. Subsystem sheets contain text only, most components are
unconnected, and generated footprints do not implement the declared packages.
The BOM lacks the PMIC inductor and capacitors. Clean ERC/DRC on passive,
no-connect symbols does not establish electrical completeness.

The historical evidence record omits subsheets and local libraries and is now
rejected by the source-inventory check. Manufacturing export is also blocked by
BOM footprint mismatches. The preliminary impedance estimate remains `assumed`.
See `SOURCE_NOTES.md` for manufacturer references; startup and pin assignments
still require circuit implementation and verification.

The authoritative electrical/mechanical contract is
`hardware-manifest.json`. In particular, pins named `NC_RESERVED_*` must not be
connected and pins named `TEST_ONLY_*` are diagnostic inputs, not production
interfaces.

## Project files

- `pager-carrier-rev-a.kicad_pro`: project settings.
- `pager-carrier-rev-a.kicad_sch`: hierarchy overview.
- `power.kicad_sch`, `host.kicad_sch`, `display.kicad_sch`,
  `input-haptics.kicad_sch`, `accelerator-mezzanine.kicad_sch`: subsystem
  text-only placeholder sheets.
- `pager-carrier-rev-a.kicad_pcb`: partially routed placeholder layout.
- `pager-carrier-rev-a.kicad_dru`: project design rules.
- `Pager.kicad_sym`, `Pager.pretty/`, and the library tables: project-local
  source for the custom connector symbol and land pattern. Project schematics
  and the routed board also embed their generated library copies.

## Validation and manufacturing exports

KiCad 10.0.x is required. Run:

```bash
python scripts/build_pager_kicad.py --kicad-cli /path/to/kicad-cli
```

The command runs ERC and DRC with violation exit codes, exports BOM, Gerbers,
drill and placement data, PDF documentation, STEP, and front/back renders,
then writes a deterministic release manifest beneath `build/kicad/pager-carrier-rev-a/`.
Generated manufacturing files are intentionally not committed.

## Power-up constraint

BQ25120A starts its SYS buck at 1.8 V. Firmware must boot from internal MCU
flash, program SYS to 3.3 V, verify it, and only then enable the switched 2.5 V,
1.0 V, and LCD 5 V rails. `ACCEL_RESET_N` remains asserted during this sequence.
