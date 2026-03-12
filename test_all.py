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

from web.app import (
    PadConfig, KeyConfig, EncoderConfig,
    generate_code_py, validate_config, BOOT_PY,
    KEYCODES, MODIFIERS,
)


# ============================================================================
# UNIT: Walidacja konfiguracji
# ============================================================================

class TestValidation:

    def test_default_config_valid(self):
        """Domyślna konfiguracja nie ma błędów."""
        cfg = PadConfig()
        errors = validate_config(cfg)
        assert errors == [], f"Nieoczekiwane błędy: {errors}"

    def test_duplicate_gpio_detected(self):
        """Zduplikowane piny GPIO powinny generować błąd."""
        cfg = PadConfig(keys=[
            KeyConfig(1, "ONE", "CTRL"),
            KeyConfig(1, "TWO", "CTRL"),  # duplikat GP1
        ])
        errors = validate_config(cfg)
        assert any("już użyty" in e for e in errors)

    def test_invalid_gpio(self):
        """GPIO poza zakresem 0-29 powinno dać błąd."""
        cfg = PadConfig(keys=[KeyConfig(99, "ONE", "CTRL")])
        errors = validate_config(cfg)
        assert any("nie istnieje" in e for e in errors)

    def test_invalid_keycode(self):
        """Nieznany keycode powinien dać błąd."""
        cfg = PadConfig(keys=[KeyConfig(1, "FAKE_KEY", "CTRL")])
        errors = validate_config(cfg)
        assert any("nieznany keycode" in e for e in errors)

    def test_invalid_modifier(self):
        """Nieznany modifier powinien dać błąd."""
        cfg = PadConfig(keys=[KeyConfig(1, "ONE", "SUPER_FAKE")])
        errors = validate_config(cfg)
        assert any("nieznany modifier" in e for e in errors)

    def test_encoder_gpio_conflict_with_key(self):
        """Piny enkodera nie mogą kolidować z klawiszami."""
        cfg = PadConfig(
            keys=[KeyConfig(9, "ONE", "CTRL")],  # GP9 = to samo co enkoder CLK
            encoder=EncoderConfig(clk_gpio=9),
        )
        errors = validate_config(cfg)
        assert any("GP9" in e and "już użyty" in e for e in errors)

    def test_encoder_internal_conflict(self):
        """Piny enkodera nie mogą być takie same."""
        cfg = PadConfig(
            keys=[],
            encoder=EncoderConfig(clk_gpio=9, dt_gpio=9, sw_gpio=11),  # CLK=DT
        )
        errors = validate_config(cfg)
        assert any("GP9" in e and "już użyty" in e for e in errors)

    def test_scroll_speed_bounds(self):
        """Scroll speed musi być 1-20."""
        cfg = PadConfig(keys=[], encoder=EncoderConfig(scroll_speed=0))
        errors = validate_config(cfg)
        assert any("scroll_speed" in e for e in errors)

        cfg2 = PadConfig(keys=[], encoder=EncoderConfig(scroll_speed=21))
        errors2 = validate_config(cfg2)
        assert any("scroll_speed" in e for e in errors2)

    def test_debounce_bounds(self):
        """Debounce musi być 5-500ms."""
        cfg = PadConfig(keys=[], encoder=EncoderConfig(debounce_ms=1))
        errors = validate_config(cfg)
        assert any("debounce_ms" in e for e in errors)

    def test_empty_keys_valid(self):
        """Zero klawiszy to poprawna konfiguracja (sam enkoder)."""
        cfg = PadConfig(keys=[])
        errors = validate_config(cfg)
        assert errors == []

    def test_max_keys(self):
        """Można podłączyć do ~24 klawiszy (bez enkodera)."""
        free = [g for g in range(1, 29) if g not in (9, 10, 11)]
        keys_list = [KeyConfig(g, "A", "CTRL") for g in free[:20]]
        cfg = PadConfig(keys=keys_list)
        errors = validate_config(cfg)
        assert errors == []


# ============================================================================
# UNIT: Generator kodu
# ============================================================================

