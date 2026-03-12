# RP2040 Auto-Deployment System (v0.0.6+)
# =========================================

Automatyczny system pobierania bibliotek i deploymentu firmware na urządzenia RP2040-One z **inteligentnym wykrywaniem trybów** i **auto-flashowaniem**.

## 🚀 Szybki start

### 1. Inteligentny deployment (v0.0.6+)
```bash
# Podłącz RP2040-One i uruchom - system sam wykryje tryb
make deploy
# lub
python3 deploy.py deploy
```

System automatycznie:
- ✅ Wykryje tryb BOOT (RPI-RP2) lub CIRCUITPY
- ✅ Wgra firmware CircuitPython jeśli potrzebne
- ✅ Wgra aplikację z konfiguracją HAL
- ✅ Skonfiguruje biblioteki

### 2. Monitorowanie i auto-deployment
```bash
# Uruchom monitorowanie - automatycznie wykryje i zdeployuje
make deploy-monitor
# lub
python3 deploy.py monitor
# or  
./auto-deploy.sh monitor
```

### 3. Przygotowanie bibliotek
```bash
# Pobierz wymagane biblioteki (jednorazowo)
make deploy-setup
# lub
python3 deploy.py setup
```

## 🔧 Nowe Funkcje v0.0.6

### 🧠 Inteligentna Detekcja Trybów
System rozróżnia automatycznie:

| Tryb urządzenia | Nazwa folderu | Akcja systemu |
|-----------------|---------------|---------------|
| **Fabryczny/BOOT** | `RPI-RP2` | Flash firmware CircuitPython |
| **Z aplikacją** | `CIRCUITPY` | Deploy aplikacji z HAL |

### 🔄 Auto-Mounting
```bash
# Automatycznie montuje niezamontowane urządzenia CIRCUITPY
# Używa udisksctl systemowe
# Fallback do manualnego montowania
```

### 🔥 Auto-Flashing Firmware
```bash
# Dla świeżych RP2040 automatycznie:
# 1. Znajdzie plik .uf2 w projekcie
# 2. Skopiuje do RPI-RP2
# 3. Poczeka na restart do CIRCUITPY
# 4. Kontynuuje deployment aplikacji
```

## 📋 Konfiguracja

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
make deploy          # Inteligentny deployment (BOOT/CIRCUITPY)
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
python3 deploy.py deploy    # Inteligentny deployment
python3 deploy.py monitor  # Monitorowanie
python3 deploy.py setup     # Pobierz biblioteki
python3 deploy.py detect    # Wykryj urządzenia
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

## 🔍 Jak to działa (v0.0.6+)

### Inteligentny Process Flow
1. **Device Detection**: Skanuje dla RPI-RP2 (BOOT) i CIRCUITPY
2. **Mode Recognition**: Automatycznie rozpoznaje tryb urządzenia
3. **Auto-Flash** (jeśli BOOT): Wgrywa firmware CircuitPython
4. **HAL Sync**: Odczytuje i waliduje konfigurację HAL
5. **Firmware Generation**: Generuje `boot.py` i `code.py` z HAL
6. **Library Management**: Pobiera i instaluje biblioteki
7. **Installation**: Kopiuje firmware na urządzenie

### Auto-Mounting System
```python
# Sprawdza /dev/disk/by-label/CIRCUITPY
# Używa udisksctl do systemowego montowania
# Fallback: sudo mount /dev/sdX1 /media/tom/CIRCUITPY
```

### Auto-Flashing Process
```python
# 1. Znajdź plik .uf2 w projekcie
# 2. Kopiuj do RPI-RP2
# 3. Czekaj 60s na restart do CIRCUITPY
# 4. Kontynuuje deployment aplikacji
```

## 🔄 Development Workflow

### 1. Pierwsze uruchomienie
```bash
# Dla świeżego RP2040
make deploy
# System sam zadba o wszystko
```

### 2. Konfiguracja sprzętowa
```bash
# Edytuj HAL konfigurację
nano hal/hal_config.toml

# Lub użyj profilu
make hal-apply PROFILE=gaming
```

### 3. Development i testy
```bash
make test
make web  # http://localhost:8080
make deploy
```

### 4. Monitorowanie
```bash
make deploy-monitor
# Auto-deployment przy podłączeniu
```

## 🎯 Scenariusze Użycia

### Scenariusz 1: Świeży RP2040
```bash
make deploy
# ✅ Wykryje RPI-RP2
# ✅ Wgra CircuitPython
# ✅ Wgra aplikację
```

### Scenariusz 2: Aktualizacja aplikacji
```bash
make hal-apply PROFILE=gaming
make deploy
# ✅ Zaktualizuje konfigurację
# ✅ Wgra nową aplikację
```

### Scenariusz 3: Development
```bash
make web  # Edytuj konfigurację
make deploy  # Wgraj zmiany
```

## 🔧 Troubleshooting (v0.0.6+)

### Problem: Nie wykrywa urządzenia
```bash
# Sprawdź fizycznie
make deploy-detect

# Sprawdź systemowo
ls /media/*/RPI-RP2 2>/dev/null || echo "Brak BOOT"
ls /media/*/CIRCUITPY 2>/dev/null || echo "Brak CIRCUITPY"
```

### Problem: Błędy montowania
```bash
# Sprawdź uprawnienia
groups $USER | grep -E "(disk|plugdev)"

# Ręczne montowanie
sudo mount /dev/sdX1 /media/tom/CIRCUITPY
```

### Problem: Nie wgralo firmware
```bash
# Ręczne wejście w tryb BOOT
# 1. Przytrzymaj BOOT
# 2. Podłącz USB
# 3. Puść BOOT przy migającej diodzie
# 4. make deploy
```

### Problem: Błędy HAL synchronizacji
```bash
# Waliduj konfigurację
make hal-validate

# Resetuj synchronizację
rm .hal_sync.json
make hal-sync
```

## 📝 Logi

System tworzy logi w:
- `backups/` - Backupy plików przed deploymentem
- `hal/backups/` - Backupy konfiguracji HAL
- `lib_cache/` - Pobrane biblioteki
- `.hal_sync.json` - Stan synchronizacji HAL

## 🎯 Podsumowanie

System zapewnia (v0.0.6+):
- ✅ **Inteligentną detekcję** trybów BOOT/CIRCUITPY
- ✅ **Auto-flashing** firmware CircuitPython
- ✅ **Auto-mounting** urządzeń systemowych
- ✅ **HAL-based configuration** - oddzielenie sprzętu od kodu
- ✅ **Profile system** - szybkie przełączanie konfiguracji
- ✅ **Automatyczny deployment** firmware generowanego z HAL
- ✅ **Backup** istniejących plików
- ✅ **Monitorowanie** w tle
- ✅ **Start przy boot** systemu

**Podłącz RP2040-One a system automatycznie zajmie się resztą!** 🚀

**Szczegółowy przewodnik:** zobacz [FIRST_TIME_SETUP.md](FIRST_TIME_SETUP.md)
**HAL Configuration:** zobacz [DEPLOYMENT_HAL.md](DEPLOYMENT_HAL.md)
