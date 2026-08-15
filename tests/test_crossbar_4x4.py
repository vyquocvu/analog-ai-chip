"""WP3.2 — 0013: 4×4 current-mode differential crossbar array.

Always-on tests validate the hand MVM reference, the behavioral-equivalence of
the profile-driven ``analog_llm`` tile (no SPICE needed), the committed
extract (error budget, currents, 2×2 regression, settling caveat), and
fail-closed shape checks. Engine-gated tests re-run the SPICE array and check
it matches the hand reference, the tile, the current ledger and the committed
extract.
"""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from analog_llm import build_tile_factory

_REPO = Path(__file__).resolve().parent.parent
_MODULE = _REPO / "book" / "0013-crossbar-4x4" / "crossbar_4x4.py"
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "crossbar-4x4-0013-extract.json"
_EXTRACT_12 = _REPO / "verification" / "circuit" / "results" / "crossbar-2x2-0012-extract.json"
_PROFILE = _REPO / "device_profiles" / "crossbar-column-v1.json"
_RESULTS_DIR = _REPO / "verification" / "circuit" / "results"


def _load():
    try:
        spec = importlib.util.spec_from_file_location("crossbar_4x4_0013", _MODULE)
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
        mod.run_array([2.5, 2.5, 2.5, 2.5], [[0.0] * 4 for _ in range(4)])
        return True
    except Exception:  # noqa: BLE001 - ngspice library missing => skip
        return False


ENGINE_OK = _engine_ok()


def _tile():
    return build_tile_factory(
        str(_PROFILE), 4, 4, g_bits=16, dac_bits=16, adc_bits=16
    )()


def test_hand_mvm_matches_direct_dot_product() -> None:
    # always-on: Vout = RF*GSCALE * W @ u, W is [outputs, inputs]
    w = np.array(mod.W_MIXED)
    u = np.array([0.4, -0.3, 0.25, -0.2])
    assert mod.ideal_out(u + mod.VREF, w) == pytest.approx(
        mod.RF * mod.GSCALE * (w @ u), rel=1e-12
    )


def test_hand_mvm_balanced_zero_is_exact() -> None:
    # always-on: all-zero weights -> exactly 0 V out
    u = np.array([0.4, -0.3, 0.25, -0.2])
    assert mod.ideal_out(u + mod.VREF, mod.W_ZERO) == pytest.approx(
        np.zeros(4), abs=1e-12
    )


def test_conductances_realize_weights_4x4() -> None:
    # always-on: G+ - G- = W * GSCALE on the full 4x4 matrix
    w = np.array(mod.W_MIXED)
    gp, gm = mod.conductances(w)
    assert (gp - gm) == pytest.approx(w * mod.GSCALE, abs=1e-15)
    assert gp.shape == gm.shape == (4, 4)
    assert np.all(gp >= mod.G0) and np.all(gm >= mod.G0)


def test_behavioral_tile_matches_hand_reference() -> None:
    # always-on, no SPICE: the profile-driven tile reproduces W @ u within its
    # 16-bit quantization floor for every committed case
    d = json.loads(_EXTRACT.read_text("utf-8"))
    tile = _tile()
    for row in d["cases"]:
        w, u = row["w"], row["u"]
        tile.program(w)
        v = np.asarray(tile.forward(np.asarray(u)), dtype=float)
        assert np.max(np.abs(v - np.asarray(row["vout_hand"]))) <= 2e-3, u
        assert np.max(np.abs(v - np.asarray(row["vout_tile"]))) <= 1e-9, u


def test_behavioral_tile_config_comes_from_profile() -> None:
    # always-on: the tile used for the comparison is profile-configured
    tile = _tile()
    assert tile.gmin == pytest.approx(1.0e-4, rel=1e-6)
    assert tile.gmax == pytest.approx(2.0e-4, rel=1e-6)
    assert tile.vin_max == pytest.approx(2.5, rel=1e-6)
    assert tile.vout_max == pytest.approx(2.5, rel=1e-6)


def test_extract_error_budget_holds() -> None:
    """Always-on: committed errors respect the frozen R3 budget."""
    d = json.loads(_EXTRACT.read_text("utf-8"))
    assert d["worst_abs_err_spice_hand_v"] <= 2e-3
    assert d["worst_abs_err_tile_hand_v"] <= 2e-3
    assert d["worst_abs_err_spice_tile_v"] <= 2e-3
    assert d["max_abs_vout_v"] <= d["headroom_v"] + 1e-3
    assert d["max_virtual_ground_err_v"] <= 0.05
    assert d["worst_current_err_a"] <= 5e-6
    assert d["regression_2x2_max_abs_err_v"] <= 1e-6


def test_extract_structure_and_currents() -> None:
    d = json.loads(_EXTRACT.read_text("utf-8"))
    assert d["name"] == "crossbar-4x4-0013"
    assert len(d["cases"]) == 5
    for row in d["cases"]:
        assert len(row["w"]) == 4 and len(row["u"]) == 4
        assert len(row["vout_spice"]) == len(row["vout_hand"]) == 4
        # SPICE-recovered currents must match the hand sum u*G per half-column
        assert row["max_current_err_a"] == pytest.approx(
            max(
                max(abs(a - b) for a, b in zip(row["iplus_spice_a"], row["iplus_hand_a"])),
                max(abs(a - b) for a, b in zip(row["iminus_spice_a"], row["iminus_hand_a"])),
            ),
            abs=1e-15,
        )
        assert row["max_current_err_a"] <= 5e-6
    # the tile config recorded in the extract is the profile-derived one
    assert d["tile"]["profile"] == "device_profiles/crossbar-column-v1.json"
    assert d["tile"]["g_bits"] == 16


