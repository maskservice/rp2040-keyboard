"""
RP2040-One Keypad — Test Suite
================================
Testy jednostkowe + E2E dla code generatora, walidatora i web API.

Uruchom:
  make test                  # lokalne pytest
  make test-docker           # w Docker
  make test-e2e              # Docker Compose E2E
"""

import ast
import json
import re
import sys
import textwrap
from pathlib import Path

import pytest

# Dodaj root projektu do PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from rp2040_keyboard.firmware import (
    PadConfig, KeyConfig, EncoderConfig,
    generate_code_py, validate_config, BOOT_PY,
    KEYCODES, MODIFIERS, AVAILABLE_GPIOS,
)

# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def valid_config():
    """Poprawna konfiguracja testowa."""
    keys = [
        KeyConfig(gpio=1, keycode="Keycode.ONE", modifier="Keycode.CONTROL+Keycode.SHIFT"),
        KeyConfig(gpio=2, keycode="Keycode.TWO", modifier="Keycode.CONTROL+Keycode.SHIFT"),
        KeyConfig(gpio=3, keycode="Keycode.THREE", modifier="Keycode.CONTROL+Keycode.SHIFT"),
    ]
    encoder = EncoderConfig(clk_gpio=9, dt_gpio=10, sw_gpio=11, scroll_speed=2, debounce_ms=3)
    return PadConfig(keys=keys, encoder=encoder)

@pytest.fixture
def invalid_config():
    """Niepoprawna konfiguracja testowa (konflikty GPIO)."""
    keys = [
        KeyConfig(gpio=1, keycode="Keycode.ONE", modifier="Keycode.CONTROL+Keycode.SHIFT"),
        KeyConfig(gpio=1, keycode="Keycode.TWO", modifier="Keycode.CONTROL+Keycode.SHIFT"),  # Konflikt
        KeyConfig(gpio=50, keycode="Keycode.THREE", modifier="Keycode.CONTROL+Keycode.SHIFT"),  # Nieprawidłowy GPIO
    ]
    return PadConfig(keys=keys, encoder=None)

# ============================================================================
# TESTY MODELI DANYCH
# ============================================================================

def test_pad_config_to_dict(valid_config):
    """Test konwersji PadConfig do słownika."""
    result = valid_config.to_dict()
    assert isinstance(result, dict)
    assert 'keys' in result
    assert 'encoder' in result
    assert len(result['keys']) == 3
    assert result['encoder']['clk_gpio'] == 9

def test_pad_config_from_dict(valid_config):
    """Test tworzenia PadConfig ze słownika."""
    data = valid_config.to_dict()
    restored = PadConfig.from_dict(data)
    assert len(restored.keys) == len(valid_config.keys)
    assert restored.encoder.clk_gpio == valid_config.encoder.clk_gpio

def test_key_config_creation():
    """Test tworzenia KeyConfig."""
    key = KeyConfig(gpio=5, keycode="Keycode.A", modifier="Keycode.CONTROL+Keycode.SHIFT")
    assert key.gpio == 5
    assert key.keycode == "Keycode.A"
    assert key.modifier == "Keycode.CONTROL+Keycode.SHIFT"

def test_encoder_config_creation():
    """Test tworzenia EncoderConfig."""
    encoder = EncoderConfig(clk_gpio=6, dt_gpio=7, sw_gpio=8, scroll_speed=5, debounce_ms=3)
    assert encoder.clk_gpio == 6
    assert encoder.dt_gpio == 7
    assert encoder.sw_gpio == 8
    assert encoder.scroll_speed == 5
    assert encoder.middle_click is True

# ============================================================================
# TESTY WALIDACJI
# ============================================================================

def test_validate_valid_config(valid_config):
    """Test walidacji poprawnej konfiguracji."""
    is_valid, errors = validate_config(valid_config)
    assert is_valid
    assert len(errors) == 0

def test_validate_invalid_config(invalid_config):
    """Test walidacji niepoprawnej konfiguracji."""
    is_valid, errors = validate_config(invalid_config)
    assert not is_valid
    assert len(errors) > 0
    assert any("GPIO 1 używane wielokrotnie" in error for error in errors)
    assert any("GPIO 50 nie jest dostępne" in error for error in errors)

