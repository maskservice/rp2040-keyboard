# ============================================================================
# RP2040-One HID Keypad — Makefile
# Softreck / Prototypowanie.pl
# ============================================================================

.PHONY: help install web dev test test-docker lint flash clean dist

PYTHON       ?= python3
PIP          ?= pip3
PORT         ?= 8080
CIRCUITPY    ?= /media/$(USER)/CIRCUITPY
UF2_URL      := https://downloads.circuitpython.org/bin/waveshare_rp2040_one/en_US/adafruit-circuitpython-waveshare_rp2040_one-en_US-9.2.0.uf2
HID_BUNDLE   := https://github.com/adafruit/Adafruit_CircuitPython_Bundle/releases/latest
DOCKER_IMG   := rp2040-keypad-test
VERSION      := 1.0.0

# ── Kolory ──────────────────────────────────────────────────────────────────
C_GREEN  := \033[1;32m
C_YELLOW := \033[1;33m
C_CYAN   := \033[1;36m
C_RESET  := \033[0m

# ============================================================================
# HELP
# ============================================================================

help: ## Pokaż tę pomoc
	@echo ""
	@echo "$(C_CYAN)RP2040-One HID Keypad$(C_RESET) v$(VERSION)"
	@echo "────────────────────────────────────────"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(C_GREEN)%-18s$(C_RESET) %s\n", $$1, $$2}'
	@echo ""

# ============================================================================
# INSTALL / SETUP
# ============================================================================

install: ## Zainstaluj zależności Python (FastAPI, pytest, etc.)
	$(PIP) install --break-system-packages -q \
		fastapi uvicorn jinja2 python-multipart \
		pytest pytest-asyncio httpx aiofiles

requirements.txt: ## Wygeneruj requirements.txt
	@echo "fastapi>=0.110.0" > requirements.txt
	@echo "uvicorn[standard]>=0.29.0" >> requirements.txt
	@echo "jinja2>=3.1.0" >> requirements.txt
	@echo "python-multipart>=0.0.9" >> requirements.txt
	@echo "aiofiles>=23.0" >> requirements.txt
	@echo "pytest>=8.0" >> requirements.txt
	@echo "pytest-asyncio>=0.23" >> requirements.txt
	@echo "httpx>=0.27" >> requirements.txt
	@echo "$(C_GREEN)✓ requirements.txt wygenerowany$(C_RESET)"

# ============================================================================
# WEB SERVICE
# ============================================================================

web: ## Uruchom web configurator (produkcja)
	@echo "$(C_CYAN)► Web configurator:$(C_RESET) http://localhost:$(PORT)"
	$(PYTHON) -m uvicorn web.app:app --host 0.0.0.0 --port $(PORT)

dev: ## Uruchom web configurator (dev z auto-reload)
	@echo "$(C_CYAN)► Web configurator DEV:$(C_RESET) http://localhost:$(PORT)"
	$(PYTHON) -m uvicorn web.app:app --host 0.0.0.0 --port $(PORT) --reload

# ============================================================================
# TESTOWANIE
# ============================================================================

test: ## Uruchom testy jednostkowe
	@echo "$(C_CYAN)► Testy jednostkowe$(C_RESET)"
	$(PYTHON) -m pytest tests/ -v --tb=short

test-e2e: ## Uruchom testy E2E (wymaga Docker)
	@echo "$(C_CYAN)► Testy E2E w Docker$(C_RESET)"
	docker compose -f docker/docker-compose.test.yml up --build --abort-on-container-exit
	docker compose -f docker/docker-compose.test.yml down

test-docker: ## Zbuduj i uruchom pełny test suite w Docker
	@echo "$(C_CYAN)► Build Docker test image$(C_RESET)"
	docker build -t $(DOCKER_IMG) -f docker/Dockerfile.test .
	@echo "$(C_CYAN)► Uruchamianie testów$(C_RESET)"
	docker run --rm $(DOCKER_IMG)
	@echo "$(C_GREEN)✓ Wszystkie testy przeszły$(C_RESET)"

lint: ## Sprawdź jakość kodu
	@echo "$(C_CYAN)► Lint$(C_RESET)"
	$(PYTHON) -m py_compile web/app.py && echo "$(C_GREEN)  ✓ web/app.py — OK$(C_RESET)"

# ============================================================================
# FLASH / DEPLOY na RP2040
# ============================================================================

flash: ## Wgraj program na podłączone CIRCUITPY
	@if [ -d "$(CIRCUITPY)" ]; then \
		echo "$(C_GREEN)► CIRCUITPY wykryty: $(CIRCUITPY)$(C_RESET)"; \
		cp firmware/boot.py "$(CIRCUITPY)/boot.py"; \
		echo "  ✓ boot.py skopiowany"; \
		cp firmware/code.py "$(CIRCUITPY)/code.py"; \
		echo "  ✓ code.py skopiowany"; \
		echo "$(C_YELLOW)⚠ Odłącz i ponownie podłącz USB aby boot.py zadziałał$(C_RESET)"; \
	else \
		echo "$(C_YELLOW)⚠ Dysk CIRCUITPY nie znaleziony w $(CIRCUITPY)$(C_RESET)"; \
		echo "  Podłącz RP2040-One z CircuitPython lub ustaw CIRCUITPY=<ścieżka>"; \
	fi

flash-custom: ## Wgraj wygenerowany config (z web configuratora)
	@if [ -f "output/code.py" ] && [ -d "$(CIRCUITPY)" ]; then \
		cp output/boot.py "$(CIRCUITPY)/boot.py"; \
		cp output/code.py "$(CIRCUITPY)/code.py"; \
		echo "$(C_GREEN)✓ Custom config wgrany na CIRCUITPY$(C_RESET)"; \
	else \
		echo "$(C_YELLOW)⚠ Brak output/code.py lub CIRCUITPY$(C_RESET)"; \
		echo "  Najpierw wygeneruj config w web configuratorze"; \
	fi

download-uf2: ## Pobierz firmware CircuitPython UF2
	@echo "$(C_CYAN)► Pobieranie CircuitPython UF2...$(C_RESET)"
	curl -L -o firmware.uf2 "$(UF2_URL)"
	@echo "$(C_GREEN)✓ Firmware zapisany: firmware.uf2$(C_RESET)"
	@echo "  Wgraj na dysk RPI-RP2 (przytrzymaj BOOT przy podłączaniu)"

# ============================================================================
# DOCKER — serwis webowy
# ============================================================================

docker-build: ## Zbuduj obraz Docker web configuratora
	docker build -t rp2040-keypad-web -f docker/Dockerfile .

docker-run: ## Uruchom web configurator w Docker
	docker run --rm -p $(PORT):8080 rp2040-keypad-web

docker-compose: ## Uruchom stack (web + testy) via docker compose
	docker compose -f docker/docker-compose.yml up --build

# ============================================================================
# DIST / CLEAN
# ============================================================================

dist: ## Przygotuj paczkę do dystrybucji
	@mkdir -p dist
	cp firmware/boot.py firmware/code.py README.md dist/
	@echo "$(C_GREEN)✓ Pliki w dist/$(C_RESET)"

clean: ## Wyczyść pliki tymczasowe
	rm -rf __pycache__ .pytest_cache tests/__pycache__
	rm -rf web/__pycache__ output/ dist/
	rm -f firmware.uf2
	@echo "$(C_GREEN)✓ Czysto$(C_RESET)"
