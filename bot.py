# ===========================================================================
# bot.py — Основной класс MinecraftBot
# ===========================================================================
# Хранит всё состояние бота:
#   - Текущие координаты (X, Y, Z)
#   - Текущие углы камеры (Yaw, Pitch)
#   - Настройки (чувствительность мыши, время копания)
#   - Флаги работы (is_running, is_shutdown)
#
# Предоставляет методы-обёртки для модулей camera, movement, mining,
# а также аварийную остановку (release_all / emergency_stop).
# ===========================================================================

import threading
import time

import pydirectinput

from math_utils import INTERACTION_RADIUS
from mining import generate_mining_order, mine_area


class MinecraftBot:
    """
    Главный класс бота для автоматизации копания в Minecraft.

    Хранит всё внутреннее состояние и координирует работу
    модулей камеры, перемещения и копания.

    Атрибуты:
        current_x, current_y, current_z (float):
            Текущие координаты персонажа (ноги).
            Устанавливаются пользователем при старте и обновляются
            при перемещении/копании.

        current_yaw (float):
            Текущий горизонтальный угол камеры (градусы).
            Minecraft: 0=юг, 90=запад, ±180=север, -90=восток.

        current_pitch (float):
            Текущий вертикальный угол камеры (градусы).
            Minecraft: 0=горизонт, -90=вверх, +90=вниз.

        mouse_sensitivity (float):
            Внутреннее значение чувствительности мыши Minecraft.
            0.0 = 0%, 0.5 = 100% (стандарт), 1.0 = 200%.

        block_break_time (float):
            Время удержания ЛКМ для разрушения блока (секунды).

        is_running (bool):
            Флаг активности бота. True = работает, False = пауза.
            Переключается горячей клавишей Q.

        is_shutdown (bool):
            Флаг полного завершения. True = программа завершается.
            Устанавливается при нажатии Escape.
    """

    def __init__(
        self,
        start_x: float,
        start_y: float,
        start_z: float,
        start_yaw: float = 0.0,
        start_pitch: float = 0.0,
        mouse_sensitivity: float = 0.5,
        block_break_time: float = 0.5,
    ):
        """
        Инициализирует бота с начальными координатами и настройками.

        Аргументы:
            start_x: начальная координата X персонажа
            start_y: начальная координата Y персонажа (ноги)
            start_z: начальная координата Z персонажа
            start_yaw: начальный Yaw (направление взгляда)
                       0=юг, 90=запад, ±180=север, -90=восток
            start_pitch: начальный Pitch (наклон головы)
                         0=горизонтально
            mouse_sensitivity: чувствительность мыши (0.0 - 1.0)
            block_break_time: время разрушения блока (секунды)
        """
        # --- Координаты ---
        self.current_x: float = start_x
        self.current_y: float = start_y
        self.current_z: float = start_z

        # --- Углы камеры ---
        self.current_yaw: float = start_yaw
        self.current_pitch: float = start_pitch

        # --- Настройки ---
        self.mouse_sensitivity: float = mouse_sensitivity
        self.block_break_time: float = block_break_time
        self.interaction_radius: float = INTERACTION_RADIUS

        # --- Флаги состояния ---
        self.is_running: bool = False
        self.is_shutdown: bool = False

        # --- Поток выполнения ---
        self._worker_thread: threading.Thread | None = None
        self._blocks_to_mine: list[tuple[int, int, int]] = []

        # --- Блокировка для потокобезопасности ---
        self._lock = threading.Lock()

        print(f"  [БОТ] Инициализирован:")
        print(f"         Позиция: ({start_x}, {start_y}, {start_z})")
        print(f"         Взгляд:  Yaw={start_yaw}°, Pitch={start_pitch}°")
        print(f"         Чувствительность мыши: {mouse_sensitivity * 200:.0f}%")
        print(f"         Время копания блока: {block_break_time} сек")

    def set_mining_area(
        self,
        x1: int, y1: int, z1: int,
        x2: int, y2: int, z2: int
    ) -> None:
        """
        Устанавливает область для очистки (кубоид).

        Генерирует оптимальный порядок блоков (сверху вниз, змейкой)
        и сохраняет его для последующего выполнения.

        Аргументы:
            x1, y1, z1: координаты первого угла кубоида
            x2, y2, z2: координаты второго угла кубоида
        """
        self._blocks_to_mine = generate_mining_order(
            x1, y1, z1, x2, y2, z2
        )

        # Вычисляем размеры области
        size_x = abs(x2 - x1) + 1
        size_y = abs(y2 - y1) + 1
        size_z = abs(z2 - z1) + 1

        print(f"\n  [ОБЛАСТЬ] Установлена:")
        print(f"            Угол 1: ({x1}, {y1}, {z1})")
        print(f"            Угол 2: ({x2}, {y2}, {z2})")
        print(f"            Размер: {size_x} × {size_y} × {size_z}")
        print(f"            Всего блоков: {len(self._blocks_to_mine)}")

    def start_mining(self) -> None:
        """
        Запускает процесс копания в отдельном потоке.

        Основная логика бота работает в фоновом потоке, чтобы
        не блокировать перехватчик горячих клавиш и консоль.
        """
        if not self._blocks_to_mine:
            print("  [ОШИБКА] Область для очистки не задана!")
            return

        if self._worker_thread and self._worker_thread.is_alive():
            print("  [ОШИБКА] Бот уже выполняет задачу!")
            return

        self._worker_thread = threading.Thread(
            target=self._mining_worker,
            name="MinecraftBot-Worker",
            daemon=True  # Поток-демон: завершится при выходе из программы
        )
        self._worker_thread.start()

    def _mining_worker(self) -> None:
        """
        Рабочий поток бота. Ожидает запуска (is_running = True)
        и выполняет копание блоков.

        Цикл:
            1. Ждём, пока бот не будет запущен (Q)
            2. Копаем блоки из списка
            3. Если бот остановлен (Q) — приостанавливаем
            4. Если бот завершён (Esc) — выходим
        """
        print("\n  [ПОТОК] Рабочий поток запущен. Ожидаем нажатия Q...\n")

        while not self.is_shutdown:
            if self.is_running:
                # Задержка перед началом работы (чтобы пользователь
                # успел переключиться в окно Minecraft)
                print("  [ПОТОК] Начинаем через 3 секунды...")
                for i in range(3, 0, -1):
                    if not self.is_running or self.is_shutdown:
                        break
                    print(f"          {i}...")
                    time.sleep(1.0)

                if self.is_running and not self.is_shutdown:
                    mine_area(self, self._blocks_to_mine)

                # После завершения копания — ставим на паузу
                if self.is_running:
                    self.is_running = False
                    print("\n  [ПОТОК] Все блоки обработаны. Бот остановлен.")
                    break
            else:
                # Ждём запуска, проверяя каждые 100 мс
                time.sleep(0.1)

        print("  [ПОТОК] Рабочий поток завершён.")

    def release_all(self) -> None:
        """
        Отпускает все зажатые клавиши и кнопки мыши.

        Вызывается при:
            - Нажатии Q (пауза)
            - Аварийной остановке
            - Завершении программы

        Отпускаем: W, A, S, D, Space, Shift, ЛКМ.
        """
        keys_to_release = ['w', 'a', 's', 'd', 'space', 'shift']

        for key in keys_to_release:
            try:
                pydirectinput.keyUp(key)
            except Exception:
                pass  # Игнорируем ошибки — главное отпустить всё

        try:
            pydirectinput.mouseUp(button='left')
        except Exception:
            pass

        try:
            pydirectinput.mouseUp(button='right')
        except Exception:
            pass

    def shutdown(self) -> None:
        """
        Полностью завершает работу бота.

        Устанавливает флаг завершения, отпускает все кнопки,
        ожидает завершения рабочего потока.
        """
        print("\n  [БОТ] Завершение работы...")
        self.is_shutdown = True
        self.is_running = False
        self.release_all()

        # Ждём завершения рабочего потока (макс. 2 секунды)
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)

        print("  [БОТ] Работа завершена. До свидания!")

    def emergency_stop(self) -> None:
        """
        Экстренная остановка бота.

        Немедленно отпускает все клавиши и мышь,
        останавливает бота.
        """
        print("\n  ⚠ ЭКСТРЕННАЯ ОСТАНОВКА!")
        self.is_running = False
        self.release_all()

    def get_status(self) -> str:
        """
        Возвращает текстовое описание текущего состояния бота.

        Возвращает:
            Строка со статусом
        """
        status = "РАБОТАЕТ" if self.is_running else "ОСТАНОВЛЕН"
        return (
            f"Статус: {status} | "
            f"Позиция: ({self.current_x:.1f}, {self.current_y:.1f}, {self.current_z:.1f}) | "
            f"Взгляд: Yaw={self.current_yaw:.1f}°, Pitch={self.current_pitch:.1f}°"
        )

    def __repr__(self) -> str:
        return (
            f"MinecraftBot("
            f"pos=({self.current_x:.1f}, {self.current_y:.1f}, {self.current_z:.1f}), "
            f"yaw={self.current_yaw:.1f}, pitch={self.current_pitch:.1f}, "
            f"running={self.is_running})"
        )
