import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_MODULE = "rp2040_keyboard.web.app:app"
HOST = "127.0.0.1"
STARTUP_TIMEOUT = 20.0
SHUTDOWN_TIMEOUT = 10.0


@pytest.fixture(scope="session")
def valid_payload():
    return {
        "keys": [
            {"gpio": 1, "keycode": "Keycode.ONE", "modifier": "Keycode.CONTROL+Keycode.SHIFT", "label": "Ctrl+Shift+1"},
            {"gpio": 2, "keycode": "Keycode.TWO", "modifier": "Keycode.CONTROL+Keycode.SHIFT", "label": "Ctrl+Shift+2"},
            {"gpio": 3, "keycode": "Keycode.THREE", "modifier": "Keycode.CONTROL+Keycode.SHIFT", "label": "Ctrl+Shift+3"},
        ],
        "encoder": {
            "clk_gpio": 9,
            "dt_gpio": 10,
            "sw_gpio": 11,
            "scroll_speed": 2,
            "middle_click": True,
            "debounce_ms": 3,
        },
    }


@pytest.fixture(scope="session")
def invalid_payload():
    return {
        "keys": [
            {"gpio": 1, "keycode": "Keycode.ONE", "modifier": "Keycode.CONTROL+Keycode.SHIFT", "label": "Ctrl+Shift+1"},
            {"gpio": 1, "keycode": "Keycode.TWO", "modifier": "Keycode.CONTROL+Keycode.SHIFT", "label": "Ctrl+Shift+2"},
            {"gpio": 50, "keycode": "Keycode.THREE", "modifier": "Keycode.CONTROL+Keycode.SHIFT", "label": "Ctrl+Shift+3"},
        ],
        "encoder": None,
    }


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, 0))
        sock.listen(1)
        return sock.getsockname()[1]


class UvicornServer:
    def __init__(self, port: int, reload_enabled: bool = False):
        self.port = port
        self.reload_enabled = reload_enabled
        self.process = None

    @property
    def base_url(self) -> str:
        return f"http://{HOST}:{self.port}"

    def start(self):
        command = [
            sys.executable,
            "-m",
            "uvicorn",
            APP_MODULE,
            "--host",
            HOST,
            "--port",
            str(self.port),
        ]
        if self.reload_enabled:
            command.append("--reload")

        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        root_str = str(PROJECT_ROOT)
        env["PYTHONPATH"] = root_str if not pythonpath else f"{root_str}:{pythonpath}"

        self.process = subprocess.Popen(
            command,
            cwd=PROJECT_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self._wait_until_ready()
        return self

    def stop(self):
        if self.process is None:
            return
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=SHUTDOWN_TIMEOUT)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=SHUTDOWN_TIMEOUT)
        if self.process.stdout is not None:
            self.process.stdout.close()

    def _wait_until_ready(self):
        deadline = time.time() + STARTUP_TIMEOUT
        last_error = None
        while time.time() < deadline:
            if self.process is not None and self.process.poll() is not None:
                output = ""
                if self.process.stdout is not None:
                    output = self.process.stdout.read()
                raise RuntimeError(f"Uvicorn exited before startup. Output:\n{output}")
            try:
                response = httpx.get(f"{self.base_url}/api/keycodes", timeout=1.0)
                if response.status_code == 200:
                    return
            except (httpx.HTTPError, OSError) as exc:
                last_error = exc
            time.sleep(0.25)
        raise RuntimeError(f"Timed out waiting for server startup: {last_error}")


@pytest.fixture(scope="module")
def web_server():
    server = UvicornServer(port=find_free_port(), reload_enabled=False).start()
    try:
        yield server.base_url
    finally:
        server.stop()


@pytest.fixture(scope="module")
def dev_server():
    server = UvicornServer(port=find_free_port(), reload_enabled=True).start()
    try:
        yield server.base_url
    finally:
        server.stop()


@pytest.mark.e2e
@pytest.mark.parametrize("server_fixture", ["web_server", "dev_server"])
def test_e2e_health_endpoints(server_fixture, request):
    base_url = request.getfixturevalue(server_fixture)

    root_response = httpx.get(f"{base_url}/", timeout=5.0)
    assert root_response.status_code == 200
    assert "text/html" in root_response.headers["content-type"]
    assert "Podejrzane drgania" in root_response.text
    assert "Próg filtracji" in root_response.text
    assert "Status nasłuchu" in root_response.text
    assert "Statystyka klawiszy" in root_response.text
    assert "Naciśnięcia" in root_response.text
    assert "Odrzucone" in root_response.text

    keycodes_response = httpx.get(f"{base_url}/api/keycodes", timeout=5.0)
    assert keycodes_response.status_code == 200
    data = keycodes_response.json()
    assert "keycodes" in data
    assert "modifiers" in data
    assert "available_gpios" in data
    assert len(data["keycodes"]) > 0


@pytest.mark.e2e
@pytest.mark.parametrize("server_fixture", ["web_server", "dev_server"])
def test_e2e_default_config(server_fixture, request):
    base_url = request.getfixturevalue(server_fixture)

    response = httpx.get(f"{base_url}/api/default", timeout=5.0)
    assert response.status_code == 200
    data = response.json()
    assert "keys" in data
    assert "encoder" in data
    assert len(data["keys"]) > 0


@pytest.mark.e2e
@pytest.mark.parametrize("server_fixture", ["web_server", "dev_server"])
def test_e2e_validate_and_generate(server_fixture, request, valid_payload, invalid_payload):
    base_url = request.getfixturevalue(server_fixture)

    valid_response = httpx.post(f"{base_url}/api/validate", json=valid_payload, timeout=5.0)
    assert valid_response.status_code == 200
    valid_data = valid_response.json()
    assert valid_data["valid"] is True
    assert valid_data["errors"] == []

    invalid_response = httpx.post(f"{base_url}/api/validate", json=invalid_payload, timeout=5.0)
    assert invalid_response.status_code == 200
    invalid_data = invalid_response.json()
    assert invalid_data["valid"] is False
    assert len(invalid_data["errors"]) > 0

    generate_response = httpx.post(f"{base_url}/api/generate", json=valid_payload, timeout=5.0)
    assert generate_response.status_code == 200
    generated = generate_response.json()
    assert generated["valid"] is True
    assert generated["errors"] == []
    assert generated["code"]
    assert generated["boot"]
