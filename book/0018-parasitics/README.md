# 0018 — Parasitic Capacitance, RC Dynamics & Transient Settling

> **Bản tiếng Việt:** [`README.vi.md`](README.vi.md)

This chapter extracts the **parasitic RC dynamics** and **transient settling times** of crossbar wordlines and bitlines, quantifying how distributed wire capacitance and cell junction/gate capacitance dictate the maximum safe MVM clock frequency across array dimensions ($N \in [4, 8, 16, 32, 64]$).

---

## 1. Distributed RC Transmission Network

![Distributed RC Parasitics Schematic](diagrams/rc_parasitics_schematic.svg)

Every crosspoint in a physical integrated crossbar contains distributed parasitic capacitances:
- **Wire Interconnect Capacitance**: $C_{\text{wire}} \approx 0.5\text{ fF}$ per cell pitch.
- **Cell / Access Transistor Capacitance**: $C_{\text{cell}} \approx 1.0\text{ fF}$ (drain/source junction + gate-drain overlap).
- **Segment Total**: $C_{\text{seg}} = C_{\text{wire}} + C_{\text{cell}} = 1.5\text{ fF}$.
- **Cumulative Bitline Capacitance**: $C_{\text{BL}} = N \cdot C_{\text{seg}}$ ($24\text{ fF}$ for $16\times 16$, $48\text{ fF}$ for $32\times 32$, $96\text{ fF}$ for $64\times 64$).

When an input voltage step is driven onto a row, the distributed $R_{\text{wire}} - C_{\text{seg}}$ network acts as a distributed RC transmission line.

---

## 2. Transient Step Response & Settling Time

![Transient Settling & Frequency Limits](diagrams/transient_settling.svg)

To perform analog matrix-vector multiplication without dynamic distortion, sampling must occur after the output current has settled within $\le 1\%$ of its steady-state value ($t \ge t_{\text{settle,1\%}}$).

### Transient Simulation Results ($R_{\text{wire}} = 1.0\,\Omega$, $C_{\text{seg}} = 1.5\text{ fF}$, Step $= 0.25\text{ V}$):

| Array Dimension $N$ | Rise Time $t_{\text{rise}}$ ($10\% \to 90\%$) | $1\%$ Settling Time $t_{\text{settle}}$ | Steady-State Current $I_{\text{ss}}$ | Max MVM Frequency $f_{\text{max}}$ |
|:---:|:---:|:---:|:---:|:---:|
| **$4\times 4$** | $16.5\text{ ps}$ | $20.0\text{ ps}$ | $24.90\,\mu\text{A}$ | $50.0\text{ GHz}$ |
| **$8\times 8$** | $16.5\text{ ps}$ | $20.0\text{ ps}$ | $24.70\,\mu\text{A}$ | $50.0\text{ GHz}$ |
| **$16\times 16$** | $16.5\text{ ps}$ | $20.5\text{ ps}$ | $24.30\,\mu\text{A}$ | $48.8\text{ GHz}$ |
| **$32\times 32$** | $16.5\text{ ps}$ | $21.5\text{ ps}$ | $23.00\,\mu\text{A}$ | $46.5\text{ GHz}$ |
| **$64\times 64$** | $12.5\text{ ps}$ | $23.5\text{ ps}$ | $19.50\,\mu\text{A}$ | $42.5\text{ GHz}$ |

---

## 3. Physical Insights & Bottleneck Hierarchy

1. **RC Settling vs Interconnect Bottleneck**:
   - The intrinsic RC settling time of small crossbar arrays ($16\times 16$ to $64\times 64$) is extremely fast ($\approx 20\dots 24\text{ ps}$), supporting theoretical clocking up to $> 40\text{ GHz}$.
   - Consequently, **crossbar RC settling is NOT the primary speed bottleneck** of an analog IMC accelerator.
2. **True System Bottlenecks**:
   - The actual throughput is limited by the **DAC conversion time** ($\approx 1\dots 5\text{ ns}$), **TIA op-amp closed-loop GBW/settling** ($\approx 2\dots 10\text{ ns}$ as characterized in Chapter 0014), and **SAR ADC conversion latency** ($\approx 5\dots 20\text{ ns}$).
   - Therefore, physical accelerator operating frequencies are typically set around **$100\text{ MHz} \dots 500\text{ MHz}$**, well within the crossbar RC settling envelope.

---

## Verification

Run the deterministic transient extraction and generate waveforms:
```bash
python book/0018-parasitics/parasitics.py
python book/0018-parasitics/diagrams/make_plots.py
```
Committed extract: [`verification/circuit/results/parasitics-0018-extract.json`](../../verification/circuit/results/parasitics-0018-extract.json).
Tested by: [`tests/test_parasitics.py`](../../tests/test_parasitics.py).
