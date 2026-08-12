"""Emit the deterministic R3/0012 2x2 crossbar SPICE evidence as JSON."""

import importlib.util
import json
from pathlib import Path

MODULE = (
    Path(__file__).resolve().parent.parent
    / "book"
    / "0012-crossbar-2x2"
    / "crossbar_2x2.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("crossbar_2x2", MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    module = load_module()
    evidence = module.spice_evidence(
        [3.0, 2.1],
        [[0.50, 0.25], [-0.50, 0.25]],
    )
    print(json.dumps(evidence, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
