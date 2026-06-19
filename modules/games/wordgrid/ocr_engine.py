import cv2
import pytesseract
import os
import gc

def extract_grid(image_path):
    try:
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Adaptive Thresholding handles both black/white themes
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        
        config = "--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        text = pytesseract.image_to_string(thresh, config=config)
        
        # Cleanup
        os.remove(image_path)
        gc.collect()
        
        mapping = {'5': 'S', '0': 'O', '1': 'I', '8': 'B'}
        matrix = []
        for line in text.splitlines():
            row = [mapping.get(c, c) for c in line.replace(" ", "") if c.isalpha() or c in mapping]
            if len(row) >= 5: # Grid rows are usually consistent
                matrix.append(row)
        return matrix
    except Exception as e:
        return None
