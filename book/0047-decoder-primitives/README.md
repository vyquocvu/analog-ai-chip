# 0047 — Reusable Decoder Primitives (Gate R10)

> **Bản tiếng Việt:** [`README.vi.md`](README.vi.md)

This chapter formalizes the **reusable digital decoder primitives** extracted from the reference transformer for **Gate R10 (Scalable model semantics & sharded checkpoints)**. It establishes exact mathematical formulations for RMSNorm, LayerNorm, SwiGLU, Rotary Position Embeddings (RoPE), and Multi-Head/Grouped-Query/Multi-Query Attention (MHA/GQA/MQA) under a strict hybrid analog/digital boundary.

---

## 1. Hybrid Compute Boundary Architecture

![Hybrid Decoder Boundary](diagrams/decoder-primitives.svg)

- **Analog-Eligible Boundary**: Static weight matrix projections ($W_Q, W_K, W_V, W_O$ and $W_{\text{gate}}, W_{\text{up}}, W_{\text{down}}$) are candidate workloads for stationary analog crossbar tiles.
- **Digital NumPy Reference**: Normalization, RoPE coordinate rotations, nonlinear activations, softmax exponentiation, and dynamic token-token attention scaling remain explicitly digital.
- **Claim Level**: `FUNCTIONAL / SOFTWARE REFERENCE` — refactoring and mathematical extraction establish decoder parity; they do not constitute physical acceleration evidence.

---

## 2. Mathematical Formulations & Hand Calculations

### 1. Root Mean Square Normalization (RMSNorm)
$$\text{RMSNorm}(x, w, \epsilon) = \frac{x}{\sqrt{\frac{1}{d}\sum_{i=1}^d x_i^2 + \epsilon}} \odot w$$
* **Hand Check**: For $x = [3.0, 4.0]$, $\text{RMS}^2 = \frac{9 + 16}{2} = 12.5$. With $w = [1.0, 2.0]$ and $\epsilon = 10^{-6}$, max error against $\frac{[3, 4]}{\sqrt{12.5 + 10^{-6}}} \odot [1, 2]$ is $< 1.11 \times 10^{-16}$.

### 2. Layer Normalization (LayerNorm)
$$\text{LayerNorm}(x, w, b, \epsilon) = \frac{x - \mu}{\sqrt{\sigma^2 + \epsilon}} \odot w + b$$
* **Hand Check**: For $x = [1.0, 3.0]$, $\mu = 2.0$, $\sigma^2 = 1.0$. With unit weight and zero bias, normalized output equals $\frac{[-1.0, 1.0]}{\sqrt{1.0 + 10^{-5}}}$ (exact parity, error $= 0.0$).

### 3. Gated SwiGLU Activation
$$\text{SwiGLU}(\text{gate}, \text{up}) = \text{SiLU}(\text{gate}) \odot \text{up} = \left(\text{gate} \cdot \frac{1}{1 + e^{-\text{gate}}}\right) \odot \text{up}$$
* **Hand Check**: At $\text{gate} = \ln(3) \approx 1.0986$, $\text{sigmoid}(\ln(3)) = \frac{3}{4} = 0.75$. For $\text{gate} = [0, \ln(3)]$ and $\text{up} = [4.0, 2.0]$, the result is $[0.0, 1.5 \ln(3)]$ (exact parity, error $= 0.0$).

### 4. Rotary Position Embedding (RoPE)
For adjacent coordinate pairs $(x_{2i}, x_{2i+1})$ at sequence position $m$ with frequency $\theta_i = b^{-2i/d}$:
$$\begin{pmatrix} x'_{2i} \\ x'_{2i+1} \end{pmatrix} = \begin{pmatrix} \cos(m\theta_i) & -\sin(m\theta_i) \\ \sin(m\theta_i) & \cos(m\theta_i) \end{pmatrix} \begin{pmatrix} x_{2i} \\ x_{2i+1} \end{pmatrix}$$
* **Hand Check**: For $[1.0, 0.0]$ at position $m=1$ with $\theta_0=1.0$, rotated vector equals $[\cos(1), \sin(1)]$ (exact parity, error $= 0.0$).

---

## 3. Attention Formats (MHA, GQA, MQA) & Cache Parity

The causal attention contract accepts Query $[T, Q_H, D]$ and Key/Value $[T, KV_H, D]$, repeating KV heads across query groups when $Q_H > KV_H$:

| Attention Mode | Query Heads ($Q_H$) | KV Heads ($KV_H$) | Group Ratio ($Q_H / KV_H$) | Scalar Loop Ref Max Delta | Step KV-Cache Max Delta |
|---|---|---|---|---|---|
| **MHA ($4 \times 4$)** | 4 | 4 | 1 | $4.44 \times 10^{-16}$ | $0.00 \times 10^{00}$ |
| **GQA ($4 \times 2$)** | 4 | 2 | 2 | $4.44 \times 10^{-16}$ | $0.00 \times 10^{00}$ |
| **MQA ($4 \times 1$)** | 4 | 1 | 4 | $2.78 \times 10^{-16}$ | $0.00 \times 10^{00}$ |

- **Full-Context vs Incremental Cache**: Single-step attention over accumulated KV-cache history (`cached_attention_step`) matches full batch sequence evaluation (`causal_attention`) to machine precision ($0.0$ delta).

---

## 4. Guardrails & Boundary Verification

1. **Even Head Dimension for RoPE**: Rejects odd head dimensions ($d \pmod 2 \neq 0$) since rotary embeddings require 2D orthogonal rotation pairs.
2. **Identical SwiGLU Shapes**: Rejects mismatched gate and up projection tensors.
3. **Divisible Attention Grouping**: Requires $Q_H \pmod{KV_H} == 0$. Rejects prime or mismatched head ratios.
4. **Finite and Positive Parameters**: Rejects non-finite, zero, or negative epsilon/frequency base constants.

---

## 5. Execution & Artifacts

Run the standalone primitives verification script:
```bash
python book/0047-decoder-primitives/decoder_primitives.py
```

Run test suite:
```bash
pytest tests/test_decoder_primitives.py
```

Deterministic extract artifact:
`verification/circuit/results/decoder-primitives-0047-extract.json`
