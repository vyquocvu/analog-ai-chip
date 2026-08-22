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
from .kv_hierarchy import (
    AttentionWorkloadStep,
    KVCachePlacement,
    KVHierarchyConfig,
    KVHierarchySummary,
    analyze_kv_hierarchy,
    calculate_kv_cache_bytes,
)
from .large_model_eval import (
    LargeModelAttributionReport,
    MechanismEvaluationResult,
    compute_cross_entropy_perplexity,
    compute_mean_kl_divergence,
    compute_top1_agreement,
    evaluate_large_model_error_attribution,
)
from .model_manifest import ModelManifest, TensorSpec
from .profile_adapter import (
    CROSSBAR_NONIDEALITY_FIELDS,
    build_tile_factory,
    build_tile_factory_from_converter_profiles,
    converter_config_from_profiles,
    nonideality_config_from_profile,
    tile_config_from_profile,
)
from .recovery import (
    LayerSensitivity,
    RecoveryLedgerEntry,
    RecoveryStrategy,
    ScalableRecoveryReport,
    evaluate_layer_sensitivities,
    evaluate_scalable_recovery_suite,
)
from .residency import (
    HardwareTopologyConfig,
    ModelResidencySummary,
    ResidencySchedule,
    ScheduleMetrics,
    analyze_model_residency,
)
from .resumable_evaluator import (
    TIER_BUDGETS,
    LayerEvaluationCheckpoint,
    ResumableModelEvaluator,
    TierBudget,
    compute_tensor_sha256,
)
from .surrogate import (
    EvaluationMode,
    NonIdealityEvaluationResult,
    SurrogateCalibrationProfile,
    calibrate_surrogate,
    evaluate_projection_nonideality,
)
from .tile import CrossbarTile
from .transformer import Metrics, TinyGPT, TinyGPTConfig

__all__ = [
    "CROSSBAR_NONIDEALITY_FIELDS",
    "TIER_BUDGETS",
    "Accelerator",
    "AttentionWorkloadStep",
    "BlockStreamedLinear",
    "CheckpointIngestionResult",
    "CheckpointInventory",
    "CrossbarTile",
    "ErrorAttributionResult",
    "EvaluationMode",
    "FileProvenance",
    "GeneralizedDecoder",
    "HardwareTopologyConfig",
    "KVCachePlacement",
    "KVHierarchyConfig",
    "KVHierarchySummary",
    "LargeModelAttributionReport",
    "LayerEvaluationCheckpoint",
    "LayerSensitivity",
    "MechanismEvaluationResult",
    "MechanismMetrics",
    "Metrics",
    "ModelManifest",
    "ModelResidencySummary",
    "NonIdealityEvaluationResult",
    "OutputCalibration",
    "RecoveryLedgerEntry",
    "RecoveryStrategy",
    "ResidencySchedule",
    "ResumableModelEvaluator",
    "ScalableRecoveryReport",
    "ScheduleMetrics",
    "StreamedMemoryBudget",
    "SurrogateCalibrationProfile",
    "TensorSpec",
    "TierBudget",
    "TinyGPT",
    "TinyGPTConfig",
    "adc",
    "analyze_kv_hierarchy",
    "analyze_model_residency",
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
    "calculate_kv_cache_bytes",
    "calibrate_surrogate",
    "causal_attention",
    "compute_cross_entropy_perplexity",
    "compute_mean_kl_divergence",
    "compute_tensor_sha256",
    "compute_top1_agreement",
    "converter_config_from_profiles",
    "dac",
    "evaluate_attribution_suite",
    "evaluate_large_model_error_attribution",
    "evaluate_layer_sensitivities",
    "evaluate_projection_nonideality",
    "evaluate_scalable_recovery_suite",
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
