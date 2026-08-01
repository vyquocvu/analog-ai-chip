# Roadmap

## Phase 1 — Crossbar foundations

- [x] Ideal Ohm/Kirchhoff MVM
- [x] Signed weights through differential pairs
- [x] Symmetric converter quantization
- [x] Explicit matrix tiling and partial sums

## Phase 2 — Non-ideal array model

- [ ] Conductance range and device programming quantization
- [ ] Read noise separated from programming variation
- [ ] Drift over time
- [ ] Stuck-at faults
- [ ] IR-drop approximation
- [ ] ADC clipping and configurable accumulation precision

## Phase 3 — Neural network mapping

- [ ] PyTorch `nn.Linear` adapter without disabling gradients globally
- [ ] Hugging Face GPT-style `Conv1D` adapter
- [ ] Per-channel and per-tile calibration
- [ ] Static projection and MLP mapping
- [ ] Dynamic attention/KV-cache boundary chapter

## Phase 4 — Architecture ledger

- [ ] Tile scheduler and dataflow model
- [ ] DAC/ADC cycle accounting
- [ ] Buffer, NoC, and partial-sum traffic
- [ ] Area, latency, and energy estimates with explicit assumptions
- [ ] FPGA prototype for the digital shell

## Phase 5 — Hardware-aware training

- [ ] Quantization-aware training
- [ ] Noise-aware fine-tuning
- [ ] Fault and drift robustness evaluation
- [ ] Reproducible perplexity experiments

Every completed item must include a readable lesson, deterministic executable evidence, tests, and a statement of model limitations.
