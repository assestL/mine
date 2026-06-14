# config.py
import random

# Путь к исполняемому файлу Tesseract OCR (для Windows)
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Название окна Minecraft (для захвата)
MINECRAFT_WINDOW_TITLE = "Minecraft"

# Задержки по умолчанию (в секундах)
MOVE_DELAY = 0.05
LOOK_STEP_DELAY = 0.008
MINE_DELAY = 0.08
HOTKEY_Q = 'q'

# Радиус взаимодействия персонажа (в блоках)
REACH_DISTANCE = 4.2  # Немного уменьшим для надежности

# Высота глаз персонажа относительно его ног Y
EYE_HEIGHT = 1.62

# Чувствительность мыши (пикселей на 1 градус)
PIXELS_PER_DEGREE = 8.0

# Скорость плавного поворота камеры (градусов за один шаг)
CAMERA_SMOOTH_STEP = 3.0

# Команда для телепортации наверх шахты при обновлении (например, "/mine", "/warp mine" или "" если выключено)
TELEPORT_COMMAND = ""


def random_delay(base: float, jitter: float = 0.015) -> float:
    """Возвращает задержку со случайным отклонением (антидетект)."""
    return max(0.005, base + random.uniform(-jitter, jitter))
