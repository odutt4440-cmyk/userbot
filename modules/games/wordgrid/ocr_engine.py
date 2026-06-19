import cv2, pytesseract, os, gc

def extract_grid(image_path):
    try:
        if not os.path.exists(image_path): return None
        img = cv2.imread(image_path)
        if img is None: return None
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Adaptive Thresholding (Best for different background brightness)
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        
        # PSM 6 is good for blocks, PSM 13 for raw characters. 
        # Using 6 with strict character whitelist.
        config = "--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        text = pytesseract.image_to_string(thresh, config=config)
        
        # Strict mapping (only keep letters)
        mapping = {
            '5':'S', '0':'O', '1':'I', '8':'B', 'Q':'O', 'Z':'Z', 
            '2':'Z', 'S':'S', 'B':'B', 'D':'D'
        }
        
        matrix = []
        for line in text.splitlines():
            # Sirf letters rakho, numbers hata do
            row = [mapping.get(c, c) for c in line.replace(" ", "") if c.isalpha()]
            # Grid size check (kam se kam 5x5)
            if len(row) >= 5: 
                matrix.append(row)
        
        return matrix if len(matrix) >= 5 else None
    except Exception:
        return None
    finally:
        if os.path.exists(image_path): os.remove(image_path)
        gc.collect()
