"""Optional SPICE check + always-on data checks for the 0007 crossbar column.

The SPICE test is skipped (not failed) when PySpice/ngspice is unavailable. The
``test_conductances_realize_weights`` and hand-arithmetic checks always run.
"""

import importlib.util
import inspect
from pathlib import Path

import pytest

from analog_llm import TinyGPT, TinyGPTConfig  # noqa: F401  (runtime import guard)

_MODULE = Path(__file__).resolve().parent.parent / "book" / "0007-crossbar-column" / "crossbar_column.py"


def _load(path):
    try:
        spec = importlib.util.spec_from_file_location("crossbar_column_" + path.stem, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:  # noqa: BLE001 - missing engine/lib => skip
        return None


mod = _load(_MODULE)


def test_conductances_realize_weights() -> None:
    # always-on: the differential conductances must satisfy G+ - G- = w*GSCALE
    gp, gm = mod.conductances([0.5, 0.25, -0.5, 0.0])
    for w, gplus, gminus in zip([0.5, 0.25, -0.5, 0.0], gp, gm):
        assert abs((gplus - gminus) - w * mod.GSCALE) < 1e-15


def test_ideal_hand_arithmetic() -> None:
    # always-on: Vout = Rf*Gscale * dot(x - VREF, w)
    expected = mod.RF * mod.GSCALE * (0.5 * 0.5 + (-0.4) * 0.25)
    assert abs(mod.ideal_out([3.0, 2.1], [0.5, 0.25]) - expected) < 1e-12


@pytest.mark.skipif(mod is None, reason="PySpice/ngspice not available")
def test_spice_column_matches_hand_calc() -> None:
    assert inspect.isfunction(mod.run_column)
    vout = mod.run_column([3.0, 2.1], [0.5, 0.25])
    assert abs(vout - 0.1500) <= 2e-2


@pytest.mark.skipif(mod is None, reason="PySpice/ngspice not available")
def test_spice_negative_weight() -> None:
    # negative weight: the minus branch carries it, output sign flips
    vout = mod.run_column([3.0, 2.1], [-0.5, 0.25])
    ideal = mod.ideal_out([3.0, 2.1], [-0.5, 0.25])
    assert abs(vout - ideal) <= 2e-2
