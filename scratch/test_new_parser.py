import cv2
import numpy as np
import pytesseract
import sys
import os
import re
import math

TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

def parse_coords_from_text(text):
    text_clean = re.sub(r'[-—–−]+', '-', text)
    
    # Try Block line first
    keywords = ["block", "lock", "ock", "black", "tock", "bisck", "блок", "6лок"]
    for line in text_clean.splitlines():
        line_lower = line.lower()
        found_kw = None
        for kw in keywords:
            if kw in line_lower:
                found_kw = kw
                break
        if found_kw:
            pos = line_lower.find(found_kw)
            sub = line[pos + len(found_kw):]
            clean_sub = sub.replace('&', '8').replace('O', '0').replace('o', '0')
            clean_sub = clean_sub.replace('I', '1').replace('l', '1').replace('S', '5')
            matches = re.findall(r'-?\d+', clean_sub)
            if len(matches) >= 3:
                try:
                    bx = float(matches[0])
                    by = float(matches[1])
                    bz = float(matches[2])
                    return (bx, by, bz), "Block Line"
                except ValueError:
                    pass

    # Try XYZ fallback line
    for line in text_clean.splitlines():
        line_lower = line.lower()
        if "xyz" in line_lower or "x y z" in line_lower:
            pos = line_lower.find("xyz") if "xyz" in line_lower else line_lower.find("x y z")
            # find length of matched trigger
            trigger_len = 3 if "xyz" in line_lower else 5
            sub = line[pos + trigger_len:]
            clean_sub = sub.replace(',', '.').replace('O', '0').replace('o', '0').replace('I', '1').replace('l', '1')
            matches = re.findall(r'-?\d+(?:\.\d+)?', clean_sub)
            if len(matches) >= 3:
                try:
                    bx = math.floor(float(matches[0]))
                    by = math.floor(float(matches[1]))
                    bz = math.floor(float(matches[2]))
                    return (float(bx), float(by), float(bz)), "XYZ Line"
                except ValueError:
                    pass
    return None, None

def test_on_image(img, name, psm=6):
    try:
        text = pytesseract.image_to_string(img, config=f'--psm {psm}')
        coords, source = parse_coords_from_text(text)
        if coords:
            print(f"SUCCESS: Method '{name}' -> parsed coords {coords} from {source}")
        else:
            print(f"FAILED: Method '{name}'")
    except Exception as e:
        print(f"ERROR: Method '{name}': {e}")

def main():
    img_path = r'c:\Users\assest\PycharmProjects\mine\debug_failed_capture.png'
    if not os.path.exists(img_path):
        print(f"Error: {img_path} not found.")
        return

    img = cv2.imread(img_path)
    if img is None:
        print("Error: failed to load image.")
        return

    gray_orig = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # We will test our candidate preprocessing methods
    # Method A: Scale 3x CUBIC Gray Thresh 120 (current code)
    gray_3x = cv2.resize(gray_orig, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    _, thresh_3x = cv2.threshold(gray_3x, 120, 255, cv2.THRESH_BINARY_INV)
    thresh_3x_pad = cv2.copyMakeBorder(thresh_3x, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=255)
    test_on_image(thresh_3x_pad, "Scale 3x CUBIC Gray Thresh 120 (current)")

    # Method B: Scale 4x CUBIC Gray Thresh 120
    gray_4x = cv2.resize(gray_orig, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    _, thresh_4x = cv2.threshold(gray_4x, 120, 255, cv2.THRESH_BINARY_INV)
    thresh_4x_pad = cv2.copyMakeBorder(thresh_4x, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=255)
    test_on_image(thresh_4x_pad, "Scale 4x CUBIC Gray Thresh 120")

    # Method C: Scale 2x LINEAR Gray Thresh 120
    gray_2x = cv2.resize(gray_orig, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
    _, thresh_2x = cv2.threshold(gray_2x, 120, 255, cv2.THRESH_BINARY_INV)
    thresh_2x_pad = cv2.copyMakeBorder(thresh_2x, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=255)
    test_on_image(thresh_2x_pad, "Scale 2x LINEAR Gray Thresh 120")

    # Method D: White mask 2x LINEAR (lower=170)
    img_2x = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
    lower_white = np.array([170, 170, 170], dtype=np.uint8)
    upper_white = np.array([255, 255, 255], dtype=np.uint8)
    mask_2x = cv2.inRange(img_2x, lower_white, upper_white)
    thresh_white_2x = cv2.bitwise_not(mask_2x)
    thresh_white_2x_pad = cv2.copyMakeBorder(thresh_white_2x, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=255)
    test_on_image(thresh_white_2x_pad, "White Mask 2x LINEAR (lower=170)")

    # Method E: White mask 3x NEAREST (lower=170)
    img_3x_nearest = cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
    mask_3x_nearest = cv2.inRange(img_3x_nearest, lower_white, upper_white)
    thresh_white_3x_nearest = cv2.bitwise_not(mask_3x_nearest)
    thresh_white_3x_nearest_pad = cv2.copyMakeBorder(thresh_white_3x_nearest, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=255)
    test_on_image(thresh_white_3x_nearest_pad, "White Mask 3x NEAREST (lower=170)")

if __name__ == '__main__':
    main()
