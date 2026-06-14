# ===========================================================================
# mining.py — Модуль копания блоков и генерации порядка очистки
# ===========================================================================
# Содержит:
#   - Генерацию списка блоков кубоида в порядке «змейки» послойно
#   - Логику копания одного блока (наведение + удержание ЛКМ)
#   - Основной цикл очистки области
#   - Защиту от самокопания (блок под ногами)
# ===========================================================================

import time

import pydirectinput

from math_utils import (
    distance_3d,
    distance_xz,
    INTERACTION_RADIUS,
    EYE_HEIGHT,
)
from camera import smooth_look_at
from movement import move_to


# ---------------------------------------------------------------------------
# Настройки копания
# ---------------------------------------------------------------------------

# Время удержания ЛКМ для разрушения блока (секунды).
# Зависит от инструмента и типа блока. Значение по умолчанию —
# среднее с запасом (камень алмазной киркой ≈ 0.3 сек,
# обсидиан алмазной киркой ≈ 9.4 сек).
# Пользователь может настроить через input_handler.
DEFAULT_BREAK_TIME = 0.5

# Дополнительная задержка после разрушения блока (секунды)
# Нужна для подбора дропа и стабилизации
POST_BREAK_DELAY = 0.1

# Максимальное расстояние, с которого можно копать (блоков)
# Чуть меньше реального радиуса для надёжности
SAFE_REACH = 4.0


def generate_mining_order(
    x1: int, y1: int, z1: int,
    x2: int, y2: int, z2: int
) -> list[tuple[int, int, int]]:
    """
    Генерирует список координат блоков внутри кубоида в оптимальном
    порядке для копания.

    Порядок обхода:
        1. Сверху вниз по Y (сначала верхние слои, чтобы не закопаться)
        2. Внутри каждого слоя — «змейкой» (boustrophedon):
           - Чётные ряды Z: X слева направо
           - Нечётные ряды Z: X справа налево
        Это минимизирует лишние перемещения персонажа.

    Аргументы:
        x1, y1, z1: координаты первого угла кубоида
        x2, y2, z2: координаты второго угла кубоида

    Возвращает:
        Список кортежей (x, y, z) — координаты блоков в порядке копания

    Пример для области 3x2x3 (x: 0-2, y: 10-11, z: 0-2):
        Y=11 (верхний слой):
            Z=0: (0,11,0), (1,11,0), (2,11,0)
            Z=1: (2,11,1), (1,11,1), (0,11,1)  ← реверс
            Z=2: (0,11,2), (1,11,2), (2,11,2)
        Y=10 (нижний слой):
            Z=0: (0,10,0), (1,10,0), (2,10,0)
            ...
    """
    # Определяем границы (min/max), чтобы порядок не зависел от
    # того, какая точка "первая", а какая "вторая"
    min_x, max_x = min(x1, x2), max(x1, x2)
    min_y, max_y = min(y1, y2), max(y1, y2)
    min_z, max_z = min(z1, z2), max(z1, z2)

    blocks = []

    # Обходим сверху вниз по Y
    for y in range(max_y, min_y - 1, -1):
        # Индекс ряда Z для определения направления змейки
        z_index = 0
        for z in range(min_z, max_z + 1):
            if z_index % 2 == 0:
                # Чётный ряд: X слева направо
                for x in range(min_x, max_x + 1):
                    blocks.append((x, y, z))
            else:
                # Нечётный ряд: X справа налево (реверс)
                for x in range(max_x, min_x - 1, -1):
                    blocks.append((x, y, z))
            z_index += 1

    return blocks


def _is_block_under_feet(bot, bx: int, by: int, bz: int) -> bool:
    """
    Проверяет, находится ли блок непосредственно под ногами персонажа.

    Копать блок под собой опасно: персонаж упадёт, и внутренние
    координаты рассинхронизируются.

    Аргументы:
        bot: экземпляр MinecraftBot
        bx, by, bz: координаты блока

    Возвращает:
        True, если блок прямо под ногами
    """
    # Блок под ногами: та же X/Z позиция, Y на 1 ниже ног персонажа
    player_block_x = int(round(bot.current_x))
    player_block_z = int(round(bot.current_z))
    player_block_y = int(bot.current_y)  # Y ног — целое число

    return (bx == player_block_x and
            bz == player_block_z and
            by == player_block_y - 1)


def _find_safe_standpoint(
    bot, bx: int, by: int, bz: int,
    mined_blocks: set[tuple[int, int, int]]
) -> tuple[float, float] | None:
    """
    Ищет безопасную позицию рядом с блоком, с которой его можно
    выкопать, не провалившись.

    Проверяет 4 соседних блока (N/S/E/W). Безопасная позиция — та,
    где под ногами есть твёрдый блок (не был выкопан ранее).

    Аргументы:
        bot: экземпляр MinecraftBot
        bx, by, bz: координаты блока для копания
        mined_blocks: множество уже выкопанных блоков

    Возвращает:
        Кортеж (safe_x, safe_z) или None, если безопасной позиции нет
    """
    # Соседние позиции (смещение по X, Z)
    neighbors = [(1, 0), (-1, 0), (0, 1), (0, -1)]

    for dx, dz in neighbors:
        safe_x = bx + dx
        safe_z = bz + dz
        # Блок, на котором будем стоять (под ногами)
        floor_block = (safe_x, by, safe_z)

        # Проверяем, что пол не был выкопан
        if floor_block not in mined_blocks:
            # Проверяем, что позиция в пределах досягаемости
            dist = distance_xz(safe_x + 0.5, safe_z + 0.5,
                               bx + 0.5, bz + 0.5)
            if dist <= SAFE_REACH:
                return float(safe_x) + 0.5, float(safe_z) + 0.5

    return None


