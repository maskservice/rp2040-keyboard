# RP2040 Auto-Deployment System
# =============================

Automatyczny system pobierania bibliotek i deploymentu firmware na urządzenia RP2040-One z **HAL (Hardware Abstraction Layer)**.

## 🚀 Szybki start

### 1. Jednorazowy deployment
```bash
# Podłącz RP2040-One i uruchom
make deploy
# lub
python3 deploy.py deploy
# lub
./auto-deploy.sh start
```

### 2. Monitorowanie i auto-deployment
```bash
# Uruchom monitorowanie - automatycznie wykryje i zdeployuje
make deploy-monitor
# lub
python3 deploy.py monitor
# lub  
./auto-deploy.sh monitor
```

### 3. Przygotowanie bibliotek
```bash
# Pobierz wymagane biblioteki (jednorazowo)
make deploy-setup
# lub
python3 deploy.py setup
```

## 📋 Konfiguracja

### HAL Configuration Files
Projekt używa **HAL (Hardware Abstraction Layer)** do oddzielenia konfiguracji sprzętowej od kodu firmware:

```bash
# Główna konfiguracja sprzętowa
hal/hal_config.toml

# Profile konfiguracyjne
hal/profiles/default.toml   # Standard 9-key + encoder
hal/profiles/minimal.toml   # Minimal 4-key + encoder  
hal/profiles/gaming.toml    # Gaming WASD + fast encoder

# Szczegółowa specyfikacja sprzętowa
hal/hardware_pins.toml
```

### Plik .env
Skopiuj `.env.example` do `.env` i dostosuj:

```bash
cp .env.example .env
```

Główne opcje:
- `AUTO_DEPLOY_ENABLED=true` - Włącz auto-deployment
- `AUTO_DEPLOY_ON_BOOT=true` - Deploy przy starcie
- `BACKUP_EXISTING_FILES=true` - Backupuj istniejące pliki
- `LIBRARY_CACHE_DIR=./lib_cache` - Katalog na biblioteki
- `SYNC_HAL_BEFORE_DEPLOY=true` - Synchronizuj HAL przed deploymentem

## 🔧 Dostępne komendy

### Makefile
```bash
make deploy          # Jednorazowy deployment
make deploy-monitor  # Monitorowanie urządzeń
make deploy-setup    # Pobierz biblioteki
make deploy-detect   # Wykryj urządzenia
```

### HAL Configuration
```bash
make hal-sync        # Synchronizuj HAL → Firmware
make hal-save        # Zapisz Firmware → HAL
make hal-validate    # Waliduj konfigurację HAL
make hal-show        # Pokaż konfigurację HAL
make hal-profiles    # Lista dostępnych profili
make hal-apply PROFILE=default  # Zastosuj profil
make hal-backup      # Stwórz backup konfiguracji
```

### Skrypty
```bash
./auto-deploy.sh start    # Jednorazowy deployment
./auto-deploy.sh monitor  # Monitorowanie
./auto-deploy.sh setup    # Pobierz biblioteki
./auto-deploy.sh detect   # Wykryj urządzenia
```

### Python
```bash
python3 deploy.py deploy    # Jednorazowy deployment
python3 deploy.py monitor  # Monitorowanie
python3 deploy.py setup     # Pobierz biblioteki
python3 deploy.py detect    # Wykryj urządzenia

python3 -m rp2040_keyboard.hal_manager sync-from-hal  # HAL sync
```

## 📁 Struktura po deploymentu

```
CIRCUITPY/
├── boot.py              # Nasz firmware startowy
├── code.py              # Główny program klawiatury (generowany z HAL)
└── lib/
    └── adafruit_hid/    # Biblioteka HID (pobrana automatycznie)
        ├── __init__.py
        ├── keyboard.py
        ├── mouse.py
        └── ...
```

## 🔍 Jak to działa

### HAL Integration
1. **Configuration in TOML**: Hardware settings defined in `hal/*.toml` files
2. **Automatic Sync**: HAL configuration synchronized before deployment
3. **Code Generation**: Firmware generated dynamically from HAL configuration
4. **Profile System**: Easy switching between hardware configurations

