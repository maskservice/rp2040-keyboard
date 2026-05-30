# rp2040-keyboard

- RP2040-One / RP2040-Zero HID Keypad + Encoder Mouse

Projekt makro-klawiatury 9-przyciskowej z enkoderem obrotowym opartej na **Waveshare RP2040-One** lub **RP2040-Zero**. Po podłączeniu do portu USB komputer rozpoznaje urządzenie jako **klawiaturę + myszkę** jednocześnie — bez instalacji sterowników.

**Repozytorium:** Softreck / Prototypowanie.pl

---

## Wspierane płytki

| Płytka | Specyfikacja | Firmware |
|--------|-------------|----------|
| **RP2040-One** | USB-A wbudowany, 4MB Flash, 20 GPIO | `rp2040-one/*.uf2` |
| **RP2040-Zero** | Micro-USB, 2MB Flash, 20 GPIO | `rp2040-zero/*.uf2` |

---

## Funkcjonalność

| Element | Funkcja | Akcja HID |
|---------|---------|-----------|
| 9 przycisków switch | Skróty klawiaturowe | Ctrl+Alt+1, Ctrl+Alt+2, ... Ctrl+Alt+9 |
| Enkoder — obrót CW | Scroll w górę | Mouse wheel up |
| Enkoder — obrót CCW | Scroll w dół | Mouse wheel down |
| Enkoder — wciśnięcie | **Lewy klik myszy** | Mouse left button |

---

## 🚀 Uruchamianie Web Configurator

Web configurator to interfejs graficzny do konfiguracji klawiatury RP2040.

### Szybki start

```bash
# Uruchom web configurator (domyślny port 8081)
make web

# Uruchom na innym porcie
PORT=8082 make web

# Tryb deweloperski z auto-reload
make dev

# Zatrzymaj serwer
make stop
```

Po uruchomieniu otwórz w przeglądarce: `http://localhost:8081` (lub wybrany port)

### Funkcje Web Configurator
- ⚙️ **Konfiguracja** - wizualny edytor przypisań klawiszy
- 🔌 **Schemat** - diagram podłączeń GPIO
- 💾 **Wgrywanie** - instrukcja flashowania firmware
- 🧪 **Testowanie** - testowanie klawiszy w czasie rzeczywistym

---

## 🚀 Auto-Deployment System with HAL

Automatyczny system pobierania bibliotek i deploymentu firmware na RP2040-One/Zero z **HAL (Hardware Abstraction Layer)**:

### Szybki start
```bash
# Podłącz RP2040 i uruchom (automatyczna detekcja płytki)
make deploy

# Wymuś konkretną płytkę (jeśli detekcja się myli)
make deploy BOARD=zero
make deploy BOARD=one

# Lub monitoruj w tle (auto-deployment przy podłączeniu)
make deploy-monitor
```

### 🔧 HAL Configuration
Projekt używa **HAL (Hardware Abstraction Layer)** do oddzielenia konfiguracji sprzętowej:

```bash
# Główna konfiguracja sprzętowa
hal/hal_config.toml

# Profile konfiguracyjne
hal/profiles/default.toml   # Standard 9-key + encoder
hal/profiles/minimal.toml   # Minimal 4-key + encoder  
hal/profiles/gaming.toml    # Gaming WASD + fast encoder
```

### Funkcje HAL
- ✅ **Hardware Abstraction**: Konfiguracja w TOML, oddzielona od kodu
- ✅ **Profile System**: Szybkie przełączanie między konfiguracjami
- ✅ **Validation**: Automatyczne sprawdzanie konfliktów GPIO
- ✅ **Version Control**: Konfiguracja sprzętowa w systemie kontroli wersji

### Nowe Funkcje v0.0.7
- 🔀 **Wsparcie RP2040-Zero**: Detekcja i firmware dla płytki Zero
- 🎯 **Wymuszanie płytki**: `BOARD=one|zero` lub `--board=one|zero`
- 📁 **Organizacja firmware**: Foldery `rp2040-one/` i `rp2040-zero/`
- 🧠 **Inteligentna detekcja**: Automatyczne rozpoznawanie trybu BOOT/CIRCUITPY
- 🔥 **Auto-flashing**: Wgrywanie firmware CircuitPython dla świeżych urządzeń
- 🔄 **Auto-mounting**: Systemowe montowanie urządzeń CIRCUITPY
- 📦 **One-command setup**: `make deploy` zajmuje się wszystkim

