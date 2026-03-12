#!/usr/bin/env python3
"""
RP2040 Keyboard Auto-Deployer
============================
Automatyczne pobieranie bibliotek i deployment na urządzenie CircuitPython.
"""

import os
import sys
import time
import json
import shutil
import zipfile
import requests
import subprocess
from pathlib import Path
from datetime import datetime

class RP2040Deployer:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.env_file = self.project_root / ".env"
        self.config = self.load_config()
        
    def load_config(self):
        """Wczytaj konfigurację z .env pliku."""
        config = {}
        if self.env_file.exists():
            with open(self.env_file, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        config[key] = value
        return config
    
    def save_config(self):
        """Zapisz konfigurację do .env pliku."""
        with open(self.env_file, 'w') as f:
            for key, value in self.config.items():
                f.write(f"{key}={value}\n")
    
    def detect_circuitpy_devices(self):
        """Wykryj podłączone urządzenia CircuitPython."""
        print("🔍 Wykrywanie urządzeń CircuitPython...")
        
        devices = []
        
        # Sprawdź common mount points dla różnych systemów
        mount_points = [
            "/media/",  # Linux
            "/mnt/",     # Linux
            "/run/media/",  # Linux
            os.path.expanduser("~/Desktop/"),  # macOS/Windows
        ]
        
        for mount_point in mount_points:
            if os.path.exists(mount_point):
                for item in os.listdir(mount_point):
                    item_path = Path(mount_point) / item
                    if item_path.is_dir():
                        # Sprawdź czy to urządzenie CircuitPython
                        if self.is_circuitpy_device(item_path):
                            devices.append({
                                'path': str(item_path),
                                'name': item,
                                'detected_at': datetime.now().isoformat()
                            })
        
        # Sprawdź też w /Volumes dla macOS
        if os.path.exists("/Volumes"):
            for item in os.listdir("/Volumes"):
                item_path = Path("/Volumes") / item
                if item_path.is_dir() and self.is_circuitpy_device(item_path):
                    devices.append({
                        'path': str(item_path),
                        'name': item,
                        'detected_at': datetime.now().isoformat()
                    })
        
        return devices
    
    def is_circuitpy_device(self, path):
        """Sprawdź czy ścieżka to urządzenie CircuitPython."""
        try:
            # Sprawdź charakterystyczne pliki
            main_py = path / "main.py"
            code_py = path / "code.py"
            boot_py = path / "boot.py"
            lib_dir = path / "lib"
            
            # Jeśli istnieje code.py lub boot.py, to prawdopodobnie CircuitPython
            if code_py.exists() or boot_py.exists():
                return True
                
            # Sprawdź info.txt (czasem istnieje)
            info_txt = path / "info.txt"
            if info_txt.exists():
                try:
                    content = info_txt.read_text().lower()
                    if "circuitpython" in content:
                        return True
                except:
                    pass
                    
            return False
        except:
            return False
    
    def download_library(self, url, extract_to):
        """Pobierz i rozpakuj bibliotekę."""
        print(f"📥 Pobieranie: {url}")
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            # Zapisz zip
            zip_path = extract_to / "temp.zip"
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            # Rozpakuj
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
            
            # Usuń zip
            zip_path.unlink()
            
            print(f"✅ Rozpakowano do: {extract_to}")
            return True
            
        except Exception as e:
            print(f"❌ Błąd pobierania: {e}")
            return False
    
    def setup_libraries(self):
        """Pobierz i przygotuj biblioteki."""
        print("📚 Przygotowywanie bibliotek...")
        
        cache_dir = Path(self.config.get('LIBRARY_CACHE_DIR', './lib_cache'))
        cache_dir.mkdir(exist_ok=True)
        
        libraries = {
            'hid': self.config.get('HID_LIBRARY_URL', 
                'https://github.com/adafruit/Adafruit_CircuitPython_HID/archive/refs/heads/main.zip'),
            'rotaryio': self.config.get('ROTARYIO_LIBRARY_URL',
                'https://github.com/adafruit/Adafruit_CircuitPython_RotaryIO/archive/refs/heads/main.zip')
        }
        
        for lib_name, url in libraries.items():
            lib_dir = cache_dir / lib_name
            lib_dir.mkdir(exist_ok=True)
            
            if not self.download_library(url, lib_dir):
                print(f"❌ Nie udało się pobrać biblioteki {lib_name}")
                return False
        
        return True
    
    def deploy_to_device(self, device_path):
        """Wdróż pliki na urządzenie."""
        print(f"🚀 Deployment na: {device_path}")
        
        device_path = Path(device_path)
        
        # Utwórz katalog lib jeśli nie istnieje
        lib_dir = device_path / "lib"
        lib_dir.mkdir(exist_ok=True)
        
        # Skopiuj biblioteki
        cache_dir = Path(self.config.get('LIBRARY_CACHE_DIR', './lib_cache'))
        
        if (cache_dir / "hid").exists():
            hid_src = cache_dir / "hid"
            hid_files = list(hid_src.glob("Adafruit_CircuitPython_HID-*/adafruit_hid"))
            if hid_files:
                hid_dest = lib_dir / "adafruit_hid"
                if hid_dest.exists():
                    shutil.rmtree(hid_dest)
                shutil.copytree(hid_files[0], hid_dest)
                print(f"✓ Skopiowano adafruit_hid")
        
        if (cache_dir / "rotaryio").exists():
            rotary_src = cache_dir / "rotaryio"
            rotary_files = list(rotary_src.glob("Adafruit_CircuitPython_RotaryIO-*/adafruit_rotaryio"))
            if rotary_files:
                rotary_dest = lib_dir / "adafruit_rotaryio"
                if rotary_dest.exists():
                    shutil.rmtree(rotary_dest)
                shutil.copytree(rotary_files[0], rotary_dest)
                print(f"✓ Skopiowano adafruit_rotaryio")
        
        # Skopiuj firmware
        firmware_dir = self.project_root / "firmware"
        
        # Backup istniejących plików
        if self.config.get('BACKUP_EXISTING_FILES', 'true').lower() == 'true':
            self.backup_device_files(device_path)
        
        # Skopiuj boot.py i code.py
        boot_src = firmware_dir / "boot.py"
        code_src = firmware_dir / "code.py"
        
        if boot_src.exists():
            shutil.copy2(boot_src, device_path / "boot.py")
            print(f"✓ Skopiowano boot.py")
        
        if code_src.exists():
            shutil.copy2(code_src, device_path / "code.py")
            print(f"✓ Skopiowano code.py")
        
        print(f"🎉 Deployment zakończony!")
        return True
    
    def backup_device_files(self, device_path):
        """Stwórz backup istniejących plików."""
        print("💾 Tworzenie backupu...")
        
        backup_dir = self.project_root / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        files_to_backup = ["boot.py", "code.py", "main.py"]
        
        for file_name in files_to_backup:
            src = Path(device_path) / file_name
            if src.exists():
                shutil.copy2(src, backup_dir / file_name)
                print(f"✓ Zbackupowano {file_name}")
        
        # Backup lib directory
        lib_src = Path(device_path) / "lib"
        if lib_src.exists():
            shutil.copytree(lib_src, backup_dir / "lib")
            print(f"✓ Zbackupowano lib/")
    
    def auto_deploy(self):
        """Automatyczny deployment."""
        print("🤖 RP2040 Auto-Deployer")
        print("=" * 40)
        
        # Wykryj urządzenia
        devices = self.detect_circuitpy_devices()
        
        if not devices:
            print("❌ Nie wykryto urządzeń CircuitPython")
            print("Podłącz RP2040-One i uruchom ponownie")
            return False
        
        print(f"✅ Wykryto {len(devices)} urządzeń:")
        for i, device in enumerate(devices, 1):
            print(f"  {i}. {device['name']} -> {device['path']}")
        
        # Przygotuj biblioteki
        if not self.setup_libraries():
            print("❌ Nie udało się przygotować bibliotek")
            return False
        
        # Deploy na każde urządzenie
        for device in devices:
            print(f"\n🚀 Deployment na {device['name']}...")
            
            if self.deploy_to_device(device['path']):
                # Zapisz informacje o urządzeniu
                self.config['CIRCUITPY_DEVICE_PATH'] = device['path']
                self.config['CIRCUITPY_DEVICE_NAME'] = device['name']
                self.config['LAST_DEVICE_DETECTION'] = device['detected_at']
                self.save_config()
                
                print(f"✅ Gotowe! {device['name']} jest gotowe do użycia")
            else:
                print(f"❌ Błąd deploymentu na {device['name']}")
        
        return True
    
    def monitor_devices(self, interval=5):
        """Monitoruj podłączane urządzenia."""
        print(f"👀 Monitorowanie urządzeń (co {interval}s)...")
        print("Naciśnij Ctrl+C aby zakończyć")
        
        try:
            while True:
                devices = self.detect_circuitpy_devices()
                
                if devices:
                    current_device = devices[0]['path']
                    last_device = self.config.get('CIRCUITPY_DEVICE_PATH')
                    
                    if current_device != last_device:
                        print(f"\n🔌 Wykryto nowe urządzenie: {devices[0]['name']}")
                        
                        if self.config.get('AUTO_DEPLOY_ON_BOOT', 'true').lower() == 'true':
                            self.auto_deploy()
                    
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n👋 Zakończono monitorowanie")

def main():
    """Main entry point."""
    deployer = RP2040Deployer()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "detect":
            devices = deployer.detect_circuitpy_devices()
            if devices:
                print("Wykryte urządzenia:")
                for device in devices:
                    print(f"  - {device['name']}: {device['path']}")
            else:
                print("Brak wykrytych urządzeń")
        
        elif command == "deploy":
            deployer.auto_deploy()
        
        elif command == "monitor":
            deployer.monitor_devices()
        
        elif command == "setup":
            deployer.setup_libraries()
        
        else:
            print("Dostępne komendy:")
            print("  detect  - Wykryj urządzenia")
            print("  deploy  - Automatyczny deployment")
            print("  monitor - Monitoruj urządzenia")
            print("  setup   - Pobierz biblioteki")
    else:
        # Domyślnie - automatyczny deployment
        deployer.auto_deploy()

if __name__ == "__main__":
    main()
