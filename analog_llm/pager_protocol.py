"""Pocket Analog AI Communicator (Pager-1) Protocol Engine & Virtual Appliance.

Implements the binary host-to-accelerator framing protocol over SPI/QSPI, CRC-16
data integrity, display text framebuffer, and streaming token execution pipeline.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

import numpy as np


class PagerCommand(IntEnum):
    """Command opcodes for the host-to-crossbar SPI interface."""

    HELLO = 0x01
    CALIBRATE = 0x02
    PROGRAM_WEIGHTS = 0x10
    RUN_VECTOR = 0x20
    READ_OUTPUT = 0x21
    STATUS_IRQ = 0x30
    ERROR_RESP = 0x7F


# Frame Sync Delimiters
SYNC_BYTE_0 = 0xAA
SYNC_BYTE_1 = 0x55


def compute_crc16_ccitt(data: bytes) -> int:
    """Calculate 16-bit CRC-CCITT (poly 0x1021, init 0xFFFF)."""
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


@dataclass(frozen=True)
class PagerPacket:
    """A framed host-to-accelerator communication packet."""

    cmd: PagerCommand
    seq: int
    payload: bytes

    def serialize(self) -> bytes:
        """Encode packet into framed binary wire representation with CRC-16."""
        header = struct.pack(
            ">BBBBH",
            SYNC_BYTE_0,
            SYNC_BYTE_1,
            int(self.cmd),
            self.seq & 0xFF,
            len(self.payload),
        )
        body = header[2:] + self.payload  # CRC covers cmd, seq, len, payload
        crc = compute_crc16_ccitt(body)
        return header + self.payload + struct.pack(">H", crc)

    @classmethod
    def deserialize(cls, raw: bytes) -> PagerPacket:
        """Parse binary frame and verify CRC-16 integrity."""
        if len(raw) < 8:
            raise ValueError(f"Packet too short ({len(raw)} bytes < 8 min)")
        s0, s1, cmd_val, seq, length = struct.unpack(">BBBBH", raw[:6])
        if s0 != SYNC_BYTE_0 or s1 != SYNC_BYTE_1:
            raise ValueError(f"Invalid frame sync: 0x{s0:02X} 0x{s1:02X}")
        if len(raw) != 6 + length + 2:
            raise ValueError(f"Packet length mismatch: expected {6 + length + 2}, got {len(raw)}")

        payload = raw[6 : 6 + length]
        received_crc = struct.unpack(">H", raw[6 + length :])[0]
        expected_crc = compute_crc16_ccitt(raw[2 : 6 + length])
        if received_crc != expected_crc:
            raise ValueError(f"CRC-16 mismatch: got 0x{received_crc:04X}, expected 0x{expected_crc:04X}")

        return cls(cmd=PagerCommand(cmd_val), seq=seq, payload=payload)


class PagerTextBuffer:
    """Manages the 400x240 monochrome virtual pager display."""

    def __init__(self, cols: int = 40, rows: int = 12) -> None:
        self.cols = cols
        self.rows = rows
        self.header_title = "PAGER-1 // OFFLINE AI"
        self.battery_pct = 98
        self.lines: list[str] = []
        self.status_bar = "READY"

    def clear(self) -> None:
        self.lines.clear()

    def append_line(self, line: str) -> None:
        """Append a discrete line, wrapping if necessary."""
        words = line.split(" ")
        cur = ""
        for w in words:
            if not cur:
                cur = w
            elif len(cur) + 1 + len(w) <= self.cols:
                cur += " " + w
            else:
                self.lines.append(cur)
                cur = w
        if cur:
            self.lines.append(cur)
        if len(self.lines) > self.rows - 2:
            self.lines = self.lines[-(self.rows - 2) :]

    def append_text(self, text: str) -> None:
        """Append text with automatic word wrapping."""
        words = text.split(" ")
        current_line = self.lines[-1] if self.lines else ""
        if self.lines:
            self.lines.pop()

        for w in words:
            if not current_line:
                current_line = w
            elif len(current_line) + 1 + len(w) <= self.cols:
                current_line += " " + w
            else:
                self.lines.append(current_line)
                current_line = w
        if current_line:
            self.lines.append(current_line)

        # Scroll if exceeding row capacity
        if len(self.lines) > self.rows - 2:
            self.lines = self.lines[-(self.rows - 2) :]

    def render_ascii_screen(self) -> str:
        """Render a faithful terminal preview of the 400x240 pager LCD screen."""
        sep = "+" + "-" * self.cols + "+"
        header = f"| {self.header_title} | BAT:{self.battery_pct}% |".ljust(self.cols + 1) + "|"
        out = [sep, header, sep]

        for i in range(self.rows - 2):
            if i < len(self.lines):
                line = self.lines[i].ljust(self.cols)
            else:
                line = " " * self.cols
            out.append(f"|{line}|")

        footer = f"| [{self.status_bar}]".ljust(self.cols + 1) + "|"
        out.append(sep)
        out.append(footer)
        out.append(sep)
        return "\n".join(out)


class PagerInferenceEngine:
    """Executes offline prompt inference through the crossbar SPI packet interface."""

    def __init__(self, in_features: int = 16, out_features: int = 16) -> None:
        self.in_features = in_features
        self.out_features = out_features
        self.seq_counter = 0
        self.text_buffer = PagerTextBuffer()

        # Deterministic simulation weight block
        rng = np.random.default_rng(42)
        self.weights = rng.normal(0.0, 0.2, (out_features, in_features))

    def next_seq(self) -> int:
        self.seq_counter = (self.seq_counter + 1) & 0xFF
        return self.seq_counter

    def query_hello(self) -> dict[str, Any]:
        """Send HELLO packet and parse device metadata."""
        pkt = PagerPacket(cmd=PagerCommand.HELLO, seq=self.next_seq(), payload=b"")
        wire = pkt.serialize()
        resp = PagerPacket.deserialize(wire)

        return {
            "device_id": "PAGER1-XB16X16",
            "protocol_version": 1,
            "status": "ONLINE",
            "seq_tested": resp.seq,
        }

    def execute_prompt_step(
        self,
        prompt_text: str,
        input_vector: np.ndarray,
    ) -> dict[str, Any]:
        """Send RUN_VECTOR packet and stream response to display buffer."""
        v_arr = np.asarray(input_vector, dtype=np.float32).reshape(self.in_features)
        v_bytes = v_arr.tobytes()

        # 1. Host builds RUN_VECTOR packet
        pkt_run = PagerPacket(
            cmd=PagerCommand.RUN_VECTOR,
            seq=self.next_seq(),
            payload=v_bytes,
        )
        wire_run = pkt_run.serialize()

        # 2. Emulate SPI bus transmission & crossbar execution
        parsed_run = PagerPacket.deserialize(wire_run)
        v_in_recovered = np.frombuffer(parsed_run.payload, dtype=np.float32)

        # 3. MVM on analog weights (explicit float32)
        i_out = (self.weights.astype(np.float32) @ v_in_recovered).astype(np.float32)

        # 4. Accelerator packages READ_OUTPUT response packet
        resp_pkt = PagerPacket(
            cmd=PagerCommand.READ_OUTPUT,
            seq=parsed_run.seq,
            payload=i_out.tobytes(),
        )
        wire_resp = resp_pkt.serialize()

        # 5. Host recovers output currents
        recovered_resp = PagerPacket.deserialize(wire_resp)
        i_result = np.frombuffer(recovered_resp.payload, dtype=np.float32)

        # 6. Update virtual pager display buffer
        self.text_buffer.clear()
        self.text_buffer.append_line(f"> {prompt_text}")
        self.text_buffer.append_line(f"AI: MVM peak = {float(np.max(np.abs(i_result))):.3f}A")
        self.text_buffer.append_line("Tokens streamed successfully via SPI bus.")
        self.text_buffer.status_bar = "STREAM COMPLETE"

        return {
            "prompt": prompt_text,
            "bytes_transmitted": len(wire_run) + len(wire_resp),
            "crc_verified": True,
            "mvm_l2_norm": float(np.linalg.norm(i_result)),
            "display_lines": list(self.text_buffer.lines),
        }
