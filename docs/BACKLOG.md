# Product Backlog

Ordered by value (highest first). Each item is a small user story with acceptance criteria.
For completed sprints and historical reviews (Sprints 1–17), see [`docs/archive/SPRINT_HISTORY.md`](archive/SPRINT_HISTORY.md).

Legend — size: `[S]` / `[M]` / `[L]`. Status: `backlog` → `in-progress` → `done`.

---

## Active Backlog (Ordered)

### V1 — BitNet b1.58 ternary quantization & crossbar mapping `[M]`
**As an** accelerator architect, **I want** to map ternary weights $W \in \{-1, 0, 1\}$ directly to differential conductance pairs $(G_{pos}, G_{neg})$ so that multi-bit weight DACs can be eliminated.

**AC:**
- [ ] BitNet b1.58 weight quantization and differential crossbar mapping in `analog_llm/`;
- [ ] Mapping verifies $W = 1 \implies (G_0, 0)$, $W = -1 \implies (0, G_0)$, $W = 0 \implies (0, 0)$;
- [ ] Pytest verification against float reference and linear layers;
- [ ] Traceable ledger accounting for 1.58-bit ternary conductance storage.

### V2 — Subthreshold MOS exponential block SPICE cell `[M]`
**As an** analog circuit designer, **I want** a SPICE netlist characterization of a subthreshold MOS differential pair / exponential current generator for Softmax so that temperature and $V_{th}$ sensitivity are quantified.

**AC:**
- [ ] SPICE netlist in `verification/circuit/` implementing subthreshold exponential current generation;
- [ ] Temperature sweep (0°C to 85°C) and process corner sensitivity analysis;
- [ ] Parameter extraction into a validated profile under `device_profiles/`;
- [ ] Pytest with engine check.

### V3 — Time-domain PWM / TDC converter architecture `[M]`
**As an** analog architect, **I want** a time-domain PWM activation encoder and TDC integrator model in `analog_llm/converters/` so we can compare time-domain vs voltage-mode SNR and energy.

**AC:**
- [ ] Behavioral PWM encoder and TDC integrator in `analog_llm/converters/`;
- [ ] Non-ideality models (clock jitter, integrator non-linearity, pulse dispersion);
- [ ] Accuracy-vs-resolution evaluation with unit tests;
- [ ] Ledger accounting for time-domain conversion cycles.

### V4 — SkyWater 130nm / TinyTapeout test cell specification `[M]`
**As a** hardware engineer, **I want** a concrete Open-Source PDK tapeout specification (TinyTapeout / Efabless ChipIgnite) for the analog crossbar neuron cell.

**AC:**
- [ ] Pinout mapping, voltage limits, and analog IO pad configuration defined;
- [ ] Xschem schematic + Magic/KLayout layout verification rules for Sky130;
- [ ] Pre-tapeout DRC/LVS check scripts documented.

### V5 — Standalone AI Text Appliance hardware & firmware specification `[M]`
**As a** product engineer, **I want** a complete system specification for an air-gapped text-in/text-out appliance (Host MCU + Keyboard + E-Ink Display + Analog CiM carrier board) so that the entire physical device can be built and evaluated.

**AC:**
- [ ] System block diagram and KiCad carrier board schematic specification (MCU $\leftrightarrow$ Analog Chiplet $\leftrightarrow$ Display $\leftrightarrow$ Keyboard);
- [ ] Firmware architecture for instant-boot text I/O, BPE tokenizer, and streaming token display driver;
- [ ] Power budget ledger for the complete device (battery life, active typing, standby);
- [ ] Enclosure specification and physical BOM.

---

## Current Sprint — Sprint 18
Goal: Consolidate the documentation architecture and specify the Dedicated AI Text Appliance and BitNet b1.58 crossbar integration.

| Id | Item | Size | Status |
|---|---|---|---|
| DOCS | Lean documentation restructuring (Roadmap, Spec, Vision, Backlog) | S | **in-progress** |
| V1 | BitNet b1.58 ternary quantization & crossbar mapping | M | **backlog** |
