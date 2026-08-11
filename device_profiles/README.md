# Device Profiles

`device_profiles/` is the contract between circuit/device verification and the architecture/LLM simulator.

A profile contains parameters that may be consumed by `analog_llm`, but every physical parameter must carry provenance. Do not copy convenient values from papers or invent defaults and then label the resulting system as verified.

## Evidence classes

- `measured`: extracted from physical hardware.
- `spice`: extracted from a named SPICE simulation.
- `derived`: calculated from other traceable evidence.
- `assumed`: explicit design assumption for sensitivity analysis only.

## Required provenance

Every profile must state:

- profile name and version;
- evidence class;
- simulator/tool and version when known;
- source schematic/netlist/model paths;
- extraction script or command;
- analysis type (`op`, `dc`, `tran`, `ac`, `noise`, `monte_carlo`, `corner`, etc.);
- supply/temperature/process or device-model conditions when relevant;
- units for physical quantities;
- limitations.

## Field-level evidence

Each physical parameter in a profile's `fields` map must carry a `value`,
`unit`, and `evidence_class`. A profile intended to support a physical claim
(`physical_claim=True`) must:

- include a non-empty `fields` map;
- mark every field `measured`, `spice`, or `derived`;
- never mark a field `assumed` (assumed evidence fails closed);

Per-field validation is enforced by `analog_llm/device_profile.py`.

## Contract example

`crossbar-column-v1.json` is the first SPICE-backed profile: extracted
deterministically from 0007 column solves (plus the 0005 rail model) by
`verification/circuit/extract_crossbar_column.py`. Regenerate with
`python verification/circuit/extract_crossbar_column.py`.

`analog_llm.profile_adapter` maps a physical profile's `fields` into
`CrossbarTile` configuration (e.g. `gmin = g0_s`, `gmax = g0_s + gscale_s_per_w`,
converter envelopes from the rail headroom). The legacy `dac`/`crossbar`/`adc`
section layout (`ideal.json`) maps the functional reference only and cannot
support a physical tile configuration. Consume with:

```python
from analog_llm import build_tile_factory
factory = build_tile_factory(
    "device_profiles/crossbar-column-v1.json", 64, 64,
    g_bits=8, dac_bits=8, adc_bits=8,
)  # physical_claim=True by default; fails closed otherwise
```

`dac-r2r-v1.json` is the first SPICE-backed converter profile: a 4-bit R-2R
ladder DAC (`book/0009-dac-r2r/r2r_dac.py`) swept over all 16 codes, emitted by
`verification/circuit/extract_dac_r2r.py`. It captures `lsb_v`, `full_scale_v`,
`offset_v`, `gain_v_per_v`, `max_inl_v` and `max_dnl_v` (`spice`); settling,
supply sensitivity and mismatch are deferred (documented in `provenance.limitations`).

## Rule for claims

`assumed` profiles are allowed for exploration but cannot support claims such as "the proposed ADC has X ENOB" or "the accelerator consumes Y energy/token". Such claims require `spice`, `derived` from verified inputs, or `measured` evidence.

`ideal.json` is intentionally functional-only and exists to verify mapping correctness.