# ===========================================================================
# main.py — Основной управляющий поток и запуск бота
# ===========================================================================

import threading
import time
import sys
import math
import random
import winsound
import keyboard as global_keyboard

import input_sim
from config import HOTKEY_Q, TELEPORT_COMMAND, random_delay
from screen_reader import ScreenReader
from chat_reader import ChatReader
from camera import CameraEngine
from movement import MovementEngine
from mine_planner import MinePlanner
from miner import Miner

# ─── Глобальное состояние бота ───────────────────────────────────────────
running = False
mined_blocks = set()
refresh_count = 0
shutdown_requested = False


def toggle_bot() -> None:
    """Переключает статус работы бота."""
    global running
    if shutdown_requested:
        return

    running = not running
    status = "▶ ЗАПУЩЕН" if running else "⏸ ОСТАНОВЛЕН (Пауза)"
    print(f"\n  [СИСТЕМА] Бот: {status}")
    
    if running:
        winsound.Beep(1000, 150)
        winsound.Beep(1200, 200)
    else:
        winsound.Beep(600, 250)


def auto_teleport() -> None:
    """Симулирует ввод команды телепортации наверх шахты."""
    if not TELEPORT_COMMAND:
        return

    print(f"  [BOT] Отправляем команду телепортации: {TELEPORT_COMMAND}")
    
    # Открываем чат клавишей 't'
    input_sim.press_key('t')
    time.sleep(0.25)
    input_sim.release_key('t')
    time.sleep(0.4)

    # Печатаем команду скан-кодами
    input_sim.type_string(TELEPORT_COMMAND)

    time.sleep(0.35)
    # Нажимаем Enter для отправки
    input_sim.press_key('enter')
    time.sleep(0.12)
    input_sim.release_key('enter')
    time.sleep(1.5)


def wait_for_mine_refresh(reader: ScreenReader, chat_reader: ChatReader, timeout: float = 300.0) -> None:
    """Ожидает обновления шахты, анализируя чат в игре."""
    print("  [BOT] Шахта полностью выработана! Ожидаем регенерации блоков...")
    
    start_time = time.time()
    check_interval = 2.0
    
    while time.time() - start_time < timeout:
        if shutdown_requested:
            return
            
        if not running:
            time.sleep(0.2)
            continue

        # Проверяем появление ключевых фраз в чате
        if chat_reader.is_mine_refreshed():
            print("  [BOT] Чат: Обнаружен перезапуск шахты!")
            break

        time.sleep(check_interval)

    # Выполняем авто-телепортацию наверх шахты
    if TELEPORT_COMMAND:
        auto_teleport()
    else:
        print("  [BOT] Авто-телепортация отключена. Поднимитесь наверх шахты вручную.")
        print("        Даем 5 секунд на подготовку...")
        time.sleep(5.0)

    # Пауза для прогрузки блоков сервером
    time.sleep(2.5)


