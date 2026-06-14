# ===========================================================================
# movement.py — Движение персонажа (WASD) и навигация к вейпоинтам
# ===========================================================================

import time
import math
import input_sim
from config import MOVE_DELAY, random_delay


class MovementEngine:
    """
    Класс симуляции нажатий клавиш для ходьбы и навигации к точкам.
    """

    def press(self, key: str, duration: float = 0.05) -> None:
        """
        Зажимает клавишу на указанное время (с небольшой погрешностью).
        """
        input_sim.press_key(key)
        time.sleep(random_delay(duration, 0.01))
        input_sim.release_key(key)

    def move_forward(self, duration: float = 0.2) -> None:
        self.press('w', duration)

    def move_backward(self, duration: float = 0.2) -> None:
        self.press('s', duration)

    def move_left(self, duration: float = 0.2) -> None:
        self.press('a', duration)

    def move_right(self, duration: float = 0.2) -> None:
        self.press('d', duration)

    def jump(self) -> None:
        self.press('space', 0.1)

    def sneak(self, duration: float = 0.1) -> None:
        self.press('shift', duration)

    def navigate_to_block(self, player_pos: tuple[float, float, float], target_pos: tuple[float, float, float], camera, reader) -> None:
        """
        Грубая навигация к целевой точке (waypoint).
        Поворачивает персонажа лицом к цели и шагает вперед.
        При возникновении препятствия подпрыгивает.
        """
        tx, ty, tz = target_pos
        px, py, pz = player_pos

        dx = tx - px
        dz = tz - pz
        dist_xz = math.sqrt(dx**2 + dz**2)

        # 1. Поворачиваем камеру в сторону цели по горизонтали
        yaw_to_target = math.degrees(math.atan2(dx, dz))
        camera.smooth_yaw_to(yaw_to_target)
        time.sleep(0.05)

        # 2. Идем вперед короткими шагами с перепроверкой координат
        max_attempts = 15
        attempts = 0
        stuck_count = 0
        
        while dist_xz > 1.5 and attempts < max_attempts:
            # Запоминаем координаты до шага
            old_x, old_z = px, pz

            # Делаем небольшой шаг вперед
            self.move_forward(0.15)
            time.sleep(0.05)

            # Считываем новые координаты
            new_pos = reader.get_player_coords()
            if new_pos is not None:
                nx, ny, nz = new_pos
                # Проверяем достоверность (макс. перемещение игрока за шаг 4.0 блока)
                if math.sqrt((nx - px)**2 + (ny - py)**2 + (nz - pz)**2) < 4.0:
                    px, py, pz = nx, ny, nz
                    dx = tx - px
                    dz = tz - pz
                    dist_xz = math.sqrt(dx**2 + dz**2)
                    
                    # Проверяем, застрял ли персонаж
                    dist_moved = math.sqrt((px - old_x)**2 + (pz - old_z)**2)
                    if dist_moved < 0.1:
                        stuck_count += 1
                        if stuck_count >= 3:
                            print("  [ДВИЖЕНИЕ] Застряли 3 раза подряд, прерываем движение для расчистки пути.")
                            break
                        # Пытаемся запрыгнуть на препятствие
                        self.jump()
                        time.sleep(0.05)
                        self.move_forward(0.15)
                    else:
                        stuck_count = 0

                    # Корректируем направление
                    yaw_to_target = math.degrees(math.atan2(dx, dz))
                    camera.smooth_yaw_to(yaw_to_target)
            else:
                # Если не удалось прочитать, предполагаем, что продвинулись
                dist_xz *= 0.85
                
            attempts += 1
