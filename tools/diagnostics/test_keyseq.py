#!/usr/bin/env python3
"""Simple key sequence tester - shows raw bytes received"""

import sys
import tty
import termios
import signal
import select

def main():
    old_settings = termios.tcgetattr(sys.stdin)
    print("🔍 Key Sequence Tester - press Ctrl+Alt+2 and other combinations")
    print("Shows raw bytes and character codes. Ctrl+C to exit.")
    print("-" * 60)

    def cleanup(signum=None, frame=None):
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        print("\n" + "-" * 60)
        print("⏹  Test stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)

    try:
        tty.setraw(sys.stdin.fileno())
        
        while True:
            # Wait for input
            if not select.select([sys.stdin], [], [], 0.1)[0]:
                continue
                
            # Read everything available with longer timeout
            buffer = ""
            while select.select([sys.stdin], [], [], 0.1)[0]:
                ch = sys.stdin.read(1)
                if ch:
                    buffer += ch
                else:
                    break
            
            if buffer:
                codes = [ord(c) for c in buffer]
                printable = []
                for c in buffer:
                    if ord(c) < 32:
                        printable.append(f"Ctrl+{chr(ord(c) + 64)}")
                    elif ord(c) == 27:
                        printable.append("ESC")
                    elif ord(c) == 127:
                        printable.append("BS")
                    else:
                        printable.append(c)
                
                print(f"Buffer: {repr(buffer)}")
                print(f"Codes:  {codes}")
                print(f"Chars:  {printable}")
                print(f"Hex:    {[f'0x{c:02x}' for c in codes]}")
                print("-" * 60)
                
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

if __name__ == "__main__":
    main()
