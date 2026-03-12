"""
Web module for RP2040-One HID Keypad
=====================================

Contains FastAPI web configurator for visual pin editing and code generation.
"""

from .app import app, create_app

__all__ = [
    "app",
    "create_app",
]

def create_app():
    """Create and configure FastAPI application."""
    return app