### Komendy HAL
```bash
make hal-profiles              # Lista dostępnych profili
make hal-apply PROFILE=gaming # Zastosuj profil gaming
make hal-validate            # Waliduj konfigurację
make hal-show                # Pokaż aktualną konfigurację
```

**Szczegóły:** zobacz [DEPLOYMENT_V2.md](DEPLOYMENT_V2.md) | [FIRST_TIME_SETUP.md](FIRST_TIME_SETUP.md) | [DEPLOYMENT_HAL.md](DEPLOYMENT_HAL.md)

---

## 📁 Struktura firmware

Firmware CircuitPython jest organizowane w podkatalogach według typu płytki:

```
rp2040-keyboard/
├── rp2040-one/          ← Firmware dla RP2040-One
│   ├── circuitpython-waveshare_rp2040_one-en_US-9.2.0.uf2
│   └── adafruit-circuitpython-waveshare_rp2040_one-pl-10.1.4.uf2
├── rp2040-zero/         ← Firmware dla RP2040-Zero
│   └── adafruit-circuitpython-waveshare_rp2040_zero-pl-10.1.4.uf2
├── deploy.py            ← Auto-deployment z detekcją płytki
└── Makefile
```

### Pobieranie firmware

```bash
# Pobierz dla obu płytek
make download-uf2-all

# Lub pojedynczo
make download-uf2       # Tylko RP2040-One
make download-uf2-zero  # Tylko RP2040-Zero
```

### Wymuszanie typu płytki

Jeśli automatyczna detekcja nie działa poprawnie:

```bash
# Metoda 1: Zmienna środowiskowa (globalna dla sesji)
export RP2040_BOARD=zero
make deploy

# Metoda 2: Argument w make (jednorazowo)
make deploy BOARD=zero
make deploy BOARD=one

# Metoda 3: Argument w deploy.py (bezpośrednio)
.venv/bin/python3 deploy.py deploy --board=zero

# Metoda 4: Environment variable inline
RP2040_BOARD=zero make deploy
```

### Komendy diagnostyczne

```bash
# Sprawdź wykrytą płytkę
make deploy-board

# Sprawdź z wymuszeniem
make deploy-board BOARD=zero

# Pełna diagnostyka USB
make deploy-diagnose
```

---

## Sprzęt

### Waveshare RP2040-One

- Mikrokontroler: RP2040 (dual-core Cortex-M0+, 133 MHz)
- Flash: 4 MB
- USB-A wbudowany (bezpośredni wtyk do portu USB-A komputera)
- 20 GPIO, programowalny w CircuitPython / MicroPython / C SDK
- Wiki: https://www.waveshare.com/wiki/RP2040-One

### Waveshare RP2040-Zero

- Mikrokontroler: RP2040 (dual-core Cortex-M0+, 133 MHz)
- Flash: 2 MB
- Micro-USB port (wymaga kabla micro-USB)
- 20 GPIO, programowalny w CircuitPython / MicroPython / C SDK
- Wiki: https://www.waveshare.com/wiki/RP2040-Zero

### Wymagane komponenty

| Komponent | Ilość | Uwagi |
|-----------|-------|-------|
| Waveshare RP2040-One **lub** RP2040-Zero | 1 | One ma wbudowany USB-A, Zero wymaga kabla micro-USB |
| Przycisk tact switch | 9 | Normalnie otwarty (NO), 2 lub 4 pin |
| Enkoder obrotowy z przyciskiem | 1 | Moduł KY-040 lub równoważny (5 pinów: CLK, DT, SW, +, GND) |
| Przewody połączeniowe | ~25 | Dupont lub lutowane |
| Płytka stykowa / PCB | 1 | Opcjonalnie |

---

## Schemat podłączeń

### Przyciski (9 sztuk) → Emulacja klawiatury

Każdy przycisk podłączony jest jednym pinem do GPIO, drugim do GND. Wewnętrzny pull-up aktywowany programowo — **nie trzeba zewnętrznych rezystorów**.

