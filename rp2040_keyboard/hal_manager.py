#!/usr/bin/env python3
"""
RP2040 HAL Configuration Manager
===============================
Zarządzanie konfiguracją HAL (Hardware Abstraction Layer)
Synchronizacja z plikami TOML i generowanie konfiguracji dla firmware.
"""

import os
import sys
import time
import json
import shutil
import toml
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any

# Dodaj ścieżkę do projektu
sys.path.insert(0, str(Path(__file__).parent))

# Proste definicje klas aby uniknąć problemów z importem
@dataclass
class KeyConfig:
    gpio: int
    keycode: str
    modifier: str = "Keycode.CONTROL+Keycode.ALT"
    label: str = ""

@dataclass 
class EncoderConfig:
    clk_gpio: int
    dt_gpio: int
    sw_gpio: int
    scroll_speed: int = 2
    middle_click: bool = True
    debounce_ms: int = 3

@dataclass
class PadConfig:
    keys: List[KeyConfig]
    encoder: Optional[EncoderConfig] = None
    
    def to_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)

@dataclass
class HALSwitchConfig:
    """Konfiguracja przełącznika w formacie HAL."""
    gpio: int
    keycode: str
    modifier: str = "Keycode.CONTROL+Keycode.ALT"
    label: str = ""
    pull: str = "up"
    debounce: int = 10

@dataclass
class HALEncoderConfig:
    """Konfiguracja enkodera w formacie HAL."""
    enabled: bool = True
    clk_gpio: int = 11
    dt_gpio: int = 12
    sw_gpio: int = 13
    pull: str = "up"
    debounce: int = 3
    scroll_speed: int = 2
    middle_click: bool = True
    steps_per_revolution: int = 24

