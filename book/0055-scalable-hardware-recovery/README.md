# 0055 — Scalable Hardware Recovery & Selective Digital Fallback (Gate R13 Exit)

> **Bản tiếng Việt:** [`README.vi.md`](README.vi.md)

This chapter concludes **Gate R13 (Large-model accuracy and hardware-recovery validation)** by formalizing **layer sensitivity profiling, affine output calibration, closed-loop write-verify tuning, defect column remapping, and selective digital fallback** with explicit hardware ledger accounting.

---

## 1. Multi-Stage Recovery Architecture & Mitigation Pipeline

![Scalable Hardware Recovery](diagrams/scalable-recovery.svg)

- **Layer Sensitivity Profiling**: Evaluates the error compounding effect by perturbing individual decoder layers in isolation, identifying high-sensitivity bottleneck blocks (e.g. input-adjacent Layer 0).
- **Physical Mitigation Mechanisms**:
  1. **Affine Output Calibration**: Per-layer gain and offset adjustment correcting systematic ADC discretization shifts ($288\text{ B}$ metadata).
  2. **Iterative Write-Verify Tuning**: Closed-loop programming pulses reducing programming variation $\sigma_{\text{prog}}$ from $1.5\%$ to $0.25\%$ ($4.2\times$ one-time programming energy).
  3. **Spare Column Defect Remapping**: Hardware redundant columns eliminating stuck-HRS/LRS fault cells.
  4. **Selective Digital Fallback**: Routing only the most sensitive layer (Layer 0) through the on-chip digital vector unit ($25\%$ digital compute overhead on a 4-layer decoder) while executing remaining layers on stationary analog crossbars.

---

## 2. Layer Sensitivity Ranking Formulation

For a decoder with $L$ layers, each layer $l$ is perturbed with representative analog non-idealities while holding other layers ideal:

$$\text{MSE}_l = \frac{1}{T \cdot V} \sum_{t=1}^T \sum_{v=1}^V \left(z_{t,v}^{(l)} - z_{t,v}^{(\text{ref})}\right)^2$$

$$\text{Rank}(l) = \text{argsort}(\text{MSE}_l, \text{descending})$$

The highest-ranked layer ($\text{Rank} = 1$) is automatically assigned to selective digital fallback.

---

## 3. Recovery Strategy Ladder & Acceptance Results

Evaluated on a 4-layer GPT-2 (T0) decoder with frozen acceptance criteria ($\text{PPL} \le 1.20\times\text{ baseline}$, $\text{Top-1 Agreement} \ge 60.0\%$):

| Recovery Strategy | Perplexity | Top-1 Agreement (%) | Mean KL Divergence | Write Energy Multiplier | Digital Compute Overhead | Acceptance Status |
|---|---|---|---|---|---|---|
| **Digital Float Baseline** | **$139.83$** | **$100.0\%$** | **$0.000\text{e}+00$** | **$1.0\times$** | **$0.0\%$** | `VERIFIED DIGITAL` |
| **`unmitigated`** | $142.69$ | $68.8\%$ | $2.399 \times 10^{-3}$ | $1.0\times$ | $0.0\%$ | **PASSED** |
| **`output_calibration`** | $142.35$ | $68.8\%$ | $2.355 \times 10^{-3}$ | $1.0\times$ | $0.5\%$ | **PASSED** |
| **`write_verify_tuning`** | $137.06$ | $50.0\%$ | $2.427 \times 10^{-3}$ | $4.2\times$ | $0.0\%$ | *Partial (Top-1)* |
| **`defect_remapping`** | $139.91$ | $56.2\%$ | $2.275 \times 10^{-3}$ | $1.1\times$ | $0.0\%$ | *Partial (Top-1)* |
| **`selective_digital_fallback`** | $141.91$ | **$75.0\%$** | $1.349 \times 10^{-3}$ | $1.0\times$ | $25.0\%$ | **PASSED** |
| **`composite_recovery`** | **$141.36$** | **$62.5\%$** | **$1.343 \times 10^{-3}$** | **$4.2\times$** | **$25.0\%$** | **PASSED** |

---

## 4. Hardware Overhead Ledger & Recovery Tradeoffs

- **Calibration Metadata Storage**: Requires $< 1\text{ KB}$ for affine scale/offset tables and spare-column defect routing LUTs.
- **Programming Energy & Time**: Iterative write-verify pulses consume $4.2\times$ standard single-pulse programming energy during one-time factory/deployment provisioning.
- **Compute Efficiency**: Selective digital fallback of Layer 0 incurs a $+25\%$ digital FP16 compute overhead but suppresses $> 44\%$ of distribution divergence ($D_{\text{KL}}$ drops from $2.399 \times 10^{-3}$ to $1.343 \times 10^{-3}$).

---

## 5. Execution & Artifacts

Run the standalone chapter verification script:
```bash
python book/0055-scalable-hardware-recovery/scalable_recovery.py
```

Run test suite:
```bash
pytest tests/test_recovery.py
```

Deterministic extract artifact:
`verification/circuit/results/scalable-recovery-0055-extract.json`
