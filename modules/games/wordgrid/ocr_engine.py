import cv2, pytesseract, os, gc

def extract_grid(image_path):
    try:
        if not os.path.exists(image_path): return None
        img = cv2.imread(image_path)
        if img is None: return None
        
        # 1. Grayscale & Noise removal
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # 2. Adaptive thresholding for clean binary image
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
        
        # 3. Grid lines ko remove karne ke liye dilate/erode (Noise removal)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        
        # 4. Invert wapas (Letters white, background black)
        thresh = cv2.bitwise_not(thresh)
        
        config = "--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        text = pytesseract.image_to_string(thresh, config=config)
        
        # Letters ko clean karna
        mapping = {'5':'S', '0':'O', '1':'I', '8':'B', 'Q':'O', 'Z':'Z', '2':'Z'}
        matrix = []
        for line in text.splitlines():
            row = [mapping.get(c, c) for c in line.replace(" ", "") if c.isalpha()]
            if len(row) >= 5: matrix.append(row)
            
        return matrix if len(matrix) >= 5 else None
    except Exception: return None
    finally:
        if os.path.exists(image_path): os.remove(image_path)
        gc.collect()
