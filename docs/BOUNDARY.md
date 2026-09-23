# Granica Odpowiedzialności i Własności: RP2040 Keyboard

## Zakres

Repozytorium `rp2040-keyboard` odpowiada za:
1. Firmware w C/C++ dla mikrokontrolera RP2040 emulującego urządzenie USB HID (klawiaturę i enkoder obrotowy).
2. Obsługę fizycznych przycisków mechanicznych stanowiska HUI (kolory: zielony, czerwony, żółty, niebieski) oraz enkodera obrotowego EC12.

## Granice

- Interpretacja kodów klawiszy i powiązanie ich ze scenariuszami OQL (np. profil `pump-on`) zachodzi w `c2004` w module `TestHuiPage`.
