import os
import glob
from image_processor import ImageProcessor
from ocr_engine import OCREngine
from processor_logic import DocumentProcessor

class AppManager:
    def __init__(self):
        self.base_dir = os.path.dirname(__file__)
        self.data_dir = os.path.join(self.base_dir, "data")
        self.paths = {
            "json": os.path.join(self.data_dir, "formats.json"),
            "templates": os.path.join(self.data_dir, "templates"),
            "input": os.path.join(self.data_dir, "input"),
            "output": os.path.join(self.data_dir, "output")
        }
        self.processor = DocumentProcessor(self.paths, ImageProcessor(), OCREngine())

    def menu_extraction(self):
        files = glob.glob(os.path.join(self.paths["input"], "*.pdf"))
        if not files: return print("\n[!] inputフォルダにPDFがありません。")

        print("\n" + "="*40)
        print(" 解析対象ファイル一覧")
        print("="*40)
        for i, f in enumerate(files):
            print(f" [{i:02d}] {os.path.basename(f)}")
        print("-" * 40)
        
        choice = input("解析する番号（複数なら 0,1,2 / 全てなら all）: ")
        if choice.lower() == 'all':
            selected = files
        else:
            try:
                selected = [files[int(x.strip())] for x in choice.split(",")]
            except:
                return print("[!] 正しい番号を入力してください。")

        print(f"\n>>> 実行中... ({len(selected)}件)")
        for pdf in selected:
            print(f"\n[処理中] {os.path.basename(pdf)}")
            try:
                fmt_name = self.processor.run_extraction(pdf)
                print(f"   ∟ 成功: {fmt_name} を適用しました。")
            except Exception as e:
                print(f"   ∟ 失敗: {e}")

        save_path = self.processor.create_excel()
        if save_path:
            print(f"\n" + "="*40)
            print(f" 全処理が完了しました。")
            print(f" 保存先: {save_path}")
            print("="*40)

if __name__ == "__main__":
    app = AppManager()
    print("\n【汎用PDFデータ抽出ツール v2.0】")
    print(" 1: フォーマット登録 (雛形から学習)")
    print(" 2: 一括抽出実行 (Excel出力)")
    mode = input("\n 選択 > ")
    if mode == "1":
        # 今回は簡略化のため、必要なら前回の登録メニューを入れてください
        pass
    elif mode == "2":
        app.menu_extraction()