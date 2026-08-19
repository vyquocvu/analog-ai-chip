# 0046 — Architecture-neutral model manifest

Gate R10 begins with a functional contract rather than another physical claim.
`ModelManifest` describes decoder semantics before a checkpoint adapter or
execution engine sees tensors. It does **not** claim that the model is resident
on, or efficiently executable by, the proposed accelerator.

![Manifest validation flow](diagrams/manifest-flow.svg)

## Canonical semantics

The version-1 manifest names vocabulary, hidden/intermediate dimensions, layers,
query and key/value heads, context, storage dtype, weight tying and linear layout.
It distinguishes each choice instead of coercing it to GPT-2 behavior:

| Concern | Supported explicit values |
|---|---|
| normalization | `layernorm`, `rmsnorm` |
| position | learned table, RoPE |
| MLP | GELU, SwiGLU |
| attention | MHA, GQA, MQA |
| linear tensors | bias or no bias; canonical `[out, in]` |

Checkpoint adapters own any source-layout transpose. The manifest accepts only
the canonical `out_in` layout and exact tensor names/shapes, so a missing tensor,
extra tensor, unsupported semantic, or ambiguous layout fails closed.

## Tiny hand calculation

The deterministic assertion uses `V=5`, `H=4`, `L=1`, two query heads, one KV
head (`D=2`), `I=6`, context 3, FP16, RMSNorm, RoPE, SwiGLU, MQA, no biases and
tied embeddings.

* Parameters: embedding `5×4=20`; three norm scales `3×4=12`; Q/O `2×4×4=32`;
  K/V `2×2×4=16`; up/down/gate `3×6×4=72`; total **152 scalars**.
* Static projection work per layer and token: `32+16+72 = 120 MACs`. Dynamic
  token-token attention is digital and deliberately excluded from this number.
* Full-context KV storage: `3 tokens × 1 layer × K/V × 1 KV head × 2 values ×
  2 bytes = 24 bytes`.

These counts are functional inventory/analytical units. They are not circuit,
latency, energy, area, or hardware-residency evidence.

## Deterministic evidence

Run `pytest tests/test_model_manifest.py`. Tests cover the hand calculation,
exact inventory acceptance, missing tensors, invalid head relationships,
unsupported positions, ambiguous layouts and context overflow.
