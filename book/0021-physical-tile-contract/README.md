# 0021 — Physical Tile Contract (Gate R5)

> **Bản tiếng Việt:** [`README.vi.md`](README.vi.md)

This chapter inaugurates **Part VI (Profile-driven accelerator architecture)** and **Gate R5 (Profile-driven physical tile)** by formalizing the end-to-end compute tile contract. The architectural simulator (`analog_llm.CrossbarTile`) consumes the trio of validated device profiles (`crossbar-v1`, `dac-r2r-v1`, `adc-sar-v1`) rather than hand-chosen default constants.

---

## 1. End-to-End Signal Chain & Physical Abstraction

![Physical Tile End-to-End Signal Flow](diagrams/physical_tile_architecture.svg)

### Full Signal Conversion Flow:
1. **Digital Input Normalization**:
   The input activation vector $x \in \mathbb{R}^M$ is normalized to the DAC full-scale envelope:
   $$x_{\text{norm}} = \frac{x}{\|x\|_\infty} \cdot V_{\text{DAC,max}}, \quad V_{\text{DAC,max}} = 2.34375\text{ V}$$
2. **4-Bit Input DAC Conversion ([`dac-r2r-v1.json`](../../device_profiles/dac-r2r-v1.json))**:
   An R-2R ladder quantizes normalized voltages into 16 discrete wordline levels ($V_{\text{LSB}} = 156.25\text{ mV}$).
3. **Differential 2D Conductance Crossbar ([`crossbar-v1.json`](../../device_profiles/crossbar-v1.json))**:
   The normalized weight matrix $W_{\text{norm}} = W / \|W\|_\infty \in [-1, 1]$ is mapped onto differential 1T1R conductance cell pairs:
   $$(G_{ij}^+, G_{ij}^-) \in [10.0\,\mu\text{S}, 100.0\,\mu\text{S}]$$
   - Balanced zero: $w=0 \implies (G_{\min}, G_{\min}) = (10\,\mu\text{S}, 10\,\mu\text{S})$.
   - Kirchhoff current summation produces bitline currents: $I_j^+ = \sum_i G_{ij}^+ V_i$ and $I_j^- = \sum_i G_{ij}^- V_i$.
4. **Differential TIA & 4-Bit SAR ADC ([`adc-sar-v1.json`](../../device_profiles/adc-sar-v1.json))**:
   A transimpedance amplifier generates differential output voltage $V_{\text{diff}, j} = R_f (I_j^+ - I_j^-)$ with $R_f = 10\text{ k}\Omega$. A 4-bit SAR ADC quantizes $V_{\text{diff}}$ over the $\pm 2.5\text{ V}$ envelope into digital codes ($V_{\text{ADC,LSB}} = 312.5\text{ mV}$).
5. **Digital Scale Recovery**:
   The digital output codes are unscaled by the dynamic range factors:
   $$y \approx \frac{y_{\text{code}}}{\text{Span}} \cdot \frac{\|W\|_\infty \cdot \|x\|_\infty}{V_{\text{DAC,max}}}$$

---

## 2. Linearity & Error Across Matrix Classes

![Physical Tile Linearity and Error Response](diagrams/physical_tile_linearity.svg)

### Characterization Results ($16\times 16$ Tile, 100 Random Vectors):

| Canonical Matrix Class | Mean Relative Error (4-bit cell) | Mean Relative Error (6-bit cell) | Output Cosine Similarity |
|---|---|---|---|
| **Identity ($W = I$)** | $19.92\%$ | $19.92\%$ | $0.9825$ |
| **Positive Uniform ($W > 0$)** | $17.22\%$ | $16.61\%$ | $0.9868$ |
| **Negative Uniform ($W < 0$)** | $17.78\%$ | $17.19\%$ | $0.9867$ |
| **Mixed-Sign ($\mathcal{U}[-1, 1]$)** | $15.44\%$ | $15.21\%$ | $0.9882$ |
| **Rank-1 ($W = u v^T$)** | $48.33\%$ | $45.41\%$ | $0.8601$ |
| **Sparse ($90\%$ zeros)** | $17.49\%$ | $17.41\%$ | $0.9860$ |
| **Zero Matrix ($W = 0$)** | **$0.0000\%$** | **$0.0000\%$** | $1.0000$ |

### Key Observations:
- **Zero-Drift Invariance**: When $W = 0$, both positive and negative arrays draw identical leakage current $I_{\text{leak}} = G_{\min} \sum V_i$, yielding exact differential cancellation ($V_{\text{diff}} = 0.000\text{ V}$).
- Coarse 4-bit converter quantization is visible: the mixed-sign case retains $0.9882$ mean cosine similarity, while the low-rank case falls to $0.8601$. These are behavioral results, not device measurements.

---

## 3. Small-Array SPICE Equivalence

![Physical tile versus small-array SPICE error](diagrams/physical_tile_spice_equivalence.svg)

The same 4-bit tile built from `crossbar-v1`, `dac-r2r-v1`, and `adc-sar-v1` is replayed on all five committed 2×2 cases from 0012 and all five committed 4×4 cases from 0013. For case $c$ and output $j$:

$$e_c = \max_j |V_{\text{tile},c,j} - V_{\text{SPICE},c,j}|$$

$$E_{\max} = \max_c e_c, \qquad \text{PASS} \iff E_{\max} \le E_{\text{budget}}$$

The budget is frozen directly from `adc-sar-v1.json#/fields/quantization_error_v`:

$$E_{\text{budget}} = 0.15625\text{ V}$$

| Evidence set | Cases | Max $|V_{\text{tile}}-V_{\text{SPICE}}|$ | RMS error |
|---|---:|---:|---:|
| 0012 2×2 SPICE | 5 | 0.150124 V | 0.087369 V |
| 0013 4×4 SPICE | 5 | 0.142807 V | 0.075789 V |
| Combined | 10 | **0.150124 V — PASS** | 0.079836 V |

This is a `SYSTEM_SIMULATED` regression criterion for the named cases. It is not promoted to a verified physical-tile claim: `crossbar-v1` contains explicitly assumed device parameters, and the current `CrossbarTile` does not yet consume its IR-drop, variation, drift, stuck-fault, or I-V non-linearity fields.

---

## 4. Provenance & Profile Integration

All tile parameters are sourced directly via `analog_llm.profile_adapter.build_tile_factory_from_converter_profiles`:
```python
factory = build_tile_factory_from_converter_profiles(
    "device_profiles/crossbar-v1.json",
    "device_profiles/dac-r2r-v1.json",
    "device_profiles/adc-sar-v1.json",
    rows=16, cols=16, g_bits=4
)
tile = factory()
tile.program(W)
y = tile.forward(x)
```

---

## Verification

Run the characterization script and generate plots:
```bash
python book/0021-physical-tile-contract/physical_tile_contract.py
python book/0021-physical-tile-contract/diagrams/make_plots.py
python book/0021-physical-tile-contract/diagrams/make_equivalence_diagram.py
```
Committed extract: [`verification/circuit/results/physical-tile-0021-extract.json`](../../verification/circuit/results/physical-tile-0021-extract.json).
Tested by: [`tests/test_physical_tile_contract.py`](../../tests/test_physical_tile_contract.py).
