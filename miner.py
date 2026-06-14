import time
import ctypes
from config import MINE_DELAY, random_delay


class Miner:
    """
    Класс симуляции кликов мыши для разрушения блоков (совместимый с DirectInput).
    """
    def press_lmb(self) -> None:
        """
        Зажимает левую кнопку мыши (ЛКМ) для непрерывной добычи.
        """
        # MOUSEEVENTF_LEFTDOWN = 0x0002
        ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)

    def release_lmb(self) -> None:
        """
        Отпускает левую кнопку мыши (ЛКМ).
        """
        # MOUSEEVENTF_LEFTUP = 0x0004
        ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)

    def mine_block(self) -> None:
        """
        Совершает один клик ЛКМ.
        """
        self.press_lmb()
        time.sleep(0.01)
        self.release_lmb()
        time.sleep(random_delay(MINE_DELAY, 0.015))

    def mine_block_hold(self, duration: float = 0.15) -> None:
        """
        Зажимает ЛКМ на указанное время.
        """
        self.press_lmb()
        time.sleep(random_delay(duration, 0.02))
        self.release_lmb()
        time.sleep(random_delay(MINE_DELAY, 0.015))
