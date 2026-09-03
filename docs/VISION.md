# Project Vision: Dedicated Analog AI Text Appliance

> **Tiếng Việt:** Xem bản tiếng Việt tại [`docs/VISION.vi.md`](VISION.vi.md).

## Core Objective
Develop a **Dedicated Offline AI Text Appliance / AI Typewriter** for conversational and creative text generation (consisting solely of a Screen, Keyboard, and Text I/O processing pipeline), powered by custom **Analog Compute-in-Memory (CiM)** silicon.

![Pager-1 Dedicated Offline AI Communicator](assets/pager_product_hero.jpg)

Key characteristics:
1. **100% Offline & Air-Gapped**: The entire language model executes locally on analog hardware—no internet connectivity required, zero data telemetry.
2. **Instant-On & Real-Time Streaming**: Single-cycle analog matrix-vector multiplication (MVM) generating tokens with ultra-low latency.
3. **Exceptional Battery Life**: Low-power display (E-Ink / monochrome OLED) combined with analog subthreshold CiM compute (nW to sub-Watt range) enables days to weeks of standalone operation.

---

## 1. End-to-End Appliance Architecture

```text
┌────────────────────────────────────────────────────────────────────────────────┐
│                   DEDICATED ANALOG AI TEXT APPLIANCE                           │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  [ MECHANICAL / CHICLET KEYBOARD ] ─┐                                          │
│  (Prompt / Text Input)              │ (USB / I2C / SPI Scan)                   │
│                                     ▼                                          │
│                      ┌──────────────────────────────┐                          │
│                      │   HOST CONTROLLER (DIGITAL)  │                          │
│                      │  - RISC-V MCU / ARM SoC      │                          │
│                      │  - Tokenizer / Detokenizer   │                          │
│                      │  - UI & Text Buffer State    │                          │
│                      │  - LayerNorm / KV Cache      │                          │
│                      └──────────────┬───────────────┘                          │
│                                     │                                          │
│                                     │ High-speed bus (QSPI / FMC / Parallel)   │
│                                     ▼                                          │
│                      ┌──────────────────────────────┐                          │
│                      │  ANALOG CIM NEURAL ENGINE    │                          │
│                      │  - Differential Crossbars    │                          │
│                      │  - BitNet Ternary Weights    │                          │
│                      │  - Subthreshold Softmax      │                          │
│                      │  - Time-Domain PWM / TDC     │                          │
│                      └──────────────┬───────────────┘                          │
│                                     │                                          │
│                                     ▼ (Token IDs)                              │
│                      ┌──────────────────────────────┐                          │
│                      │  E-INK / MONO OLED DISPLAY   │                          │
│                      │  (Real-time Token Stream)    │                          │
│                      └──────────────────────────────┘                          │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Node Technology Selection

* **Prototyping / PoC Phase: 130nm (SkyWater SKY130)**
  * **Rationale:** Open-source PDKs (SkyWater/GlobalFoundries via Open-PDKs), accessible via multi-project wafer (MPW) services without corporate legal barriers or multi-million-dollar mask costs.
* **Commercial / Production Target: 28nm Planar / HKMG**
  * **Rationale:** The "sweet spot" for analog/mixed-signal design. 28nm offers balanced density, moderate mask costs, and sufficient voltage headroom to maintain signal-to-noise ratio (SNR) in DAC/ADC and analog crossbars—avoiding the severe analog scaling walls seen in sub-7nm FinFET nodes.
* *Commercial Foundry Note:* Cost-effective MPW slots ($8K–$30K) are suitable for funded R&D, but closed PDKs present friction for open-source reproducible research.

---

## 3. Architecture & Technical Innovations on Analog Silicon

![28nm ReRAM Crossbar Computing Core Infographic](assets/analog_crossbar_silicon.jpg)

To optimize LLM inference on analog hardware, the project explores four complementary pillars:

1. **Ternary LLM Architecture (BitNet b1.58):**
   * Quantizes weights to ternary values $W \in \{-1, 0, 1\}$.
   * Eliminates complex multi-bit weight DACs. Matrix multiplication reduces to a differential current-steering switch network ($W = 1 \implies G_{pos}=G_0, G_{neg}=0$; $W = -1 \implies G_{pos}=0, G_{neg}=G_0$; $W = 0 \implies G_{pos}=0, G_{neg}=0$) paired with compact SRAM-CiM or eNVM arrays.
2. **Subthreshold Analog Circuits (for Softmax):**
   * Leverages MOSFET subthreshold drain current ($I_{DS} \propto \exp\left(\frac{V_{GS}-V_{th}}{n V_T}\right)$) to compute the exponential function intrinsically at nano-Watt power budgets.
3. **Time-Domain Computing (PWM & TDC):**
   * Encodes activation values into pulse-width modulated (PWM) signals rather than voltage amplitudes, accumulates charge on integrating capacitors, and performs readout via Time-to-Digital Converters (TDCs).
4. **Hybrid Pipeline Architecture:**
   * Analog Crossbar tiles handle heavy linear projections ($Q, K, V, O$, MLP up/down).
   * Digital controller (e.g., RISC-V VexRiscv core) coordinates token sequencing, layer synchronization, and non-linear operations (RMSNorm/LayerNorm, residual adds, and sampling).

---

## 4. Physical Form Factor & User Experience

The final device is an **AI Communicator / Dedicated AI Typewriter**:

![Pager-1 Everyday Carry Lifestyle](assets/pager_in_hand_edc.jpg)

* **Hardware Interface:**
  * **Keyboard:** Compact mechanical keyboard (40%/60% or Ortholinear layout) or low-profile chiclet keyboard.
  * **Display:** E-Paper display (E-Ink 4.2"–6.0") or high-contrast monochrome Memory LCD for glare-free, eye-friendly reading.
  * **Chassis:** CNC aluminum or industrial 3D printed body, integrated Li-ion battery and USB Type-C charging.

![Pager-1 3D Exploded Teardown Diagram](assets/pager_exploded_view.jpg)
* **Software Experience:**
  * Zero bloated OS: Instant-on boot (< 1 second).
  * Distraction-free prompt interface: Type query $\rightarrow$ real-time analog token stream.
  * Local storage: Save sessions/notes as plain `.txt` or `.md` files to an SD card.

---

## 5. Scaling Strategy for Large Models (7B, 70B)

To scale beyond single-die capacity without compromising efficiency:

1. **eNVM Integration (ReRAM / MRAM):** Transition from SRAM to non-volatile resistive RAM on 28nm to increase cell density by 3–5× with zero standby leakage power.
2. **2.5D Chiplet Modular Packaging:** Standardized ~1B parameter chiplet tiles interconnected via high-bandwidth silicon interposers (UCIe standard).
3. **Pipeline Parallelism:** Standard PCIe accelerator cards hosting partitions of model layers, interconnected via high-speed inter-card links.

---

## 6. Open-Source EDA & Verification Stack

* **Xschem:** Schematic capture for analog/mixed-signal blocks.
* **Ngspice / Xyce:** Transistor-level circuit simulation for DC/transient sweeps, noise, temperature, and parameter extraction to `device_profiles/`.
* **Magic VLSI / KLayout:** Physical layout design and DRC verification.
* **Netgen:** Layout vs. Schematic (LVS) verification.
* **KiCad:** PCB system carrier design (integrating Host MCU, keyboard matrix, E-Ink display, power management, and Analog Chip socket).
* **Tape-Out Path:** Initial test cells via **Tiny Tapeout** (Sky130 analog pins), progressing to **Efabless ChipIgnite** (~$9,750 for 10mm² PoC carrier).
