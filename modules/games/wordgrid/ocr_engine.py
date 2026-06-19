import cv2
import pytesseract
import os
import gc

def extract_grid(image_path):
    try:
        img = cv2.imread(image_path)
        if img is None: return None
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Blur thoda kam karo agar letters chote hain
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        
        # PSM 6 is for a uniform block of text. Try PSM 11/12 agar grid mein letters door-door hain.
        config = "--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        text = pytesseract.image_to_string(thresh, config=config)
        
        # Debugging: Saved messages mein raw text bhejne ke liye yaha print karo
        # print(f"DEBUG OCR RAW: {text}") 
        
        mapping = {'5': 'S', '0': 'O', '1': 'I', '8': 'B'}
        matrix = []
        for line in text.splitlines():
            row = [mapping.get(c, c) for c in line.replace(" ", "") if c.isalpha() or c in mapping]
            if len(row) >= 3: # Min 3 letters in a row to consider it a grid line
                matrix.append(row)
        
        return matrix
    except Exception as e:
        # Error log karo
        return None
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)
            gc.collect()