def test_validate_encoder_gpio_conflicts():
    """Test konfliktów GPIO w enkoderze."""
    keys = [KeyConfig(gpio=9, keycode="Keycode.ONE", modifier="Keycode.CONTROL+Keycode.SHIFT")]
    encoder = EncoderConfig(clk_gpio=9, dt_gpio=10, sw_gpio=11, debounce_ms=3)  # Konflikt z przyciskiem
    config = PadConfig(keys=keys, encoder=encoder)
    
    is_valid, errors = validate_config(config)
    assert not is_valid
    assert any("GPIO 9 enkodera koliduje" in error for error in errors)

def test_validate_encoder_same_clk_dt():
    """Test tej samej wartości CLK i DT."""
    encoder = EncoderConfig(clk_gpio=9, dt_gpio=9, sw_gpio=10, debounce_ms=3)
    config = PadConfig(keys=[], encoder=encoder)
    
    is_valid, errors = validate_config(config)
    assert not is_valid
    assert any("CLK i DT enkodera nie mogą być tym samym pinem" in error for error in errors)

def test_validate_scroll_speed_range():
    """Test zakresu prędkości scrolla."""
    encoder = EncoderConfig(clk_gpio=9, dt_gpio=10, sw_gpio=11, scroll_speed=15, debounce_ms=3)
    config = PadConfig(keys=[], encoder=encoder)
    
    is_valid, errors = validate_config(config)
    assert not is_valid
    assert any("Scroll speed musi być między 1 a 10" in error for error in errors)

# ============================================================================
# TESTY GENERATORA KODU
# ============================================================================

def test_generate_code_basic(valid_config):
    """Test podstawowej generacji kodu."""
    code = generate_code_py(valid_config)
    assert isinstance(code, str)
    assert len(code) > 0
    assert "import board" in code
    assert "import digitalio" in code
    assert "import rotaryio" in code
    assert "Keyboard(usb_hid.devices)" in code
    assert "Mouse(usb_hid.devices)" in code

def test_generate_code_keys_section(valid_config):
    """Test sekcji konfiguracji przycisków."""
    code = generate_code_py(valid_config)
    assert "key_1_pin = digitalio.DigitalInOut(board.GP1)" in code
    assert "key_2_pin = digitalio.DigitalInOut(board.GP2)" in code
    assert "key_3_pin = digitalio.DigitalInOut(board.GP3)" in code
    assert "digitalio.Pull.UP" in code
    assert "keyboard.press(Keycode.CONTROL, Keycode.SHIFT, Keycode.ONE)" in code

def test_generate_code_encoder_section(valid_config):
    """Test sekcji konfiguracji enkodera."""
    code = generate_code_py(valid_config)
    assert "encoder = rotaryio.IncrementalEncoder(board.GP9, board.GP10)" in code
    assert "encoder_button = digitalio.DigitalInOut(board.GP11)" in code
    assert "SCROLL_SPEED = 2" in code

def test_generate_code_main_loop(valid_config):
    """Test głównej pętli programu."""
    code = generate_code_py(valid_config)
    assert "while True:" in code
    assert "keyboard.press" in code
    assert "keyboard.release" in code
    assert "mouse.move" in code

def test_generate_code_without_encoder():
    """Test generacji kodu bez enkodera."""
    keys = [KeyConfig(gpio=1, keycode="Keycode.ONE", modifier="Keycode.CONTROL+Keycode.SHIFT")]
    config = PadConfig(keys=keys, encoder=None)
    
    code = generate_code_py(config)
    assert "rotaryio" not in code
    assert "encoder" not in code
    assert "Keyboard(usb_hid.devices)" in code

def test_generate_code_syntax_valid(valid_config):
    """Test czy wygenerowany kod ma poprawną składnię Python."""
    code = generate_code_py(valid_config)
    try:
        ast.parse(code)
        assert True  # Kod parsuje się poprawnie
    except SyntaxError:
        assert False, "Wygenerowany kod ma błędy składniowe"

# ============================================================================
# TESTY STAŁYCH
# ============================================================================

def test_keycodes_constants():
    """Test stałych kodów klawiszy."""
    assert isinstance(KEYCODES, dict)
    assert "A" in KEYCODES
    assert "ONE" in KEYCODES
    assert "F1" in KEYCODES
    assert KEYCODES["A"] == "Keycode.A"
    assert KEYCODES["ONE"] == "Keycode.ONE"

def test_modifiers_constants():
    """Test stałych modyfikatorów."""
    assert isinstance(MODIFIERS, dict)
    assert "CTRL" in MODIFIERS
    assert "ALT" in MODIFIERS
    assert "SHIFT" in MODIFIERS
    assert MODIFIERS["CTRL"] == "Keycode.CONTROL"

