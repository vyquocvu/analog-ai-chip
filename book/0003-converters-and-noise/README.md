# 0003 — DAC, ADC, quantization, and noise

> **Reading time:** ~12 min · **Run:** `python book/0003-converters-and-noise/train.py`
> **Bản tiếng Việt:** [`README.vi.md`](README.vi.md)

The crossbar is analog, but the values a model deals with — activations in,
weighted sums out — enter and leave the analog domain through **converters**. A
converter cannot represent a continuous value exactly; it has finite
resolution. This chapter makes that numerical cost explicit and adds a first,
honest model of read noise.

## 1. Where the converters sit

```text
  x (digital) ──► [DAC] ──► V ──► [crossbar] ──► I ──► [ADC] ──► ŷ (digital)
                   finite bits              finite bits + noise
```

- The **DAC** turns a digital activation into a voltage. It can only hit a
  discrete set of levels.
- The **ADC** measures the summed current (after conversion to voltage) and
  quantizes it to discrete codes.

Both are *value-changing*. An ideal crossbar with real converters is no longer
an exact `G @ x`.

## 2. The symmetric quantization model

For a signed `b`-bit converter this chapter uses `qmax = 2^(b-1) − 1` and a
scale set by the largest magnitude in the signal:

```text
scale = max(|x|) / qmax
code  = round(x / scale)
x_hat = code × scale
```

`scale` is one quantum step; `code` is clipped to `[−qmax, +qmax]`. Because the
mapping is symmetric about zero, `Q(−x) = −Q(x)`.

![Symmetric quantization staircase (b = 4)](diagrams/quantization.svg)

The red dashed line is the ideal `x̂ = x`. The blue staircase is what the
converter actually reports.

## 3. Error bound

The maximum rounding error of an unsaturated, ideal converter is **half one
quantization step**:

```text
max |x_hat − x| ≤ scale / 2
```

For `b = 4`, `scale = max|x| / 7`; with `max|x| = 1.0` that is `scale = 1/7`
and `scale/2 ≈ 0.0714`. The example point `x = 0.2` maps to code
`round(0.2 × 7) = 1`, i.e. `x̂ = 1/7 ≈ 0.1429` — an error of about `0.057`.

## 4. Run it

```bash
python book/0003-converters-and-noise/train.py
```

It verifies the `scale/2` bound for `values = [−1, −0.3, 0, 0.2, 1]`, then adds
a **deterministic** Gaussian noise sample (fixed seed `7`) to the ideal crossbar
output `[0.9, 1.6]`. The result is reproducible on any machine.

```text
quantized: [-1.   -0.2857  0.   0.1429  1.   ]
max quantization error: 0.0571        (≤ 0.0714)
deterministic noisy sample: [0.9000, 1.6030]
```

## 5. Noise: why it is explicit, not a blur

The ADC's real output also carries noise (thermal, reference, aperture
uncertainty). Here it is modelled as one `noise_std`, but it is added to the
vector **explicitly** with a fixed seed — it is a visible input, not a hidden
"error". That is the difference the project insists on: name every non-ideality
as its own parameter rather than folding it into a single vague number.
(Compare how `analog_llm.converters` adds `gain`, `offset`, and `noise_std`
separately.)

## 6. What this model does not include

This chapter does **not** yet model:

- integral/differential non-linearity (INL/DNL);
- ADC saturation recovery (what happens when the input exceeds the range);
- conductance drift, IR drop, stuck cells, or temperature;
- converter energy or timing.

Those must be added as explicit features later — not hidden behind the one
Gaussian `noise_std`. The `analog_llm` simulator already adds `adc_gain`,
`adc_offset`, clipping, and finite weight bits on top of this foundation.

## 7. Exercises

1. For `bits = 8`, what is `qmax`? If `max|x| = 2.0`, what is `scale`? Place
   `x = 0.5` on the staircase and compute `x̂`.
2. Try `bits = 2` (so `qmax = 1`). What are the only possible outputs, and why
   is the error bound now very large?
3. Confirm the symmetry: run the quantizer on `[0.3, −0.3]` and check
   `Q(−x) = −Q(x)`.
4. Modify the train script: add a second, much larger `noise_std` and observe
   how `max quantization error` is unaffected while the "measurement" is noisier.

## 8. Next

Chapter 0004 (`tiling`) shows how a logical LLM matrix that is far larger than
one physical crossbar is split into tiles and accumulated. Then the
`analog_llm` simulator combines *this* converter model with differential
weights and tiling to run a full tiny transformer (`scripts/run_llm_sim.py`).
