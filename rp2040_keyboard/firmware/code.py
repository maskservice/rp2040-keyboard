"""
RP2040-One HID Keypad + Encoder Mouse
======================================
9 klawiszy (Ctrl+Alt+1..Ctrl+Alt+9) + enkoder obrotowy (scroll myszki + middle-click)

Hardware:
  - Waveshare RP2040-One / RP2040-Zero
  - 9x switch buttons → GP1-GP9
  - 1x rotary encoder z przyciskiem → GP11 (CLK), GP12 (DT), GP13 (SW)

Firmware: CircuitPython 9.x + adafruit_hid

Autor: Softreck / Prototypowanie.pl
"""

import time
import board
import digitalio
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.mouse import Mouse

# =============================================================================
# KONFIGURACJA PINÓW
# =============================================================================

# Mapowanie klawiszy: (pin GPIO, klawisz numeryczny dla Ctrl+Alt+N)
KEY_PINS = [
    (board.GP1, Keycode.ONE),       # Przycisk 1 → Ctrl+Alt+1
    (board.GP2, Keycode.TWO),       # Przycisk 2 → Ctrl+Alt+2
    (board.GP3, Keycode.THREE),     # Przycisk 3 → Ctrl+Alt+3
    (board.GP4, Keycode.FOUR),      # Przycisk 4 → Ctrl+Alt+4
    (board.GP5, Keycode.FIVE),      # Przycisk 5 → Ctrl+Alt+5
    (board.GP6, Keycode.SIX),       # Przycisk 6 → Ctrl+Alt+6
    (board.GP7, Keycode.SEVEN),     # Przycisk 7 → Ctrl+Alt+7
    (board.GP8, Keycode.EIGHT),     # Przycisk 8 → Ctrl+Alt+8
    (board.GP9, Keycode.NINE),      # Przycisk 9 → Ctrl+Alt+9
]

# Enkoder obrotowy
ENCODER_CLK_PIN = board.GP11    # Encoder A (CLK)
ENCODER_DT_PIN = board.GP12   # Encoder B (DT)
ENCODER_SW_PIN = board.GP13   # Encoder push button (SW)

# Parametry scroll
SCROLL_SPEED = 2              # Ilość kroków scrolla na tick enkodera
DEBOUNCE_MS = 20              # Debounce w milisekundach dla przycisków
ENCODER_DEBOUNCE_MS = 5       # Debounce enkodera (krótszy dla płynności)

# =============================================================================
# INICJALIZACJA HID
# =============================================================================

keyboard = Keyboard(usb_hid.devices)
mouse = Mouse(usb_hid.devices)

# =============================================================================
# INICJALIZACJA PINÓW KLAWISZY
# =============================================================================

keys = []
for pin, keycode in KEY_PINS:
    dio = digitalio.DigitalInOut(pin)
    dio.direction = digitalio.Direction.INPUT
    dio.pull = digitalio.Pull.UP  # Wewnętrzny pull-up, przycisk zwiera do GND
    keys.append({
        'pin': dio,
        'keycode': keycode,
        'last_state': True,        # True = nie wciśnięty (pull-up)
        'last_change': 0,
    })

# =============================================================================
# INICJALIZACJA ENKODERA
# =============================================================================

encoder_clk = digitalio.DigitalInOut(ENCODER_CLK_PIN)
encoder_clk.direction = digitalio.Direction.INPUT
encoder_clk.pull = digitalio.Pull.UP

encoder_dt = digitalio.DigitalInOut(ENCODER_DT_PIN)
encoder_dt.direction = digitalio.Direction.INPUT
encoder_dt.pull = digitalio.Pull.UP

encoder_sw = digitalio.DigitalInOut(ENCODER_SW_PIN)
encoder_sw.direction = digitalio.Direction.INPUT
encoder_sw.pull = digitalio.Pull.UP

encoder_last_clk = encoder_clk.value
encoder_sw_last = True
encoder_sw_last_change = 0

# =============================================================================
# GŁÓWNA PĘTLA
# =============================================================================

print("RP2040 HID Keypad + Mouse aktywny!")
print(f"Klawisze: 9x (Ctrl+Alt+1..Ctrl+Alt+9)")
print(f"Enkoder: scroll góra/dół + middle-click")

while True:
    now = time.monotonic() * 1000  # Czas w ms

    # --- Obsługa 9 klawiszy (Ctrl+Alt+1..Ctrl+Alt+9) ---
    for key in keys:
        current = key['pin'].value  # False = wciśnięty (zwarte do GND)

        if current != key['last_state']:
            if (now - key['last_change']) > DEBOUNCE_MS:
                key['last_change'] = now
                key['last_state'] = current

                if not current:  # Wciśnięcie (falling edge)
                    keyboard.press(Keycode.CONTROL, Keycode.ALT, key['keycode'])
                else:            # Zwolnienie (rising edge)
                    keyboard.release_all()

    # --- Obsługa enkodera obrotowego (scroll myszki) ---
    clk_val = encoder_clk.value
    if clk_val != encoder_last_clk:
        dt_val = encoder_dt.value
        if dt_val != clk_val:
            # Obrót w prawo (CW) → scroll w górę
            mouse.move(wheel=SCROLL_SPEED)
        else:
            # Obrót w lewo (CCW) → scroll w dół
            mouse.move(wheel=-SCROLL_SPEED)
        encoder_last_clk = clk_val

    # --- Obsługa przycisku enkodera (middle-click) ---
    sw_val = encoder_sw.value
    if sw_val != encoder_sw_last:
        if (now - encoder_sw_last_change) > DEBOUNCE_MS:
            encoder_sw_last_change = now
            encoder_sw_last = sw_val

            if not sw_val:  # Wciśnięcie
                mouse.press(Mouse.MIDDLE_BUTTON)
            else:           # Zwolnienie
                mouse.release(Mouse.MIDDLE_BUTTON)

    time.sleep(0.001)  # 1ms — niska latencja pętli
