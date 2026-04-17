import pytesseract
import cv2
import numpy as np
import os

tesseract_exe_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
if os.path.exists(tesseract_exe_path):
    pytesseract.pytesseract.tesseract_cmd = tesseract_exe_path

class OCREngine:
    def is_text_based(self, path): return False

    def extract_from_image(self, img):
        if img is None or img.size == 0: return ""
        
        # 1. 枠線対策：画像の縁（上下左右）を3ピクセルずつ削る
        # これで、多少座標がズレて枠線が入っても強制的に消去します
        h, w = img.shape[:2]
        if h > 10 and w > 10:
            img = img[3:h-3, 3:w-3]

        # 2. 前処理
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        
        # 3. ノイズ除去（白黒をハッキリさせて細いカスレを埋める）
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        
        # 4. OCR実行
        # --psm 7 は「1行のテキスト」として読む設定
        custom_config = r'--oem 3 --psm 7 -l jpn+eng'
        text = pytesseract.image_to_string(thresh, config=custom_config)
        
        # 「ー」や「_」など、罫線の残骸が化けやすい記号を徹底的に掃除
        clean_text = text.replace("\n", "").replace("|", "").replace("_", "").replace(" ", "")
        return clean_text.strip()