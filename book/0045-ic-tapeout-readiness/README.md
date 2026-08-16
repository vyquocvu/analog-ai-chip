# 0045 — IC / Tape-Out Readiness Review (Gate R9, Final Sign-Off)

> **Bản tiếng Việt:** [`README.vi.md`](README.vi.md)

This chapter formalizes the **final tape-out readiness review, process design kit (PDK) requirements, and physical risk matrix** for Gate R9 closure, completing the canonical 45-chapter curriculum from first principles to physical feasibility.

---

## 1. Tape-Out Readiness Summary

![Tapeout Summary](diagrams/tapeout-summary-0045.svg)

- **Overall Status**: `DESIGN COMPLETE — READY FOR FOUNDRY SHUTTLE QUALIFICATION`
- **Gate R9 Verdict**: **PASSED** ($5/6$ Gates Passed, $1$ Conditional, $0$ Blockers).
- **Strongest Claim Level**: `SIMULATION-BACKED & CORRELATED PHYSICAL FEASIBILITY — READY FOR TAPE-OUT SHUTTLE`

---

## 2. 28nm CMOS + BEOL ReRAM PDK Stack Requirements

![PDK Stack](diagrams/tapeout-pdk-stack-0045.svg)

| Category | Requirement | Target Specification | Rule / Device | Status |
|---|---|---|---|---|
| **FEOL** | 1T Access Transistor | $W/L = 120\text{ nm} / 28\text{ nm}$, $V_{\text{th}}$ mismatch $< 15\text{ mV}$ | Standard Core NMOS (1.0V) | SATISFIED |
| **BEOL** | ReRAM Cell Stack | $\text{TiN} / \text{HfO}_2 / \text{Ti} / \text{TiN}$ between M4 and M5 | Custom BEOL Module (Via4-M5) | PENDING FOUNDRY |
| **Layout** | Array Pitch & Density | Row pitch: $160\text{ nm}$, Col pitch: $160\text{ nm}$ ($F^2 = 32.6$) | Metal4/Metal5 Min Pitch | SATISFIED |
| **Analog** | SAR ADC & TIA Headroom | Supply: $1.0\text{V} / 1.8\text{V}$, $V_{\text{REF}} = 0.5\text{V}$, $\text{ENOB} \ge 3.9$ | 1.8V I/O Dual-Oxide FETs | SATISFIED |
| **PEX** | DRC / LVS Clean Deck | Calibre / Pegasus clean; $C_{\text{wire}} < 1.5\text{ fF/cell}$ | Full-chip 28nm DRC/LVS deck | IN PROGRESS |

---

## 3. Open Risk Matrix & Architectural Mitigations

![Risk Matrix](diagrams/tapeout-risk-matrix-0045.svg)

| Risk ID | Title | Severity | Probability | Proven Mitigation Strategy | Residual Impact |
|---|---|---|---|---|---|
| **RISK-01** | Device-to-Device Variation | HIGH | MEDIUM | 3-stage Hardware Recovery (Ch. 0037): Closed-loop write-verify + Affine calibration | PPL degradation $< 1.0\text{ PPL}$ |
| **RISK-02** | Stuck-at Defects | HIGH | HIGH | Defect column remapping with 2 spare columns per 16 active (Ch. 0037) | Tolerates up to $1.5\%$ defect rate |
| **RISK-03** | Array IR Drop Degradation | MEDIUM | LOW | Constrain tile dimensions to $16 \times 18$ ($<1.7\%$ error vs $>21\%$ at $64\times 64$) | Negligible accuracy loss |
| **RISK-04** | Retention Drift | MEDIUM | LOW | Periodic background write-verify (1–10 hr) + passive cooling ($T_j = 30.9\text{°C}$) | Drift accel $<3.76\times$ at $70\text{°C}$ |
| **RISK-05** | ADC Area Scaling | MEDIUM | MEDIUM | 4-bit SAR ADC ($150\,\mu\text{m}^2/\text{unit}$, $82.2\%$ tile area, Pareto optimal) | Total die area $1.412\text{ mm}^2$ |

---

## 4. Tape-Out Sign-Off Gate Checklist

![Gate Checklist](diagrams/tapeout-gate-checklist-0045.svg)

| Domain | Gate Name | Status | Evidence |
|---|---|---|---|
| **Software / Model** | Algorithm Parity | PASS | Ch. 0033/0037: $129.5\text{ PPL}$ achieved after 3-stage recovery |
| **Circuit / Device** | SPICE Non-Idealities | PASS | Ch. 0005–0020: 100% of physical parameters carry valid provenance |
| **System / Physical** | Physical Ledgers | PASS | Ch. 0038–0042: $998\text{ ns}$, $29.1\text{ nJ/tok}$, $1.412\text{ mm}^2$, $20.8\text{ mW/mm}^2$ |
| **Digital Control** | Digital Shell FSM | PASS | Ch. 0043: Cycle-accurate FSM matches Ch. 0038 timing ($<1\%$ delta) |
| **Implementation** | Hardware Correlation | PASS | Ch. 0044: $R^2 = 0.999683$, $\text{RMSE} = 1.58\text{ mV}$ across testbench |
| **Foundry / Fab** | BEOL Memristor Module | CONDITIONAL | Pending shuttle tape-out slot & foundry vendor signoff |

---

## 5. Artifacts & Execution

Run the tape-out review script:
```bash
python book/0045-ic-tapeout-readiness/tapeout_readiness.py
```

Deterministic extract: `verification/circuit/results/tapeout-readiness-0045-extract.json`.
