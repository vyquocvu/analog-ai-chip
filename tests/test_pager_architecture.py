"""Tests for Chapter 0069: Pocket Analog AI Communicator (Pager-1) Product Architecture."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from analog_layout.pager_hardware import (
    PagerDisplayConfig,
    PagerFormFactorConfig,
    PagerHostMCUConfig,
    PagerPowerTreeConfig,
    simulate_pager_power_budget,
)

_REPO = Path(__file__).resolve().parent.parent
_MODULE = _REPO / "book" / "0069-pager-product-architecture" / "pager_product_architecture.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("pager_0069", _MODULE)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {_MODULE}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pager_0069"] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()


def test_pager_architecture_extract_matches_committed() -> None:
    """Verify that the extract script produces deterministic output matching committed JSON."""
    payload = mod.run_pager_architecture_extract()
    assert mod.RESULT_PATH.is_file(), f"Extract JSON missing at {mod.RESULT_PATH}"
    assert mod.SVG_PATH.is_file(), f"Diagram SVG missing at {mod.SVG_PATH}"

    committed = json.loads(mod.RESULT_PATH.read_text(encoding="utf-8"))
    assert payload == committed
    assert payload["status"] == "PASSED"
    assert payload["gate"] == "R18"
    assert payload["work_package"] == "WP18.1"


def test_pager_power_budget_targets() -> None:
    """Verify hand-computable battery autonomy and thermal dissipation targets."""
    power = PagerPowerTreeConfig(battery_capacity_mah=1200.0, battery_nominal_voltage_v=3.7)
    report = simulate_pager_power_budget(power=power)

    # Standby must exceed 30 days
    assert report.standby_battery_life_days >= 30.0
    # Continuous active inference must exceed 40 hours
    assert report.continuous_active_life_hours >= 40.0
    # Surface temperature under natural convection must remain touch-safe (< 45 C)
    assert report.peak_surface_temp_c < 45.0
    assert report.is_autonomy_compliant is True
    assert report.is_thermal_compliant is True


def test_display_fits_chassis_envelope() -> None:
    """Assert that 2.7-inch display active area fits within the 72x54 mm chassis."""
    form = PagerFormFactorConfig()
    disp = PagerDisplayConfig()

    # Active display area must be strictly smaller than exterior chassis dimensions
    assert disp.active_width_mm < form.chassis_width_mm
    assert disp.active_height_mm < form.chassis_height_mm

    # Bezel margins must be at least 4 mm on all sides
    margin_x = (form.chassis_width_mm - disp.active_width_mm) / 2.0
    margin_y = (form.chassis_height_mm - disp.active_height_mm) / 2.0
    assert margin_x >= 4.0
    assert margin_y >= 4.0


def test_mcu_low_power_retention() -> None:
    """Assert that host controller sleep current retains SRAM under 10 uA."""
    mcu = PagerHostMCUConfig()
    assert mcu.sleep_current_ua <= 10.0
    assert mcu.on_chip_sram_kb >= 256  # Sufficient for tokenizer and KV buffer
