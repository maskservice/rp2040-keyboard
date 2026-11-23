#!/usr/bin/env python3
"""
Debug firmware dla RP2040-Zero - specjalnie dla Ctrl+Alt+7
Uruchom na RP2040-Zero do testowania przycisku 7
"""

import time
import board
import digitalio
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.mouse import Mouse

# Inicjalizacja HID
keyboard = Keyboard(usb_hid.devices)
mouse = Mouse(usb_hid.devices)

print("=== DEBUG Ctrl+Alt+7 RP2040-Zero ===")
print("Testowanie różnych metod wysyłania Ctrl+Alt+7")
print("Podłącz przycisk do GP7 i masy")

# Przycisk 7 na GP7 (Ctrl+Alt+7)
key_7_pin = digitalio.DigitalInOut(board.GP7)
key_7_pin.direction = digitalio.Direction.INPUT
key_7_pin.pull = digitalio.Pull.UP

# Przycisk testowy na GP1 do zmiany metod
test_pin = digitalio.DigitalInOut(board.GP1)
test_pin.direction = digitalio.Direction.INPUT
test_pin.pull = digitalio.Pull.UP

# Zmienne
last_key7_state = True
last_test_state = True
last_change = 0
test_method = 0
DEBOUNCE_MS = 50

def test_method_1():
    """Metoda 1: press(CONTROL, ALT, SEVEN) + release_all()"""
    print("Metoda 1: press(CONTROL, ALT, SEVEN) + release_all()")
    keyboard.press(Keycode.CONTROL, Keycode.ALT, Keycode.SEVEN)
    time.sleep(0.05)
    keyboard.release_all()

def test_method_2():
    """Metoda 2: press(CONTROL) + press(ALT) + press(SEVEN) + release_all()"""
    print("Metoda 2: press(CONTROL) + press(ALT) + press(SEVEN) + release_all()")
    keyboard.press(Keycode.CONTROL)
    time.sleep(0.01)
    keyboard.press(Keycode.ALT)
    time.sleep(0.01)
    keyboard.press(Keycode.SEVEN)
    time.sleep(0.05)
    keyboard.release_all()

def test_method_3():
    """Metoda 3: press(CONTROL, ALT) + press(SEVEN) + release_all()"""
    print("Metoda 3: press(CONTROL, ALT) + press(SEVEN) + release_all()")
    keyboard.press(Keycode.CONTROL, Keycode.ALT)
    time.sleep(0.01)
    keyboard.press(Keycode.SEVEN)
    time.sleep(0.05)
    keyboard.release_all()

def test_method_4():
    """Metoda 4: Wysyłanie pojedynczych klawiszy z opóźnieniami"""
    print("Metoda 4: Pojedyncze klawisze z opóźnieniami")
    keyboard.press(Keycode.CONTROL)
    time.sleep(0.02)
    keyboard.press(Keycode.ALT)
    time.sleep(0.02)
    keyboard.press(Keycode.SEVEN)
    time.sleep(0.1)
    keyboard.release(Keycode.SEVEN)
    time.sleep(0.01)
    keyboard.release(Keycode.ALT)
    time.sleep(0.01)
    keyboard.release(Keycode.CONTROL)

def test_method_5():
    """Metoda 5: Dłuższe przytrzymanie"""
    print("Metoda 5: Dłuższe przytrzymanie (0.2s)")
    keyboard.press(Keycode.CONTROL, Keycode.ALT, Keycode.SEVEN)
    time.sleep(0.2)
    keyboard.release_all()

methods = [test_method_1, test_method_2, test_method_3, test_method_4, test_method_5]

print(f"Aktualna metoda: {test_method + 1}/5")
print("Wciśnij GP1 aby zmienić metodę, GP7 aby testować Ctrl+Alt+7")

while True:
    now = time.monotonic() * 1000
    key7_current = key_7_pin.value
    test_current = test_pin.value
    
    # Obsługa przycisku zmiany metody (GP1)
    if test_current != last_test_state:
        if (now - last_change) > DEBOUNCE_MS:
            last_change = now
            last_test_state = test_current
            
            if not test_current:  # Wciśnięcie
                test_method = (test_method + 1) % len(methods)
                print(f"\n--- Zmieniono na metodę {test_method + 1}/5 ---")
                methods[test_method]()
                print(f"Wciśnij GP7 dla testu metodą {test_method + 1}")
    
    # Obsługa przycisku 7 (GP7)
    if key7_current != last_key7_state:
        if (now - last_change) > DEBOUNCE_MS:
            last_change = now
            last_key7_state = key7_current
            
            if not key7_current:  # Wciśnięcie
                print(f"\n=== TEST Metoda {test_method + 1}/5 ===")
                print("Wciśnięto przycisk 7 (GP7) - wysyłanie Ctrl+Alt+7")
                methods[test_method]()
                print("Zakończono wysyłanie")
    
    time.sleep(0.001)
