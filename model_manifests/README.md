# Model manifests

`ModelManifest` is the architecture-neutral semantic contract used by R10 before a checkpoint is mapped into the simulator.

A manifest describes **model semantics**, not accelerator capability. It records decoder dimensions and the choices that affect tensor meaning:

- LayerNorm vs RMSNorm;
- learned position embeddings vs RoPE;
- GELU vs SwiGLU;
- linear bias vs no bias;
- tied vs untied token/LM-head embeddings;
- MHA, GQA, or MQA through explicit query-head and KV-head counts;
- checkpoint dtype and maximum context.

Canonical matrix tensors use `[out, in]`. Embeddings use `[rows, cols]`. Inventory validation fails closed instead of guessing a transpose/layout.

`tiny-decoder-v1.json` is the hand-computable schema-v1 fixture used by `tests/test_model_manifest.py`. Its expected values are:

| Quantity | Value |
|---|---:|
| unique parameters | 424 |
| dense projection MACs / token / layer | 128 |
| KV bytes / token / layer | 32 |
| KV bytes at 8 tokens across 2 layers | 512 |
| attention grouping | MHA |

These values verify accounting and shape semantics only. They are not latency, energy, area, or physical-execution claims.
