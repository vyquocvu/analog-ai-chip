"""Scalable non-ideality evaluation and statistical surrogates.

Defines exact, layer-sampled, and statistical-surrogate evaluation modes with
stratified calibration against profile-driven physical tile simulations and
strict fail-closed domain verification.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .accelerator import Accelerator
from .block_stream import streamed_linear_mvm
from .tile import CrossbarTile

FloatArray = NDArray[np.float64]


class EvaluationMode(str, Enum):
    """Explicit simulation fidelity modes."""

    EXACT = "exact"
    LAYER_SAMPLED = "layer-sampled"
    STATISTICAL_SURROGATE = "statistical-surrogate"


@dataclass(frozen=True)
class SurrogateCalibrationProfile:
    """Calibrated statistical error profile for one projection family."""

    layer_family: str
    error_mean: float
    error_std: float
    snr_db: float
    max_abs_error: float
    relative_l2_error_pct: float
    calibrated_weight_max: float
    tile_rows: int
    tile_cols: int
    num_samples: int
    profile_name: str

    def validate_domain(self, weight: FloatArray, tile_rows: int, tile_cols: int) -> None:
        """Fail closed if evaluation parameters exceed the calibrated domain."""
        if tile_rows != self.tile_rows or tile_cols != self.tile_cols:
            raise ValueError(
                f"Tile dimension mismatch: requested {tile_rows}x{tile_cols}, "
                f"calibrated for {self.tile_rows}x{self.tile_cols}"
            )
        weight_max = float(np.max(np.abs(weight)))
        if weight_max > self.calibrated_weight_max * 1.5:
            raise ValueError(
                f"Weight magnitude {weight_max:.3f} exceeds calibrated domain limit "
                f"{self.calibrated_weight_max * 1.5:.3f}"
            )


@dataclass(frozen=True)
class NonIdealityEvaluationResult:
    """Output tensor tagged with explicit simulation mode and error metrics."""

    output: FloatArray
    mode: EvaluationMode
    is_physical_simulation: bool
    mode_description: str
    metadata: dict[str, Any]


def calibrate_surrogate(
    tile_factory: Callable[[], CrossbarTile],
    layer_family: str,
    in_features: int = 64,
    out_features: int = 64,
    tile_rows: int = 16,
    tile_cols: int = 16,
    num_samples: int = 10,
    weight_max: float = 0.5,
    seed: int = 42,
    profile_name: str = "crossbar-v1",
) -> SurrogateCalibrationProfile:
    """Calibrate statistical surrogate error against exact profile-driven tile execution."""
    rng = np.random.default_rng(seed)
    errors: list[float] = []
    signal_powers: list[float] = []
    noise_powers: list[float] = []
    max_errs: list[float] = []

    for _ in range(num_samples):
        # Generate representative projection weights and activations
        W = rng.normal(0.0, weight_max / 2.0, (out_features, in_features))
        x = rng.normal(0.0, 1.0, (in_features,))

        float_ref = W @ x

        # Exact physical tile execution
        acc = Accelerator(tile_factory, tile_rows, tile_cols, tile_count=16)
        exact_out = streamed_linear_mvm(x, W, tile_rows=tile_rows, tile_cols=tile_cols, accelerator=acc)

        delta = exact_out - float_ref
        errors.extend(delta.tolist())
        max_errs.append(float(np.max(np.abs(delta))))

        sig_pow = float(np.mean(float_ref**2))
        noise_pow = float(np.mean(delta**2))
        signal_powers.append(sig_pow)
        noise_powers.append(max(1e-12, noise_pow))

    err_arr = np.array(errors)
    mean_err = float(np.mean(err_arr))
    std_err = float(np.std(err_arr))
    avg_sig = float(np.mean(signal_powers))
    avg_noise = float(np.mean(noise_powers))
    snr_db = 10.0 * math.log10(avg_sig / avg_noise) if avg_noise > 0 else 100.0
    rel_l2_pct = (math.sqrt(avg_noise) / max(1e-12, math.sqrt(avg_sig))) * 100.0

    return SurrogateCalibrationProfile(
        layer_family=layer_family,
        error_mean=mean_err,
        error_std=std_err,
        snr_db=snr_db,
        max_abs_error=float(np.max(max_errs)),
        relative_l2_error_pct=rel_l2_pct,
        calibrated_weight_max=weight_max,
        tile_rows=tile_rows,
        tile_cols=tile_cols,
        num_samples=num_samples,
        profile_name=profile_name,
    )


def evaluate_projection_nonideality(
    x: FloatArray,
    weight: FloatArray,
    bias: FloatArray | None = None,
    mode: EvaluationMode = EvaluationMode.EXACT,
    tile_factory: Callable[[], CrossbarTile] | None = None,
    tile_rows: int = 16,
    tile_cols: int = 16,
    surrogate_profile: SurrogateCalibrationProfile | None = None,
    layer_index: int = 0,
    sampled_layer_indices: Sequence[int] = (0,),
    rng: np.random.Generator | None = None,
) -> NonIdealityEvaluationResult:
    """Evaluate linear projection under exact, layer-sampled, or surrogate simulation mode."""
    weight_arr = np.asarray(weight)
    x_arr = np.asarray(x, dtype=np.float64)
    float_out = x_arr @ weight_arr.T
    if bias is not None:
        float_out += np.asarray(bias, dtype=np.float64)

    if mode == EvaluationMode.EXACT:
        if tile_factory is None:
            raise ValueError("Exact evaluation mode requires tile_factory")
        acc = Accelerator(tile_factory, tile_rows, tile_cols, tile_count=16)
        out = streamed_linear_mvm(
            x_arr, weight_arr, bias=bias, tile_rows=tile_rows, tile_cols=tile_cols, accelerator=acc
        )
        return NonIdealityEvaluationResult(
            output=out,
            mode=EvaluationMode.EXACT,
            is_physical_simulation=True,
            mode_description="Full profile-driven physical tile MVM simulation",
            metadata={"macs": acc.macs, "tile_cycles": acc.tile_cycles},
        )

    if mode == EvaluationMode.LAYER_SAMPLED:
        is_sampled = layer_index in sampled_layer_indices
        if is_sampled:
            if tile_factory is None:
                raise ValueError("Layer-sampled mode requires tile_factory for sampled layers")
            acc = Accelerator(tile_factory, tile_rows, tile_cols, tile_count=16)
            out = streamed_linear_mvm(
                x_arr, weight_arr, bias=bias, tile_rows=tile_rows, tile_cols=tile_cols, accelerator=acc
            )
            return NonIdealityEvaluationResult(
                output=out,
                mode=EvaluationMode.LAYER_SAMPLED,
                is_physical_simulation=True,
                mode_description=f"Exact physical simulation on sampled layer {layer_index}",
                metadata={"layer_index": layer_index, "sampled": True, "macs": acc.macs},
            )
        return NonIdealityEvaluationResult(
            output=float_out,
            mode=EvaluationMode.LAYER_SAMPLED,
            is_physical_simulation=False,
            mode_description=f"Digital float bypass on un-sampled layer {layer_index}",
            metadata={"layer_index": layer_index, "sampled": False, "macs": 0},
        )

    if mode == EvaluationMode.STATISTICAL_SURROGATE:
        if surrogate_profile is None:
            raise ValueError("Statistical surrogate mode requires a calibrated surrogate_profile")
        surrogate_profile.validate_domain(weight_arr, tile_rows, tile_cols)

        local_rng = rng if rng is not None else np.random.default_rng(42)
        noise = local_rng.normal(
            loc=surrogate_profile.error_mean,
            scale=surrogate_profile.error_std,
            size=float_out.shape,
        )
        surrogate_out = float_out + noise
        return NonIdealityEvaluationResult(
            output=surrogate_out,
            mode=EvaluationMode.STATISTICAL_SURROGATE,
            is_physical_simulation=False,
            mode_description="Calibrated empirical Gaussian statistical surrogate noise injection",
            metadata={
                "snr_db": surrogate_profile.snr_db,
                "error_std": surrogate_profile.error_std,
                "layer_family": surrogate_profile.layer_family,
            },
        )

    raise ValueError(f"Unknown evaluation mode: {mode}")
