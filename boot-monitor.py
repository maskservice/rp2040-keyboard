#!/usr/bin/env python3
"""
RP2040 Boot Monitor - Auto-deployment on device boot
===================================================

Uruchamiane automatycznie przy starcie systemu do monitorowania
podłączanych urządzeń RP2040-One i automatycznego deploymentu.
"""

import os
import sys
import time
import signal
import subprocess
from pathlib import Path

# Dodaj ścieżkę do skryptu deploy.py
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from deploy import RP2040Deployer

class BootMonitor:
    def __init__(self):
        self.deployer = RP2040Deployer()
        self.running = True
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """Ustaw obsługę sygnałów do eleganckiego zamykania."""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Obsługa sygnałów."""
        print(f"\n📡 Otrzymano sygnał {signum}, zamykanie...")
        self.running = False
    
    def check_initial_devices(self):
        """Sprawdź czy urządzenia są już podłączone przy starcie."""
        print("🔍 Sprawdzanie istniejących urządzeń...")
        devices = self.deployer.detect_circuitpy_devices()
        
        if devices:
            print(f"✅ Znaleziono {len(devices)} urządzeń przy starcie")
            for device in devices:
                print(f"  - {device['name']}: {device['path']}")
            
            # Auto-deploy jeśli włączony
            if self.deployer.config.get('AUTO_DEPLOY_ON_BOOT', 'true').lower() == 'true':
                print("🚀 Auto-deployment przy starcie...")
                self.deployer.auto_deploy()
        else:
            print("ℹ️  Brak urządzeń przy starcie, oczekiwanie na podłączenie...")
    
    def run(self):
        """Główna pętla monitorowania."""
        print("🚀 RP2040 Boot Monitor uruchomiony")
        print("👂 Nasłuchiwanie na podłączenie urządzeń...")
        print("Naciśnij Ctrl+C aby zakończyć")
        print()
        
        # Sprawdź urządzenia przy starcie
        self.check_initial_devices()
        
        last_check = time.time()
        check_interval = 5  # Sprawdzaj co 5 sekund
        
        while self.running:
            try:
                current_time = time.time()
                
                # Sprawdzaj urządzenia co określony interwał
                if current_time - last_check >= check_interval:
                    devices = self.deployer.detect_circuitpy_devices()
                    
                    if devices:
                        current_device = devices[0]['path']
                        last_device = self.deployer.config.get('CIRCUITPY_DEVICE_PATH')
                        
                        # Nowe urządzenie podłączone
                        if current_device != last_device:
                            print(f"\n🔌 Wykryto nowe urządzenie: {devices[0]['name']}")
                            
                            if self.deployer.config.get('AUTO_DEPLOY_ON_BOOT', 'true').lower() == 'true':
                                print("🚀 Auto-deployment...")
                                self.deployer.auto_deploy()
                    
                    last_check = current_time
                    time.sleep(1)  # Krótka pauza
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Błąd: {e}")
                time.sleep(5)  # Poczekaj przed kolejną próbą
        
        print("👋 Boot Monitor zakończony")

def main():
    """Main entry point."""
    monitor = BootMonitor()
    monitor.run()

if __name__ == "__main__":
    main()