### Deployment Process
1. **Device Detection**: Scans for CircuitPython devices on common mount points
2. **HAL Synchronization**: Reads and validates HAL configuration
3. **Firmware Generation**: Generates `boot.py` and `code.py` from HAL settings
4. **Library Management**: Downloads and installs required libraries
5. **Backup**: Creates backups of existing files
6. **Installation**: Copies generated firmware and libraries to device

### HAL Configuration Example
```toml
[device]
name = "RP2040-One-Keypad"
version = "1.0"

[encoder]
enabled = true
clk_gpio = 11      # WE A signal
dt_gpio = 12       # WE B signal  
sw_gpio = 13       # PUSH button
middle_click = false  # Uses left click instead of middle
debounce = 3
scroll_speed = 2

[switches]
switch_1 = {gpio = 1, keycode = "Keycode.ONE", modifier = "Keycode.CONTROL+Keycode.SHIFT", label = "Ctrl+Shift+1"}
switch_2 = {gpio = 2, keycode = "Keycode.TWO", modifier = "Keycode.CONTROL+Keycode.SHIFT", label = "Ctrl+Shift+2"}
# ... more switches
```

## 🔄 Development Workflow

### 1. Configure Hardware
```bash
# Edit HAL configuration
nano hal/hal_config.toml

# Or use a profile
make hal-apply PROFILE=gaming
```

### 2. Validate Configuration
```bash
make hal-validate
```

### 3. Generate and Deploy
```bash
make deploy
```

### 4. Monitor and Auto-deploy
```bash
make deploy-monitor
```

## 🎯 HAL Profiles

### Available Profiles
- **default**: 9 keys (Ctrl+Shift+1..Ctrl+Shift+9) + encoder with left click
- **minimal**: 4 keys + encoder (GPIO efficient)
- **gaming**: WASD + functions + fast encoder

### Profile Management
```bash
make hal-profiles              # List profiles
make hal-apply PROFILE=gaming # Apply profile
make hal-backup               # Backup current config
make hal-save                 # Save current as profile
```

## 🔧 Troubleshooting

### Brak wykrytych urządzeń
```bash
# Sprawdź ręcznie
ls /media/*/CIRCUITPY 2>/dev/null || ls /mnt/*/CIRCUITPY 2>/dev/null

# Sprawdź HAL konfigurację
make hal-show
```

### Błędy synchronizacji HAL
```bash
# Waliduj konfigurację
make hal-validate

# Sprawdź profile
make hal-profiles

# Resetuj synchronizację
rm .hal_sync.json
make hal-sync
```

### Problemy z bibliotekami
```bash
# Wyczyść cache i pobierz ponownie
rm -rf lib_cache/
make deploy-setup
```

### Konflikty GPIO
```bash
# Sprawdź walidację
make hal-validate

# Pokaż szczegóły
python3 -m rp2040_keyboard.hal_manager show
```

## 📝 Logi

System tworzy logi w:
- `backups/` - Backupy plików przed deploymentem
- `hal/backups/` - Backupy konfiguracji HAL
- `lib_cache/` - Pobrane biblioteki
- `.hal_sync.json` - Stan synchronizacji HAL

## 🎯 Podsumowanie

System zapewnia:
- ✅ **Automatyczne pobieranie** bibliotek
- ✅ **Detekcję urządzeń** CircuitPython  
- ✅ **HAL-based configuration** - oddzielenie sprzętu od kodu
- ✅ **Profile system** - szybkie przełączanie konfiguracji
- ✅ **Automatyczny deployment** firmware generowanego z HAL
- ✅ **Backup** istniejących plików
- ✅ **Monitorowanie** w tle
- ✅ **Start przy boot** systemu

### HAL Benefits
- **Hardware Abstraction**: Separate hardware config from firmware code
- **Version Control**: TOML files can be versioned and tracked
- **Multiple Profiles**: Easy switching between configurations
- **Validation**: Automatic checking of GPIO conflicts and constraints
- **Professional Structure**: Industry-standard embedded systems approach

Podłącz RP2040-One a system automatycznie zainstaluje wszystko co potrzebne na podstawie konfiguracji HAL! 🚀
