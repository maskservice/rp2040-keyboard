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

# =============================================================================
# UWAGA: WSZELKIE ZMIANY MAPOWANIA KLAWISZY W TYM PLIKU MUSZĄ BYĆ RÓWNIEŻ
# ZAKTUALIZOWANE W PLIKU: hal/hal_config.toml (sekcje [switches.switch_X])
# =============================================================================
# Mapowanie klawiszy: (pin GPIO, klawisz numeryczny dla Ctrl+Alt+N)
KEY_PINS = [
    (board.GP1, Keycode.NINE),      # Przycisk 1 → Ctrl+Alt+9
    (board.GP2, Keycode.EIGHT),     # Przycisk 2 → Ctrl+Alt+8
    (board.GP3, Keycode.FIVE),      # Przycisk 3 → Ctrl+Alt+5
    (board.GP29, Keycode.ONE),      # Przycisk 4 → Ctrl+Alt+1
    (board.GP4, Keycode.SEVEN),     # Przycisk 5 → Ctrl+Alt+7
    (board.GP5, Keycode.SIX),       # Przycisk 6 → Ctrl+Alt+6
    (board.GP6, Keycode.FOUR),      # Przycisk 7 → Ctrl+Alt+4
    (board.GP7, Keycode.TWO),       # Przycisk 8 → Ctrl+Alt+2
    (board.GP8, Keycode.THREE),     # Przycisk 9 → Ctrl+Alt+3
]


# Enkoder obrotowy
ENCODER_CLK_PIN = board.GP11    # Encoder A (CLK)
ENCODER_DT_PIN = board.GP12   # Encoder B (DT)
ENCODER_SW_PIN = board.GP13   # Encoder push button (SW)

# Parametry scroll
SCROLL_SPEED = 2              # Ilość kroków scrolla na tick enkodera
RELEASE_DEBOUNCE_MS = 100     # Zwolnij przycisk dopiero po 100ms ciągłego braku GND
ENCODER_DEBOUNCE_MS = 10      # Debounce enkodera (zwiększone dla stabilności)

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
        'pressed': False,          # Czy klawisz jest logicznie wciśnięty
        'last_low_time': 0,        # Ostatni czas gdy pin był LOW (GND)
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
encoder_sw_pressed = False
encoder_sw_last_low = 0

# =============================================================================
# GŁÓWNA PĘTLA
# =============================================================================

print("RP2040 HID Keypad + Mouse aktywny!")
print(f"Klawisze: 9x (Ctrl+Alt+1..Ctrl+Alt+9)")
print(f"Enkoder: scroll góra/dół + middle-click")

while True:
    now = time.monotonic() * 1000  # Czas w ms

    # --- Obsługa 9 klawiszy (Ctrl+Alt+1..Ctrl+Alt+9) ---
    # Działa jak zwykła klawiatura:
    #   - GND na pinie = klawisz TRZYMANY (jak palec na klawiszu)
    #   - Brak GND przez 100ms = klawisz ZWOLNIONY
    #   - Krótkie drgania styków są ignorowane (naturalne zjawisko)
    #   - release() zwalnia TYLKO ten konkretny klawisz, nie wszystkie
    for key in keys:
        current = key['pin'].value  # False = wciśnięty (zwarte do GND)

        if not current:  # Pin jest LOW (GND) — styk zwarty
            key['last_low_time'] = now
            if not key['pressed']:
                # Natychmiastowa detekcja wciśnięcia — bez opóźnienia
                key['pressed'] = True
                keyboard.press(Keycode.CONTROL, Keycode.ALT, key['keycode'])
        else:  # Pin jest HIGH — styk otwarty (może być drganie!)
            if key['pressed']:
                # Zwolnij dopiero gdy pin jest HIGH nieprzerwanie przez 100ms
                if (now - key['last_low_time']) > RELEASE_DEBOUNCE_MS:
                    key['pressed'] = False
                    # Zwolnij TYLKO ten klawisz (nie release_all!)
                    keyboard.release(key['keycode'])
                    # Zwolnij modyfikatory tylko gdy ŻADEN przycisk nie jest wciśnięty
                    if not any(k['pressed'] for k in keys):
                        keyboard.release(Keycode.CONTROL, Keycode.ALT)

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
    # Ten sam algorytm: natychmiastowe wciśnięcie + opóźnione zwolnienie
    sw_val = encoder_sw.value
    if not sw_val:  # Pin LOW (GND) — styk zwarty
        encoder_sw_last_low = now
        if not encoder_sw_pressed:
            encoder_sw_pressed = True
            mouse.press(Mouse.MIDDLE_BUTTON)
    else:  # Pin HIGH — styk otwarty
        if encoder_sw_pressed:
            if (now - encoder_sw_last_low) > RELEASE_DEBOUNCE_MS:
                encoder_sw_pressed = False
                mouse.release(Mouse.MIDDLE_BUTTON)

    time.sleep(0.001)  # 1ms — niska latencja pętli
