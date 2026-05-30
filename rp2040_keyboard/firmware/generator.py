"""
Code generator for RP2040-One HID Keypad
=========================================

Generates CircuitPython code based on configuration.
"""

import textwrap
from dataclasses import dataclass, field
from typing import Optional

# Constants
AVAILABLE_GPIOS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
                   16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29]

KEYCODES = {
    "ONE": "Keycode.ONE", "TWO": "Keycode.TWO", "THREE": "Keycode.THREE",
    "FOUR": "Keycode.FOUR", "FIVE": "Keycode.FIVE", "SIX": "Keycode.SIX",
    "SEVEN": "Keycode.SEVEN", "EIGHT": "Keycode.EIGHT", "NINE": "Keycode.NINE",
    "ZERO": "Keycode.ZERO",
    "A": "Keycode.A", "B": "Keycode.B", "C": "Keycode.C", "D": "Keycode.D",
    "E": "Keycode.E", "F": "Keycode.F", "G": "Keycode.G", "H": "Keycode.H",
    "I": "Keycode.I", "J": "Keycode.J", "K": "Keycode.K", "L": "Keycode.L",
    "M": "Keycode.M", "N": "Keycode.N", "O": "Keycode.O", "P": "Keycode.P",
    "Q": "Keycode.Q", "R": "Keycode.R", "S": "Keycode.S", "T": "Keycode.T",
    "U": "Keycode.U", "V": "Keycode.V", "W": "Keycode.W", "X": "Keycode.X",
    "Y": "Keycode.Y", "Z": "Keycode.Z",
    "F1": "Keycode.F1", "F2": "Keycode.F2", "F3": "Keycode.F3", "F4": "Keycode.F4",
    "F5": "Keycode.F5", "F6": "Keycode.F6", "F7": "Keycode.F7", "F8": "Keycode.F8",
    "F9": "Keycode.F9", "F10": "Keycode.F10", "F11": "Keycode.F11", "F12": "Keycode.F12",
    "SPACE": "Keycode.SPACE", "ENTER": "Keycode.ENTER", "ESCAPE": "Keycode.ESCAPE",
    "TAB": "Keycode.TAB", "BACKSPACE": "Keycode.BACKSPACE", "DELETE": "Keycode.DELETE",
    "UP": "Keycode.UP_ARROW", "DOWN": "Keycode.DOWN_ARROW",
    "LEFT": "Keycode.LEFT_ARROW", "RIGHT": "Keycode.RIGHT_ARROW",
    "HOME": "Keycode.HOME", "END": "Keycode.END",
    "PAGE_UP": "Keycode.PAGE_UP", "PAGE_DOWN": "Keycode.PAGE_DOWN",
    "CAPS_LOCK": "Keycode.CAPS_LOCK", "SCROLL_LOCK": "Keycode.SCROLL_LOCK",
    "PAUSE": "Keycode.PAUSE", "INSERT": "Keycode.INSERT",
    "NUM_LOCK": "Keycode.NUM_LOCK",
}

MODIFIERS = {
    "CTRL": "Keycode.CONTROL",
    "ALT": "Keycode.ALT", 
    "SHIFT": "Keycode.SHIFT",
    "GUI": "Keycode.GUI",
}

VALID_MODIFIER_VALUES = set(MODIFIERS.values())

@dataclass
class KeyConfig:
    gpio: int
    keycode: str
    modifier: str = ""
    label: str = ""

@dataclass 
class EncoderConfig:
    clk_gpio: int
    dt_gpio: int
    sw_gpio: int
    scroll_speed: int = 2
    middle_click: bool = True
    debounce_ms: int = 3  # Debouncing time in milliseconds (inspirowane Arduino)

@dataclass
class PadConfig:
    keys: list[KeyConfig] = field(default_factory=list)
    encoder: Optional[EncoderConfig] = None
    
    def to_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PadConfig':
        keys = [KeyConfig(**k) for k in data.get('keys', [])]
        encoder = None
        if data.get('encoder'):
            encoder = EncoderConfig(**data['encoder'])
        return cls(keys=keys, encoder=encoder)


