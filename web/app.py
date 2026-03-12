"""
RP2040-One HID Keypad — Web Configurator
==========================================
FastAPI backend: visual pin editor, code generator, wiring guide, flash instructions.

Uruchom:  make web        (lub:  uvicorn web.app:app --port 8080)
Dev:      make dev        (auto-reload)
Docker:   make docker-run
"""

from __future__ import annotations

import json
import os
import textwrap
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

# ============================================================================
# STAŁE
# ============================================================================

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

BOOT_PY = '''
import usb_hid
import time
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.mouse import Mouse

# Enable USB HID devices
time.sleep(1)  # Wait for USB enumeration
keyboard = Keyboard(usb_hid.devices)
mouse = Mouse(usb_hid.devices)
'''

# ============================================================================
# MODELE DANYCH
# ============================================================================

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

@dataclass
class PadConfig:
    keys: list[KeyConfig] = field(default_factory=list)
    encoder: Optional[EncoderConfig] = None
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PadConfig':
        keys = [KeyConfig(**k) for k in data.get('keys', [])]
        encoder = None
        if data.get('encoder'):
            encoder = EncoderConfig(**data['encoder'])
        return cls(keys=keys, encoder=encoder)

# ============================================================================
# WALIDACJA
# ============================================================================

def validate_config(config: PadConfig) -> tuple[bool, list[str]]:
    """Waliduje konfigurację pod kątem konfliktów GPIO i poprawności parametrów."""
    errors = []
    used_gpios = set()
    
    # Sprawdź przyciski
    for key in config.keys:
        if key.gpio not in AVAILABLE_GPIOS:
            errors.append(f"GPIO {key.gpio} nie jest dostępne")
        elif key.gpio in used_gpios:
            errors.append(f"GPIO {key.gpio} używane wielokrotnie")
        else:
            used_gpios.add(key.gpio)
            
        if key.keycode not in KEYCODES.values():
            errors.append(f"Nieznany keycode: {key.keycode}")
            
        if key.modifier not in MODIFIERS.values():
            errors.append(f"Nieznany modifier: {key.modifier}")
    
    # Sprawdź enkoder
    if config.encoder:
        enc_gpios = [config.encoder.clk_gpio, config.encoder.dt_gpio, config.encoder.sw_gpio]
        for gpio in enc_gpios:
            if gpio not in AVAILABLE_GPIOS:
                errors.append(f"GPIO {gpio} enkodera nie jest dostępne")
            elif gpio in used_gpios:
                errors.append(f"GPIO {gpio} enkodera koliduje z innym pinem")
            else:
                used_gpios.add(gpio)
                
        if config.encoder.clk_gpio == config.encoder.dt_gpio:
            errors.append("CLK i DT enkodera nie mogą być tym samym pinem")
            
        if not (1 <= config.encoder.scroll_speed <= 10):
            errors.append("Scroll speed musi być między 1 a 10")
    
    return len(errors) == 0, errors

# ============================================================================
# GENERATOR KODU
# ============================================================================

def generate_code_py(config: PadConfig) -> str:
    """Generuje plik code.py na podstawie konfiguracji."""
    
    # Sekcja importów i definicji
    imports = '''
import board
import digitalio
import rotaryio
import time
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.mouse import Mouse

# Inicjalizacja HID (boot.py już włączył urządzenia)
keyboard = Keyboard()
mouse = Mouse()
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
# Enkoder obrotowy
encoder = rotaryio.IncrementalEncoder(board.GP{config.encoder.clk_gpio}, board.GP{config.encoder.dt_gpio})
encoder_button = digitalio.DigitalInOut(board.GP{config.encoder.sw_gpio})
encoder_button.direction = digitalio.Direction.INPUT
encoder_button.pull = digitalio.Pull.UP

encoder_last_pos = 0
SCROLL_SPEED = {config.encoder.scroll_speed}
'''
    
    # Główna pętla
    main_loop = '''
# Główna pętla
last_positions = [None] * len(key_pins)
encoder_last_pos = encoder.position if 'encoder' in locals() else 0

while True:
    # Obsługa przycisków
'''
    
    # Dodaj obsługę każdego przycisku
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
    # Obsługa enkodera
    current_pos = encoder.position
    if current_pos != encoder_last_pos:
        steps = current_pos - encoder_last_pos
        if steps > 0:
            for _ in range(abs(steps) * SCROLL_SPEED):
                mouse.move(wheel=1)
        else:
            for _ in range(abs(steps) * SCROLL_SPEED):
                mouse.move(wheel=-1)
        encoder_last_pos = current_pos
    
    # Przycisk enkodera
