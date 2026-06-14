import cv2
import sys
import os

sys.path.append(os.path.abspath('.'))

from screen_reader import ScreenReader

def main():
    img_path = 'debug_failed_capture.png'
    if not os.path.exists(img_path):
        print(f"Error: {img_path} not found.")
        return

    print(f"Loading '{img_path}' for offline OCR test...")
    img = cv2.imread(img_path)
    
    reader = ScreenReader()
    # Mock capture_relative_region to return our failed capture image
    reader.capture_relative_region = lambda *args, **kwargs: img

    print("Running get_player_coords()...")
    coords = reader.get_player_coords()
    
    print("Running get_camera_angles()...")
    angles = reader.get_camera_angles()

    print("\n================ TEST RESULTS ================")
    print(f"Parsed coordinates: {coords} (Expected: (17.0, 149.0, 12.0))")
    print(f"Parsed angles:      {angles} (Expected: (177.3, 27.0))")
    print(f"Selected preprocessing index: {reader.successful_method_idx}")
    print("==============================================")

    if coords == (17.0, 149.0, 12.0) and angles is not None and abs(angles[0] - 177.3) < 0.1 and abs(angles[1] - 27.0) < 0.1:
        print("\n[SUCCESS] Both coordinates and camera angles were parsed 100% correctly!")
        sys.exit(0)
    else:
        print("\n[FAILURE] OCR results do not match expected coordinates or camera angles.")
        sys.exit(1)

if __name__ == '__main__':
    main()
