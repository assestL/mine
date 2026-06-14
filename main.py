# ===========================================================================
# main.py — Точка входа в программу
# ===========================================================================
# Координирует запуск всех компонентов:
#   1. Выводит инструкции
#   2. Собирает данные от пользователя (координаты, настройки)
#   3. Создаёт экземпляр MinecraftBot
#   4. Запускает слушатель горячих клавиш
#   5. Запускает рабочий поток бота
#   6. Ожидает завершения (Escape)
#
# Безопасный выход: при любом исключении отпускаются все клавиши.
# ===========================================================================

import sys
import time

from bot import MinecraftBot
from hotkey import create_hotkey_listener
from input_handler import (
    print_instructions,
    get_cuboid_coordinates,
    get_player_position,
    get_player_direction,
    get_settings,
)


def main() -> None:
    """
    Главная функция программы.

    Последовательность:
        1. Приветствие и инструкции
        2. Ввод координат области
        3. Ввод позиции и направления персонажа
        4. Ввод настроек
        5. Создание бота и настройка области
        6. Запуск слушателя горячих клавиш
        7. Запуск рабочего потока
        8. Ожидание завершения
    """
    bot = None  # Определяем заранее для блока finally

    try:
        # --- 1. Приветствие ---
        print_instructions()

        # --- 2. Координаты кубоида ---
        (x1, y1, z1), (x2, y2, z2) = get_cuboid_coordinates()

        # --- 3. Позиция персонажа ---
        player_x, player_y, player_z = get_player_position()

        # --- 4. Направление взгляда ---
        player_yaw = get_player_direction()

        # --- 5. Настройки ---
        mouse_sensitivity, block_break_time = get_settings()

        # --- 6. Создание бота ---
        bot = MinecraftBot(
            start_x=player_x,
            start_y=player_y,
            start_z=player_z,
            start_yaw=player_yaw,
            start_pitch=0.0,  # Начинаем с горизонтального взгляда
            mouse_sensitivity=mouse_sensitivity,
            block_break_time=block_break_time,
        )

        # Устанавливаем область для очистки
        bot.set_mining_area(x1, y1, z1, x2, y2, z2)

        # --- 7. Запуск слушателя горячих клавиш ---
        listener = create_hotkey_listener(bot)
        listener.start()

        # Проверяем, что слушатель действительно запустился
        import time as _t
        _t.sleep(0.3)  # Даём потоку время стартовать
        print(f"  [DEBUG] Listener alive: {listener.is_alive()}")
        print(f"  [DEBUG] Listener thread: {listener.name}, daemon={listener.daemon}")

        # --- 8. Запуск рабочего потока бота ---
        bot.start_mining()

        # --- 9. Ожидание ---
        print("\n" + "=" * 60)
        print("  ✅ Бот готов к работе!")
        print("  ➡  Переключитесь в окно Minecraft")
        print("  ➡  Нажмите Q для запуска")
        print("  ➡  Нажмите Escape для выхода")
        print("  ➡  (все нажатия клавиш логируются в консоль)")
        print("=" * 60 + "\n")

        # Ожидаем завершения слушателя горячих клавиш
        # (он завершится при нажатии Escape)
        listener.join()

    except KeyboardInterrupt:
        # Ctrl+C в консоли — корректное завершение
        print("\n\n  [СИСТЕМА] Ctrl+C — завершение программы...")

    except Exception as e:
        # Любая непредвиденная ошибка
        print(f"\n\n  ❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # ВСЕГДА выполняем безопасное завершение
        if bot is not None:
            bot.shutdown()
        print("\n  Программа завершена.")
        sys.exit(0)


# ===========================================================================
# Точка входа
# ===========================================================================
if __name__ == '__main__':
    main()
