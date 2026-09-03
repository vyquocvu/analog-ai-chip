"""Pocket Analog AI Communicator (Pager-1) Hardware Architecture & Power Engine.

Models the ultra-low-power physical form factor, Memory LCD display, host MCU,
keypad, power distribution tree, and battery lifetime for a standalone offline appliance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PagerFormFactorConfig:
    """Pocket pager chassis dimensions, ergonomics, and weight."""

    chassis_width_mm: float = 72.0
    chassis_height_mm: float = 54.0
    chassis_depth_mm: float = 14.5
    total_mass_g: float = 85.0
    material: str = "CNC Aluminum 6061-T6 / Anodized Black"
    has_belt_clip: bool = True
    water_resistance_rating: str = "IP54 (Splash and Dust Resistant)"


@dataclass(frozen=True)
class PagerDisplayConfig:
    """Ultra-low-power reflective display parameters."""

    model: str = "Sharp LS027B7DH01 Memory LCD"
    diagonal_inch: float = 2.7
    resolution_width: int = 400
    resolution_height: int = 240
    active_width_mm: float = 58.80
    active_height_mm: float = 35.28
    color_depth_bits: int = 1  # Monochrome
    static_hold_power_uw: float = 15.0  # 5.0 uA at 3.0V
    active_refresh_power_uw: float = 120.0  # At 10 Hz text streaming
    refresh_rate_hz: float = 10.0
    contrast_ratio: float = 14.0


@dataclass(frozen=True)
class PagerHostMCUConfig:
    """Host digital controller (RP2040 / STM32U5 Cortex-M33)."""

    model: str = "STM32U575 / RP2040 Dual-Core"
    active_clock_mhz: float = 48.0
    sleep_clock_mhz: float = 1.0
    active_current_ma: float = 8.50  # at 3.3V (28.05 mW)
    sleep_current_ua: float = 3.20  # Deep stop mode with RAM retention
    on_chip_sram_kb: int = 520
    qspi_flash_mb: int = 16
    bus_frequency_mhz: float = 24.0  # QSPI to analog accelerator


@dataclass(frozen=True)
class PagerPowerTreeConfig:
    """Battery, PMIC, and voltage regulator network."""

    battery_capacity_mah: float = 1200.0  # 1S Li-Po pouch cell
    battery_nominal_voltage_v: float = 3.70
    battery_energy_wh: float = 4.44  # 1.2 Ah * 3.7 V
    pmic_model: str = "TI BQ25120"
    pmic_quiescent_current_ua: float = 0.70  # 700 nA Iq
    vdd_dig_voltage_v: float = 3.30
    vdd_ref_voltage_v: float = 2.50  # Analog virtual ground VREF
    vdd_core_voltage_v: float = 1.00  # Crossbar core supply
    vrm_efficiency_pct: float = 91.5


@dataclass(frozen=True)
class PagerKeypadHapticConfig:
    """Tactile input and haptic feedback subsystem."""

    key_count: int = 35  # Full QWERTY thumb pad
    key_switch_type: str = "Tactile Metal Dome (6.0 mm, 160 gf)"
    keypad_controller: str = "TI TCA8418 I2C Matrix Controller"
    keypad_standby_current_ua: float = 1.50
    has_rotary_jog_dial: bool = True
    haptic_driver: str = "TI DRV2605L"
    lra_motor_type: str = "10mm Linear Resonant Actuator (205 Hz)"
    alert_pulse_energy_uj: float = 35.0  # Energy per notification buzz


@dataclass(frozen=True)
class PagerPowerBudgetReport:
    """Complete energy budget, battery autonomy, and thermal signoff."""

    standby_power_uw: float
    standby_battery_life_days: float
    active_typing_power_mw: float
    active_inference_power_mw: float
    continuous_active_life_hours: float
    daily_mixed_use_days: float  # Assuming 2 hours active per day
    is_autonomy_compliant: bool
    is_thermal_compliant: bool
    peak_surface_temp_c: float
    metadata: dict[str, Any] = field(default_factory=dict)


def simulate_pager_power_budget(
    form: PagerFormFactorConfig | None = None,
    disp: PagerDisplayConfig | None = None,
    mcu: PagerHostMCUConfig | None = None,
    power: PagerPowerTreeConfig | None = None,
    key: PagerKeypadHapticConfig | None = None,
    analog_mvm_power_mw: float = 12.50,  # 16x16 tile active compute power
    ambient_temp_c: float = 25.0,
) -> PagerPowerBudgetReport:
    """Calculate complete energy ledger, battery runtime, and surface temperature."""
    _form = form or PagerFormFactorConfig()
    _disp = disp or PagerDisplayConfig()
    _mcu = mcu or PagerHostMCUConfig()
    _pwr = power or PagerPowerTreeConfig()
    _key = key or PagerKeypadHapticConfig()

    # 1. Standby Power (Display hold + MCU sleep + PMIC Iq + Keypad standby)
    p_disp_standby_uw = _disp.static_hold_power_uw
    p_mcu_standby_uw = _mcu.sleep_current_ua * _pwr.vdd_dig_voltage_v
    p_pmic_standby_uw = _pwr.pmic_quiescent_current_ua * _pwr.battery_nominal_voltage_v
    p_key_standby_uw = _key.keypad_standby_current_ua * _pwr.vdd_dig_voltage_v

    standby_power_uw = p_disp_standby_uw + p_mcu_standby_uw + p_pmic_standby_uw + p_key_standby_uw
    standby_current_ua = standby_power_uw / _pwr.battery_nominal_voltage_v

    # Standby runtime: (1200 mAh * 1000 uA/mA) / (standby_current_ua * 24 h/day)
    standby_days = (_pwr.battery_capacity_mah * 1000.0) / (max(standby_current_ua, 1e-3) * 24.0)

    # 2. Active Typing Power (MCU scanning + Display refreshing at 5 Hz)
    p_mcu_active_mw = _mcu.active_current_ma * _pwr.vdd_dig_voltage_v
    p_disp_active_mw = _disp.active_refresh_power_uw / 1000.0
    active_typing_power_mw = (p_mcu_active_mw + p_disp_active_mw) / (_pwr.vrm_efficiency_pct / 100.0)

    # 3. Active Inference Power (MCU streaming + Analog Crossbars active)
    active_inference_power_mw = (
        p_mcu_active_mw + p_disp_active_mw + analog_mvm_power_mw
    ) / (_pwr.vrm_efficiency_pct / 100.0)

    # Continuous active runtime (hours at full inference)
    continuous_hours = (_pwr.battery_energy_wh * 1000.0) / active_inference_power_mw

    # Mixed usage: 2 hours active inference/typing per day + 22 hours standby
    daily_energy_mwh = (2.0 * active_inference_power_mw) + (22.0 * standby_power_uw / 1000.0)
    mixed_use_days = (_pwr.battery_energy_wh * 1000.0) / daily_energy_mwh

    # Thermal dissipation check (passive natural convection over 72x54x14.5 mm chassis)
    # Total surface area: 2*(7.2*5.4 + 7.2*1.45 + 5.4*1.45) cm2 = 2*(38.88 + 10.44 + 7.83) = 114.3 cm2
    # Heat transfer coeff h ≈ 10 W/(m2 K) -> Rth ≈ 1 / (h * Area) ≈ 1 / (10 * 0.0114) ≈ 8.7 K/W
    r_th_chassis_k_w = 8.70
    delta_t = (active_inference_power_mw / 1000.0) * r_th_chassis_k_w
    peak_surface_temp = ambient_temp_c + delta_t

    is_autonomy_ok = standby_days >= 30.0 and continuous_hours >= 40.0
    is_thermal_ok = peak_surface_temp <= 45.0  # Skin touch threshold

    return PagerPowerBudgetReport(
        standby_power_uw=round(standby_power_uw, 2),
        standby_battery_life_days=round(standby_days, 1),
        active_typing_power_mw=round(active_typing_power_mw, 2),
        active_inference_power_mw=round(active_inference_power_mw, 2),
        continuous_active_life_hours=round(continuous_hours, 1),
        daily_mixed_use_days=round(mixed_use_days, 1),
        is_autonomy_compliant=is_autonomy_ok,
        is_thermal_compliant=is_thermal_ok,
        peak_surface_temp_c=round(peak_surface_temp, 2),
        metadata={
            "form_factor_mm": f"{_form.chassis_width_mm}x{_form.chassis_height_mm}x{_form.chassis_depth_mm}",
            "display_model": _disp.model,
            "mcu_model": _mcu.model,
            "battery_model": f"{_pwr.battery_capacity_mah:.0f} mAh Li-Po ({_pwr.battery_energy_wh:.2f} Wh)",
            "chassis_rth_k_w": r_th_chassis_k_w,
        },
    )
