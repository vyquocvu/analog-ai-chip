"""WP3.1 — 0012: 2×2 current-mode differential crossbar array.

Always-on tests validate the hand MVM reference (orientation, balanced zero,
column independence and fail-closed shape checks) and the committed extract
(per-case SPICE-vs-hand error, headroom, virtual-ground bound, independence,
half-stage rail finding). Engine-gated tests re-run the SPICE array and check
it reproduces the hand reference and the committed extract.
"""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parent.parent
_MODULE = _REPO / "book" / "0012-crossbar-2x2" / "crossbar_2x2.py"
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "crossbar-2x2-0012-extract.json"


def _load():
    try:
        spec = importlib.util.spec_from_file_location("crossbar_2x2_0012", _MODULE)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:  # noqa: BLE001 - missing engine/lib => skip
        return None


mod = _load()


def _engine_ok():
    """True when a real ngspice operating-point solve runs through the module."""
    if mod is None or not getattr(mod, "_PYSPICE_OK", False):
        return False
    try:
        mod.run_array([mod.VREF, mod.VREF], [[0.0, 0.0], [0.0, 0.0]])
        return True
    except Exception:  # noqa: BLE001 - ngspice library missing => skip
        return False


ENGINE_OK = _engine_ok()


def test_hand_mvm_matches_direct_dot_product() -> None:
    # always-on: Vout = RF*GSCALE * W @ (x - VREF), W is [outputs, inputs]
    xs = [3.0, 2.1]
    w = np.array([[0.50, 0.25], [-0.25, 0.50]])
    u = np.asarray(xs) - mod.VREF
    assert mod.ideal_out(xs, w) == pytest.approx(mod.RF * mod.GSCALE * (w @ u), rel=1e-12)


def test_hand_mvm_case_values() -> None:
    # always-on: hand-computable cases from the chapter README
    assert mod.ideal_out([3.5, 1.5], [[1.0, -1.0], [-1.0, 1.0]]) == pytest.approx(
        [2.0, -2.0], abs=1e-12
    )
    assert mod.ideal_out([2.5, 2.5], [[0.0, 0.0], [0.0, 0.0]]) == pytest.approx(
        [0.0, 0.0], abs=1e-12
    )
    # boundary envelope: u = [2.5, 0] with unit weights -> Vout = [2.5, 0]
    assert mod.ideal_out([5.0, 2.5], [[1.0, 0.0], [0.0, 1.0]]) == pytest.approx(
        [2.5, 0.0], abs=1e-12
    )


def test_conductances_realize_weights_and_balanced_zero() -> None:
    # always-on: G+ - G- = W * GSCALE, zero weight sits at the balanced G0 cell
    w = np.array([[0.5, -0.25], [0.0, 1.0]])
    gp, gm = mod.conductances(w)
    assert (gp - gm) == pytest.approx(w * mod.GSCALE, abs=1e-15)
    assert np.all(gp >= mod.G0) and np.all(gm >= mod.G0)
    assert gp[1, 0] == mod.G0 and gm[1, 0] == mod.G0  # zero weight -> balanced


def test_hand_model_columns_are_independent() -> None:
    # always-on: only column 1 changes -> column 0 output identical
    xs = [3.0, 2.1]
    a = mod.ideal_out(xs, [[0.50, 0.25], [0.25, 0.50]])
    b = mod.ideal_out(xs, [[0.50, 0.25], [-1.0, 0.0]])
    assert a[0] == pytest.approx(b[0], abs=1e-12)


def test_half_stage_rail_envelope() -> None:
    # always-on: |u| <= VREF / (RF*(G0 + GSCALE)) keeps half-stages in the rail
    expected = mod.VREF / (mod.RF * (mod.G0 + mod.GSCALE))
    assert mod.half_stage_rail_envelope_v() == pytest.approx(expected)
    assert 1.2 < expected < 1.3  # 2.5 V / 2 V-per-volt = 1.25 V


def test_conductances_reject_bad_input() -> None:
    with pytest.raises(ValueError):
        mod.conductances(np.array([1.0, 0.0]))  # 1-D, not [outputs, inputs]
    with pytest.raises(ValueError):
        mod.conductances(np.array([[1.0, np.nan], [0.0, 1.0]]))


def test_ideal_out_rejects_shape_and_finite_mismatch() -> None:
    with pytest.raises(ValueError):
        mod.ideal_out([3.0], [[0.5, 0.25], [-0.25, 0.5]])  # xs length != inputs
    with pytest.raises(ValueError):
        mod.ideal_out([3.0, 2.1], [0.5, 0.25])  # 1-D weights
    with pytest.raises(ValueError):
        mod.ideal_out([3.0, float("inf")], [[0.5, 0.25], [-0.25, 0.5]])