def test_boot_py_constant():
    """Test stałej BOOT_PY."""
    assert isinstance(BOOT_PY, str)
    assert len(BOOT_PY) > 0
    assert "usb_hid" in BOOT_PY
    assert "KEYBOARD" in BOOT_PY
    assert "MOUSE" in BOOT_PY

# ============================================================================
# TESTY INTEGRACYJNE
# ============================================================================

def test_full_workflow_valid_config(valid_config):
    """Test pełnego przepływu pracy dla poprawnej konfiguracji."""
    # 1. Walidacja
    is_valid, errors = validate_config(valid_config)
    assert is_valid
    assert len(errors) == 0
    
    # 2. Generacja kodu
    code = generate_code_py(valid_config)
    assert len(code) > 0
    
    # 3. Parsowanie kodu
    try:
        ast.parse(code)
    except SyntaxError:
        assert False, "Wygenerowany kod ma błędy składniowe"

def test_full_workflow_invalid_config(invalid_config):
    """Test pełnego przepływu pracy dla niepoprawnej konfiguracji."""
    # 1. Walidacja
    is_valid, errors = validate_config(invalid_config)
    assert not is_valid
    assert len(errors) > 0

def test_config_serialization_roundtrip(valid_config):
    """Test serializacji i deserializacji konfiguracji."""
    # 1. Konwersja do słownika
    data = valid_config.to_dict()
    assert isinstance(data, dict)
    
    # 2. Odtworzenie ze słownika
    restored = PadConfig.from_dict(data)
    
    # 3. Porównanie
    assert len(restored.keys) == len(valid_config.keys)
    assert restored.encoder.clk_gpio == valid_config.encoder.clk_gpio
    assert restored.encoder.dt_gpio == valid_config.encoder.dt_gpio
    assert restored.encoder.sw_gpio == valid_config.encoder.sw_gpio

# ============================================================================
# TESTY BRANDEŻOWYCH PRZYPADKÓW
# ============================================================================

def test_maximum_keys_configuration():
    """Test konfiguracji z maksymalną liczbą przycisków."""
    keys = []
    keycodes = ["Keycode.ONE", "Keycode.TWO", "Keycode.THREE", "Keycode.FOUR", 
                "Keycode.FIVE", "Keycode.SIX", "Keycode.SEVEN", "Keycode.EIGHT", "Keycode.NINE"]
    for i, (gpio, keycode) in enumerate(zip([1, 2, 3, 4, 5, 6, 7, 8, 29], keycodes), 1):
        keys.append(KeyConfig(gpio=gpio, keycode=keycode, modifier="Keycode.CONTROL+Keycode.SHIFT"))
    
    config = PadConfig(keys=keys, encoder=None)
    is_valid, errors = validate_config(config)
    assert is_valid
    assert len(errors) == 0
    
    code = generate_code_py(config)
    # Count unique key pin definitions (key_1_pin, key_2_pin, etc.)
    import re
    key_pin_matches = re.findall(r'key_(\d+)_pin = digitalio\.DigitalInOut', code)
    assert len(key_pin_matches) == 9

def test_minimum_configuration():
    """Test minimalnej konfiguracji (jeden przycisk)."""
    keys = [KeyConfig(gpio=1, keycode="Keycode.A", modifier="Keycode.CONTROL+Keycode.SHIFT")]
    config = PadConfig(keys=keys, encoder=None)
    
    is_valid, errors = validate_config(config)
    assert is_valid
    assert len(errors) == 0
    
    code = generate_code_py(config)
    assert "key_1_pin" in code

def test_encoder_only_configuration():
    """Test konfiguracji tylko z enkoderem."""
    encoder = EncoderConfig(clk_gpio=9, dt_gpio=10, sw_gpio=11, scroll_speed=3, middle_click=False, debounce_ms=3)
    config = PadConfig(keys=[], encoder=encoder)
    
    is_valid, errors = validate_config(config)
    assert is_valid
    assert len(errors) == 0
    
    code = generate_code_py(config)
    assert "encoder" in code
    assert "mouse.move" in code  # Still needed for scrolling
    assert "Mouse.MIDDLE_BUTTON" not in code

def test_all_modifiers():
    """Test wszystkich modyfikatorów."""
    modifiers = ["Keycode.CONTROL", "Keycode.ALT", "Keycode.SHIFT", "Keycode.GUI"]
    keys = []
    for i, modifier in enumerate(modifiers, 1):
        keys.append(KeyConfig(gpio=i, keycode="Keycode.A", modifier=modifier))
    
    config = PadConfig(keys=keys, encoder=None)
    is_valid, errors = validate_config(config)
    assert is_valid
    assert len(errors) == 0

