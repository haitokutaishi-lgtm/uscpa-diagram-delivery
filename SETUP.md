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

### GitHub Pages（diagram-site）への自動同期

図解 HTML はこのリポジトリの `publish-html/` を正とし、Actions が **`diagram-site` リポジトリの `topics/<slug>/index.html` にコピーして push** します。

1. GitHub で **Fine-grained personal access token**（または classic PAT）を作成し、対象リポジトリ **`diagram-site`** に **Contents: Read and write** を付与する。
2. このリポジトリ（FAR テキスト一覧）の Secrets に追加する。
   - Name: `DIAGRAM_SITE_PUSH_TOKEN`
   - Value: 上記 PAT（1行）

**動き:**

- **`Sync diagram-site topics`** … `main` へ `publish-html/` が push されたときに diagram-site へ同期（手動編集時）。
- **`図解 自動生成→配信`**（旧名 Discord 図解配信）… 日・水・土 9:00 JST に **(1) topic-spec から HTML 自動生成（必要時） (2) diagram-site 同期 (3) Discord 投稿** を一括実行。

### 新テーマを自動で出す手順

1. `schedule/topic-specs/<slug>.json` を作成（`schedule/topic-specs/_example.json` をコピー）
2. `ops/diagram-publish-manifest.json` に slug / source を追加
3. `schedule/posts.json` に配信日・title・description・url を追加
4. 何もしなくてよい — 配信日の cron で生成→公開→Discord

既に `publish-html/` があるテーマ（再掲）は spec 不要。同期と Discord のみ走ります。

スラッグとファイルの対応は **`ops/diagram-publish-manifest.json`** のみ。新しい `topics/...` を配信に載せるときは、(1) `publish-html/` に HTML を置く (2) manifest に `{ "slug", "source" }` を追加する (3) `posts.json` の URL の slug と一致させる。

`publish-html/avatars/` に PNG 等を置くと、同期時に **各** `topics/<slug>/avatars/` へもコピーされる。HTML からは `avatars/ファイル名.png` の相対パスで参照する（対話キャラの設計書は `.cursor/skills/uscpa-dialog-characters/SKILL.md` を参照）。

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

**図解 自動生成→配信** は、`last_posted_date` より後で今日以前の **最古の未投稿キー** を1件処理します。キューが空なら投稿せず成功終了します。

**確認:** Actions の実行ログを開き、`Post today entry to Discord` に  
`Today (Asia/Tokyo): …` と `Keys in schedule/posts.json` が出るので、**今日の日付がキー一覧に含まれているか**見る。

**対処 A:** `posts.json` に今日のキーを追加して push してから、再度 Run workflow。

**対処 B（テスト用）:** Actions → **図解 自動生成→配信** → **Run workflow** → **post_date** に未投稿の日付を指定。HTML を spec から作り直す場合は **force_regenerate** をオン。

## 6. 図解 HTML の置き場（専用リポジトリ）

- リポジトリ: [diagram-site](https://github.com/haitokutaishi-lgtm/diagram-site)（`~/diagram-site`）
- 規約: `topics/<テーマID>/index.html`（新規は `topics/_template` をコピー）
- 公開 URL の形: `https://haitokutaishi-lgtm.github.io/diagram-site/topics/<テーマID>/index.html`
- `posts.json` の `url` には、上記の **フル URL**（図解が表示できたあと）を書く。

初回はリポジトリ **Settings → Pages** で `main` / `/(root)` を有効化（既に有効なら不要）。
