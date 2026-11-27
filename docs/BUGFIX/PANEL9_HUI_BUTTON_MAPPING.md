---
{
  "schema": "wellmanifest.docs/document/v2",
  "id": "panel9-hui-button-mapping",
  "kind": "bugfix",
  "version": 1,
  "title": "Wyrównanie mapowania przycisków SW1–SW9 płytki panel9 do układu HUI w C2004",
  "status": "proposed",
  "owner": "maskservice/rp2040-keyboard",
  "scope": "repository",
  "updated": "2026-11-27",
  "source_revision": "8202ad0d8cd768932757ec9c62a81c48fe5b27b1",
  "priority": "P1",
  "evidence": [
    "viewer:artifacts/pcb/panel9.kicad_pcb@c910c61a83be8fee",
    "c2004:packages/ui-components/src/test-hui.ts",
    "rp2040-keyboard:tests/test_rp2040_keyboard.py"
  ]
}
---

# Wyrównanie mapowania przycisków SW1–SW9 płytki panel9 do układu HUI w C2004

<!-- docs:section summary -->
## Cel i rezultat

Naprawiono błędne przypisanie skrótów `Ctrl+Alt+1..9` dla wszystkich 9 fizycznych przycisków `SW1..SW9` płytki `panel9` (RP2040-Zero) tak, aby ich położenie geometryczne `4 + 1 + 4` odpowiadało dokładnie układowi przycisków `test-hui` w aplikacji `maskservice/c2004`, oraz poprawiono cytowanie wartości w `hal/hardware_pins.toml`.

<!-- docs:section details -->
## Zakres i rozwiązanie

Poprzednia wersja płytki prototypowej (RP2040-One) zakładała kolejność przewodów `[9, 8, 5, 1, 7, 6, 4, 2, 3]`. Przy migracji na `panel9.kicad_pcb` zaktualizowano piny GPIO (`[14, 6, 7, 8, 5, 1, 4, 3, 2]`), lecz zachowano starą kolejność kodów HID, co powodowało rozjazd `0/9` względem ekranu HUI.

| Przycisk PCB | Pozycja `(X, Y)` | GPIO | Poprzedni skrót | Poprawiony skrót | Akcja C2004 HUI |
|---|---|---|---|---|---|
| `SW1` (góra-1) | `(118, 74.5)` | `GP14` | `Ctrl+Alt+9` | `Ctrl+Alt+6` | `Głowa ＋` (`head-inflate`) |
| `SW2` (góra-2) | `(148, 74.5)` | `GP6` | `Ctrl+Alt+8` | `Ctrl+Alt+2` | `LP +5` (`lp-pwm-plus5`) |
| `SW3` (góra-3) | `(198, 74.5)` | `GP7` | `Ctrl+Alt+5` | `Ctrl+Alt+3` | `LP +10` (`lp-pwm-plus10`) |
| `SW4` (góra-4) | `(228, 74.5)` | `GP8` | `Ctrl+Alt+1` | `Ctrl+Alt+4` | `AL START` (`al-start`) |
| `SW5` (środek) | `(173, 92.0)` | `GP5` | `Ctrl+Alt+7` | `Ctrl+Alt+5` | `LP Upust` (`lp-bleed`) |
| `SW6` (dół-1) | `(118, 109.5)` | `GP1` | `Ctrl+Alt+6` | `Ctrl+Alt+1` | `Głowa −` (`head-deflate`) |
| `SW7` (dół-2) | `(148, 109.5)` | `GP4` | `Ctrl+Alt+4` | `Ctrl+Alt+7` | `LP −5` (`lp-pwm-minus5`) |
| `SW8` (dół-3) | `(198, 109.5)` | `GP3` | `Ctrl+Alt+2` | `Ctrl+Alt+8` | `LP −10` (`lp-pwm-minus10`) |
| `SW9` (dół-4) | `(228, 109.5)` | `GP2` | `Ctrl+Alt+3` | `Ctrl+Alt+9` | `AL STOP` (`al-stop`) |

Enkoder na `J1` (`ENC_A=GP0`, `ENC_B=GP15`, `ENC_SW=GP26` → `Mouse.MIDDLE_BUTTON`) oraz dekoder Gray-code pozostają bez zmian. Zacytowano także `vcc = "3.3V"`, `gnd = "0V"`, `max_gpio_voltage = "3.3V"` w `hal/hardware_pins.toml`.

<!-- docs:section validation -->
## Weryfikacja

- `make lint` (`py_compile` + `ruff check`), `pytest` w `tests/test_rp2040_keyboard.py` (w tym test wszystkich 9 GPIO przeciw macierzy `[6, 2, 3, 4, 5, 1, 7, 8, 9]` oraz parsowanie `hardware_pins.toml`), `hal_manager validate` i `nohardcode_check.py`.

<!-- docs:section risks -->
## Ryzyka i następny krok

W trakcie weryfikacji fizyczna płytka `panel9` nie była podłączona do USB ani do stanowiska LAN (`192.168.188.116/249/224`). Po podłączeniu modułu RP2040-Zero należy wgrać zaktualizowany `code.py` poleceniem `make deploy BOARD=zero` (bez wykonywania backupu flasha w trybie dev) i potwierdzić fizycznie każdy z 9 przycisków.
