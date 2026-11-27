"""Unit and firmware behavior tests for rp2040-keyboard."""

from __future__ import annotations

import ast
import re
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import toml

REPO_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_PANEL9_SWITCHES = [14, 6, 7, 8, 5, 1, 4, 3, 2]
EXPECTED_PANEL9_KEYCODES = [
    "Keycode.SIX",
    "Keycode.TWO",
    "Keycode.THREE",
    "Keycode.FOUR",
    "Keycode.FIVE",
    "Keycode.ONE",
    "Keycode.SEVEN",
    "Keycode.EIGHT",
    "Keycode.NINE",
]
EXPECTED_PANEL9_ENCODER = (0, 15, 26)


class _StopFirmwareLoop(BaseException):
    """Sentinel exception to exit infinite CircuitPython main loops during tests."""


def _run_circuitpython_firmware(source: str, drive_step):
    """Execute CircuitPython firmware source under deterministic fake hardware modules."""
    pins_by_num: dict[int, MagicMock] = {}
    mouse_moves: list[int] = []
    mouse_presses: list[int] = []
    mouse_releases: list[int] = []
    key_presses: list[tuple[int, ...]] = []
    key_releases: list[tuple[int, ...]] = []

    board_mod = types.ModuleType("board")
    for gp in range(30):
        setattr(board_mod, f"GP{gp}", gp)

    class _FakeDigitalInOut:
        def __init__(self, pin_num: int):
            self.pin_num = pin_num
            self.direction = None
            self.pull = None
            self.value = True
            pins_by_num[pin_num] = self

    digitalio_mod = types.ModuleType("digitalio")
    digitalio_mod.DigitalInOut = _FakeDigitalInOut
    digitalio_mod.Direction = types.SimpleNamespace(INPUT="INPUT", OUTPUT="OUTPUT")
    digitalio_mod.Pull = types.SimpleNamespace(UP="UP", DOWN="DOWN")

    class _FakeIncrementalEncoder:
        def __init__(self, clk: int, dt: int):
            if abs(clk - dt) != 1:
                raise ValueError("Pins must be sequential")
            self.position = 0

    rotaryio_mod = types.ModuleType("rotaryio")
    rotaryio_mod.IncrementalEncoder = _FakeIncrementalEncoder

    usb_hid_mod = types.ModuleType("usb_hid")
    usb_hid_mod.devices = object()

    class _FakeKeyboard:
        def __init__(self, _devices):
            pass

        def press(self, *codes):
            key_presses.append(codes)

        def release(self, *codes):
            key_releases.append(codes)

        def release_all(self):
            key_releases.append(("ALL",))

    class _FakeMouse:
        LEFT_BUTTON = 1
        RIGHT_BUTTON = 2
        MIDDLE_BUTTON = 4

        def __init__(self, _devices):
            pass

        def move(self, *, x=0, y=0, wheel=0):
            if wheel:
                mouse_moves.append(wheel)

        def press(self, button):
            mouse_presses.append(button)

        def release(self, button):
            mouse_releases.append(button)

    keycode_cls = type(
        "Keycode",
        (),
        {
            "CONTROL": 0xE0,
            "ALT": 0xE2,
            "SHIFT": 0xE1,
            "GUI": 0xE3,
            "ONE": 0x1E,
            "TWO": 0x1F,
            "THREE": 0x20,
            "FOUR": 0x21,
            "FIVE": 0x22,
            "SIX": 0x23,
            "SEVEN": 0x24,
            "EIGHT": 0x25,
            "NINE": 0x26,
        },
    )

    adafruit_hid_pkg = types.ModuleType("adafruit_hid")
    kb_mod = types.ModuleType("adafruit_hid.keyboard")
    kb_mod.Keyboard = _FakeKeyboard
    kc_mod = types.ModuleType("adafruit_hid.keycode")
    kc_mod.Keycode = keycode_cls
    mouse_mod = types.ModuleType("adafruit_hid.mouse")
    mouse_mod.Mouse = _FakeMouse

    clock = {"t": 0.0, "step": 0}
    fake_time = types.ModuleType("time")

    def _monotonic():
        return clock["t"]

    def _sleep(dt):
        clock["t"] += max(dt, 0.001)
        clock["step"] += 1
        drive_step(clock["step"], clock, pins_by_num)

    fake_time.monotonic = _monotonic
    fake_time.sleep = _sleep

    saved = {}
    injected = {
        "board": board_mod,
        "digitalio": digitalio_mod,
        "rotaryio": rotaryio_mod,
        "usb_hid": usb_hid_mod,
        "adafruit_hid": adafruit_hid_pkg,
        "adafruit_hid.keyboard": kb_mod,
        "adafruit_hid.keycode": kc_mod,
        "adafruit_hid.mouse": mouse_mod,
        "time": fake_time,
    }
    for name, mod in injected.items():
        saved[name] = sys.modules.get(name)
        sys.modules[name] = mod

    try:
        with pytest.raises(_StopFirmwareLoop):
            exec(compile(source, "<circuitpython-firmware>", "exec"), {"__name__": "__main__"})
    finally:
        for name, orig in saved.items():
            if orig is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = orig

    return {
        "pins": pins_by_num,
        "mouse_moves": mouse_moves,
        "mouse_presses": mouse_presses,
        "mouse_releases": mouse_releases,
        "key_presses": key_presses,
        "key_releases": key_releases,
    }


