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

# ============================================================================
# APLIKACJA FASTAPI
# ============================================================================

app = FastAPI(
    title="RP2040-One Keypad Configurator",
    description="Visual pin editor and code generator for RP2040-One HID keypad",
    version="0.0.2"
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
        KeyConfig(gpio=9, keycode="Keycode.NINE", modifier="Keycode.CONTROL", label="Ctrl+9"),  # Zmiana z GP29 na GP9
    ]
    
    default_encoder = EncoderConfig(
        clk_gpio=11,      # WE A = GP11
        dt_gpio=12,       # WE B = GP12  
        sw_gpio=13,       # PUSH = GP13
        scroll_speed=2,
        middle_click=True,
        debounce_ms=3  # Debouncing inspirowane Arduino
    )
    
    config = PadConfig(keys=default_keys, encoder=default_encoder)
    return config.to_dict()

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
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { color: #333; margin-bottom: 10px; }
        .btn { padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin: 5px; }
        .btn-primary { background: #007bff; color: white; }
        .btn-success { background: #28a745; color: white; }
        .code-output { background: #1e1e1e; color: #d4d4d4; padding: 20px; border-radius: 8px; font-family: monospace; white-space: pre-wrap; max-height: 400px; overflow-y: auto; margin: 20px 0; }
        .message { padding: 10px; margin: 10px 0; border-radius: 4px; }
        .success { background: #d4edda; color: #155724; }
        .error { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎹 RP2040-One Keypad Configurator</h1>
            <p>Generator kodu CircuitPython dla klawiatury HID</p>
        </div>

        <div>
            <button class="btn btn-primary" onclick="loadDefault()">📥 Wczytaj domyślną konfigurację</button>
            <button class="btn btn-success" onclick="generateCode()">🚀 Generuj Kod</button>
        </div>

        <div id="messages"></div>
        <div id="codeOutput" class="code-output">Kliknij "Generuj Kod" aby zobaczyć rezultat...</div>
    </div>

    <script>
        let config = {};

        async function loadDefault() {
            try {
                const response = await fetch('/api/default');
                config = await response.json();
                showMessage('Domyślna konfiguracja wczytana!', 'success');
            } catch (error) {
                showMessage('Błąd wczytywania: ' + error.message, 'error');
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
                } else {
                    showMessage('Błędy: ' + result.errors.join(', '), 'error');
                }
            } catch (error) {
                showMessage('Błąd generowania: ' + error.message, 'error');
            }
        }

        function showMessage(message, type) {
            const container = document.getElementById('messages');
            const div = document.createElement('div');
            div.className = 'message ' + type;
            div.textContent = message;
            container.appendChild(div);
            setTimeout(() => div.remove(), 5000);
        }
    </script>
</body>
</html>
'''

if __name__ == "__main__":
    main()
