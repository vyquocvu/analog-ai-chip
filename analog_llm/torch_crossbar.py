"""GPU-accelerated PyTorch crossbar simulation backend.

Provides batched, mixed-precision matrix-vector multiplication for analog crossbars
with fused converter quantization and GPU-native IR-drop perturbation modeling.
"""

from __future__ import annotations

from typing import Any

try:
    import torch
    from torch import nn

    _TORCH_AVAILABLE = True
except ImportError:  # pragma: no cover
    _TORCH_AVAILABLE = False
    torch = None  # type: ignore
    nn = Any  # type: ignore


def is_torch_available() -> bool:
    """Return True if PyTorch is installed and available."""
    return _TORCH_AVAILABLE


if _TORCH_AVAILABLE:

    class FusedSymmetricConverter(torch.autograd.Function):
        """Quantize values to symmetric n-bit codes in device registers.

        Performs clipping, rounding, and dequantization without host-device synchronization.
        """

        @staticmethod
        def forward(  # type: ignore[override]
            ctx: Any,
            x: torch.Tensor,
            bits: int,
            vmax: float = 1.0,
        ) -> torch.Tensor:
            if bits < 2:
                raise ValueError("bits must be an integer >= 2")
            qmax = 2 ** (bits - 1) - 1
            scale = vmax / qmax
            scale_inv = qmax / vmax

            # Fused clip and round-to-nearest
            x_clipped = torch.clamp(x, -vmax, vmax)
            codes = torch.round(x_clipped * scale_inv).clamp(-qmax, qmax)
            return codes * scale

        @staticmethod
        def backward(ctx: Any, grad_output: torch.Tensor) -> tuple[torch.Tensor, None, None]:  # type: ignore[override]
            # Straight-Through Estimator (STE) for quantization-aware training/gradient flows
            return grad_output, None, None

    def quantize_converter(
        x: torch.Tensor,
        bits: int,
        vmax: float = 1.0,
    ) -> torch.Tensor:
        """Functional symmetric converter wrapper."""
        return FusedSymmetricConverter.apply(x, bits, vmax)

    class TorchCrossbarLinear(nn.Module):
        """Batched PyTorch linear layer modeling analog crossbar non-idealities.

        Precision policy:
        - Weights & activations: FP16 or BF16 for Tensor Core GEMM.
        - Accumulation & partial sums: FP32 for numerical stability.
        - Converter quantization: Fused in device registers.
        """

        def __init__(
            self,
            in_features: int,
            out_features: int,
            g_bits: int = 6,
            dac_bits: int = 8,
            adc_bits: int = 8,
            vin_max: float = 1.0,
            vout_max: float = 1.0,
            gmin: float = 0.05,
            gmax: float = 1.0,
            r_wire_ohm: float = 0.0,
            dtype: torch.dtype = torch.float32,
            device: torch.device | str | None = None,
        ) -> None:
            super().__init__()
            self.in_features = in_features
            self.out_features = out_features
            self.g_bits = g_bits
            self.dac_bits = dac_bits
            self.adc_bits = adc_bits
            self.vin_max = vin_max
            self.vout_max = vout_max
            self.gmin = gmin
            self.gmax = gmax
            self.r_wire_ohm = r_wire_ohm
            self.target_dtype = dtype

            # Registered weight buffers on device
            self.register_buffer(
                "weight_scale", torch.tensor(1.0, dtype=torch.float32, device=device)
            )
            self.register_buffer(
                "g_pos", torch.zeros(out_features, in_features, dtype=dtype, device=device)
            )
            self.register_buffer(
                "g_neg", torch.zeros(out_features, in_features, dtype=dtype, device=device)
            )

        @torch.no_grad()
        def program_weights(self, weights: torch.Tensor) -> None:
            """Program signed weights onto differential conductances (G+, G-)."""
            w = weights.to(device=self.g_pos.device, dtype=torch.float32)
            if w.shape != (self.out_features, self.in_features):
                raise ValueError(
                    f"Weight shape {w.shape} != ({self.out_features}, {self.in_features})"
                )

            peak = float(torch.max(torch.abs(w)).item()) if w.numel() > 0 else 0.0
            scale = max(peak, 1e-12)
            self.weight_scale.copy_(torch.tensor(scale, dtype=torch.float32))

            w_norm = torch.clamp(w / scale, -1.0, 1.0)
            w_pos = torch.clamp(w_norm, min=0.0)
            w_neg = torch.clamp(-w_norm, min=0.0)

            # Quantize conductances
            levels = 2**self.g_bits - 1
            g_span = self.gmax - self.gmin

            gp = self.gmin + (torch.round(w_pos * levels) / levels) * g_span
            gn = self.gmin + (torch.round(w_neg * levels) / levels) * g_span
            gp[w_pos == 0.0] = self.gmin
            gn[w_neg == 0.0] = self.gmin

            self.g_pos.copy_(gp.to(self.target_dtype))
            self.g_neg.copy_(gn.to(self.target_dtype))

        def _apply_ir_drop_perturbation(
            self,
            v_eff: torch.Tensor,
            g_mat: torch.Tensor,
        ) -> torch.Tensor:
            """First-order Neumann series perturbation for 2D crossbar IR drop on GPU.

            Computes voltage attenuation along row lines and voltage elevation
            along column lines via parallel cumulative sums.
            """
            # v_eff: [..., in_features], g_mat: [out_features, in_features]
            # First order cell currents: [..., out_features, in_features]
            i_cell_0 = v_eff.unsqueeze(-2) * g_mat.unsqueeze(0)

            # Cumulative row currents left-to-right (diverted along row)
            i_row_cum = torch.cumsum(i_cell_0.flip(-1), dim=-1).flip(-1)
            v_drop_row = self.r_wire_ohm * torch.cumsum(i_row_cum, dim=-1)

            # Cumulative col currents top-to-bottom (summed toward TIA at bottom)
            i_col_cum = torch.cumsum(i_cell_0, dim=-2)
            v_rise_col = self.r_wire_ohm * torch.cumsum(i_col_cum.flip(-2), dim=-2).flip(-2)

            v_cell = torch.clamp(v_eff.unsqueeze(-2) - v_drop_row - v_rise_col, min=0.0)
            # Sum currents across rows into column outputs
            return torch.sum(v_cell * g_mat.unsqueeze(0), dim=-1)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            """Batched forward pass: shape [..., in_features] -> [..., out_features]."""
            in_shape = x.shape
            x_flat = x.reshape(-1, self.in_features).to(self.target_dtype)

            # 1. Dynamic range scaling without CPU sync (stays in GPU registers)
            token_peaks = torch.amax(torch.abs(x_flat), dim=-1, keepdim=True).clamp(min=1e-12)
            x_norm = x_flat / token_peaks * self.vin_max

            # 2. Input DAC quantization
            v_eff = quantize_converter(x_norm, self.dac_bits, self.vin_max)

            # 3. MVM evaluation (ideal or with GPU-native IR drop)
            if self.r_wire_ohm > 1e-12:
                ip = self._apply_ir_drop_perturbation(v_eff, self.g_pos)
                in_ = self._apply_ir_drop_perturbation(v_eff, self.g_neg)
                s = ip - in_
            else:
                # Direct GEMM: [Tokens, In] @ [In, Out] -> [Tokens, Out]
                ip = torch.matmul(v_eff, self.g_pos.t())
                in_ = torch.matmul(v_eff, self.g_neg.t())
                s = ip - in_

            # 4. Rescale and output ADC quantization
            g_span = self.gmax - self.gmin
            s = s / g_span
            y = s * (self.weight_scale * token_peaks / self.vin_max)
            y_adc = quantize_converter(y, self.adc_bits, self.vout_max)

            return y_adc.reshape(*in_shape[:-1], self.out_features)