def _drive_encoder_and_switch_scenario(step: int, clock: dict, pins: dict[int, object]) -> None:
    """Simulate CW cycle, CCW cycle, contact bounce, SW6 press, and ENC_SW middle-click."""
    # Gray code (CLK=GP0, DT=GP15): rest is (True, True) == 3
    # CW full cycle: 3 -> 1 -> 0 -> 2 -> 3
    # CCW full cycle: 3 -> 2 -> 0 -> 1 -> 3
    # Bounce: 3 -> 1 -> 3 -> 1 -> 3
    seq = {
        1: (True, True),
        5: (False, True),   # CW 3->1
        6: (False, False),  # CW 1->0
        7: (True, False),   # CW 0->2
        8: (True, True),    # CW 2->3 (+1 tick)
        15: (True, False),  # CCW 3->2
        16: (False, False), # CCW 2->0
        17: (False, True),  # CCW 0->1
        18: (True, True),   # CCW 1->3 (-1 tick)
        25: (False, True),  # Bounce 3->1
        26: (True, True),   # Bounce 1->3
        27: (False, True),  # Bounce 3->1
        28: (True, True),   # Bounce 1->3 (net 0)
    }
    if step in seq:
        clk_val, dt_val = seq[step]
        pins[0].value = clk_val
        pins[15].value = dt_val
        clock["t"] += 0.01  # exceed ENCODER_DEBOUNCE_MS between full cycles

    if step == 30:
        pins[26].value = False  # ENC_SW press
    elif step == 32:
        pins[26].value = True   # ENC_SW release
    elif step == 35:
        pins[1].value = False   # SW6 (GP1 -> Ctrl+Alt+1 / head-deflate) press
    elif step == 37:
        pins[1].value = True    # SW6 release
    elif step >= 80:
        raise _StopFirmwareLoop()


def test_placeholder():
    """Placeholder test to verify the test setup works."""
    assert True


def test_import():
    """Verify the main package can be imported."""
    import rp2040_keyboard  # noqa: F401


def test_hal_models_exports_contract():
    """Verify all models in hal_models are re-exported by hal_manager identically."""
    import rp2040_keyboard.hal_manager as manager
    import rp2040_keyboard.hal_models as models

    symbols = [
        "KeyConfig",
        "EncoderConfig",
        "PadConfig",
        "HALSwitchConfig",
        "HALEncoderConfig",
    ]
    for sym in symbols:
        assert getattr(manager, sym) is getattr(models, sym)


