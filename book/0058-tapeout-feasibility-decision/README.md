# 0058 — Go/No-Go Architecture Decision & Physical Tape-Out Target (Gate R14 Exit)

> **Bản tiếng Việt:** [`README.vi.md`](README.vi.md)

This chapter concludes **Gate R14 (Multi-tier physical feasibility and design decision)** and marks the **successful completion of the entire analog AI chip architecture roadmap (Gates R0 through R14)**. It presents the unified **Go/No-Go architecture decision report** and formulates the primary physical tape-out target specifications.

---

## 1. Integrated Architecture Decision Matrix (T0–T3)

![Tape-Out Feasibility Decision](diagrams/tapeout-decision.svg)

- **Strict Feasibility Classification**:
  - **T0 (GPT-2 124M)**: **`FEASIBLE` / `GO`** — Monolithic single-die silicon ($336.1\text{ mm}^2 \le 400.0\text{ mm}^2$), $100\%$ stationary ReRAM weights, air-cooled ($1.92\text{ W/cm}^2$), achieving $244,247\text{ TPS}$ at $26.38\ \mu\text{J/token}$. **Selected Primary Tape-Out Target**.
  - **T1 (LLaMA-1B)**: **`CONDITIONAL` / `CONDITIONAL_GO`** — 11-chiplet 2.5D interposer package ($4,093.7\text{ mm}^2$). Feasible with high-density UCIe links, pending multi-die thermal/yield qualification.
  - **T2 (3B) & T3 (7B)**: **`INFEASIBLE` / `NO_GO`** for stationary analog IMC — Exceeds package packaging limits ($> 29\text{ dies}$); layer reload from off-chip HBM introduces severe memory bottleneck, losing the analog compute-in-memory energy advantage.

---

## 2. Selected Tape-Out Implementation Target Specifications

| Parameter | Specification | Verification Evidence Provenance |
|---|---|---|
| **Target Architecture** | **`T0_GPT2_124M`** ($12\text{ layers}, 768\text{ hidden}, 12\text{ heads}$) | Validated via `analog_llm.model_manifest` |
| **Process Node** | **$28\text{nm BEOL Via4-M5 ReRAM}$** ($160\text{ nm}$ cell pitch) | SPICE compact model (`device_profiles/crossbar-v1.json`) |
| **Die Dimensions** | **$18.3\text{ mm} \times 18.3\text{ mm}$ ($336.1\text{ mm}^2$)** | Monolithic die under $400.0\text{ mm}^2$ reticle limit |
| **Package Type** | **FCBGA-676 ($21\text{ mm} \times 21\text{ mm}$)** | Flip-chip ball grid array with heat spreader |
| **Decode Throughput** | **$244,247.5\text{ TPS}$** | Stationary crossbar MVM ($20\text{ ns}$ tile cycle) |
| **Energy per Token** | **$26.38\ \mu\text{J / token}$** | Subsystem parametric ledger (Chapter 0056) |
| **Active Power** | **$6.44\text{ W}$ ($1.92\text{ W/cm}^2$)** | **`PASS_AIR_COOLED`** ($< 150\text{ W/cm}^2$ limit) |
| **Hardware Recovery** | Output calibration, write-verify tuning, spare columns | Accuracy restored to $75\%$ Top-1 (Chapter 0055) |

---

## 3. Multi-Tier Feasibility Rationale & Evidence Requirements

| Tier | Status | Verdict | Die Count | Silicon Area | Decode Throughput | Primary Bottleneck | Prerequisite Evidence for Promotion |
|---|---|---|---|---|---|---|---|
| **T0** | **`FEASIBLE`** | **`GO`** | $1$ | $336.1\text{ mm}^2$ | $244,247\text{ TPS}$ | `adc_area_bandwidth_limit` | DRC/LVS clean tape-out signoff & foundry shuttle slot. |
| **T1** | **`CONDITIONAL`** | **`CONDITIONAL_GO`** | $11$ | $4,093.7\text{ mm}^2$ | $69,685\text{ TPS}$ | `digital_attention_compute_limit` | 2.5D interposer thermal stress simulation & KGD testing protocol. |
| **T2** | **`INFEASIBLE`** | **`NO_GO`** | $29$ | $11,369.1\text{ mm}^2$ | $3,132\text{ TPS}$ | `crossbar_capacity_limit` | 3D monolithic BEOL stacking (>4 layers) & sub-100nm pitch. |
| **T3** | **`INFEASIBLE`** | **`NO_GO`** | $66$ | $26,147.2\text{ mm}^2$ | $547\text{ TPS}$ | `crossbar_capacity_limit` | Optical inter-chiplet fabric & analog photonic attention co-processor. |

---

## 4. Full Physical Evidence Chain & Roadmap Gate Closure

Every gate across the canonical curriculum has been closed with verifiable evidence:
- **Gates R0–R5**: Foundational device physics, SPICE non-ideality extraction, 8-bit converters, and crossbar array mapping.
- **Gates R6–R9**: Small-model transformer mapping, physical ledgers, and FPGA/PCB/tape-out correlation.
- **Gates R10–R13**: Sharded checkpoint loading, memory-bounded streaming simulator, KV-cache hierarchy, and hardware accuracy recovery.
- **Gate R14**: Parametric physical ledger, architectural Pareto sweeps, digital break-even proof, and formal tape-out decision signoff.

---

## 5. Execution & Artifacts

Run the standalone chapter verification script:
```bash
python book/0058-tapeout-feasibility-decision/tapeout_decision.py
```

Run test suite:
```bash
pytest tests/test_decision_report.py
```

Deterministic extract artifact:
`verification/circuit/results/tapeout-decision-0058-extract.json`
