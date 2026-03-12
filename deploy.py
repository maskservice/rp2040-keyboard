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
import urllib.request
import subprocess
from pathlib import Path
from datetime import datetime

# Dodaj ścieżkę do projektu
sys.path.insert(0, str(Path(__file__).parent))

from rp2040_keyboard.hal_manager import HALConfigManager

class RP2040Deployer:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.env_file = self.project_root / ".env"
        self.config = self.load_config()
        self.hal_manager = HALConfigManager(self.project_root)
        
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
    
    def mount_circuitpy_device(self):
        """Znajdź i zamontuj niezamontowane urządzenie CIRCUITPY."""
        print("🔍 Szukam niezamontowanego urządzenia CIRCUITPY...")
        
        # Sprawdź /dev/disk/by-label/ dla CIRCUITPY
        by_label_path = Path("/dev/disk/by-label/")
        if by_label_path.exists():
            for link in by_label_path.iterdir():
                if link.name.upper() == "CIRCUITPY":
                    # Znaleziono urządzenie, sprawdź czy już zamontowane
                    device_real = os.path.realpath(link)
                    print(f"   ✓ Znaleziono urządzenie: {device_real}")
                    
                    # Spróbuj zamontować używając udisksctl
                    try:
                        result = subprocess.run(
                            ["udisksctl", "mount", "-b", device_real],
                            capture_output=True, text=True, timeout=10
                        )
                        if result.returncode == 0:
                            # Wyciągnij ścieżkę mount z outputu
                            mount_path = self._extract_mount_path(result.stdout)
                            if mount_path:
                                print(f"   ✓ Zamontowano w: {mount_path}")
                                return mount_path
                        else:
                            print(f"   ⚠️ udisksctl error: {result.stderr}")
                    except (subprocess.TimeoutExpired, FileNotFoundError):
                        pass
                    
                    # Fallback - spróbuj zamontować ręcznie
                    mount_point = "/media/tom/CIRCUITPY"
                    try:
                        os.makedirs(mount_point, exist_ok=True)
                        result = subprocess.run(
                            ["sudo", "mount", device_real, mount_point],
                            capture_output=True, text=True, timeout=5
                        )
                        if result.returncode == 0:
                            print(f"   ✓ Zamontowano w: {mount_point}")
                            return mount_point
                    except (subprocess.TimeoutExpired, FileNotFoundError):
                        pass
                    
                    print(f"   ⚠️ Nie udało się zamontować {device_real}")
        
        return None
    
    def _extract_mount_path(self, udisks_output):
        """Wyciągnij ścieżkę mount z outputu udisksctl."""
        # Output format: "Mounted /dev/sdX1 at /media/tom/CIRCUITPY"
        if "at " in udisks_output:
            parts = udisks_output.split("at ")
            if len(parts) > 1:
                return parts[1].strip().rstrip(".")
        return None
    
    def detect_circuitpy_devices(self):
        """Wykryj podłączone urządzenia CircuitPython."""
        print("🔍 Wykrywanie urządzeń CircuitPython...")
        
        devices = []
        
        # Bezpośrednie sprawdzenie CIRCUITPY
        direct_circuitpy = "/media/tom/CIRCUITPY"
        if Path(direct_circuitpy).exists():
            if self.is_circuitpy_device(Path(direct_circuitpy)):
                devices.append({
                    'path': direct_circuitpy,
                    'name': 'CIRCUITPY',
                    'detected_at': datetime.now().isoformat()
                })
                print(f"   ✓ Znaleziono: {direct_circuitpy}")
                return devices
        
        # Jeśli nie zamontowane, spróbuj zamontować
        mounted_path = self.mount_circuitpy_device()
        if mounted_path:
            devices.append({
                'path': mounted_path,
                'name': 'CIRCUITPY',
                'detected_at': datetime.now().isoformat()
            })
            print(f"   ✓ Zamontowano i wykryto: {mounted_path}")
            return devices
        
        # Sprawdź common mount points dla różnych systemów
        mount_points = [
            "/media/",  # Linux
            "/mnt/",     # Linux
            "/run/media/",  # Linux
            os.path.expanduser("~/Desktop/"),  # macOS/Windows
        ]
        
        # Dodaj bezpośrednie sprawdzenie /media/tom/CIRCUITPY
        direct_paths = [
            "/media/tom/CIRCUITPY",
            "/media/*/CIRCUITPY",
            "/mnt/*/CIRCUITPY",
        ]
        
        # Sprawdź bezpośrednie ścieżki
        for pattern in direct_paths:
            if '*' in pattern:
                # Użyj glob dla wzorców
                from glob import glob
                for path in glob(pattern):
                    if self.is_circuitpy_device(Path(path)):
                        devices.append({
                            'path': path,
                            'name': Path(path).name,
                            'detected_at': datetime.now().isoformat()
                        })
            else:
                if self.is_circuitpy_device(Path(pattern)):
                    devices.append({
                        'path': pattern,
                        'name': Path(pattern).name,
                        'detected_at': datetime.now().isoformat()
                    })
        
        # Sprawdź standardowe mount points
        for mount_point in mount_points:
            if os.path.exists(mount_point):
                try:
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
                except PermissionError:
                    # Pomiń katalogi do których nie mamy dostępu
                    continue
                except Exception:
                    continue
        
        # Sprawdź też w /Volumes dla macOS
        if os.path.exists("/Volumes"):
            try:
                for item in os.listdir("/Volumes"):
                    item_path = Path("/Volumes") / item
                    if item_path.is_dir() and self.is_circuitpy_device(item_path):
                        devices.append({
                            'path': str(item_path),
                            'name': item,
                            'detected_at': datetime.now().isoformat()
                        })
            except Exception:
                pass
        
        return devices
    
    def detect_boot_mode_devices(self):
        """Wykryj urządzenia w trybie boot (RPI-RP2)."""
        found_paths = set()  # Uniknij duplikatów
        devices = []
        
        # Ścieżki do RPI-RP2
        boot_paths = [
            "/media/tom/RPI-RP2",
            "/media/*/RPI-RP2",
            "/mnt/*/RPI-RP2",
            "/Volumes/RPI-RP2",
        ]
        
        for pattern in boot_paths:
            if '*' in pattern:
                from glob import glob
                for path in glob(pattern):
                    if path not in found_paths and Path(path).exists():
                        found_paths.add(path)
                        devices.append({
                            'path': path,
                            'name': 'RPI-RP2',
                            'mode': 'boot',
                            'detected_at': datetime.now().isoformat()
                        })
            else:
                if pattern not in found_paths and Path(pattern).exists():
                    found_paths.add(pattern)
                    devices.append({
                        'path': pattern,
                        'name': 'RPI-RP2',
                        'mode': 'boot',
                        'detected_at': datetime.now().isoformat()
                    })
        
        return devices
    
    def flash_uf2(self, device_path):
        """Wgraj firmware UF2 w trybie boot."""
        print(f"🔥 Flashowanie firmware na {device_path}...")
        
        # Znajdź plik UF2
        uf2_files = list(self.project_root.glob("*.uf2"))
        if not uf2_files:
            print("❌ Nie znaleziono pliku .uf2 w katalogu projektu")
            return False
        
        # Użyj pierwszego znalezionego UF2 (najnowszego)
        uf2_file = uf2_files[0]
        print(f"📁 Używam: {uf2_file.name}")
        
        try:
            shutil.copy2(uf2_file, Path(device_path) / uf2_file.name)
            print(f"✅ Skopiowano {uf2_file.name}")
            print("⏳ Czekam na zrestartowanie do trybu CircuitPython...")
            print("   (jeśli się nie zrestartuje, odłącz i podłącz ponownie RP2040)")
            
            # Czekaj na przełączenie do CIRCUITPY (max 60s)
            for i in range(60):
                time.sleep(1)
                # Próbuj zamontować jeśli nie wykryte
                if i % 5 == 0:
                    circuitpy_devices = self.detect_circuitpy_devices()
                else:
                    # Szybkie sprawdzenie bez logowania
                    circuitpy_devices = self._quick_check_circuitpy()
                
                if circuitpy_devices:
                    print(f"✅ Wykryto CIRCUITPY po {i+1}s")
                    return True
                if i % 10 == 0 and i > 0:
                    print(f"   ... czekam ({i}s)")
            
            print("⚠️ Timeout - urządzenie nie przeszło w tryb CircuitPython")
            
            # Diagnostyka - sprawdź czy urządzenie jest widoczne
            print("\n🔍 DIAGNOSTYKA:")
            self._diagnose_usb_device()
            
            print("\n💡 Spróbuj: odłącz i podłącz ponownie RP2040, potem uruchom deploy")
            return False
            
        except Exception as e:
            print(f"❌ Błąd flashowania: {e}")
            return False
    
    def _diagnose_usb_device(self):
        """Diagnostyka widoczności urządzenia USB w systemie."""
        # Sprawdź /dev/disk/by-label/
        by_label = Path("/dev/disk/by-label/")
        if by_label.exists():
            labels = [l.name for l in by_label.iterdir()]
            circuitpy_labels = [l for l in labels if "CIRCUIT" in l.upper()]
            if circuitpy_labels:
                print(f"   ✓ Znaleziono etykiety CIRCUITPY: {circuitpy_labels}")
            else:
                print(f"   ✗ Brak CIRCUITPY w /dev/disk/by-label/")
                print(f"     Dostępne etykiety: {labels}")
        else:
            print("   ✗ Brak katalogu /dev/disk/by-label/")
        
        # Sprawdź lsusb dla RP2040
        try:
            result = subprocess.run(
                ["lsusb"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                rp2040_lines = [l for l in lines if any(x in l.lower() for x in 
                    ['rp2040', 'pico', 'wave', '2e8a', '239a', '239b'])]
                if rp2040_lines:
                    print(f"   ✓ RP2040 widoczne w USB:")
                    for line in rp2040_lines:
                        print(f"     {line}")
                else:
                    print("   ✗ RP2040 NIE widoczne w lsusb")
                    print(f"     Wszystkie urządzenia USB: {len(lines)}")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            print("   ⚠️ Nie można uruchomić lsusb")
        
        # Sprawdź nowe urządzenia blokowe
        try:
            result = subprocess.run(
                ["lsblk", "-f"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                # Szukaj urządzeń FAT12/FAT16/FAT32 (typowe dla CIRCUITPY)
                small_devices = [l for l in lines if any(fs in l for fs in 
                    ['FAT12', 'FAT16', 'FAT32', 'CIRCUIT', 'RPI-RP2'])]
                if small_devices:
                    print(f"   ✓ Znaleziono urządzenia pamięci masowej:")
                    for line in small_devices:
                        print(f"     {line}")
                else:
                    print("   ✗ Brak nowych urządzeń pamięci masowej")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            print("   ⚠️ Nie można uruchomić lsblk")
    
    def _quick_check_circuitpy(self):
        """Szybkie sprawdzenie bez logowania - używane w pętli oczekiwania."""
        direct_circuitpy = "/media/tom/CIRCUITPY"
        if Path(direct_circuitpy).exists():
            return [{'path': direct_circuitpy, 'name': 'CIRCUITPY'}]
        
        # Sprawdź czy jest niezamontowane urządzenie
        by_label_path = Path("/dev/disk/by-label/")
        if by_label_path.exists():
            for link in by_label_path.iterdir():
                if link.name.upper() == "CIRCUITPY":
                    # Spróbuj zamontować
                    mounted = self.mount_circuitpy_device()
                    if mounted:
                        return [{'path': mounted, 'name': 'CIRCUITPY'}]
        return []
    
    def is_circuitpy_device(self, path):
        """Sprawdź czy ścieżka to urządzenie CircuitPython."""
        try:
            path = Path(path)
            
            # Sprawdź czy ścieżka istnieje i jest katalogiem
            if not path.exists() or not path.is_dir():
                return False
            
            # Jeśli nazwa to CIRCUITPY, to prawdopodobnie to on (mount point)
            if path.name.upper() == "CIRCUITPY":
                return True
            
            # Sprawdź charakterystyczne pliki
            main_py = path / "main.py"
            code_py = path / "code.py"
            boot_py = path / "boot.py"
            lib_dir = path / "lib"
            boot_out_txt = path / "boot_out.txt"
            
            # Jeśli istnieje boot_out.txt z CircuitPython - to pewne
            if boot_out_txt.exists():
                try:
                    content = boot_out_txt.read_text().lower()
                    if "circuitpython" in content:
                        return True
                except:
                    pass
            
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
            # Pobierz plik używając urllib
            with urllib.request.urlopen(url) as response:
                zip_data = response.read()
            
            # Zapisz zip
            zip_path = extract_to / "temp.zip"
            with open(zip_path, 'wb') as f:
                f.write(zip_data)
            
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
            # rotaryio jest wbudowane w CircuitPython, nie trzeba pobierać
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
        
        # Synchronizuj konfigurację HAL przed deploymentem
        if self.config.get('SYNC_HAL_BEFORE_DEPLOY', 'true').lower() == 'true':
            print("🔄 Synchronizacja konfiguracji HAL...")
            try:
                config = self.hal_manager.get_current_config()
                self.hal_manager.sync_to_hal(config)
                print("✅ Konfiguracja HAL zsynchronizowana")
            except Exception as e:
                print(f"⚠️ Błąd synchronizacji HAL: {e}")
        
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
        
        # rotaryio jest wbudowane w CircuitPython, nie trzeba kopiować
        print(f"✓ rotaryio jest wbudowane w CircuitPython")
        
        # Skopiuj firmware
        firmware_dir = self.project_root / "rp2040_keyboard" / "firmware"
        
        # Backup istniejących plików
        if self.config.get('BACKUP_EXISTING_FILES', 'true').lower() == 'true':
            self.backup_device_files(device_path)
        
        # Wygeneruj firmware z aktualnej konfiguracji HAL
        try:
            from rp2040_keyboard.firmware import generate_code_py
            from rp2040_keyboard.firmware import BOOT_PY
            
            # Pobierz aktualną konfigurację z HAL
            config = self.hal_manager.get_current_config()
            
            # Wygeneruj kod
            generated_code = generate_code_py(config)
            generated_boot = BOOT_PY.strip()
            
            # Zapisz wygenerowane pliki
            with open(device_path / "code.py", 'w') as f:
                f.write(generated_code)
            print(f"✓ Wygenerowano code.py z konfiguracji HAL")
            
            with open(device_path / "boot.py", 'w') as f:
                f.write(generated_boot)
            print(f"✓ Wygenerowano boot.py")
            
        except Exception as e:
            print(f"⚠️ Błąd generowania firmware: {e}")
            print("Kopiuję statyczne pliki firmware...")
            
            # Fallback do statycznych plików
            boot_src = firmware_dir / "boot_template.py"
            code_src = firmware_dir / "code.py"
            
            if boot_src.exists():
                with open(boot_src, 'r') as f:
                    boot_content = f.read()
                # Wyodrębnij BOOT_PY z pliku
                if "BOOT_PY = '''" in boot_content:
                    start = boot_content.find("BOOT_PY = '''") + 12
                    end = boot_content.find("'''", start)
                    boot_code = boot_content[start:end]
                    with open(device_path / "boot.py", 'w') as f:
                        f.write(boot_code)
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
        print()
        print("📋 INSTRUKCJA:")
        print("   1. Podłącz RP2040 do USB")
        print("   2. Jeśli w trybie BOOT (RPI-RP2) - wgram firmware")
        print("   3. Jeśli w trybie CIRCUITPY - wgram kod aplikacji")
        print()
        
        # Najpierw sprawdź tryb boot (RPI-RP2)
        boot_devices = self.detect_boot_mode_devices()
        if boot_devices:
            print(f"🔥 Wykryto {len(boot_devices)} urządzeń w trybie BOOT:")
            for device in boot_devices:
                print(f"  • {device['name']} -> {device['path']}")
            print()
            print("💡 To świeży/fabryczny RP2040. Wgrywam firmware CircuitPython...")
            print()
            
            for device in boot_devices:
                print(f"🔥 Flashowanie {device['name']}...")
                if self.flash_uf2(device['path']):
                    print("✅ Firmware wgrany!")
                    print()
                    print("⏳ Czekam na zainicjalizowanie systemu plików CIRCUITPY...")
                    time.sleep(3)  # Poczekaj na pełne zamontowanie
                    print()
                else:
                    print("❌ Błąd flashowania")
                    return False
        
        # Teraz sprawdź tryb CircuitPython
        devices = self.detect_circuitpy_devices()
        
        if not devices:
            print("❌ Nie wykryto urządzeń CircuitPython")
            print()
            if not boot_devices:
                print("💡 CO ZROBIĆ:")
                print("   1. Podłącz RP2040 do USB (zwykłe podłączenie)")
                print("   2. Lub wejdź w tryb BOOT:")
                print("      • Przytrzymaj przycisk BOOT na RP2040")
                print("      • Naciśnij RESET (lub odłącz i podłącz USB)")
                print("      • Puść BOOT gdy dioda zacznie migać")
                print("   3. Uruchom ponownie: make deploy")
                print()
                # Diagnostyka gdy brak urządzenia
                print("🔍 DIAGNOSTYKA SYSTEMU:")
                self._diagnose_usb_device()
            else:
                # Był w trybie boot, został wgrany UF2, ale nie pojawił się CIRCUITPY
                print("⚠️  Firmware wgrany, ale CIRCUITPY się nie pojawił")
                print()
                print("🔍 DIAGNOSTYKA:")
                self._diagnose_usb_device()
                print()
                print("💡 NASTĘPNY KROK (wymagany!):")
                print("   Po wgraniu firmware UF2, RP2040 wymaga FIZYCZNEGO odłączenia:")
                print()
                print("   1. Odłącz kabel USB od RP2040")
                print("   2. Poczekaj 3 sekundy")
                print("   3. Podłącz ponownie (zwykłe podłączenie, bez BOOT)")
                print("   4. Uruchom: make deploy")
                print()
            return False
        
        print(f"✅ Wykryto {len(devices)} urządzeń CIRCUITPY:")
        for i, device in enumerate(devices, 1):
            print(f"  {i}. {device['name']} -> {device['path']}")
        print()
        print("📦 Rozpoczynam deployment kodu aplikacji...")
        print()
        
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
