# HAL Configuration Directory
# ==========================

This directory contains Hardware Abstraction Layer (HAL) configuration files for the RP2040-One keyboard project.

## Files

- `hal_config.toml` - Main HAL configuration (switches, encoder, device settings)
- `hardware_pins.toml` - Detailed pin mapping and hardware specifications
- `profiles/` - Different hardware profiles (optional)
- `backups/` - Automatic backups of HAL configurations

## Usage

```bash
# Show current HAL configuration
make hal-show

# Edit configuration
nano hal/hal_config.toml

# Sync with firmware
make hal-sync

# Validate configuration
make hal-validate
```

## HAL Structure

The HAL layer abstracts hardware details from firmware:

```
Application Layer
    ↓
HAL Configuration (hal/*.toml)
    ↓
Firmware Generator
    ↓
Hardware (RP2040-One)
```

## Configuration Format

TOML format provides human-readable, version-controllable hardware configuration suitable for embedded systems development.
