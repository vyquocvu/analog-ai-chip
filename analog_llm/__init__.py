"""Hybrid analog-digital LLM accelerator simulator.

Build a crossbar tile, route a small transformer through it, and measure how
converter and conductance non-idealities change the output.
"""

from .accelerator import Accelerator
from .attribution import (
    ErrorAttributionResult,
    MechanismMetrics,
    attribute_from_profiles,
    attribute_tile_error,
    evaluate_attribution_suite,
)
from .calibration import OutputCalibration, output_calibration_from_profile
from .converters import adc, dac, symmetric_converter
from .crossbar import (
    apply_conductance_drift,
    apply_iv_nonlinearity,
    apply_programming_variation,
    apply_read_noise,
    apply_stuck_faults,
    map_differential,
    mvm,
    scale_weights,
    solve_crossbar_nodal,
)
from .device_profile import load_device_profile, validate_device_profile
from .model_manifest import ModelManifest, TensorDescriptor
from .profile_adapter import (
    CROSSBAR_NONIDEALITY_FIELDS,
    build_tile_factory,
    build_tile_factory_from_converter_profiles,
    converter_config_from_profiles,
    nonideality_config_from_profile,
    tile_config_from_profile,
)
from .tile import CrossbarTile
from .transformer import Metrics, TinyGPT, TinyGPTConfig

__all__ = [
    "CROSSBAR_NONIDEALITY_FIELDS",
    "Accelerator",
    "CrossbarTile",
    "ErrorAttributionResult",
    "MechanismMetrics",
    "Metrics",
    "ModelManifest",
    "OutputCalibration",
    "TensorDescriptor",
    "TinyGPT",
    "TinyGPTConfig",
    "adc",
    "apply_conductance_drift",
    "apply_iv_nonlinearity",
    "apply_programming_variation",
    "apply_read_noise",
    "apply_stuck_faults",
    "attribute_from_profiles",
    "attribute_tile_error",
    "build_tile_factory",
    "build_tile_factory_from_converter_profiles",
    "converter_config_from_profiles",
    "dac",
    "evaluate_attribution_suite",
    "load_device_profile",
    "map_differential",
    "mvm",
    "nonideality_config_from_profile",
    "output_calibration_from_profile",
    "scale_weights",
    "solve_crossbar_nodal",
    "symmetric_converter",
    "tile_config_from_profile",
    "validate_device_profile",
]
