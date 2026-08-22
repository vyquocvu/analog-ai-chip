# 0049 — Block-Streamed Linear Execution & Memory Bounding (Gate R11)

> **Bản tiếng Việt:** [`README.vi.md`](README.vi.md)

This chapter formalizes **block-streamed linear execution and host memory bounding** for **Gate R11 (Memory-bounded large-model simulator)**. It replaces legacy whole-matrix $\text{float64}$ transposition and full-array duplication with dtype-preserving, tile-blocked streaming that directly matches physical crossbar hardware partitions ($16 \times 16$).

---

## 1. Block-Streamed Linear Architecture & Tile Partitioning

![Block-Streamed Partitioning](diagrams/block-stream.svg)

- **Tile-Blocked Streaming**: Large projection weight matrices $W \in \mathbb{R}^{\text{out} \times \text{in}}$ are divided into independent $(R \times C)$ sub-blocks $W_{i,j}$ (default $16 \times 16$), matching physical crossbar tile boundaries.
- **Dtype Preservation**: Weights remain in their source precision ($\text{float16}, \text{bfloat16}$) during streaming without materializing multi-gigabyte $\text{float64}$ memory copies.
- **Strict Hybrid Boundary**:
  - Sub-block MVM operations execute either on stationary analog tiles (via [`Accelerator`](../../analog_llm/accelerator.py)) or through vectorized digital kernels.
  - Partial sum accumulations across row blocks ($\sum_j X_j W_{i,j}^T$) and additive bias injections occur digitally.

---

## 2. Mathematical Formulations & Partial Sum Accumulation

For an input activation matrix $X \in \mathbb{R}^{T \times \text{in}}$ partitioned into column chunks $X_j \in \mathbb{R}^{T \times R}$ and weight matrix $W \in \mathbb{R}^{\text{out} \times \text{in}}$ partitioned into $(C \times R)$ blocks $W_{i,j}$:

$$Y_i = \sum_{j=0}^{N_{\text{row}}-1} X_j W_{i,j}^T + b_i$$

- **Exact Equivalence**: Block-streamed accumulation achieves bitwise and machine-precision equivalence ($\Delta < 10^{-12}$) against monolithic matrix-vector multiplications.
- **Boundary Handling**: Non-multiple dimensions along input or output features are zero-padded to $(R \times C)$ tile boundaries and truncated at digital accumulation.

---

## 3. Working Memory Bounds & Scalable Tier Analysis

Monolithic simulator execution converts entire weight matrices to $\text{float64}$ ($8\text{ bytes/parameter}$). Block-streamed execution bounds peak host working memory to:

$$M_{\text{peak}} = (R \cdot C \cdot \text{dtype\_bytes}) + (T \cdot \text{in} \cdot 8) + (T \cdot \text{out} \cdot 8)$$

| Projection Benchmark | Dimensions ($[\text{out}, \text{in}]$) | Tile Blocks ($16 \times 16$) | Monolithic FP64 Mem | Streamed Working Mem | Memory Reduction |
|---|---|---|---|---|---|
| **Hand-Calc ($2 \times 2$)** | $4 \times 6$ | $6$ | $192\text{ B}$ | $88\text{ B}$ | **$2.2\times$** |
| **T0 (TinyGPT Proj)** | $64 \times 64$ | $16$ | $32.0\text{ KB}$ | $1.5\text{ KB}$ | **$21.3\times$** |
| **T1 (1B Attention Proj)** | $2048 \times 2048$ | $16,384$ | $32.0\text{ MB}$ | $32.5\text{ KB}$ | **$1,008.2\times$** |
| **T2 (7B Attention Proj)** | $4096 \times 4096$ | $65,536$ | $128.0\text{ MB}$ | $64.5\text{ KB}$ | **$2,032.1\times$** |

*For large-model projections (T1/T2), block-streamed execution reduces peak working memory by over $1000\times$ during single-token autoregressive decode.*

---

## 4. Batched Prefill vs Single-Token Decode Scaling

- **Single-Token Decode ($T=1$)**: Peak memory is dominated by tile block storage ($R \cdot C \cdot \text{dtype\_bytes} \approx 512\text{ B}$), ensuring minimal process RSS footprint.
- **Batched Prefill ($T=16\dots 64$)**: Memory scales linearly with context length ($O(T \cdot (\text{in} + \text{out}))$), while weight loading remains strictly bounded to one tile block at a time.

---

## 5. Execution & Artifacts

Run the standalone chapter verification script:
```bash
python book/0049-block-streamed-execution/block_streamed_execution.py
```

Run test suite:
```bash
pytest tests/test_block_stream.py
```

Deterministic extract artifact:
`verification/circuit/results/block-streamed-0049-extract.json`
