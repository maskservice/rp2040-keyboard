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

@dataclass
class KeyConfig:
    gpio: int
    keycode: str
    modifier: str = "CTRL"
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
    key_pins_code = []
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
# Enkoder obrotowy - zoptymalizowany debouncing
encoder = rotaryio.IncrementalEncoder(board.GP{config.encoder.clk_gpio}, board.GP{config.encoder.dt_gpio})
encoder_button = digitalio.DigitalInOut(board.GP{config.encoder.sw_gpio})
encoder_button.direction = digitalio.Direction.INPUT
encoder_button.pull = digitalio.Pull.UP

# Ustawienia debouncing inspirowane Arduino
ENCODER_DEBOUNCE_MS = {config.encoder.debounce_ms}
SCROLL_SPEED = {config.encoder.scroll_speed}

# Zmienne do śledzenia stanu
encoder_last_pos = 0
encoder_last_time = time.monotonic()
encoder_last_count = 0
'''
    
    # Główna pętla
    main_loop = '''
# Główna pętla
'''
    
    if config.keys:
        main_loop += f'''last_positions = [None] * {len(config.keys)}
'''
    
    if config.encoder:
        main_loop += '''encoder_button_pressed = None
encoder_last_pos = encoder.position
'''
    
    main_loop += '''
while True:
'''
    
    # Dodaj obsługę przycisków
    if config.keys:
        main_loop += '''    # Obsługa przycisków
'''
        for i, key in enumerate(config.keys, 1):
            main_loop += f'''
    if not key_{i}_pin.value and last_positions[{i-1}] is None:
        keyboard.press({key.modifier}, {key.keycode})
        time.sleep(0.1)  # Debounce
        keyboard.release({key.modifier}, {key.keycode})
        last_positions[{i-1}] = False
    elif key_{i}_pin.value and last_positions[{i-1}] is False:
        last_positions[{i-1}] = None
'''
    
    # Dodaj obsługę enkodera
    if config.encoder:
        main_loop += '''
    # Obsługa enkodera - zoptymalizowana pętla inspirowana Arduino
    current_pos = encoder.position
    current_time = time.monotonic()
    
    # Debouncing - sprawdzaj tylko jeśli minął wystarczający czas
    if (current_time - encoder_last_time) >= (ENCODER_DEBOUNCE_MS / 1000.0):
        if current_pos != encoder_last_pos:
            # Wykryj kierunek i kroki (jak w Arduino)
            steps = current_pos - encoder_last_pos
            
            # Ogranicz maksymalne kroki dla uniknięcia "skakania"
            if abs(steps) <= 10:
                if steps > 0:
                    # Obrót w prawo (CW) - scroll w górę
                    for _ in range(abs(steps) * SCROLL_SPEED):
                        mouse.move(wheel=1)
                else:
                    # Obrót w lewo (CCW) - scroll w dół  
                    for _ in range(abs(steps) * SCROLL_SPEED):
                        mouse.move(wheel=-1)
                
                encoder_last_count += steps
            else:
                # Zbyt duża zmiana - zresetuj pozycję
                encoder.position = encoder_last_pos
            
            encoder_last_pos = current_pos
            encoder_last_time = current_time
    
'''
        
        if config.encoder.middle_click:
            main_loop += '''    # Przycisk enkodera - debouncing (middle click)
    if not encoder_button.value and encoder_button_pressed is None:
        mouse.click(Mouse.MIDDLE_BUTTON)
        encoder_button_pressed = False
        time.sleep(0.01)  # Krótki debounce dla przycisku
    elif encoder_button.value and encoder_button_pressed is False:
        encoder_button_pressed = None

'''
        else:
            main_loop += '''    # Przycisk enkodera - debouncing (left click)
    if not encoder_button.value and encoder_button_pressed is None:
        mouse.click(Mouse.LEFT_BUTTON)
        encoder_button_pressed = False
        time.sleep(0.01)  # Krótki debounce dla przycisku
    elif encoder_button.value and encoder_button_pressed is False:
        encoder_button_pressed = None

'''
    
    main_loop += '''    time.sleep(0.01)  # Małe opóźnienie
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
    "AVAILABLE_GPIOS",
]
