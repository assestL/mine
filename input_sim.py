# ===========================================================================
# input_sim.py — Низкоуровневый ввод DirectInput через SendInput
# ===========================================================================

import ctypes
from ctypes import wintypes
import time
import random

# ─── Константы DirectInput ────────────────────────────────────────────────
MOUSEEVENTF_MOVE        = 0x0001
MOUSEEVENTF_LEFTDOWN    = 0x0002
MOUSEEVENTF_LEFTUP      = 0x0004

INPUT_MOUSE    = 0
INPUT_KEYBOARD = 1

KEYEVENTF_KEYUP    = 0x0002
KEYEVENTF_SCANCODE = 0x0008

# Scan-коды клавиш для стандартной раскладки QWERTY
KEY_SCAN_MAP = {
    '1': 0x02, '2': 0x03, '3': 0x04, '4': 0x05, '5': 0x06,
    '6': 0x07, '7': 0x08, '8': 0x09, '9': 0x0A, '0': 0x0B,
    '-': 0x0C, '=': 0x0D, 'backspace': 0x0E, 'tab': 0x0F,
    'q': 0x10, 'w': 0x11, 'e': 0x12, 'r': 0x13, 't': 0x14,
    'y': 0x15, 'u': 0x16, 'i': 0x17, 'o': 0x18, 'p': 0x19,
    '[': 0x1A, ']': 0x1B, 'enter': 0x1C, 'ctrl': 0x1D,
    'a': 0x1E, 's': 0x1F, 'd': 0x20, 'f': 0x21, 'g': 0x22,
    'h': 0x23, 'j': 0x24, 'k': 0x25, 'l': 0x26, ';': 0x27,
    "'": 0x28, '`': 0x29, 'shift': 0x2A, '\\': 0x2B,
    'z': 0x2C, 'x': 0x2D, 'c': 0x2E, 'v': 0x2F, 'b': 0x30,
    'n': 0x31, 'm': 0x32, ',': 0x33, '.': 0x34, '/': 0x35,
    'alt': 0x38, 'space': 0x39, 'esc': 0x01
}

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("_input", _INPUT_UNION)]

SendInput = ctypes.windll.user32.SendInput


def send_key_direct(scan_code: int, key_up: bool = False) -> None:
    """Отправляет низкоуровневое нажатие/отпускание клавиши по скан-коду."""
    flags = KEYEVENTF_SCANCODE
    if key_up:
        flags |= KEYEVENTF_KEYUP
    
    inp = INPUT(
        type=INPUT_KEYBOARD,
        _input=_INPUT_UNION(ki=KEYBDINPUT(
            wVk=0,
            wScan=scan_code,
            dwFlags=flags,
            time=0,
            dwExtraInfo=ctypes.pointer(wintypes.ULONG(0))
        ))
    )
    SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))


def press_key(key: str) -> None:
    """Зажимает клавишу (по строковому названию)."""
    scan_code = KEY_SCAN_MAP.get(key.lower())
    if scan_code is not None:
        send_key_direct(scan_code, key_up=False)


def release_key(key: str) -> None:
    """Отпускает клавишу (по строковому названию)."""
    scan_code = KEY_SCAN_MAP.get(key.lower())
    if scan_code is not None:
        send_key_direct(scan_code, key_up=True)


def press_key_for(key: str, duration: float) -> None:
    """Нажимает клавишу на указанную продолжительность."""
    press_key(key)
    time.sleep(duration)
    release_key(key)


def type_string(s: str) -> None:
    """Печатает строку посимвольно, используя скан-коды и Shift для спецсимволов."""
    shifted_chars = {
        ':': 0x27,
        '_': 0x0C,
        '?': 0x35,
        '!': 0x02,
        '@': 0x03,
    }

    for char in s:
        char_lower = char.lower()
        is_upper = char.isupper()
        
        # Если нужен зажатый Shift
        need_shift = is_upper or (char in shifted_chars)
        
        if need_shift:
            send_key_direct(0x2A, key_up=False)  # Hold Shift
            time.sleep(0.01 + random.uniform(0.002, 0.005))
            
        if char in shifted_chars:
            scan = shifted_chars[char]
        else:
            scan = KEY_SCAN_MAP.get(char_lower)
            
        if scan is not None:
            # Нажимаем символ
            send_key_direct(scan, key_up=False)
            time.sleep(0.02 + random.uniform(0.002, 0.005))
            send_key_direct(scan, key_up=True)
            time.sleep(0.02 + random.uniform(0.002, 0.005))
            
        if need_shift:
            send_key_direct(0x2A, key_up=True)  # Release Shift
            time.sleep(0.01 + random.uniform(0.002, 0.005))
