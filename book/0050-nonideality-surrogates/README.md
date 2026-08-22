# 0050 — Scalable Non-Ideality Surrogates (Gate R11)

> **Bản tiếng Việt:** [`README.vi.md`](README.vi.md)

This chapter formalizes **scalable non-ideality evaluation modes and calibrated statistical surrogates** for **Gate R11 (Memory-bounded large-model simulator)**. It establishes an auditable 3-tier simulation hierarchy (`EXACT`, `LAYER_SAMPLED`, `STATISTICAL_SURROGATE`), cross-calibrated against profile-driven physical tile simulations to enable fast, memory-bounded evaluation of multi-billion parameter models without misrepresenting surrogate approximations as physical hardware acceleration.

---

## 1. Simulation Fidelity Ladder & Mode Classification

![Simulation Fidelity Hierarchy](diagrams/surrogate-modes.svg)

| Evaluation Mode | Provenance Label | Physical Fidelity | Speedup vs Exact | Intended Workload Target |
|---|---|---|---|---|
| **`EXACT`** | `VERIFIED PHYSICAL` | $100\%$ (All 9 physical mechanisms modeled on $16 \times 16$ tiles) | $1.0\times$ | T0 & small matrix verification runs |
| **`LAYER_SAMPLED`** | `SAMPLED HYBRID` | Stratified (Exact on subset $L \in \{0, L/2, L-1\}$, float bypass on rest) | $\approx 4\text{--}8\times$ | T1 & deep decoder layer propagation studies |
| **`STATISTICAL_SURROGATE`** | `APPROXIMATE STATISTICAL` | Calibrated empirical Gaussian noise $\mathcal{N}(\mu, \sigma^2)$ per projection | $>50\times$ | T2/T3 fast exploratory screening |

*Rule: The simulator strictly distinguishes physical simulation from statistical approximation. Surrogate or sampled runs must never be reported as verified physical acceleration.*

---

## 2. Stratified Calibration Methodology

Surrogate parameters are extracted by sweeping physical tile executions across stratified projection benchmarks:
- **Noise Statistics**: Mean error $\mu_{\text{err}} = \mathbb{E}[y_{\text{exact}} - y_{\text{float}}]$, standard deviation $\sigma_{\text{err}} = \text{std}(y_{\text{exact}} - y_{\text{float}})$.
- **Signal-to-Noise Ratio (SNR)**:
  $$\text{SNR}_{\text{dB}} = 10 \log_{10}\left(\frac{\mathbb{E}[y_{\text{float}}^2]}{\mathbb{E}[(y_{\text{exact}} - y_{\text{float}})^2]}\right)$$
- **Relative $L_2$ Error**:
  $$\text{Rel } L_2 (\%) = \frac{\sqrt{\text{MSE}}}{\text{RMS}(y_{\text{float}})} \times 100$$

---

## 3. Stratified Calibration Profiles by Projection Family

Calibrated against $16 \times 16$ crossbar tiles with 8-bit DAC/ADC, relative programming variation ($\sigma_{\text{prog}}=1.5\%$), read noise ($\sigma_{\text{read}}=0.8\%$), and ADC Gaussian noise ($\sigma_{\text{adc}}=0.5\%$):

| Projection Family | Error Mean ($\mu$) | Error Std ($\sigma$) | SNR (dB) | Relative $L_2$ Error | Calibrated $W_{\text{max}}$ |
|---|---|---|---|---|---|
| **`attention.q_proj`** | $-6.45 \times 10^{-4}$ | $3.71 \times 10^{-2}$ | $32.90\text{ dB}$ | $2.26\%$ | $0.40$ |
| **`attention.k_proj`** | $-6.45 \times 10^{-4}$ | $3.71 \times 10^{-2}$ | $32.90\text{ dB}$ | $2.26\%$ | $0.40$ |
| **`attention.v_proj`** | $-6.45 \times 10^{-4}$ | $3.71 \times 10^{-2}$ | $32.90\text{ dB}$ | $2.26\%$ | $0.40$ |
| **`attention.out_proj`** | $-8.44 \times 10^{-4}$ | $4.13 \times 10^{-2}$ | $31.81\text{ dB}$ | $2.57\%$ | $0.40$ |
| **`mlp.gate_proj`** | $+4.11 \times 10^{-5}$ | $3.63 \times 10^{-2}$ | $33.00\text{ dB}$ | $2.24\%$ | $0.40$ |
| **`mlp.up_proj`** | $-1.26 \times 10^{-3}$ | $3.83 \times 10^{-2}$ | $32.17\text{ dB}$ | $2.46\%$ | $0.40$ |
| **`mlp.down_proj`** | $+4.11 \times 10^{-5}$ | $3.63 \times 10^{-2}$ | $33.00\text{ dB}$ | $2.24\%$ | $0.40$ |

---

## 4. Fail-Closed Domain Guards & Boundary Verification

The surrogate evaluator enforces strict fail-closed constraints before noise injection:
1. **Weight Magnitude Domain**: Rejects evaluation if $\max(|W|) > 1.5 \times W_{\text{calibrated\_max}}$ to prevent extrapolating outside linear conductance boundaries.
2. **Tile Geometry Match**: Fails closed if the evaluation tile partition (e.g. $16 \times 16$) diverges from the calibration profile dimensions.
3. **Explicit Tagging**: Every evaluation output carries `is_physical_simulation` (`bool`) and `mode_description` to prevent silent misattribution.

---

## 5. Execution & Artifacts

Run the standalone chapter calibration and verification script:
```bash
python book/0050-nonideality-surrogates/nonideality_surrogates.py
```

Run test suite:
```bash
pytest tests/test_surrogate.py
```

Deterministic extract artifact:
`verification/circuit/results/nonideality-surrogates-0050-extract.json`
