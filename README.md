# PDF Translator

学術論文PDFのレイアウトを維持したまま、英語から日本語に翻訳するツールです。  
数式や図表はそのまま保持されます。

## アーキテクチャ

責務を4つのモジュールに分離したパイプライン構成です。

```
main.py                  # パイプラインのオーケストレーション & 自己修正ループ
modules/
├── extractor.py         # PDFからテキストブロックを段落単位で抽出
├── translator.py        # Gemini APIによる翻訳 & 状態管理
├── builder.py           # 翻訳テキストを元のレイアウトに再構成しPDF出力
└── evaluator.py         # 出力PDFを再抽出し、翻訳の反映率を自動評価
```

### 処理フロー

1. **抽出** — 入力PDFからテキストブロックと座標を抽出し `temp/state.json` に保存
2. **翻訳** — 未翻訳ブロックをGemini APIで日本語に翻訳、結果をstate.jsonに記録
3. **再構成** — 元PDFの該当領域を白塗りし、翻訳済みテキストを同じ座標に描画
4. **評価** — 出力PDFからテキストを再抽出し、翻訳結果（正解データ）との一致率を算出
5. **自己修正** — 一致率が80%未満の場合、失敗ブロックを再翻訳して最大3回リトライ

## セットアップ

### 前提条件

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) パッケージマネージャー
- Gemini API Key

### インストール

```bash
# 依存パッケージのインストール
uv add pymupdf google-genai python-dotenv
```

### API Keyの設定

プロジェクトルートに `.env` ファイルを作成:

```
GEMINI_API_KEY=your_api_key_here
```

## 使い方

```bash
# 基本的な使い方
uv run python main.py input/paper.pdf

# ページ数を制限（テスト・デバッグ用）
uv run python main.py input/paper.pdf --limit 3

# 状態ファイルのパスを指定
uv run python main.py input/paper.pdf --state temp/my_state.json
```

翻訳済みPDFは `output/` ディレクトリに `<元ファイル名>_translated.pdf` として出力されます。

## ディレクトリ構成

```
pdf-translator/
├── input/          # 翻訳対象のPDFを配置
├── output/         # 翻訳済みPDFの出力先
├── temp/           # 状態管理ファイル (state.json)
├── modules/        # 各モジュール
├── main.py         # エントリーポイント
├── .env            # API Key
└── pyproject.toml
```

## 状態管理

翻訳の進捗は `temp/state.json` に保存されます。  
各ブロックは以下のステータスを持ちます:

| ステータス | 説明 |
|-----------|------|
| `pending` | 未翻訳（翻訳待ち） |
| `translated` | 翻訳完了 |
| `error` | 翻訳エラー（次回リトライ対象） |

途中で中断しても、再実行時に翻訳済みブロックはスキップされます。

## 技術スタック

- **PDF操作**: [PyMuPDF](https://pymupdf.readthedocs.io/)
- **翻訳API**: [Google Gemini](https://ai.google.dev/) (`gemini-2.5-flash`)
- **フォント**: macOS内蔵ヒラギノ角ゴシック（フォールバック: PyMuPDF内蔵CJKフォント）
