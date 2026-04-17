import cv2
import pytesseract
import numpy as np

def process_image_and_ocr(image_path, regions, display_w, display_h):
    img = cv2.imread(image_path)
    if img is None:
        return []
        
    orig_h, orig_w = img.shape[:2]
    
    # Scale factors (UI map size to Actual Image size)
    scale_w = orig_w / float(display_w)
    scale_h = orig_h / float(display_h)

    results = []
    
    for region in regions:
        # Scale UI coordinates back to original image coordinates
        x = int(region['x'] * scale_w)
        y = int(region['y'] * scale_h)
        w = int(region['w'] * scale_w)
        h = int(region['h'] * scale_h)
        tag = region.get('tag', 'Unknown')
        
        # Ensure boundaries
        x = max(0, x)
        y = max(0, y)
        w = min(orig_w - x, w)
        h = min(orig_h - y, h)
        
        cropped = img[y:y+h, x:x+w]
        
        if cropped.size == 0:
            results.append({
                "tag": tag,
                "text": "Crop Error: Out of bounds."
            })
            continue
            
        # Preprocessing for better OCR
        # Convert to grayscale
        gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
        
        # Thresholding
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        
        try:
             # Try JPN + ENG first
             text = pytesseract.image_to_string(thresh, lang='jpn+eng', config='--psm 6')
             text = text.strip()
        except pytesseract.TesseractError as e:
             try:
                 # Fallback to default
                 text = pytesseract.image_to_string(thresh, config='--psm 6')
                 text = text.strip()
             except Exception as inner_e:
                 text = "OCR Error. See console."
        except Exception as e:
             if 'tesseract is not installed or it\'s not in your PATH' in str(e):
                 text = "Error: Tesseract is not installed or not in PATH."
             else:
                 text = f"OCR Error: {str(e)}"
                 
        results.append({
            "tag": tag,
            "text": text
        })
        
    return results
