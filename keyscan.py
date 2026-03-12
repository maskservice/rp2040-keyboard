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
            while select.select([sys.stdin], [], [], 0.05)[0]:
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
                
                # Add debug info for unknown patterns
                if "Multi[" in label:
                    debug_info = f"DEBUG: buffer={repr(''.join(key_buffer))}, codes={codes}"
                    sys.stdout.write(f"\r\x1b[K  key: {label:<25s}  codes={codes}\r\n")
                    sys.stdout.write(f"\r\x1b[K  {debug_info}\r\n")
                else:
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
        
        # Special case: Ctrl+Alt might send ESC + [ + digit in some terminals
        if first == 27 and second == 91 and (third >= 48 and third <= 57):
            # This might be Alt+digit, but could also be Ctrl+Alt+digit in some configs
            return f"Alt+{chr(third)} (possible Ctrl+Alt)"
        
        # ESC + digit patterns
        if first == 27 and (second >= 48 and second <= 57):
            return f"Alt+{chr(second)} (possible Ctrl+Alt)"
        
        # GP29 and similar terminals: ESC + digit + letter patterns
        if first == 27 and (second >= 48 and second <= 57) and ((third >= 65 and third <= 90) or (third >= 97 and third <= 122)):
            return f"Alt+{chr(second)}+{chr(third).upper()}"
    
    # Check for 4-key combinations (some terminals send ESC + [ + 1 + digit for Alt+number)
    if len(keys) == 4:
        first, second, third, fourth = codes[0], codes[1], codes[2], codes[3]
        
        # ESC + [ + 1 + digit pattern (Alt+number in some terminals)
        if first == 27 and second == 91 and third == 49 and (fourth >= 48 and fourth <= 57):
            return f"Alt+{chr(fourth)}"
        
        # ESC + [ + digit + ~ pattern (function keys, but sometimes Alt combinations)
        if first == 27 and second == 91 and (third >= 48 and third <= 57) and fourth == 126:
            return f"Alt+F{chr(third)}"
        
        # GP29 specific: ESC + [ + digit + letter patterns
        if first == 27 and second == 91 and (third >= 48 and third <= 57) and ((fourth >= 65 and fourth <= 90) or (fourth >= 97 and fourth <= 122)):
            return f"Alt+{chr(third)}+{chr(fourth).upper()}"
        
        # Common pattern: ESC + [ + 1 + ~ (for F1-F10, sometimes repurposed)
        if first == 27 and second == 91 and third == 49 and fourth == 126:
            return "Alt+F1 (possible Ctrl+Alt+1)"
        
        # Pattern for Ctrl+Alt+7 in some terminals: ESC + [ + 1 + 7 + ~
        if len(keys) >= 5:
            fifth = codes[4] if len(codes) > 4 else 0
            if first == 27 and second == 91 and third == 49 and fourth >= 48 and fourth <= 57 and fifth == 126:
                return f"Alt+F{chr(fourth)} (possible Ctrl+Alt+{chr(fourth)})"
    
    # Check for 5-key combinations (GP29 and similar complex terminals)
    if len(keys) == 5:
        first, second, third, fourth, fifth = codes[0], codes[1], codes[2], codes[3], codes[4]
        
        # ESC + [ + 1 + digit + ~ pattern (some terminals for Ctrl+Alt+number)
        if first == 27 and second == 91 and third == 49 and (fourth >= 48 and fourth <= 57) and fifth == 126:
            return f"Ctrl+Alt+{chr(fourth)}"
        
        # ESC + [ + digit + semicolon + digit patterns
        if first == 27 and second == 91 and (third >= 48 and third <= 57) and fourth == 59 and (fifth >= 48 and fifth <= 57):
            return f"Ctrl+Alt+{chr(fifth)}"
    
    # More complex combinations - provide detailed debug info
    return f"Multi[{len(keys)}]: {repr(''.join(keys))} [codes: {codes}]"


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
        # GP29 and similar terminals additional patterns
        "\x1b[1~": "Home",
        "\x1b[4~": "End",
        "\x1b[7~": "Home",
        "\x1b[8~": "End",
        # Function key variants
        "\x1b[11~": "F1",
        "\x1b[12~": "F2",
        "\x1b[13~": "F3",
        "\x1b[14~": "F4",
    }
    if seq in mapping:
        return mapping[seq]
    
    # Check for GP29-style function key patterns: ESC [ number ~
    if len(seq) >= 3 and seq[0] == '\x1b' and seq[1] == '[' and seq[-1] == '~':
        num_part = seq[2:-1]
        if num_part.isdigit():
            return f"F{num_part}"
    
    # Check for Alt+number patterns: ESC number
    if len(seq) == 2 and seq[0] == '\x1b' and seq[1].isdigit():
        return f"Alt+{seq[1]}"
    
    # Check for Alt+letter patterns: ESC letter
    if len(seq) == 2 and seq[0] == '\x1b' and seq[1].isalpha():
        return f"Alt+{seq[1].upper()}"
    
    return f"ESC+{repr(seq[1:])}"


if __name__ == "__main__":
    main()
