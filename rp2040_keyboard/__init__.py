"""
RP2040-One HID Keypad Package
==============================

Complete solution for RP2040-One based USB HID keypad with rotary encoder.
Includes firmware generator, web configurator, and comprehensive test suite.
"""

__version__ = "0.0.9"
__author__ = "Tom Sapletta"
__email__ = "tom@sapletta.com"

from .firmware import generate_firmware, validate_config
from .web import create_app
from .hal_manager import HALConfigManager

__all__ = [
    "generate_firmware",
    "validate_config", 
    "create_app",
    "HALConfigManager",
]
