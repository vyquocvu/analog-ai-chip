# Chapter 0069 — Pocket Analog AI Communicator (Pager-1) Product Architecture

This chapter specifies the hardware architecture, physical form factor, bill of materials (BOM), and power delivery tree for a standalone, battery-powered **Pocket Analog AI Communicator ("AI Pager / Beeper")**, opening **Gate R18** (`WP18.1`).

---

## 1. Product Vision & Concept

The **Pager-1** is a pocket-sized, offline, air-gapped language communicator designed for focused text processing, laboratory logging, and field prompting. Unlike general-purpose smartphones that consume hundreds of milliwatts idling on wireless radios and LCD backlights, the Pager-1 relies on:
1. **Reflective Memory LCD Display**: Sunlight-readable Sharp LS027B7DH01; the official listing specifies $175\,\mu\text{W}$ for its stated update pattern.
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
│   400x240 @ 175 µW update    STM32U575VGT6        Differential Crossbars    │
│                                                                             │
│  [TACTILE QWERTY DOME]   ── [I2C TCA8418]     ── [DRV2605L LRA HAPTIC]      │
│   35 Keys + Jog Dial         Keypad Scanner       Silent Pager Buzz         │
│                                                                             │
│  [1200 mAh LI-PO POUCH]  ── [TI BQ25120A PMIC] ─ [3.3V / 2.5V / 1.0V RAILS]│
│   4.44 Wh Capacity           700 nA Iq Buck       91.5% VRM Efficiency      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Power Ledger Summary
* **Standby Mode**: $193.1\,\mu\text{W}$ assumed total, giving about $958\text{ days}$ analytically; bench validation is pending.
* **Active Inference Mode**: $44.5\text{ mW}$ assumed total, giving about $99.8\text{ hours}$ analytically.
* **Mixed Daily Usage**: about $47.6\text{ days}$ under the stated assumed duty cycle.
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
