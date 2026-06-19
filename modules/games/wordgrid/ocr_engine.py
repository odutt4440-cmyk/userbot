import cv2, pytesseract, os, gc

def extract_grid(image_path):
    try:
        # Check if file exists
        if not os.path.exists(image_path): return None
        
        img = cv2.imread(image_path)
        if img is None: return None
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Binarization for better OCR
        _, thresh = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        
        config = "--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        text = pytesseract.image_to_string(thresh, config=config)
        
        mapping = {'5':'S', '0':'O', '1':'I', '8':'B', 'Q':'O', 'Z':'2', 'A':'A', 'D':'D', 'B':'B', 'S':'S', 'G':'G', 'I':'I', 'L':'L', 'T':'T'}
        matrix = []
        for line in text.splitlines():
            row = [mapping.get(c, c) for c in line.replace(" ", "") if c.isalpha() or c in mapping]
            if len(row) >= 5: matrix.append(row)
        return matrix if matrix else None
    except Exception: return None
    finally:
        if os.path.exists(image_path): os.remove(image_path)
        gc.collect()
