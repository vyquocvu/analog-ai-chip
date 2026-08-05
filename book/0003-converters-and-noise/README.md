# 0003 — DAC, ADC, quantization, and noise

The crossbar is analog, but model activations and outputs usually enter and leave through converters. Finite converter resolution changes values before and after the array.

For a signed `b`-bit converter, this lesson uses `qmax = 2^(b-1)-1` and:

```text
scale = max(abs(x)) / qmax
code  = round(x / scale)
x_hat = code × scale
```

The maximum rounding error of an unsaturated ideal converter is half one quantization step.

Run `python book/0003-converters-and-noise/train.py` to verify the bound and compare a deterministic noisy output with the ideal result.

## What this model does not include

This chapter does not yet model integral/differential non-linearity, ADC saturation recovery, conductance drift, IR drop, stuck cells, temperature, or converter energy. Those must be explicit features rather than hidden behind one Gaussian noise parameter.
