# RP2040-One HID Keypad + Encoder Mouse

Projekt makro-klawiatury 9-przyciskowej z enkoderem obrotowym opartej na Waveshare RP2040-One. Po podłączeniu do portu USB komputer rozpoznaje urządzenie jako **klawiaturę + myszkę** jednocześnie — bez instalacji sterowników.

**Repozytorium:** Softreck / Prototypowanie.pl

---

## Funkcjonalność

| Element | Funkcja | Akcja HID |
|---------|---------|-----------|
| 9 przycisków switch | Skróty klawiaturowe | Ctrl+1, Ctrl+2, ... Ctrl+9 |
| Enkoder — obrót CW | Scroll w górę | Mouse wheel up |
| Enkoder — obrót CCW | Scroll w dół | Mouse wheel down |
| Enkoder — wciśnięcie | Klik środkowy myszy | Mouse middle button |

---

## Sprzęt

### Waveshare RP2040-One

- Mikrokontroler: RP2040 (dual-core Cortex-M0+, 133 MHz)
- Flash: 4 MB
- USB-A wbudowany (bezpośredni wtyk do portu USB-A komputera)
- 20 GPIO, programowalny w CircuitPython / MicroPython / C SDK
- Wiki: https://www.waveshare.com/wiki/RP2040-One

### Wymagane komponenty

| Komponent | Ilość | Uwagi |
|-----------|-------|-------|
| Waveshare RP2040-One | 1 | Z wbudowanym wtyczką USB-A |
| Przycisk tact switch | 9 | Normalnie otwarty (NO), 2 lub 4 pin |
| Enkoder obrotowy z przyciskiem | 1 | Moduł KY-040 lub równoważny (5 pinów: CLK, DT, SW, +, GND) |
| Przewody połączeniowe | ~25 | Dupont lub lutowane |
| Płytka stykowa / PCB | 1 | Opcjonalnie |

---

## Schemat podłączeń

### Przyciski (9 sztuk) → Emulacja klawiatury

Każdy przycisk podłączony jest jednym pinem do GPIO, drugim do GND. Wewnętrzny pull-up aktywowany programowo — **nie trzeba zewnętrznych rezystorów**.

```
Przycisk 1:  GP1  ←→ [SWITCH] ←→ GND    → Ctrl+1
Przycisk 2:  GP2  ←→ [SWITCH] ←→ GND    → Ctrl+2
Przycisk 3:  GP3  ←→ [SWITCH] ←→ GND    → Ctrl+3
Przycisk 4:  GP4  ←→ [SWITCH] ←→ GND    → Ctrl+4
Przycisk 5:  GP5  ←→ [SWITCH] ←→ GND    → Ctrl+5
Przycisk 6:  GP6  ←→ [SWITCH] ←→ GND    → Ctrl+6
Przycisk 7:  GP7  ←→ [SWITCH] ←→ GND    → Ctrl+7
Przycisk 8:  GP8  ←→ [SWITCH] ←→ GND    → Ctrl+8
Przycisk 9:  GP29 ←→ [SWITCH] ←→ GND    → Ctrl+9
```

### Enkoder obrotowy (KY-040) → Emulacja myszki

Moduł enkodera ma 5 wyprowadzeń. Trzy wymagają podłączenia do GPIO, dwa do zasilania:

```
Pin enkodera    →  RP2040-One       Funkcja
─────────────────────────────────────────────
CLK (A)         →  GP9              Sygnał A enkodera
DT  (B)         →  GP10             Sygnał B enkodera
SW              →  GP11             Przycisk enkodera
+   (VCC)       →  3V3              Zasilanie 3.3V
GND             →  GND              Masa
```

> **Uwaga:** GP12 i GP13 pozostają wolne — można je wykorzystać w przyszłych rozszerzeniach (np. LED statusu, drugi enkoder, buzzer).

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
   ENC CLK ────→│  GP9  ●                       │
   ENC DT  ────→│  GP10 ●                       │
   ENC SW  ────→│  GP11 ●                       │
     (wolny)    │  GP12 ○                       │
     (wolny)    │  GP13 ○                       │
                │  ...                           │
      Btn9 ────→│  GP29 ●                       │
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
│   └── code.py        ← Domyślny program (Ctrl+1..9 + scroll)
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

1. Otwórz: https://circuitpython.org/board/waveshare_rp2040_one/
2. Pobierz najnowszy plik `.uf2` (CircuitPython 9.x)

### Krok 2: Wgranie firmware CircuitPython

1. **Odłącz** RP2040-One od komputera
2. **Przytrzymaj przycisk BOOT** na płytce (mały przycisk przy krawędzi)
3. **Włóż** RP2040-One do portu USB-A komputera **trzymając BOOT**
4. Zwolnij przycisk BOOT — w systemie pojawi się dysk **RPI-RP2**
5. **Skopiuj** pobrany plik `.uf2` na dysk RPI-RP2
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
| 1 | GP1 | Ctrl+1 | Zakładka 1 w przeglądarce |
| 2 | GP2 | Ctrl+2 | Zakładka 2 |
| 3 | GP3 | Ctrl+3 | Zakładka 3 |
| 4 | GP4 | Ctrl+4 | Zakładka 4 |
| 5 | GP5 | Ctrl+5 | Zakładka 5 |
| 6 | GP6 | Ctrl+6 | Zakładka 6 |
| 7 | GP7 | Ctrl+7 | Zakładka 7 |
| 8 | GP8 | Ctrl+8 | Zakładka 8 |
| 9 | GP29 | Ctrl+9 | Ostatnia zakładka |

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

Aby zmienić modyfikator (np. Alt zamiast Ctrl), zmień linię w pętli głównej:

```python
# Zamień Ctrl na Alt:
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

---

## Konserwacja

- **Aktualizacja CircuitPython:** Powtórz krok 2 (BOOT + UF2), pliki na CIRCUITPY zostają
- **Aktualizacja bibliotek:** Pobierz nowy bundle i nadpisz `lib/adafruit_hid/`
- **Backup:** Skopiuj zawartość CIRCUITPY na dysk — to zwykłe pliki

---

## Licencja

MIT — Softreck / Prototypowanie.pl
