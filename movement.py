# ===========================================================================
# movement.py — Перемещение персонажа (с реальными координатами)
# ===========================================================================
# Использует F3+C (screen_reader) для получения РЕАЛЬНОЙ позиции
# вместо внутреннего dead reckoning, который дрейфует.
#
# Алгоритм перемещения:
#   1. F3+C → узнать реальную позицию
#   2. Повернуть камеру к цели
#   3. Зажать W на расчётное время
#   4. F3+C → проверить, дошли ли
#   5. Повторить если нужно (до 5 попыток)
# ===========================================================================

import time
import math
import datetime

import pydirectinput

from math_utils import (
    calculate_yaw,
    distance_xz,
    normalize_angle,
)
from camera import look_at_yaw
from screen_reader import sync_position


# ---------------------------------------------------------------------------
# Константы
# ---------------------------------------------------------------------------

# Скорость ходьбы (блоков/секунду)
WALK_SPEED = 4.317

# Допуск позиционирования — «дошли», если ближе этого расстояния
POSITION_TOLERANCE = 1.5

# Максимум попыток перемещения к одной точке
MAX_ATTEMPTS = 5

# Максимальное время ходьбы за одну попытку (секунды)
MAX_WALK_TIME = 4.0


def _timestamp() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]


def move_to(bot, target_x: float, target_z: float) -> bool:
    """
    Перемещает персонажа к указанной горизонтальной позиции.

    Использует реальные координаты из F3+C для навигации.
    Алгоритм:
        1. Читаем реальную позицию (F3+C)
        2. Если уже на месте — выходим
        3. Поворачиваем камеру в сторону цели
        4. Зажимаем W на расчётное время (расстояние / скорость)
        5. Проверяем позицию снова (F3+C)
        6. Повторяем если не дошли (до MAX_ATTEMPTS раз)

    Аргументы:
        bot: экземпляр MinecraftBot
        target_x: целевая координата X
        target_z: целевая координата Z

    Возвращает:
        True если дошли, False если не удалось
    """
    if not bot.is_running:
        return False

    for attempt in range(MAX_ATTEMPTS):
        if not bot.is_running:
            return False

        # --- Читаем реальную позицию ---
        sync_position(bot)

        dist = distance_xz(bot.current_x, bot.current_z, target_x, target_z)

        if dist < POSITION_TOLERANCE:
            return True

        # --- Поворачиваем к цели ---
        dx = target_x - bot.current_x
        dz = target_z - bot.current_z
        target_yaw = calculate_yaw(dx, dz)

        # Поворот камеры горизонтально (pitch=0, смотрим прямо)
        look_at_yaw(bot, target_yaw, 0.0)
        time.sleep(0.05)

        # --- Идём вперёд ---
        walk_time = dist / WALK_SPEED
        walk_time = min(walk_time, MAX_WALK_TIME)
        walk_time = max(walk_time, 0.2)  # Минимум 200мс

        print(
            f"  [{_timestamp()}] [ДВИЖЕНИЕ] "
            f"Попытка {attempt + 1}/{MAX_ATTEMPTS}: "
            f"расстояние={dist:.1f} блоков, "
            f"ходьба={walk_time:.1f}с"
        )

        pydirectinput.keyDown('w')
        # Ходим с проверкой флага остановки
        walk_start = time.time()
        while time.time() - walk_start < walk_time:
            if not bot.is_running:
                pydirectinput.keyUp('w')
                return False
            time.sleep(0.05)
        pydirectinput.keyUp('w')

        time.sleep(0.1)  # Пауза после остановки

    # --- Финальная проверка ---
    sync_position(bot)
    dist = distance_xz(bot.current_x, bot.current_z, target_x, target_z)
    if dist < POSITION_TOLERANCE:
        return True

    print(f"  [{_timestamp()}] [ДВИЖЕНИЕ] Не удалось дойти до ({target_x:.1f}, {target_z:.1f})")
    return False
