import json
import os
import datetime
import pandas as pd

class DocumentProcessor:
    """
    手動登録式
    [役割] 抽出ロジックの中核。メモにあるズレ補正とText/Image判定を統合。
    """
    def __init__(self, paths, img_proc, ocr_eng):
        self.paths = paths
        self.img_proc = img_proc
        self.ocr_eng = ocr_eng
        self.temp_data_list = []
        self._ensure_json()

    def _ensure_json(self):
        if not os.path.exists(self.paths["json"]) or os.path.getsize(self.paths["json"]) == 0:
            with open(self.paths["json"], "w", encoding="utf-8") as f: json.dump([], f)

    def run_registration(self, target_pdf, fmt_name, tags):
        """ [役割] アンカーとタグ座標をセットで保存 """
        image = self.img_proc.load_image_from_pdf(target_pdf)
        rects = self.img_proc.find_rectangles(image)
        anchor = self.img_proc.get_anchor_point(rects)

        with open(self.paths["json"], "r", encoding="utf-8") as f:
            data = json.load(f)
        data.append({"format_name": fmt_name, "anchor": anchor, "tags": tags})
        with open(self.paths["json"], "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def run_extraction(self, pdf_path):
        """ [役割] ズレ補正を行いながらデータを抜き出す """
        image = self.img_proc.load_image_from_pdf(pdf_path)
        rects = self.img_proc.find_rectangles(image)
        curr_anchor = self.img_proc.get_anchor_point(rects)

        # 形式特定
        with open(self.paths["json"], "r", encoding="utf-8") as f:
            formats = json.load(f)
        
        matched = None
        for fmt in formats:
            ref = fmt["anchor"]
            if ((curr_anchor[0]-ref[0])**2 + (curr_anchor[1]-ref[1])**2)**0.5 < 50:
                matched = fmt; break
        if not matched: raise ValueError("形式不一致")

        # ズレ補正値
        off_x, off_y = curr_anchor[0] - matched["anchor"][0], curr_anchor[1] - matched["anchor"][1]
        
        res = {"ファイル名": os.path.basename(pdf_path), "形式": matched["format_name"]}
        is_text = self.ocr_eng.is_text_based(pdf_path)

        for tag in matched["tags"]:
            # 補正後座標 (ピクセル)
            ax, ay, aw, ah = tag["x"]+off_x, tag["y"]+off_y, tag["w"], tag["h"]
            
            if is_text:
                # [重要] ピクセル座標をpdfplumberのポイント座標に変換(200DPI想定)
                bbox = (ax*72/200, ay*72/200, (ax+aw)*72/200, (ay+ah)*72/200)
                val = self.ocr_eng.extract_from_text_pdf(pdf_path, bbox)
            else:
                crop = self.img_proc.crop_image(image, (ax, ay, aw, ah))
                val = self.ocr_eng.extract_from_image(crop)
            
            res[tag["tag_name"]] = val.strip() if val else ""
        
        self.temp_data_list.append(res)
        return matched["format_name"]

    def create_excel(self):
        if not self.temp_data_list: return None
        path = os.path.join(self.paths["output"], f"result_{datetime.datetime.now():%Y%m%d_%H%M}.xlsx")
        pd.DataFrame(self.temp_data_list).to_excel(path, index=False)
        return path