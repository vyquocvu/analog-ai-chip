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

## Rule for claims

`assumed` profiles are allowed for exploration but cannot support claims such as "the proposed ADC has X ENOB" or "the accelerator consumes Y energy/token". Such claims require `spice`, `derived` from verified inputs, or `measured` evidence.

`ideal.json` is intentionally functional-only and exists to verify mapping correctness.