'''
        if config.encoder.middle_click:
            main_loop += '''
    if not encoder_button.value and encoder_button_pressed is None:
        mouse.click(Mouse.MIDDLE_BUTTON)
        time.sleep(0.1)
        encoder_button_pressed = False
    elif encoder_button.value and encoder_button_pressed is False:
        encoder_button_pressed = None
'''
    
    main_loop += '''
    time.sleep(0.01)  # Maże opóźnienie
'''
    
    # Połącz wszystko
    full_code = imports + ''.join(key_pins_code) + encoder_code + main_loop
    
    return textwrap.dedent(full_code).strip()

# ============================================================================
# APLIKACJA FASTAPI
# ============================================================================

app = FastAPI(
    title="RP2040-One Keypad Configurator",
    description="Visual pin editor and code generator for RP2040-One HID keypad",
    version="1.0.0"
)

# ============================================================================
# ENDPOINTY API
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Główna strona z edytorem wizualnym."""
    return HTML_RESPONSE

@app.get("/api/keycodes")
async def get_keycodes():
    """Zwraca dostępne kody klawiszy."""
    return {
        "keycodes": {k: v for k, v in KEYCODES.items()},
        "modifiers": MODIFIERS,
        "available_gpios": AVAILABLE_GPIOS
    }

@app.post("/api/validate")
async def validate_config_endpoint(config: dict):
    """Waliduje konfigurację."""
    try:
        pad_config = PadConfig.from_dict(config)
        is_valid, errors = validate_config(pad_config)
        return {"valid": is_valid, "errors": errors}
    except Exception as e:
        return {"valid": False, "errors": [str(e)]}

@app.post("/api/generate")
async def generate_code_endpoint(config: dict):
    """Generuje kod CircuitPython."""
    try:
        pad_config = PadConfig.from_dict(config)
        is_valid, errors = validate_config(pad_config)
        
        if not is_valid:
            return {"valid": False, "errors": errors, "code": None}
            
        code_py = generate_code_py(pad_config)
        return {
            "valid": True, 
            "errors": [], 
            "code": code_py,
            "boot": BOOT_PY.strip()
        }
    except Exception as e:
        return {"valid": False, "errors": [str(e)], "code": None}

@app.get("/api/default")
async def get_default_config():
    """Zwraca domyślną konfigurację."""
    default_keys = [
        KeyConfig(gpio=1, keycode="Keycode.ONE", modifier="Keycode.CONTROL", label="Ctrl+1"),
        KeyConfig(gpio=2, keycode="Keycode.TWO", modifier="Keycode.CONTROL", label="Ctrl+2"),
        KeyConfig(gpio=3, keycode="Keycode.THREE", modifier="Keycode.CONTROL", label="Ctrl+3"),
        KeyConfig(gpio=4, keycode="Keycode.FOUR", modifier="Keycode.CONTROL", label="Ctrl+4"),
        KeyConfig(gpio=5, keycode="Keycode.FIVE", modifier="Keycode.CONTROL", label="Ctrl+5"),
        KeyConfig(gpio=6, keycode="Keycode.SIX", modifier="Keycode.CONTROL", label="Ctrl+6"),
        KeyConfig(gpio=7, keycode="Keycode.SEVEN", modifier="Keycode.CONTROL", label="Ctrl+7"),
        KeyConfig(gpio=8, keycode="Keycode.EIGHT", modifier="Keycode.CONTROL", label="Ctrl+8"),
        KeyConfig(gpio=29, keycode="Keycode.NINE", modifier="Keycode.CONTROL", label="Ctrl+9"),
    ]
    
    default_encoder = EncoderConfig(
        clk_gpio=9,
        dt_gpio=10, 
        sw_gpio=11,
        scroll_speed=2,
        middle_click=True
    )
    
    config = PadConfig(keys=default_keys, encoder=default_encoder)
    return config.to_dict()

# ============================================================================
# FRONTEND (HTML + JS)
# ============================================================================

HTML_RESPONSE = '''
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RP2040-One Keypad Configurator</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { color: #333; margin-bottom: 10px; }
        .tabs { display: flex; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .tab { flex: 1; padding: 15px; background: #f8f9fa; border: none; cursor: pointer; transition: all 0.3s; }
        .tab.active { background: #007bff; color: white; }
        .tab-content { display: none; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .tab-content.active { display: block; }
        .pin-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(80px, 1fr)); gap: 10px; margin: 20px 0; }
        .pin { aspect-ratio: 1; border: 2px solid #ddd; border-radius: 8px; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.3s; font-weight: bold; }
        .pin.used { background: #007bff; color: white; border-color: #007bff; }
        .pin.free { background: white; }
        .pin:hover { transform: scale(1.05); }
        .config-section { margin: 20px 0; }
        .key-item { background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 10px; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: 500; }
        .form-group select, .form-group input { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
        .btn { padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; transition: all 0.3s; }
        .btn-primary { background: #007bff; color: white; }
        .btn-success { background: #28a745; color: white; }
        .btn:hover { transform: translateY(-2px); }
        .code-output { background: #1e1e1e; color: #d4d4d4; padding: 20px; border-radius: 8px; font-family: 'Courier New', monospace; white-space: pre-wrap; max-height: 400px; overflow-y: auto; }
        .error { color: #dc3545; background: #f8d7da; padding: 10px; border-radius: 4px; margin-bottom: 10px; }
        .success { color: #155724; background: #d4edda; padding: 10px; border-radius: 4px; margin-bottom: 10px; }
        .wiring-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        .wiring-table th, .wiring-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        .wiring-table th { background: #f8f9fa; }

        /* ── TEST PAGE ── */
        .test-hint { text-align:center; padding:12px 16px; font-size:14px; color:#666; background:#e8f4f8; border-radius:8px; margin-bottom:20px; border:1px solid #b8daff; }
        .test-hint kbd { background:#fff; padding:2px 8px; border-radius:3px; font-family:monospace; font-size:13px; border:1px solid #ccc; box-shadow:0 1px 2px rgba(0,0,0,.1); }
        .test-stats { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-bottom:20px; }
        .stat-card { background:#fff; border:1px solid #ddd; border-radius:8px; padding:16px; text-align:center; box-shadow:0 2px 6px rgba(0,0,0,.05); }
        .stat-card .val { font-size:28px; font-weight:800; font-family:monospace; color:#007bff; }
        .stat-card .lbl { font-size:11px; color:#888; text-transform:uppercase; letter-spacing:.06em; margin-top:4px; }
        .stat-card.enc-stat .val { color:#17a2b8; }
        .stat-card.total-stat .val { color:#ffc107; }
        .test-grid-layout { display:grid; grid-template-columns:1fr 1fr; gap:20px; }
        @media(max-width:768px) { .test-grid-layout { grid-template-columns:1fr; } }
        .test-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; max-width:360px; margin:0 auto; }
        .test-btn { aspect-ratio:1; border:2px solid #ddd; border-radius:12px; background:#f8f9fa; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:4px; transition:.15s; cursor:default; user-select:none; }
        .test-btn .combo { font-size:11px; color:#888; font-weight:600; }
        .test-btn .num { font-size:32px; font-weight:800; color:#333; }
        .test-btn .label { font-size:10px; color:#aaa; }
        .test-btn.active { border-color:#28a745; background:#d4edda; transform:scale(.95); box-shadow:0 0 16px rgba(40,167,69,.3); }
        .test-btn.active .num { color:#28a745; }
        .test-btn.active .combo { color:#28a745; }
        .encoder-vis { display:flex; align-items:center; justify-content:center; gap:24px; padding:20px; }
        .enc-wheel { width:100px; height:100px; border-radius:50%; border:3px solid #ddd; position:relative; display:flex; align-items:center; justify-content:center; background:conic-gradient(from 0deg,#f0f0f0 0%,#ddd 25%,#f0f0f0 50%,#ddd 75%,#f0f0f0 100%); transition:transform .15s ease-out, border-color .2s, box-shadow .2s; }
        .enc-wheel .knob { width:12px; height:12px; border-radius:50%; background:#999; position:absolute; top:6px; }
        .enc-wheel.scroll-up { border-color:#28a745; box-shadow:0 0 12px rgba(40,167,69,.3); }
        .enc-wheel.scroll-down { border-color:#17a2b8; box-shadow:0 0 12px rgba(23,162,184,.3); }
        .enc-wheel.btn-press { border-color:#ffc107; box-shadow:0 0 12px rgba(255,193,7,.3); transform:scale(.92) !important; }
        .enc-info { text-align:left; }
        .enc-info .dir { font-size:22px; font-weight:800; font-family:monospace; min-height:30px; }
        .enc-info .dir.up { color:#28a745; }
        .enc-info .dir.down { color:#17a2b8; }
        .enc-info .clicks { font-size:13px; color:#888; font-family:monospace; }
        .enc-info .delta { font-size:12px; color:#aaa; margin-top:4px; }
        .event-log { background:#1e1e1e; border-radius:8px; padding:12px; max-height:400px; overflow-y:auto; font-family:'Courier New',monospace; font-size:12px; line-height:1.7; color:#d4d4d4; }
        .event-log::-webkit-scrollbar { width:4px; }
        .event-log::-webkit-scrollbar-thumb { background:#555; border-radius:2px; }
        .event-log .ev { padding:3px 8px; border-radius:4px; margin-bottom:3px; display:flex; align-items:center; gap:8px; }
        .event-log .ev.key-ev { background:rgba(40,167,69,.1); border-left:2px solid #28a745; }
        .event-log .ev.enc-ev { background:rgba(23,162,184,.1); border-left:2px solid #17a2b8; }
        .event-log .ev.btn-ev { background:rgba(255,193,7,.1); border-left:2px solid #ffc107; }
        .event-log .ts { color:#888; min-width:85px; font-size:11px; }
        .event-log .msg { color:#d4d4d4; }
        .log-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:10px; }
        .log-header h3 { margin:0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎹 RP2040-One Keypad Configurator</h1>
            <p>Wizualny edytor pinów i generator kodu CircuitPython</p>
        </div>

        <div class="tabs">
            <button class="tab active" onclick="showTab('editor')">📍 Edytor Pinów</button>
            <button class="tab" onclick="showTab('wiring')">🔌 Schemat Podłączeń</button>
            <button class="tab" onclick="showTab('code')">👨‍💻 Kod</button>
            <button class="tab" onclick="showTab('flash')">💾 Flashowanie</button>
            <button class="tab" onclick="showTab('test')">🎮 Test</button>
        </div>

        <div id="editor" class="tab-content active">
            <h2>Edytor Pinów</h2>
            <div class="pin-grid" id="pinGrid"></div>
            
            <div class="config-section">
                <h3>Przyciski</h3>
                <div id="keysList"></div>
                <button class="btn btn-primary" onclick="addKey()">+ Dodaj przycisk</button>
            </div>

            <div class="config-section">
                <h3>Enkoder Obrotowy</h3>
                <div id="encoderConfig"></div>
            </div>

            <div id="messages"></div>
            <button class="btn btn-success" onclick="generateCode()">🚀 Generuj Kod</button>
        </div>

        <div id="wiring" class="tab-content">
            <h2>Schemat Podłączeń</h2>
            <table class="wiring-table" id="wiringTable">
                <thead>
                    <tr><th>Element</th><th>Pin RP2040</th><th>Pin Elementu</th><th>Funkcja</th></tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>

        <div id="code" class="tab-content">
            <h2>Wygenerowany Kod</h2>
            <div class="form-group">
                <button class="btn btn-primary" onclick="copyCode()">📋 Kopiuj code.py</button>
                <button class="btn btn-primary" onclick="copyBoot()">📋 Kopiuj boot.py</button>
                <button class="btn btn-success" onclick="downloadCode()">⬇️ Pobierz pliki</button>
            </div>
            <div class="code-output" id="codeOutput">Wygeneruj kod aby zobaczyć rezultat...</div>
        </div>

        <div id="flash" class="tab-content">
            <h2>Instrukcja Flashowania</h2>
            <ol>
                <li><strong>Pobierz CircuitPython UF2:</strong> <a href="https://circuitpython.org/board/waveshare_rp2040_one/" target="_blank">circuitpython.org/board/waveshare_rp2040_one</a></li>
                <li><strong>Wgraj firmware:</strong> Przytrzymaj BOOT, podłącz USB, skopiuj UF2 na RPI-RP2</li>
                <li><strong>Instaluj bibliotekę HID:</strong> Skopiuj adafruit_hid/ do CIRCUITPY/lib/</li>
                <li><strong>Skopiuj boot.py:</strong> Do głównego katalogu CIRCUITPY</li>
                <li><strong>Skopiuj code.py:</strong> Do głównego katalogu CIRCUITPY</li>
                <li><strong>Odłącz i podłącz USB:</strong> Urządzenie powinno działać jako klawiatura + mysz</li>
            </ol>
        </div>

        <div id="test" class="tab-content">
            <h2>🎮 Test klawiatury RP2040</h2>
            <div class="test-hint">
                Naciśnij <kbd>Ctrl</kbd> + <kbd>1</kbd>…<kbd>9</kbd> aby przetestować klawisze &nbsp;|&nbsp; Obróć kółkiem myszy aby przetestować enkoder &nbsp;|&nbsp; Środkowy klik = przycisk enkodera
            </div>

            <div class="test-stats">
                <div class="stat-card">
                    <div class="val" id="statKeys">0</div>
                    <div class="lbl">Klawisze</div>
                </div>
                <div class="stat-card enc-stat">
                    <div class="val" id="statScroll">0</div>
                    <div class="lbl">Scroll ticks</div>
                </div>
                <div class="stat-card total-stat">
                    <div class="val" id="statTotal">0</div>
                    <div class="lbl">Łącznie</div>
                </div>
            </div>

            <div class="test-grid-layout">
                <div>
                    <h3 style="margin-bottom:12px">Klawisze Ctrl+1…9</h3>
                    <div class="test-grid" id="testGrid"></div>

                    <h3 style="margin:20px 0 12px">Enkoder (Scroll / Middle-click)</h3>
                    <div style="background:#fff;border:1px solid #ddd;border-radius:8px;box-shadow:0 2px 6px rgba(0,0,0,.05)">
                        <div class="encoder-vis">
                            <div class="enc-wheel" id="encWheel">
                                <div class="knob"></div>
                            </div>
                            <div class="enc-info">
                                <div class="dir" id="encDir">—</div>
                                <div class="clicks">Scroll: <span id="encCount">0</span> ticks</div>
                                <div class="delta">Ostatni: <span id="encDelta">—</span></div>
                            </div>
                        </div>
                    </div>
                </div>

                <div>
                    <div class="log-header">
                        <h3>Event Log</h3>
                        <button class="btn" onclick="clearTestLog()" style="font-size:12px;padding:4px 12px">Wyczyść</button>
                    </div>
                    <div class="event-log" id="eventLog">
                        <div class="ev" style="color:#888;border:none">Oczekiwanie na zdarzenia...</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let config = {
            keys: [],
            encoder: null
        };
        let keycodes = {};
        let availableGpios = [];

        async function init() {
            const response = await fetch('/api/default');
            config = await response.json();
            
            const keycodesResponse = await fetch('/api/keycodes');
            const data = await keycodesResponse.json();
            keycodes = data.keycodes;
            availableGpios = data.available_gpios;
            
            renderPinGrid();
            renderKeys();
            renderEncoder();
            updateWiringTable();
        }

        function showTab(tabName) {
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            
            event.target.classList.add('active');
            document.getElementById(tabName).classList.add('active');
        }

        function renderPinGrid() {
            const grid = document.getElementById('pinGrid');
            grid.innerHTML = '';
            
            const usedPins = new Set();
            config.keys.forEach(key => usedPins.add(key.gpio));
            if (config.encoder) {
                usedPins.add(config.encoder.clk_gpio);
                usedPins.add(config.encoder.dt_gpio);
                usedPins.add(config.encoder.sw_gpio);
            }
            
            for (let gpio of availableGpios) {
                const pin = document.createElement('div');
                pin.className = `pin ${usedPins.has(gpio) ? 'used' : 'free'}`;
                pin.textContent = `GP${gpio}`;
                pin.onclick = () => selectPin(gpio);
                grid.appendChild(pin);
            }
        }

        function selectPin(gpio) {
            // Znajdź pierwszy nieużywany slot
            if (config.keys.length < 9) {
                config.keys.push({
                    gpio: gpio,
                    keycode: 'Keycode.ONE',
                    modifier: 'Keycode.CONTROL',
                    label: `Key ${config.keys.length + 1}`
                });
                renderKeys();
                renderPinGrid();
                updateWiringTable();
            }
        }

        function renderKeys() {
            const container = document.getElementById('keysList');
            container.innerHTML = '';
            
            config.keys.forEach((key, index) => {
                const div = document.createElement('div');
                div.className = 'key-item';
                div.innerHTML = `
                    <div class="form-group">
                        <label>GPIO</label>
                        <select onchange="updateKey(${index}, 'gpio', this.value)">
                            ${availableGpios.map(gpio => 
                                `<option value="${gpio}" ${key.gpio === gpio ? 'selected' : ''}>GP${gpio}</option>`
                            ).join('')}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Klawisz</label>
                        <select onchange="updateKey(${index}, 'keycode', this.value)">
                            ${Object.entries(keycodes).map(([name, code]) => 
                                `<option value="${code}" ${key.keycode === code ? 'selected' : ''}>${name}</option>`
                            ).join('')}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Modyfikator</label>
                        <select onchange="updateKey(${index}, 'modifier', this.value)">
                            <option value="Keycode.CONTROL" ${key.modifier === 'Keycode.CONTROL' ? 'selected' : ''}>Ctrl</option>
                            <option value="Keycode.ALT" ${key.modifier === 'Keycode.ALT' ? 'selected' : ''}>Alt</option>
                            <option value="Keycode.SHIFT" ${key.modifier === 'Keycode.SHIFT' ? 'selected' : ''}>Shift</option>
                            <option value="Keycode.GUI" ${key.modifier === 'Keycode.GUI' ? 'selected' : ''}>Win/Cmd</option>
                        </select>
                    </div>
                    <button class="btn" onclick="removeKey(${index})">🗑️ Usuń</button>
                `;
                container.appendChild(div);
            });
        }

        function renderEncoder() {
            const container = document.getElementById('encoderConfig');
            if (!config.encoder) {
                container.innerHTML = '<button class="btn btn-primary" onclick="addEncoder()">+ Dodaj enkoder</button>';
                return;
            }
            
            container.innerHTML = `
                <div class="key-item">
                    <div class="form-group">
                        <label>CLK</label>
                        <select onchange="updateEncoder('clk_gpio', this.value)">
                            ${availableGpios.map(gpio => 
                                `<option value="${gpio}" ${config.encoder.clk_gpio === gpio ? 'selected' : ''}>GP${gpio}</option>`
                            ).join('')}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>DT</label>
                        <select onchange="updateEncoder('dt_gpio', this.value)">
                            ${availableGpios.map(gpio => 
                                `<option value="${gpio}" ${config.encoder.dt_gpio === gpio ? 'selected' : ''}>GP${gpio}</option>`
                            ).join('')}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>SW (przycisk)</label>
                        <select onchange="updateEncoder('sw_gpio', this.value)">
                            ${availableGpios.map(gpio => 
                                `<option value="${gpio}" ${config.encoder.sw_gpio === gpio ? 'selected' : ''}>GP${gpio}</option>`
                            ).join('')}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Prędkość scrolla</label>
                        <input type="number" min="1" max="10" value="${config.encoder.scroll_speed}" 
                               onchange="updateEncoder('scroll_speed', this.value)">
                    </div>
                    <div class="form-group">
                        <label><input type="checkbox" ${config.encoder.middle_click ? 'checked' : ''} 
                                       onchange="updateEncoder('middle_click', this.checked)"> Środkowy klik</label>
                    </div>
                    <button class="btn" onclick="removeEncoder()">🗑️ Usuń enkoder</button>
                </div>
            `;
        }

        function updateKey(index, field, value) {
            config.keys[index][field] = value;
            renderPinGrid();
            updateWiringTable();
        }

        function updateEncoder(field, value) {
            config.encoder[field] = value;
            renderPinGrid();
            updateWiringTable();
        }

        function addKey() {
            if (config.keys.length >= 9) {
                showMessage('Maksymalnie 9 przycisków', 'error');
                return;
            }
            
            const freeGpios = availableGpios.filter(gpio => {
                const used = config.keys.some(key => key.gpio === gpio);
                if (config.encoder) {
                    return !used && gpio !== config.encoder.clk_gpio && 
                           gpio !== config.encoder.dt_gpio && gpio !== config.encoder.sw_gpio;
                }
                return !used;
            });
            
            if (freeGpios.length === 0) {
                showMessage('Brak wolnych pinów GPIO', 'error');
                return;
            }
            
            config.keys.push({
                gpio: freeGpios[0],
                keycode: 'Keycode.ONE',
                modifier: 'Keycode.CONTROL',
                label: `Key ${config.keys.length + 1}`
            });
            
            renderKeys();
            renderPinGrid();
            updateWiringTable();
        }

        function removeKey(index) {
            config.keys.splice(index, 1);
            renderKeys();
            renderPinGrid();
            updateWiringTable();
        }

        function addEncoder() {
            const freeGpios = availableGpios.filter(gpio => {
                const used = config.keys.some(key => key.gpio === gpio);
                return !used;
            });
            
            if (freeGpios.length < 3) {
                showMessage('Potrzebne 3 wolne piny GPIO dla enkodera', 'error');
                return;
            }
            
            config.encoder = {
                clk_gpio: freeGpios[0],
                dt_gpio: freeGpios[1],
                sw_gpio: freeGpios[2],
                scroll_speed: 2,
                middle_click: true
            };
            
            renderEncoder();
            renderPinGrid();
            updateWiringTable();
        }

        function removeEncoder() {
            config.encoder = null;
            renderEncoder();
            renderPinGrid();
            updateWiringTable();
        }

        function updateWiringTable() {
            const tbody = document.querySelector('#wiringTable tbody');
            tbody.innerHTML = '';
            
            config.keys.forEach((key, index) => {
                const row = tbody.insertRow();
                row.innerHTML = `
                    <td>Przycisk ${index + 1}</td>
                    <td>GP${key.gpio}</td>
                    <td>Pin 1</td>
                    <td>${key.modifier.replace('Keycode.', '')} + ${key.keycode.replace('Keycode.', '')}</td>
                `;
            });
            
            if (config.encoder) {
                const encRows = [
                    ['Enkoder CLK', config.encoder.clk_gpio, 'CLK', 'Sygnał A enkodera'],
                    ['Enkoder DT', config.encoder.dt_gpio, 'DT', 'Sygnał B enkodera'],
                    ['Enkoder SW', config.encoder.sw_gpio, 'SW', 'Przycisk enkodera']
                ];
                
                encRows.forEach(([name, gpio, pin, func]) => {
                    const row = tbody.insertRow();
                    row.innerHTML = `<td>${name}</td><td>GP${gpio}</td><td>${pin}</td><td>${func}</td>`;
                });
            }
        }

        async function generateCode() {
            try {
                const response = await fetch('/api/generate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(config)
                });
                
                const result = await response.json();
                
                if (result.valid) {
                    document.getElementById('codeOutput').textContent = result.code;
                    showMessage('Kod wygenerowany pomyślnie!', 'success');
                    currentCode = result.code;
                    currentBoot = result.boot;
                } else {
                    showMessage('Błędy walidacji: ' + result.errors.join(', '), 'error');
                }
            } catch (error) {
                showMessage('Błąd generowania kodu: ' + error.message, 'error');
            }
        }

        let currentCode = '';
        let currentBoot = '';

        function copyCode() {
            if (currentCode) {
                navigator.clipboard.writeText(currentCode);
                showMessage('code.py skopiowany do schowka!', 'success');
            }
        }

        function copyBoot() {
            if (currentBoot) {
                navigator.clipboard.writeText(currentBoot);
                showMessage('boot.py skopiowany do schowka!', 'success');
            }
        }

        function downloadCode() {
            if (!currentCode) return;
            
            // Pobierz code.py
            const codeBlob = new Blob([currentCode], {type: 'text/plain'});
            const codeUrl = URL.createObjectURL(codeBlob);
            const codeLink = document.createElement('a');
            codeLink.href = codeUrl;
            codeLink.download = 'code.py';
            codeLink.click();
            
            // Pobierz boot.py
            const bootBlob = new Blob([currentBoot], {type: 'text/plain'});
            const bootUrl = URL.createObjectURL(bootBlob);
            const bootLink = document.createElement('a');
            bootLink.href = bootUrl;
            bootLink.download = 'boot.py';
            bootLink.click();
            
            showMessage('Pliki pobrane!', 'success');
        }

        function showMessage(message, type) {
            const container = document.getElementById('messages');
            const div = document.createElement('div');
            div.className = type;
            div.textContent = message;
            container.appendChild(div);
            setTimeout(() => div.remove(), 5000);
        }

        // Inicjalizacja
        init();

        // ══════════════ TEST PAGE ══════════════

        // Build test grid
        (function buildTestGrid() {
            const grid = document.getElementById('testGrid');
            if (!grid) return;
            const labels = ['Tab 1','Tab 2','Tab 3','Tab 4','Tab 5','Tab 6','Tab 7','Tab 8','Tab 9'];
            for (let i = 1; i <= 9; i++) {
                const btn = document.createElement('div');
                btn.className = 'test-btn';
                btn.id = 'test-key-' + i;
                btn.innerHTML = `<span class="combo">Ctrl +</span><span class="num">${i}</span><span class="label">${labels[i-1]}</span>`;
                grid.appendChild(btn);
            }
        })();

        // Test state
        let testKeyCount = 0, testScrollCount = 0, testTotalCount = 0;
        let encRotation = 0;
        const eventLogEl = document.getElementById('eventLog');
        const encWheelEl = document.getElementById('encWheel');
        let logStarted = false;

        function testTs() {
            const d = new Date();
            return d.toLocaleTimeString('pl-PL', {hour:'2-digit',minute:'2-digit',second:'2-digit'}) + '.' + String(d.getMilliseconds()).padStart(3,'0');
        }

        function addLogEntry(msg, type) {
            if (!logStarted) { eventLogEl.innerHTML = ''; logStarted = true; }
            const ev = document.createElement('div');
            ev.className = 'ev ' + type;
            ev.innerHTML = `<span class="ts">${testTs()}</span><span class="msg">${msg}</span>`;
            eventLogEl.prepend(ev);
            while (eventLogEl.children.length > 200) eventLogEl.removeChild(eventLogEl.lastChild);
            testTotalCount++;
            document.getElementById('statTotal').textContent = testTotalCount;
        }

        function clearTestLog() {
            eventLogEl.innerHTML = '<div class="ev" style="color:#888;border:none">Oczekiwanie na zdarzenia...</div>';
            logStarted = false;
            testKeyCount = 0; testScrollCount = 0; testTotalCount = 0;
            document.getElementById('statKeys').textContent = '0';
            document.getElementById('statScroll').textContent = '0';
            document.getElementById('statTotal').textContent = '0';
            document.getElementById('encCount').textContent = '0';
            encRotation = 0;
            if (encWheelEl) encWheelEl.style.transform = '';
        }

        // Keyboard event detection (Ctrl+1..9)
        const activeTestKeys = new Set();

        document.addEventListener('keydown', function(e) {
            if (!e.ctrlKey && !e.metaKey) return;
            const digit = (e.key >= '1' && e.key <= '9') ? parseInt(e.key) : null;
            if (!digit) return;

            e.preventDefault();
            e.stopPropagation();

            if (activeTestKeys.has(digit)) return;
            activeTestKeys.add(digit);

            const btn = document.getElementById('test-key-' + digit);
            if (btn) btn.classList.add('active');

            testKeyCount++;
            document.getElementById('statKeys').textContent = testKeyCount;
            addLogEntry(`Ctrl+${digit} ▼ wciśnięty`, 'key-ev');
        });

        document.addEventListener('keyup', function(e) {
            const digit = (e.key >= '1' && e.key <= '9') ? parseInt(e.key) : null;
            if (!digit) return;

            activeTestKeys.delete(digit);
            const btn = document.getElementById('test-key-' + digit);
            if (btn) btn.classList.remove('active');
            addLogEntry(`Ctrl+${digit} ▲ zwolniony`, 'key-ev');
        });

        // Scroll wheel detection (encoder)
        let scrollTimeout;
        document.addEventListener('wheel', function(e) {
            const testTab = document.getElementById('test');
            if (!testTab || !testTab.classList.contains('active')) return;

            e.preventDefault();

            const direction = e.deltaY < 0 ? 'up' : 'down';
            const delta = Math.round(e.deltaY);

            encRotation += direction === 'up' ? -15 : 15;
            if (encWheelEl) encWheelEl.style.transform = `rotate(${encRotation}deg)`;

            if (encWheelEl) {
                encWheelEl.classList.remove('scroll-up', 'scroll-down');
                encWheelEl.classList.add(direction === 'up' ? 'scroll-up' : 'scroll-down');
                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(() => {
                    encWheelEl.classList.remove('scroll-up', 'scroll-down');
                }, 300);
            }

            const dirEl = document.getElementById('encDir');
            if (dirEl) {
                dirEl.textContent = direction === 'up' ? '↑ CW' : '↓ CCW';
                dirEl.className = 'dir ' + direction;
            }

            document.getElementById('encDelta').textContent = `deltaY: ${delta}`;
            testScrollCount++;
            document.getElementById('statScroll').textContent = testScrollCount;
            document.getElementById('encCount').textContent = testScrollCount;

            addLogEntry(`Scroll ${direction === 'up' ? '↑ CW (góra)' : '↓ CCW (dół)'} Δ${delta}`, 'enc-ev');
        }, { passive: false });

        // Middle-click detection (encoder button)
        document.addEventListener('mousedown', function(e) {
            if (e.button !== 1) return;
            const testTab = document.getElementById('test');
            if (!testTab || !testTab.classList.contains('active')) return;

            e.preventDefault();
            if (encWheelEl) encWheelEl.classList.add('btn-press');
            addLogEntry('Middle-click ▼ (enkoder SW)', 'btn-ev');
        });

        document.addEventListener('mouseup', function(e) {
            if (e.button !== 1) return;
            if (encWheelEl) encWheelEl.classList.remove('btn-press');
            addLogEntry('Middle-click ▲ zwolniony', 'btn-ev');
        });
    </script>
</body>
</html>
'''

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
