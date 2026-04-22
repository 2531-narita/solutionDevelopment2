from flask import Flask, render_template, request, redirect, url_for, send_file
import os
from werkzeug.utils import secure_filename

from image_processor import ImageProcessor
from ocr_engine import OCREngine
from processor_logic import DocumentProcessor

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'

# フォルダ自動生成
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

paths = {
    "json": "data/formats.json",
    "templates": "data/templates",
    "input": UPLOAD_FOLDER,
    "output": OUTPUT_FOLDER
}

processor = DocumentProcessor(paths, ImageProcessor(), OCREngine())


# =========================
# トップページ
# =========================
@app.route('/')
def index():
    files = os.listdir(UPLOAD_FOLDER)
    return render_template('index.html', files=files)


# =========================
# アップロード
# =========================
@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')

    if file and file.filename.endswith('.pdf'):
        filename = secure_filename(file.filename)
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(save_path)

    return redirect(url_for('index'))


# =========================
# 処理実行
# =========================
@app.route('/process', methods=['POST'])
def process():
    selected_files = request.form.getlist('files')
    results = []

    for f in selected_files:
        pdf_path = os.path.join(UPLOAD_FOLDER, f)

        try:
            fmt = processor.run_extraction(pdf_path)
            results.append((f, '成功', fmt))
        except Exception as e:
            results.append((f, '失敗', str(e)))

    excel_path = processor.create_excel()

    # 👉 ファイル名だけ渡す（ここが重要）
    excel_name = os.path.basename(excel_path) if excel_path else None

    return render_template(
        'result.html',
        results=results,
        excel=excel_name
    )


# =========================
# ダウンロード
# =========================
@app.route('/download')
def download():
    file = request.args.get('file')

    if not file:
        return "ファイルが指定されていません", 400

    file_path = os.path.join(OUTPUT_FOLDER, file)

    if not os.path.exists(file_path):
        return "ファイルが見つかりません", 404

    return send_file(file_path, as_attachment=True)


# =========================
# 起動
# =========================
if __name__ == '__main__':
    app.run(debug=True)