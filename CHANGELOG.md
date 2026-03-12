# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.12] - 2026-03-12

### Docs
- Update DEPLOYMENT_HAL.md
- Update FIRST_TIME_SETUP.md
- Update PROJECT_STRUCTURE.md
- Update README.md

### Test
- Update test_ctrl_shift_1_debug.py
- Update test_shortcuts.py
- Update tests/test_web_e2e.py

### Other
- Update hal/hal_config.toml
- Update hal/profiles/default.toml
- Update hal/profiles/minimal.toml
- Update keyscan.html
- Update keyscan.py
- Update rp2040_keyboard/firmware/code.py
- Update rp2040_keyboard/hal_manager.py
- Update rp2040_keyboard/web/app.py

## [0.0.11] - 2026-03-12

### Docs
- Update DEPLOYMENT_HAL.md
- Update FIRST_TIME_SETUP.md
- Update PROJECT_STRUCTURE.md
- Update README.md

### Test
- Update test_ctrl_shift_1_debug.py
- Update tests/test_web_e2e.py

### Other
- Update .hal_sync.json
- Update Makefile
- Update hal/hal_config.toml
- Update hal/profiles/minimal.toml
- Update rp2040_keyboard/firmware/code.py
- Update rp2040_keyboard/web/app.py

## [0.0.10] - 2026-03-12

### Docs
- Update README.md

### Test
- Update test_shortcuts.py
- Update tests/test_all.py
- Update tests/test_web_e2e.py

### Other
- Update .hal_sync.json
- Update hal/hal_config.toml
- Update hal/profiles/default.toml
- Update rp2040_keyboard/firmware/code.py
- Update rp2040_keyboard/firmware/generator.py
- Update rp2040_keyboard/firmware/validator.py
- Update rp2040_keyboard/hal_manager.py
- Update rp2040_keyboard/web/app.py

## [0.0.9] - 2026-03-12

### Docs
- Update README.md

### Test
- Update tests/test_web_e2e.py

### Other
- Update .hal_sync.json
- Update Makefile
- Update deploy.py
- Update hal/hal_config.toml
- Update rp2040-one/adafruit-circuitpython-waveshare_rp2040_one-pl-10.1.4.uf2
- Update rp2040-one/circuitpython-waveshare_rp2040_one-en_US-9.2.0.uf2
- Update rp2040-zero/adafruit-circuitpython-waveshare_rp2040_zero-pl-10.1.4.uf2
- Update rp2040_keyboard/web/app.py

## [0.0.8] - 2026-03-12

### Docs
- Update FIRST_TIME_SETUP.md

### Test
- Update tests/test_all.py

### Other
- Update Makefile
- Update adafruit-circuitpython-waveshare_rp2040_one-pl-10.1.4.uf2.backup
- Update circuitpython-waveshare_rp2040_one-en_US-9.2.0.uf2
- Update deploy.py
- Update requirements.txt
- Update rp2040_keyboard/firmware/boot_template.py
- Update rp2040_keyboard/firmware/generator.py
- Update rp2040_keyboard/web/app.py

## [0.0.7] - 2026-03-12

### Docs
- Update CHANGELOG.md
- Update DEPLOYMENT.md
- Update FIRST_TIME_SETUP.md
- Update README.md

### Other
- Update deploy.py
- Update web/__init__.py
- Update web/app.py

## [0.0.6] - 2026-03-12

### Added
- **Intelligent device detection**: Automatic BOOT/CIRCUITPY mode recognition
- **Auto-flashing firmware**: Automatic CircuitPython installation for fresh devices
- **Auto-mounting system**: System-level device mounting with udisksctl
- **One-command setup**: `make deploy` handles everything automatically
- **First-time setup guide**: Complete guide for new RP2040 devices

### Changed
- **GP13 button action**: Changed from middle click to left click mouse button
- **Deployment system**: Enhanced with smart device detection
- **HAL integration**: Web configurator uses HAL as source of truth
- **Firmware generation**: Now generates from HAL configuration instead of static files

### Docs
- Update DEPLOYMENT_HAL.md
- Update PROJECT_STRUCTURE.md  
- Update README.md
- Add FIRST_TIME_SETUP.md
- Add DEPLOYMENT_V2.md

### Other
- Update .hal_sync.json
- Update Makefile
- Update deploy.py with new mounting and flashing functions
- Update hal_manager.py with new directory structure
- Update hal/hal_config.toml
- Update hal/profiles/default.toml
- Update hal/profiles/gaming.toml
- Update hal/profiles/minimal.toml
- Update rp2040_keyboard/__init__.py
- Update rp2040_keyboard/firmware/generator.py
- Update rp2040_keyboard/hal_manager.py
- ... and 1 more files

## [0.0.5] - 2026-03-12

### Docs
- Update DEPLOYMENT.md
- Update README.md
- Update hal/README.md

### Other
- Update .hal_sync.json
- Update Makefile
- Update auto-deploy.sh
- Update boot-monitor.py
- Update deploy.py
- Update firmware/boot.py
- Update firmware/code.py
- Update hal/hal_config.toml
- Update hal/hardware_pins.toml
- Update hal_manager.py
- ... and 2 more files

## [0.0.4] - 2026-03-12

### Docs
- Update docs/ec12.pdf
- Update docs/enkoder-24-imp-l15mm-z-przyc-ec12-145.pdf
- Update docs/enkoder-24-impulsy-przycisk-ec12-l-20-356.pdf
- Update docs/enkoder-30-imp-l15mm-z-przyc-ec12.pdf
- Update docs/iduino_rotary_sensor.ino

### Test
- Update tests/test_all.py

### Other
- Update .gitignore
- Update Rotation_Sensor.ino
- Update adafruit-circuitpython-waveshare_rp2040_one-pl-10.1.4.uf2
- Update deploy.py
- Update rp2040_keyboard/firmware/generator.py
- Update rp2040_keyboard/firmware/validator.py
- Update rp2040_keyboard/web/app.py
- Update web/app.py

## [0.0.3] - 2026-03-12

### Test
- Update tests/test_all.py

### Other
- Update rp2040_keyboard/__init__.py
- Update rp2040_keyboard/firmware/__init__.py
- Update rp2040_keyboard/firmware/boot.py
- Update rp2040_keyboard/firmware/boot_template.py
- Update rp2040_keyboard/firmware/code.py
- Update rp2040_keyboard/firmware/generator.py
- Update rp2040_keyboard/firmware/validator.py
- Update rp2040_keyboard/web/__init__.py
- Update rp2040_keyboard/web/app.py
- Update web/app.py

## [0.0.2] - 2026-03-12

### Docs
- Update README copy.md
- Update README.md

### Test
- Update test_all.py
- Update tests/test_rp2040_keyboard.py

### Other
- Update app.py
- Update docker/Dockerfile
- Update docker/Dockerfile.test
- Update docker/docker-compose.test.yml
- Update docker/docker-compose.yml
- Update firmware/boot.py
- Update firmware/code.py
- Update requirements.txt
- Update web/__init__.py

## [0.0.1] - 2026-03-12

### Docs
- Update README copy.md

### Test
- Update test_all.py

### Other
- Update .gitignore
- Update Dockerfile.test
- Update Makefile
- Update app.py
- Update boot.py
- Update code.py
- Update docker-compose.test.yml
- Update project.sh

