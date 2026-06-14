# ===========================================================================
# camera.py — Плавное управление камерой (мышь)
# ===========================================================================

import math
import time
import random
import ctypes
from config import PIXELS_PER_DEGREE, CAMERA_SMOOTH_STEP, EYE_HEIGHT


class CameraEngine:
    """
    Класс управления камерой через симуляцию перемещений мыши.
    """
    def __init__(self):
        self.current_yaw = 0.0    # 0 = Юг, 90 = Запад, 180 = Север, -90 = Восток
        self.current_pitch = 0.0  # 0 = Горизонт, +90 = Вниз, -90 = Вверх

    def calibrate(self, yaw: float, pitch: float) -> None:
        """
        Калибрует текущие углы камеры реальными значениями из игры.
        """
        self.current_yaw = yaw
        self.current_pitch = pitch

    def _move_mouse_delta(self, dx_deg: float, dy_deg: float) -> None:
        """
        Перемещает мышь на относительное количество градусов (совместимо с DirectInput).
        """
        dx_px = int(dx_deg * PIXELS_PER_DEGREE)
        dy_px = int(dy_deg * PIXELS_PER_DEGREE)
        # MOUSEEVENTF_MOVE = 0x0001
        ctypes.windll.user32.mouse_event(0x0001, dx_px, dy_px, 0, 0)

    def smooth_rotate_to(self, target_yaw: float, target_pitch: float, step: float = None) -> None:
        """
        Плавно поворачивает камеру к целевым углам шагами по CAMERA_SMOOTH_STEP.
        """
        if step is None:
            step = CAMERA_SMOOTH_STEP

        # Нормализуем Yaw дельту в [-180, 180]
        dyaw = target_yaw - self.current_yaw
        dyaw = (dyaw + 180) % 360 - 180

        # Нормализуем Pitch дельту
        dpitch = target_pitch - self.current_pitch
        dpitch = max(-90.0 - self.current_pitch, min(90.0 - self.current_pitch, dpitch))

        total_abs = max(abs(dyaw), abs(dpitch))
        if total_abs < 0.3:
            return  # Уже смотрим близко к цели

        steps = max(1, int(total_abs / step))

        yaw_step = dyaw / steps
        pitch_step = dpitch / steps

        for _ in range(steps):
            self._move_mouse_delta(yaw_step, pitch_step)
            self.current_yaw += yaw_step
            self.current_pitch += pitch_step
            # Небольшая пауза между шагами для плавности
            time.sleep(0.006)

    def smooth_yaw_to(self, target_yaw: float) -> None:
        """
        Поворачивает камеру только по горизонтали (Pitch остается прежним).
        """
        self.smooth_rotate_to(target_yaw, self.current_pitch)

    def look_at_block(self, player_pos: tuple[float, float, float], block_pos: tuple[int, int, int]) -> None:
        """
        Вычисляет углы к центру блока с учетом высоты глаз и плавно наводит камеру.
        Антидетект: добавляет небольшую случайную погрешность в прицеливание.
        """
        px, py, pz = player_pos
        bx, by, bz = block_pos

        # Центр блока с небольшим случайным смещением (антидетект)
        jitter_x = random.uniform(-0.12, 0.12)
        jitter_y = random.uniform(-0.12, 0.12)
        jitter_z = random.uniform(-0.12, 0.12)

        target_x = bx + 0.5 + jitter_x
        target_y = by + 0.5 + jitter_y
        target_z = bz + 0.5 + jitter_z

        eye_y = py + EYE_HEIGHT  # Высота глаз

        dx = target_x - px
        dy = target_y - eye_y
        dz = target_z - pz

        # Угол горизонтального поворота (Yaw)
        yaw = math.degrees(math.atan2(dx, dz))

        # Угол вертикального поворота (Pitch)
        dist_xz = math.sqrt(dx**2 + dz**2)
        pitch = math.degrees(math.atan2(-dy, dist_xz))

        self.smooth_rotate_to(yaw, pitch)
