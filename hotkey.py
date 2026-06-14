# ===========================================================================
# hotkey.py — Модуль перехвата горячих клавиш
# ===========================================================================
# Обеспечивает глобальный перехват клавиши Q для старта/стопа бота.
# Использует pynput.keyboard.Listener — работает в отдельном потоке
# и перехватывает нажатия независимо от фокуса окна.
#
# ВАЖНО: Когда Minecraft (или другая игра) захватывает клавиатуру
# через DirectInput, атрибут key.char может быть None даже для
# обычных символьных клавиш. Поэтому мы определяем клавишу Q
# тремя способами:
#   1. key.char == 'q'      (обычный режим)
#   2. key.vk == 0x51       (виртуальный код клавиши Q)
#   3. key == KeyCode(vk=81) (явное сравнение)
# ===========================================================================

import winsound
import datetime

from pynput import keyboard
from pynput.keyboard import KeyCode


# ---------------------------------------------------------------------------
# Виртуальный код клавиши Q (Windows VK_Q)
# https://learn.microsoft.com/en-us/windows/win32/inputdev/virtual-key-codes
# ---------------------------------------------------------------------------
VK_Q = 0x51  # 81 в десятичной системе

# ---------------------------------------------------------------------------
# Настройки звуковых сигналов
# ---------------------------------------------------------------------------

# Частота и длительность звукового сигнала при СТАРТЕ (высокий бип)
START_BEEP_FREQ = 1000    # Гц
START_BEEP_DURATION = 200  # мс

# Частота и длительность звукового сигнала при СТОПЕ (низкий бип)
STOP_BEEP_FREQ = 500     # Гц
STOP_BEEP_DURATION = 300  # мс

# Включить подробное логирование нажатий (для отладки)
DEBUG_KEYS = True


def _timestamp() -> str:
    """Возвращает текущее время для логов."""
    return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]


def _play_start_sound() -> None:
    """Воспроизводит звуковой сигнал при запуске бота (два коротких бипа)."""
    winsound.Beep(START_BEEP_FREQ, START_BEEP_DURATION)
    winsound.Beep(START_BEEP_FREQ + 200, START_BEEP_DURATION)


def _play_stop_sound() -> None:
    """Воспроизводит звуковой сигнал при остановке бота (один длинный бип)."""
    winsound.Beep(STOP_BEEP_FREQ, STOP_BEEP_DURATION)


def _is_q_key(key) -> bool:
    """
    Проверяет, является ли нажатая клавиша — клавишей Q.

    Использует три метода определения для надёжности:
      1. key.char == 'q' — стандартный способ (работает без DirectInput)
      2. key.vk == 0x51 — виртуальный код Windows (работает ВСЕГДА)
      3. Сравнение с KeyCode.from_vk(VK_Q) — запасной вариант

    Аргументы:
        key: объект нажатой клавиши от pynput

    Возвращает:
        True, если это клавиша Q
    """
    # Метод 1: через символ (char)
    try:
        if hasattr(key, 'char') and key.char is not None:
            if key.char.lower() == 'q':
                if DEBUG_KEYS:
                    print(f"  [{_timestamp()}] [HOTKEY] Q определена через char='{key.char}'")
                return True
    except Exception:
        pass

    # Метод 2: через виртуальный код (vk) — главный для игр!
    try:
        if hasattr(key, 'vk') and key.vk is not None:
            if key.vk == VK_Q:
                if DEBUG_KEYS:
                    print(f"  [{_timestamp()}] [HOTKEY] Q определена через vk={key.vk} (0x{key.vk:02X})")
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

    При нажатии клавиши Q:
        - Если бот остановлен → запускает его (is_running = True)
        - Если бот работает → останавливает его (is_running = False)
    При нажатии Escape:
        - Полностью завершает программу

    Аргументы:
        bot: экземпляр MinecraftBot

    Возвращает:
        Экземпляр keyboard.Listener (ещё не запущенный)
    """

    print(f"  [{_timestamp()}] [HOTKEY] Слушатель горячих клавиш создаётся...")
    print(f"  [{_timestamp()}] [HOTKEY] DEBUG_KEYS = {DEBUG_KEYS} (логирование всех нажатий)")

    def on_press(key) -> bool | None:
        """
        Обработчик нажатия клавиш.

        Логирует ВСЕ нажатия (при DEBUG_KEYS=True) для диагностики,
        затем проверяет целевые клавиши (Q и Escape).

        Аргументы:
            key: объект нажатой клавиши

        Возвращает:
            False для завершения слушателя, None для продолжения
        """
        # --- Логирование КАЖДОГО нажатия для диагностики ---
        if DEBUG_KEYS:
            key_info = _describe_key(key)
            print(f"  [{_timestamp()}] [HOTKEY] Нажата клавиша: {key_info}")

        try:
            # --- Проверка Q (три метода) ---
            if _is_q_key(key):
                _toggle_bot(bot)
                return None

            # --- Проверка Escape ---
            if key == keyboard.Key.esc:
                print(f"\n  [{_timestamp()}] [СИСТЕМА] Нажат Escape — завершение программы...")
                bot.shutdown()
                return False  # Остановить слушатель

        except Exception as e:
            print(f"  [{_timestamp()}] [HOTKEY] ОШИБКА в обработчике: {e}")

        return None

    listener = keyboard.Listener(on_press=on_press)
    print(f"  [{_timestamp()}] [HOTKEY] Слушатель создан, ожидает запуска")
    return listener


def _describe_key(key) -> str:
    """
    Формирует подробное текстовое описание нажатой клавиши
    для диагностического лога.

    Выводит все доступные атрибуты: тип, char, vk, name.

    Аргументы:
        key: объект нажатой клавиши от pynput

    Возвращает:
        Строка с описанием клавиши
    """
    parts = [f"type={type(key).__name__}"]

    # Символ (char)
    try:
        if hasattr(key, 'char'):
            parts.append(f"char={repr(key.char)}")
    except Exception:
        parts.append("char=<error>")

    # Виртуальный код (vk)
    try:
        if hasattr(key, 'vk') and key.vk is not None:
            parts.append(f"vk={key.vk} (0x{key.vk:02X})")
    except Exception:
        parts.append("vk=<error>")

    # Имя специальной клавиши (name)
    try:
        if hasattr(key, 'name'):
            parts.append(f"name={key.name}")
    except Exception:
        pass

    # Строковое представление
    parts.append(f"str={repr(str(key))}")

    return " | ".join(parts)


def _toggle_bot(bot) -> None:
    """
    Переключает состояние бота между работой и паузой.

    Аргументы:
        bot: экземпляр MinecraftBot
    """
    if not bot.is_running:
        # --- ЗАПУСК ---
        bot.is_running = True
        print(f"\n  [{_timestamp()}] ▶ БОТ ЗАПУЩЕН (нажмите Q для паузы)")
        _play_start_sound()
    else:
        # --- ОСТАНОВКА ---
        bot.is_running = False
        bot.release_all()  # Отпускаем все зажатые клавиши/кнопки
        print(f"\n  [{_timestamp()}] ⏸ БОТ ОСТАНОВЛЕН (нажмите Q для продолжения)")
        _play_stop_sound()