```
Przycisk 1:  GP1  ←→ [SWITCH] ←→ GND    → Ctrl+Alt+1
Przycisk 2:  GP2  ←→ [SWITCH] ←→ GND    → Ctrl+Alt+2
Przycisk 3:  GP3  ←→ [SWITCH] ←→ GND    → Ctrl+Alt+3
Przycisk 4:  GP4  ←→ [SWITCH] ←→ GND    → Ctrl+Alt+4
Przycisk 5:  GP5  ←→ [SWITCH] ←→ GND    → Ctrl+Alt+5
Przycisk 6:  GP6  ←→ [SWITCH] ←→ GND    → Ctrl+Alt+6
Przycisk 7:  GP7  ←→ [SWITCH] ←→ GND    → Ctrl+Alt+7
Przycisk 8:  GP8  ←→ [SWITCH] ←→ GND    → Ctrl+Alt+8
Przycisk 9:  GP9  ←→ [SWITCH] ←→ GND    → Ctrl+Alt+9
```

### Enkoder obrotowy (KY-040) → Emulacja myszki

Moduł enkodera ma 5 wyprowadzeń. Trzy wymagają podłączenia do GPIO, dwa do zasilania:

```
Pin enkodera    →  RP2040-One       Funkcja
─────────────────────────────────────────────
CLK (A)         →  GP11             Sygnał A enkodera
DT  (B)         →  GP12             Sygnał B enkodera
SW              →  GP13             Przycisk enkodera
+   (VCC)       →  3V3              Zasilanie 3.3V
GND             →  GND              Masa
```

> **Uwaga:** GP10 pozostaje wolne — można je wykorzystać w przyszłych rozszerzeniach.

### Diagram fizyczny

```
                    RP2040-One (widok z góry, USB-A w prawo)
                 ┌──────────────────────────────┐
                 │                          USB-A ====
                 │  GP0  ○                       │
      Btn1 ────→│  GP1  ●                       │
      Btn2 ────→│  GP2  ●                       │
      Btn3 ────→│  GP3  ●                       │
      Btn4 ────→│  GP4  ●                       │
      Btn5 ────→│  GP5  ●                       │
      Btn6 ────→│  GP6  ●                       │
      Btn7 ────→│  GP7  ●                       │
      Btn8 ────→│  GP8  ●                       │
      Btn9 ────→│  GP9  ●                       │
     (wolny)    │  GP10 ○                       │
   ENC CLK ────→│  GP11 ●                       │
   ENC DT  ────→│  GP12 ●                       │
   ENC SW  ────→│  GP13 ●                       │
                │  ...                           │
                │  3V3  ●←──── ENC VCC (+)       │
                │  GND  ●←──── ENC GND + BTN GND│
                 └──────────────────────────────┘
     
     ● = pin używany    ○ = pin wolny
```

---

## Oprogramowanie

### Platforma: CircuitPython 9.x

CircuitPython to fork MicroPythona od Adafruit ze wbudowaną obsługą USB HID. Wystarczy skopiować pliki na dysk CIRCUITPY — brak kompilacji, brak IDE.

### Pliki projektu

```
CIRCUITPY/
├── boot.py          ← Konfiguracja USB HID (keyboard + mouse)
├── code.py          ← Główny program (pętla obsługi klawiszy + enkodera)
└── lib/
    └── adafruit_hid/  ← Biblioteka HID (skopiowana z bundle)

Repozytorium:
├── firmware/
│   ├── boot.py        ← Plik startowy USB HID
│   └── code.py        ← Domyślny program (Ctrl+Alt+1..9 + scroll)
├── rp2040-one/        ← Firmware UF2 dla RP2040-One
│   └── *.uf2
├── rp2040-zero/       ← Firmware UF2 dla RP2040-Zero
│   └── *.uf2
├── web/
│   └── app.py         ← Web Configurator (FastAPI + frontend)
├── tests/
│   └── test_all.py    ← 34 testy (unit + E2E)
├── docker/
│   ├── Dockerfile           ← Obraz web serwisu
│   ├── Dockerfile.test      ← Obraz test runnera
│   ├── docker-compose.yml   ← Stack webowy
│   └── docker-compose.test.yml  ← Stack E2E testów
├── Makefile           ← Komendy: web, flash, test, docker
├── requirements.txt
└── README.md
```

