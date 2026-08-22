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
from .block_stream import (
    BlockStreamedLinear,
    StreamedMemoryBudget,
    calculate_execution_memory_budget,
    streamed_linear_mvm,
)
from .calibration import OutputCalibration, output_calibration_from_profile
from .checkpoint_loader import (
    CheckpointIngestionResult,
    CheckpointInventory,
    FileProvenance,
    load_hf_checkpoint,
)
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
from .decoder_primitives import (
    apply_rope,
    cached_attention_step,
    causal_attention,
    gelu,
    layer_norm,
    rms_norm,
    silu,
    swiglu,
)
from .device_profile import load_device_profile, validate_device_profile
from .generalized_decoder import GeneralizedDecoder
from .model_manifest import ModelManifest, TensorSpec
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
    "BlockStreamedLinear",
    "CheckpointIngestionResult",
    "CheckpointInventory",
    "CrossbarTile",
    "ErrorAttributionResult",
    "FileProvenance",
    "GeneralizedDecoder",
    "MechanismMetrics",
    "Metrics",
    "ModelManifest",
    "OutputCalibration",
    "StreamedMemoryBudget",
    "TensorSpec",
    "TinyGPT",
    "TinyGPTConfig",
    "adc",
    "apply_conductance_drift",
    "apply_iv_nonlinearity",
    "apply_programming_variation",
    "apply_read_noise",
    "apply_rope",
    "apply_stuck_faults",
    "attribute_from_profiles",
    "attribute_tile_error",
    "build_tile_factory",
    "build_tile_factory_from_converter_profiles",
    "cached_attention_step",
    "calculate_execution_memory_budget",
    "causal_attention",
    "converter_config_from_profiles",
    "dac",
    "evaluate_attribution_suite",
    "gelu",
    "layer_norm",
    "load_device_profile",
    "load_hf_checkpoint",
    "map_differential",
    "mvm",
    "nonideality_config_from_profile",
    "output_calibration_from_profile",
    "rms_norm",
    "scale_weights",
    "silu",
    "solve_crossbar_nodal",
    "streamed_linear_mvm",
    "swiglu",
    "symmetric_converter",
    "tile_config_from_profile",
    "validate_device_profile",
]
