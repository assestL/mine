# ===========================================================================
# math_utils.py — Математические утилиты для Minecraft-бота
# ===========================================================================
# Содержит функции для:
#   - Вычисления углов Yaw (горизонт) и Pitch (вертикаль)
#   - Перевода градусов в пиксели перемещения мыши
#   - Линейной интерполяции (Lerp)
#   - Нормализации углов
#   - Вычисления расстояний
# ===========================================================================

import math


# ---------------------------------------------------------------------------
# Константы Minecraft
# ---------------------------------------------------------------------------

# Высота глаз персонажа относительно координаты ног (Y)
EYE_HEIGHT = 1.62

# Максимальный радиус взаимодействия в Survival-режиме (в блоках)
INTERACTION_RADIUS = 4.5

# Максимальный угол Pitch (ограничение Minecraft: строго от -90 до +90)
MAX_PITCH = 90.0
MIN_PITCH = -90.0


def calculate_yaw(dx: float, dz: float) -> float:
    """
    Вычисляет угол Yaw (горизонтальный поворот) в системе координат Minecraft.

    Система координат Minecraft:
        Yaw =   0° → взгляд на юг  (+Z)
        Yaw =  90° → взгляд на запад (-X)
        Yaw = 180° → взгляд на север (-Z)
        Yaw = -90° → взгляд на восток (+X)

    Аргументы:
        dx: разница по оси X (target_x - player_x)
        dz: разница по оси Z (target_z - player_z)

    Возвращает:
        Угол Yaw в градусах [-180, 180]
    """
    # atan2(-dx, dz) даёт угол от оси Z (юг) с учётом инверсии X
    yaw = math.atan2(-dx, dz) * (180.0 / math.pi)
    return yaw


def calculate_pitch(dy: float, horizontal_dist: float) -> float:
    """
    Вычисляет угол Pitch (вертикальный наклон) в системе координат Minecraft.

    Система координат Minecraft:
        Pitch =  0°  → горизонтально
        Pitch = -90° → смотрим вверх (зенит)
        Pitch = +90° → смотрим вниз (надир)

    Аргументы:
        dy: разница по высоте (target_y - eye_y), где eye_y = player_y + 1.62
        horizontal_dist: горизонтальное расстояние до цели (sqrt(dx² + dz²))

    Возвращает:
        Угол Pitch в градусах [-90, 90]
    """
    if horizontal_dist < 0.001:
        # Цель прямо над/под нами — смотрим строго вверх или вниз
        return MIN_PITCH if dy > 0 else MAX_PITCH

    pitch = -math.atan2(dy, horizontal_dist) * (180.0 / math.pi)
    # Ограничиваем Pitch допустимым диапазоном
    return max(MIN_PITCH, min(MAX_PITCH, pitch))


def get_target_angles(
    player_x: float, player_y: float, player_z: float,
    target_x: float, target_y: float, target_z: float
) -> tuple[float, float]:
    """
    Вычисляет целевые углы Yaw и Pitch для наведения на блок.

    Аргументы:
        player_x, player_y, player_z: координаты ног персонажа
        target_x, target_y, target_z: координаты центра целевого блока

    Возвращает:
        Кортеж (target_yaw, target_pitch)
    """
    # Разницы координат (целимся в центр блока, +0.5 к целочисленным координатам)
    dx = (target_x + 0.5) - player_x
    dy = (target_y + 0.5) - (player_y + EYE_HEIGHT)
    dz = (target_z + 0.5) - player_z

    # Горизонтальное расстояние для вычисления Pitch
    horizontal_dist = math.sqrt(dx * dx + dz * dz)

    target_yaw = calculate_yaw(dx, dz)
    target_pitch = calculate_pitch(dy, horizontal_dist)

    return target_yaw, target_pitch


def degrees_to_mouse_delta(delta_degrees: float, sensitivity: float = 0.5) -> int:
    """
    Переводит угол поворота (в градусах) в количество пикселей перемещения мыши.

    Формула Minecraft для чувствительности:
        f = sensitivity * 0.6 + 0.2
        mouse_factor = f³ * 8.0
        Один пиксель мыши = mouse_factor * 0.15 градусов

    Аргументы:
        delta_degrees: необходимый поворот в градусах
        sensitivity: внутреннее значение чувствительности Minecraft (0.0 - 1.0)
                     0.0  = "0%"   (минимум)
                     0.5  = "100%" (стандарт)
                     1.0  = "200%" (максимум)

    Возвращает:
        Количество пикселей для перемещения мыши (целое число)
    """
    f = sensitivity * 0.6 + 0.2
    mouse_factor = f * f * f * 8.0
    degrees_per_pixel = mouse_factor * 0.15

    if degrees_per_pixel < 0.0001:
        return 0

    pixels = delta_degrees / degrees_per_pixel
    return int(round(pixels))


def normalize_angle(angle: float) -> float:
    """
    Нормализует угол в диапазон [-180, 180].

    Это нужно для корректного вычисления кратчайшего пути поворота.
    Например: поворот от 170° до -170° должен быть 20° вправо,
    а не 340° влево.

    Аргументы:
        angle: исходный угол в градусах

    Возвращает:
        Нормализованный угол в диапазоне [-180, 180]
    """
    while angle > 180.0:
        angle -= 360.0
    while angle <= -180.0:
        angle += 360.0
    return angle


def angle_difference(current: float, target: float) -> float:
    """
    Вычисляет кратчайшую разницу между двумя углами.

    Результат может быть отрицательным (поворот влево) или
    положительным (поворот вправо).

    Аргументы:
        current: текущий угол
        target: целевой угол

    Возвращает:
        Кратчайшая разница в градусах [-180, 180]
    """
    return normalize_angle(target - current)


def lerp(start: float, end: float, t: float) -> float:
    """
    Линейная интерполяция между двумя значениями.

    Используется для плавного перемещения мыши от текущего
    положения к целевому за N шагов.

    Аргументы:
        start: начальное значение
        end: конечное значение
        t: параметр интерполяции [0.0, 1.0]
           0.0 = start, 1.0 = end, 0.5 = середина

    Возвращает:
        Интерполированное значение
    """
    return start + (end - start) * t


def smoothstep(t: float) -> float:
    """
    Синусоидальное сглаживание (ease-in-out) для более
    естественного поворота камеры.

    Формула Hermite: 3t² - 2t³
    При t=0: результат 0, при t=1: результат 1
    Кривая плавно ускоряется в начале и замедляется к концу.

    Аргументы:
        t: параметр интерполяции [0.0, 1.0]

    Возвращает:
        Сглаженное значение [0.0, 1.0]
    """
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def distance_3d(
    x1: float, y1: float, z1: float,
    x2: float, y2: float, z2: float
) -> float:
    """
    Евклидово расстояние между двумя точками в 3D-пространстве.

    Аргументы:
        x1, y1, z1: координаты первой точки
        x2, y2, z2: координаты второй точки

    Возвращает:
        Расстояние (float)
    """
    dx = x2 - x1
    dy = y2 - y1
    dz = z2 - z1
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def distance_xz(
    x1: float, z1: float,
    x2: float, z2: float
) -> float:
    """
    Горизонтальное расстояние (без учёта высоты) между двумя точками.

    Используется для проверки: находится ли блок в горизонтальном
    радиусе взаимодействия.

    Аргументы:
        x1, z1: координаты первой точки (горизонтальные)
        x2, z2: координаты второй точки (горизонтальные)

    Возвращает:
        Горизонтальное расстояние (float)
    """
    dx = x2 - x1
    dz = z2 - z1
    return math.sqrt(dx * dx + dz * dz)
