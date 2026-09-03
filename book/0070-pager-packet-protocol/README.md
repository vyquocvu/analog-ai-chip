# Chapter 0070 — Host-to-CiM Binary Packet Protocol & Virtual Pager Runtime

This chapter designs the binary host-to-accelerator communication protocol, packet framing, CRC-16 integrity verification, and virtual terminal display runtime for the **Pocket Analog AI Communicator (Pager-1)**, closing **Gate R18** (`WP18.2`).

---

## 1. Protocol Architecture & Packet Framing

To communicate over physical serial peripheral interfaces (SPI / QSPI) between the host MCU and analog crossbar mezzanine with zero corrupted conductance writes:

```text
┌───────────┬───────────┬───────────┬───────────┬───────────────────┬───────────┐
│ SYNC (2B) │  CMD (1B) │  SEQ (1B) │  LEN (2B) │ PAYLOAD (N BYTES) │ CRC16 (2B)│
│ 0xAA 0x55 │  Opcode   │  0..255   │ BigEndian │ Quantized Vectors │  CCITT    │
└───────────┴───────────┴───────────┴───────────┴───────────────────┴───────────┘
```

### Supported Command Opcodes
* `0x01`: `CMD_HELLO` — Probe accelerator revision, tile dimensions, and online status.
* `0x02`: `CMD_CALIBRATE` — Initiate DAC/ADC auto-zero offset cancellation.
* `0x10`: `CMD_PROGRAM_WEIGHTS` — Write non-volatile conductances to RRAM array cells.
* `0x20`: `CMD_RUN_VECTOR` — Stream input DAC voltage activations into the crossbar rows.
* `0x21`: `CMD_READ_OUTPUT` — Retrieve integrated column current ADC codes into host memory.
* `0x30`: `CMD_STATUS_IRQ` — Query interrupt status flags (done, busy, thermal alert).

---

## 2. Virtual Pager Display Terminal

The `PagerTextBuffer` models the 400×240 monochrome display with word-wrapping, scrolling, and a dedicated status header:

```text
+----------------------------------------+
| PAGER-1 // OFFLINE AI | BAT:98%        |
+----------------------------------------+
| > Summarize test results               |
| AI: MVM peak=0.063A                    |
| Tokens streamed successfully via       |
| SPI bus.                               |
+----------------------------------------+
| [STREAM COMPLETE]                      |
+----------------------------------------+
```

---

## 3. Extraction & Deterministic Evidence

Run the protocol verification:
```bash
python book/0070-pager-packet-protocol/pager_packet_protocol.py
```

Artifacts generated:
* `verification/circuit/results/pager-protocol-0070-extract.json`
* `book/0070-pager-packet-protocol/diagrams/pager-protocol-0070.svg`
