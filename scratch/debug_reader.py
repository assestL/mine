import cv2
import sys
import os
import re

sys.path.append(os.path.abspath('.'))

from screen_reader import ScreenReader

def main():
    img = cv2.imread('debug_failed_capture.png')
    reader = ScreenReader()
    
    for idx in range(6):
        thresh = reader.preprocess_image(img, idx)
        import pytesseract
        text = pytesseract.image_to_string(thresh, config='--psm 6')
        
        text_clean = re.sub(r'[-—–−]+', '-', text)
        print(f"\n================ Method {idx}: ==================")
        
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
                clean_sub = clean_sub.replace('I', '1').replace('l', '1').replace('S', '5')
                matches = re.findall(r'-?\d+', clean_sub)
                
                print(f"Original Line: {repr(line)}")
                print(f"Sub:           {repr(sub)}")
                print(f"Cleaned Sub:   {repr(clean_sub)}")
                print(f"Matches:       {matches}")

if __name__ == '__main__':
    main()
