# RP2040 Keyboard Project Structure
# =================================

Professional embedded systems project with HAL (Hardware Abstraction Layer), 
auto-deployment, and comprehensive configuration management.

## 📁 Directory Structure

```
rp2040-keyboard/
├── 📋 Project Root
│   ├── README.md                 # Main project documentation
│   ├── CHANGELOG.md              # Version history
│   ├── DEPLOYMENT.md             # Deployment guide
│   ├── Makefile                  # Build automation
│   ├── pyproject.toml            # Python package config
│   ├── VERSION                   # Current version
│   │
│   ├── 🤖 Automation & Deployment
│   │   ├── deploy.py             # Auto-deployment system
│   │   ├── boot-monitor.py       # Boot-time monitoring
│   │   ├── auto-deploy.sh        # Deployment wrapper
│   │   ├── lib_cache/            # Downloaded libraries
│   │   └── backups/              # Deployment backups
│   │
│   ├── ⚙️ HAL Configuration
│   │   └── hal/                  # Hardware Abstraction Layer
│   │       ├── README.md         # HAL documentation
│   │       ├── hal_config.toml   # Main hardware config
│   │       ├── hardware_pins.toml # Pin mapping & specs
│   │       ├── profiles/         # Predefined configurations
│   │       │   ├── default.toml  # Standard 9-key layout
│   │       │   ├── minimal.toml  # Minimal 4-key layout
│   │       │   └── gaming.toml   # Gaming WASD layout
│   │       └── backups/          # HAL configuration backups
│   │
│   ├── 🐍 Python Package
│   │   └── rp2040_keyboard/      # Main Python package
│   │       ├── __init__.py       # Package metadata
│   │       ├── hal_manager.py    # HAL configuration manager
│   │       ├── firmware/         # Firmware generation
│   │       │   ├── __init__.py
│   │       │   ├── generator.py  # Code generator
│   │       │   ├── validator.py  # Configuration validation
│   │       │   └── boot_template.py
│   │       └── web/              # Web configurator
│   │           ├── __init__.py
│   │           └── app.py        # FastAPI application
│   │
│   ├── 🧪 Testing
│   │   └── tests/                # Test suite
│   │       ├── test_all.py       # Comprehensive tests
│   │       └── test_rp2040_keyboard.py
│   │
│   ├── 🐳 Docker
│   │   └── docker/               # Container configurations
│   │       ├── docker-compose.yml
│   │       ├── Dockerfile.web
│   │       └── Dockerfile.test
│   │
│   ├── 📚 Documentation
│   │   └── docs/                 # Additional docs
│   │
│   └── 🔧 Configuration Files
│       ├── .env.example          # Environment template
│       ├── goal.yaml             # CI/CD automation
│       └── requirements.txt      # Python dependencies
```

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface Layer                      │
├─────────────────────────────────────────────────────────────┤
│  Web Configurator (FastAPI) │ HAL Manager │ CLI Tools       │
│         ↓ HAL Integration                                      │
├─────────────────────────────────────────────────────────────┤
│                Hardware Abstraction Layer (HAL)              │
├─────────────────────────────────────────────────────────────┤
│  hal_config.toml │ Profiles │ Validation │ Sync System      │
│         ↓ Firmware Generation                                   │
├─────────────────────────────────────────────────────────────┤
│                   Firmware Generation Layer                  │
├─────────────────────────────────────────────────────────────┤
│  Code Generator │ Validator │ Template Engine               │
├─────────────────────────────────────────────────────────────┤
│                    Target Hardware Layer                     │
└─────────────────────────────────────────────────────────────┘
│              RP2040-One + Switches + Encoder               │
```

## 🎯 Key Components

### **HAL (Hardware Abstraction Layer)**
- **Purpose**: Separate hardware configuration from firmware logic
- **Files**: `hal/*.toml` files with hardware specifications
- **Benefits**: Easy reconfiguration, multiple profiles, version control

### **Auto-Deployment System**
- **Purpose**: Automatic library download and device flashing
- **Features**: Device detection, backup, library management
- **Usage**: `make deploy` or `make deploy-monitor`

### **Firmware Generator**
- **Purpose**: Generate CircuitPython code from HAL configuration
- **Features**: Conditional imports, optimized encoder handling
- **Output**: Ready-to-flash `boot.py` and `code.py`

### **Web Configurator**
- **Purpose**: Visual interface for configuration
- **Features**: Pin editor, real-time validation, code preview
- **API**: RESTful endpoints for integration

## 🚀 Quick Start

```bash
# 1. Setup development environment
make setup

# 2. Configure hardware (optional)
nano hal/hal_config.toml

# 3. Generate firmware
make web  # Open configurator at http://localhost:8080

# 4. Deploy to device
make deploy

# 5. Monitor and auto-deploy
make deploy-monitor
```

## 🔧 HAL Profiles

### Available Profiles
- **default**: 9 keys (Ctrl+1..9) + encoder
- **minimal**: 4 keys + encoder (GPIO efficient)
- **gaming**: WASD + functions + fast encoder

### Profile Management
```bash
make hal-profiles              # List profiles
make hal-apply PROFILE=gaming # Apply profile
make hal-backup               # Backup current config
```

## 📦 Package Structure

The project follows Python packaging best practices:

- **Package**: `rp2040_keyboard`
- **Entry Points**: `rp2040_keyboard.web`, `rp2040_keyboard.hal_manager`
- **Dependencies**: Managed via `pyproject.toml`
- **Testing**: `pytest` with comprehensive coverage

## 🔄 Development Workflow

1. **Edit HAL Configuration**: `hal/hal_config.toml`
2. **Validate**: `make hal-validate`
3. **Generate Code**: `make web` or CLI tools
4. **Test**: `make test`
5. **Deploy**: `make deploy`
6. **Version**: `goal -a` (automatic)

## 🎨 Design Principles

- **Separation of Concerns**: HAL vs Firmware vs Application
- **Configuration as Code**: TOML files version controlled
- **Automation First**: Minimal manual steps
- **Professional Structure**: Industry-standard organization
- **Extensibility**: Easy to add new profiles and features

This structure provides a solid foundation for embedded systems development with proper abstraction layers and automation.