def bot_loop(x1: float, y1: float, z1: float, x2: float, y2: float, z2: float) -> None:
    """Главный рабочий цикл бота."""
    global running, mined_blocks, refresh_count, shutdown_requested

    reader = ScreenReader()
    chat_reader = ChatReader()
    camera = CameraEngine()
    movement = MovementEngine()
    planner = MinePlanner(x1, y1, z1, x2, y2, z2)
    miner = Miner()

    # Вычисляем общее количество блоков в шахте
    total_blocks = (
        (planner.x_max - planner.x_min + 1) *
        (planner.y_max - planner.y_min + 1) *
        (planner.z_max - planner.z_min + 1)
    )

    print(f"  [BOT] Область шахты: X({planner.x_min}..{planner.x_max}), Y({planner.y_min}..{planner.y_max}), Z({planner.z_min}..{planner.z_max})")
    print(f"  [BOT] Всего блоков в шахте: {total_blocks}")

    last_running = False
    last_valid_pos = None
    last_valid_time = None
    last_warning_time = 0.0

    while not shutdown_requested:
        if not running:
            last_running = False
            time.sleep(0.1)
            continue

        if not last_running:
            # Бот только что запущен или снят с паузы
            print("  [СИСТЕМА] Калибровка направления камеры...")
            calibrated = False
            for _ in range(5):
                angles = reader.get_camera_angles()
                if angles is not None:
                    yaw, pitch = angles
                    camera.calibrate(yaw, pitch)
                    print(f"  [СИСТЕМА] Камера успешно откалибрована: Yaw={yaw:.1f}, Pitch={pitch:.1f}")
                    calibrated = True
                    break
                time.sleep(0.3)
            if not calibrated:
                print("  [WARN] Не удалось автоматически настроить камеру. Бот будет использовать сохраненные углы.")
            last_running = True

        # Условие: если выкопали всю шахту — ждем обновления
        if len(mined_blocks) >= total_blocks:
            print(f"  [BOT] Успешно завершен круг #{refresh_count + 1}!")
            mined_blocks.clear()
            refresh_count += 1
            wait_for_mine_refresh(reader, chat_reader)
            last_valid_pos = None
            last_valid_time = None
            continue

        # Читаем реальные координаты из игры через OCR
        player_pos = reader.get_player_coords()
        if player_pos is None:
            print("  [WARN] Не удалось прочитать F3 координаты! Проверьте, открыт ли F3-экран.")
            time.sleep(1.0)
            continue

        # Валидация координат (фильтрация шума OCR)
        px, py, pz = player_pos
        current_time = time.time()
        y_valid = (planner.y_min - 5 <= py <= planner.y_max + 10)
        jump_valid = True
        
        if last_valid_pos is not None and last_valid_time is not None:
            dt = current_time - last_valid_time
            max_dist = max(5.0, 15.0 * dt)
            dist = math.sqrt(
                (px - last_valid_pos[0])**2 +
                (py - last_valid_pos[1])**2 +
                (pz - last_valid_pos[2])**2
            )
        
        # Обработка резких скачков (респавн шахты или падение)
        if last_valid_pos:
            if py - last_valid_pos[1] > 5:
                print(f"  [СИСТЕМА] Обнаружен респавн шахты (скачок Y: {last_valid_pos[1]} -> {py}). Сбрасываем прогресс!")
                mined_blocks.clear()
            elif abs(px - last_valid_pos[0]) > 20 or abs(pz - last_valid_pos[2]) > 20:
                print(f"  [СИСТЕМА] Считанные координаты {player_pos} отклонены (огромный скачок XZ)")
                last_warning_time = current_time
                time.sleep(0.1)
                continue

        last_valid_pos = player_pos
        last_valid_time = current_time

        print(f"  [STATUS] Персонаж на позиции: ({player_pos[0]:.2f}, {player_pos[1]:.2f}, {player_pos[2]:.2f})")

        # Находим блоки в радиусе досягаемости игрока
        blocks_nearby = planner.get_blocks_near(player_pos, mined_blocks)
        
        if blocks_nearby:
            # Выкапываем все блоки в радиусе досягаемости, удерживая ЛКМ (профессиональный быстрый зажим)
            miner.press_lmb()
            
            try:
                for block in blocks_nearby:
                    if shutdown_requested or not running:
                        break

                    # Наводим камеру на блок
                    camera.look_at_block(player_pos, block)
                    # Имитируем время на разрушение блока (0.5 сек)
                    time.sleep(random_delay(0.5, 0.05))
                    
                    mined_blocks.add(block)

                    # Выводим прогресс
                    progress = (len(mined_blocks) / total_blocks) * 100
                    print(f"    [ПРОГРЕСС] Выкопано {len(mined_blocks)}/{total_blocks} ({progress:.1f}%) | Блок: {block}")

                    # Антидетект: случайные паузы "усталости" раз в 35 блоков
                    if len(mined_blocks) % 35 == 0:
                        miner.release_lmb()  # Отпускаем ЛКМ перед отдыхом
                        break_duration = random.uniform(1.5, 3.5)
                        print(f"    [АНТИДЕТЕКТ] Имитируем паузу игрока на {break_duration:.2f}с...")
                        time.sleep(break_duration)
                        if running and not shutdown_requested:
                            miner.press_lmb()  # Снова зажимаем ЛКМ
            finally:
                miner.release_lmb()
                
            time.sleep(0.1)
            continue

        # Если в радиусе досягаемости нет блоков, ищем ближайший unmined блок
        closest_block = planner.get_closest_unmined_block(player_pos, mined_blocks)
        
        if closest_block:
            # Направляемся к вейпоинту (ближайшему блоку)
            print(f"  [ДВИЖЕНИЕ] Нет блоков в reach. Идем к ближайшему блоку: {closest_block}")
            
            # Поскольку к целевому блоку нужно подойти на reach distance, navigate_to_block остановится, как только приблизится
            movement.navigate_to_block(player_pos, closest_block, camera, reader)
            time.sleep(0.1)
        else:
            # Блоков не осталось, но len(mined_blocks) < total_blocks (возможно, какие-то пропустили, или шахта обновляется)
            print("  [BOT] В шахте не найдено доступных блоков для копания. Ожидаем ресета...")
            mined_blocks.clear()
            wait_for_mine_refresh(reader, chat_reader)


def main() -> None:
    """Точка входа программы."""
    global shutdown_requested

    print("=" * 60)
    print("        🤖 MINECRAFT PRISON BOT — РЕЖИМ ШАХТЫ")
    print("=" * 60)
    print("  Инструкция:")
    print("  1. Запустите Minecraft в оконном режиме.")
    print("  2. Встаньте в шахту, откройте меню F3 (экран координат).")
    print("  3. Введите координаты противоположных углов шахты.")
    print("  4. Нажмите Q/Й в игре для запуска и паузы бота.")
    print("  5. Для завершения нажмите Ctrl+C в этой консоли.")
    print("=" * 60)

    try:
        print("\n  📍 Угол 1 шахты:")
        x1 = float(input("     X1: "))
        y1 = float(input("     Y1: "))
        z1 = float(input("     Z1: "))

        print("\n  📍 Противоположный угол 2:")
        x2 = float(input("     X2: "))
        y2 = float(input("     Y2: "))
        z2 = float(input("     Z2: "))
    except ValueError:
        print("\n  [ОШИБКА] Координаты должны быть числами!")
        sys.exit(1)

    print(f"\n  [СИСТЕМА] Бот инициализирован для кубоида: ({x1}, {y1}, {z1}) ➔ ({x2}, {y2}, {z2})")
    print(f"  [СИСТЕМА] Нажмите [{HOTKEY_Q.upper()}] для запуска/паузы бота.")

    # Привязываем глобальный хоткей
    global_keyboard.add_hotkey(HOTKEY_Q, toggle_bot)

    # Запускаем основной поток бота
    bot_thread = threading.Thread(
        target=bot_loop,
        args=(x1, y1, z1, x2, y2, z2),
        daemon=True
    )
    bot_thread.start()

    # Ожидаем завершения
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n  [СИСТЕМА] Получен сигнал прерывания. Выключение...")
        shutdown_requested = True
        sys.exit(0)


if __name__ == "__main__":
    main()