class TestCodeGenerator:

    def test_generates_valid_python(self):
        """Wygenerowany code.py musi być poprawnym Pythonem (AST parse)."""
        cfg = PadConfig()
        code = generate_code_py(cfg)
        # Powinien parsować się jako Python — zastępujemy importy CircuitPython
        parseable = _make_parseable(code)
        try:
            ast.parse(parseable)
        except SyntaxError as e:
            pytest.fail(f"Wygenerowany kod nie jest poprawnym Pythonem:\n{e}\n\n{code}")

    def test_contains_all_gpios(self):
        """Kod musi zawierać wszystkie skonfigurowane piny GPIO."""
        cfg = PadConfig()
        code = generate_code_py(cfg)
        for k in cfg.keys:
            assert f"GP{k.gpio}" in code, f"Brak GP{k.gpio} w wygenerowanym kodzie"

    def test_contains_encoder_pins(self):
        """Kod musi zawierać piny enkodera."""
        cfg = PadConfig()
        code = generate_code_py(cfg)
        assert f"GP{cfg.encoder.clk_gpio}" in code
        assert f"GP{cfg.encoder.dt_gpio}" in code
        assert f"GP{cfg.encoder.sw_gpio}" in code

    def test_contains_hid_imports(self):
        """Kod musi importować keyboard i mouse z adafruit_hid."""
        cfg = PadConfig()
        code = generate_code_py(cfg)
        assert "from adafruit_hid.keyboard import Keyboard" in code
        assert "from adafruit_hid.mouse import Mouse" in code

    def test_custom_keycodes(self):
        """Zmiana keycode'ów musi się odzwierciedlić w kodzie."""
        cfg = PadConfig(keys=[
            KeyConfig(1, "F1", "ALT", "Pomoc"),
            KeyConfig(2, "ESCAPE", "NONE", "Wyjście"),
        ])
        code = generate_code_py(cfg)
        assert "Keycode.F1" in code
        assert "Keycode.ESCAPE" in code

    def test_scroll_speed_in_code(self):
        """scroll_speed z konfiguracji musi być w kodzie."""
        cfg = PadConfig(encoder=EncoderConfig(scroll_speed=7))
        code = generate_code_py(cfg)
        assert "SCROLL_SPEED    = 7" in code or "SCROLL_SPEED = 7" in code

    def test_modifier_in_press(self):
        """Modifier CTRL musi pojawić się w keyboard.press()."""
        cfg = PadConfig(keys=[KeyConfig(1, "ONE", "CTRL")])
        code = generate_code_py(cfg)
        assert "Keycode.CONTROL" in code

    def test_no_modifier(self):
        """NONE modifier = brak modyfikatora w press()."""
        cfg = PadConfig(keys=[KeyConfig(1, "A", "NONE")])
        code = generate_code_py(cfg)
        assert "keyboard.press(key['keycode'])" in code


class TestBootPy:

    def test_boot_contains_keyboard_and_mouse(self):
        """boot.py musi włączać KEYBOARD i MOUSE."""
        assert "Device.KEYBOARD" in BOOT_PY
        assert "Device.MOUSE" in BOOT_PY

    def test_boot_imports_usb_hid(self):
        assert "import usb_hid" in BOOT_PY


# ============================================================================
# E2E: Web API
# ============================================================================

@pytest.fixture
def client():
    from httpx import AsyncClient, ASGITransport
    from web.app import app
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class TestWebAPI:

    @pytest.mark.asyncio
    async def test_homepage_loads(self, client):
        """Strona główna (HTML) musi się załadować."""
        r = await client.get("/")
        assert r.status_code == 200
        assert "Keypad Configurator" in r.text

    @pytest.mark.asyncio
    async def test_defaults_endpoint(self, client):
        """GET /api/defaults zwraca poprawną strukturę."""
        r = await client.get("/api/defaults")
        assert r.status_code == 200
        d = r.json()
        assert "keys" in d
        assert "encoder" in d
        assert "available_keycodes" in d
        assert len(d["keys"]) == 9

    @pytest.mark.asyncio
    async def test_validate_ok(self, client):
        """POST /api/validate z dobrą konfiguracją."""
        r = await client.get("/api/defaults")
        cfg = r.json()
        payload = {"keys": cfg["keys"], "encoder": cfg["encoder"]}
        v = await client.post("/api/validate", json=payload)
        assert v.json()["valid"] is True

    @pytest.mark.asyncio
    async def test_validate_duplicate_gpio(self, client):
        """POST /api/validate z duplikatem GPIO."""
        payload = {
            "keys": [
                {"gpio": 1, "keycode": "ONE", "modifier": "CTRL"},
                {"gpio": 1, "keycode": "TWO", "modifier": "CTRL"},
            ],
            "encoder": {"clk_gpio": 9, "dt_gpio": 10, "sw_gpio": 11,
                        "scroll_speed": 2, "debounce_ms": 50},
        }
        v = await client.post("/api/validate", json=payload)
        assert v.json()["valid"] is False

    @pytest.mark.asyncio
    async def test_generate_returns_code(self, client):
        """POST /api/generate zwraca code_py i boot_py."""
        r = await client.get("/api/defaults")
        cfg = r.json()
        payload = {"keys": cfg["keys"], "encoder": cfg["encoder"]}
        g = await client.post("/api/generate", json=payload)
        assert g.status_code == 200
        d = g.json()
        assert "code_py" in d
        assert "boot_py" in d
        assert "import" in d["code_py"]

    @pytest.mark.asyncio
    async def test_generate_invalid_returns_400(self, client):
        """POST /api/generate z błędami zwraca 400."""
        payload = {
            "keys": [{"gpio": 99, "keycode": "FAKE", "modifier": "CTRL"}],
            "encoder": {"clk_gpio": 9, "dt_gpio": 10, "sw_gpio": 11,
                        "scroll_speed": 2, "debounce_ms": 50},
        }
        g = await client.post("/api/generate", json=payload)
        assert g.status_code == 400

    @pytest.mark.asyncio
    async def test_download_boot(self, client):
        """GET /api/download/boot.py zwraca plik."""
        r = await client.get("/api/download/boot.py")
        assert r.status_code == 200
        assert "usb_hid" in r.text

    @pytest.mark.asyncio
    async def test_full_flow(self, client):
        """E2E: pobranie domyślnych → walidacja → generacja → download."""
        # 1. Defaults
        defaults = (await client.get("/api/defaults")).json()

        # 2. Modify — dodaj etykiety
        keys = defaults["keys"]
        for i, k in enumerate(keys):
            k["label"] = f"Makro {i+1}"

        payload = {"keys": keys, "encoder": defaults["encoder"]}

        # 3. Validate
        v = (await client.post("/api/validate", json=payload)).json()
        assert v["valid"] is True

        # 4. Generate
        g = (await client.post("/api/generate", json=payload)).json()
        assert "code_py" in g

        # 5. Download
        dl = await client.get("/api/download/code.py")
        assert dl.status_code == 200
        assert "Makro 1" in dl.text


