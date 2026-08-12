"""Optional end-to-end checks of circuit simulations.

Skipped (not failed) when PySpice or the ngspice engine is unavailable, so the
core suite and CI stay dependency-light. Install with `pip install -e '.[sim]'`
plus the ngspice engine to enable them.
"""

import importlib.util
import inspect
from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parent.parent
_MODULE = _REPO / "book" / "0005-one-analog-neuron" / "sim_neuron.py"
_MODULE_NI = _REPO / "book" / "0005-one-analog-neuron" / "sim_neuron_nonideal.py"
_MODULE_SW = _REPO / "book" / "0005-one-analog-neuron" / "sweep_neuron.py"
_MODULE_HR = _REPO / "book" / "0005-one-analog-neuron" / "headroom_neuron.py"
_MODULE_LYR = _REPO / "book" / "0006-many-neurons" / "layer_neuron_spice.py"
_MODULE_2X2 = _REPO / "book" / "0012-crossbar-2x2" / "crossbar_2x2.py"
_HAS_PYSPICE = importlib.util.find_spec("PySpice") is not None


def _load(path):
    try:
        spec = importlib.util.spec_from_file_location("sim_neuron_" + path.stem, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:  # noqa: BLE001 - missing engine/lib => skip
        return None


neuron = _load(_MODULE)
neuron_ni = _load(_MODULE_NI)
neuron_sw = _load(_MODULE_SW) if neuron_ni is not None else None
neuron_hr = _load(_MODULE_HR) if neuron_ni is not None else None
neuron_lyr = _load(_MODULE_LYR) if neuron_ni is not None else None
crossbar_2x2 = _load(_MODULE_2X2)


@pytest.mark.skipif(neuron is None, reason="PySpice/ngspice not available")
def test_neuron_simulator_matches_hand_calc() -> None:
    assert inspect.isfunction(neuron.measure), "sim_neuron.measure must be callable"
    cases = [
        (0.5, 1.0, 0.50),
        (0.2, 0.8, 0.30),
        (1.0, 0.0, 0.50),
        (0.0, 2.0, 0.50),
        (0.6, 1.2, 0.60),
        (0.8, 0.4, 0.50),
    ]
    for x1, x2, y in cases:
        vout = abs(neuron.measure(x1, x2))
        assert abs(vout - y) <= 5e-3, f"x=({x1},{x2}) got |Vout|={vout:.4f} want {y}"


@pytest.mark.skipif(neuron_ni is None, reason="PySpice/ngspice not available")
def test_neuron_nonideal_linear_and_rails() -> None:
    out, n = neuron_ni.run_linear(3.0, 2.1, 2.5)
    assert abs(out - 2.35) <= 5e-3, f"linear region out={out:.4f}"
    assert abs(n - 2.5) <= 0.05, "virtual ground should sit near the reference"

    sat = neuron_ni.clamp(neuron_ni.run_linear(-2.0, -2.0, 2.5)[0])
    assert abs(sat - 5.0) <= 5e-3, "should clip at the high rail"

    gnd_clip = neuron_ni.clamp(neuron_ni.run_linear(0.5, 1.0, 0.0)[0])
    assert abs(gnd_clip - 0.0) <= 5e-3, "gnd-referenced inverting summer clips at 0 V"


@pytest.mark.skipif(neuron_lyr is None, reason="PySpice/ngspice not available")
def test_two_neuron_layer_matches_ideal() -> None:
    v0, v1 = neuron_lyr.run_layer(3.0, 2.1)
    i0 = neuron_lyr.ideal_out(3.0, 2.1, 0.50, 0.25)
    assert abs(v0 - i0) <= 5e-3
    assert abs(v1 - i0) <= 5e-3


@pytest.mark.skipif(neuron_hr is None, reason="PySpice/ngspice not available")
def test_neuron_virtual_ground_and_headroom() -> None:
    _, err_good = neuron_hr.virtual_ground_error(neuron_hr.AOL_GOOD)
    _, err_weak = neuron_hr.virtual_ground_error(neuron_hr.AOL_WEAK)
    assert np.max(np.abs(err_good)) < 1e-3, "virtual-ground error too large at Aol=1e4"
    assert np.max(np.abs(err_weak)) > np.max(np.abs(err_good)), "must scale with 1/Aol"
    up = neuron_hr.VHI - neuron_hr.VREF
    down = neuron_hr.VREF - neuron_hr.VLO
    assert abs(up - 2.5) < 1e-9 and abs(down - 2.5) < 1e-9


@pytest.mark.skipif(neuron_sw is None, reason="PySpice/ngspice not available")
def test_neuron_dc_sweep_slope_and_rails() -> None:
    xs, _, outs_chip = neuron_sw.sweep()
    mask = (outs_chip > neuron_sw.VLO + 1e-9) & (outs_chip < neuron_sw.VHI - 1e-9)
    slope = float(np.polyfit(xs[mask], outs_chip[mask], 1)[0])
    assert abs(slope - (-neuron_sw.W1)) < 0.02, f"slope {slope:.3f}"
    assert np.all(outs_chip <= neuron_sw.VHI + 1e-9)
    assert np.all(outs_chip >= neuron_sw.VLO - 1e-9)
    assert np.any(outs_chip >= neuron_sw.VHI - 1e-9)
    assert np.any(outs_chip <= neuron_sw.VLO + 1e-9)


@pytest.mark.skipif(
    crossbar_2x2 is None or not _HAS_PYSPICE,
    reason="PySpice/ngspice not available",
)
def test_crossbar_2x2_spice_matches_two_column_reference() -> None:
    xs = [3.0, 2.1]
    weights = [[0.50, 0.25], [-0.50, 0.25]]
    actual = crossbar_2x2.run_array(xs, weights)
    expected = crossbar_2x2.ideal_mvm(xs, weights)
    np.testing.assert_allclose(actual, expected, atol=2e-2, rtol=0.0)
