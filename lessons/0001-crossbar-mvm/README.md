# 0001 — Ohm + Kirchhoff = matrix-vector multiplication

A ReRAM cell stores a non-negative conductance `G`. Apply voltage `V` and Ohm's law gives the cell current:

```text
I = V × G
```

Currents meeting on an output line add, so Kirchhoff's current law gives a dot product. For two inputs and two outputs, use:

```text
V = [0.2, 0.5]
G = [[2.0, 1.0],
     [0.5, 3.0]]
```

Compute by hand:

```text
I0 = 2.0×0.2 + 1.0×0.5 = 0.9
I1 = 0.5×0.2 + 3.0×0.5 = 1.6
```

Therefore `I = G @ V = [0.9, 1.6]`.

Run `python lessons/0001-crossbar-mvm/train.py`. The assertions are the contract between this arithmetic and the implementation.

## Break it deliberately

Change one conductance to a negative value. The program rejects it because a physical conductance is non-negative. Lesson 0002 shows how two arrays represent signed neural-network weights without inventing negative conductance.

## Important boundary

The NumPy multiplication is a functional check of the equation. It does not simulate transistor dynamics, wire resistance, ADC energy, or timing.
