# ===========================================================================
# screen_reader.py — Распознавание координат из F3 меню через OCR
# ===========================================================================

import mss
import cv2
import numpy as np
import pytesseract
import re
import math
import ctypes
from ctypes import wintypes
from config import TESSERACT_PATH

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


def find_minecraft_window() -> tuple[int, int, int, int] | None:
    """
    Находит координаты (left, top, right, bottom) активного окна Minecraft.
    Ищет любое видимое окно Minecraft, отфильтровывая ложные совпадения (браузеры, IDE и др.).
    """
    hwnd = find_minecraft_hwnd()
    if hwnd:
        rect = wintypes.RECT()
        if ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return (rect.left, rect.top, rect.right, rect.bottom)
    return None


def find_minecraft_hwnd() -> int | None:
    """
    Находит дескриптор (HWND) активного окна Minecraft.
    Сначала проверяет текущее активное (foreground) окно. Если оно содержит "minecraft",
    возвращает его немедленно. Это предотвращает чтение из фоновых окон (например, IDE/браузера).
    """
    GetForegroundWindow = ctypes.windll.user32.GetForegroundWindow
    GetWindowText = ctypes.windll.user32.GetWindowTextW
    GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
    IsWindowVisible = ctypes.windll.user32.IsWindowVisible

    # 1. Проверяем текущее активное окно на переднем плане
    fg_hwnd = GetForegroundWindow()
    if fg_hwnd and IsWindowVisible(fg_hwnd):
        length = GetWindowTextLength(fg_hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            GetWindowText(fg_hwnd, buff, length + 1)
            title_lower = buff.value.lower()
            
            is_mc = ("minecraft" in title_lower or 
                     "laby" in title_lower or 
                     "lunar" in title_lower or 
                     "badlion" in title_lower or 
                     "tlauncher" in title_lower or 
                     "forge" in title_lower or 
                     "fabric" in title_lower)
            
            is_ignored = any(x in title_lower for x in [
                "chrome", "firefox", "opera", "yandex", "edge", "browser", "discord",
                "visual studio", "vscode", "pycharm", "idea", "antigravity", "google"
            ])
            
            if is_mc and not is_ignored:
                return fg_hwnd

    # 2. Если активное окно не MC, ищем среди остальных
    EnumWindows = ctypes.windll.user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    found_hwnd = [None]

    def foreach_window(hwnd, lParam):
        if IsWindowVisible(hwnd):
            length = GetWindowTextLength(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                GetWindowText(hwnd, buff, length + 1)
                title = buff.value
                title_lower = title.lower()
                is_mc = ("minecraft" in title_lower or 
                         "laby" in title_lower or 
                         "lunar" in title_lower or 
                         "badlion" in title_lower or 
                         "tlauncher" in title_lower or 
                         "forge" in title_lower or 
                         "fabric" in title_lower)
                is_ignored = any(x in title_lower for x in [
                    "chrome", "firefox", "opera", "yandex", "edge", "browser", "discord",
                    "visual studio", "vscode", "pycharm", "idea", "antigravity", "google"
                ])
                if is_mc and not is_ignored:
                    found_hwnd[0] = hwnd
                    return False
        return True

    EnumWindows(EnumWindowsProc(foreach_window), 0)
    return found_hwnd[0]


def get_game_offsets(coords: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    """
    Вычисляет реальное положение игрового холста на экране,
    компенсируя рамки и заголовок окна Windows.
    Возвращает (origin_x, origin_y, width, height).
    """
    left, top, right, bottom = coords
    width = right - left
    height = bottom - top

    # Полноэкранный режим
    if left == 0 and top == 0:
        return 0, 0, width, height
    
    # Для оконного и максимизированного режима в Windows 10/11 рамки (drop shadow) 
    # занимают 7-8 пикселей, а заголовок около 31 пикселя.
    # Если окно максимизировано, left обычно равно -8, тогда left + 8 = 0 (истинный левый край).
    return left + 8, top + 31, width - 16, height - 39


METHOD_DESCRIPTIONS = [
    "Scale 3x CUBIC + Gray Thresh 120",
    "Scale 2x LINEAR + Gray Thresh 120",
    "Scale 4x CUBIC + Gray Thresh 120",
    "Scale 3x NEAREST + White Mask 170",
    "Scale 1x + Gray Thresh 120",
    "Scale 3x NEAREST + Gray Thresh 120"
]


class ScreenReader:
    """
    Класс для захвата экрана и распознавания текста (координат и чата).
    """
    def __init__(self):
        self.sct = mss.mss()
        self.cached_hwnd = None
        self.successful_method_idx = 0

    def get_window_coords(self) -> tuple[int, int, int, int] | None:
        """
        Получает координаты окна Minecraft с использованием кэшированного HWND.
        """
        if self.cached_hwnd is None or not ctypes.windll.user32.IsWindow(self.cached_hwnd):
            self.cached_hwnd = find_minecraft_hwnd()
            if self.cached_hwnd is None:
                return None
                
        rect = wintypes.RECT()
        if ctypes.windll.user32.GetWindowRect(self.cached_hwnd, ctypes.byref(rect)):
            return (rect.left, rect.top, rect.right, rect.bottom)
        return None

    def capture_relative_region(self, rel_x: int, rel_y: int, w: int, h: int) -> np.ndarray | None:
        """
        Захватывает регион относительно игрового окна.
        """
        coords = self.get_window_coords()
        if not coords:
            return None
            
        origin_x, origin_y, _, _ = get_game_offsets(coords)
        
        monitor = {
            "top": origin_y + rel_y,
            "left": origin_x + rel_x,
            "width": w,
            "height": h
        }
        try:
            img = np.array(self.sct.grab(monitor))
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        except Exception:
            return None

    def preprocess_image(self, img: np.ndarray, method_idx: int) -> np.ndarray:
        """
        Применяет один из способов предобработки изображения перед OCR.
        """
        if method_idx == 0:
            # Scale 3x CUBIC, Gray Thresh 120
            img_resized = cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
            gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY_INV)
            return cv2.copyMakeBorder(thresh, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=255)
            
        elif method_idx == 1:
            # Scale 2x LINEAR, Gray Thresh 120
            img_resized = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
            gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY_INV)
            return cv2.copyMakeBorder(thresh, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=255)
            
        elif method_idx == 2:
            # Scale 4x CUBIC, Gray Thresh 120
            img_resized = cv2.resize(img, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
            gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY_INV)
            return cv2.copyMakeBorder(thresh, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=255)

        elif method_idx == 3:
            # Scale 3x NEAREST, White Mask (lower=170)
            img_resized = cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
            lower_white = np.array([170, 170, 170], dtype=np.uint8)
            upper_white = np.array([255, 255, 255], dtype=np.uint8)
            mask = cv2.inRange(img_resized, lower_white, upper_white)
            thresh = cv2.bitwise_not(mask)
            return cv2.copyMakeBorder(thresh, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=255)

        elif method_idx == 4:
            # Scale 1x, Gray Thresh 120
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY_INV)
            return cv2.copyMakeBorder(thresh, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=255)

        elif method_idx == 5:
            # Scale 3x NEAREST, Gray Thresh 120
            img_resized = cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
            gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY_INV)
            return cv2.copyMakeBorder(thresh, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=255)

        else:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            return gray

    def _parse_coords(self, text: str) -> tuple[float, float, float] | None:
        """
        Парсит координаты X Y Z из OCR текста.
        """
        text_clean = re.sub(r'[-—–−]+', '-', text)
        
        # 1. Сначала ищем строку с ключевым словом блока
        block_keywords = ["block", "lock", "ock", "black", "tock", "bisck", "блок", "6лок"]
        for line in text_clean.splitlines():
            line_lower = line.lower()
            found_kw = None
            for kw in block_keywords:
                if kw in line_lower:
                    found_kw = kw
                    break
            if found_kw:
                pos = line_lower.find(found_kw)
                sub = line[pos + len(found_kw):]
                clean_sub = sub.replace('&', '8').replace('O', '0').replace('o', '0')
                clean_sub = clean_sub.replace('I', '1').replace('l', '1').replace('i', '1').replace('S', '5')
                
                matches = re.findall(r'-?\d+', clean_sub)
                if len(matches) >= 3:
                    try:
                        return (float(matches[0]), float(matches[1]), float(matches[2]))
                    except ValueError:
                        pass
                        
        # 2. Если Block: не найден, пробуем найти XYZ: как запасной вариант
        for line in text_clean.splitlines():
            line_lower = line.lower()
            if "xyz" in line_lower or "x y z" in line_lower:
                pos = line_lower.find("xyz") if "xyz" in line_lower else line_lower.find("x y z")
                trigger_len = 3 if "xyz" in line_lower else 5
                sub = line[pos + trigger_len:]
                clean_sub = sub.replace(',', '.').replace('O', '0').replace('o', '0').replace('I', '1').replace('l', '1').replace('i', '1')
                matches = re.findall(r'-?\d+(?:\.\d+)?', clean_sub)
                if len(matches) >= 3:
                    try:
                        bx = math.floor(float(matches[0]))
                        by = math.floor(float(matches[1]))
                        bz = math.floor(float(matches[2]))
                        return (float(bx), float(by), float(bz))
                    except ValueError:
                        pass
        return None

    def _parse_angles(self, text: str) -> tuple[float, float] | None:
        """
        Парсит углы Yaw / Pitch из OCR текста.
        """
        text_clean = re.sub(r'[-—–−]+', '-', text)
        for line in text_clean.splitlines():
            if "facing:" in line.lower() or "facing" in line.lower():
                clean_line = line.replace(',', '.')
                matches = re.findall(r'(-?\d+(?:\.\d+)?)\s*[\/\\|]\s*(-?\d+(?:\.\d+)?)', clean_line)
                if matches:
                    try:
                        yaw = float(matches[-1][0])
                        pitch = float(matches[-1][1])
                        return yaw, pitch
                    except ValueError:
                        pass
        return None

    def _ocr_with_fallback(self, img: np.ndarray, parse_fn) -> tuple | None:
        """
        Выполняет OCR с автовыбором наиболее подходящего метода бинаризации.
        Сначала пробует последний успешный метод, затем остальные по очереди.
        """
        # Сначала пробуем последний успешный метод
        thresh = self.preprocess_image(img, self.successful_method_idx)
        text = pytesseract.image_to_string(thresh, config='--psm 6')
        result = parse_fn(text)
        if result is not None:
            return result

        # Если не получилось, перебираем все методы
        for idx in range(len(METHOD_DESCRIPTIONS)):
            if idx == self.successful_method_idx:
                continue
            try:
                thresh = self.preprocess_image(img, idx)
                text = pytesseract.image_to_string(thresh, config='--psm 6')
                result = parse_fn(text)
                if result is not None:
                    self.successful_method_idx = idx
                    print(f"  [ScreenReader] Метод OCR автоматически переключен на: {METHOD_DESCRIPTIONS[idx]}")
                    return result
            except Exception:
                pass

        return None

    def get_player_coords(self) -> tuple[float, float, float] | None:
        """
        Сканирует левый верхний угол игрового окна, распознает целые координаты Block XYZ.
        """
        try:
            # Захватываем область пошире и повыше (900x400), чтобы не обрезать на высоких GUI Scale
            img = self.capture_relative_region(0, 0, 900, 400)
            if img is None:
                coords = self.get_window_coords()
                if not coords:
                    print("  [ScreenReader DEBUG] Окно Minecraft не найдено! Проверьте, запущена ли игра.")
                else:
                    print(f"  [ScreenReader DEBUG] Окно найдено {coords}, но не удалось сделать скриншот холста.")
                return None

            res = self._ocr_with_fallback(img, self._parse_coords)
            if res is not None:
                return res

            # Если мы дошли досюда, значит не удалось распознать блок-координаты
            coords = self.get_window_coords()
            print("  [ScreenReader DEBUG] Ошибка парсинга блок-координат из скриншота.")
            if coords:
                print(f"  [ScreenReader DEBUG] Координаты окна игры: {coords}")
                cv2.imwrite("debug_failed_capture.png", img)
                thresh = self.preprocess_image(img, self.successful_method_idx)
                cv2.imwrite("debug_failed_thresh.png", thresh)
                
                try:
                    text = pytesseract.image_to_string(thresh, config='--psm 6')
                    safe_text = text.encode('utf-8', errors='replace').decode('utf-8')
                    print(f"  [ScreenReader DEBUG] Распознанный текст:\n{safe_text}")
                except Exception:
                    pass
                print(f"  [ScreenReader DEBUG] Скриншоты сохранены в debug_failed_capture.png и debug_failed_thresh.png")
        except Exception as e:
            print(f"  [ScreenReader] Ошибка OCR координат: {e}")
            
        return None

    def get_camera_angles(self) -> tuple[float, float] | None:
        """
        Распознает углы поворота камеры Yaw и Pitch из экрана F3.
        """
        try:
            img = self.capture_relative_region(0, 0, 900, 400)
            if img is None:
                return None
            return self._ocr_with_fallback(img, self._parse_angles)
        except Exception as e:
            print(f"  [ScreenReader] Ошибка OCR углов камеры: {e}")
        return None
