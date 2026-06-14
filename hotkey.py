# ===========================================================================
# hotkey.py — Модуль перехвата горячих клавиш
# ===========================================================================
# Обеспечивает глобальный перехват клавиши Q для старта/стопа бота.
# Поддерживает русскую раскладку клавиатуры (клавиша Й).
# ===========================================================================

import winsound
import datetime

from pynput import keyboard
from pynput.keyboard import KeyCode

# ---------------------------------------------------------------------------
# Виртуальный код клавиши Q (Windows VK_Q)
# ---------------------------------------------------------------------------
VK_Q = 0x51

# ---------------------------------------------------------------------------
# Настройки звуковых сигналов
# ---------------------------------------------------------------------------

START_BEEP_FREQ = 1000
START_BEEP_DURATION = 200

STOP_BEEP_FREQ = 500
STOP_BEEP_DURATION = 300

# Отключаем подробное логирование каждого нажатия по умолчанию, чтобы не флудить
DEBUG_KEYS = False


def _timestamp() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]


def _play_start_sound() -> None:
    winsound.Beep(START_BEEP_FREQ, START_BEEP_DURATION)
    winsound.Beep(START_BEEP_FREQ + 200, START_BEEP_DURATION)


def _play_stop_sound() -> None:
    winsound.Beep(STOP_BEEP_FREQ, STOP_BEEP_DURATION)


def _is_q_key(key) -> bool:
    """
    Проверяет, является ли нажатая клавиша — клавишей Q/Й.
    """
    # Метод 1: через символ (char) — поддерживает английскую и русскую раскладку
    try:
        if hasattr(key, 'char') and key.char is not None:
            if key.char.lower() in ('q', 'й'):
                if DEBUG_KEYS:
                    print(f"  [{_timestamp()}] [HOTKEY] Q/Й определена через char='{key.char}'")
                return True
    except Exception:
        pass

    # Метод 2: через виртуальный код (vk)
    try:
        if hasattr(key, 'vk') and key.vk is not None:
            if key.vk == VK_Q:
                if DEBUG_KEYS:
                    print(f"  [{_timestamp()}] [HOTKEY] Q определена через vk={key.vk}")
                return True
    except Exception:
        pass

    # Метод 3: прямое сравнение с KeyCode
    try:
        if key == KeyCode.from_vk(VK_Q):
            if DEBUG_KEYS:
                print(f"  [{_timestamp()}] [HOTKEY] Q определена через KeyCode.from_vk()")
            return True
    except Exception:
        pass

    return False


def create_hotkey_listener(bot) -> keyboard.Listener:
    """
    Создаёт и возвращает глобальный слушатель горячих клавиш.
    """
    print(f"  [{_timestamp()}] [HOTKEY] Слушатель горячих клавиш создан")

    def on_press(key) -> bool | None:
        if DEBUG_KEYS:
            key_info = _describe_key(key)
            print(f"  [{_timestamp()}] [HOTKEY] Нажата клавиша: {key_info}")

        try:
            if _is_q_key(key):
                _toggle_bot(bot)
                return None

            if key == keyboard.Key.esc:
                print(f"\n  [{_timestamp()}] [СИСТЕМА] Нажат Escape — завершение программы...")
                bot.shutdown()
                return False

        except Exception as e:
            print(f"  [{_timestamp()}] [HOTKEY] ОШИБКА в обработчике: {e}")

        return None

    listener = keyboard.Listener(on_press=on_press)
    return listener


def _describe_key(key) -> str:
    parts = [f"type={type(key).__name__}"]

    try:
        if hasattr(key, 'char'):
            parts.append(f"char={repr(key.char)}")
    except Exception:
        parts.append("char=<error>")

    try:
        if hasattr(key, 'vk') and key.vk is not None:
            parts.append(f"vk={key.vk} (0x{key.vk:02X})")
    except Exception:
        parts.append("vk=<error>")

    try:
        if hasattr(key, 'name'):
            parts.append(f"name={key.name}")
    except Exception:
        pass

    parts.append(f"str={repr(str(key))}")
    return " | ".join(parts)


def _toggle_bot(bot) -> None:
    if not bot.is_running:
        bot.is_running = True
        print(f"\n  [{_timestamp()}] ▶ БОТ ЗАПУЩЕН (нажмите Q/Й для паузы)")
        _play_start_sound()
    else:
        bot.is_running = False
        bot.release_all()
        print(f"\n  [{_timestamp()}] ⏸ БОТ ОСТАНОВЛЕН (нажмите Q/Й для продолжения)")
        _play_stop_sound()
