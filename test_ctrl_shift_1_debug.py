#!/usr/bin/env python3
"""
Test skrypt do diagnostyki problemu z Ctrl+Shift+1
Uruchom na komputerze (nie na RP2040) do testowania HID
"""

import time
import board
import digitalio
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

# Inicjalizacja HID
keyboard = Keyboard(usb_hid.devices)

# Przycisk testowy na GP1
key_pin = digitalio.DigitalInOut(board.GP1)
key_pin.direction = digitalio.Direction.INPUT
key_pin.pull = digitalio.Pull.UP

print("=== DEBUG Ctrl+Shift+1 ===")
print("Testowanie różnych metod wysyłania klawiszy...")
print("Wciśnij przycisk GP1 aby testować")

test_mode = 0
last_state = True
last_change = 0
DEBOUNCE_MS = 20

def test_method_1():
    """Metoda 1: press() z pojedynczym release()"""
    print("Metoda 1: press(CONTROL, SHIFT, ONE) + release(CONTROL, SHIFT, ONE)")
    keyboard.press(Keycode.CONTROL, Keycode.SHIFT, Keycode.ONE)
    time.sleep(0.05)
    keyboard.release(Keycode.CONTROL, Keycode.SHIFT, Keycode.ONE)

def test_method_2():
    """Metoda 2: press() z release_all()"""
    print("Metoda 2: press(CONTROL, SHIFT, ONE) + release_all()")
    keyboard.press(Keycode.CONTROL, Keycode.SHIFT, Keycode.ONE)
    time.sleep(0.05)
    keyboard.release_all()

def test_method_3():
    """Metoda 3: press() individualnych klawiszy"""
    print("Metoda 3: press(CONTROL) + press(SHIFT) + press(ONE) + release_all()")
    keyboard.press(Keycode.CONTROL)
    time.sleep(0.01)
    keyboard.press(Keycode.SHIFT)
    time.sleep(0.01)
    keyboard.press(Keycode.ONE)
    time.sleep(0.05)
    keyboard.release_all()

def test_method_4():
    """Metoda 4: Z dodatkowym opóźnieniem przed release"""
    print("Metoda 4: Dłuższe przytrzymanie przed release")
    keyboard.press(Keycode.CONTROL, Keycode.SHIFT, Keycode.ONE)
    time.sleep(0.1)  # Dłuższe przytrzymanie
    keyboard.release_all()

methods = [test_method_1, test_method_2, test_method_3, test_method_4]

while True:
    now = time.monotonic() * 1000
    current = key_pin.value
    
    # Wykryj wciśnięcie przycisku
    if current != last_state:
        if (now - last_change) > DEBOUNCE_MS:
            last_change = now
            last_state = current
            
            if not current:  # Wciśnięcie
                print(f"\n--- Test {test_mode + 1}/4 ---")
                methods[test_mode]()
                test_mode = (test_mode + 1) % len(methods)
                print("Wciśnij ponownie dla następnej metody...")
    
    time.sleep(0.01)