---

## Instrukcja nagrywania krok po kroku

### Krok 1: Pobranie CircuitPython UF2

1. **Dla RP2040-One**: Otwórz https://circuitpython.org/board/waveshare_rp2040_one/
2. **Dla RP2040-Zero**: Otwórz https://circuitpython.org/board/waveshare_rp2040_zero/
3. Pobierz najnowszy plik `.uf2` (CircuitPython 9.x)

Lub użyj make:
```bash
# Pobierz dla obu płytek
make download-uf2-all
```

### Krok 2: Wgranie firmware CircuitPython

**Dla RP2040-One (USB-A wbudowane):**
1. **Odłącz** RP2040-One od komputera
2. **Przytrzymaj przycisk BOOT** na płytce (mały przycisk przy krawędzi)
3. **Włóż** RP2040-One do portu USB-A komputera **trzymając BOOT**

**Dla RP2040-Zero (Micro-USB):**
1. **Odłącz** kabel micro-USB od płytki
2. **Przytrzymaj przycisk BOOT** na płytce
3. **Podłącz** kabel micro-USB **trzymając BOOT**

**Dla obu płytek (kontynuacja):**
4. Zwolnij przycisk BOOT — w systemie pojawi się dysk **RPI-RP2**
5. **Skopiuj** pobrany plik `.uf2` na dysk RPI-RP2
   - Automatycznie: `make deploy`
   - Ręcznie: `sudo cp rp2040-one/*.uf2 /media/$USER/RPI-RP2/` (lub `rp2040-zero/`)
6. Płytka automatycznie się zrestartuje
7. W systemie pojawi się nowy dysk o nazwie **CIRCUITPY**

> Jeśli dysk RPI-RP2 nie pojawia się, spróbuj użyć innego portu USB lub kabla. Na Linuxie sprawdź `lsblk` po podłączeniu.

### Krok 3: Instalacja biblioteki adafruit_hid

1. Pobierz Adafruit CircuitPython Bundle: https://circuitpython.org/libraries
   - Wybierz bundle pasujący do wersji CircuitPython (9.x)
2. Rozpakuj archiwum ZIP
3. Z folderu `lib/` skopiuj **cały katalog** `adafruit_hid/` do `CIRCUITPY/lib/`

Struktura po skopiowaniu:
```
CIRCUITPY/lib/adafruit_hid/
├── __init__.mpy
├── keyboard.mpy
├── keyboard_layout_us.mpy
├── keycode.mpy
└── mouse.mpy
```

### Krok 4: Skopiowanie programu