def test_panel9_pinout_consistency_across_firmware_and_hal():
    """Verify static code.py and HAL defaults match panel9.kicad_pcb."""
    code_path = REPO_ROOT / "rp2040_keyboard" / "firmware" / "code.py"
    code_source = code_path.read_text(encoding="utf-8")
    ast.parse(code_source)

    key_matches = re.findall(r"\(board\.GP(\d+),\s*(Keycode\.[A-Z]+)\)", code_source)
    assert [int(gp) for gp, _ in key_matches] == EXPECTED_PANEL9_SWITCHES
    assert [kc for _, kc in key_matches] == EXPECTED_PANEL9_KEYCODES
    assert "ENCODER_CLK_PIN = board.GP0" in code_source
    assert "ENCODER_DT_PIN = board.GP15" in code_source
    assert "ENCODER_SW_PIN = board.GP26" in code_source
    assert "Mouse.MIDDLE_BUTTON" in code_source

    hal_cfg = toml.loads((REPO_ROOT / "hal" / "hal_config.toml").read_text(encoding="utf-8"))
    default_path = REPO_ROOT / "hal" / "profiles" / "default.toml"
    default_cfg = toml.loads(default_path.read_text(encoding="utf-8"))
    for cfg in (hal_cfg, default_cfg):
        switches = [cfg["switches"][f"switch_{i}"] for i in range(1, 10)]
        assert [s["gpio"] for s in switches] == EXPECTED_PANEL9_SWITCHES
        assert [s["keycode"] for s in switches] == EXPECTED_PANEL9_KEYCODES
        assert cfg["encoder"]["clk_gpio"] == 0
        assert cfg["encoder"]["dt_gpio"] == 15
        assert cfg["encoder"]["sw_gpio"] == 26
        assert cfg["encoder"]["middle_click"] is True


def test_static_firmware_handles_nonsequential_gp0_gp15_and_middle_click():
    """Static code.py must survive rotaryio ValueError on GP0/GP15 and decode CW/CCW."""
    code_path = REPO_ROOT / "rp2040_keyboard" / "firmware" / "code.py"
    code_source = code_path.read_text(encoding="utf-8")
    result = _run_circuitpython_firmware(code_source, _drive_encoder_and_switch_scenario)

    assert result["mouse_moves"] == [2, -2]
    assert result["mouse_presses"] == [4]
    assert result["mouse_releases"] == [4]
    assert (0xE0, 0xE2, 0x1E) in result["key_presses"]  # SW6 -> Ctrl+Alt+1 (head-deflate)


def test_generated_firmware_handles_nonsequential_gp0_gp15_and_20ms_debounce():
    """Generated code.py must survive rotaryio ValueError on GP0/GP15 and decode CW/CCW."""
    from rp2040_keyboard.firmware import EncoderConfig, KeyConfig, PadConfig, generate_code_py

    keys = [
        KeyConfig(gpio=gp, keycode=kc, modifier="Keycode.CONTROL+Keycode.ALT")
        for gp, kc in zip(EXPECTED_PANEL9_SWITCHES, EXPECTED_PANEL9_KEYCODES)
    ]
    encoder = EncoderConfig(
        clk_gpio=0,
        dt_gpio=15,
        sw_gpio=26,
        scroll_speed=2,
        middle_click=True,
        debounce_ms=5,
    )
    code = generate_code_py(PadConfig(keys=keys, encoder=encoder))
    ast.parse(code)

    assert code.count("RELEASE_DEBOUNCE_MS = 20") == 1
    result = _run_circuitpython_firmware(code, _drive_encoder_and_switch_scenario)
    assert result["mouse_moves"] == [2, -2]
    assert result["mouse_presses"] == [4]
    assert result["mouse_releases"] == [4]
    assert (0xE0, 0xE2, 0x1E) in result["key_presses"]


def test_panel9_all_nine_switches_match_hui_spatial_grid():
    """Verify all 9 panel9 GPIOs emit Ctrl+Alt shortcuts matching C2004's 4+1+4 grid."""
    code_path = REPO_ROOT / "rp2040_keyboard" / "firmware" / "code.py"
    code_source = code_path.read_text(encoding="utf-8")
    # SW1..SW9 -> digits [6, 2, 3, 4, 5, 1, 7, 8, 9]
    expected_codes = [0x23, 0x1F, 0x20, 0x21, 0x22, 0x1E, 0x24, 0x25, 0x26]

    def _drive_all_switches(step: int, clock: dict, pins: dict[int, object]) -> None:
        idx, phase = divmod(step - 1, 30)
        if idx < len(EXPECTED_PANEL9_SWITCHES):
            gpio = EXPECTED_PANEL9_SWITCHES[idx]
            if phase == 0:
                pins[gpio].value = False
            elif phase == 2:
                pins[gpio].value = True
            clock["t"] += 0.015
        else:
            raise _StopFirmwareLoop()

    result = _run_circuitpython_firmware(code_source, _drive_all_switches)
    assert result["key_presses"] == [(0xE0, 0xE2, kc) for kc in expected_codes]


