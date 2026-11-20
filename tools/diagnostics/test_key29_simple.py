#!/usr/bin/env python3
"""
Test firmware dla RP2040-Zero - specjalnie dla GP29 (Ctrl+Alt+9)
Sprawdza czy przycisk 9 działa poprawnie na GP29
"""

import time
import board
import digitalio
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.mouse import Mouse

print("=== TEST GP29 (Ctrl+Alt+9) ===")
print("Sprawdzenie czy przycisk 9 działa na GP29")
print("Podłącz przycisk do GP29 i masy")

# Inicjalizacja HID
keyboard = Keyboard(usb_hid.devices)
mouse = Mouse(usb_hid.devices)

# Przycisk 9 na GP29 (Ctrl+Alt+9)
key_29_pin = digitalio.DigitalInOut(board.GP29)
key_29_pin.direction = digitalio.Direction.INPUT
key_29_pin.pull = digitalio.Pull.UP

# Przycisk testowy na GP1 do porównania
key_1_pin = digitalio.DigitalInOut(board.GP1)
key_1_pin.direction = digitalio.Direction.INPUT
key_1_pin.pull = digitalio.Pull.UP

# Zmienne
last_key29_state = True
last_key1_state = True
last_change = 0
DEBOUNCE_MS = 50

print("GP29 konfiguracja:")
print(f"  Pin: {key_29_pin}")
print(f"  Direction: {key_29_pin.direction}")
print(f"  Pull: {key_29_pin.pull}")
print()
print("Testowanie - wciśnij przyciski:")
print("  GP1 -> Ctrl+Alt+1 (kontrolka)")
print("  GP29 -> Ctrl+Alt+9 (testowany)")

while True:
    now = time.monotonic() * 1000
    key29_current = key_29_pin.value
    key1_current = key_1_pin.value
    
    # Obsługa przycisku 1 (kontrolka)
    if key1_current != last_key1_state:
        if (now - last_change) > DEBOUNCE_MS:
            last_change = now
            last_key1_state = key1_current
            
            if not key1_current:  # Wciśnięcie
                print("✅ GP1 wciśnięty -> Ctrl+Alt+1")
                keyboard.press(Keycode.CONTROL, Keycode.ALT, Keycode.ONE)
                keyboard.release_all()
    
    # Obsługa przycisku 29 (testowany)
    if key29_current != last_key29_state:
        if (now - last_change) > DEBOUNCE_MS:
            last_change = now
            last_key29_state = key29_current
            
            if not key29_current:  # Wciśnięcie
                print("✅ GP29 wciśnięty -> Ctrl+Alt+9")
                keyboard.press(Keycode.CONTROL, Keycode.ALT, Keycode.NINE)
                keyboard.release_all()
            else:
                print("🔌 GP29 zwolniony")
    
    # Status co 2 sekundy
    if int(now) % 2000 < 50:  # Co 2 sekundy
        print(f"Status: GP1={key1_current} GP29={key29_current}")
    
    time.sleep(0.001)