def test_extract_is_committed_and_within_bounds() -> None:
    """Always-on: the committed SPICE extract satisfies every physical bound."""
    d = json.loads(_EXTRACT.read_text("utf-8"))
    assert d["name"] == "crossbar-2x2-0012"
    assert len(d["cases"]) == 5
    # every case: SPICE reproduces the hand MVM within the VCVS tolerance
    assert d["worst_abs_err_v"] <= 2e-3
    # differential outputs stay inside the +-2.5 V headroom
    assert d["max_abs_vout_v"] <= d["headroom_v"] + 1e-3
    # virtual ground stays near VREF (loading bound)
    assert d["max_virtual_ground_err_v"] <= 0.05
    # columns are uncoupled: changing column 1 leaves column 0 unchanged
    assert d["column_independence_err_v"] <= 2e-3
    # exactly one half-stage rail violation (the boundary case finding)
    assert d["half_stage_rail_violations"] == 1
    assert d["half_stage_rail_envelope_v"] == pytest.approx(1.25, abs=1e-9)


def test_extract_cases_cover_signed_zero_boundary() -> None:
    d = json.loads(_EXTRACT.read_text("utf-8"))
    ws = [row["w"] for row in d["cases"]]
    # mixed signs, full-scale differential, balanced zero, one zero per row,
    # boundary envelope at |Vout| = headroom
    assert any(any(cell < 0 for row in w for cell in row) for w in ws)
    assert any(w == [[0.0, 0.0], [0.0, 0.0]] for w in ws)
    assert any(max(abs(v) for v in row["vout_spice"]) > 2.0 for row in d["cases"])
    assert all(len(row["vout_spice"]) == 2 for row in d["cases"])
    for row in d["cases"]:
        assert row["max_abs_err_v"] == pytest.approx(
            max(abs(s - h) for s, h in zip(row["vout_spice"], row["vout_hand"])), abs=1e-12
        )


@pytest.mark.skipif(not ENGINE_OK, reason="PySpice/ngspice not available")
def test_spice_array_matches_hand_reference() -> None:
    for xs, w in mod.CASES:
        vout, vg = mod.run_array(xs, w)
        ideal = mod.ideal_out(xs, w)
        assert np.max(np.abs(vout - ideal)) <= 2e-3, f"xs={xs}, W={w}"
        assert np.max(np.abs(vout)) <= mod.HEADROOM_V + 1e-3
        assert vg.max() <= 0.05


@pytest.mark.skipif(not ENGINE_OK, reason="PySpice/ngspice not available")
def test_spice_balanced_zero_is_exact() -> None:
    vout, _ = mod.run_array([2.5, 2.5], [[0.0, 0.0], [0.0, 0.0]])
    assert np.all(np.abs(vout) <= 1e-12)


@pytest.mark.skipif(not ENGINE_OK, reason="PySpice/ngspice not available")
def test_spice_columns_are_independent() -> None:
    err = mod.independence_error(
        [3.0, 2.1], [[0.50, 0.25], [0.25, 0.50]], [[0.50, 0.25], [-1.0, 0.0]]
    )
    assert err <= 2e-3


@pytest.mark.skipif(not ENGINE_OK, reason="PySpice/ngspice not available")
def test_extract_reproduces_committed_results() -> None:
    d = json.loads(_EXTRACT.read_text("utf-8"))
    assert d["worst_abs_err_v"] == pytest.approx(
        max(
            float(np.max(np.abs(mod.run_array(row["xs"], row["w"])[0] - mod.ideal_out(row["xs"], row["w"]))))
            for row in d["cases"]
        ),
        rel=1e-6, abs=1e-12,
    )
    # per-case committed values must reproduce within tolerance
    for row in d["cases"]:
        vout, vg = mod.run_array(row["xs"], row["w"])
        assert vout == pytest.approx(row["vout_spice"], rel=2e-3, abs=1e-12)
        assert vg.max() == pytest.approx(row["max_virtual_ground_err_v"], rel=2e-3, abs=1e-12)
    assert mod.independence_error(
        [3.0, 2.1], [[0.50, 0.25], [0.25, 0.50]], [[0.50, 0.25], [-1.0, 0.0]]
    ) == pytest.approx(d["column_independence_err_v"], abs=1e-12)
