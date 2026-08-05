# Product Specification — Homebrew Analog LLM Accelerator (simulation)

Status: draft for v0.1. All numbers below are simulation targets, not silicon
measurements. Nothing here is a claim of speed or efficiency over a GPU.

## 1. Purpose

A hybrid analog-digital accelerator concept for running a small decoder-only
language model (transformer). Dense matrix-vector multiplications — attention
QKV, attention output, MLP up/down, and the head — are executed on crossbar
tiles of programmable conductance. Layer-norm, softmax, GELU, residual/bias
adds, and the embedding lookup are digital.

The product is simulated end to end in NumPy so the mapping rules, the
non-ideality model, and the accuracy/latency/energy trade-offs are exact and
reproducible before any hardware exists.

## 2. Matrix convention

For every linear layer we compute one or more `y = W @ x` with:

- each input element drives one crossbar **row** (via a DAC),
- each output is collected from one crossbar **column** (via the output stage),
- weights are stored as `[output, input]`.

Signed weights use differential encoding on two conductance arrays:

```text
W_eff = G_pos - G_neg        (normalized to [-1, 1] by the conductance span)
```

## 3. Non-ideal component model

| Block | Non-idealities | Parameters | Units |
|---|---|---|---|
| Weight storage | Finite resolution of programmable conductance | `g_bits`, `gmin`, `gmax` | conductance levels |
| Input DAC | Resolution, range clipping | `dac_bits`, `vin_max` | bits, V |
| Crossbar | Differential subtraction | (part of weight model) | — |
| Output ADC | Resolution, clipping, additive noise, gain/offset | `adc_bits`, `vout_max`, `adc_noise_std`, `adc_gain`, `adc_offset` | bits, V |

Explicitly **not** modelled (out of scope for v0.1): INL/DNL, IR drop, stuck
cells, conductance drift over temperature, converter energy, and circuit timing.

## 4. Signal envelope (v0.1 target values)

| Quantity | Target | Notes |
|---|---|---|
| Supply | single low-voltage rail | not simulated numerically |
| Input voltage range | `[-vin_max, vin_max]` | `vin_max = 1.0` (normalized) |
| Output ADC range | `[-vout_max, vout_max]` | chosen to fit headroom |
| Conductance range | `[gmin, gmax] = [0.05, 1.0]` | arbitrary normalized units |
| Weight resolution | `g_bits` (e.g. 6–14) | dominant weight-side error |
| ADC/DAC resolution | `adc_bits` / `dac_bits` | dominant activation-side error |

The error budget is reported as max absolute logit error and token agreement
against a float baseline on a fixed seed.

## 5. Physical ledger

Every run must report:

- `macs`: multiplies and accumulates performed on tiles (resolved `G+ - G-`
  cells only; zero padding adds no useful work);
- `tile_cycles`: lower bound on sequential block-MVM latency assuming uniform
  parallel tiles (`ceil(blocks / tile_count)`);
- `rewrites`: number of times a physical tile had to be re-programmed
  (temporal reuse when a matrix needs more tiles than on board);
- `tiles_used`: number of physical tile instances consumed.

These are *simulation* metrics, not wall-clock time or energy. No energy/latency
advantage over a GPU may be claimed from them.

## 6. Module boundary

| Module | Scope |
|---|---|
| `converters` | DAC/ADC quantization, clipping, noise, gain/offset |
| `crossbar` | weight -> conductance mapping, differential MVM |
| `tile` | one physical `rows x cols` programmable tile |
| `accelerator` | tiling, partial sums, temporal reuse, ledger |
| `transformer` | TinyGPT model, hybrid float/analog forward + generate |
| `report` | text report of config, ledger, and accuracy |

## 7. Acceptance

- `pytest` and `ruff check .` pass.
- A high-precision, noiseless accelerator reproduces the float baseline
  (token agreement ~1.0, logit error ~0) on the tiny model — this validates
  correct tiling and mapping, not a fabrication claim.
- A budget-constrained accelerator shows monotone, bounded degradation so the
  sensitivity to each non-ideality is visible.
- Every reported metric states its assumptions and units.
