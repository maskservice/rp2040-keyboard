#!/usr/bin/env python3
"""Key scanner - listens for key presses and prints them. Ctrl+C to exit."""

import sys
import tty
import termios
import signal
import select


def main():
    old_settings = termios.tcgetattr(sys.stdin)
    print("🎹 Keyscan: listening for key presses... (Ctrl+C to exit)")
    print("-" * 50)
    print("💡 Test kombinacji: Ctrl+Alt+1, Ctrl+Alt+A, etc.")
    print("-" * 50)

    def cleanup(signum=None, frame=None):
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        print("\n" + "-" * 50)
        print("⏹  Keyscan stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)

    try:
        tty.setraw(sys.stdin.fileno())
        key_buffer = []
        
        while True:
            # Wait for input with timeout
            if not select.select([sys.stdin], [], [], 0.1)[0]:
                continue
                
            ch = sys.stdin.read(1)
            if not ch:
                break
                
            code = ord(ch)
            key_buffer.append(ch)
            
            # Ctrl+C
            if code == 3:
                cleanup()

            # Try to detect multi-key combinations
            # Give some time for additional keys to arrive
            while select.select([sys.stdin], [], [], 0.01)[0]:
                next_ch = sys.stdin.read(1)
                if next_ch:
                    key_buffer.append(next_ch)

            # Analyze the buffer
            if len(key_buffer) == 1:
                # Single key
                if code == 27:
                    # Escape sequence
                    seq = ch
                    while select.select([sys.stdin], [], [], 0.05)[0]:
                        seq += sys.stdin.read(1)
                    
                    codes = [ord(c) for c in seq]
                    label = _decode_escape(seq)
                    sys.stdout.write(f"\r\x1b[K  ESC seq: {label:<20s}  codes={codes}\r\n")
                    sys.stdout.flush()
                    key_buffer = []
                    continue
                elif code < 32:
                    # Ctrl key
                    label = f"Ctrl+{chr(code + 64)}"
                    sys.stdout.write(f"\r\x1b[K  key: {label:<20s}  char={repr(ch)}  code={code}\r\n")
                    sys.stdout.flush()
                    key_buffer = []
                    continue
                else:
                    # Regular key
                    label = _label(ch, code)
                    sys.stdout.write(f"\r\x1b[K  key: {label:<20s}  char={repr(ch)}  code={code}\r\n")
                    sys.stdout.flush()
                    key_buffer = []
                    continue
            
            # Multi-key analysis
            if len(key_buffer) >= 2:
                codes = [ord(c) for c in key_buffer]
                label = _decode_multi_key(key_buffer, codes)
                sys.stdout.write(f"\r\x1b[K  key: {label:<25s}  codes={codes}\r\n")
                sys.stdout.flush()
                key_buffer = []
                continue
                
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


def _label(ch, code):
    if code < 32:
        return f"Ctrl+{chr(code + 64)}"
    if code == 32:
        return "Space"
    if code == 127:
        return "Backspace"
    return ch


def _decode_multi_key(keys, codes):
    """Decode multi-key combinations like Ctrl+Alt+1"""
    
    # Check for Ctrl+Alt patterns
    if len(keys) == 2:
        first, second = codes[0], codes[1]
        
        # Ctrl+Alt+number (Ctrl sends code < 32, Shift sends the actual key)
        if first < 32 and (second >= 48 and second <= 57):
            ctrl_char = chr(first + 64)
            return f"Ctrl+Alt+{chr(second)}"
        
        # Ctrl+Alt+letter
        if first < 32 and ((second >= 65 and second <= 90) or (second >= 97 and second <= 122)):
            ctrl_char = chr(first + 64)
            key_char = chr(second).upper()
            return f"Ctrl+Alt+{key_char}"
        
        # Ctrl+Alt+number (Ctrl sends code < 32, Alt sends escape sequence)
        if first < 32 and second == 27:
            ctrl_char = chr(first + 64)
            return f"Ctrl+Alt+[ESC]"
        
        # Other combinations
        return f"Multi: {repr(''.join(keys))}"
    
    # Check for 3-key combinations (Ctrl+Alt+number often sends 3 chars)
    if len(keys) == 3:
        first, second, third = codes[0], codes[1], codes[2]
        
        # Ctrl+Alt+number pattern: Ctrl code + ESC + number
        if first < 32 and second == 27 and (third >= 48 and third <= 57):
            ctrl_char = chr(first + 64)
            return f"Ctrl+Alt+{chr(third)}"
        
        # Ctrl+Alt+letter pattern: Ctrl code + ESC + letter
        if first < 32 and second == 27 and ((third >= 65 and third <= 90) or (third >= 97 and third <= 122)):
            ctrl_char = chr(first + 64)
            key_char = chr(third).upper()
            return f"Ctrl+Alt+{key_char}"
    
    # More complex combinations
    return f"Multi[{len(keys)}]: {repr(''.join(keys))}"


def _decode_escape(seq):
    mapping = {
        "\x1b[A": "Up",
        "\x1b[B": "Down",
        "\x1b[C": "Right",
        "\x1b[D": "Left",
        "\x1b[H": "Home",
        "\x1b[F": "End",
        "\x1b[2~": "Insert",
        "\x1b[3~": "Delete",
        "\x1b[5~": "PageUp",
        "\x1b[6~": "PageDown",
        "\x1bOP": "F1",
        "\x1bOQ": "F2",
        "\x1bOR": "F3",
        "\x1bOS": "F4",
        "\x1b[15~": "F5",
        "\x1b[17~": "F6",
        "\x1b[18~": "F7",
        "\x1b[19~": "F8",
        "\x1b[20~": "F9",
        "\x1b[21~": "F10",
        "\x1b[23~": "F11",
        "\x1b[24~": "F12",
    }
    if seq in mapping:
        return mapping[seq]
    return f"ESC+{repr(seq[1:])}"


if __name__ == "__main__":
    main()
