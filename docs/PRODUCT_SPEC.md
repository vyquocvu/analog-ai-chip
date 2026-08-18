# Product Specification — Analog LLM Accelerator & Appliance

Status: simulation-verified design & system specification. The product is a hybrid analog-digital compute-in-memory (CiM) accelerator and dedicated offline text appliance concept. The repository establishes simulation-backed physical feasibility by tracing system parameters to circuit/device evidence.

Nothing here is a claim of fabricated silicon performance.

---

## 1. Purpose & Core Architecture

Dense matrix-vector multiplications (MVM) — attention QKV, attention output, MLP up/down, and linear heads — are mapped onto programmable-conductance crossbar tiles. Layer norm, softmax, GELU/SiLU, residual/bias adds, token sequencing, and embedding lookup remain digital unless a later design explicitly replaces them with analog subthreshold/time-domain primitives.

The design is verified across multiple levels:
1. Analytical and NumPy functional reference;
2. Behavioral non-ideal model;
3. Transistor-level SPICE circuit simulation;
4. Variation and process/temperature corner analysis;
5. Circuit/device parameter extraction (`device_profiles/`);
6. Multi-tile architecture and model-level simulation (`analog_llm/`);
7. End-to-end physical feasibility reporting.

See [`docs/SIMULATION_STACK.md`](SIMULATION_STACK.md) and [`docs/VISION.md`](VISION.md).

---

## 2. Matrix Convention & Signed Weight Encoding

For every linear layer computing $y = W \cdot x$:
- Each input element drives one crossbar row through a DAC/input driver stage;
- Each output is collected from one crossbar column through an output stage/ADC;
- Weights are stored as `[output, input]` shape;
- Adapters must transpose only at a named boundary.

Conductance is strictly non-negative ($G \ge 0$). Signed weights use differential encoding:

$$W_{\text{eff}} = \text{gain} \cdot (G_{\text{pos}} - G_{\text{neg}})$$

For Ternary BitNet b1.58 weights ($W \in \{-1, 0, 1\}$):
- $W = +1 \implies (G_{\text{pos}} = G_0, G_{\text{neg}} = 0)$
- $W = -1 \implies (G_{\text{pos}} = 0, G_{\text{neg}} = G_0)$
- $W = 0 \implies (G_{\text{pos}} = 0, G_{\text{neg}} = 0)$

---

## 3. Circuit-to-System Profile Contract

Physical and system parameters must not be silently hard-coded. `analog_llm/` consumes validated entries from `device_profiles/` for any run intended to represent physical implementation.

Evidence classes:

| Class | Meaning | May support physical claim? |
|---|---|---|
| `measured` | Extracted from real hardware measurement | Yes |
| `spice` | Extracted from named SPICE circuit simulation | Yes (simulation-backed) |
| `derived` | Computed analytically from traceable inputs | Yes (with derivation) |
| `assumed` | Design or sensitivity assumption | No |

---

## 4. Non-Ideal Component Model

Target non-ideality mechanisms include:

| Block | Mechanisms / Quantities |
|---|---|
| **Weight Storage** | $g_{\min}/g_{\max}$, finite states, programming variation, read noise, drift, stuck states |
| **Input Driver / DAC** | Resolution/ENOB, voltage range, clipping, offset/gain error, INL/DNL, settling time |
| **Crossbar Array** | Differential subtraction, line resistance, IR drop, parasitic capacitance, sneak paths |
| **Output Stage / ADC** | Full-scale range, resolution/ENOB, clipping, thermal noise, offset/gain error, TIA settling |
| **Environment / Supply** | Supply rail droop, temperature ($0^\circ\text{C}$–$85^\circ\text{C}$), and process corners |

---

## 5. Matrix Tiling & Temporal Reuse Scheduler

A logical weight matrix $W$ of shape $(R, C)$ mapped over physical tiles of shape $(T_r, T_c)$ is decomposed into block groups:

$$B_R = \lceil R / T_r \rceil, \quad B_C = \lceil C / T_c \rceil, \quad \text{blocks} = B_R \times B_C$$

Over $T$ available physical on-board tiles:
- $\text{mvm\_cycles} = \lceil \text{blocks} / T \rceil$
- $\text{programs} = \text{blocks}$
- $\text{rewrites} = \max(0, \text{blocks} - T)$

Partial sums across column groups are accumulated digitally per output row block.

---

## 6. Hardware Module Interface & Manifest

Every physical hardware module / PCB revision must provide a machine-readable manifest:

```yaml
module_type: crossbar
hardware_revision: xb4x4-rev-a
rows: 4
columns: 4
signed_encoding: differential
supply_volts: 5.0
input_range_volts: [0.0, 5.0]
output_range_volts: [0.0, 5.0]
calibration_schema: 1
```

Host controller command set: `HELLO`, `DESCRIBE`, `SELF_TEST`, `CALIBRATE`, `PROGRAM_WEIGHTS`, `RUN_VECTOR`, `READ_STATUS`.

---

## 7. Electrical Envelope & Safety Invariants

- Low-voltage educational electronics only ($5\text{V}$ USB, current-limited bench supply, or regulated Li-ion).
- Common analog virtual ground reference ($V_{\text{REF}} = V_{\text{DD}} / 2 = 2.5\text{V}$).
- Input voltages must stay strictly within documented common-mode limits.
- Never connect exposed project circuits directly to mains power.

---

## 8. Physical Ledger & Reporting Invariants

Every architecture run reports at minimum:
1. **Accuracy metrics** (vs float baseline, fixed seed): `token agreement`, `max |logit error|`.
2. **Physical ledger**:
   - `macs`: Resolved differential conductance operations;
   - `tile cycles`: Lower bound on sequential block-MVM cycles $\lceil \text{blocks} / T \rceil$;
   - `rewrites`: Number of physical tiles re-programmed (temporal reuse);
   - `programs`: Number of weight blocks programmed onto tiles ($\ge \text{rewrites}$).
3. **Invariants (enforced by `analog_llm/guardrail.py`)**:
   - Every number is a simulation quantity in stated units; no wall-clock or energy value may be presented as measured unless backed by hardware logs.
   - No unproven performance claim (`faster-than`, `gpu-equivalent`, `O(1) compute/energy`) may appear without a committed physical ledger and explicit disclaimer.
   - Every execution is deterministic (fixed random seed) and fails closed on invalid inputs.
