#!/bin/bash
# RP2040 Auto-Deploy Service
# ========================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/deploy.py"

# Sprawdź czy Python jest dostępny
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 nie jest zainstalowany"
    exit 1
fi

# Sprawdź czy skrypt istnieje
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "❌ Skrypt deploy.py nie znaleziony w $SCRIPT_DIR"
    exit 1
fi

echo "🤖 RP2040 Auto-Deploy Service"
echo "============================"
echo ""

# Sprawdź argumenty
case "${1:-}" in
    "start")
        echo "🚀 Uruchamianie auto-deployment..."
        python3 "$PYTHON_SCRIPT" deploy
        ;;
    "monitor")
        echo "👀 Monitorowanie urządzeń..."
        python3 "$PYTHON_SCRIPT" monitor
        ;;
    "setup")
        echo "📚 Pobieranie bibliotek..."
        python3 "$PYTHON_SCRIPT" setup
        ;;
    "detect")
        echo "🔍 Wykrywanie urządzeń..."
        python3 "$PYTHON_SCRIPT" detect
        ;;
    "help"|"-h"|"--help")
        echo "Użycie: $0 [komenda]"
        echo ""
        echo "Komendy:"
        echo "  start    - Jednorazowy deployment"
        echo "  monitor  - Monitoruj i auto-deployuj"
        echo "  setup    - Pobierz biblioteki"
        echo "  detect   - Wykryj urządzenia"
        echo "  help     - Pokaż pomoc"
        ;;
    "")
        echo "Domyślna komenda: auto-deployment"
        python3 "$PYTHON_SCRIPT" deploy
        ;;
    *)
        echo "❌ Nieznana komenda: $1"
        echo "Użyj '$0 help' aby zobaczyć dostępne komendy"
        exit 1
        ;;
esac
