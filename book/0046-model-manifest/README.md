# 0046 — Architecture-Neutral Model Manifest (Gate R10)

> **Bản tiếng Việt:** [`README.vi.md`](README.vi.md)

This chapter formalizes the **architecture-neutral model manifest (`ModelManifest`)** for decoder-only transformer architectures under **Gate R10 (Scalable model semantics & sharded checkpoints)**. It establishes an explicit, fail-closed functional contract before any checkpoint loader, memory manager, or simulation engine processes weight tensors.

---

## 1. Model Manifest Schema & Contract Flow

![Manifest Validation Flow](diagrams/manifest-flow.svg)

- **Purpose**: Provide a single source of truth for tensor dimensions, weight tying, normalization, positional encodings, and attention grouping without coercing non-GPT architectures into GPT-2 conventions.
- **Claim Level**: `FUNCTIONAL & ANALYTICAL SOFTWARE CONTRACT` — describes model semantics only; does not claim hardware residency or physical acceleration.
- **Canonical Tensor Layout**: All 2D weight matrices are strictly standardized to `out_in` layout ($[\text{dim}_{\text{out}}, \text{dim}_{\text{in}}]$).

---

## 2. Canonical Decoder Semantics

The version-1 manifest specifies every structural parameter explicitly:

| Dimension / Concern | Supported Explicit Values | Schema Constraint & Behavior |
|---|---|---|
| **Normalization** | `layernorm`, `rmsnorm` | `rmsnorm` disables additive bias vectors across all layers |
| **Positional Encoding** | `learned`, `rope` | `rope` eliminates learned position embedding tables |
| **MLP Activation** | `gelu`, `swiglu` | `swiglu` introduces explicit `mlp.gate_proj.weight` tensors |
| **Attention Mechanism** | `mha`, `gqa`, `mqa` | Enforces head divisibility ($\text{num\_heads} \pmod{\text{kv\_heads}} == 0$) |
| **Tensor Layout** | `out_in` | Simulator-native $[\text{out}, \text{in}]$ format; rejects ambiguous transposition |
| **Embedding Tying** | `tied_embeddings` (`bool`) | If `True`, excludes independent `lm_head.weight` from parameter count |
| **Precision Data Type** | `float16`, `bfloat16`, `float32`, `float64` | Dictates analytical KV-cache byte footprint |

---

## 3. Tier Evaluation & Hand-Calculated Reference

### Tiny Hand-Calculated Reference ($V=5, H=4, L=1, \text{QH}=2, \text{KVH}=1, I=6, \text{ctx}=3$)
A minimal hand-computable model (FP16, RMSNorm, RoPE, SwiGLU, MQA, tied embeddings) provides exact deterministic ground truth:
- **Parameter Count**:
  $$\text{Embeddings } (5 \times 4 = 20) + \text{Norm Scales } (3 \times 4 = 12) + W_{Q,O} (2 \times 4 \times 4 = 32) + W_{K,V} (2 \times 2 \times 4 = 16) + W_{\text{up},\text{down},\text{gate}} (3 \times 6 \times 4 = 72) = \mathbf{152 \text{ parameters}}$$
- **Static Projection MACs**: $32 + 16 + 72 = \mathbf{120 \text{ MACs/layer/token}}$ (Dynamic token-token attention is digital and tracked separately).
- **Full KV-Cache Footprint**: $3 \text{ tokens} \times 1 \text{ layer} \times 2 (\text{K/V}) \times 1 \text{ head} \times 2 \text{ values} \times 2 \text{ bytes} = \mathbf{24 \text{ bytes}}$.

### Multi-Tier Analytical Inventory Summary

| Tier Benchmark | Architecture Specs | Parameters | Layer Proj MACs | Full KV Cache | Step-1 KV Cache |
|---|---|---|---|---|---|
| **Hand-Calc Validation** | $1\text{L}, 4\text{D}, 2\text{Q}/1\text{KV}, \text{ctx}=3$ | $152$ | $120$ | $24\text{ B}$ | $8\text{ B}$ |
| **T0 (TinyGPT Ref)** | $2\text{L}, 64\text{D}, 4\text{Q}/4\text{KV}, \text{ctx}=16$ | $109,312$ | $49,152$ | $16.0\text{ KB}$ | $1.0\text{ KB}$ |
| **T1 (Scalable 1B GQA)** | $16\text{L}, 2048\text{D}, 16\text{Q}/4\text{KV}, \text{ctx}=2048$ | $852,559,872$ | $45,088,768$ | $64.0\text{ MB}$ | $32.0\text{ KB}$ |
| **T2 (Scalable 7B GQA)** | $32\text{L}, 4096\text{D}, 32\text{Q}/8\text{KV}, \text{ctx}=4096$ | $5,933,109,248$ | $177,209,344$ | $512.0\text{ MB}$ | $128.0\text{ KB}$ |

---

## 4. Fail-Closed Guardrails

The manifest rejects invalid or ambiguous configurations at instantiation:
1. **Head Divisibility**: Rejects configurations where `hidden_size` does not divide evenly by `num_attention_heads`, or where `num_attention_heads` does not divide evenly by `num_key_value_heads`.
2. **Attention Head Constraints**: Rejects MHA if $\text{KV} \neq \text{Q}$, MQA if $\text{KV} \neq 1$, and GQA if KV is not strictly between $1$ and $\text{Q}$.
3. **Exact Inventory Validation**: `validate_tensors()` requires an exact 1:1 match of all tensor names and shapes. Any missing or extraneous tensor raises `ValueError`.
4. **Context Overflow**: Rejects KV-cache queries for sequence lengths exceeding `context_length`.

---

## 5. Execution & Artifacts

Run the standalone chapter verification script:
```bash
python book/0046-model-manifest/model_manifest.py
```

Run test suite:
```bash
pytest tests/test_model_manifest.py
```

Deterministic extract artifact:
`verification/circuit/results/model-manifest-0046-extract.json`
