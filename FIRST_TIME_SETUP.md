# RP2040 First-Time Setup Guide
# ===========================

Kompletny przewodnik dla pierwszego uruchomienia RP2040-One z tym projektem.

## 🎯 Scenariusze Użycia

### Scenariusz 1: Świeży RP2040 (Fabryczny)
Jeśli masz nowy RP2040-One lub przywrócony do ustawień fabrycznych:

```bash
# 1. Podłącz RP2040 do USB
# 2. Uruchom automatyczny setup
make deploy

# System automatycznie:
# ✅ Wykryje tryb BOOT (RPI-RP2)
# ✅ Wgra firmware CircuitPython
# ✅ Poczeka na przełączenie do CIRCUITPY  
# ✅ Wgra aplikację z konfiguracją HAL
# ✅ Skonfiguruje biblioteki
```

### Scenariusz 2: RP2040 z CircuitPython
Jeśli RP2040 już ma CircuitPython:

```bash
# 1. Podłącz RP2040 do USB
# 2. Wgraj aplikację
make deploy

# System automatycznie:
# ✅ Wykryje tryb CIRCUITPY
# ✅ Wgra aplikację z konfiguracją HAL
# ✅ Skonfiguruje biblioteki
```

### Scenariusz 3: Ręczna konfiguracja
Jeśli chcesz ręcznie kontrolować proces:

```bash
# 1. Sprawdź stan urządzenia
make deploy-detect

# 2. Jeśli w trybie BOOT, wgraj firmware
make flash

# 3. Jeśli w trybie CIRCUITPY, wgraj aplikację  
make deploy
```

## 🔧 Automatyczne Funkcje (v0.0.6+)

### Auto-Mounting
System automatycznie montuje niezamontowane urządzenia CIRCUITPY:

```bash
# Sprawdza /dev/disk/by-label/CIRCUITPY
# Używa udisksctl do montowania
# Fallback do manualnego montowania
```

### Auto-Flashing
Dla urządzeń w trybie BOOT:

```bash
# Automatycznie znajduje plik .uf2
# Kopiuje do RPI-RP2
# Czeka na restart do CIRCUITPY
# Kontynuuje deployment aplikacji
```

### Smart Detection
System rozróżnia tryby urządzenia:

| Tryb | Nazwa | Akcja |
|------|-------|-------|
| BOOT | RPI-RP2 | Flash firmware CircuitPython |
| CIRCUITPY | CIRCUITPY | Deploy aplikacji |

## 📋 Wymagania

### System
- Linux (Ubuntu/Debian/Mint)
- Python 3.8+
- `udisksctl` (dla auto-mountingu)

### Sprzęt
- RP2040-One board
- Kabel USB-A
- Komputer z portem USB-A

### Oprogramowanie
```bash
# Instalacja zależności
make install

# Lub ręcznie
pip3 install fastapi uvicorn pytest toml
```

## 🚀 Szybki Start (5 minut)

```bash
# 1. Klonuj repozytorium
git clone https://github.com/tom Sapletta/rp2040-keyboard.git
cd rp2040-keyboard

# 2. Instalacja
make install

# 3. Podłącz RP2040 do USB

# 4. Uruchom deployment
make deploy

# 5. Gotowe! Sprawdź działanie:
# - Przyciski: Ctrl+1..Ctrl+9
# - Enkoder: Scroll + Left Click
```

## 🔍 Troubleshooting

### Problem: Nie wykrywa urządzenia
```bash
# Sprawdź fizycznie:
lsusb | grep -i rp2040
ls /media/*/CIRCUITPY 2>/dev/null || echo "Brak CIRCUITPY"

# Sprawdź tryb BOOT:
ls /media/*/RPI-RP2 2>/dev/null || echo "Brak RPI-RP2"
```

### Problem: Błędy uprawnień
```bash
# Dodaj użytkownika do grup (jeśli potrzebne)
sudo usermod -a -G disk,plugdev $USER

# Lub użyj sudo dla montowania
sudo make deploy
```

### Problem: Nie wgralo firmware
```bash
# Ręczne wejście w tryb BOOT:
# 1. Przytrzymaj przycisk BOOT na RP2040
# 2. Podłącz USB (lub naciśnij RESET)
# 3. Puść BOOT gdy dioda zacznie migać
# 4. Uruchom: make deploy
```

### Problem: Błędy bibliotek
```bash
# Wyczyść i pobierz ponownie
rm -rf lib_cache/
make deploy-setup
make deploy
```

## 🎮 Testowanie Działania

Po udanym deployment:

```bash
# Test przycisków
# Naciśnij GP1 -> powinno wygenerować Ctrl+1
# Naciśnij GP2 -> powinno wygenerować Ctrl+2
# ... itd.

# Test enkodera
# Obrót w prawo -> scroll w górę
# Obrót w lewo -> scroll w dół  
# Wciśnięcie -> left click myszy

# Test web configurator
make web
# Otwórz http://localhost:8080
```

## 📝 Logi i Debugowanie

```bash
# Szczegółowe logi deployment
python3 deploy.py deploy

# Logi HAL
make hal-show

# Testy jednostkowe
make test
```

## 🔄 Proces Deployment (v0.0.6+)

```
Podłączenie USB
    ↓
Detekcja trybu (BOOT/CIRCUITPY)
    ↓
Jeśli BOOT:
  • Flash firmware CircuitPython (.uf2)
  • Czekaj na restart
    ↓
Jeśli CIRCUITPY:
  • Synchronizuj HAL konfigurację
  • Generuj firmware z HAL
  • Pobierz biblioteki (adafruit_hid)
  • Wgraj boot.py + code.py
  • Gotowe!
```

## 🎯 Następne Kroki

Po pierwszym setup:

1. **Konfiguracja HAL:** `nano hal/hal_config.toml`
2. **Profile:** `make hal-apply PROFILE=gaming`
3. **Web configurator:** `make web`
4. **Monitorowanie:** `make deploy-monitor`

**Gratulacje! Twój RP2040-One jest gotowy do użycia!** 🚀
