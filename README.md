# Analog AI Machine

[![CI](https://github.com/vyquocvu/analog-ai-chip/actions/workflows/ci.yml/badge.svg)](https://github.com/vyquocvu/analog-ai-chip/actions/workflows/ci.yml)

**Study analog AI step by step, and design (in simulation) a product that runs
language models on crossbar tiles.** This repository contains two
complementary tracks:

1. **`book/` — sequential study track**: one ordered set of chapters — theory
   with executable `train.py` assertions plus DIY hardware builds — backed by
   `maths/` (a plain-language reference shelf). Read these in order.
2. **`analog_llm/` — product simulator**: the simulated design of a hybrid
   analog-digital accelerator that runs a small language model (transformer),
   with explicit converter/conductance non-idealities, plus a physical ledger
   and accuracy report.

> Every model here is software. No claim that this is "faster / more efficient
> than a GPU" is made unless backed by a measured (not assumed) ledger. NumPy
> computation is never described as physical analog acceleration.

---

## Track 1 — Sequential study (`book/`)

The book is one ordered path. It is also executable: theory chapters 0001–0004
start from a tiny hand-computable example encoded as an assertion in `train.py`;
chapter 0005 turns one weighted sum into a measurable analog circuit.

| # | Topic | Path |
|---|---|---|
| 0000 | System and boundaries | `book/0000-what-we-are-building/` |
| 0001 | Ohm + Kirchhoff = MVM | `book/0001-crossbar-mvm/` |
| 0002 | Signed differential weights | `book/0002-differential-pairs/` |
| 0003 | DAC/ADC, quantization, noise | `book/0003-converters-and-noise/` |
| 0004 | Tiling a matrix across arrays | `book/0004-tiling/` |
| 0005 | One analog neuron (hardware) | `book/0005-one-analog-neuron/` |

Reference: `maths/`, `docs/MODULE_STANDARD.md`, `docs/SAFETY.md`.

**Circuit simulation:** chapter 0005 verifies the neuron circuit in SPICE
(before building) through PySpice + ngspice — see
`book/0005-one-analog-neuron/sim_neuron.py`. Optional:
`brew install ngspice` then `pip install -e '.[sim]'`.

> **Tiếng Việt:** mỗi chương đều có `README.vi.md` ở cùng thư mục (bản tiếng Việt) bên cạnh `README.md` (tiếng Anh).

```bash
python book/0001-crossbar-mvm/train.py
python book/0002-differential-pairs/train.py
python book/0003-converters-and-noise/train.py
python book/0004-tiling/train.py
```

## Track 2 — Analog LLM product simulator (`analog_llm/`)

A decoder-only transformer (nanoGPT-style) runs end to end in NumPy. Every
dense matrix-vector multiplication — attention QKV, attention output, MLP
up/down, and the head — is routed through simulated crossbar tiles with
non-idealities. Layer-norm, softmax, GELU, bias/residual adds, and the
embedding lookup are digital.

```text
tokens ─► embedding
          └─► [LN ─► QKV ─► attention ─► out ─► LM]
                    └► [LN ─► MLP up ─► GELU ─► MLP down]
                                │
                       all linears routed through
                     DAC → crossbar tiles → ADC (partial sums digital)
```

Simulated non-idealities: programmable-conductance resolution (`g_bits`),
differential `G+/G−` encoding, DAC bits + clipping, ADC bits + clipping +
noise + gain/offset. Details: [`docs/PRODUCT_SPEC.md`](docs/PRODUCT_SPEC.md).

```bash
python scripts/run_llm_sim.py   # LLM-on-tiles demo + ledger/accuracy report
```

```text
analog_llm/
├── converters.py      DAC/ADC bits, clipping, noise, gain/offset
├── crossbar.py        weight → conductance, differential MVM
├── tile.py            one programmable rows×cols crossbar tile
├── accelerator.py     tiling, partial sums, temporal reuse, ledger
├── transformer.py     TinyGPT, hybrid float/analog inference
└── report.py          config + physical ledger + accuracy
```

---

## Install and verify

```bash
python -m pip install -e '.[dev]'
pytest                 # run tests for both tracks
ruff check .           # lint
python scripts/run_llm_sim.py
```

The demo reports a high-precision accelerator (should match float) and a
budget-constrained one (realistic degradation), together with
[`docs/ROADMAP.md`](docs/ROADMAP.md) and
[`docs/PRODUCT_SPEC.md`](docs/PRODUCT_SPEC.md).

## Honesty principles

- Distinguish three levels of claim: *functional*, *circuit/device*, *system*.
- Simulate non-idealities explicitly; never hide resolution/noise/clipping
  behind a single scalar "error".
- Do not derive `O(1)` or end-to-end energy/latency advantage from one ideal
  crossbar operation; every report must quote the physical ledger (MACs, tile
  MVM cycles, rewrites) and state its assumptions.

## License

MIT. See [LICENSE](LICENSE).