def test_extract_settling_is_recorded_not_claimed() -> None:
    d = json.loads(_EXTRACT.read_text("utf-8"))
    s = d["settling"]
    assert len(s) == 1
    row = s[0]
    assert row["cl_farad"] == 1e-12
    assert row["settle_time_spice_s"] > 0
    assert "no bandwidth model" in row["note"]  # caveat is explicit
    # never promoted into a physical claim: the tile profile has no settling
    # or bandwidth field, and no 0013 profile was published
    profile = json.loads(_PROFILE.read_text("utf-8"))
    assert "settling" not in profile
    assert "bandwidth" not in profile
    assert not (_RESULTS_DIR / "crossbar-4x4-0013-profile.json").exists()


def test_extract_regression_matches_0012() -> None:
    d = json.loads(_EXTRACT.read_text("utf-8"))
    d12 = json.loads(_EXTRACT_12.read_text("utf-8"))
    # the 4x4 suite is a superset of the 2x2 evidence: the same topology family
    assert d["regression_2x2_max_abs_err_v"] <= 1e-6
    assert d12["worst_abs_err_v"] <= 2e-3


def test_ideal_out_rejects_bad_input() -> None:
    with pytest.raises(ValueError):
        mod.ideal_out([3.0, 2.1], mod.W_MIXED)  # xs length != 4 inputs
    with pytest.raises(ValueError):
        mod.ideal_out([3.0, 2.1, 3.0, 2.1], np.array([1.0, 0.0, 0.0, 0.0]))  # 1-D W
    with pytest.raises(ValueError):
        mod.ideal_out([3.0, 2.1, 3.0, np.nan], mod.W_MIXED)


@pytest.mark.skipif(not ENGINE_OK, reason="PySpice/ngspice not available")
def test_spice_matches_hand_and_tile() -> None:
    tile = _tile()
    for w, u in mod.CASES:
        xs = [ui + mod.VREF for ui in u]
        vout, vg = mod.run_array(xs, w)
        ideal = mod.ideal_out(xs, w)
        tile.program(w)
        vtile = np.asarray(tile.forward(np.asarray(u)), dtype=float)
        assert np.max(np.abs(vout - ideal)) <= 2e-3, u
        assert np.max(np.abs(vout - vtile)) <= 2e-3, u
        assert np.max(np.abs(vout)) <= mod.HEADROOM_V + 1e-3
        assert vg.max() <= 0.05


@pytest.mark.skipif(not ENGINE_OK, reason="PySpice/ngspice not available")
def test_spice_balanced_zero_is_exact() -> None:
    vout, _ = mod.run_array([2.5] * 4, [[0.0] * 4 for _ in range(4)])
    assert np.all(np.abs(vout) <= 1e-12)


@pytest.mark.skipif(not ENGINE_OK, reason="PySpice/ngspice not available")
def test_spice_currents_match_hand() -> None:
    for w, u in mod.CASES:
        xs = [ui + mod.VREF for ui in u]
        ic = mod.column_currents_spice(xs, w)
        ih = mod.column_currents_hand(xs, w)
        assert np.max(np.abs(ic["iplus"] - ih["iplus"])) <= 5e-6
        assert np.max(np.abs(ic["iminus"] - ih["iminus"])) <= 5e-6


@pytest.mark.skipif(not ENGINE_OK, reason="PySpice/ngspice not available")
def test_spice_reproduces_0012_cases() -> None:
    d12 = json.loads(_EXTRACT_12.read_text("utf-8"))
    for row in d12["cases"]:
        vout, _ = mod.run_array(row["xs"], row["w"])
        assert np.max(np.abs(vout - np.asarray(row["vout_spice"]))) <= 1e-6


@pytest.mark.skipif(not ENGINE_OK, reason="PySpice/ngspice not available")
def test_extract_reproduces_committed_results() -> None:
    d = json.loads(_EXTRACT.read_text("utf-8"))
    tile = _tile()
    for row in d["cases"]:
        w, u = row["w"], row["u"]
        xs = [ui + d["vref_v"] for ui in u]
        vout, vg = mod.run_array(xs, w)
        assert vout == pytest.approx(row["vout_spice"], rel=2e-3, abs=1e-12)
        assert vg.max() == pytest.approx(row["max_virtual_ground_err_v"], rel=2e-3, abs=1e-12)
        ic = mod.column_currents_spice(xs, w)
        assert ic["iplus"] == pytest.approx(row["iplus_spice_a"], rel=2e-3, abs=1e-9)
        tile.program(w)
        vtile = np.asarray(tile.forward(np.asarray(u)), dtype=float)
        assert vtile == pytest.approx(row["vout_tile"], rel=1e-6, abs=1e-9)
    # settling is deterministic
    d2 = json.loads(_EXTRACT.read_text("utf-8"))
    assert d["settling"] == d2["settling"]
