"""WP2.1 — 0011 converter variation: calibration candidates.

Always-on tests validate the deterministic calibration math (two-point gain/
offset and full transfer LUT) on ideal, gain-only, offset-only and INL-only
transfers. Engine-gated test re-runs calibration on the SPICE mismatch draws.
"""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parent.parent
_MODULE = _REPO / "book" / "0011-converter-variation" / "calibration.py"


def _load():
    try:
        spec = importlib.util.spec_from_file_location("calibration_0011", _MODULE)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:  # noqa: BLE001 - missing engine/lib => skip
        return None


mod = _load()

_VARIATION = _REPO / "book" / "0011-converter-variation" / "variation.py"


def _engine_ok():
    """True when a real ngspice op solve runs through variation.py (SPICE MC)."""
    try:
        spec = importlib.util.spec_from_file_location("variation_0011_cal", _VARIATION)
        vmod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(vmod)
    except Exception:  # noqa: BLE001 - missing engine/lib => skip
        return False
    if not getattr(vmod, "_PYSPICE_OK", False):
        return False
    try:
        vmod.mismatched_output(0, np.zeros(vmod.resistor_count()))  # one trivial solve
        return True
    except Exception:  # noqa: BLE001 - ngspice library missing => skip
        return False


ENGINE_OK = _engine_ok()

BITS, VREF = 4, 2.5


def _ideal(n=4):
    return np.tile(np.arange(16, dtype=float) * (VREF / 16.0), (n, 1))


def test_two_point_calibrate_removes_gain_and_offset() -> None:
    t = _ideal() * 1.05 + 0.1
    out = mod.two_point_calibrate(t)
    assert mod.residual_error(out) <= 1e-12


def test_two_point_calibrate_leaves_only_inl() -> None:
    t = _ideal()
    t[:, 8] += 0.05  # pure INL bump at code 8
    out = mod.two_point_calibrate(t)
    # gain/offset are gone; the INL bump survives
    assert mod.residual_error(out) == pytest.approx(0.05, rel=1e-6)


def test_lookup_table_calibrate_zeroes_static_mismatch() -> None:
    t = _ideal() * 1.05 + 0.1
    t[:, 8] += 0.05
    out = mod.lookup_table_calibrate(t)
    assert mod.residual_error(out) <= 1e-12


def test_calibration_shapes_fail_closed() -> None:
    with pytest.raises(ValueError):
        mod.two_point_calibrate(np.zeros((4, 15)))
    with pytest.raises(ValueError):
        mod.two_point_calibrate(np.zeros((0, 16)))
    with pytest.raises(ValueError):
        mod.lookup_table_calibrate(np.zeros((4, 15)))
    with pytest.raises(ValueError):
        mod.residual_error(np.zeros((3, 4)), bits=4)  # wrong code count


def test_two_point_calibrate_rejects_zero_slope() -> None:
    with pytest.raises(ValueError, match="positive end-to-end slope"):
        mod.two_point_calibrate(np.zeros((2, 16)))


def test_two_point_on_ideal_is_identity() -> None:
    out = mod.two_point_calibrate(_ideal())
    assert mod.residual_error(out) <= 1e-12
    assert np.allclose(out, _ideal(), atol=1e-12)


@pytest.mark.skipif(not ENGINE_OK, reason="PySpice/ngspice not available")
def test_calibration_on_spice_mismatch_removes_error() -> None:
    spec = importlib.util.spec_from_file_location(
        "variation_0011_cal",
        _VARIATION,
    )
    vmod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vmod)
    t = vmod.transfers_spice(vmod.draw_deltas())
    raw = mod.residual_error(t)
    two_pt = mod.residual_error(mod.two_point_calibrate(t))
    lut = mod.residual_error(mod.lookup_table_calibrate(t))
    assert two_pt < raw  # two-point removes the gain/offset share
    assert lut <= 1e-12  # full LUT zeroes static mismatch
