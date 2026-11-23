#!/usr/bin/env python3
"""GP29 specific key sequence tester for Ctrl+Alt combinations"""

import sys
import tty
import termios
import signal
import select

def main():
    old_settings = termios.tcgetattr(sys.stdin)
    print("🔍 GP29 Key Sequence Tester")
    print("Testowanie Ctrl+Alt+7 i innych kombinacji")
    print("Naciśnij kombinacje klawiszy, Ctrl+C aby zakończyć")
    print("=" * 60)

    def cleanup(signum=None, frame=None):
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        print("\n" + "=" * 60)
        print("⏹  Test zakończony.")
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)

    try:
        tty.setraw(sys.stdin.fileno())
        
        while True:
            # Wait for input
            if not select.select([sys.stdin], [], [], 0.1)[0]:
                continue
                
            # Read everything available with longer timeout for GP29
            buffer = ""
            while select.select([sys.stdin], [], [], 0.15)[0]:
                ch = sys.stdin.read(1)
                if ch:
                    buffer += ch
                else:
                    break
            
            if buffer:
                codes = [ord(c) for c in buffer]
                hex_codes = [f'0x{c:02x}' for c in codes]
                
                # Try to decode as known patterns
                decoded = decode_gp29_pattern(buffer, codes)
                
                print(f"Bufor:    {repr(buffer)}")
                print(f"Kody:     {codes}")
                print(f"Hex:      {hex_codes}")
                print(f"Zdekodowano: {decoded}")
                print("-" * 60)
                
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

def decode_gp29_pattern(buffer, codes):
    """Specjalne dekodowanie dla wzorców GP29"""
    
    # Sprawdź Ctrl+Alt+number patterns
    if len(codes) >= 2:
        # Pattern 1: Ctrl code (<32) + ESC + number
        if len(codes) == 3 and codes[0] < 32 and codes[1] == 27 and codes[2] >= 48 and codes[2] <= 57:
            return f"Ctrl+Alt+{chr(codes[2])}"
        
        # Pattern 2: ESC + [ + 1 + number + ~ (GP29 style)
        if len(codes) == 5 and codes[0] == 27 and codes[1] == 91 and codes[2] == 49 and codes[3] >= 48 and codes[3] <= 57 and codes[4] == 126:
            return f"Ctrl+Alt+{chr(codes[3])} (GP29 pattern)"
        
        # Pattern 3: ESC + [ + number + ~
        if len(codes) >= 4 and codes[0] == 27 and codes[1] == 91 and codes[-2] >= 48 and codes[-2] <= 57 and codes[-1] == 126:
            return f"Alt+F{chr(codes[-2])} (może być Ctrl+Alt)"
        
        # Pattern 4: ESC + number
        if len(codes) == 2 and codes[0] == 27 and codes[1] >= 48 and codes[1] <= 57:
            return f"Alt+{chr(codes[1])} (może być Ctrl+Alt)"
        
        # Pattern 5: ESC + [ + number
        if len(codes) == 3 and codes[0] == 27 and codes[1] == 91 and codes[2] >= 48 and codes[2] <= 57:
            return f"Alt+{chr(codes[2])} (może być Ctrl+Alt)"
    
    return "Nieznany wzorzec"

if __name__ == "__main__":
    main()
