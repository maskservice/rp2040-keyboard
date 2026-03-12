# RP2040 Auto-Deployment System
# =============================

Automatyczny system pobierania bibliotek i deploymentu firmware na urządzenia RP2040-One z CircuitPython.

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

## 🔧 Dostępne komendy

### Makefile
```bash
make deploy          # Jednorazowy deployment
make deploy-monitor  # Monitorowanie urządzeń
make deploy-setup    # Pobierz biblioteki
make deploy-detect   # Wykryj urządzenia
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
```

## 📁 Struktura po deploymentu

```
CIRCUITPY/
├── boot.py              # Nasz firmware startowy
├── code.py              # Główny program klawiatury
└── lib/
    └── adafruit_hid/    # Biblioteka HID (pobrana automatycznie)
        ├── __init__.py
        ├── keyboard.py
        └── mouse.py
```

## 🔍 Jak to działa

1. **Detekcja urządzeń**: Skrypt skanuje common mount points looking for CircuitPython devices
2. **Pobieranie bibliotek**: Automatycznie pobiera `adafruit_hid` z GitHub
3. **Backup**: Tworzy backup istniejących plików przed deploymentem
4. **Deployment**: Kopiuje firmware i biblioteki na urządzenie
5. **Monitorowanie**: Ciągle sprawdza podłączone urządzenia

## 🛠️ Auto-start przy boot systemu

### Linux systemd
```bash
# Stwórz service file
sudo nano /etc/systemd/system/rp2040-deploy.service
```

```ini
[Unit]
Description=RP2040 Auto-Deploy Service
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/home/youruser/rp2040-keyboard
ExecStart=/home/youruser/rp2040-keyboard/boot-monitor.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Włącz service
sudo systemctl enable rp2040-deploy.service
sudo systemctl start rp2040-deploy.service
```

### Crontab
```bash
# Dodaj do crontab
crontab -e

# Uruchom przy starcie systemu
@reboot /home/user/rp2040-keyboard/boot-monitor.py >> /home/user/rp2040-deploy.log 2>&1 &
```

## 🔧 Troubleshooting

### Brak wykrytych urządzeń
```bash
# Sprawdź ręcznie
ls /media/*/CIRCUITPY 2>/dev/null || ls /mnt/*/CIRCUITPY 2>/dev/null
```

### Błędy uprawnień
```bash
# Upewnij się że skrypty są wykonywalne
chmod +x deploy.py boot-monitor.py auto-deploy.sh
```

### Problemy z bibliotekami
```bash
# Wyczyść cache i pobierz ponownie
rm -rf lib_cache/
python3 deploy.py setup
```

## 📝 Logi

System tworzy logi w:
- `backups/` - Backupy plików przed deploymentem
- `lib_cache/` - Pobrane biblioteki
- `.env` - Konfiguracja i ostatnie urządzenie

## 🎯 Podsumowanie

System zapewnia:
- ✅ **Automatyczne pobieranie** bibliotek
- ✅ **Detekcję urządzeń** CircuitPython  
- ✅ **Automatyczny deployment** firmware
- ✅ **Backup** istniejących plików
- ✅ **Monitorowanie** w tle
- ✅ **Start przy boot** systemu

Podłącz RP2040-One a system automatycznie zainstaluje wszystko co potrzebne! 🚀
