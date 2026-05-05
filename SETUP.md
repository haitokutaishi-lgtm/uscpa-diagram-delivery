# 図解 × Discord 定期配信 — セットアップ

## 1. スプレッドシート

1. Google スプレッドシートを新規作成
2. **ファイル → インポート → アップロード** で `ops/content-registry-template.csv` を取り込む
3. 1行目を固定行にし、以降のテーマを追記（版管理の正はここ）

`posts.json` は **その週に Discord で流す分だけ**、日付キーで同期してもよい（運用は好みで）。

## 2. Webhook（必ず秘密情報として扱う）

- Discord サーバー設定 → 連携サービス → ウェブフック → URL をコピー
- **チャットに貼った URL は無効化し、再発行した URL を GitHub Secrets にだけ保存**

GitHub リポジトリ → Settings → Secrets and variables → Actions → New repository secret

- Name: `DISCORD_WEBHOOK_URL`
- Value: 再発行したウェブフック URL（1行）

## 3. このフォルダを GitHub に載せる

例:

```bash
cd ~/uscpa-diagram-delivery
git init -b main
git add .
git commit -m "Add Discord schedule and content registry template"
gh repo create uscpa-diagram-delivery --public --source=. --remote=origin --push
```

## 4. 配信スケジュール（確定仕様）

- **日・水・土 9:00 JST**（A 方針）
- `schedule/posts.json` に **`"YYYY-MM-DD"`** キーで、その日の投稿内容を書く
- その日にエントリが無い場合は **何も投稿しない**（エラーにしない）

## 5. 失敗時のリトライ

Actions のタブから該当ワークフローを **Re-run failed jobs**、または **workflow_dispatch** で手動再実行。

## 6. GitHub Pages

図解 HTML のホスト先は従来どおり別リポジトリでもよい。`posts.json` の `url` に **公開済みのフル URL** を書く。
