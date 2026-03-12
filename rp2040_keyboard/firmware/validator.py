"""
Configuration validator for RP2040-One HID Keypad
==================================================

Validates GPIO conflicts and parameter ranges.
"""

from .generator import AVAILABLE_GPIOS, KEYCODES, MODIFIERS, PadConfig

def validate_config(config: PadConfig) -> tuple[bool, list[str]]:
    """Waliduje konfigurację pod kątem konfliktów GPIO i poprawności parametrów."""
    errors = []
    used_gpios = set()
    
    # Sprawdź przyciski
    for key in config.keys:
        if key.gpio not in AVAILABLE_GPIOS:
            errors.append(f"GPIO {key.gpio} nie jest dostępne")
        elif key.gpio in used_gpios:
            errors.append(f"GPIO {key.gpio} używane wielokrotnie")
        else:
            used_gpios.add(key.gpio)
            
        if key.keycode not in KEYCODES.values():
            errors.append(f"Nieznany keycode: {key.keycode}")
            
        if key.modifier not in MODIFIERS.values():
            errors.append(f"Nieznany modifier: {key.modifier}")
    
    # Sprawdź enkoder
    if config.encoder:
        enc_gpios = [config.encoder.clk_gpio, config.encoder.dt_gpio, config.encoder.sw_gpio]
        for gpio in enc_gpios:
            if gpio not in AVAILABLE_GPIOS:
                errors.append(f"GPIO {gpio} enkodera nie jest dostępne")
            elif gpio in used_gpios:
                errors.append(f"GPIO {gpio} enkodera koliduje z innym pinem")
            else:
                used_gpios.add(gpio)
                
        if config.encoder.clk_gpio == config.encoder.dt_gpio:
            errors.append("CLK i DT enkodera nie mogą być tym samym pinem")
            
        if not (1 <= config.encoder.scroll_speed <= 10):
            errors.append("Scroll speed musi być między 1 a 10")
    
    return len(errors) == 0, errors

__all__ = ["validate_config"]
