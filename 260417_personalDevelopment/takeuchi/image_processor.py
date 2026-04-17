import cv2
import numpy as np
import pdfplumber

class ImageProcessor:
    """
    [役割] PDFの画像変換、枠線の抽出、および画像のクロップ(切り抜き)処理
    """
    def load_image_from_pdf(self, path):
        """ [役割] どんなPDFでも解像度200DPIで均一に画像化する """
        with pdfplumber.open(path) as pdf:
            page_image = pdf.pages[0].to_image(resolution=200)
            img_array = np.array(page_image.original.convert('RGB'))
            return cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

    def find_rectangles(self, img):
        """ [役割] 画像内の四角形（枠線）をすべて探し出す """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 50, 150)
        
        cnts, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        rects = []
        for c in cnts:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            if len(approx) == 4: 
                rects.append(cv2.boundingRect(approx))
        return rects

    def get_anchor_point(self, rects):
        """ [役割] 検出した枠線の中で、一番「左上」にあるものを基準点(アンカー)とする """
        if not rects: return [0, 0]
        anchor = min(rects, key=lambda r: r[0] + r[1])
        return [anchor[0], anchor[1]]

    def crop_image(self, img, rect):
        """ [役割] 指定された座標に基づいて画像を切り抜く """
        x, y, w, h = rect
        # 画像の範囲外に出ないように安全対策
        img_h, img_w = img.shape[:2]
        y1, y2 = max(0, y), min(img_h, y + h)
        x1, x2 = max(0, x), min(img_w, x + w)
        return img[y1:y2, x1:x2]