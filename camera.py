# ===========================================================================
# camera.py — Управление камерой (БЫСТРАЯ ВЕРСИЯ)
# ===========================================================================
# Плавный поворот камеры через относительное перемещение мыши.
# Оптимизировано для скорости: адаптивное число шагов
# (меньше шагов для малых углов).
# ===========================================================================

import time
import math

import pydirectinput

from math_utils import (
    get_target_angles,
    angle_difference,
    degrees_to_mouse_delta,
    normalize_angle,
    calculate_yaw,
)


# ---------------------------------------------------------------------------
# Настройки скорости поворота
# ---------------------------------------------------------------------------

# Задержка между микрошагами (секунды)
STEP_DELAY = 0.004  # 4 мс (было 8 мс)

# Минимальный порог — углы меньше этого не поворачиваем
MIN_ANGLE_THRESHOLD = 0.2


def _adaptive_steps(delta_yaw: float, delta_pitch: float) -> int:
    """
    Вычисляет оптимальное количество шагов поворота
    в зависимости от величины угла.

    Маленькие углы (<10°): 3 шага ≈ 12мс
    Средние (10-45°): 5 шагов ≈ 20мс
    Большие (45-90°): 7 шагов ≈ 28мс
    Очень большие (>90°): 10 шагов ≈ 40мс

    Аргументы:
        delta_yaw: разница горизонтального угла
        delta_pitch: разница вертикального угла

    Возвращает:
        Количество шагов
    """
    max_delta = max(abs(delta_yaw), abs(delta_pitch))

    if max_delta < 10:
        return 3
    elif max_delta < 45:
        return 5
    elif max_delta < 90:
        return 7
    else:
        return 10


def smooth_look_at(bot, target_x: float, target_y: float, target_z: float) -> None:
    """
    Плавно поворачивает камеру персонажа на указанную точку.

    Использует адаптивное число шагов для скорости.
    Маленькие повороты выполняются за ~12мс,
    большие — за ~40мс.

    Аргументы:
        bot: экземпляр MinecraftBot
        target_x, target_y, target_z: координаты целевого блока
    """
    if not bot.is_running:
        return

    # Вычислить целевые углы
    target_yaw, target_pitch = get_target_angles(
        bot.current_x, bot.current_y, bot.current_z,
        target_x, target_y, target_z
    )

    # Кратчайшие разницы углов
    delta_yaw = angle_difference(bot.current_yaw, target_yaw)
    delta_pitch = angle_difference(bot.current_pitch, target_pitch)

    # Если уже смотрим на цель — пропускаем
    if abs(delta_yaw) < MIN_ANGLE_THRESHOLD and abs(delta_pitch) < MIN_ANGLE_THRESHOLD:
        return

    # Адаптивное число шагов
    steps = _adaptive_steps(delta_yaw, delta_pitch)

    # Общее количество пикселей для поворота
    total_px_x = degrees_to_mouse_delta(delta_yaw, bot.mouse_sensitivity)
    total_px_y = degrees_to_mouse_delta(delta_pitch, bot.mouse_sensitivity)

    accumulated_x = 0
    accumulated_y = 0

    for step in range(1, steps + 1):
        if not bot.is_running:
            return

        t = step / steps
        # Линейная интерполяция (без smoothstep для максимальной скорости)
        target_px_x = int(round(total_px_x * t))
        target_px_y = int(round(total_px_y * t))

        step_px_x = target_px_x - accumulated_x
        step_px_y = target_px_y - accumulated_y

        if step_px_x != 0 or step_px_y != 0:
            pydirectinput.moveRel(step_px_x, step_px_y, relative=True)

        accumulated_x = target_px_x
        accumulated_y = target_px_y

        time.sleep(STEP_DELAY)

    # Обновить углы бота
    bot.current_yaw = normalize_angle(target_yaw)
    bot.current_pitch = max(-90.0, min(90.0, target_pitch))


def instant_look_at(bot, target_x: float, target_y: float, target_z: float) -> None:
    """
    Мгновенный поворот камеры (без сглаживания).
    Используется при перемещении к новой позиции.
    """
    if not bot.is_running:
        return

    target_yaw, target_pitch = get_target_angles(
        bot.current_x, bot.current_y, bot.current_z,
        target_x, target_y, target_z
    )

    delta_yaw = angle_difference(bot.current_yaw, target_yaw)
    delta_pitch = angle_difference(bot.current_pitch, target_pitch)

    px_x = degrees_to_mouse_delta(delta_yaw, bot.mouse_sensitivity)
    px_y = degrees_to_mouse_delta(delta_pitch, bot.mouse_sensitivity)

    if px_x != 0 or px_y != 0:
        pydirectinput.moveRel(px_x, px_y, relative=True)

    bot.current_yaw = normalize_angle(target_yaw)
    bot.current_pitch = max(-90.0, min(90.0, target_pitch))


def look_at_yaw(bot, target_yaw: float, target_pitch: float = 0.0) -> None:
    """
    Поворачивает камеру в указанном направлении (абсолютные углы).
    Используется для поворота перед началом движения.
    """
    if not bot.is_running:
        return

    delta_yaw = angle_difference(bot.current_yaw, target_yaw)
    delta_pitch = angle_difference(bot.current_pitch, target_pitch)

    steps = _adaptive_steps(delta_yaw, delta_pitch)
    total_px_x = degrees_to_mouse_delta(delta_yaw, bot.mouse_sensitivity)
    total_px_y = degrees_to_mouse_delta(delta_pitch, bot.mouse_sensitivity)

    accumulated_x = 0
    accumulated_y = 0

    for step in range(1, steps + 1):
        if not bot.is_running:
            return
        t = step / steps
        target_px_x = int(round(total_px_x * t))
        target_px_y = int(round(total_px_y * t))
        step_px_x = target_px_x - accumulated_x
        step_px_y = target_px_y - accumulated_y
        if step_px_x != 0 or step_px_y != 0:
            pydirectinput.moveRel(step_px_x, step_px_y, relative=True)
        accumulated_x = target_px_x
        accumulated_y = target_px_y
        time.sleep(STEP_DELAY)

    bot.current_yaw = normalize_angle(target_yaw)
    bot.current_pitch = max(-90.0, min(90.0, target_pitch))
