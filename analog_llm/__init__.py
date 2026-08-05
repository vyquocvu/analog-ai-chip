"""Hybrid analog-digital LLM accelerator simulator.

Build a crossbar tile, route a small transformer through it, and measure how
converter and conductance non-idealities change the output.
"""

from .accelerator import Accelerator
from .converters import adc, dac, symmetric_converter
from .crossbar import map_differential, mvm, scale_weights
from .tile import CrossbarTile
from .transformer import Metrics, TinyGPT, TinyGPTConfig

__all__ = [
    "Accelerator",
    "CrossbarTile",
    "Metrics",
    "TinyGPT",
    "TinyGPTConfig",
    "adc",
    "dac",
    "map_differential",
    "mvm",
    "scale_weights",
    "symmetric_converter",
]
