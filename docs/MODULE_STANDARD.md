# Module Standard

Status: draft for Homebrew Analog AI v0.1.

## Design goals

- safe low-voltage operation;
- modules testable independently;
- explicit units and signal ranges;
- no hidden calibration assumptions;
- simulator and hardware share one matrix convention;
- replaceable conductance technologies.

## Logical modules

1. Power/reference
2. Controller
3. DAC/input driver
4. Conductance crossbar
5. Current-to-voltage/output stage
6. ADC/measurement
7. Activation/bypass
8. Backplane

## Matrix convention

For `y = W @ x`:

- each input vector element drives one crossbar row;
- each output is collected from one crossbar column;
- documentation stores weights as `[output, input]`;
- adapters must transpose only at a named boundary;
- physical diagrams must label row, column, input, and output indices.

## Signed weights

Conductance is non-negative. Signed weights use differential encoding:

```text
W = gain * (G_positive - G_negative)
```

A module must report its conductance range, zero-weight mapping, gain, and calibration revision.

## Initial electrical envelope

The exact values remain milestone decisions, but v0.1 modules must:

- use a single low-voltage supply or clearly documented derived rails;
- expose a common analog reference/virtual ground;
- define the safe input range at every connector;
- prevent digital I/O from exceeding controller ratings;
- provide labeled ground and reference test points.

No chapter may assume that a nominal rail-to-rail op-amp is linear at both rails without measurement.

## Digital protocol

The host/controller protocol will use versioned commands:

```text
HELLO
DESCRIBE
SELF_TEST
CALIBRATE
PROGRAM_WEIGHTS
RUN_VECTOR
READ_STATUS
```

Responses must include protocol version, hardware revision, calibration ID, units, and explicit error codes. Unsupported ranges fail closed rather than clipping silently.

## Module manifest

Every hardware revision must provide a machine-readable manifest containing:

```yaml
module_type: crossbar
hardware_revision: xb4x4-rev-a
rows: 4
columns: 4
signed_encoding: differential
supply_volts: TBD
input_range_volts: TBD
output_range_volts: TBD
calibration_schema: 1
```

## Evidence

A module is not complete when only the schematic exists. It needs assembly instructions, BOM, bring-up procedure, expected test-point measurements, measured results, calibration data, known failure modes, and photographs or diagrams matching the tested revision.