1. Skopiuj plik `boot.py` do katalogu głównego **CIRCUITPY/**
2. Skopiuj plik `code.py` do katalogu głównego **CIRCUITPY/**
3. Po skopiowaniu `code.py` płytka **automatycznie się zrestartuje** i program ruszy

> **WAŻNE:** Plik `boot.py` działa TYLKO przy starcie urządzenia (podłączeniu USB). Po skopiowaniu `boot.py` odłącz i ponownie podłącz RP2040-One, aby USB HID się poprawnie zainicjalizował.

### Krok 5: Weryfikacja

1. Odłącz i ponownie włóż RP2040-One do portu USB
2. System powinien rozpoznać urządzenie jako **klawiaturę + myszkę**
3. Sprawdź:
   - Wciśnij przycisk 1 → powinno zadziałać Ctrl+1 (np. przełączenie zakładki w przeglądarce)
   - Obróć enkoder → strona powinna się scrollować
   - Wciśnij enkoder → środkowy klik myszy (np. otwarcie linku w nowej zakładce)

**Linux — weryfikacja w dmesg:**
```bash
sudo dmesg | tail -20
# Powinno pokazać:
# usb X-X: Product: RP2040-One
# input: ... as /devices/.../input0  (keyboard)
# input: ... as /devices/.../input1  (mouse)
```

**Windows — weryfikacja:**
- Menadżer urządzeń → Klawiatury → "HID Keyboard Device"
- Menadżer urządzeń → Myszy → "HID-compliant mouse"

---

## Mapowanie klawiszy

| Przycisk | GPIO | Akcja | Typowe zastosowanie |
|----------|------|-------|---------------------|
| 1 | GP1 | Ctrl+Alt+1 | Globalne makro 1 |
| 2 | GP2 | Ctrl+Alt+2 | Globalne makro 2 |
| 3 | GP3 | Ctrl+Alt+3 | Globalne makro 3 |
| 4 | GP4 | Ctrl+Alt+4 | Globalne makro 4 |
| 5 | GP5 | Ctrl+Alt+5 | Globalne makro 5 |
| 6 | GP6 | Ctrl+Alt+6 | Globalne makro 6 |
| 7 | GP7 | Ctrl+Alt+7 | Globalne makro 7 |
| 8 | GP8 | Ctrl+Alt+8 | Globalne makro 8 |
| 9 | GP9 | Ctrl+Alt+9 | Globalne makro 9 |

| Enkoder | GPIO | Akcja |
|---------|------|-------|
| Obrót CW | GP9+GP10 | Scroll w górę |
| Obrót CCW | GP9+GP10 | Scroll w dół |
| Wciśnięcie | GP11 | Middle-click myszy |

---

## Modyfikacja skrótów

Aby zmienić przypisanie klawiszy, edytuj tablicę `KEY_PINS` w pliku `code.py`:

```python
# Przykład: zmiana Przycisk 1 na Ctrl+Z (cofnij)
KEY_PINS = [
    (board.GP1, Keycode.Z),        # Przycisk 1 → Ctrl+Z
    # ...
]
```

Aktualne domyślne mapowanie używa `Ctrl+Alt+1..9`, aby ograniczyć kolizje z typowymi skrótami przeglądarki.

Aby zmienić modyfikator (np. Shift zamiast Ctrl+Alt), zmień linię w pętli głównej:

```python
# Zamień Ctrl+Alt na Shift:
keyboard.press(Keycode.ALT, key['keycode'])
# ...
keyboard.release(Keycode.ALT, key['keycode'])
```

Dostępne modyfikatory: `Keycode.CONTROL`, `Keycode.ALT`, `Keycode.SHIFT`, `Keycode.GUI` (Win/Cmd).

Prędkość scrolla reguluje stała `SCROLL_SPEED` (domyślnie 2 — zwiększ dla szybszego scrolla).

---

## Rozwiązywanie problemów

| Problem | Rozwiązanie |
|---------|-------------|
| Dysk CIRCUITPY nie pojawia się | Przytrzymaj BOOT → włóż USB → wgraj UF2 ponownie |
| Klawiatura działa, mysz nie | Odłącz i ponownie podłącz USB (boot.py ładuje się przy starcie) |
| Przycisk nie reaguje | Sprawdź lutowanie / podłączenie do GND |
| Enkoder "skacze" / podwójne kroki | Zwiększ `ENCODER_DEBOUNCE_MS` w code.py (np. na 10) |
| Scroll za szybki/wolny | Zmień `SCROLL_SPEED` (1 = wolniej, 5 = szybciej) |
| Debugowanie | Podłącz terminal szeregowy (Mu Editor / `screen /dev/ttyACM0 115200`) |
| Import error: adafruit_hid | Skopiuj bibliotekę do CIRCUITPY/lib/ |
| **Zła detekcja płytki** (wgrywa zły firmware) | Użyj `make deploy BOARD=zero` lub `make deploy BOARD=one` |
| Nie można zapisać na RPI-RP2 (uprawnienia) | Użyj `sudo cp rp2040-X/*.uf2 /media/$USER/RPI-RP2/` |

---

## Konserwacja

- **Aktualizacja CircuitPython:** Powtórz krok 2 (BOOT + UF2), pliki na CIRCUITPY zostają
- **Aktualizacja bibliotek:** Pobierz nowy bundle i nadpisz `lib/adafruit_hid/`
- **Backup:** Skopiuj zawartość CIRCUITPY na dysk — to zwykłe pliki

---


## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

## Author

Created by **Tom Sapletta** - [tom@sapletta.com](mailto:tom@sapletta.com)
