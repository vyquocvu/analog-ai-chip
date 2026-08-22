# 0053 — KV-Cache Hierarchy, Paged Allocation & Digital Attention Wall (Gate R12 Exit)

> **Bản tiếng Việt:** [`README.vi.md`](README.vi.md)

This chapter concludes **Gate R12 (Large-model accelerator capacity and data movement)** by formalizing **KV-cache memory hierarchy, GQA/MQA compression scaling, paged block allocation, and the digital Attention Wall bottleneck crossover** across design tiers T0–T3.

---

## 1. Paged Memory Hierarchy & Multi-Tier Placement

![KV-Cache Hierarchy & Attention Wall](diagrams/kv-hierarchy.svg)

- **Three Memory Tiers**:
  1. **On-Chip Paged SRAM ($64\text{--}128\text{ MB}$, $8.0\text{ TB/s}$)**: Ultra-low latency ($< 5\text{ ns}$), hosting KV cache for T0 and short-context T1.
  2. **Package HBM3e ($32\text{--}96\text{ GB}$, $1.2\text{ TB/s}$)**: High-capacity tier hosting KV cache for long-context T1, T2, and T3 workloads ($T \ge 4096$).
  3. **Host DRAM ($64\text{ GB/s}$ via PCIe Gen5)**: Backup tier for overflow sequences exceeding package capacity.
- **Paged Allocation**: KV tensors are allocated in discrete $16\text{-token}$ blocks to eliminate memory fragmentation during variable-length autoregressive decoding.

---

## 2. GQA/MQA Compression Formulations

For a model with $L$ layers, $KV_H$ key-value heads, head dimension $d = H / Q_H$, context length $T$, and $\text{dtype\_bytes} = 2$ ($\text{FP16}$):

$$M_{\text{KV}} = 2 \times L \times KV_H \times d \times T \times \text{dtype\_bytes}$$

$$\text{GQA Compression Factor} = \frac{Q_H}{KV_H}$$

- **Multi-Head Attention (MHA)**: $KV_H = Q_H \implies 1.0\times$ baseline footprint.
- **Grouped-Query Attention (GQA)**: $1 < KV_H < Q_H$ (e.g. $KV_H = 4, Q_H = 32 \implies 8.0\times\text{ memory reduction}$).
- **Multi-Query Attention (MQA)**: $KV_H = 1 \implies Q_H\times\text{ memory reduction}$.

---

## 3. Workload Ladder KV Scaling & Placement (T0–T3)

| Model Tier | Architecture | GQA Ratio | Context ($T$) | KV Footprint | Memory Placement | Primary Latency Bottleneck |
|---|---|---|---|---|---|---|
| **Hand-Calc ($2\text{L}$)** | GQA ($4/2$) | $2.0\times$ | $64$ | $8.0\text{ KB}$ | `on_chip_sram` | Analog MVM ($15.0\ \mu\text{s}$) |
| **T0 (GPT-2 124M)** | MHA ($12/12$) | $1.0\times$ | $1,024$ | $36.0\text{ MB}$ | `on_chip_sram` | Analog MVM ($15.0\ \mu\text{s}$) |
| **T1 (LLaMA-1B)** | GQA ($32/4$) | $8.0\times$ | $2,048$ | $44.0\text{ MB}$ | `on_chip_sram` | Analog MVM ($15.0\ \mu\text{s}$) |
| **T1 (LLaMA-1B)** | GQA ($32/4$) | $8.0\times$ | $4,096$ | $88.0\text{ MB}$ | `package_hbm` | **Digital Attention Wall** ($73.4\ \mu\text{s}$) |
| **T2 (LLaMA-3B)** | GQA ($32/8$) | $4.0\times$ | $8,192$ | $672.0\text{ MB}$ | `package_hbm` | **Digital Attention Wall** ($560.1\ \mu\text{s}$) |
| **T3 (LLaMA-2 7B)** | MHA ($32/32$) | $1.0\times$ | $8,192$ | $4,096.0\text{ MB}$ | `package_hbm` | **Digital Attention Wall** ($3,413.5\ \mu\text{s}$) |

---

## 4. The Digital Attention Wall & Crossover Bottleneck Analysis

Analog in-memory computing executes linear weight projections at stationary $\mathcal{O}(1)$ cycle latency. However, token-token causal attention remains fundamentally digital ($Q K^T + \text{Softmax} + \text{Attn} V$):

$$\text{Latency}_{\text{digital}} = \frac{2 \times T \times H \times L \times 2}{\text{TFLOPS}_{\text{digital}}} + \frac{M_{\text{KV}}(T)}{\text{Bandwidth}_{\text{memory}}}$$

- **Analog Dominant Phase ($T < T_{\text{crossover}}$)**: When KV cache fits in ultra-wide on-chip SRAM ($8.0\text{ TB/s}$), digital attention latency is $< 10\ \mu\text{s}$, and stationary analog MVM dominates overall decode time.
- **Attention Wall Phase ($T > T_{\text{crossover}}$)**: As context length extends, KV cache spills into HBM ($1.2\text{ TB/s}$). Memory read traffic ($\mathcal{O}(T)$) and digital attention MACs ($\mathcal{O}(T)$ decode, $\mathcal{O}(T^2)$ prefill) overtake stationary crossbar projections.
- **System Takeaway**: Accelerated analog MVM alone cannot scale long-context inference without high-bandwidth digital attention co-processors and aggressive GQA compression.

---

## 5. Execution & Artifacts

Run the standalone chapter verification script:
```bash
python book/0053-kv-cache-hierarchy/kv_cache_hierarchy.py
```

Run test suite:
```bash
pytest tests/test_kv_hierarchy.py
```

Deterministic extract artifact:
`verification/circuit/results/kv-hierarchy-0053-extract.json`
