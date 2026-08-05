# Calibration & power-down — 0005 analog neuron

Run in the order listed. **Power down before changing any component value.**

## Bring-up

1. Read `../docs/SAFETY.md` first.
2. With power off: confirm polarity and continuity of the +5 V and gnd rails,
   and that nothing shorts VCC to gnd.
3. Apply power with **no input signal**. Verify TP1 (5.0 V), TP3 (REF ≈ 2.5 V),
   TP4 (VREF ≈ 2.5 V), and the quiescent output TP8:
   - with `x1 = x2 = 2.5 V` expect `Vout ≈ 2.5 V`.
4. Confirm the summing node TP5 sits at the reference (virtual ground,
   `≈ 2.5 V`) — this is `headroom_neuron.py`'s result on real hardware.
5. Add **one input branch**; set `x2 = 2.5 V`, sweep `x1`, and record TP6 vs
   TP8. The output slope should be about `−0.50` over the linear range.
6. Add the **second** branch and check the combined swing matches
   `Vout = 2.5 − (0.50·(x1−2.5) + 0.25·(x2−2.5))`.

## Calibration record (fill per revision)

| Quantity | Ideal | Measured | Error |
|---|---|---|---|
| VREF | 2.500 V |  |  |
| Slope d(Vout)/dx1 | −0.500 |  |  |
| Slope d(Vout)/dx2 | −0.250 |  |  |
| Virtual-ground error | 0 V |  |  |
| Output noise (RMS) | < 5 mV |  |  |

The measured slopes absorb resistor tolerance and the measured virtual-ground
error absorbs op-amp offset/NL — both are the explicit non-idealities the sims
predict. Record them, don't tweak values silently.

## Saturation check (do it once, deliberately)

Increase `x1` until the output stops following the line and pins at a rail
(≈0 V or ≈5 V). Record that input. This is `sweep_neuron.py`'s clip point on
real hardware and proves where the linear region ends.

## Power-down

1. Remove input signals first.
2. Turn the supply off (or unplug USB) before touching/breadboarding.
3. Discharge any capacitors on the rails before rewiring.
