# 0029 — Q/K/V Attention Projections Mapping (Gate R7)

> **Bản tiếng Việt:** [`README.vi.md`](README.vi.md)

This chapter formalizes the **packed multi-tile mapping of Transformer Multi-Head Self-Attention linear projections ($W_{QKV}$ and $W_O$), multi-head slicing, and attention logit sensitivity** for **Gate R7 (Transformer and LLM validation)**.

---

## 1. Attention Projection Architecture & Tile Grid

![QKV Projections Mapping](diagrams/qkv-projections-0029.svg)

For an input hidden state $x \in \mathbb{R}^{d_{\text{model}}}$:
1. **Fused Packed $W_{QKV} \in \mathbb{R}^{3 d_{\text{model}} \times d_{\text{model}}}$**:
   - Tiled across $K_{r,\text{qkv}} \times K_{c,\text{qkv}}$ physical $16\times 16$ crossbar tiles:
     $$K_{r,\text{qkv}} = \lceil 3 d_{\text{model}} / 16 \rceil, \quad K_{c,\text{qkv}} = \lceil d_{\text{model}} / 16 \rceil$$
   - For TinyGPT ($d_{\text{model}} = 64$): $192 \times 64 \to 12 \times 4 = 48\text{ physical tiles}$.
   - Multicasts $x$ across all rows in parallel, producing Query, Key, and Value vectors simultaneously.
2. **Output Projection $W_O \in \mathbb{R}^{d_{\text{model}} \times d_{\text{model}}}$**:
   - Tiled across $4 \times 4 = 16\text{ physical tiles}$ ($64 \times 64$).
   - Total static attention tiles: $48 + 16 = 64\text{ physical tiles}$.
3. **Multi-Head Slicing & Logit Sensitivity**:
   - Slices $q, k, v$ into $n_{\text{heads}}$ heads of dimension $d_{\text{head}} = d_{\text{model}} / n_{\text{heads}}$:
     $$Q_h = q[h \cdot d_{\text{head}} : (h+1) \cdot d_{\text{head}}], \quad K_h = k[h \cdot d_{\text{head}} : (h+1) \cdot d_{\text{head}}]$$
   - Computes raw attention score:
     $$S_h = \frac{Q_h K_h^T}{\sqrt{d_{\text{head}}}}$$
   - Evaluates cosine similarity, logit perturbation, and post-ADC calibration ($a^* = 0.9795135$).

---

## 2. Accuracy & Projection Metrics

### TinyGPT Attention Benchmarks ($d_{\text{model}} = 64, 64$ Physical Tiles):

| Projection Vector / Logit | Matrix / Head Dimension | Physical Tile Grid | Relative $L_2$ Error | Cosine Similarity | SNR (dB) |
|---|---|---|---|---|---|
| **Query Vector ($Q$)** | $64 \times 64$ (4 heads $\times 16$) | $16\text{ tiles}$ (within QKV grid) | **$39.07\%$** | **$0.9344$** | $8.2\text{ dB}$ |
| **Key Vector ($K$)** | $64 \times 64$ (4 heads $\times 16$) | $16\text{ tiles}$ (within QKV grid) | **$37.65\%$** | **$0.9360$** | $8.5\text{ dB}$ |
| **Value Vector ($V$)** | $64 \times 64$ (4 heads $\times 16$) | $16\text{ tiles}$ (within QKV grid) | **$39.38\%$** | **$0.9312$** | $8.1\text{ dB}$ |
| **Output Projection ($O$)** | $64 \times 64$ | $16\text{ physical tiles}$ | **$40.35\%$** | **$0.9238$** | $7.9\text{ dB}$ |
| **Attention Logit ($S_h$)** | $4\text{ heads}$ | — | **$77.77\%$** | — | $2.2\text{ dB}$ |

---

## 3. Mathematical Formulas

- **Fused QKV Projection**: $[q; k; v] = a^* \cdot \sum_{j=0}^{K_{c,\text{qkv}}-1} \text{Tile}_{\text{qkv}, i, j}(x_j)$
- **Multi-Head Slicing**: $Q_h = q[h \cdot d_{\text{head}} : (h+1) \cdot d_{\text{head}}]$
- **Attention Logit**: $S_h = \frac{Q_h K_h^T}{\sqrt{d_{\text{head}}}}$
- **Cosine Similarity**: $\text{Sim}(y, \hat{y}) = \frac{y \cdot \hat{y}}{\|y\|_2 \|\hat{y}\|_2}$

---

## 4. Execution & Artifacts

Run the deterministic QKV projection evaluation:
```bash
python book/0029-qkv-projections/qkv_projections.py
```
Committed extract artifact at: `verification/circuit/results/qkv-projections-0029-extract.json`.
