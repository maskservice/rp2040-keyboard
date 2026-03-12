"""
RP2040-One HID Keypad — Web Configurator
==========================================
FastAPI backend: visual pin editor, code generator, wiring guide, flash instructions.

Uruchom:  make web        (lub:  uvicorn web.app:app --port 8080)
Dev:      make dev        (auto-reload)
Docker:   make docker-run
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

# Import from firmware module
from ..firmware import (
    PadConfig, KeyConfig, EncoderConfig,
    generate_code_py, validate_config, BOOT_PY,
    KEYCODES, MODIFIERS, AVAILABLE_GPIOS
)

# Import HAL manager
from ..hal_manager import HALConfigManager

# ============================================================================
# APLIKACJA FASTAPI
# ============================================================================

app = FastAPI(
    title="RP2040-One Keypad Configurator",
    description="Visual pin editor and code generator for RP2040-One HID keypad",
    version="0.0.6"
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
    """Zwraca domyślną konfigurację z HAL lub standardową."""
    hal_manager = HALConfigManager()
    try:
        config = hal_manager.get_current_config()
        return config.to_dict()
    except Exception as e:
        print(f"⚠️ Błąd HAL, używam domyślnej konfiguracji: {e}")
        # Fallback do domyślnej konfiguracji
    default_keys = [
        KeyConfig(gpio=1, keycode="Keycode.ONE", modifier="Keycode.CONTROL+Keycode.SHIFT", label="Ctrl+Shift+1"),
        KeyConfig(gpio=2, keycode="Keycode.TWO", modifier="Keycode.CONTROL+Keycode.SHIFT", label="Ctrl+Shift+2"),
        KeyConfig(gpio=3, keycode="Keycode.THREE", modifier="Keycode.CONTROL+Keycode.SHIFT", label="Ctrl+Shift+3"),
        KeyConfig(gpio=4, keycode="Keycode.FOUR", modifier="Keycode.CONTROL+Keycode.SHIFT", label="Ctrl+Shift+4"),
        KeyConfig(gpio=5, keycode="Keycode.FIVE", modifier="Keycode.CONTROL+Keycode.SHIFT", label="Ctrl+Shift+5"),
        KeyConfig(gpio=6, keycode="Keycode.SIX", modifier="Keycode.CONTROL+Keycode.SHIFT", label="Ctrl+Shift+6"),
        KeyConfig(gpio=7, keycode="Keycode.SEVEN", modifier="Keycode.CONTROL+Keycode.SHIFT", label="Ctrl+Shift+7"),
        KeyConfig(gpio=8, keycode="Keycode.EIGHT", modifier="Keycode.CONTROL+Keycode.SHIFT", label="Ctrl+Shift+8"),
        KeyConfig(gpio=9, keycode="Keycode.NINE", modifier="Keycode.CONTROL+Keycode.SHIFT", label="Ctrl+Shift+9"),
    ]
    
    default_encoder = EncoderConfig(
        clk_gpio=11,      # WE A = GP11
        dt_gpio=12,       # WE B = GP12  
        sw_gpio=13,       # PUSH = GP13
        scroll_speed=2,
        middle_click=False,  # Zmienione na left click
        debounce_ms=3  # Debouncing inspirowane Arduino
    )
    
    config = PadConfig(keys=default_keys, encoder=default_encoder)
    return config.to_dict()

@app.get("/api/hal/sync")
async def sync_hal_config(direction: str = "from-hal"):
    """Synchronizuj konfigurację HAL."""
    hal_manager = HALConfigManager()
    try:
        if direction == "from-hal":
            config = hal_manager.sync_from_hal()
            return {
                "success": True,
                "message": "Zsynchronizowano z HAL",
                "config": config.to_dict()
            }
        elif direction == "to-hal":
            # Pobierz aktualną konfigurację i zapisz do HAL
            config = hal_manager.get_current_config()
            hal_manager.sync_to_hal(config)
            return {
                "success": True,
                "message": "Zapisano do HAL"
            }
        else:
            return {"success": False, "message": "Nieprawidłowy kierunek"}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.get("/api/hal/validate")
async def validate_hal_config():
    """Waliduj konfigurację HAL."""
    hal_manager = HALConfigManager()
    try:
        hal_config = hal_manager.load_hal_config()
        is_valid, errors = hal_manager.validate_hal_config(hal_config)
        return {
            "valid": is_valid,
            "errors": errors
        }
    except Exception as e:
        return {"valid": False, "errors": [str(e)]}

def create_app():
    """Create and configure FastAPI application."""
    return app

def main():
    """Main entry point for the web application."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

