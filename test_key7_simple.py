#!/usr/bin/env python3
"""
Prosty test firmware dla RP2040-Zero - identyczny jak oryginalny code.py
ale z debugowaniem dla przycisku 7 (Ctrl+Alt+7)
"""

import time
import board
import digitalio
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.mouse import Mouse

# =============================================================================
# KONFIGURACJA PINÓW (identyczna jak w oryginalnym code.py)
# =============================================================================

# Mapowanie klawiszy: (pin GPIO, klawisz numeryczny dla Ctrl+Alt+N)
KEY_PINS = [
    (board.GP1, Keycode.ONE),       # Przycisk 1 → Ctrl+Alt+1
    (board.GP2, Keycode.TWO),       # Przycisk 2 → Ctrl+Alt+2
    (board.GP3, Keycode.THREE),     # Przycisk 3 → Ctrl+Alt+3
    (board.GP4, Keycode.FOUR),      # Przycisk 4 → Ctrl+Alt+4
    (board.GP5, Keycode.FIVE),      # Przycisk 5 → Ctrl+Alt+5
    (board.GP6, Keycode.SIX),       # Przycisk 6 → Ctrl+Alt+6
    (board.GP7, Keycode.SEVEN),     # Przycisk 7 → Ctrl+Alt+7  <- PROBLEM
    (board.GP8, Keycode.EIGHT),     # Przycisk 8 → Ctrl+Alt+8
    (board.GP9, Keycode.NINE),      # Przycisk 9 → Ctrl+Alt+9
]

# Enkoder obrotowy
ENCODER_CLK_PIN = board.GP11    # Encoder A (CLK)
ENCODER_DT_PIN = board.GP12   # Encoder B (DT)
ENCODER_SW_PIN = board.GP13   # Encoder push button (SW)

# Parametry (identyczne jak w oryginale)
SCROLL_SPEED = 2
DEBOUNCE_MS = 20
ENCODER_DEBOUNCE_MS = 5

# =============================================================================
# INICJALIZACJA HID
# =============================================================================

keyboard = Keyboard(usb_hid.devices)
mouse = Mouse(usb_hid.devices)

# =============================================================================
# INICJALIZACJA PINÓW KLAWISZY (identyczna)
# =============================================================================

keys = []
for pin, keycode in KEY_PINS:
    dio = digitalio.DigitalInOut(pin)
    dio.direction = digitalio.Direction.INPUT
    dio.pull = digitalio.Pull.UP
    keys.append({
        'pin': dio,
        'keycode': keycode,
        'last_state': True,
        'last_change': 0,
    })

# =============================================================================
# INICJALIZACJA ENKODERA (identyczna)
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
# GŁÓWNA PĘTLA (identyczna z dodanym debugiem)
# =============================================================================

print("RP2040 HID Keypad + Mouse - DEBUG VERSION")
print(f"Klawisze: 9x (Ctrl+Alt+1..Ctrl+Alt+9)")
print(f"Enkoder: scroll góra/dół + middle-click")
print("SZCZEGÓŁOWY DEBUG DLA PRZYCISKU 7 (Ctrl+Alt+7)")

while True:
    now = time.monotonic() * 1000

    # --- Obsługa 9 klawiszy (Ctrl+Alt+1..Ctrl+Alt+9) ---
    for i, key in enumerate(keys):
        current = key['pin'].value  # False = wciśnięty (zwarte do GND)

        if current != key['last_state']:
            if (now - key['last_change']) > DEBOUNCE_MS:
                key['last_change'] = now
                key['last_state'] = current

                # Specjalny debug dla przycisku 7 (Ctrl+Alt+7)
                if i == 6:  # Indeks 6 to 7. klawisz
                    print(f"\n=== DEBUG PRZYCISK 7 (GP7) ===")
                    print(f"Czas: {now}ms")
                    print(f"Stan pinu: {current} (False=wciśnięty)")
                    print(f"Keycode: {key['keycode']}")
                    print(f"Oczekiwane: Ctrl+Alt+7")
                    
                    if not current:  # Wciśnięcie (falling edge)
                        print("→ WCIŚNIĘCIE: wysyłanie Ctrl+Alt+7")
                        keyboard.press(Keycode.CONTROL, Keycode.ALT, key['keycode'])
                        print("→ ZWOLNIENIE: release_all()")
                        keyboard.release_all()
                        print("→ Zakończono")
                    else:
                        print("→ Zwolnienie przycisku (brak akcji)")
                else:
                    # Standardowa obsługa dla pozostałych klawiszy
                    if not current:  # Wciśnięcie (falling edge)
                        keyboard.press(Keycode.CONTROL, Keycode.ALT, key['keycode'])
                    else:            # Zwolnienie (rising edge)
                        keyboard.release_all()

    # --- Obsługa enkodera obrotowego (scroll myszki) ---
    clk_val = encoder_clk.value
    if clk_val != encoder_last_clk:
        dt_val = encoder_dt.value
        if dt_val != clk_val:
            mouse.move(wheel=SCROLL_SPEED)
        else:
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

    time.sleep(0.001)
