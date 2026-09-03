# Chapter 0069 — Pocket Analog AI Communicator (Pager-1) Product Architecture

This chapter specifies the hardware architecture, physical form factor, bill of materials (BOM), and power delivery tree for a standalone, battery-powered **Pocket Analog AI Communicator ("AI Pager / Beeper")**, opening **Gate R18** (`WP18.1`).

---

## 1. Product Vision & Concept

The **Pager-1** is a pocket-sized, offline, air-gapped language communicator designed for focused text processing, laboratory logging, and field prompting. Unlike general-purpose smartphones that consume hundreds of milliwatts idling on wireless radios and LCD backlights, the Pager-1 relies on:
1. **Reflective Memory LCD / E-Paper Display**: Sunlight-readable display consuming only $15\,\mu\text{W}$ in static text hold.
2. **Analog Compute-in-Memory Neural Core**: Zero-leakage non-volatile ReRAM crossbars evaluating matrix-vector multiplications directly at the physical storage cells.
3. **Dedicated Tactile Input**: Full 35-key QWERTY thumb pad with tactile metal domes and side rotary jog dial for single-handed navigation.
4. **Month-Long Standby Autonomy**: Powered by an integrated $1200\text{ mAh}$ Li-Po battery and ultra-low quiescent current PMIC ($700\text{ nA}$ $I_q$), delivering $>30\text{ days}$ of standby life.

---

## 2. Hardware Architecture & Power Ledger

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                 POCKET ANALOG AI COMMUNICATOR (PAGER-1)                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [2.7" SHARP MEMORY LCD] ── [HOST CONTROLLER] ── [ANALOG CIM MEZZANINE]     │
│   400x240 @ 15 µW hold       STM32U5 / RP2040     Differential Crossbars    │
│                                                                             │
│  [TACTILE QWERTY DOME]   ── [I2C TCA8418]     ── [DRV2605L LRA HAPTIC]      │
│   35 Keys + Jog Dial         Keypad Scanner       Silent Pager Buzz         │
│                                                                             │
│  [1200 mAh LI-PO POUCH]  ── [TI BQ25120 PMIC] ── [3.3V / 2.5V / 1.0V RAILS]│
│   4.44 Wh Capacity           700 nA Iq Buck       91.5% VRM Efficiency      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Power Ledger Summary
* **Standby Mode**: $35.6\,\mu\text{W}$ total consumption ($9.6\,\mu\text{A}$ at $3.7\text{V}$) $\implies \mathbf{5,200\text{ hours} \approx 216\text{ days}}$ standby autonomy (Target $\ge 30\text{ days}$).
* **Active Inference Mode**: $44.8\text{ mW}$ total consumption (Host MCU + Memory LCD refresh + Analog Crossbars) $\implies \mathbf{99\text{ hours}}$ continuous generation (Target $\ge 40\text{ hours}$).
* **Mixed Daily Usage**: $\mathbf{41.5\text{ days}}$ (assuming 2 hours of active inference and 22 hours of standby per day).
* **Thermal Envelope**: Natural passive convection maintains peak surface temperature at $25.4^\circ\text{C}$ ($< 45^\circ\text{C}$ skin touch limit).

---

## 3. Extraction & Deterministic Evidence

Run the architecture sign-off extraction:
```bash
python book/0069-pager-product-architecture/pager_product_architecture.py
```

Artifacts generated:
* `verification/layout/results/pager-architecture-0069-extract.json`
* `book/0069-pager-product-architecture/diagrams/pager-architecture-0069.svg`
