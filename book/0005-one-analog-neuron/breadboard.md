# Breadboard wiring — 0005 analog neuron (LM358, single 5 V supply)

The circuit is a two-input **inverting summer** with a **2.5 V virtual
reference** so it works on a single 5 V supply (see `sim_neuron_nonideal.py`
scenarios 1–2: without the reference it clips at 0 V).

LM358 is dual: op-amp **A** is a unity-gain buffer that makes the 2.5 V
reference low-impedance; op-amp **B** is the inverting summer.

## LM358 pinout (DIP-8)

```text
        +----v----+
   OUT1 |1      8| VCC (+5 V)
   IN1- |2      7| OUT2   (Vout)
   IN1+ |3      6| IN2-   (summing node n)
    VSS |4      5| IN2+   (VREF = 2.5 V)
        +--------+
```

## Step-by-step (do with power OFF until step 9)

1. Mount U1 across the breadboard center gap (pins 1-4 left, 5-8 right).
2. **Power rails:** VCC+ rail = `+5 V` (pin 8), VCC−/gnd rail = `0 V` (pin 4).
   Add C2 (10 µF) and one C1 (0.1 µF) between +5 V and gnd.
3. **Reference divider:** R3 = 10 k from `+5 V` rail to node **REF**; R4 = 10 k
   from node **REF** to `0 V`. Node REF ≈ 2.5 V.
4. **Reference buffer (U1A):** IN1+ (pin 3) -> node REF. IN1- (pin 2) -> OUT1
   (pin 1). Now OUT1 = 2.5 V, call it **VREF**.
5. **Summer non-inverting (U1B):** IN2+ (pin 5) -> **VREF** (from OUT1).
6. **Inputs:** input source **x1** -> R1 (2.0 k) -> node **n** (pin 6).
   input source **x2** -> R2 (4.0 k) -> node **n**.
7. **Feedback:** Rf (1.0 k) from OUT2 (pin 7) to node **n** (pin 6).
8. Add second C1 (0.1 µF) between VREF and gnd.
9. **Apply power** and verify per `testpoints.md` before adding signal.

## Node → breadboard location (pin-by-pin)

| Node | Wired to | Expected |
|---|---|---|
| VCC (+5 V) | rail + 8 | 5.0 V |
| GND | rail − 4 | 0 V |
| REF (divider out) | pin 3 | 2.5 V |
| VREF (buffered) | OUT1=pin1, pin5 | 2.5 V |
| n (summing node) | pin6 = R1+R2+Rf | 2.5 V (virtual ground) |
| OUT2 (Vout) | pin7 | 2.5 ± weighted swing |

## Safe input hints

- Keep inputs such that the output stays in `[0.5, 4.5]` V (away from the
  rails). For `|Vout − VREF| ≤ 2.5 V` the circuit is linear.
- Drive inputs from battery/USB-level sources referenced to the same gnd, or
  use the bench supply's second output; never drive two active outputs into the
  same node.

## Bring-up & power-down

Follow `calibration.md` for the bring-up sequence and always
**power down before changing component values.**
