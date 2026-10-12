#!/usr/bin/env python3
"""
RP2040 HAL Configuration Models
===============================
Dataclass models for HAL key, encoder, and switch configurations.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass
class KeyConfig:
    gpio: int
    keycode: str
    modifier: str = "Keycode.CONTROL+Keycode.ALT"
    label: str = ""


@dataclass
class EncoderConfig:
    clk_gpio: int
    dt_gpio: int
    sw_gpio: int
    scroll_speed: int = 2
    middle_click: bool = True
    debounce_ms: int = 3


@dataclass
class PadConfig:
    keys: List[KeyConfig]
    encoder: Optional[EncoderConfig] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class HALSwitchConfig:
    """Konfiguracja przełącznika w formacie HAL."""

    gpio: int
    keycode: str
    modifier: str = "Keycode.CONTROL+Keycode.ALT"
    label: str = ""
    pull: str = "up"
    debounce: int = 10


@dataclass
class HALEncoderConfig:
    """Konfiguracja enkodera w formacie HAL."""

    enabled: bool = True
    clk_gpio: int = 11
    dt_gpio: int = 12
    sw_gpio: int = 13
    pull: str = "up"
    debounce: int = 3
    scroll_speed: int = 2
    middle_click: bool = True
    steps_per_revolution: int = 24


__all__ = [
    "EncoderConfig",
    "HALEncoderConfig",
    "HALSwitchConfig",
    "KeyConfig",
    "PadConfig",
]
