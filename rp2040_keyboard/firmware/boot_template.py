"""
CircuitPython boot.py template for RP2040-One HID Keypad
========================================================

This file initializes USB HID devices (keyboard + mouse) and should be
placed in the root directory of the CircuitPython drive.
"""

BOOT_PY = '''
import usb_hid
import time
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.mouse import Mouse

# Enable USB HID devices
time.sleep(1)  # Wait for USB enumeration
keyboard = Keyboard(usb_hid.devices)
mouse = Mouse(usb_hid.devices)
'''
