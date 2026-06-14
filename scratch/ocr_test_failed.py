import cv2
import numpy as np
import pytesseract
import sys
import os
import re

# Set tesseract path
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

def try_ocr(img, name, psm=6):
    try:
        text = pytesseract.image_to_string(img, config=f'--psm {psm}')
        text_clean = re.sub(r'[-—–−]+', '-', text)
        ascii_text = text_clean.encode('ascii', errors='replace').decode('ascii')
        print(f"=== Method: {name} (psm={psm}) ===")
        print(ascii_text.strip())
        print("----------------------------------------\n")
    except Exception as e:
        print(f"Error in {name}: {e}")

def main():
    img_path = r'c:\Users\assest\PycharmProjects\mine\debug_failed_capture.png'
    if not os.path.exists(img_path):
        print(f"Error: {img_path} not found.")
        return

    img = cv2.imread(img_path)
    if img is None:
        print("Error: failed to load image.")
        return

    print(f"Original image size: {img.shape}")

    # Convert to grayscale first
    gray_orig = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    for scale in [2, 3, 4]:
        for interp_name, interp_val in [("NEAREST", cv2.INTER_NEAREST), ("CUBIC", cv2.INTER_CUBIC), ("LINEAR", cv2.INTER_LINEAR)]:
            gray_resized = cv2.resize(gray_orig, None, fx=scale, fy=scale, interpolation=interp_val)
            
            # Try simple thresholding
            _, thresh = cv2.threshold(gray_resized, 120, 255, cv2.THRESH_BINARY_INV)
            thresh_pad = cv2.copyMakeBorder(thresh, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=255)
            
            try_ocr(thresh_pad, f"Gray Thresh 120 | Scale {scale}x | {interp_name}")

            # Try white mask on resized color image
            img_resized = cv2.resize(img, None, fx=scale, fy=scale, interpolation=interp_val)
            lower_white = np.array([170, 170, 170], dtype=np.uint8)
            upper_white = np.array([255, 255, 255], dtype=np.uint8)
            mask = cv2.inRange(img_resized, lower_white, upper_white)
            thresh_white = cv2.bitwise_not(mask)
            thresh_white_pad = cv2.copyMakeBorder(thresh_white, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=255)
            
            try_ocr(thresh_white_pad, f"White Mask (lower=170) | Scale {scale}x | {interp_name}")

if __name__ == '__main__':
    main()
