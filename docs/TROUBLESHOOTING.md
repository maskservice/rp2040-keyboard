# Troubleshooting Guide for RP2040 Keyboard & Encoder Service

Operational runbooks and diagnosis procedures for `maskservice-rp2040-keyboard` input emulation, EC12 rotary encoder decoding, and HID matrix interfaces.

## Common Issues & Remediation

### 1. Encoder Chatter & Bouncing Transitions
- **Symptom**: Rotary knob registers double-clicks or erratic direction reversing.
- **Diagnosis**: Check quadrature pulse timing and debouncing state machine.
- **Remediation**: Tune debounce filter window (default 5ms); inspect hardware pull-up resistors on EC12 pins.

### 2. Physical Limits & Jog Step Ceiling
- **Symptom**: Manual jog wheel commands push motor beyond maximum velocity.
- **Diagnosis**: Verify pulse rate translation to motion commands.
- **Remediation**: Movement speed must strictly observe the 50,000 steps/s hardware limit (`MAX_SPEED_STEPS_PER_SECOND = 50000`). Enforce rate limiting on encoder step delta.

### 3. USB HID Enumeration Failure
- **Symptom**: Host OS does not detect keyboard/composite input device.
- **Diagnosis**: Check `dmesg -w` or `lsusb` for descriptor stall.
- **Remediation**: Reset RP2040 via watchdog or replug; verify TinyUSB stack configuration.

### 4. Code Reuse & Deduplication Conformance
- **Symptom**: `conformance.py` flags missing scan receipt or unmitigated duplicate debounce logic.
- **Diagnosis**: Run `python3 standard/conformance.py --project /home/tom/github/maskservice/rp2040-keyboard`.
- **Remediation**: Run `record_scan_receipt.py` to record verified scan evidence in `.reuse/redup-receipt.json`.
