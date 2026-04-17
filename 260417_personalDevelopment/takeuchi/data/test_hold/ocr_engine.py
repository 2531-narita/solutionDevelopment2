import pdfplumber
import pytesseract
import cv2
import numpy as np
import os

# Tesseractの実行ファイルパス（インストール先に合わせて調整してください）
tesseract_exe_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
if os.path.exists(tesseract_exe_path):
    pytesseract.pytesseract.tesseract_cmd = tesseract_exe_path

class OCREngine:
    """
    [役割] 
    1. PDF内にテキストデータがあれば直接抜き出す（精度100%）。
    2. テキストがない、または抽出に失敗した場合は、画像処理を施してからOCRを実行する。
    """

    def is_text_based(self, path):
        """ [役割] PDF内部にデジタルテキストが保持されているか判定 """
        try:
            with pdfplumber.open(path) as pdf:
                # 1ページ目の全テキストを取得
                txt = pdf.pages[0].extract_text()
                # 1文字でもデジタルデータがあればTrueを返す
                return len(txt.strip()) > 0 if txt else False
        except:
            return False

    def extract_from_text_pdf(self, path, bbox):
        """ 
        [役割] デジタルテキスト抽出。
        指定範囲(bbox)を少し広げて文字を確実にキャッチする。
        """
        try:
            with pdfplumber.open(path) as pdf:
                page = pdf.pages[0]
                
                # 座標の遊び（パディング）。ズレ対策として上下左右に5ポイント広げる
                padding = 5
                safe_bbox = (
                    max(0, bbox[0] - padding),
                    max(0, bbox[1] - padding),
                    min(page.width, bbox[2] + padding),
                    min(page.height, bbox[3] + padding)
                )
                
                cropped = page.within_bbox(safe_bbox)
                text = cropped.extract_text()
                
                if text:
                    # 表の境界線などで拾いやすい不要な記号や改行を掃除
                    clean_text = text.replace("\n", "").replace("|", "").strip()
                    return clean_text if clean_text else None
                return None
        except:
            return None

    def extract_from_image(self, img):
        """ 
        [役割] 画像OCR。
        罫線を消去し、文字だけを浮き上がらせてからTesseractに渡す。
        """
        if img is None or img.size == 0:
            return ""
        
        # --- 画像前処理 ---
        # 1. グレースケール化と拡大（認識率向上）
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        
        # 2. 二値化（白黒反転：文字を白、背景を黒にする）
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

        # 3. 罫線除去（文字の棒より明らかに長い線だけを消す）
        # 横線の検出と除去
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (thresh.shape[1] // 2, 1))
        h_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, h_kernel)
        thresh = cv2.subtract(thresh, h_lines)
        
        # 縦線の検出と除去
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, thresh.shape[0] // 2))
        v_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, v_kernel)
        thresh = cv2.subtract(thresh, v_lines)

        # 4. 背景を白に戻す
        result_img = cv2.bitwise_not(thresh)

        # --- OCR実行 ---
        # lang='jpn+eng': 日本語と英語を両方認識
        # --psm 7: 1行のテキストとして処理（セル内の抽出に最適）
        custom_config = r'--oem 3 --psm 7 -l jpn+eng'
        text = pytesseract.image_to_string(result_img, config=custom_config)
        
        # 読み取り結果のクリーニング
        clean_text = text.replace("\n", "").replace("|", "").replace(" ", "").strip()
        return clean_text

    def is_valid_pdf(self, path):
        """ [役割] ファイルが正常なPDFかチェック """
        try:
            with pdfplumber.open(path) as pdf:
                return len(pdf.pages) > 0
        except:
            return False