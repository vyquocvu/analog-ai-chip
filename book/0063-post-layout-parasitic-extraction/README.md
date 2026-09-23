# 0063 — Post-Layout Parasitic Extraction & Analytical Settling

> **Bản tiếng Việt:** [`README.vi.md`](README.vi.md)

This chapter estimates geometry-based RC totals and an **analytical single-pole** step response. All technology coefficients and timing baselines are **assumed**. It does not run ngspice, solve a distributed RC network, or establish physical verification or Gate R16 signoff.

## 1. Geometry-based RC model

![RC estimate](diagrams/parasitic-extraction.svg)

`analog_layout.pex` groups shapes by net name and estimates lumped RC totals. Its SPEF serializer does not establish extracted electrical connectivity or a validated distributed bitline topology.

Assumed coefficients include M4/M5 resistance 1.20 ohm/µm, substrate capacitance 0.08 fF/µm, coupling capacitance 0.12 fF/µm per edge, and Via4 contact resistance 1.50 ohm/contact. These are not foundry-qualified or measured values. No via capacitance is calculated by this extractor.

The deterministic 16×16 example produces 291 nets, 610.42 ohm total resistance and 33.18 fF total capacitance. These are model totals, not measurements.

## 2. Single-pole settling estimate

![Analytical response](diagrams/transient-settling-waveform.svg)

For mean net resistance R and capacitance C, the model uses assumed intrinsic capacitance 20 fF, driver resistance 50 ohm and coupling multiplier 1.5:

`tau_post = 1.18 ns + 0.40 ns + R_driver × (1.5 C) + 0.5 R × (20 fF + 1.5 C)`

RC products are converted from ohm·fF to ns. The **1.18 ns baseline and 0.40 ns increment are assumptions**, not extracted time constants. Averaging does not preserve worst-case paths. The resulting tau is approximately 1.58003 ns; most of its 33.9% increase comes from the assumed 0.40 ns increment.

For a normalized step starting at zero:

`y(t) = 1 − exp(−t/tau)`

`t(f) = −tau × ln(1 − f)`

Thus 90% takes `ln(10) × tau`, and 99.9% takes `ln(1000) × tau`, not 1.20 and 1.55 times tau. Monotonicity is imposed by this model, not evidence that a real circuit has no ringing.

## 3. Assumed aperture comparison — FAILED

| Quantity | Analytical estimate |
|---|---:|
| 90% settling | 3.64 ns |
| 99.9% settling | 10.91 ns |
| Assumed sampling aperture | 5.00 ns |
| Aperture / target settling time | 0.458× |
| Meets default 99.9% target | No |

`target_accuracy_pct` governs the margin and pass/fail result; named 90% and 99.9% outputs remain fixed reference thresholds. The configuration requires finite `0 < target_accuracy_pct < 100` and a finite positive `sampling_window_ns`. Equality at the aperture passes the analytical comparison only.

No bit-error rate, ADC accuracy, PVT behavior, noise, distributed settling, or physical feasibility is verified. The unused ReRAM resistance config field is not a device model. The legacy JSON key `transient_settling_signoff` contains an analytical estimate only; `evidence_class: assumed` and `physical_verified: false` apply throughout. No device profile is published or promoted.

## 4. Reproduction

```bash
python book/0063-post-layout-parasitic-extraction/parasitic_extraction.py
pytest tests/test_layout_pex.py
```

The script regenerates both SVG figures and `verification/layout/results/parasitic-extraction-0063-extract.json` deterministically. Tests check the exponential identity, alternative targets, aperture boundaries, invalid configurations, and evidence labels. This scoped correction does not repair STA/LVS or update gate claims elsewhere.
