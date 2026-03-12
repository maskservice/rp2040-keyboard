"""
CircuitPython boot.py template for RP2040-One HID Keypad
========================================================

This file initializes USB HID devices (keyboard + mouse) and should be
placed in the root directory of the CircuitPython drive.
"""

BOOT_PY = '''
import usb_hid

# Enable USB HID devices (keyboard + mouse + consumer control)
usb_hid.enable(
    (usb_hid.Device.KEYBOARD,
     usb_hid.Device.MOUSE,
     usb_hid.Device.CONSUMER_CONTROL)
)
'''
