# 0012 — 2×2 differential crossbar

This chapter scales the verified single current-mode column from 0007 into the
smallest true array: **two shared input rows feeding two independent output
columns**.  The purpose is topology verification, not yet device realism.

## What is being proved

For the repository matrix convention `W[output, input]`, the circuit must
implement

```text
y = RF · GSCALE · W @ (x − VREF)
```

with each signed weight represented by a differential pair:

```text
G+ = G0 + max(w, 0) · GSCALE
G- = G0 + max(-w, 0) · GSCALE
G+ - G- = w · GSCALE
```

Both output columns see the **same input voltages**.  Their conductance cells
and TIA readouts are independent, so changing weights in one output must not
change the mathematical result of the other output.

## Reference case

```text
x = [3.0, 2.1] V
VREF = 2.5 V
x - VREF = [0.5, -0.4] V

W = [[ 0.50, 0.25],
     [-0.50, 0.25]]
```

Because `RF · GSCALE = 1`, the hand result is

```text
y0 =  0.50·0.50 + 0.25·(-0.40) =  0.15 V
y1 = -0.50·0.50 + 0.25·(-0.40) = -0.35 V
```

`ideal_mvm()` is the executable NumPy oracle for this calculation.

## Circuit model

Each output has two current sums:

- positive conductance plane `G+` → TIA output `Vp`;
- negative conductance plane `G-` → TIA output `Vm`;
- differential result `Vout = Vm - Vp`.

As in 0007, each TIA branch is solved independently.  This is exact for the
current model because the branches are uncoupled except for their ideal shared
input voltage sources.

The SPICE model is currently a DC operating-point model with a high-gain VCVS
op-amp.  It does **not** yet model programmable-memory physics, line resistance,
parasitic RC, drift, or finite-bandwidth settling; those belong to later R3/R4
packages.

## Headroom

`headroom_report()` calculates all four TIA branch voltages (`Vp0`, `Vp1`,
`Vm0`, `Vm1`) before differential subtraction.  A differential output can look
reasonable while an internal branch has already exceeded a supply rail, so the
chapter fails closed on this distinction instead of silently clipping.

The nominal reference case stays inside the `[0, 5] V` envelope.  A deliberate
full-rail / maximum-weight case is included in the tests and must be reported as
overdrive.

## Run

Functional/reference tests require only the normal development dependencies:

```bash
pytest tests/test_crossbar_2x2.py -q
```

SPICE verification requires the repository simulation dependencies plus an
ngspice shared library:

```bash
python -m pip install -e '.[dev,sim]'
python book/0012-crossbar-2x2/crossbar_2x2.py
pytest tests/test_circuit_sim.py -q
```

## TDD evidence

The first PR commit added the contract tests before the implementation.  CI
failed specifically because `book/0012-crossbar-2x2/crossbar_2x2.py` did not
exist.  The implementation was added only after that RED state was observed.

## Completion boundary

This chapter is complete only when:

- shared-row / two-column functional tests pass;
- signed, zero/balanced, shape/range and headroom boundary tests pass;
- the 2×2 SPICE result agrees with the hand/NumPy result within the stated
  tolerance on a runner with working ngspice shared-library support;
- roadmap evidence points to the executable tests rather than to this prose.

A passing 2×2 ideal-conductance circuit does **not** prove ReRAM behavior or a
scalable physical array.  The next package is the 4×4 topology, not a system
performance claim.
