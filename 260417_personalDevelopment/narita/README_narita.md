# 伝票転記システム (narita)

## 1. このシステムでできること
このシステムは、伝票PDFから項目を抽出し、確認と修正を行ったうえでExcelへ出力するためのアプリです。

主な目的は次の2点です。
- 伝票転記作業の手入力を減らすこと
- フォーマットごとの差異を吸収しながら、抽出処理を安定運用すること

## 2. 全体フロー
処理の流れは次の通りです。

1. フォーマット登録モードで、空伝票または記入済み伝票から枠を選択してタグ名を付ける
2. 文字認識モードで、記入済みPDFをアップロードする
3. 自動でフォーマット照合を行う
4. 座標補正を行って項目テキストを抽出する
5. 画面で抽出結果を確認し、必要なら手動修正する
6. Excelを新規作成してダウンロードする

## 3. 実装済み機能
### 3.1 フォーマット登録
- PDFアップロード
- 枠線検出 (OpenCV)
- 検出枠の可視化
- クリックによる枠選択とタグ付け
- 重複チェック (暫定)
- フォーマットの保存、名称変更、削除

### 3.2 文字認識
- 記入済みPDFアップロード
- フォーマット自動照合
- 自動照合失敗時の手動フォーマット指定
- PDF種別判定
	- テキスト型PDF: 座標ベースで抽出
	- 画像型PDF: OCRで抽出
- 抽出枠のデバッグ表示

### 3.3 抽出結果とExcel
- 抽出結果の一覧表示
- 手動編集と保存
- 複数結果の蓄積
- Excel新規作成とダウンロード

## 4. フォーマット判別の考え方 (現行)
フォーマット判別は、次の3要素を組み合わせた総合スコアで実施します。

- 基準枠の近さ
- 全体レイアウトの近さ
- ページ縦横比の近さ

総合スコアは次の重みで計算し、値が小さい候補を優先します。

- 基準枠の近さ: 45%
- 全体レイアウトの近さ: 45%
- ページ縦横比の近さ: 10%

補足:
- 枠数差のペナルティを加算し、枠の不足/過剰が大きい候補を下げる
- しきい値を超える場合は自動一致にせず、手動指定にフォールバックする
- 不一致時は候補ごとの内訳を表示し、誤判別の原因を確認できる

## 5. 同一フォーマットで枠サイズが異なる場合の扱い
同じ帳票なのに枠の大きさが変わるケースでは、次の方針で対応します。

- 判別は位置関係を重視する
- サイズ差は補助的な情報として扱う
- 必要に応じてしきい値を調整する

現在の判別方式は、位置関係とページ比率を中心に評価するため、サイズ差のみの揺らぎに比較的強い設計です。

## 6. 使用技術
- Streamlit
- pdfplumber
- PyMuPDF
- OpenCV
- numpy
- Pillow
- pytesseract
- openpyxl
- pydantic
- streamlit-image-coordinates

## 7. ディレクトリ概要
主要構成は次の通りです。

- app/main.py: Streamlit画面と処理フロー
- app/services: PDF処理、枠検出、照合、OCR、Excel出力
- data/formats.json: フォーマット定義
- outputs: 出力Excel
- tests: 単体テスト
- samples/formats: フォーマット登録用サンプル
- samples/recognition: 認識テスト用サンプル

## 8. 環境構築（初回セットアップ）
### 8.1 前提条件
- Python 3.10以上
- Windows環境を想定
- Tesseract-OCRがインストール可能であること

### 8.2 Python仮想環境の作成
narita フォルダで以下を実行します。移動コマンド↓
```bash
cd ./solutionDevelopment2/260417_personalDevelopment/narita

# Windows: PowerShellまたはコマンドプロンプト
python -m venv .venv
```

### 8.3 仮想環境のアクティベーション

#### Windows (PowerShell)
```bash
.\.venv\Scripts\Activate.ps1
```

#### Windows (コマンドプロンプト)
```bash
.venv\Scripts\activate.bat
```

#### Linux/Mac
```bash
source .venv/bin/activate
```

### 8.4 ライブラリのインストール
仮想環境をアクティベーション後、以下を実行します。

```bash
pip install -r requirements.txt
```

主要ライブラリ:
- streamlit: UIフレームワーク
- pdfplumber: PDF処理
- opencv-python: 枠線検出
- pytesseract: OCRエンジン
- openpyxl: Excel出力

### 8.5 Tesseract-OCRのインストール（重要）
pytesseractはTesseract-OCRとセットで動作します。別途インストールが必要です。

#### Windows
1. 以下からインストーラをダウンロード
   https://github.com/UB-Mannheim/tesseract/wiki
   
    tesseract-ocr-w64-setup-5.5.0.20241111.exe (64 bit)をダウンロード

2. インストーラ実行（デフォルト: C:\Program Files\Tesseract-OCR）

3. Pythonから使用可能にするため、以下を app/main.py に追加（またはセットアップ時に確認）
   ```python
   import pytesseract
   pytesseract.pytesseract.pytesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
   ```
   
   既に実装済み場合は不要です。

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get install tesseract-ocr
```

#### Mac
```bash
brew install tesseract
```

### 8.6 セットアップ確認
以下のコマンドで正常にセットアップできたか確認します。

```bash
# Pythonライブラリの確認
pip list

# Tesseractの確認
tesseract --version
```

## 9. 起動方法
1. narita フォルダへ移動
2. 仮想環境をアクティベーション（上記 8.3 を参照）
3. 以下のコマンドで起動

```bash
.venv\Scripts\activate.bat
python -m streamlit run app/main.py
```

または PowerShell の場合：

```bash
.\.venv\Scripts\Activate.ps1
python -m streamlit run app/main.py
```

4. ブラウザが自動で起動し、`http://localhost:8501` にアクセスします

### トラブル時の確認
- ポート 8501 が既に使用中の場合
  ```bash
  streamlit run app/main.py --server.port 8502
  ```

## 10. テスト実行
次のコマンドで単体テストを実行できます。

```bash
python -m unittest discover -s tests
```

## 11. 現在の課題
- OCR精度の改善
- 実データでのしきい値最適化
- 結合テストと異常系テストの拡充
- ログ整備 (処理時間、失敗原因、抽出成功率)

## 12. 運用メモ
- フォーマット定義は data/formats.json に保存される
- 定義破損時に備えて定期バックアップを推奨
- フォーマット追加後は、同一帳票の複数サンプルで判別確認を行う