class HALConfigManager:
    """Menadżer konfiguracji HAL."""
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.hal_dir = self.project_root / "hal"
        self.hal_config_file = self.hal_dir / "hal_config.toml"
        self.hardware_pins_file = self.hal_dir / "hardware_pins.toml"
        self.profiles_dir = self.hal_dir / "profiles"
        self.backups_dir = self.hal_dir / "backups"
        self.sync_file = self.project_root / ".hal_sync.json"
        
        # Upewnij się że katalogi istnieją
        self.hal_dir.mkdir(exist_ok=True)
        self.profiles_dir.mkdir(exist_ok=True)
        self.backups_dir.mkdir(exist_ok=True)
        
    def load_hal_config(self) -> Dict[str, Any]:
        """Wczytaj konfigurację HAL z pliku TOML."""
        if not self.hal_config_file.exists():
            return self.create_default_hal_config()
        
        try:
            with open(self.hal_config_file, 'r', encoding='utf-8') as f:
                return toml.load(f)
        except Exception as e:
            print(f"❌ Błąd wczytywania hal_config.toml: {e}")
            return self.create_default_hal_config()
    
    def load_hardware_pins(self) -> Dict[str, Any]:
        """Wczytaj konfigurację pinów sprzętowych."""
        if not self.hardware_pins_file.exists():
            return {}
        
        try:
            with open(self.hardware_pins_file, 'r', encoding='utf-8') as f:
                return toml.load(f)
        except Exception as e:
            print(f"❌ Błąd wczytywania hardware_pins.toml: {e}")
            return {}
    
    def create_default_hal_config(self) -> Dict[str, Any]:
        """Stwórz domyślną konfigurację HAL."""
        return {
            "device": {
                "name": "RP2040-One-Keypad",
                "version": "1.0",
                "description": "9-key keypad with rotary encoder",
                "created": datetime.now().isoformat(),
                "modified": datetime.now().isoformat()
            },
            "pins": {
                "available": list(range(1, 30))
            },
            "switches": {},
            "encoder": {
                "enabled": True,
                "clk_gpio": 11,
                "dt_gpio": 12,
                "sw_gpio": 13,
                "pull": "up",
                "debounce": 3,
                "scroll_speed": 2,
                "middle_click": True,
                "steps_per_revolution": 24
            },
            "hardware": {
                "vcc": 3.3,
                "logic_level": "3.3V",
                "max_current": 50,
                "encoder_type": "incremental",
                "switch_type": "tactile"
            },
            "timing": {
                "debounce_switch": 10,
                "debounce_encoder": 3,
                "scan_interval": 1,
                "debounce_button": 10
            },
            "features": {
                "keyboard_enabled": True,
                "mouse_enabled": True,
                "encoder_scroll": True,
                "encoder_middle_click": True,
                "debounce_enabled": True
            }
        }
    
    def hal_to_firmware_config(self, hal_config: Dict[str, Any]) -> PadConfig:
        """Konwertuj konfigurację HAL na konfigurację firmware."""
        # Konwertuj przełączniki
        keys = []
        switches = hal_config.get("switches", {})
        
        for switch_key, switch_data in switches.items():
            if isinstance(switch_data, dict):
                key_config = KeyConfig(
                    gpio=switch_data.get("gpio"),
                    keycode=switch_data.get("keycode"),
                    modifier=switch_data.get("modifier", "Keycode.CONTROL"),
                    label=switch_data.get("label", "")
                )
                keys.append(key_config)
        
        # Konwertuj enkoder
        encoder_data = hal_config.get("encoder", {})
        if encoder_data.get("enabled", True):
            encoder_config = EncoderConfig(
                clk_gpio=encoder_data.get("clk_gpio", 11),
                dt_gpio=encoder_data.get("dt_gpio", 12),
                sw_gpio=encoder_data.get("sw_gpio", 13),
                scroll_speed=encoder_data.get("scroll_speed", 2),
                middle_click=encoder_data.get("middle_click", True),
                debounce_ms=encoder_data.get("debounce", 3)
            )
        else:
            encoder_config = None
        
        return PadConfig(keys=keys, encoder=encoder_config)
    
    def firmware_to_hal_config(self, config: PadConfig, hal_config: Dict[str, Any]) -> Dict[str, Any]:
        """Konwertuj konfigurację firmware na HAL i zaktualizuj."""
        # Zaktualizuj przełączniki
        switches = {}
        for i, key in enumerate(config.keys, 1):
            switches[f"switch_{i}"] = {
                "gpio": key.gpio,
                "keycode": key.keycode,
                "modifier": key.modifier,
                "label": key.label,
                "pull": "up",
                "debounce": 10
            }
        
        # Zaktualizuj enkoder
        if config.encoder:
            hal_config["encoder"] = {
                "enabled": True,
                "clk_gpio": config.encoder.clk_gpio,
                "dt_gpio": config.encoder.dt_gpio,
                "sw_gpio": config.encoder.sw_gpio,
                "pull": "up",
                "debounce": config.encoder.debounce_ms,
                "scroll_speed": config.encoder.scroll_speed,
                "middle_click": config.encoder.middle_click,
                "steps_per_revolution": hal_config.get("encoder", {}).get("steps_per_revolution", 24)
            }
        else:
            hal_config["encoder"]["enabled"] = False
        
        # Zaktualizuj znacznik czasu
        hal_config["device"]["modified"] = datetime.now().isoformat()
        hal_config["switches"] = switches
        
        return hal_config
    
    def save_hal_config(self, hal_config: Dict[str, Any]):
        """Zapisz konfigurację HAL do pliku."""
        try:
            with open(self.hal_config_file, 'w', encoding='utf-8') as f:
                toml.dump(hal_config, f)
            print(f"✅ Zapisano konfigurację HAL do {self.hal_config_file}")
        except Exception as e:
            print(f"❌ Błąd zapisu hal_config.toml: {e}")
    
    def load_sync_state(self) -> Dict[str, Any]:
        """Wczytaj stan synchronizacji."""
        if not self.sync_file.exists():
            return {}
        
        try:
            with open(self.sync_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def save_sync_state(self, state: Dict[str, Any]):
        """Zapisz stan synchronizacji."""
        try:
            with open(self.sync_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"❌ Błąd zapisu stanu synchronizacji: {e}")
    
    def sync_from_hal(self) -> PadConfig:
        """Synchronizuj konfigurację z HAL do firmware."""
        print("🔄 Synchronizacja HAL → Firmware...")
        
        hal_config = self.load_hal_config()
        sync_state = self.load_sync_state()
        
        # Sprawdź czy coś się zmieniło
        hal_modified = hal_config.get("device", {}).get("modified", "")
        last_sync = sync_state.get("last_hal_sync", "")
        
        if hal_modified == last_sync:
            print("ℹ️  Konfiguracja HAL jest aktualna")
            return self.hal_to_firmware_config(hal_config)
        
        # Konwertuj konfigurację
        config = self.hal_to_firmware_config(hal_config)
        
        # Zapisz stan synchronizacji
        sync_state["last_hal_sync"] = hal_modified
        sync_state["sync_direction"] = "hal_to_firmware"
        sync_state["sync_time"] = datetime.now().isoformat()
        self.save_sync_state(sync_state)
        
        print("✅ Zsynchronizowano konfigurację z HAL")
        return config
    
    def sync_to_hal(self, config: PadConfig):
        """Synchronizuj konfigurację firmware do HAL."""
        print("🔄 Synchronizacja Firmware → HAL...")
        
        hal_config = self.load_hal_config()
        sync_state = self.load_sync_state()
        
        # Konwertuj i zaktualizuj HAL
        updated_hal_config = self.firmware_to_hal_config(config, hal_config)
        
        # Zapisz konfigurację HAL
        self.save_hal_config(updated_hal_config)
        
        # Zapisz stan synchronizacji
        sync_state["last_hal_sync"] = updated_hal_config["device"]["modified"]
        sync_state["sync_direction"] = "firmware_to_hal"
        sync_state["sync_time"] = datetime.now().isoformat()
        self.save_sync_state(sync_state)
        
        print("✅ Zsynchronizowano konfigurację do HAL")
    
    def get_current_config(self) -> PadConfig:
        """Pobierz aktualną konfigurację z uwzględnieniem HAL."""
        # Sprawdź czy istnieje konfiguracja HAL
        if self.hal_config_file.exists():
            return self.sync_from_hal()
        
        # Użyj domyślnej konfiguracji
        default_keys = [
            KeyConfig(gpio=1, keycode="Keycode.ONE", modifier="Keycode.CONTROL+Keycode.ALT", label="Ctrl+Alt+1"),
            KeyConfig(gpio=2, keycode="Keycode.TWO", modifier="Keycode.CONTROL+Keycode.ALT", label="Ctrl+Alt+2"),
            KeyConfig(gpio=3, keycode="Keycode.THREE", modifier="Keycode.CONTROL+Keycode.ALT", label="Ctrl+Alt+3"),
            KeyConfig(gpio=4, keycode="Keycode.FOUR", modifier="Keycode.CONTROL+Keycode.ALT", label="Ctrl+Alt+4"),
            KeyConfig(gpio=5, keycode="Keycode.FIVE", modifier="Keycode.CONTROL+Keycode.ALT", label="Ctrl+Alt+5"),
            KeyConfig(gpio=6, keycode="Keycode.SIX", modifier="Keycode.CONTROL+Keycode.ALT", label="Ctrl+Alt+6"),
            KeyConfig(gpio=7, keycode="Keycode.SEVEN", modifier="Keycode.CONTROL+Keycode.ALT", label="Ctrl+Alt+7"),
            KeyConfig(gpio=8, keycode="Keycode.EIGHT", modifier="Keycode.CONTROL+Keycode.ALT", label="Ctrl+Alt+8"),
            KeyConfig(gpio=9, keycode="Keycode.NINE", modifier="Keycode.CONTROL+Keycode.ALT", label="Ctrl+Alt+9"),
        ]
        
        default_encoder = EncoderConfig(
            clk_gpio=11,
            dt_gpio=12,
            sw_gpio=13,
            scroll_speed=2,
            middle_click=True,
            debounce_ms=3
        )
        
        return PadConfig(keys=default_keys, encoder=default_encoder)
    
    def validate_hal_config(self, hal_config: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Walidacja konfiguracji HAL."""
        errors = []
        
        # Sprawdź przełączniki
        switches = hal_config.get("switches", {})
        used_gpios = set()
        
        for switch_key, switch_data in switches.items():
            if not isinstance(switch_data, dict):
                errors.append(f"Przełącznik {switch_key} ma nieprawidłowy format")
                continue
            
            gpio = switch_data.get("gpio")
            if gpio is None:
                errors.append(f"Przełącznik {switch_key} nie ma zdefiniowanego GPIO")
                continue
            
            if gpio in used_gpios:
                errors.append(f"GPIO {gpio} używane wielokrotnie")
            else:
                used_gpios.add(gpio)
        
        # Sprawdź enkoder
        encoder = hal_config.get("encoder", {})
        if encoder.get("enabled", True):
            for pin_key in ["clk_gpio", "dt_gpio", "sw_gpio"]:
                gpio = encoder.get(pin_key)
                if gpio is None:
                    errors.append(f"Enkoder nie ma zdefiniowanego {pin_key}")
                elif gpio in used_gpios:
                    errors.append(f"GPIO {gpio} enkodera koliduje z innym pinem")
        
        return len(errors) == 0, errors
    
    def list_profiles(self) -> List[str]:
        """Lista dostępnych profili HAL."""
        if not self.profiles_dir.exists():
            return []
        
        profiles = []
        for file in self.profiles_dir.glob("*.toml"):
            profiles.append(file.stem)
        
        return sorted(profiles)
    
    def load_profile(self, profile_name: str) -> Dict[str, Any]:
        """Wczytaj profil HAL."""
        profile_file = self.profiles_dir / f"{profile_name}.toml"
        
        if not profile_file.exists():
            raise FileNotFoundError(f"Profile {profile_name} not found")
        
        try:
            with open(profile_file, 'r', encoding='utf-8') as f:
                return toml.load(f)
        except Exception as e:
            raise ValueError(f"Error loading profile {profile_name}: {e}")
    
    def save_profile(self, profile_name: str, config: Dict[str, Any]):
        """Zapisz profil HAL."""
        profile_file = self.profiles_dir / f"{profile_name}.toml"
        
        try:
            with open(profile_file, 'w', encoding='utf-8') as f:
                toml.dump(config, f)
            print(f"✅ Zapisano profil {profile_name}")
        except Exception as e:
            print(f"❌ Błąd zapisu profilu {profile_name}: {e}")
    
    def apply_profile(self, profile_name: str):
        """Zastosuj profil HAL."""
        print(f"🔄 Applying profile: {profile_name}")
        
        # Backup current config
        backup_file = self.backups_dir / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.toml"
        if self.hal_config_file.exists():
            shutil.copy2(self.hal_config_file, backup_file)
            print(f"✅ Backup zapisany: {backup_file.name}")
        
        # Load and apply profile
        profile_config = self.load_profile(profile_name)
        
        # Merge with base config if specified
        if "base" in profile_config:
            base_file = self.hal_dir / profile_config["base"]
            if base_file.exists():
                base_config = self.load_hal_config()
                # Deep merge profile over base
                merged_config = self.merge_configs(base_config, profile_config)
                profile_config = merged_config
        
        # Save as current config
        self.save_hal_config(profile_config)
        
        # Update sync state
        sync_state = self.load_sync_state()
        sync_state["last_applied_profile"] = profile_name
        sync_state["profile_applied_at"] = datetime.now().isoformat()
        self.save_sync_state(sync_state)
        
        print(f"✅ Profil {profile_name} zastosowany")
    
    def merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Głębokie scalanie konfiguracji."""
        result = base.copy()
        
        for key, value in override.items():
            if key == "base":
                continue  # Skip base reference
            
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self.merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def create_backup(self, name: Optional[str] = None):
        """Stwórz backup aktualnej konfiguracji HAL."""
        if not name:
            name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        backup_file = self.backups_dir / f"{name}.toml"
        
        if self.hal_config_file.exists():
            shutil.copy2(self.hal_config_file, backup_file)
            print(f"✅ Backup utworzony: {backup_file}")
        else:
            print(f"⚠️ Brak pliku konfiguracyjnego do backupu")
        
        return backup_file

def main():
    """Main entry point."""
    manager = HALConfigManager()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "sync-from-hal":
            config = manager.sync_from_hal()
            print(f"Konfiguracja firmware: {len(config.keys)} przełączników, enkoder: {'tak' if config.encoder else 'nie'}")
        
        elif command == "sync-to-hal":
            # Pobierz aktualną konfigurację i zsynchronizuj do HAL
            config = manager.get_current_config()
            manager.sync_to_hal(config)
        
        elif command == "validate":
            hal_config = manager.load_hal_config()
            is_valid, errors = manager.validate_hal_config(hal_config)
            if is_valid:
                print("✅ Konfiguracja HAL jest poprawna")
            else:
                print("❌ Błędy w konfiguracji HAL:")
                for error in errors:
                    print(f"  - {error}")
        
        elif command == "show":
            hal_config = manager.load_hal_config()
            print("Aktualna konfiguracja HAL:")
            print(json.dumps(hal_config, indent=2, ensure_ascii=False))
        
        elif command == "profiles":
            profiles = manager.list_profiles()
            print("Dostępne profile:")
            for profile in profiles:
                print(f"  - {profile}")
        
        elif command == "apply-profile" and len(sys.argv) > 2:
            profile_name = sys.argv[2]
            manager.apply_profile(profile_name)
        
        elif command == "save-profile" and len(sys.argv) > 2:
            profile_name = sys.argv[2]
            hal_config = manager.load_hal_config()
            manager.save_profile(profile_name, hal_config)
        
        elif command == "backup":
            manager.create_backup()
        
        else:
            print("Dostępne komendy:")
            print("  sync-from-hal   - Synchronizuj HAL → Firmware")
            print("  sync-to-hal     - Synchronizuj Firmware → HAL")
            print("  validate        - Waliduj konfigurację HAL")
            print("  show            - Pokaż konfigurację HAL")
            print("  profiles        - Lista dostępnych profili")
            print("  apply-profile X - Zastosuj profil X")
            print("  save-profile X  - Zapisz aktualną konfigurację jako profil X")
            print("  backup          - Stwórz backup konfiguracji")
    else:
        # Domyślnie - pokaż aktualną konfigurację
        config = manager.get_current_config()
        print(f"🔧 Aktualna konfiguracja:")
        print(f"  Przełączniki: {len(config.keys)}")
        for i, key in enumerate(config.keys, 1):
            print(f"    {i}. GPIO{key.gpio} → {key.modifier}+{key.keycode}")
        if config.encoder:
            print(f"  Enkoder: GPIO{config.encoder.clk_gpio}/{config.encoder.dt_gpio}/{config.encoder.sw_gpio}")

if __name__ == "__main__":
    main()
