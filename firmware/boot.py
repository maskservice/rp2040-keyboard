"""
boot.py — Konfiguracja USB HID
===============================
Włącza jednoczesną emulację klawiatury i myszki.
Plik uruchamiany przy starcie RP2040 PRZED code.py.
"""

import usb_hid

# Włączenie obu urządzeń HID: klawiatura + mysz
usb_hid.enable(
    (
        usb_hid.Device.KEYBOARD,
        usb_hid.Device.MOUSE,
    )
)
