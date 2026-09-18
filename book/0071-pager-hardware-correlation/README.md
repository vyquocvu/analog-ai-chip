# Chapter 0071 — Pager Carrier Design Verification

This chapter records the Rev A carrier's KiCad design evidence and a separate
representative transfer sweep. It does not claim fabricated or measured hardware.

The 70 × 52 mm, 1.2 mm four-layer source is in
`kicad/pager-carrier-rev-a/`. KiCad 10.0.6 reports zero ERC violations, zero
PCB DRC violations, zero unrouted items, and zero schematic-parity issues. The
0.32 mm impedance geometry remains `assumed` pending a fabricator stackup or
coupon measurement.

The ten-point transfer sweep is deterministic synthetic data. Its numerical
fit may be used for sensitivity testing, but cannot be promoted to `measured`.
Real measurement import requires a raw file with instrument manufacturer,
model, serial number, acquisition time, and a source-file hash.

Run:

```bash
python book/0071-pager-hardware-correlation/pager_hardware_correlation.py
python scripts/build_pager_kicad.py --kicad-cli /path/to/kicad-cli
```

Tracked results are `verification/circuit/results/pager-correlation-0071-extract.json`,
`device_profiles/assumed/pager-crossbar-representative-v1.json`, and the chapter
diagram. Manufacturing outputs are generated under the ignored `build/` tree.
