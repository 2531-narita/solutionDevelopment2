import json
import os
import datetime
import pandas as pd
import cv2

class DocumentProcessor:
    """ [役割] 指定された座標を画像として切り出し、OCRエンジンに渡して文字化する """
    
    def __init__(self, paths, img_proc, ocr_eng):
        self.paths = paths
        self.img_proc = img_proc
        self.ocr_eng = ocr_eng
        self.temp_data_list = []

    def run_extraction(self, pdf_path):
        # 1. PDFを画像(OpenCV形式)に変換
        image = self.img_proc.load_image_from_pdf(pdf_path)
        img_h, img_w = image.shape[:2]
        
        # 2. 基準点(アンカー)を探す。見つからなければ[0,0]
        rects = self.img_proc.find_rectangles(image)
        curr_anchor = self.img_proc.get_anchor_point(rects) if rects else [0, 0]

        # 3. 設定ファイル(JSON)の読み込み
        with open(self.paths["json"], "r", encoding="utf-8") as f:
            formats = json.load(f)
        
        if not formats:
            raise ValueError("formats.json が読み込めないか空です。")

        # 最初のフォーマットを適用
        matched = formats[0]
        base = matched["base_size"]
        
        # 4. 倍率とオフセットを計算
        # 座標がズレる最大要因なので、端数を考慮して計算
        scale_x = img_w / float(base["width"])
        scale_y = img_h / float(base["height"])
        
        off_x = curr_anchor[0] - (matched["anchor"][0] * scale_x)
        off_y = curr_anchor[1] - (matched["anchor"][1] * scale_y)
        
        res = {"ファイル名": os.path.basename(pdf_path)}

        for tag in matched["tags"]:
            # 画像上の切り抜き範囲を算出
            ax = int((tag["x"] * scale_x) + off_x)
            ay = int((tag["y"] * scale_y) + off_y)
            aw = int(tag["w"] * scale_x)
            ah = int(tag["h"] * scale_y)
            
            # 画像を切り抜く（範囲外エラー防止のため制限をかける）
            x_end = min(ax + aw, img_w)
            y_end = min(ay + ah, img_h)
            crop = image[max(0, ay):y_end, max(0, ax):x_end]
            
            # --- 【デバッグ】切り抜いた画像を保存 ---
            # 実行後、この画像を見て「文字が入っているか」確認してください
            debug_filename = f"debug_{tag['tag_name']}.png"
            cv2.imwrite(debug_filename, crop)
            # ------------------------------------

            # OCR実行
            val = self.ocr_eng.extract_from_image(crop)
            
            print(f"      - {tag['tag_name']}: {val}")
            res[tag["tag_name"]] = val

        self.temp_data_list.append(res)
        return matched["format_name"]

    def create_excel(self):
        if not self.temp_data_list: return None
        now = datetime.datetime.now().strftime("%m%d_%H%M")
        path = os.path.join(self.paths["output"], f"Extraction_{now}.xlsx")
        pd.DataFrame(self.temp_data_list).to_excel(path, index=False)
        return path