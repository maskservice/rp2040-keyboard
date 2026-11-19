# Ticket 005: Align RP2040-Zero firmware and HAL with `panel9` PCB and fix non-sequential encoder decoding

- **ID**: ticket-005
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-19

## Goal and scope

Align `maskservice/rp2040-keyboard` firmware, HAL defaults, generator, and deployer with the `maskservice/viewer` `panel9` RP2040-Zero PCB (`SW1..SW9 = GP14, GP6, GP7, GP8, GP5, GP1, GP4, GP3, GP2`, `ENC_A=GP0, ENC_B=GP15, ENC_SW=GP26`, `Mouse.MIDDLE_BUTTON`), add a Gray-code `digitalio` quadrature fallback when `rotaryio.IncrementalEncoder` raises `ValueError` for non-sequential pins (`GP0`/`GP15`), and fix `deploy.py` unmounted `RPI-RP2` auto-mount and no-backup dev default.

## Acceptance criteria

- [x] AC-01: `rp2040_keyboard/firmware/code.py`, `hal/hal_config.toml`, `hal/hardware_pins.toml`, `hal/profiles/default.toml`, `hal_models.py`, `hal_manager.py`, and `web/app.py` reflect the exact `panel9` PCB pinout and `Mouse.MIDDLE_BUTTON`.
- [x] AC-02: Both static `code.py` and `generate_code_py()` handle non-sequential encoder GPIOs (`GP0`, `GP15`) via `_QUAD_TABLE` fallback without crashing on `ValueError` and debounce encoder steps cleanly.
- [x] AC-03: `deploy.py` mounts unmounted `/dev/disk/by-label/RPI-RP2` via `udisksctl` and defaults `BACKUP_EXISTING_FILES` to `'false'` per dev no-backup policy.
- [x] AC-04: `pytest tests/` passes completely.
