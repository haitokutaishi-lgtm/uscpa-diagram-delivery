# 図解 × Discord 定期配信 — セットアップ

## 1. 正データ（何をいつ流すか）

- **正は `schedule/posts.json`**。ここに書いた日付・タイトル・URL だけが Discord に飛ぶ。
- スプレッドシートは **補助台帳**（コピー用）でよい。シートを正にすると二重管理なので、慣れるまでは **JSON だけ**で十分。

## 1b. スプレッドシート（任意）

1. Google スプレッドシートを新規作成
2. **ファイル → インポート** で `ops/content-registry-template.csv` を取り込む
3. 承認・メモ用。最終的に Discord に反映するのは **`posts.json` の push**。

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

### 「緑チェックなのに Discord に何も来ない」とき

**Discord 図解配信** は、`schedule/posts.json` に **その実行日のキー（日本時間の今日と一致する `YYYY-MM-DD`）** が無いと **投稿せず成功で終了**します。

**確認:** Actions の実行ログを開き、`Post today entry to Discord` に  
`Today (Asia/Tokyo): …` と `Keys in schedule/posts.json` が出るので、**今日の日付がキー一覧に含まれているか**見る。

**対処 A:** `posts.json` に今日のキーを追加して push してから、再度 Run workflow。

**対処 B（テスト用）:** Actions → **Discord 図解配信** → **Run workflow** を開き、**post_date** に `posts.json` に既にある日付（例: `2026-05-11`）を入力して実行 → そのキーの投稿が飛ぶか確認できる。

## 6. 図解 HTML の置き場（専用リポジトリ）

- リポジトリ: [diagram-site](https://github.com/haitokutaishi-lgtm/diagram-site)（`~/diagram-site`）
- 規約: `topics/<テーマID>/index.html`（新規は `topics/_template` をコピー）
- 公開 URL の形: `https://haitokutaishi-lgtm.github.io/diagram-site/topics/<テーマID>/index.html`
- `posts.json` の `url` には、上記の **フル URL**（図解が表示できたあと）を書く。

初回はリポジトリ **Settings → Pages** で `main` / `/(root)` を有効化（既に有効なら不要）。
