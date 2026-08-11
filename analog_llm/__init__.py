"""Hybrid analog-digital LLM accelerator simulator.

Build a crossbar tile, route a small transformer through it, and measure how
converter and conductance non-idealities change the output.
"""

from .accelerator import Accelerator
from .converters import adc, dac, symmetric_converter
from .crossbar import map_differential, mvm, scale_weights
from .device_profile import load_device_profile, validate_device_profile
from .profile_adapter import build_tile_factory, tile_config_from_profile
from .tile import CrossbarTile
from .transformer import Metrics, TinyGPT, TinyGPTConfig

__all__ = [
    "Accelerator",
    "CrossbarTile",
    "Metrics",
    "TinyGPT",
    "TinyGPTConfig",
    "adc",
    "build_tile_factory",
    "dac",
    "load_device_profile",
    "map_differential",
    "mvm",
    "scale_weights",
    "symmetric_converter",
    "tile_config_from_profile",
    "validate_device_profile",
]
