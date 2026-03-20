# PDF Translator

学術論文PDFを英語から日本語に翻訳し、Word文書（.docx）として出力するツールです。  
数式や図表はそのまま保持されます。

## アーキテクチャ

責務を3つのモジュールに分離したパイプライン構成です。

```
main.py                  # パイプラインのオーケストレーション
modules/
├── extractor.py         # PDFからMarkdownとしてセクション単位でテキストを抽出
├── translator.py        # Gemini APIによる翻訳 & 状態管理
└── builder.py           # 翻訳済みMarkdownをWord文書（.docx）に変換して出力
```

### 処理フロー

1. **抽出** — `pymupdf4llm` でPDFをMarkdownに変換し、セクション単位に分割して `temp/state.json` に保存
2. **翻訳** — 未翻訳セクションをGemini APIで日本語に翻訳、結果をstate.jsonに記録
3. **構築** — 翻訳済みMarkdownを解析し、`python-docx` で見出し・段落・表・画像を含むWord文書を生成

## セットアップ

### 前提条件

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) パッケージマネージャー
- Gemini API Key
- macOS (Apple Silicon)

### インストール

```bash
# 依存パッケージのインストール
uv sync
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

翻訳済みWord文書は `output/` ディレクトリに `<元ファイル名>_translated.docx` として出力されます。

## ディレクトリ構成

```
pdf-translator/
├── input/          # 翻訳対象のPDFを配置
├── output/         # 翻訳済みWord文書の出力先
├── temp/           # 状態管理ファイル (state.json) と中間生成物
│   └── images/     # PDFから抽出された図表画像
├── modules/        # 各モジュール
├── main.py         # エントリーポイント
├── .env            # API Key
└── pyproject.toml
```

## 状態管理

翻訳の進捗は `temp/state.json` に保存されます。  
各セクションは以下のステータスを持ちます:

| ステータス | 説明 |
|-----------|------|
| `pending` | 未翻訳（翻訳待ち） |
| `translated` | 翻訳完了 |
| `error` | 翻訳エラー（次回リトライ対象） |

途中で中断しても、再実行時に翻訳済みセクションはスキップされます。  
また、PDFからの再抽出時にテキストが変わっていないセクションも再翻訳をスキップします。

## 技術スタック

- **PDF → Markdown変換**: [pymupdf4llm](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/)
- **Word文書生成**: [python-docx](https://python-docx.readthedocs.io/)
- **翻訳API**: [Google Gemini](https://ai.google.dev/) (`gemini-2.5-flash`)
- **PDF処理**: [PyMuPDF](https://pymupdf.readthedocs.io/)
