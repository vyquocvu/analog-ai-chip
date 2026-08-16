# 0042 — Integrated Physical Feasibility Report (Gate R8)

> **Bản tiếng Việt:** [`README.vi.md`](README.vi.md)

This chapter generates the **final integrated physical feasibility report** for the analog IMC accelerator, consolidating all evidence from Gate R8 chapters 0038–0041. Every claim is labelled with its evidence class, separating `measured`, `spice`, `derived`, and `assumed` tiers. Sensitivity ranges are documented for all assumed parameters, and all efficiency claims are audited against the physical ledger.

---

## 1. Gate R8 Verdict

![Feasibility Summary](diagrams/feasibility-summary-0042.svg)

> **Gate R8: PASSED — 7/7 milestones satisfied.**

The strongest available status without fabricated hardware is:
> *SYSTEM-LEVEL DERIVED — All physical metrics are derived from evidence-tagged coefficients. No fabricated-hardware measurements are available. Gate R8 is satisfied at the derived/assumed physical modelling level.*

---

## 2. Physical Claims Ledger

![Physical Claims Ledger](diagrams/feasibility-ledger-0042.svg)

| Domain | Claim | Value | Evidence |
|---|---|---|---|
| **Latency** | Single-token decode latency | **998.0 ns** | `derived` (Ch.0038) |
| **Latency** | Decode throughput | **1,002,004 tok/s** | `derived` (Ch.0038) |
| **Energy** | Energy per token | **29.08 nJ/token** | `derived` (Ch.0039) |
| **Energy** | Active chip power | **29.14 mW** | `derived` (Ch.0039) |
| **Energy** | Efficiency advantage vs digital | **8.6×** | `derived` — digital baseline assumed |
| **Area** | Single tile area | **3,281.5 µm²** | `derived` (Ch.0040) |
| **Area** | Total chip die area | **1.412 mm²** | `derived` (Ch.0040) |
| **Area** | Compute area efficiency | **75.6 GOPS/mm²** | `derived` (Ch.0040) |
| **Thermal** | Nominal junction temperature | **30.87°C** | `derived` (Ch.0041) |
| **Thermal** | Power density | **20.79 mW/mm²** | `derived` (Ch.0041) |

---

## 3. Sensitivity Ranges for Assumed Parameters

![Sensitivity Ranges](diagrams/feasibility-sensitivity-0042.svg)

| Assumed Parameter | Baseline | Pessimistic Impact | Optimistic Impact |
|---|---|---|---|
| ADC unit area ($A_{\text{adc}}$) | 150 µm² | Tile +44%, Chip 2.01 mm² | Tile −47%, Chip 0.76 mm² |
| ADC energy per conversion | 0.5 pJ/conv | Energy: 86.4 nJ (+197%) | Energy: 15.2 nJ (−48%) |
| Thermal resistance ($\theta_{ja}$) | 200 °C/W | $T_j = 39.7\text{ °C}$ (tighter) | $T_j = 26.5\text{ °C}$ (near ambient) |
| Memristor activation energy ($E_a$) | 0.6 eV | AF = 6.8× at 70°C | AF = 2.0× at 70°C |
| Digital baseline energy | 250 nJ/token | Advantage: 2.7× | Advantage: 17.2× |

> [!WARNING]
> The **ADC energy** and **digital baseline energy** assumptions dominate the efficiency claim uncertainty. The 8.6× advantage is conditional on the stated 250 nJ/token int8 digital model.

---

## 4. Efficiency Claims Audit

![Gate R8 Status](diagrams/feasibility-gate-r8-0042.svg)

All **4 efficiency claims are ALLOWED** with documented caveats:

| Claim | Ratio | Allowed | Caveat |
|---|---|---|---|
| IMC vs digital energy | 8.6× | ✓ | Digital baseline is assumed (250 nJ/token) |
| Crossbar GEMV is O(1) | 1.0× per-compute-step | ✓ | Full token decode is O(T) due to digital softmax/LayerNorm |
| Passive cooling sufficient | 4.8× margin | ✓ | θ_ja = 200 °C/W is assumed for bare die |
| Compute density | 75.6 GOPS/mm² | ✓ | Derived from assumed-ADC tile model |

---

## 5. Gate R8 Milestone Checklist (7 / 7 PASSED)

| Milestone | Status | Chapter |
|---|---|---|
| Latency model with evidence-tagged timing coefficients | ✓ | 0038 |
| Energy/power model with evidence-tagged coefficients | ✓ | 0039 |
| Area model with explicit topology/process/layout assumptions | ✓ | 0040 |
| Thermal/power-density sanity checks | ✓ | 0041 |
| Sensitivity ranges for all still-assumed parameters | ✓ | **0042** |
| No GPU/ASIC superiority claim without comparable measured evidence | ✓ | **0042** |
| Integrated feasibility report generated | ✓ | **0042** |

---

## 6. Execution

```bash
python book/0042-integrated-feasibility-report/feasibility_report.py
```

Extract at: `verification/circuit/results/integrated-feasibility-0042-extract.json`
