# Curriculum — Canonical Design Sequence

> For the implementation status and evidence gate verification requirements, see [`docs/ROADMAP.md`](ROADMAP.md).

This document indexes the sequential book chapters (`book/`) from first principles to full LLM inference:

```text
Math / ideal reference
        ↓
Circuit primitives (Ohm + Kirchhoff = MVM)
        ↓
SPICE-verified current-mode crossbar
        ↓
Circuit-to-profile extraction
        ↓
DAC / ADC signal path
        ↓
Small crossbar arrays (2×2, 4×4)
        ↓
Device realism & variation (IR drop, drift, parasitics)
        ↓
Profile-driven physical tile & partial sums
        ↓
Multi-tile accelerator + NoC data movement
        ↓
Transformer & LLM mapping (QKV, Attention, MLP)
        ↓
Latency / energy / area physical feasibility
        ↓
FPGA / PCB / silicon correlation
```

---

## Chapter Index

* **Part I — Math and functional reference:** [`book/0000`](../book/0000-what-we-are-building/) through [`book/0004`](../book/0004-tiling/)
* **Part II — Circuit primitives & current-mode compute:** [`book/0005`](../book/0005-one-analog-neuron/) through [`book/0007`](../book/0007-crossbar-column/)
* **Part III — Converter signal path:** [`book/0009`](../book/0009-dac-r2r/) through [`book/0011`](../book/0011-converter-variation/)
* **Part IV — Small physical crossbar arrays:** [`book/0012`](../book/0012-crossbar-2x2/) through [`book/0014`](../book/0014-array-timing/)
* **Part V — Device realism & variation:** [`book/0015`](../book/0015-conductance-model/) through [`book/0020`](../book/0020-crossbar-v1/)
* **Part VI — Profile-driven accelerator architecture:** [`book/0021`](../book/0021-physical-tile-contract/) through [`book/0026`](../book/0026-calibration/)
* **Part VII & VIII — Transformer & LLM inference:** [`book/0027`](../book/0027-linear-layer/) through [`book/0037`](../book/0037-hardware-recovery/)
* **Part IX & X — Feasibility & correlation:** [`book/0038`](../book/0038-latency-ledger/) through [`book/0045`](../book/0045-ic-tapeout-readiness/)
* **Part XI — Scalable model semantics & sharded checkpoints:** [`book/0046`](../book/0046-model-manifest/) through [`book/0048`](../book/0048-generalized-decoder/)
* **Part XII — Memory-bounded execution & non-ideality surrogates:** [`book/0049`](../book/0049-block-streamed-execution/) through [`book/0051`](../book/0051-resumable-evaluator/)
* **Part XIII — Large-model architecture & KV-cache hierarchy:** [`book/0052`](../book/0052-weight-residency-topology/) through [`book/0053`](../book/0053-kv-cache-hierarchy/)
* **Part XIV — Large-model error attribution & hardware recovery:** [`book/0054`](../book/0054-large-model-error-attribution/) through [`book/0055`](../book/0055-scalable-hardware-recovery/)
* **Part XV — Multi-tier physical feasibility & tape-out decision:** [`book/0056`](../book/0056-parametric-physical-ledger/) through [`book/0058`](../book/0058-tapeout-feasibility-decision/)
* **Part XVI — Physical layout & DRC/LVS verification:** [`book/0059`](../book/0059-reram-macro-layout/) through [`book/0062`](../book/0062-top-level-chip-assembly/)
* **Part XVII — Post-layout parasitic extraction & static timing:** [`book/0063`](../book/0063-post-layout-parasitic-extraction/) through [`book/0065`](../book/0065-dynamic-power-grid-em-signoff/)
* **Part XVIII — Tape-out signoff, packaging & PCB carrier integration:** [`book/0066`](../book/0066-gdsii-streamout-tapeout-signoff/) through [`book/0068`](../book/0068-pcie-gen5-carrier-board-signoff/)

> **Tiếng Việt:** Mỗi chương trong `book/` đều có file `README.vi.md` song ngữ bên cạnh `README.md`.
