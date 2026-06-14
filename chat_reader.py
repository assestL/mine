# ===========================================================================
# chat_reader.py — Чтение чата для отслеживания перезапуска шахты
# ===========================================================================

import mss
import cv2
import numpy as np
import pytesseract
from config import TESSERACT_PATH

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


class ChatReader:
    """
    Класс для захвата чата и поиска сообщений об обновлении шахты.
    """
    def __init__(self):
        self.sct = mss.mss()

    def read_chat(self) -> str:
        """
        Захватывает чат относительно размеров окна игры, обрабатывает и возвращает текст.
        """
        try:
            from screen_reader import find_minecraft_window, get_game_offsets
            coords = find_minecraft_window()
            if not coords:
                return ""

            origin_x, origin_y, _, height = get_game_offsets(coords)
            
            # Чат в Minecraft находится в левом нижнем углу холста игры.
            # Копируем полосу шириной 550px и высотой 220px у самого низа
            rel_x = 10
            rel_y = max(0, height - 230)

            monitor = {
                "top": origin_y + rel_y,
                "left": origin_x + rel_x,
                "width": 550,
                "height": 200
            }

            img = np.array(self.sct.grab(monitor))
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

            # Масштабируем x3 для улучшения распознавания OCR
            img_resized = cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
            gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
            
            # Пороговый фильтр для выявления светлого текста чата
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

            text = pytesseract.image_to_string(thresh, config='--psm 6')
            return text
        except Exception as e:
            print(f"  [ChatReader] Ошибка OCR чата: {e}")
            return ""

    def is_mine_refreshed(self) -> bool:
        """
        Проверяет, появилось ли в чате сообщение о ресете шахты.
        """
        chat_text = self.read_chat().lower()
        
        # Ключевые фразы для разных серверов
        keywords = [
            "mine reset", 
            "mine refresh", 
            "шахта обновлена", 
            "шахта обновилась", 
            "mine has been reset", 
            "обновление шахты"
        ]
        
        return any(kw in chat_text for kw in keywords)