def normalize_modifiers(modifier: str | list[str] | tuple[str, ...] | None) -> list[str]:
    if not modifier:
        return []

    if isinstance(modifier, (list, tuple)):
        raw_modifiers = list(modifier)
    else:
        # Usuń "Keycode." jeśli istnieje, podziel po "+", a następnie dodaj z powrotem
        cleaned = modifier.replace("Keycode.", "")
        raw_modifiers = [f"Keycode.{part.strip()}" for part in cleaned.split("+") if part.strip()]

    # Filtruj tylko prawidłowe modyfikatory
    valid_modifiers = []
    for part in raw_modifiers:
        if part in VALID_MODIFIER_VALUES:
            valid_modifiers.append(part)
        else:
            print(f"⚠️ Nieznany modyfikator: {part}")
    
    return valid_modifiers

def generate_code_py(config: PadConfig) -> str:
    """Generuje plik code.py na podstawie konfiguracji."""
    
    # Sekcja importów - warunkowe
    imports = '''
import board
import digitalio
import time
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode'''
    
    if config.encoder:
        imports += '''
import rotaryio
from adafruit_hid.mouse import Mouse'''
    
    imports += '''

# Inicjalizacja HID (boot.py już włączył urządzenia)
keyboard = Keyboard(usb_hid.devices)
'''
    
    if config.encoder:
        imports += '''mouse = Mouse(usb_hid.devices)
'''
    
    # Konfiguracja pinów przycisków
    key_pins_code = ['''
# =============================================================================
# UWAGA: WSZELKIE ZMIANY MAPOWANIA KLAWISZY (LUB KONFIGURACJI)
# MUSZĄ BYĆ RÓWNIEŻ ZAKTUALIZOWANE W PLIKU: hal/hal_config.toml
# =============================================================================
''']
    for i, key in enumerate(config.keys, 1):
        key_pins_code.append(f'''
# Przycisk {i} -> {key.modifier} + {key.keycode}
key_{i}_pin = digitalio.DigitalInOut(board.GP{key.gpio})
key_{i}_pin.direction = digitalio.Direction.INPUT
key_{i}_pin.pull = digitalio.Pull.UP
''')
    
    # Konfiguracja enkodera
    encoder_code = ""
    if config.encoder:
        encoder_code = f'''
# Enkoder obrotowy
encoder = rotaryio.IncrementalEncoder(board.GP{config.encoder.clk_gpio}, board.GP{config.encoder.dt_gpio})
encoder_button = digitalio.DigitalInOut(board.GP{config.encoder.sw_gpio})
encoder_button.direction = digitalio.Direction.INPUT
encoder_button.pull = digitalio.Pull.UP

ENCODER_DEBOUNCE_MS = {config.encoder.debounce_ms}
SCROLL_SPEED = {config.encoder.scroll_speed}

# Parametry debounce — asymetryczny algorytm
RELEASE_DEBOUNCE_MS = 100  # Zwolnij dopiero po 100ms ciągłego braku GND

# Zmienne do śledzenia stanu enkodera
encoder_last_pos = 0
encoder_last_time = time.monotonic()
encoder_last_count = 0
encoder_btn_pressed = False
encoder_btn_last_low = 0
'''
    
    # Główna pętla
    main_loop = '''
# Główna pętla
'''
    
    if config.keys:
        # Generuj tablice stanu klawiszy
        main_loop += f'''# Stan klawiszy — asymetryczny debounce (natychmiastowe wciśnięcie, opóźnione zwolnienie)
key_pressed = [False] * {len(config.keys)}
key_last_low = [0.0] * {len(config.keys)}
RELEASE_DEBOUNCE_MS = 100  # Zwolnij dopiero po 100ms ciągłego braku GND
'''
        # Generuj tablicę pinów i modyfikatorów
        main_loop += f'''key_pins = [{", ".join(f"key_{i}_pin" for i in range(1, len(config.keys) + 1))}]
'''
        # Generuj tablicę keycodów
        keycodes_list = []
        modifiers_list = []
        for key in config.keys:
            keycodes_list.append(key.keycode)
            mods = normalize_modifiers(key.modifier)
            modifiers_list.append(mods)
        
        main_loop += f'''key_keycodes = [{", ".join(keycodes_list)}]
'''
        # Generuj tablicę modyfikatorów jako listę list
        mod_strs = []
        for mods in modifiers_list:
            mod_strs.append(f"[{', '.join(mods)}]")
        main_loop += f'''key_modifiers = [{", ".join(mod_strs)}]
'''
    
    if config.encoder:
        main_loop += '''encoder_last_pos = encoder.position
'''
    
    main_loop += '''
while True:
    now = time.monotonic() * 1000  # Czas w ms
'''
    
    # Dodaj obsługę przycisków — nowy algorytm
    if config.keys:
        main_loop += f'''
    # Obsługa przycisków — działa jak zwykła klawiatura:
    #   GND na pinie = klawisz TRZYMANY (jak palec na klawiszu)
    #   Brak GND przez 100ms = klawisz ZWOLNIONY
    #   Krótkie drgania styków ignorowane (naturalne zjawisko)
    for i in range({len(config.keys)}):
        current = key_pins[i].value  # False = wciśnięty (zwarte do GND)

        if not current:  # Pin jest LOW (GND) — styk zwarty
            key_last_low[i] = now
            if not key_pressed[i]:
                # Natychmiastowa detekcja wciśnięcia — bez opóźnienia
                key_pressed[i] = True
                keyboard.press(*key_modifiers[i], key_keycodes[i])
        else:  # Pin jest HIGH — styk otwarty (może być drganie!)
            if key_pressed[i]:
                # Zwolnij dopiero gdy pin jest HIGH nieprzerwanie przez 100ms
                if (now - key_last_low[i]) > RELEASE_DEBOUNCE_MS:
                    key_pressed[i] = False
                    # Zwolnij TYLKO ten klawisz
                    keyboard.release(key_keycodes[i])
                    # Zwolnij modyfikatory gdy ŻADEN przycisk nie jest wciśnięty
                    if not any(key_pressed):
                        keyboard.release_all()
'''
    
    # Dodaj obsługę enkodera
    if config.encoder:
        main_loop += '''
    # Obsługa enkodera obrotowego
    current_pos = encoder.position
    current_time = time.monotonic()
    
    if (current_time - encoder_last_time) >= (ENCODER_DEBOUNCE_MS / 1000.0):
        if current_pos != encoder_last_pos:
            steps = current_pos - encoder_last_pos
            
            if abs(steps) <= 10:
                if steps > 0:
                    for _ in range(abs(steps) * SCROLL_SPEED):
                        mouse.move(wheel=1)
                else:
                    for _ in range(abs(steps) * SCROLL_SPEED):
                        mouse.move(wheel=-1)
                
                encoder_last_count += steps
            else:
                encoder.position = encoder_last_pos
            
            encoder_last_pos = current_pos
            encoder_last_time = current_time
    
'''
        
        # Przycisk enkodera — ten sam algorytm asymetryczny
        click_button = "Mouse.MIDDLE_BUTTON" if config.encoder.middle_click else "Mouse.LEFT_BUTTON"
        click_name = "middle click" if config.encoder.middle_click else "left click"
        main_loop += f'''    # Przycisk enkodera ({click_name}) — natychmiastowe wciśnięcie + opóźnione zwolnienie
    if not encoder_button.value:  # Pin LOW (GND) — styk zwarty
        encoder_btn_last_low = now
        if not encoder_btn_pressed:
            encoder_btn_pressed = True
            mouse.press({click_button})
    else:  # Pin HIGH — styk otwarty
        if encoder_btn_pressed:
            if (now - encoder_btn_last_low) > RELEASE_DEBOUNCE_MS:
                encoder_btn_pressed = False
                mouse.release({click_button})

'''
    
    main_loop += '''    time.sleep(0.001)  # 1ms — niska latencja pętli
'''
    
    # Połącz wszystko
    full_code = imports + ''.join(key_pins_code) + encoder_code + main_loop
    
    return textwrap.dedent(full_code).strip()

__all__ = [
    "generate_code_py",
    "PadConfig",
    "KeyConfig", 
    "EncoderConfig",
    "KEYCODES",
    "MODIFIERS",
    "VALID_MODIFIER_VALUES",
    "normalize_modifiers",
    "AVAILABLE_GPIOS",
]
