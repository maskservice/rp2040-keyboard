import board
import digitalio
import time
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

# Inicjalizacja HID
keyboard = Keyboard(usb_hid.devices)

# Przycisk testowy
key_pin = digitalio.DigitalInOut(board.GP1)
key_pin.direction = digitalio.Direction.INPUT
key_pin.pull = digitalio.Pull.UP

print("Test klawiszy Ctrl+Alt+1...")

while True:
    if not key_pin.value:
        print("Wciśnięto przycisk - wysyłanie Ctrl+Alt+1")
        keyboard.press(Keycode.CONTROL, Keycode.ALT, Keycode.ONE)
        time.sleep(0.1)
        keyboard.release_all()
        time.sleep(0.3)  # Dłuższy debounce
    else:
        time.sleep(0.01)