# ============================================================================
# E2E: Generowany kod — analiza statyczna
# ============================================================================

class TestGeneratedCodeQuality:

    def test_no_syntax_errors_default(self):
        """Domyślna konfiguracja generuje poprawny Python."""
        code = generate_code_py(PadConfig())
        parseable = _make_parseable(code)
        ast.parse(parseable)

    def test_no_syntax_errors_custom(self):
        """Niestandardowa konfiguracja generuje poprawny Python."""
        cfg = PadConfig(
            keys=[
                KeyConfig(0, "F1", "ALT", "Funkcja 1"),
                KeyConfig(15, "SPACE", "SHIFT", "Spacja"),
                KeyConfig(28, "ENTER", "NONE", "Enter"),
            ],
            encoder=EncoderConfig(clk_gpio=20, dt_gpio=21, sw_gpio=22, scroll_speed=5)
        )
        code = generate_code_py(cfg)
        parseable = _make_parseable(code)
        ast.parse(parseable)

    def test_no_hardcoded_pins_leak(self):
        """Generowany kod nie powinien mieć hardkodowanych pinów spoza konfiguracji."""
        cfg = PadConfig(
            keys=[KeyConfig(15, "A", "CTRL")],
            encoder=EncoderConfig(clk_gpio=20, dt_gpio=21, sw_gpio=22)
        )
        code = generate_code_py(cfg)
        # GP1-GP8 nie powinny być w kodzie
        for g in [1, 2, 3, 4, 5, 6, 7, 8]:
            # Szukamy "board.GPX" — dokładne dopasowanie
            assert f"board.GP{g}," not in code and f"board.GP{g}\n" not in code, \
                f"Znaleziono hardkodowany GP{g} w kodzie"

    def test_while_true_loop(self):
        """Kod musi mieć główną pętlę while True."""
        code = generate_code_py(PadConfig())
        assert "while True:" in code

    def test_sleep_present(self):
        """Pętla musi mieć time.sleep() dla kontroli CPU."""
        code = generate_code_py(PadConfig())
        assert "time.sleep(" in code


# ============================================================================
# HELPERS
# ============================================================================

def _make_parseable(code: str) -> str:
    """Zamień importy CircuitPython na stub'y, aby ast.parse() działał."""
    # Zastąp board.GPxx na stałe int
    code = re.sub(r'board\.GP(\d+)', r'\1', code)
    # Zastąp Keycode.XXX na stringi
    code = re.sub(r'Keycode\.(\w+)', r'"\1"', code)
    # Zastąp Mouse.MIDDLE_BUTTON
    code = code.replace('Mouse.MIDDLE_BUTTON', '4')
    # Zamień importy na fake'y
    lines = []
    for line in code.split('\n'):
        stripped = line.strip()
        if stripped.startswith(('import board', 'import digitalio',
                                'import usb_hid', 'from adafruit_hid')):
            lines.append('# ' + line)
        elif 'Keyboard(usb_hid' in line:
            lines.append(line.replace('Keyboard(usb_hid.devices)', 'None'))
        elif 'Mouse(usb_hid' in line:
            lines.append(line.replace('Mouse(usb_hid.devices)', 'None'))
        elif 'digitalio.DigitalInOut' in line:
            lines.append(line.split('=')[0] + '= None')
        elif '.direction' in stripped or '.pull' in stripped:
            lines.append('# ' + line)
        elif stripped.startswith(('keyboard.', 'mouse.')):
            # Preserve indentation but replace with pass
            indent = line[:len(line) - len(line.lstrip())]
            lines.append(indent + 'pass  # ' + stripped)
        elif 'encoder_clk.value' in line or 'encoder_dt.value' in line or 'encoder_sw.value' in line:
            # Replace .value calls with None
            lines.append(line.replace('encoder_clk.value', 'None')
                            .replace('encoder_dt.value', 'None')
                            .replace('encoder_sw.value', 'None'))
        elif "key['pin'].value" in line:
            lines.append(line.replace("key['pin'].value", 'None'))
        else:
            lines.append(line)
    return '\n'.join(lines)
