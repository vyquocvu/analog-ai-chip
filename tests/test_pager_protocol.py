"""Tests for Chapter 0070: Host-to-CiM Binary Packet Protocol & Virtual Pager Runtime."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from analog_llm.pager_protocol import (
    PagerCommand,
    PagerPacket,
    PagerTextBuffer,
)

_REPO = Path(__file__).resolve().parent.parent
_MODULE = _REPO / "book" / "0070-pager-packet-protocol" / "pager_packet_protocol.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("pager_0070", _MODULE)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {_MODULE}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pager_0070"] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()


def test_pager_protocol_extract_matches_committed() -> None:
    """Verify that the extract script produces deterministic output matching committed JSON."""
    payload = mod.run_pager_protocol_extract()
    assert mod.RESULT_PATH.is_file(), f"Extract JSON missing at {mod.RESULT_PATH}"
    assert mod.SVG_PATH.is_file(), f"Diagram SVG missing at {mod.SVG_PATH}"

    committed = json.loads(mod.RESULT_PATH.read_text(encoding="utf-8"))
    assert payload == committed
    assert payload["status"] == "PASSED"
    assert payload["gate"] == "R18"
    assert payload["work_package"] == "WP18.2"


def test_crc16_detection_and_fail_closed() -> None:
    """Verify that single-bit payload corruption triggers CRC-16 fail-closed rejection."""
    payload = b"CALIBRATION_VOLTAGE_DATA_0123"
    pkt = PagerPacket(cmd=PagerCommand.CALIBRATE, seq=42, payload=payload)
    wire = bytearray(pkt.serialize())

    # Corrupt one bit in the payload
    wire[10] ^= 0x01

    with pytest.raises(ValueError, match="CRC-16 mismatch"):
        PagerPacket.deserialize(bytes(wire))


def test_invalid_sync_and_short_packets_fail_closed() -> None:
    """Assert that bad sync delimiters or truncated bytes are rejected."""
    # 1. Packet too short
    with pytest.raises(ValueError, match="Packet too short"):
        PagerPacket.deserialize(b"\xAA\x55\x01")

    # 2. Corrupt sync header
    pkt = PagerPacket(cmd=PagerCommand.HELLO, seq=1, payload=b"")
    wire = bytearray(pkt.serialize())
    wire[0] = 0xFF
    with pytest.raises(ValueError, match="Invalid frame sync"):
        PagerPacket.deserialize(bytes(wire))


def test_command_opcodes_roundtrip() -> None:
    """Verify all defined PagerCommand opcodes serialize and deserialize cleanly."""
    commands = [
        PagerCommand.HELLO,
        PagerCommand.CALIBRATE,
        PagerCommand.PROGRAM_WEIGHTS,
        PagerCommand.RUN_VECTOR,
        PagerCommand.READ_OUTPUT,
        PagerCommand.STATUS_IRQ,
    ]
    for i, cmd in enumerate(commands):
        pkt = PagerPacket(cmd=cmd, seq=i, payload=f"PAYLOAD_{cmd.name}".encode())
        wire = pkt.serialize()
        recovered = PagerPacket.deserialize(wire)
        assert recovered.cmd == cmd
        assert recovered.seq == i
        assert recovered.payload == f"PAYLOAD_{cmd.name}".encode()


def test_pager_text_buffer_word_wrap_and_scroll() -> None:
    """Verify display buffer word-wrapping and line scrolling mechanics."""
    buf = PagerTextBuffer(cols=20, rows=6)
    buf.append_line("Line 1 Short")
    buf.append_line("Line 2 Another")
    buf.append_line("Line 3 Third")
    buf.append_line("Line 4 Fourth")
    buf.append_line("Line 5 Fifth (should scroll)")

    # Capacity is rows - 2 (header and footer take 2 rows)
    assert len(buf.lines) == 4
    assert "scroll)" in buf.lines[-1]
    assert "Line 5 Fifth (should" in buf.lines[-2]
    rendered = buf.render_ascii_screen()
    assert "PAGER-1" in rendered
    assert "READY" in rendered
