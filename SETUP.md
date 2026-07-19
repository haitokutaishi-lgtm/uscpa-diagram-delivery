# 図解 × Discord 定期配信 — セットアップ

## 1. 正データ（何をいつ流すか）

- **配信の正**: `schedule/posts.json`（**日・水・土の cron が `delivery-queue.json` から自動追記**）→ Discord。
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

1. SSH 鍵ペアを作成し、公開鍵を **`diagram-site` リポジトリの Deploy Key（Allow write access 有効）** として登録する。

   ```bash
   ssh-keygen -t ed25519 -N "" -f /tmp/diagram_site_deploy_key
   gh api repos/haitokutaishi-lgtm/diagram-site/keys \
     -f title="uscpa-diagram-delivery sync (Actions)" \
     -f key="$(cat /tmp/diagram_site_deploy_key.pub)" -F read_only=false
   ```

2. このリポジトリ（FAR テキスト一覧）の Secrets に追加する。
   - Name: `DIAGRAM_SITE_DEPLOY_KEY`
   - Value: 上記の **秘密鍵**（`/tmp/diagram_site_deploy_key` の中身）

   ```bash
   gh secret set DIAGRAM_SITE_DEPLOY_KEY \
     --repo haitokutaishi-lgtm/uscpa-diagram-delivery < /tmp/diagram_site_deploy_key
   ```

   Deploy Key は `diagram-site` 1リポジトリにしか効かないため、PAT より漏えい時の影響が小さい（旧 `DIAGRAM_SITE_PUSH_TOKEN` 方式は 2026-07 に廃止）。

**動き:**

- **`Sync diagram-site topics`** … `main` へ `publish-html/` が push されたときに diagram-site へ同期（手動編集時）。
- **`図解 自動生成→配信`**（旧名 Discord 図解配信）… 日・水・土 9:00 JST に **(1) topic-spec から HTML 自動生成（必要時） (2) diagram-site 同期 (3) Discord 投稿** を一括実行。

### 完全自動で回すために必要なもの

| 項目 | 場所 |
|------|------|
| Discord Webhook | GitHub Secret `DISCORD_WEBHOOK_URL`（**必須**） |
| diagram-site 更新 | Secret `DIAGRAM_SITE_DEPLOY_KEY`（**強く推奨**） |

**配信時刻はランダムではありません。** 日・水・土 **9:00 JST** 固定です。以前 3:00 頃に出たのは GitHub cron の遅延（UTC 0時台の混雑）が原因で、`timezone: Asia/Tokyo` と 9:00 までの待機で抑えています。

**Secret の手動確認は不要です。** 次のタイミングで Actions が自動検証します。

- **毎回の配信**（日・水・土 9:00）… `図解 自動生成→配信` の prepare 冒頭
- **週1回**（日曜 9:00 JST）… `図解配信 Secrets ヘルスチェック`（投稿なし・ログと Summary のみ）
- **いつでも** … Actions → `図解配信 Secrets ヘルスチェック` → Run workflow

失敗したら Actions の実行ログまたは **Summary** タブに ❌ と理由が出ます（Secret の値そのものは表示されません）。
| 配信バックログ | `schedule/delivery-queue.json`（未スケジュール分） |
| 先読み枠数 | `schedule/delivery-config.json` の `lookahead_slots`（既定6） |
| 除外 slug | 同 `excluded_slugs`（既定: DTA・在庫LCMドリル） |

### 新テーマを追加するとき（手動はここだけ）

1. `publish-html/<slug>.html` を用意（または `schedule/topic-specs/<slug>.json`）
2. `ops/diagram-publish-manifest.json` に `{ slug, source }` を追加
3. `schedule/delivery-queue.json` の `items` に `{ id, slug, title, description }` を追加

**`posts.json` に日付を書く必要はありません。** 次の日・水・土の枠が空いていれば cron が自動で日付キーを足します。

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
