"""Architecture-neutral, fail-closed decoder model contract.

This module describes functional tensor semantics only.  Its byte and MAC
counts are analytical software inventory values, not physical-hardware claims.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import prod
from typing import Mapping, Sequence


_DTYPE_BYTES = {"float16": 2, "bfloat16": 2, "float32": 4, "float64": 8}
_NORMS = {"layernorm", "rmsnorm"}
_POSITIONS = {"learned", "rope"}
_ACTIVATIONS = {"gelu", "swiglu"}
_ATTENTIONS = {"mha", "gqa", "mqa"}


@dataclass(frozen=True)
class TensorSpec:
    """One canonical tensor, with dimensions in simulator-native layout."""

    shape: tuple[int, ...]
    layout: str
    analog_eligible: bool

    @property
    def parameters(self) -> int:
        return prod(self.shape)


@dataclass(frozen=True)
class ModelManifest:
    """Version 1 contract for a decoder-only transformer's static tensors.

    Linear matrices always use ``out_in`` layout.  Embedding tables use
    ``vocab_hidden`` and vectors use ``vector``; checkpoint adapters must name
    any transpose before validating against this contract.
    """

    vocab_size: int
    hidden_size: int
    num_layers: int
    num_attention_heads: int
    num_key_value_heads: int
    intermediate_size: int
    context_length: int
    dtype: str = "float32"
    norm_type: str = "layernorm"
    position_type: str = "learned"
    activation_type: str = "gelu"
    attention_type: str = "mha"
    linear_bias: bool = True
    tied_embeddings: bool = True
    tensor_layout: str = "out_in"
    version: int = 1

    def __post_init__(self) -> None:
        integer_fields = {
            "vocab_size": self.vocab_size,
            "hidden_size": self.hidden_size,
            "num_layers": self.num_layers,
            "num_attention_heads": self.num_attention_heads,
            "num_key_value_heads": self.num_key_value_heads,
            "intermediate_size": self.intermediate_size,
            "context_length": self.context_length,
        }
        for name, value in integer_fields.items():
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.version != 1:
            raise ValueError(f"unsupported manifest version: {self.version}")
        self._require_choice("dtype", self.dtype, set(_DTYPE_BYTES))
        self._require_choice("norm_type", self.norm_type, _NORMS)
        self._require_choice("position_type", self.position_type, _POSITIONS)
        self._require_choice("activation_type", self.activation_type, _ACTIVATIONS)
        self._require_choice("attention_type", self.attention_type, _ATTENTIONS)
        if self.tensor_layout != "out_in":
            raise ValueError("tensor_layout must explicitly be 'out_in'")
        if self.hidden_size % self.num_attention_heads:
            raise ValueError("hidden_size must be divisible by num_attention_heads")
        if self.num_attention_heads % self.num_key_value_heads:
            raise ValueError("num_attention_heads must be divisible by num_key_value_heads")
        expected_kv = {
            "mha": self.num_attention_heads,
            "mqa": 1,
        }.get(self.attention_type)
        if expected_kv is not None and self.num_key_value_heads != expected_kv:
            raise ValueError(f"{self.attention_type} requires num_key_value_heads={expected_kv}")
        if self.attention_type == "gqa" and not (
            1 < self.num_key_value_heads < self.num_attention_heads
        ):
            raise ValueError("gqa requires key/value heads strictly between MQA and MHA")

    @staticmethod
    def _require_choice(name: str, value: str, choices: set[str]) -> None:
        if value not in choices:
            raise ValueError(f"unsupported {name} {value!r}; expected one of {sorted(choices)}")

    @property
    def head_dimension(self) -> int:
        return self.hidden_size // self.num_attention_heads

    @property
    def dtype_bytes(self) -> int:
        return _DTYPE_BYTES[self.dtype]

    def tensor_specs(self) -> dict[str, TensorSpec]:
        """Return the complete canonical tensor inventory."""
        h, i = self.hidden_size, self.intermediate_size
        kv = self.num_key_value_heads * self.head_dimension
        specs: dict[str, TensorSpec] = {
            "token_embedding.weight": TensorSpec((self.vocab_size, h), "vocab_hidden", False),
            "final_norm.weight": TensorSpec((h,), "vector", False),
        }
        if self.position_type == "learned":
            specs["position_embedding.weight"] = TensorSpec(
                (self.context_length, h), "position_hidden", False
            )
        if self.norm_type == "layernorm":
            specs["final_norm.bias"] = TensorSpec((h,), "vector", False)
        if not self.tied_embeddings:
            specs["lm_head.weight"] = TensorSpec((self.vocab_size, h), "out_in", True)

        for layer in range(self.num_layers):
            prefix = f"layers.{layer}"
            for norm in ("attention_norm", "mlp_norm"):
                specs[f"{prefix}.{norm}.weight"] = TensorSpec((h,), "vector", False)
                if self.norm_type == "layernorm":
                    specs[f"{prefix}.{norm}.bias"] = TensorSpec((h,), "vector", False)
            matrices = {
                "attention.q_proj.weight": (h, h),
                "attention.k_proj.weight": (kv, h),
                "attention.v_proj.weight": (kv, h),
                "attention.out_proj.weight": (h, h),
                "mlp.up_proj.weight": (i, h),
                "mlp.down_proj.weight": (h, i),
            }
            if self.activation_type == "swiglu":
                matrices["mlp.gate_proj.weight"] = (i, h)
            for name, shape in matrices.items():
                specs[f"{prefix}.{name}"] = TensorSpec(shape, "out_in", True)
                if self.linear_bias:
                    specs[f"{prefix}.{name.removesuffix('.weight')}.bias"] = TensorSpec(
                        (shape[0],), "vector", False
                    )
        return specs

    @property
    def parameter_count(self) -> int:
        """Number of independently stored scalar parameters (tied head excluded)."""
        return sum(spec.parameters for spec in self.tensor_specs().values())

    @property
    def per_layer_projection_macs(self) -> int:
        """Static linear MACs for one token in one decoder layer.

        Token-token score/value work depends on sequence length and remains a
        separate digital operation; this count covers only static projections.
        """
        h, i = self.hidden_size, self.intermediate_size
        kv = self.num_key_value_heads * self.head_dimension
        attention = h * h + 2 * kv * h + h * h
        mlp = 2 * h * i + (h * i if self.activation_type == "swiglu" else 0)
        return attention + mlp

    def kv_cache_bytes(self, tokens: int | None = None) -> int:
        """Bytes for K and V across all layers at ``tokens`` cached positions."""
        positions = self.context_length if tokens is None else tokens
        if (
            isinstance(positions, bool)
            or not isinstance(positions, int)
            or not (0 <= positions <= self.context_length)
        ):
            raise ValueError(f"tokens must be an integer in [0, {self.context_length}]")
        return (
            positions
            * self.num_layers
            * 2
            * self.num_key_value_heads
            * self.head_dimension
            * self.dtype_bytes
        )

    def validate_tensors(self, tensors: Mapping[str, Sequence[int]]) -> None:
        """Fail closed unless names and shapes exactly match the manifest."""
        expected = self.tensor_specs()
        missing = sorted(set(expected) - set(tensors))
        extra = sorted(set(tensors) - set(expected))
        if missing or extra:
            raise ValueError(f"tensor inventory mismatch: missing={missing}, extra={extra}")
        for name, spec in expected.items():
            shape = tuple(tensors[name])
            if shape != spec.shape:
                raise ValueError(f"tensor {name!r} has shape {shape}, expected {spec.shape}")
