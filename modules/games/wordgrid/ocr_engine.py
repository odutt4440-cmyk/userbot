import cv2, pytesseract, os, gc

def extract_grid(image_path):
    try:
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        
        config = "--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        text = pytesseract.image_to_string(thresh, config=config)
        
        mapping = {'5': 'S', '0': 'O', '1': 'I', '8': 'B', 'Q': 'O'} # OCR fixes
        matrix = []
        for line in text.splitlines():
            row = [mapping.get(c, c) for c in line.replace(" ", "") if c.isalpha() or c in mapping]
            if len(row) >= 5: matrix.append(row)
        return matrix
    except: return None
    finally:
        if os.path.exists(image_path): os.remove(image_path)
        gc.collect()