def mine_block(bot, bx: int, by: int, bz: int) -> bool:
    """
    Выкапывает один блок: наводит камеру и удерживает ЛКМ.

    Алгоритм:
        1. Проверить расстояние до блока. Если далеко — подойти.
        2. Плавно навести камеру на центр блока.
        3. Зажать ЛКМ на время block_break_time.
        4. Отпустить ЛКМ.

    Аргументы:
        bot: экземпляр MinecraftBot
        bx, by, bz: координаты блока

    Возвращает:
        True, если блок успешно выкопан (или предполагается, что выкопан)
        False, если произошла ошибка или бот остановлен
    """
    if not bot.is_running:
        return False

    # --- Шаг 1: Подойти к блоку, если он далеко ---
    dist = distance_3d(
        bot.current_x, bot.current_y + EYE_HEIGHT, bot.current_z,
        bx + 0.5, by + 0.5, bz + 0.5
    )

    if dist > SAFE_REACH:
        # Вычисляем позицию, с которой можно достать до блока
        # (подходим на расстояние 2 блока от цели)
        approach_x, approach_z = _calculate_approach_position(
            bot.current_x, bot.current_z,
            bx + 0.5, bz + 0.5
        )
        success = move_to(bot, approach_x, approach_z)
        if not success:
            return False

    if not bot.is_running:
        return False

    # --- Шаг 2: Плавно навести камеру ---
    smooth_look_at(bot, bx, by, bz)

    if not bot.is_running:
        return False

    # --- Шаг 3: Зажать ЛКМ (копание) ---
    pydirectinput.mouseDown(button='left')
    try:
        # Ждём время разрушения блока, проверяя флаг остановки
        break_time = bot.block_break_time
        check_interval = 0.05  # Проверяем каждые 50 мс
        elapsed = 0.0

        while elapsed < break_time:
            if not bot.is_running:
                return False
            sleep_time = min(check_interval, break_time - elapsed)
            time.sleep(sleep_time)
            elapsed += sleep_time

    finally:
        # --- Шаг 4: ВСЕГДА отпускаем ЛКМ ---
        pydirectinput.mouseUp(button='left')

    # Пауза после разрушения
    time.sleep(POST_BREAK_DELAY)

    return True


def _calculate_approach_position(
    player_x: float, player_z: float,
    target_x: float, target_z: float
) -> tuple[float, float]:
    """
    Вычисляет позицию подхода к целевому блоку.

    Мы хотим подойти на расстояние ~2 блока от цели,
    двигаясь по прямой от текущей позиции.

    Аргументы:
        player_x, player_z: текущая позиция игрока
        target_x, target_z: координаты целевого блока

    Возвращает:
        Кортеж (approach_x, approach_z) — позиция подхода
    """
    dx = target_x - player_x
    dz = target_z - player_z
    dist = distance_xz(player_x, player_z, target_x, target_z)

    if dist < 0.1:
        return target_x, target_z

    # Нормализуем вектор и смещаем на 2 блока от цели
    approach_dist = 2.0
    ratio = (dist - approach_dist) / dist
    ratio = max(0.0, ratio)

    approach_x = player_x + dx * ratio
    approach_z = player_z + dz * ratio

    return approach_x, approach_z


def mine_area(bot, blocks: list[tuple[int, int, int]]) -> None:
    """
    Основной цикл очистки области: последовательно копает все блоки
    из списка, обрабатывая edge cases.

    Алгоритм:
        Для каждого блока в списке:
        1. Если блок под ногами — сместиться на безопасную позицию.
        2. Подойти к блоку (если далеко).
        3. Навести камеру и выкопать.
        4. Пометить блок как выкопанный.
        5. Вывести прогресс в консоль.

    Аргументы:
        bot: экземпляр MinecraftBot
        blocks: список координат блоков (в порядке копания)
    """
    total = len(blocks)
    mined = 0
    mined_blocks: set[tuple[int, int, int]] = set()

    print(f"\n{'='*60}")
    print(f"  Начинаем очистку области: {total} блоков")
    print(f"{'='*60}\n")

    for i, (bx, by, bz) in enumerate(blocks):
        if not bot.is_running:
            print(f"\n  [СТОП] Бот остановлен на блоке {i+1}/{total}")
            return

        # --- Проверка: блок под ногами? ---
        if _is_block_under_feet(bot, bx, by, bz):
            print(f"  [ЗАЩИТА] Блок ({bx}, {by}, {bz}) под ногами — ищем безопасную позицию")
            safe_pos = _find_safe_standpoint(bot, bx, by, bz, mined_blocks)
            if safe_pos:
                safe_x, safe_z = safe_pos
                print(f"           Смещаемся на ({safe_x:.1f}, {safe_z:.1f})")
                move_to(bot, safe_x, safe_z)
            else:
                print(f"           Безопасная позиция не найдена — пропускаем блок")
                continue

        # --- Копаем блок ---
        success = mine_block(bot, bx, by, bz)
        if success:
            mined += 1
            mined_blocks.add((bx, by, bz))

            # Прогресс каждые 10 блоков
            if mined % 10 == 0 or mined == total:
                progress = (mined / total) * 100
                print(f"  [ПРОГРЕСС] {mined}/{total} блоков ({progress:.1f}%)")
        else:
            if not bot.is_running:
                print(f"\n  [СТОП] Бот остановлен на блоке {i+1}/{total}")
                return
            print(f"  [ОШИБКА] Не удалось выкопать блок ({bx}, {by}, {bz}) — пропускаем")

    # --- Итоги ---
    print(f"\n{'='*60}")
    print(f"  Очистка завершена!")
    print(f"  Выкопано: {mined}/{total} блоков")
    if mined < total:
        print(f"  Пропущено: {total - mined} блоков")
    print(f"{'='*60}\n")
