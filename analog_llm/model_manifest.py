"""Architecture-neutral decoder-only model manifest.

The manifest is a semantic contract for model structure and checkpoint mapping.
It deliberately does not describe accelerator feasibility. R10 uses it to keep
GPT-2-style and Llama-style decoder semantics explicit before generalized
execution/checkpoint ingestion is added in later work packages.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import prod
from typing import Any, Mapping

_SUPPORTED_DTYPES = {"float16": 2, "bfloat16": 2, "float32": 4}
_SUPPORTED_NORMS = {"layernorm", "rmsnorm"}
_SUPPORTED_POSITIONS = {"learned", "rope"}
_SUPPORTED_ACTIVATIONS = {"gelu", "swiglu"}
_SUPPORTED_LAYOUTS = {"out_in", "rows_cols", "vector"}


@dataclass(frozen=True)
class TensorDescriptor:
    """Expected tensor shape plus an explicit, non-ambiguous layout contract."""

    shape: tuple[int, ...]
    layout: str

    def __post_init__(self) -> None:
        if not self.shape or any(dim <= 0 for dim in self.shape):
            raise ValueError(f"tensor shape must contain positive dimensions, got {self.shape}")
        if self.layout not in _SUPPORTED_LAYOUTS:
            raise ValueError(
                f"unsupported tensor layout {self.layout!r}; expected one of "
                f"{sorted(_SUPPORTED_LAYOUTS)}"
            )

    @property
    def elements(self) -> int:
        return prod(self.shape)


@dataclass(frozen=True)
class ModelManifest:
    """Versioned semantic description of a decoder-only Transformer.

    Weight matrices use the canonical ``[out, in]`` layout. Embedding matrices
    use ``[rows, cols]`` and scalar/vector parameters use ``vector``. Explicit
    layouts prevent checkpoint loaders from silently guessing transposes.
    """

    schema_version: str
    architecture: str
    vocab_size: int
    hidden_size: int
    num_layers: int
    num_attention_heads: int
    num_key_value_heads: int
    head_dim: int
    intermediate_size: int
    max_context: int
    dtype: str
    tie_embeddings: bool
    norm_type: str
    norm_bias: bool
    position_type: str
    activation: str
    linear_bias: bool

    def __post_init__(self) -> None:
        if self.schema_version != "1.0":
            raise ValueError(f"unsupported schema_version {self.schema_version!r}")
        if self.architecture != "decoder-only":
            raise ValueError("architecture must be 'decoder-only'")

        positive = {
            "vocab_size": self.vocab_size,
            "hidden_size": self.hidden_size,
            "num_layers": self.num_layers,
            "num_attention_heads": self.num_attention_heads,
            "num_key_value_heads": self.num_key_value_heads,
            "head_dim": self.head_dim,
            "intermediate_size": self.intermediate_size,
            "max_context": self.max_context,
        }
        invalid = [name for name, value in positive.items() if value <= 0]
        if invalid:
            raise ValueError(f"manifest dimensions must be positive: {', '.join(invalid)}")

        if self.hidden_size != self.num_attention_heads * self.head_dim:
            raise ValueError(
                "head_dim is inconsistent with hidden_size and num_attention_heads: "
                f"{self.hidden_size} != {self.num_attention_heads} * {self.head_dim}"
            )
        if self.num_attention_heads % self.num_key_value_heads != 0:
            raise ValueError(
                "num_key_value_heads must divide the number of attention heads "
                f"({self.num_attention_heads} % {self.num_key_value_heads} != 0)"
            )
        if self.dtype not in _SUPPORTED_DTYPES:
            raise ValueError(f"unsupported dtype {self.dtype!r}")
        if self.norm_type not in _SUPPORTED_NORMS:
            raise ValueError(f"unsupported norm_type {self.norm_type!r}")
        if self.position_type not in _SUPPORTED_POSITIONS:
            raise ValueError(f"unsupported position_type {self.position_type!r}")
        if self.activation not in _SUPPORTED_ACTIVATIONS:
            raise ValueError(f"unsupported activation {self.activation!r}")

    @property
    def kv_hidden_size(self) -> int:
        """Number of channels stored for one K or V vector per token."""
        return self.num_key_value_heads * self.head_dim

    @property
    def dtype_bytes(self) -> int:
        return _SUPPORTED_DTYPES[self.dtype]

    def expected_tensors(self) -> dict[str, TensorDescriptor]:
        """Return the exact neutral tensor inventory implied by this manifest."""
        h = self.hidden_size
        kv = self.kv_hidden_size
        m = self.intermediate_size
        specs: dict[str, TensorDescriptor] = {
            "token_embedding.weight": TensorDescriptor((self.vocab_size, h), "rows_cols"),
        }
        if self.position_type == "learned":
            specs["position_embedding.weight"] = TensorDescriptor(
                (self.max_context, h), "rows_cols"
            )

        for layer in range(self.num_layers):
            prefix = f"layers.{layer}"
            specs[f"{prefix}.attn_norm.weight"] = TensorDescriptor((h,), "vector")
            specs[f"{prefix}.attn.q.weight"] = TensorDescriptor((h, h), "out_in")
            specs[f"{prefix}.attn.k.weight"] = TensorDescriptor((kv, h), "out_in")
            specs[f"{prefix}.attn.v.weight"] = TensorDescriptor((kv, h), "out_in")
            specs[f"{prefix}.attn.o.weight"] = TensorDescriptor((h, h), "out_in")
            specs[f"{prefix}.mlp_norm.weight"] = TensorDescriptor((h,), "vector")

            if self.norm_bias:
                specs[f"{prefix}.attn_norm.bias"] = TensorDescriptor((h,), "vector")
                specs[f"{prefix}.mlp_norm.bias"] = TensorDescriptor((h,), "vector")
            if self.linear_bias:
                specs[f"{prefix}.attn.q.bias"] = TensorDescriptor((h,), "vector")
                specs[f"{prefix}.attn.k.bias"] = TensorDescriptor((kv,), "vector")
                specs[f"{prefix}.attn.v.bias"] = TensorDescriptor((kv,), "vector")
                specs[f"{prefix}.attn.o.bias"] = TensorDescriptor((h,), "vector")

            if self.activation == "gelu":
                specs[f"{prefix}.mlp.up.weight"] = TensorDescriptor((m, h), "out_in")
                specs[f"{prefix}.mlp.down.weight"] = TensorDescriptor((h, m), "out_in")
                if self.linear_bias:
                    specs[f"{prefix}.mlp.up.bias"] = TensorDescriptor((m,), "vector")
                    specs[f"{prefix}.mlp.down.bias"] = TensorDescriptor((h,), "vector")
            else:  # swiglu
                specs[f"{prefix}.mlp.gate.weight"] = TensorDescriptor((m, h), "out_in")
                specs[f"{prefix}.mlp.up.weight"] = TensorDescriptor((m, h), "out_in")
                specs[f"{prefix}.mlp.down.weight"] = TensorDescriptor((h, m), "out_in")
                if self.linear_bias:
                    specs[f"{prefix}.mlp.gate.bias"] = TensorDescriptor((m,), "vector")
                    specs[f"{prefix}.mlp.up.bias"] = TensorDescriptor((m,), "vector")
                    specs[f"{prefix}.mlp.down.bias"] = TensorDescriptor((h,), "vector")

        specs["final_norm.weight"] = TensorDescriptor((h,), "vector")
        if self.norm_bias:
            specs["final_norm.bias"] = TensorDescriptor((h,), "vector")
        if not self.tie_embeddings:
            specs["lm_head.weight"] = TensorDescriptor((self.vocab_size, h), "out_in")
        return specs

    def parameter_count(self) -> int:
        """Return the number of unique trainable parameters implied by the manifest."""
        return sum(spec.elements for spec in self.expected_tensors().values())

    def per_layer_linear_macs(self) -> int:
        """Dense projection MACs for one token in one decoder layer.

        This intentionally excludes token-token attention score/value MACs because
        those depend on sequence length. It is the architecture-neutral static
        projection count used by later analog-eligibility inventories.
        """
        h = self.hidden_size
        kv = self.kv_hidden_size
        m = self.intermediate_size
        attention = h * h + h * kv + h * kv + h * h
        mlp = h * m + m * h
        if self.activation == "swiglu":
            mlp += h * m
        return attention + mlp

    def kv_bytes_per_token_per_layer(self) -> int:
        """Bytes for K and V cache entries for one token in one layer."""
        return 2 * self.kv_hidden_size * self.dtype_bytes

    def kv_cache_bytes(self, tokens: int) -> int:
        """Total decoder KV bytes for ``tokens`` across all layers."""
        if tokens <= 0:
            raise ValueError("tokens must be positive")
        if tokens > self.max_context:
            raise ValueError(
                f"tokens {tokens} exceed max_context {self.max_context}"
            )
        return tokens * self.num_layers * self.kv_bytes_per_token_per_layer()

    def validate_tensor_inventory(
        self, inventory: Mapping[str, TensorDescriptor]
    ) -> None:
        """Fail closed unless a checkpoint inventory exactly matches the contract."""
        expected = self.expected_tensors()
        missing = sorted(set(expected) - set(inventory))
        extra = sorted(set(inventory) - set(expected))
        if missing:
            raise ValueError(f"missing tensors: {', '.join(missing)}")
        if extra:
            raise ValueError(f"unexpected tensors: {', '.join(extra)}")

        for name, spec in expected.items():
            actual = inventory[name]
            if actual.layout not in _SUPPORTED_LAYOUTS:
                raise ValueError(f"tensor {name} has ambiguous/unsupported layout {actual.layout!r}")
            if actual.layout != spec.layout:
                raise ValueError(
                    f"tensor {name} layout {actual.layout!r} != expected {spec.layout!r}"
                )
            if actual.shape != spec.shape:
                raise ValueError(
                    f"tensor {name} shape {actual.shape} != expected {spec.shape}"
                )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the versioned manifest without derived fields."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ModelManifest:
        """Construct from an exact schema-v1 mapping; unknown keys fail closed."""
        known = set(cls.__dataclass_fields__)
        unknown = sorted(set(data) - known)
        missing = sorted(known - set(data))
        if unknown:
            raise ValueError(f"unknown manifest fields: {', '.join(unknown)}")
        if missing:
            raise ValueError(f"missing manifest fields: {', '.join(missing)}")
        return cls(**dict(data))