# ============================================================================
# FRONTEND (HTML + JS) - uproszczony
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
        .header { text-align: center; margin-bottom: 20px; }
        .header h1 { color: #333; margin-bottom: 10px; }
        
        /* Tabs */
        .tabs { display: flex; border-bottom: 2px solid #007bff; margin-bottom: 20px; }
        .tab { padding: 12px 24px; cursor: pointer; background: #e9ecef; border: none; border-radius: 4px 4px 0 0; margin-right: 4px; }
        .tab:hover { background: #dee2e6; }
        .tab.active { background: #007bff; color: white; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        
        /* Buttons */
        .btn { padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin: 5px; }
        .btn-primary { background: #007bff; color: white; }
        .btn-success { background: #28a745; color: white; }
        .btn-warning { background: #ffc107; color: black; }
        
        /* Config Editor */
        .config-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; margin: 20px 0; }
        .key-config { background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .key-config h4 { margin-bottom: 10px; color: #333; }
        .form-group { margin-bottom: 10px; }
        .form-group label { display: block; margin-bottom: 5px; font-size: 14px; }
        .form-group select, .form-group input { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
        
        /* Code Output */
        .code-output { background: #1e1e1e; color: #d4d4d4; padding: 20px; border-radius: 8px; font-family: 'Courier New', monospace; white-space: pre-wrap; max-height: 400px; overflow-y: auto; margin: 20px 0; font-size: 13px; }
        
        /* Messages */
        .message { padding: 12px; margin: 10px 0; border-radius: 4px; }
        .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        
        /* Wiring Diagram */
        .wiring-diagram { background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .pin-table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        .pin-table th, .pin-table td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        .pin-table th { background: #f8f9fa; font-weight: 600; }
        
        /* Flash Instructions */
        .flash-steps { background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .flash-steps ol { margin-left: 20px; }
        .flash-steps li { margin: 10px 0; line-height: 1.6; }
        .flash-steps code { background: #f8f9fa; padding: 2px 6px; border-radius: 3px; font-family: monospace; }
        
        /* Test Section */
        .test-area { background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .test-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; max-width: 400px; margin: 20px auto; }
        .test-key { padding: 30px; border: 2px solid #007bff; border-radius: 8px; text-align: center; cursor: pointer; background: white; transition: all 0.2s; position: relative; }
        .test-key:hover { background: #e3f2fd; }
        .test-key:active { background: #007bff; color: white; }
        .test-key.pressed { background: #28a745; color: white; border-color: #28a745; transform: scale(0.95); }
        .test-key .status { position: absolute; top: 5px; right: 5px; font-size: 10px; background: rgba(0,0,0,0.1); padding: 2px 4px; border-radius: 3px; }
        .test-key .timing { position: absolute; bottom: 5px; left: 5px; right: 5px; font-size: 9px; text-align: center; opacity: 0.8; }
        .test-encoder { margin-top: 20px; padding: 20px; border: 2px dashed #28a745; border-radius: 8px; text-align: center; }
        .test-log { background: #f8f9fa; padding: 15px; border-radius: 4px; margin: 20px 0; font-family: monospace; font-size: 12px; max-height: 200px; overflow-y: auto; }
        .test-log .log-entry { margin: 2px 0; padding: 2px 5px; border-radius: 2px; }
        .test-log .press { background: #d4edda; color: #155724; }
        .test-log .release { background: #f8d7da; color: #721c24; }
        .test-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin: 20px 0; }
        .test-stat { background: #e9ecef; padding: 10px; border-radius: 4px; text-align: center; }
        .test-stat .value { font-size: 18px; font-weight: bold; color: #007bff; }
        .test-stat .label { font-size: 12px; color: #666; }
        
        /* Status indicators */
        .status { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 5px; }
        .status.ok { background: #28a745; }
        .status.error { background: #dc3545; }
        .status.warning { background: #ffc107; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎹 RP2040-One/Zero Keypad Configurator</h1>
            <p>Generator kodu CircuitPython dla klawiatury HID + enkoder myszy</p>
        </div>

        <div class="tabs">
            <button class="tab active" onclick="showTab(event, 'config')">⚙️ Konfiguracja</button>
            <button class="tab" onclick="showTab(event, 'wiring')">🔌 Schemat</button>
            <button class="tab" onclick="showTab(event, 'flash')">💾 Wgrywanie</button>
            <button class="tab" onclick="showTab(event, 'test')">🧪 Testowanie</button>
        </div>

        <div id="messages"></div>

        <!-- Tab: Config -->
        <div id="config" class="tab-content active">
            <div style="text-align: center; margin-bottom: 20px;">
                <button class="btn btn-primary" onclick="loadDefault()">📥 Wczytaj domyślną konfigurację</button>
                <button class="btn btn-success" onclick="generateCode()">🚀 Generuj Kod CircuitPython</button>
                <button class="btn btn-warning" onclick="downloadCode()">💾 Pobierz pliki</button>
            </div>
            
            <div class="config-grid" id="keyConfigs">
                <!-- Key configs will be generated here -->
            </div>
            
            <h3 style="margin-top: 30px;">Wygenerowany kod:</h3>
            <div id="codeOutput" class="code-output">Kliknij "Generuj Kod" aby zobaczyć rezultat...</div>
        </div>

        <!-- Tab: Wiring -->
        <div id="wiring" class="tab-content">
            <div class="wiring-diagram">
                <h2>🔌 Schemat podłączeń</h2>
                
                <h3>Przyciski (9 sztuk) → Emulacja klawiatury</h3>
                <table class="pin-table">
                    <tr><th>Przycisk</th><th>GPIO</th><th>Akcja</th><th>Opis</th></tr>
                    <tr><td>Btn 1</td><td>GP1</td><td>Ctrl+Shift+1</td><td>Globalne makro 1</td></tr>
                    <tr><td>Btn 2</td><td>GP2</td><td>Ctrl+Shift+2</td><td>Globalne makro 2</td></tr>
                    <tr><td>Btn 3</td><td>GP3</td><td>Ctrl+Shift+3</td><td>Globalne makro 3</td></tr>
                    <tr><td>Btn 4</td><td>GP4</td><td>Ctrl+Shift+4</td><td>Globalne makro 4</td></tr>
                    <tr><td>Btn 5</td><td>GP5</td><td>Ctrl+Shift+5</td><td>Globalne makro 5</td></tr>
                    <tr><td>Btn 6</td><td>GP6</td><td>Ctrl+Shift+6</td><td>Globalne makro 6</td></tr>
                    <tr><td>Btn 7</td><td>GP7</td><td>Ctrl+Shift+7</td><td>Globalne makro 7</td></tr>
                    <tr><td>Btn 8</td><td>GP8</td><td>Ctrl+Shift+8</td><td>Globalne makro 8</td></tr>
                    <tr><td>Btn 9</td><td>GP9</td><td>Ctrl+Shift+9</td><td>Globalne makro 9</td></tr>
                </table>
                
                <h3>Enkoder obrotowy (KY-040) → Emulacja myszki</h3>
                <table class="pin-table">
                    <tr><th>Pin enkodera</th><th>→ RP2040</th><th>Funkcja</th></tr>
                    <tr><td>CLK (A)</td><td>GP9</td><td>Sygnał A enkodera</td></tr>
                    <tr><td>DT (B)</td><td>GP10</td><td>Sygnał B enkodera</td></tr>
                    <tr><td>SW</td><td>GP11</td><td>Przycisk enkodera (middle-click)</td></tr>
                    <tr><td>+ (VCC)</td><td>3V3</td><td>Zasilanie 3.3V</td></tr>
                    <tr><td>GND</td><td>GND</td><td>Masa</td></tr>
                </table>
                
                <div class="info" style="margin-top: 20px; padding: 15px; background: #e3f2fd; border-radius: 4px;">
                    <strong>💡 Wskazówka:</strong> GP12 i GP13 pozostają wolne — można je wykorzystać w przyszłych rozszerzeniach.
                </div>
            </div>
        </div>

        <!-- Tab: Flash -->
        <div id="flash" class="tab-content">
            <div class="flash-steps">
                <h2>💾 Instrukcja wgrywania firmware</h2>
                
                <h3>Krok 1: Tryb BOOT (RPI-RP2)</h3>
                <ol>
                    <li><strong>Odłącz</strong> RP2040 od komputera</li>
                    <li><strong>Przytrzymaj przycisk BOOT</strong> na płytce</li>
                    <li><strong>Podłącz</strong> kabel USB <strong>trzymając BOOT</strong></li>
                    <li>Zwolnij BOOT — pojawi się dysk <code>RPI-RP2</code></li>
                </ol>
                
                <h3>Krok 2: Wgranie CircuitPython UF2</h3>
                <ol>
                    <li>Skopiuj plik <code>*.uf2</code> na dysk RPI-RP2:
                        <br><code>sudo cp rp2040-one/*.uf2 /media/$USER/RPI-RP2/</code> (dla One)
                        <br><code>sudo cp rp2040-zero/*.uf2 /media/$USER/RPI-RP2/</code> (dla Zero)
                    </li>
                    <li>Płytka automatycznie się zrestartuje</li>
                    <li>Pojawi się dysk <code>CIRCUITPY</code></li>
                </ol>
                
                <h3>Krok 3: Wgranie programu</h3>
                <ol>
                    <li>Skopiuj wygenerowany <code>boot.py</code> i <code>code.py</code> na CIRCUITPY</li>
                    <li>Odłącz i podłącz ponownie USB</li>
                    <li>Sprawdź czy działa: <code>lsusb | grep -i rp2040</code></li>
                </ol>
                
                <h3>Automatyczny deployment</h3>
                <p>Użyj komendy:</p>
                <code>make deploy</code> lub <code>make deploy BOARD=one|zero</code>
            </div>
        </div>

        <!-- Tab: Test -->
        <div id="test" class="tab-content">
            <div class="test-area">
                <h2>🧪 Testowanie klawiszy</h2>
                <p>Wykrywanie naciśnięć klawiszy RP2040 w czasie rzeczywistym:</p>
                
                <div class="test-stats">
                    <div class="test-stat">
                        <div class="value" id="totalPresses">0</div>
                        <div class="label">Liczba naciśnięć</div>
                    </div>
                    <div class="test-stat">
                        <div class="value" id="avgDuration">0ms</div>
                        <div class="label">Średni czas trwania</div>
                    </div>
                    <div class="test-stat">
                        <div class="value" id="lastReaction">0ms</div>
                        <div class="label">Ostatni czas reakcji</div>
                    </div>
                    <div class="test-stat">
                        <div class="value" id="activeKeys">0</div>
                        <div class="label">Aktywne klawisze</div>
                    </div>
                </div>
                
                <div class="test-grid">
                    <div class="test-key" data-key="1">1<br><small>Ctrl+Shift+1</small><div class="status"></div><div class="timing"></div></div>
                    <div class="test-key" data-key="2">2<br><small>Ctrl+Shift+2</small><div class="status"></div><div class="timing"></div></div>
                    <div class="test-key" data-key="3">3<br><small>Ctrl+Shift+3</small><div class="status"></div><div class="timing"></div></div>
                    <div class="test-key" data-key="4">4<br><small>Ctrl+Shift+4</small><div class="status"></div><div class="timing"></div></div>
                    <div class="test-key" data-key="5">5<br><small>Ctrl+Shift+5</small><div class="status"></div><div class="timing"></div></div>
                    <div class="test-key" data-key="6">6<br><small>Ctrl+Shift+6</small><div class="status"></div><div class="timing"></div></div>
                    <div class="test-key" data-key="7">7<br><small>Ctrl+Shift+7</small><div class="status"></div><div class="timing"></div></div>
                    <div class="test-key" data-key="8">8<br><small>Ctrl+Shift+8</small><div class="status"></div><div class="timing"></div></div>
                    <div class="test-key" data-key="9">9<br><small>Ctrl+Shift+9</small><div class="status"></div><div class="timing"></div></div>
                </div>
                
                <div class="test-log" id="testLog">
                    <div style="text-align: center; color: #666;">Oczekiwanie na naciśnięcia klawiszy...</div>
                </div>
                
                <div class="test-encoder">
                    <h4>🖱️ Test enkodera</h4>
                    <p>Obrót enkodera = scroll myszy</p>
                    <p>Wciśnięcie enkodera = middle-click</p>
                </div>
                
                <div class="info" style="margin-top: 20px;">
                    <strong>ℹ️ Uwaga:</strong> Testowanie wymaga podłączonego urządzenia RP2040 z wgranym firmware.
                    <br><strong>ℹ️ Zmiana:</strong> Klawisze używają teraz mapowania Ctrl+Shift+1..9 dla makr globalnych.
                    <br><strong>💡 Podpowiedź:</strong> Taki układ ogranicza kolizje z typowymi skrótami przeglądarki opartymi o same cyfry i klawisze funkcyjne.
                    <br><strong>🔧 Tryb testu:</strong> Symuluje wykrywanie naciśnięć - kliknij klawisz aby przetestować wizualizację.
                </div>
            </div>
        </div>
    </div>

    <script>
        let config = {};
        let generatedCode = '';
        let generatedBoot = '';
        const KEYCODES = ['ONE','TWO','THREE','FOUR','FIVE','SIX','SEVEN','EIGHT','NINE','ZERO','A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z','F1','F2','F3','F4','F5','F6','F7','F8','F9','F10','F11','F12','ENTER','SPACE','TAB','ESCAPE','BACKSPACE','DELETE','UP_ARROW','DOWN_ARROW','LEFT_ARROW','RIGHT_ARROW','HOME','END','PAGE_UP','PAGE_DOWN'];
        const MODIFIERS = ['CONTROL', 'SHIFT', 'CONTROL+SHIFT', 'ALT', 'GUI'];

        function showTab(evt, tabName) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            evt.target.classList.add('active');
            document.getElementById(tabName).classList.add('active');
            // Update URL hash
            window.location.hash = tabName;
        }

        function showTabByName(tabName) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelector(`.tab[onclick*="'${tabName}'"]`).classList.add('active');
            document.getElementById(tabName).classList.add('active');
        }

        // Handle URL hash on page load and hash change
        window.addEventListener('hashchange', () => {
            const tabName = window.location.hash.slice(1) || 'config';
            if (document.getElementById(tabName)) {
                showTabByName(tabName);
            }
        });

        // Load tab from URL on startup
        const initialTab = window.location.hash.slice(1) || 'config';
        if (initialTab !== 'config' && document.getElementById(initialTab)) {
            showTabByName(initialTab);
        }

        async function loadDefault() {
            try {
                const response = await fetch('/api/default');
                config = await response.json();
                renderKeyConfigs();
                showMessage('✅ Domyślna konfiguracja wczytana!', 'success');
            } catch (error) {
                showMessage('❌ Błąd wczytywania: ' + error.message, 'error');
            }
        }

        function renderKeyConfigs() {
            const container = document.getElementById('keyConfigs');
            container.innerHTML = '';
            
            if (!config.keys) return;
            
            config.keys.forEach((key, index) => {
                const div = document.createElement('div');
                div.className = 'key-config';
                div.innerHTML = `
                    <h4>🔘 Przycisk ${index + 1} (GPIO${key.gpio})</h4>
                    <div class="form-group">
                        <label>Klawisz:</label>
                        <select id="key-${index}-keycode" onchange="updateConfig(${index})">
                            ${KEYCODES.map(k => `<option value="Keycode.${k}" ${key.keycode === `Keycode.${k}` ? 'selected' : ''}>${k}</option>`).join('')}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Modyfikator:</label>
                        <select id="key-${index}-modifier" onchange="updateConfig(${index})">
                            <option value="">Brak</option>
                            ${MODIFIERS.map(m => `<option value="${m.split('+').map(part => `Keycode.${part}`).join('+')}" ${key.modifier === m.split('+').map(part => `Keycode.${part}`).join('+') ? 'selected' : ''}>${m}</option>`).join('')}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Etykieta:</label>
                        <input type="text" id="key-${index}-label" value="${key.label || ''}" onchange="updateConfig(${index})">
                    </div>
                `;
                container.appendChild(div);
            });
        }

        function updateConfig(index) {
            if (!config.keys || !config.keys[index]) return;
            config.keys[index].keycode = document.getElementById(`key-${index}-keycode`).value;
            config.keys[index].modifier = document.getElementById(`key-${index}-modifier`).value;
            config.keys[index].label = document.getElementById(`key-${index}-label`).value;
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
                    generatedCode = result.code;
                    generatedBoot = result.boot;
                    document.getElementById('codeOutput').textContent = 
                        '# boot.py\\n' + result.boot + '\\n\\n# code.py\\n' + result.code;
                    showMessage('✅ Kod wygenerowany pomyślnie!', 'success');
                } else {
                    showMessage('❌ Błędy: ' + result.errors.join(', '), 'error');
                }
            } catch (error) {
                showMessage('❌ Błąd generowania: ' + error.message, 'error');
            }
        }

        function downloadCode() {
            if (!generatedCode || !generatedBoot) {
                showMessage('❌ Najpierw wygeneruj kod!', 'error');
                return;
            }
            
            // Download boot.py
            const bootBlob = new Blob([generatedBoot], {type: 'text/x-python'});
            const bootUrl = URL.createObjectURL(bootBlob);
            const bootLink = document.createElement('a');
            bootLink.href = bootUrl;
            bootLink.download = 'boot.py';
            bootLink.click();
            
            // Download code.py
            const codeBlob = new Blob([generatedCode], {type: 'text/x-python'});
            const codeUrl = URL.createObjectURL(codeBlob);
            const codeLink = document.createElement('a');
            codeLink.href = codeUrl;
            codeLink.download = 'code.py';
            codeLink.click();
            
            showMessage('✅ Pliki pobrane!', 'success');
        }

        function testKey(keyNum) {
            showMessage(`🔘 Test przycisku ${keyNum} - wciśnij fizyczny przycisk na płytce`, 'info');
        }

        function showMessage(message, type) {
            const container = document.getElementById('messages');
            const div = document.createElement('div');
            div.className = 'message ' + type;
            div.textContent = message;
            container.appendChild(div);
            setTimeout(() => div.remove(), 5000);
        }

        // Load default on startup
        loadDefault();
    </script>
</body>
</html>
'''

if __name__ == "__main__":
    main()