def test_load_hardware_pins_toml_parses_cleanly():
    """Verify hal/hardware_pins.toml parses without float conversion errors."""
    from rp2040_keyboard.hal_manager import HALConfigManager

    manager = HALConfigManager(project_root=REPO_ROOT)
    pins = manager.load_hardware_pins()
    assert pins, "hardware_pins.toml failed to parse"
    assert pins["global"]["vcc"] == "3.3V"
    assert pins["global"]["gnd"] == "0V"
    for gp in EXPECTED_PANEL9_SWITCHES + list(EXPECTED_PANEL9_ENCODER):
        assert f"pin_{gp}" in pins["pin_mapping"]


def test_deployer_defaults_no_backup_and_mounts_unmounted_boot_device(monkeypatch, tmp_path):
    """deploy.py must default BACKUP_EXISTING_FILES to false and mount unmounted RPI-RP2."""
    sys.path.insert(0, str(REPO_ROOT))
    import deploy

    deployer = deploy.RP2040Deployer()
    deployer.project_root = tmp_path
    deployer.config = {}

    assert deployer._get_setting("BACKUP_EXISTING_FILES", "false") == "false"

    boot_mount = tmp_path / "RPI-RP2"
    boot_mount.mkdir()
    monkeypatch.setattr(deployer, "_find_mounted_label_paths", lambda _label: [])
    monkeypatch.setattr(
        deployer,
        "_find_device_by_label",
        lambda label: "/dev/sda1" if label == "RPI-RP2" else None,
    )
    monkeypatch.setattr(deployer, "mount_boot_device", lambda: str(boot_mount))

    detected = deployer.detect_boot_mode_devices()
    assert len(detected) == 1
    assert detected[0]["path"] == str(boot_mount)
    assert detected[0]["mode"] == "boot"


def test_web_create_app_contract():
    """Verify web package re-exports app and create_app cleanly."""
    from rp2040_keyboard.web import app, create_app

    assert create_app() is app


def test_generated_firmware_encoder_single_hid_report_and_20ms_debounce():
    """Verify generated firmware avoids 100ms bleed, USB floods, and position oscillation."""
    from rp2040_keyboard.firmware import EncoderConfig, KeyConfig, PadConfig, generate_code_py

    config = PadConfig(
        keys=[KeyConfig(gpio=1, keycode="Keycode.ONE", modifier="Keycode.CONTROL+Keycode.ALT")],
        encoder=EncoderConfig(clk_gpio=11, dt_gpio=12, sw_gpio=13, scroll_speed=2, debounce_ms=3),
    )
    code = generate_code_py(config)
    ast.parse(code)
    assert code.count("RELEASE_DEBOUNCE_MS = 20") == 1
    assert "wheel_delta = max(-127, min(127, steps * SCROLL_SPEED))" in code
    assert "mouse.move(wheel=wheel_delta)" in code
    assert "for _ in range(abs(steps)" not in code
    assert "encoder.position = encoder_last_pos" not in code


def test_static_firmware_code_py_contract():
    """Verify firmware/code.py syntax, 20ms release debounce, MIDDLE_BUTTON, and rotaryio."""
    code_path = REPO_ROOT / "rp2040_keyboard" / "firmware" / "code.py"
    source = code_path.read_text(encoding="utf-8")
    ast.parse(source)
    assert "RELEASE_DEBOUNCE_MS = 20" in source
    assert "Mouse.MIDDLE_BUTTON" in source
    assert "Mouse.LEFT_BUTTON" not in source
    assert "rotaryio.IncrementalEncoder" in source
    assert "ENCODER_DEBOUNCE_MS" in source
