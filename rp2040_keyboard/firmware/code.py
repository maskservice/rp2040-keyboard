"""
RP2040-Zero HID Keypad + Encoder Mouse (panel9 PCB)
===================================================
9 klawiszy (Ctrl+Alt+1..Ctrl+Alt+9) + enkoder obrotowy (scroll myszki + middle-click)

Hardware (zgodny z maskservice/viewer/artifacts/pcb/panel9.kicad_pcb):
  - Waveshare RP2040-Zero (lub kompatybilny RP2040-One)
  - 9x switch buttons → GP14, GP6, GP7, GP8, GP5, GP1, GP4, GP3, GP2
  - 1x rotary encoder z przyciskiem (J1 RJ45) → GP0 (ENC_A/CLK), GP15 (ENC_B/DT), GP26 (ENC_SW)

Firmware: CircuitPython 9.x/10.x + adafruit_hid

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
# KONFIGURACJA PINÓW (panel9.kicad_pcb)
# =============================================================================

# =============================================================================
# UWAGA: WSZELKIE ZMIANY MAPOWANIA KLAWISZY W TYM PLIKU MUSZĄ BYĆ RÓWNIEŻ
# ZAKTUALIZOWANE W PLIKU: hal/hal_config.toml (sekcje [switches.switch_X])
# =============================================================================
# Mapowanie klawiszy: (pin GPIO, klawisz numeryczny dla Ctrl+Alt+N)
KEY_PINS = [
    (board.GP14, Keycode.SIX),      # Przycisk 1 (SW1: X=118, Y=74.5)  → Ctrl+Alt+6 (Głowa +)
    (board.GP6, Keycode.TWO),       # Przycisk 2 (SW2: X=148, Y=74.5)  → Ctrl+Alt+2 (LP +5)
    (board.GP7, Keycode.THREE),     # Przycisk 3 (SW3: X=198, Y=74.5)  → Ctrl+Alt+3 (LP +10)
    (board.GP8, Keycode.FOUR),      # Przycisk 4 (SW4: X=228, Y=74.5)  → Ctrl+Alt+4 (AL START)
    (board.GP5, Keycode.FIVE),      # Przycisk 5 (SW5: X=173, Y=92.0)  → Ctrl+Alt+5 (LP Upust)
    (board.GP1, Keycode.ONE),       # Przycisk 6 (SW6: X=118, Y=109.5) → Ctrl+Alt+1 (Głowa -)
    (board.GP4, Keycode.SEVEN),     # Przycisk 7 (SW7: X=148, Y=109.5) → Ctrl+Alt+7 (LP -5)
    (board.GP3, Keycode.EIGHT),     # Przycisk 8 (SW8: X=198, Y=109.5) → Ctrl+Alt+8 (LP -10)
    (board.GP2, Keycode.NINE),      # Przycisk 9 (SW9: X=228, Y=109.5) → Ctrl+Alt+9 (AL STOP)
]


# Enkoder obrotowy (J1 RJ45: pin 6=ENC_A, pin 4=ENC_B, pin 2=ENC_SW)
ENCODER_CLK_PIN = board.GP0    # Encoder A (CLK)
ENCODER_DT_PIN = board.GP15    # Encoder B (DT)
ENCODER_SW_PIN = board.GP26    # Encoder push button (SW)

# Parametry scroll i debounce
SCROLL_SPEED = 2              # Ilość kroków scrolla na tick enkodera
RELEASE_DEBOUNCE_MS = 20      # Zwolnij przycisk dopiero po 20ms ciągłego braku GND
ENCODER_DEBOUNCE_MS = 5       # Minimalny odstęp raportu enkodera (ms)
ENCODER_IDLE_RESET_MS = 150   # Reset niepełnego kroku po powrocie do spoczynku (11)

# Tabela przejść Gray-code 4-stanowego dekodera kwadraturowego ((prev << 2) | curr)
_QUAD_TABLE = (
    0, -1, 1, 0,
    1, 0, 0, -1,
    -1, 0, 0, 1,
    0, 1, -1, 0,
)

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

# Uwaga: rotaryio.IncrementalEncoder na RP2040 wymaga sąsiednich pinów (|A-B|==1).
# Dla panel9 (GP0, GP15) zgłasza ValueError — przechodzimy na dekoder digitalio.
try:
    import rotaryio

    encoder = rotaryio.IncrementalEncoder(ENCODER_CLK_PIN, ENCODER_DT_PIN)
    encoder_last_pos = encoder.position
except (ImportError, ValueError, RuntimeError):
    encoder = None
    encoder_clk = digitalio.DigitalInOut(ENCODER_CLK_PIN)
    encoder_clk.direction = digitalio.Direction.INPUT
    encoder_clk.pull = digitalio.Pull.UP

    encoder_dt = digitalio.DigitalInOut(ENCODER_DT_PIN)
    encoder_dt.direction = digitalio.Direction.INPUT
    encoder_dt.pull = digitalio.Pull.UP

    encoder_state = (int(encoder_clk.value) << 1) | int(encoder_dt.value)
    encoder_accum = 0
    encoder_last_change_time = 0.0

encoder_sw = digitalio.DigitalInOut(ENCODER_SW_PIN)
encoder_sw.direction = digitalio.Direction.INPUT
encoder_sw.pull = digitalio.Pull.UP

encoder_last_time = 0.0
encoder_sw_pressed = False
encoder_sw_last_low = 0

# =============================================================================
# GŁÓWNA PĘTLA
# =============================================================================

print("RP2040 HID Keypad + Mouse aktywny!")
print("Klawisze: 9x (Ctrl+Alt+1..Ctrl+Alt+9)")
print("Enkoder: scroll góra/dół + middle-click")

while True:
    now = time.monotonic() * 1000  # Czas w ms

    # --- Obsługa 9 klawiszy (Ctrl+Alt+1..Ctrl+Alt+9) ---
    # Działa jak zwykła klawiatura:
    #   - GND na pinie = klawisz TRZYMANY (jak palec na klawiszu)
    #   - Brak GND przez 20ms = klawisz ZWOLNIONY
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
                # Zwolnij dopiero gdy pin jest HIGH nieprzerwanie przez 20ms
                if (now - key['last_low_time']) > RELEASE_DEBOUNCE_MS:
                    key['pressed'] = False
                    # Zwolnij TYLKO ten klawisz (nie release_all!)
                    keyboard.release(key['keycode'])
                    # Zwolnij modyfikatory tylko gdy ŻADEN przycisk nie jest wciśnięty
                    if not any(k['pressed'] for k in keys):
                        keyboard.release(Keycode.CONTROL, Keycode.ALT)

    # --- Obsługa enkodera obrotowego (scroll myszki) ---
    if encoder is not None:
        if (now - encoder_last_time) >= ENCODER_DEBOUNCE_MS:
            current_pos = encoder.position
            if current_pos != encoder_last_pos:
                steps = current_pos - encoder_last_pos
                if abs(steps) <= 32:
                    wheel_delta = max(-127, min(127, steps * SCROLL_SPEED))
                    if wheel_delta:
                        mouse.move(wheel=wheel_delta)
                encoder_last_pos = current_pos
                encoder_last_time = now
    else:
        curr_state = (int(encoder_clk.value) << 1) | int(encoder_dt.value)
        if curr_state != encoder_state:
            encoder_accum += _QUAD_TABLE[(encoder_state << 2) | curr_state]
            encoder_state = curr_state
            encoder_last_change_time = now
        elif (
            curr_state == 3
            and encoder_accum
            and (now - encoder_last_change_time) > ENCODER_IDLE_RESET_MS
        ):
            encoder_accum = 0

        if abs(encoder_accum) >= 4 and (now - encoder_last_time) >= ENCODER_DEBOUNCE_MS:
            steps = encoder_accum // 4 if encoder_accum > 0 else -((-encoder_accum) // 4)
            encoder_accum -= steps * 4
            wheel_delta = max(-127, min(127, steps * SCROLL_SPEED))
            if wheel_delta:
                mouse.move(wheel=wheel_delta)
            encoder_last_time = now

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

    time.sleep(0.0005)  # 0.5ms — niezawodne próbkowanie enkodera i niska latencja
