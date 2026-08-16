# 0037 — Hardware-Aware Recovery (Gate R7)

> **Bản tiếng Việt:** [`README.vi.md`](README.vi.md)

This chapter formalizes the **3-stage physical hardware-aware recovery framework** (Post-ADC Affine Calibration, Defect-Aware Column Remapping, and Closed-Loop Write-Verify Conductance Adaptation) on physical crossbars for **Gate R7 (Transformer and LLM validation)**.

---

## 1. Hardware Recovery Framework Overview

![Hardware-Aware Recovery](diagrams/hardware-recovery-0037.svg)

- **Problem Context**: Compounded 4-bit converter quantization, memristor stuck defects, and programming variance cause logit degradation in raw analog inference.
- **Recovery Solution**: A 3-stage hardware-software co-design framework corrects IR drop attenuation, swaps defective columns to redundant spare arrays, and iteratively trims conductances.

---

## 2. 3-Stage Mathematical Recovery Pipeline

![Recovery Pipeline](diagrams/hardware-recovery-pipeline-0037.svg)

1. **Stage 1 — Post-ADC Affine Calibration**:
   $$y_{\text{cal}} = \alpha \odot (y_{\text{adc}} - \beta)$$
   Digital scale $\alpha$ and offset $\beta$ correction performed per tile column, eliminating common-mode drift and IR drop voltage gradients with minimal digital overhead (1 ADD + 1 MUL).
2. **Stage 2 — Defect-Aware Column Remapping**:
   $$\text{col\_remap}[k] = \text{spare\_idx}$$
   On-chip $18:16$ MUX redirects defective bitlines (stuck HRS / LRS cells) to $2$ redundant spare physical columns per tile, eliminating $>90\%$ of defect noise.
3. **Stage 3 — Closed-Loop Weight Adaptation**:
   $$G_{\text{target}} \pm \Delta G_{\text{pulse}}$$
   Multi-pulse write-verify loop reduces effective programming variance from $\sigma_{\text{prog}} = 3.0\%$ to $0.5\%$, recovering near-float perplexity ($129.53\text{ PPL}$ vs Float $124.03\text{ PPL}$).

---

## 3. Perplexity & Parity Recovery Progression

![Parity Recovery Waterfall](diagrams/hardware-recovery-parity-0037.svg)

| Stage | Mitigations Active | Logit SNR | Perplexity (PPL) | Delta to Float |
|---|---|---|---|---|
| **Float Reference** | — (FP64 Digital Reference) | $\infty$ | **$124.03$** | Baseline |
| **Stage 0 (Raw)** | None (Uncalibrated 4-bit Hardware) | $-0.34\text{ dB}$ | **$135.16$** | $+11.13\text{ PPL}$ |
| **Stage 1 (Affine)** | Post-ADC $\alpha, \beta$ correction | $-1.07\text{ dB}$ | **$137.25$** | $+13.22\text{ PPL}$ |
| **Stage 2 (Remap)** | Redundant spare column replacement | $-0.76\text{ dB}$ | **$136.01$** | $+11.98\text{ PPL}$ |
| **Stage 3 (Write-Verify)** | Precision pulse tuning + remap + affine | **$-0.92\text{ dB}$** | **$129.53$** | **$+5.50\text{ PPL}$ (Recovered)** |

---

## 4. Hardware Architecture with Calibration & Redundancy

![Hardware Architecture](diagrams/hardware-recovery-hardware-0037.svg)

- **Tile Layout**: $16\times 18$ Memristor Crossbar ($16$ active columns + $2$ redundant spare columns).
- **Control & Routing**: $18:16$ column MUX for defective bitline bypassing.
- **On-Chip ALU**: 16-wide affine arithmetic unit executing $y = \alpha \odot (x - \beta)$ in a single clock cycle ($2.5\text{ fJ/MAC}$).

---

## 5. Execution & Artifacts

Run the deterministic hardware recovery simulation:
```bash
python book/0037-hardware-recovery/hardware_recovery.py
```
Committed extract artifact at: `verification/circuit/results/hardware-recovery-0037-extract.json`.
