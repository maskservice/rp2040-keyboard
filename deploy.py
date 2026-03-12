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
import errno
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
        self.username = os.environ.get("USER") or os.environ.get("USERNAME") or "tom"
        
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

    def _sync_path(self, path):
        path = Path(path)
        try:
            if path.exists() and path.is_file():
                with open(path, 'rb') as f:
                    os.fsync(f.fileno())
        except OSError:
            pass

        try:
            parent = path.parent if path.parent.exists() else None
            if parent:
                fd = os.open(parent, os.O_RDONLY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
        except OSError:
            pass

        os.sync()

    def _get_free_space(self, path):
        try:
            stats = os.statvfs(path)
            return stats.f_bavail * stats.f_frsize
        except OSError:
            return None

    def _ensure_target_ready(self, target_dir, required_bytes=0):
        target_dir = Path(target_dir)
        if not target_dir.exists() or not target_dir.is_dir():
            raise FileNotFoundError(f"Ścieżka urządzenia nie istnieje: {target_dir}")

        if not os.access(target_dir, os.W_OK):
            raise PermissionError(f"Brak prawa zapisu do: {target_dir}")

        free_bytes = self._get_free_space(target_dir)
        if free_bytes is not None and required_bytes and free_bytes < required_bytes:
            raise OSError(
                errno.ENOSPC,
                f"Za mało miejsca na urządzeniu: potrzeba {required_bytes:,} B, dostępne {free_bytes:,} B"
            )

    def _copy_file_verified(self, src_path, dest_path, label=None):
        src_path = Path(src_path)
        dest_path = Path(dest_path)
        label = label or dest_path.name

        self._ensure_target_ready(dest_path.parent, src_path.stat().st_size)
        shutil.copy2(src_path, dest_path)
        self._sync_path(dest_path)

        if not dest_path.exists():
            raise IOError(f"{label}: plik nie istnieje po kopiowaniu")

        src_size = src_path.stat().st_size
        dst_size = dest_path.stat().st_size
        if src_size != dst_size:
            raise IOError(
                f"{label}: rozmiar po kopiowaniu niezgodny (src={src_size:,} B, dst={dst_size:,} B)"
            )

        return dst_size

    def _write_text_verified(self, dest_path, content, label=None):
        dest_path = Path(dest_path)
        label = label or dest_path.name
        encoded = content.encode("utf-8")

        self._ensure_target_ready(dest_path.parent, len(encoded))
        with open(dest_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())

        self._sync_path(dest_path)

        if not dest_path.exists():
            raise IOError(f"{label}: plik nie istnieje po zapisie")

        if dest_path.stat().st_size != len(encoded):
            raise IOError(
                f"{label}: rozmiar po zapisie niezgodny (expected={len(encoded):,} B, actual={dest_path.stat().st_size:,} B)"
            )

        return dest_path.stat().st_size

    def _wait_for_circuitpy_after_flash(self, previous_boot_path=None, timeout=60):
        previous_boot_path = Path(previous_boot_path) if previous_boot_path else None
        boot_path_gone = False

        for i in range(timeout):
            time.sleep(1)

            if previous_boot_path and not boot_path_gone and not previous_boot_path.exists():
                boot_path_gone = True
                print("   ✓ RPI-RP2 zniknął z systemu plików")

            quick_devices = self._quick_check_circuitpy()
            if quick_devices:
                print(f"✅ Wykryto CIRCUITPY po {i+1}s")
                print("🎉 RP2040 zrestartował się pomyślnie!")
                print()
                return True

            if i % 10 == 0 and i > 0:
                print(f"   ... czekam na restart ({i}s)")

        if self._find_device_by_label("CIRCUITPY"):
            mounted = self.mount_circuitpy_device()
            if mounted:
                print("✅ Wykryto CIRCUITPY po końcowej próbie montowania")
                print()
                return True

        return False

    def _label_mount_patterns(self, label):
        label = label.upper()
        return [
            f"/media/{self.username}/{label}",
            f"/media/*/{label}",
            f"/mnt/*/{label}",
            f"/run/media/{self.username}/{label}",
            f"/run/media/*/{label}",
            f"/Volumes/{label}",
        ]

    def _find_mounted_label_paths(self, label):
        from glob import glob

        found = []
        seen = set()
        for pattern in self._label_mount_patterns(label):
            for path in glob(pattern):
                resolved = str(Path(path).resolve())
                if resolved not in seen and Path(path).exists():
                    seen.add(resolved)
                    found.append(path)
        return found

    def _find_device_by_label(self, label):
        by_label_path = Path("/dev/disk/by-label/")
        if not by_label_path.exists():
            return None

        for link in by_label_path.iterdir():
            if link.name.upper() == label.upper():
                return os.path.realpath(link)
        return None
    
    def mount_circuitpy_device(self):
        """Znajdź i zamontuj niezamontowane urządzenie CIRCUITPY."""
        print("🔍 Szukam niezamontowanego urządzenia CIRCUITPY...")

        device_real = self._find_device_by_label("CIRCUITPY")
        if device_real:
            print(f"   ✓ Znaleziono urządzenie: {device_real}")

            try:
                result = subprocess.run(
                    ["udisksctl", "mount", "-b", device_real],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    mount_path = self._extract_mount_path(result.stdout)
                    if mount_path:
                        print(f"   ✓ Zamontowano w: {mount_path}")
                        return mount_path
                elif result.stderr and "already mounted" not in result.stderr.lower():
                    print(f"   ⚠️ udisksctl error: {result.stderr}")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

            mounted_paths = self._find_mounted_label_paths("CIRCUITPY")
            if mounted_paths:
                print(f"   ✓ Wykryto istniejący mount: {mounted_paths[0]}")
                return mounted_paths[0]

            mount_point = f"/media/{self.username}/CIRCUITPY"
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
        
        found_paths = set()  # Uniknij duplikatów
        devices = []
        
        def _add_device(path_str, name=None):
            """Dodaj urządzenie jeśli nie jest duplikatem."""
            real_path = str(Path(path_str).resolve())
            if real_path not in found_paths:
                found_paths.add(real_path)
                devices.append({
                    'path': path_str,
                    'name': name or Path(path_str).name,
                    'detected_at': datetime.now().isoformat()
                })
                return True
            return False
        
        direct_paths = self._find_mounted_label_paths("CIRCUITPY")
        for direct_circuitpy in direct_paths:
            if self.is_circuitpy_device(Path(direct_circuitpy)):
                _add_device(direct_circuitpy, 'CIRCUITPY')
                print(f"   ✓ Znaleziono: {direct_circuitpy}")
                return devices
        
        # Jeśli nie zamontowane, spróbuj zamontować
        mounted_path = self.mount_circuitpy_device()
        if mounted_path:
            _add_device(mounted_path, 'CIRCUITPY')
            print(f"   ✓ Zamontowano i wykryto: {mounted_path}")
            return devices
        
        # Sprawdź ścieżki glob
        from glob import glob
        search_patterns = self._label_mount_patterns("CIRCUITPY")
        
        for pattern in search_patterns:
            for path in glob(pattern):
                if self.is_circuitpy_device(Path(path)):
                    _add_device(path)
        
        # Sprawdź /Volumes dla macOS
        if os.path.exists("/Volumes"):
            try:
                for item in os.listdir("/Volumes"):
                    item_path = Path("/Volumes") / item
                    if item_path.is_dir() and self.is_circuitpy_device(item_path):
                        _add_device(str(item_path), item)
            except Exception:
                pass
        
        return devices
    
    def detect_boot_mode_devices(self):
        """Wykryj urządzenia w trybie boot (RPI-RP2)."""
        found_paths = set()  # Uniknij duplikatów
        devices = []

        boot_paths = self._label_mount_patterns("RPI-RP2")
        
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
        
        # Preferuj oficjalny plik CircuitPython (en_US) zamiast lokalizacji
        preferred_uf2 = None
        official_uf2 = None
        
        for uf2_file in uf2_files:
            if "circuitpython-waveshare_rp2040_one-en_US" in uf2_file.name:
                official_uf2 = uf2_file
            elif "circuitpython-waveshare_rp2040_one" in uf2_file.name and "en_US" not in uf2_file.name:
                preferred_uf2 = uf2_file
        
        # Użyj oficjalnego pliku jeśli dostępny
        uf2_file = official_uf2 or preferred_uf2 or uf2_files[0]
        print(f"📁 Używam: {uf2_file.name}")
        
        # Sprawdź rozmiar pliku
        file_size = uf2_file.stat().st_size
        print(f"📏 Rozmiar: {file_size:,} bytes")
        
        # Wyodrębnij wersję z nazwy pliku
        if "9.2.0" in uf2_file.name:
            print("🔧 Wersja CircuitPython: 9.2.0 (oficjalna)")
        elif "10.1.4" in uf2_file.name:
            print("🔧 Wersja CircuitPython: 10.1.4 (polska)")
            print("⚠️  Uwaga: polska wersja może mieć problemy z restartem")
        else:
            print("🔧 Wersja CircuitPython: nieznana")
        
        if file_size < 1000000 or file_size > 3000000:
            print(f"⚠️  Podejrzany rozmiar pliku: {file_size:,} bytes")
            print("   Powinien być ~1.7-2.0 MB dla CircuitPython RP2040")
        
        try:
            dest_path = Path(device_path) / uf2_file.name
            print(f"📝 Kopiowanie {uf2_file.name} ({file_size:,} bytes)...")
            written_size = self._copy_file_verified(uf2_file, dest_path, "UF2")
            print("💾 Wymuszam zapis na urządzenie USB (sync)...")
            self._sync_path(dest_path)
            print(f"✅ Zapis zweryfikowany: {written_size:,} bytes")
            
            # Czekamy na pełne zakończenie zapisu USB
            print("⏳ Czekam 5s na zakończenie zapisu USB...")
            time.sleep(5)
            
            # Final sync przed zakończeniem
            self._sync_path(dest_path)
            
            # Walidacja - sprawdź czy RP2040 odczytał plik UF2
            print("🔍 Walidacja odczytu przez RP2040...")
            time.sleep(2)  # Daj RP2040 czas na odczytanie
            
            # Sprawdź czy plik UF2 zniknął (dobry znak)
            uf2_disappeared = False
            if not dest_path.exists():
                print("✅ Plik UF2 zniknął - RP2040 odczytał firmware")
                uf2_disappeared = True
            else:
                print(f"⚠️ Plik UF2 nadal widoczny na RPI-RP2")
                try:
                    remaining_size = dest_path.stat().st_size
                    print(f"   Rozmiar: {remaining_size:,} bytes")
                except:
                    pass
            
            print()
            print("⏳ Czekam na restart RP2040 do trybu CircuitPython...")
            print("   RP2040 powinien automatycznie się zrestartować po odczyciu UF2")
            print()

            if self._wait_for_circuitpy_after_flash(device_path, timeout=60):
                return True

            if uf2_disappeared:
                print("⚠️ Timeout, ale plik UF2 zniknął")
                print("💡 RP2040 odczytał firmware, ale system nie udostępnił jeszcze CIRCUITPY.")
                print("   Spróbuj ponownie: make deploy")
            else:
                print("⚠️ Timeout - RP2040 nie zrestartował się")
                print("💡 Wymagane działanie:")
                print("   1. FIZYCZNIE odłącz kabel USB od RP2040")
                print("   2. Poczekaj 3 sekundy")
                print("   3. Podłącz ponownie (zwykłe podłączenie)")
                print("   4. Uruchom: make deploy")
                print()
                print("🔍 Diagnostyka:")
                self._diagnose_usb_device()
            
            return False
            
        except Exception as e:
            print(f"❌ Błąd flashowania: {e}")
            return False
    
    def _quick_check_circuitpy(self):
        """Szybkie sprawdzenie bez logowania - używane w pętli oczekiwania."""
        for direct_circuitpy in self._find_mounted_label_paths("CIRCUITPY"):
            if Path(direct_circuitpy).exists():
                return [{'path': direct_circuitpy, 'name': 'CIRCUITPY'}]

        if self._find_device_by_label("CIRCUITPY"):
            mounted = self.mount_circuitpy_device()
            if mounted:
                return [{'path': mounted, 'name': 'CIRCUITPY'}]
        return []
    
    def _diagnose_usb_device(self):
        """Diagnostyka urządzenia USB - sprawdza fizyczne połączenie."""
        print("   Sprawdzanie połączenia USB...")
        
        # Sprawdź czy RP2040 jest widoczne na USB
        try:
            result = subprocess.run(
                ["lsusb"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            rp2040_found = False
            for line in result.stdout.split('\n'):
                if 'rp2040' in line.lower() or 'waveshare' in line.lower():
                    print(f"   ✅ Znaleziono urządzenie USB: {line.strip()}")
                    rp2040_found = True
                elif 'circuitpython' in line.lower():
                    print(f"   ✅ Znaleziono CircuitPython: {line.strip()}")
                    rp2040_found = True
                elif 'rpi-rp2' in line.lower():
                    print(f"   ✅ Znaleziono RPI-RP2: {line.strip()}")
                    rp2040_found = True
            
            if not rp2040_found:
                print("   ❌ Nie znaleziono urządzenia RP2040/CircuitPython na USB")
                print("   💡 Sprawdź:")
                print("      - Czy kabel USB jest podłączony?")
                print("      - Czy dioda na RP2040 świeci?")
                print("      - Czy port USB działa (spróbuj inny port/kabel)?")
                print("      - Czy RP2040 jest uszkodzone?")
                
                # Pokaż ostatnie urządzenia USB dla diagnostyki
                print("\n   Ostatnie urządzenia USB:")
                for line in result.stdout.split('\n')[-5:]:
                    if line.strip():
                        print(f"      {line.strip()}")
        
        except Exception as e:
            print(f"   ⚠️ Błąd sprawdzania USB: {e}")
        
        # Sprawdź urządzenia blokowe
        print("\n   Sprawdzanie urządzeń blokowych...")
        try:
            result = subprocess.run(
                ["lsblk", "-f"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            circuitpy_found = False
            for line in result.stdout.split('\n'):
                if 'circuitpy' in line.lower():
                    print(f"   ✅ Znaleziono CIRCUITPY: {line.strip()}")
                    circuitpy_found = True
                elif 'rpi-rp2' in line.lower():
                    print(f"   ✅ Znaleziono RPI-RP2: {line.strip()}")
                    circuitpy_found = True
            
            if not circuitpy_found:
                print("   ❌ Nie znaleziono CIRCUITPY/RPI-RP2 w systemie plików")
                
                # Sprawdź etykietyty dysków
                try:
                    label_result = subprocess.run(
                        ["ls", "-la", "/dev/disk/by-label/"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    
                    labels = []
                    for line in label_result.stdout.split('\n'):
                        if 'circuitpy' in line.lower() or 'rpi-rp2' in line.lower():
                            labels.append(line.strip())
                    
                    if labels:
                        print("   🔍 Znaleziono etykietyty (ale nie zamontowane):")
                        for label in labels:
                            print(f"      {label}")
                    else:
                        print("   ❌ Brak etykiet CIRCUITPY/RPI-RP2")
                        
                except Exception:
                    pass
        
        except Exception as e:
            print(f"   ⚠️ Błąd sprawdzania urządzeń blokowych: {e}")
        
        # Sprawdź procesy systemowe
        print("\n   Sprawdzanie procesów systemowych...")
        try:
            result = subprocess.run(
                ["ps", "aux"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            usb_processes = []
            for line in result.stdout.split('\n'):
                if 'usb' in line.lower() and ('storage' in line.lower() or 'mount' in line.lower()):
                    usb_processes.append(line.strip())
            
            if usb_processes:
                print("   🔍 Procesy USB/storage:")
                for proc in usb_processes[:3]:  # Pokaż max 3
                    print(f"      {proc}")
            else:
                print("   ℹ️  Brak widocznych procesów USB/storage")
        
        except Exception:
            pass
        
        print("\n   📋 PODSUMOWANIE DIAGNOZY:")
        print("   1. Jeśli nie widzisz RP2040 w lsusb → problem fizyczny (kabel/port/urządzenie)")
        print("   2. Jeśli widzisz RP2040 ale nie ma CIRCUITPY → problem z firmware")
        print("   3. Jeśli widzisz RPI-RP2 → urządzenie w trybie BOOT, potrzebuje wgrania UF2")
        print("   4. Jeśli widzisz CIRCUITPY ale nie jest zamontowane → problem z montowaniem")
    
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
        self._ensure_target_ready(device_path, 4096)
        
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
        self._sync_path(lib_dir)
        
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
                self._sync_path(hid_dest)
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
            self._write_text_verified(device_path / "code.py", generated_code, "code.py")
            print(f"✓ Wygenerowano code.py z konfiguracji HAL")
            
            self._write_text_verified(device_path / "boot.py", generated_boot, "boot.py")
            print(f"✓ Wygenerowano boot.py")
            
            # Wymusz zapis na dysk USB
            self._sync_path(device_path / "boot.py")
            self._sync_path(device_path / "code.py")
            print(f"✓ Zsynchronizowano zapis na urządzenie")
            
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
                    self._write_text_verified(device_path / "boot.py", boot_code, "boot.py")
                    print(f"✓ Skopiowano boot.py")
            
            if code_src.exists():
                self._copy_file_verified(code_src, device_path / "code.py", "code.py")
                print(f"✓ Skopiowano code.py")

            self._sync_path(device_path / "boot.py")
            self._sync_path(device_path / "code.py")
        
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
                flash_result = self.flash_uf2(device['path'])
                if flash_result:
                    # True = RP2040 zrestartował się do CIRCUITPY, kontynuuj deployment
                    print("✅ Firmware wgrany i RP2040 zrestartowany!")
                    print()
                    # Nie kończ tutaj - kontynuuj do detekcji CIRCUITPY poniżej
                    break
                else:
                    # False = wymaga fizycznego odłączenia lub błąd
                    print("❌ Wymagane fizyczne odłączenie/podłączenie RP2040")
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
                # Był w trybie boot, został wgrany UF2 - to jest oczekiwane!
                print("✅ Firmware wgrany pomyślnie!")
                print()
                print("🔧 WYMAGANE DZIAŁANIE:")
                print("   1. FIZYCZNIE odłącz kabel USB od RP2040")
                print("   2. Poczekaj 3 sekundy")
                print("   3. Podłącz ponownie (zwykłe podłączenie, BEZ trzymania BOOT)")
                print("   4. Uruchom: make deploy")
                print()
                print("💡 RP2040 NIE restartuje automatycznie - wymaga fizycznego odłączenia!")
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