# ============================================================================
# TESTY WYDAJNOŚCIOWE
# ============================================================================

def test_code_generation_performance(valid_config):
    """Test wydajności generowania kodu."""
    import time
    
    start_time = time.time()
    for _ in range(100):
        generate_code_py(valid_config)
    end_time = time.time()
    
    # 100 generacji powinno zająć mniej niż 1 sekundę
    assert (end_time - start_time) < 1.0

def test_validation_performance():
    """Test wydajności walidacji."""
    import time
    
    # Duża konfiguracja
    keys = []
    for i in range(20):  # Więcej niż maksymalna liczba, aby testować walidację
        keys.append(KeyConfig(gpio=i, keycode="Keycode.A", modifier="Keycode.CONTROL+Keycode.SHIFT"))
    
    config = PadConfig(keys=keys, encoder=None)
    
    start_time = time.time()
    for _ in range(100):
        validate_config(config)
    end_time = time.time()
    
    # 100 walidacji powinno zająć mniej niż 0.5 sekundy
    assert (end_time - start_time) < 0.5

# ============================================================================
# TESTY E2E - WEB API
# ============================================================================

@pytest.mark.asyncio
async def test_api_default_config():
    """Test API - domyślna konfiguracja."""
    from rp2040_keyboard.web.app import app
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    response = client.get("/api/default")
    
    assert response.status_code == 200
    data = response.json()
    assert "keys" in data
    assert "encoder" in data
    assert len(data["keys"]) == 9  # Domyślnie 9 przycisków

@pytest.mark.asyncio
async def test_api_validate_valid(valid_config):
    """Test API - walidacja poprawnej konfiguracji."""
    from rp2040_keyboard.web.app import app
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    response = client.post("/api/validate", json=valid_config.to_dict())
    
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert len(data["errors"]) == 0

@pytest.mark.asyncio
async def test_api_validate_invalid(invalid_config):
    """Test API - walidacja niepoprawnej konfiguracji."""
    from rp2040_keyboard.web.app import app
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    response = client.post("/api/validate", json=invalid_config.to_dict())
    
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert len(data["errors"]) > 0

@pytest.mark.asyncio
async def test_api_generate_code(valid_config):
    """Test API - generowanie kodu."""
    from rp2040_keyboard.web.app import app
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    response = client.post("/api/generate", json=valid_config.to_dict())
    
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert "code" in data
    assert "boot" in data
    assert len(data["code"]) > 0
    assert len(data["boot"]) > 0

@pytest.mark.asyncio
async def test_api_keycodes():
    """Test API - pobieranie dostępnych kodów."""
    from rp2040_keyboard.web.app import app
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    response = client.get("/api/keycodes")
    
    assert response.status_code == 200
    data = response.json()
    assert "keycodes" in data
    assert "modifiers" in data
    assert "available_gpios" in data
    assert len(data["keycodes"]) > 0
    assert len(data["modifiers"]) > 0
    assert len(data["available_gpios"]) > 0

# ============================================================================
# TESTY REGRESJI
# ============================================================================

def test_regression_gpio_range_check():
    """Test regresji - sprawdzanie zakresu GPIO."""
    # Test z GPIO poza zakresem
    keys = [KeyConfig(gpio=100, keycode="Keycode.A", modifier="Keycode.CONTROL+Keycode.SHIFT")]
    config = PadConfig(keys=keys, encoder=None)
    
    is_valid, errors = validate_config(config)
    assert not is_valid
    assert any("nie jest dostępne" in error for error in errors)

def test_regression_empty_config():
    """Test regresji - pusta konfiguracja."""
    config = PadConfig(keys=[], encoder=None)
    
    is_valid, errors = validate_config(config)
    assert is_valid  # Pusta konfiguracja jest poprawna
    
    code = generate_code_py(config)
    assert "import board" in code  # Nadal powinien zawierać podstawowe importy

def test_regression_encoder_middle_click_false():
    """Test regresji - enkoder bez middle click."""
    encoder = EncoderConfig(clk_gpio=9, dt_gpio=10, sw_gpio=11, middle_click=False, debounce_ms=3)
    config = PadConfig(keys=[], encoder=encoder)
    
    code = generate_code_py(config)
    assert "Mouse.MIDDLE_BUTTON" not in code

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
