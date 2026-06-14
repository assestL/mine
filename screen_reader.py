# ===========================================================================
# screen_reader.py — Чтение координат из Minecraft через F3+C
# ===========================================================================
# Minecraft при нажатии F3+C копирует в буфер обмена команду:
#   /execute in minecraft:overworld run tp @s X Y Z Yaw Pitch
#
# Мы парсим эту строку, чтобы получить реальные координаты и углы
# персонажа. Это решает проблему рассинхронизации внутреннего
# трекера позиции.
#
# Для чтения буфера обмена используем Windows API через ctypes —
# никаких дополнительных зависимостей не требуется.
# ===========================================================================

import ctypes
import time
import re
import datetime

import pydirectinput


# ---------------------------------------------------------------------------
# Windows Clipboard API (ctypes)
# ---------------------------------------------------------------------------

CF_UNICODETEXT = 13


def _get_clipboard_text() -> str:
    """
    Читает текст из буфера обмена Windows через Win32 API.

    Не требует дополнительных библиотек — использует ctypes.

    Возвращает:
        Текст из буфера обмена (или пустая строка при ошибке)
    """
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    if not user32.OpenClipboard(0):
        return ""

    try:
        if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
            return ""

        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return ""

        kernel32.GlobalLock.restype = ctypes.c_void_p
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return ""

        try:
            return ctypes.c_wchar_p(ptr).value or ""
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def _timestamp() -> str:
    """Временная метка для логов."""
    return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]


# ---------------------------------------------------------------------------
# Чтение координат
# ---------------------------------------------------------------------------

# Регулярное выражение для парсинга команды /tp
# Формат: /execute in minecraft:overworld run tp @s X Y Z Yaw Pitch
_TP_PATTERN = re.compile(
    r'tp\s+@s\s+'
    r'([-\d.]+)\s+'   # X
    r'([-\d.]+)\s+'   # Y
    r'([-\d.]+)\s+'   # Z
    r'([-\d.]+)\s+'   # Yaw
    r'([-\d.]+)'      # Pitch
)


def read_player_data() -> dict | None:
    """
    Нажимает F3+C в Minecraft и парсит координаты из буфера обмена.

    Последовательность:
        1. Зажимаем F3
        2. Нажимаем C (Minecraft копирует /tp в буфер)
        3. Отпускаем F3
        4. Читаем буфер обмена
        5. Парсим X, Y, Z, Yaw, Pitch

    Возвращает:
        Словарь {'x', 'y', 'z', 'yaw', 'pitch'} или None при ошибке
    """
    # --- Нажатие F3+C ---
    pydirectinput.keyDown('f3')
    time.sleep(0.04)
    pydirectinput.press('c')
    time.sleep(0.04)
    pydirectinput.keyUp('f3')

    # Ждём, пока Minecraft обновит буфер обмена
    time.sleep(0.15)

    # --- Чтение буфера ---
    clipboard = _get_clipboard_text()

    if not clipboard:
        print(f"  [{_timestamp()}] [SYNC] Буфер обмена пуст!")
        return None

    # --- Парсинг ---
    match = _TP_PATTERN.search(clipboard)
    if match:
        data = {
            'x': float(match.group(1)),
            'y': float(match.group(2)),
            'z': float(match.group(3)),
            'yaw': float(match.group(4)),
            'pitch': float(match.group(5)),
        }
        return data

    print(f"  [{_timestamp()}] [SYNC] Не удалось распарсить: {clipboard[:80]}")
    return None


def sync_position(bot) -> bool:
    """
    Синхронизирует внутреннее состояние бота с реальными
    координатами из Minecraft.

    Вызывает read_player_data() (F3+C) и обновляет:
        bot.current_x, current_y, current_z
        bot.current_yaw, current_pitch

    Аргументы:
        bot: экземпляр MinecraftBot

    Возвращает:
        True если синхронизация успешна, False при ошибке
    """
    data = read_player_data()
    if data is None:
        return False

    bot.current_x = data['x']
    bot.current_y = data['y']
    bot.current_z = data['z']
    bot.current_yaw = data['yaw']
    bot.current_pitch = data['pitch']

    print(
        f"  [{_timestamp()}] [SYNC] "
        f"Позиция: ({data['x']:.2f}, {data['y']:.2f}, {data['z']:.2f}) "
        f"Yaw={data['yaw']:.1f}° Pitch={data['pitch']:.1f}°"
    )
    return True
