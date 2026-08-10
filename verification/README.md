# Verification Evidence

This directory is reserved for reproducible evidence that moves the design from functional correctness toward physical feasibility.

```text
verification/
├── functional/      analytical and NumPy reference checks
├── circuit/         ngspice/PySpice and Xyce circuit analyses
├── monte_carlo/     statistical variation runs
├── corners/         voltage / temperature / device-model corners
├── architecture/    tile, scheduler, buffer and traffic checks
├── model_accuracy/  logits, token agreement, perplexity/accuracy
└── reports/         generated feasibility reports
```

Do not commit a plot without preserving enough information to regenerate or verify the values behind it. Preferred evidence is script + source model/netlist + machine-readable result + generated visualization.

Circuit extraction should publish reusable parameters into `device_profiles/`. `analog_llm/` should consume those profiles for any claim intended to represent a proposed physical device.
