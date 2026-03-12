"""
Firmware module for RP2040-One HID Keypad
==========================================

Contains CircuitPython code generation and validation logic.
"""

from .generator import generate_code_py, PadConfig, KeyConfig, EncoderConfig, KEYCODES, MODIFIERS, AVAILABLE_GPIOS
from .validator import validate_config
from .boot_template import BOOT_PY

__all__ = [
    "generate_code_py",
    "PadConfig", 
    "KeyConfig",
    "EncoderConfig",
    "validate_config",
    "KEYCODES",
    "MODIFIERS", 
    "AVAILABLE_GPIOS",
    "BOOT_PY",
]

def generate_firmware(config: PadConfig) -> tuple[str, str]:
    """Generate complete firmware (boot.py + code.py) for given configuration."""
    is_valid, errors = validate_config(config)
    if not is_valid:
        raise ValueError(f"Invalid configuration: {errors}")
    
    code_py = generate_code_py(config)
    return BOOT_PY.strip(), code_py
