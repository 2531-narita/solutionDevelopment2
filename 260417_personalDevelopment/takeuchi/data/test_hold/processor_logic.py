import json
import os
import datetime
import pandas as pd
import pdfplumber

class DocumentProcessor:
    """ [役割] デジタル抽出とOCR抽出を自動で使い分けるロジック統括 """
    def __init__(self, paths, img_proc, ocr_eng):
        self.paths = paths
        self.img_proc = img_proc
        self.ocr_eng = ocr_eng
        self.temp_data_list = []

    def run_extraction(self, pdf_path):
        image = self.img_proc.load_image_from_pdf(pdf_path)
        rects = self.img_proc.find_rectangles(image)
        curr_anchor = self.img_proc.get_anchor_point(rects) if rects else [0, 0]

        with open(self.paths["json"], "r", encoding="utf-8") as f:
            formats = json.load(f)
        
        if not formats:
            raise ValueError("formats.json が空です。")

        # アンカー判定（500px以内なら一致とみなすガバガバ判定）
        matched = None
        for fmt in formats:
            ref = fmt["anchor"]
            dist = ((curr_anchor[0]-ref[0])**2 + (curr_anchor[1]-ref[1])**2)**0.5
            if dist < 500:
                matched = fmt
                break
        
        if not matched:
            matched = formats[0]
            print(f"   [!] 形式特定不能のため、'{matched['format_name']}' を強制適用します。")

        # 倍率計算
        base = matched["base_size"]
        scale_x = image.shape[1] / base["width"]
        scale_y = image.shape[0] / base["height"]
        off_x = curr_anchor[0] - (matched["anchor"][0] * scale_x)
        off_y = curr_anchor[1] - (matched["anchor"][1] * scale_y)
        
        res = {"ファイル名": os.path.basename(pdf_path)}
        is_text_pdf = self.ocr_eng.is_text_based(pdf_path)

        with pdfplumber.open(pdf_path) as pdf:
            p = pdf.pages[0]
            pts_x, pts_y = p.width / image.shape[1], p.height / image.shape[0]

        for tag in matched["tags"]:
            # 画像上の座標
            ax = (tag["x"] * scale_x) + off_x
            ay = (tag["y"] * scale_y) + off_y
            aw, ah = tag["w"] * scale_x, tag["h"] * scale_y
            
            val = None

            # --- ステップ1: デジタルテキスト抽出を試みる ---
            if is_text_pdf:
                bbox = (ax * pts_x, ay * pts_y, (ax+aw) * pts_x, (ay+ah) * pts_y)
                val = self.ocr_eng.extract_from_text_pdf(pdf_path, bbox)
            
            # --- ステップ2: デジタル抽出が空、または画像PDFならOCR(画像認識)に切り替え ---
            if val is None or val.strip() == "":
                crop = self.img_proc.crop_image(image, (int(ax), int(ay), int(aw), int(ah)))
                val = self.ocr_eng.extract_from_image(crop)
            
            content = val.strip() if val else ""
            print(f"      - {tag['tag_name']}: {content[:20]}")
            res[tag["tag_name"]] = content

        self.temp_data_list.append(res)
        return matched["format_name"]

    def create_excel(self):
        if not self.temp_data_list: return None
        now = datetime.datetime.now().strftime("%m%d_%H%M")
        path = os.path.join(self.paths["output"], f"Extraction_{now}.xlsx")
        pd.DataFrame(self.temp_data_list).to_excel(path, index=False)
        return path