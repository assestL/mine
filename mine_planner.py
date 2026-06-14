# ===========================================================================
# mine_planner.py — Планировщик маршрута и обхода шахты
# ===========================================================================

import math
from config import REACH_DISTANCE


class MinePlanner:
    """
    Класс для расчета точек маршрута (вейпоинтов) персонажа и поиска блоков.
    """
    def __init__(self, x1: float, y1: float, z1: float, x2: float, y2: float, z2: float):
        # Нормализуем координаты углов шахты
        self.x_min = int(min(x1, x2))
        self.x_max = int(max(x1, x2))
        self.y_min = int(min(y1, y2))
        self.y_max = int(max(y1, y2))
        self.z_min = int(min(z1, z2))
        self.z_max = int(max(z1, z2))

    def generate_waypoints(self, layer_height: int = 2) -> list[tuple[int, int, int]]:
        """
        Генерирует список путевых точек (позиций игрока) послойно СВЕРХУ ВНИЗ.
        Внутри слоя движение происходит "змейкой" для максимальной скорости.
        """
        waypoints = []

        # Шаг сетки путевых точек зависит от дальности копания (с запасом в 1 блок)
        step = max(2, int(REACH_DISTANCE) - 1)

        # Проход сверху вниз (с max_y до min_y)
        y = self.y_max
        while y >= self.y_min:
            z_range = list(range(self.z_min, self.z_max + 1, step))
            # Если крайняя координата пропущена шагом сетки, принудительно добавляем ее
            if z_range[-1] != self.z_max:
                z_range.append(self.z_max)

            x_range_fwd = list(range(self.x_min, self.x_max + 1, step))
            if x_range_fwd[-1] != self.x_max:
                x_range_fwd.append(self.x_max)

            x_range_bwd = list(reversed(x_range_fwd))

            # Проход змейкой по сетке X/Z
            for i, z in enumerate(z_range):
                # Чередуем направление движения по оси X
                x_range = x_range_fwd if i % 2 == 0 else x_range_bwd
                for x in x_range:
                    waypoints.append((x, y, z))

            # Переходим на следующий (более глубокий) слой
            y -= layer_height

        return waypoints

    def get_max_unmined_y(self, mined_set: set) -> int | None:
        """
        Находит максимальный Y среди всех еще не выкопанных блоков в шахте.
        """
        for y in range(self.y_max, self.y_min - 1, -1):
            for x in range(self.x_min, self.x_max + 1):
                for z in range(self.z_min, self.z_max + 1):
                    if (x, y, z) not in mined_set:
                        return y
        return None

    def get_active_y_layers(self, player_pos: tuple[float, float, float], mined_set: set) -> list[int]:
        """
        Возвращает список активных Y слоев.
        Если игрок находится на нормальной высоте (близко к верхнему невыкопанному слою),
        то активными считаются верхняя пара невыкопанных слоев (движение сверху вниз).
        Если игрок провалился ниже (например, из-за взрыва), активными становятся слои 
        на уровне его текущей высоты, чтобы он мог расчистить место вокруг себя.
        """
        current_max_y = self.get_max_unmined_y(mined_set)
        if current_max_y is None:
            return []

        px, py, pz = player_pos
        py_int = int(round(py))

        # Если игрок упал ниже самого высокого невыкопанного слоя более чем на 2 блока
        if py_int < current_max_y - 2:
            # Целимся в слои на уровне игрока
            active_y = []
            for offset in [1, 0, -1, -2]:
                target_y = py_int + offset
                if self.y_min <= target_y <= self.y_max:
                    active_y.append(target_y)
            return active_y
        else:
            # Обычный режим: пара верхних невыкопанных слоев
            k = (self.y_max - current_max_y) // 2
            y_upper = self.y_max - 2 * k
            y_lower = y_upper - 1
            
            active_y = [y_upper]
            if y_lower >= self.y_min:
                active_y.append(y_lower)
            return active_y

    def get_snake_index(self, bx: int, by: int, bz: int) -> int:
        """
        Вычисляет индекс блока в строгой последовательности змейки (strip-mining).
        """
        x_idx = bx - self.x_min
        
        # Направление движения по оси Z (чередуется для каждого столбца X)
        if x_idx % 2 == 0:
            z_idx = bz - self.z_min
        else:
            z_idx = self.z_max - bz
            
        z_length = self.z_max - self.z_min + 1
        col_idx = x_idx * z_length + z_idx
        
        # Верхние блоки (больший Y) должны иметь меньший индекс, чтобы копаться первыми.
        # Вычитаем Y из 400 (Y в Minecraft <= 320), чтобы перевернуть сортировку:
        # Чем выше блок, тем меньше его (400 - by), значит он будет выкопан раньше нижнего.
        return col_idx * 1000 + (400 - by)

    def get_blocks_near(self, player_pos: tuple[float, float, float], mined_set: set) -> list[tuple[int, int, int]]:
        """
        Возвращает список всех блоков шахты в радиусе REACH_DISTANCE от персонажа,
        которые еще не были выкопаны и находятся на ТЕКУЩИХ АКТИВНЫХ СЛОЯХ Y.
        Сортирует их строго по индексу змейки, чтобы бот не крутился вокруг своей оси, 
        а копал "проходкой туннелями" (сначала полностью один X, потом следующий).
        """
        px, py, pz = player_pos
        blocks = []

        active_y = self.get_active_y_layers(player_pos, mined_set)
        if not active_y:
            return []

        # Сканируем кубоид вокруг игрока в пределах REACH_DISTANCE
        r = int(math.ceil(REACH_DISTANCE))
        
        bx_min = max(self.x_min, int(math.floor(px - r)))
        bx_max = min(self.x_max, int(math.ceil(px + r)))
        bz_min = max(self.z_min, int(math.floor(pz - r)))
        bz_max = min(self.z_max, int(math.ceil(pz + r)))

        feet_y = int(math.floor(py))

        for bx in range(bx_min, bx_max + 1):
            for by in active_y:
                # Фильтр: никогда не копаем ниже уровня ног, чтобы не проваливаться под себя
                if by < feet_y:
                    continue

                for bz in range(bz_min, bz_max + 1):
                    if (bx, by, bz) in mined_set:
                        continue

                    # Вычисляем расстояние от глаз игрока до центра блока
                    dist = math.sqrt(
                        (bx + 0.5 - px)**2 +
                        (by + 0.5 - (py + 1.62))**2 +
                        (bz + 0.5 - pz)**2
                    )

                    if dist <= REACH_DISTANCE:
                        # Фильтр: копаем только в пределах горизонтального радиуса 2.3,
                        # чтобы копать проходкой (тоннелем) и заставлять бота бежать вперед, а не выбивать пещеру вокруг
                        dist_xz = math.sqrt((bx + 0.5 - px)**2 + (bz + 0.5 - pz)**2)
                        if dist_xz > 2.3:
                            continue

                        # Строгая сортировка по змейке
                        snake_index = self.get_snake_index(bx, by, bz)
                        
                        # Штраф за копание блока под собой (на случай клиппинга)
                        penalty = 1000000 if dist_xz < 0.8 else 0
                        
                        blocks.append(((bx, by, bz), snake_index + penalty))

        # Сортируем блоки по индексу змейки
        blocks.sort(key=lambda item: item[1])
        return [item[0] for item in blocks]

    def get_closest_unmined_block(self, player_pos: tuple[float, float, float], mined_set: set) -> tuple[int, int, int] | None:
        """
        Находит следующий еще не выкопанный блок в шахте согласно строгой последовательности змейки.
        Бот будет направляться к нему.
        """
        active_y = self.get_active_y_layers(player_pos, mined_set)
        if not active_y:
            return None
            
        best_block = None
        min_index = float('inf')
        
        for y in active_y:
            for x in range(self.x_min, self.x_max + 1):
                for z in range(self.z_min, self.z_max + 1):
                    if (x, y, z) in mined_set:
                        continue
                    
                    idx = self.get_snake_index(x, y, z)
                    if idx < min_index:
                        min_index = idx
                        best_block = (x, y, z)
                        
        return best_block
