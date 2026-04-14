# 🌌 NASA 宇宙探検ダッシュボード

NASAの「今日の宇宙画像（APOD）」を取得し、Amazon BedrockのAIが中高生向けに日本語で解説してくれるWebアプリです。

## 機能

- 日付を選択すると、その日の宇宙画像（または動画）を表示
- NASAによる英語の解説文を表示
- ボタン1つでAI（Amazon Nova Lite）が日本語で解説

## 事前準備

### NASA API Key

[api.nasa.gov](https://api.nasa.gov) で無料取得できます。
すぐ試したい場合は `DEMO_KEY`（リクエスト数制限あり）をそのままご利用ください。

### AWS 認証情報

Amazon Bedrockを使用するため、AWS認証情報が必要です。
`ap-northeast-1`（東京リージョン）で `amazon.nova-lite-v1:0` モデルへのアクセス権を有効にしてください。

## セットアップ

### uv を使う場合（開発者向け）

```bash
uv run streamlit run nasa01.py
```

### pip を使う場合

```bash
pip install -r requirements.txt
streamlit run nasa01.py
```

## 使い方

1. サイドバーにNASA APIキーを入力（デフォルト: `DEMO_KEY`）
2. 見たい日付を選択
3. 「宇宙を探索する」ボタンを押す
4. 画像と英語の解説が表示されたら「AIに日本語で解説してもらう」ボタンを押す
