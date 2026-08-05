"""Guardrail: reject performance claims that are not backed by measurements.

The AGENTS.md rules forbid describing NumPy as physical analog acceleration,
deriving an O(1) / energy / latency advantage from one ideal crossbar op, or
claiming GPU-equivalence from the physical ledger. This module encodes that
rule as code: it scans source files and report text for *claim* phrases (not
the mere word "gpu", which legitimately appears in disclaimers like "no GPU
comparison") and raises if any forbidden claim is present.

A report that merely *disclaims* ("no GPU comparison", "not wall-clock or
energy") passes; one that claims a real speedup over a GPU fails.
"""

from __future__ import annotations

import re
from pathlib import Path

# Claim phrases (lower-cased matching). Deliberately NOT banning the word "gpu"
# alone, because our honest reports must say "no GPU comparison".
_CLAIM_RE = re.compile(
    r"faster than (a |the )?(gpu|baseline|fp32|float)\b"
    r"|gpu[- ]?equivalent"
    r"|replac(?:e|es|ing) (a |the )?(real |physical )?gpu"
    r"|comparable to (a |the )?gpu"
    r"|beats? a (gpu|gpu)"
    r"|orders? of magnitude (faster|better|cheaper)"
    r"|o\(1\) (compute|energy|latency|inference)"
    ,
    flags=re.IGNORECASE,
)

_ERROR = "performance claim not backed by measurement"


def check_text_claims(text: str, source: str = "text") -> None:
    """Raise if ``text`` contains a forbidden performance claim."""
    for m in _CLAIM_RE.finditer(text.lower()):
        raise ValueError(f"{_ERROR} in {source}: {m.group(0)!r} (add a measured ledger + disclaimer)")


def check_python_files(root: str | Path) -> int:
    """Scan every ``.py`` under ``root`` for forbidden claims; return count."""
    fails = 0
    for path in sorted(Path(root).rglob("*.py")):
        try:
            check_text_claims(path.read_text(), source=str(path))
        except ValueError:
            fails += 1
    return fails
