"""Unit tests for GPU-accelerated PyTorch crossbar simulation backend."""

from __future__ import annotations

import pytest

from analog_llm.torch_crossbar import is_torch_available


def test_torch_availability_flag() -> None:
    """Check that is_torch_available() returns a boolean flag."""
    avail = is_torch_available()
    assert isinstance(avail, bool)


def test_torch_crossbar_module_if_available() -> None:
    """Test TorchCrossbarLinear when PyTorch is available in the environment."""
    if not is_torch_available():
        pytest.skip("PyTorch not installed in test environment")

    import torch

    from analog_llm.torch_crossbar import TorchCrossbarLinear, quantize_converter

    # 1. Converter quantization test
    x = torch.tensor([-1.2, -0.5, 0.0, 0.49, 1.5])
    q = quantize_converter(x, bits=4, vmax=1.0)
    assert q.shape == x.shape
    assert float(q.max()) <= 1.0
    assert float(q.min()) >= -1.0

    # 2. Linear layer forward shape and determinism
    in_features, out_features = 32, 16
    layer = TorchCrossbarLinear(
        in_features=in_features,
        out_features=out_features,
        g_bits=4,
        dac_bits=4,
        adc_bits=4,
    )
    w = torch.randn(out_features, in_features)
    layer.program_weights(w)

    inp = torch.randn(2, 5, in_features)  # [Batch, Tokens, In]
    out = layer(inp)
    assert out.shape == (2, 5, out_features)

    # 3. IR-drop attenuation test
    layer_ir = TorchCrossbarLinear(
        in_features=in_features,
        out_features=out_features,
        r_wire_ohm=1.0,
    )
    layer_ir.program_weights(w)
    out_ir = layer_ir(inp)
    assert out_ir.shape == (2, 5, out_features)
