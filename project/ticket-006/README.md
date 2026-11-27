# Ticket 006: Align `panel9` physical switch keymap (`SW1..SW9`) with C2004 HUI layout

- **ID**: ticket-006
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-27

## Goal and scope

Fix the 0/9 spatial mismatch between the `panel9` PCB (`SW1..SW9` on `GP14, GP6, GP7, GP8, GP5, GP1, GP4, GP3, GP2`) and the C2004 `test-hui` 4+1+4 button layout (`[6, 2, 3, 4, 5, 1, 7, 8, 9]`), and quote unit strings (`"3.3V"`, `"0V"`) in `hal/hardware_pins.toml` so `HALConfigManager.load_hardware_pins()` parses cleanly.

## Acceptance criteria

- [x] AC-01: `KEY_PINS` in `rp2040_keyboard/firmware/code.py`, `hal/hal_config.toml`, `hal/profiles/default.toml`, `hal/hardware_pins.toml`, `rp2040_keyboard/hal_manager.py`, and `rp2040_keyboard/web/app.py` map `SW1..SW9` to `Ctrl+Alt+6, 2, 3, 4, 5, 1, 7, 8, 9`.
- [x] AC-02: `hal/hardware_pins.toml` parses cleanly without TOML float conversion errors.
- [x] AC-03: `make lint`, `pytest`, `hal_manager validate`, and `nohardcode_check.py` pass.
