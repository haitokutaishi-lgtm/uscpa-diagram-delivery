# topic-specs（図解自動生成用）

`図解 自動生成→配信` ワークフローが、配信日の直前に **HTML を自動生成**するときに読む JSON です。

## 構成（10部・2026-07改訂）

生成される HTML は次の順（存在するセクションのみ・番号は自動採番）。

① 30秒でわかるこのページ（`three`） → ② 先に言葉をそろえる（`glossary`） → ③ よくある悩み → ④ 会計の背景と仕訳 → ⑤ 計算の型 → ⑥ 対話で整理 → ⑦ 横串マップ（`crossmap`） → ⑧ 出題パターンの引き出し（`patterns`） → ⑨ 理解確認MC（`focus`＋`distractors_html` 付き） → ⑩ まとめ（`one_minute_html`＋`checklist`）

新規テーマでは `glossary` / `crossmap` / `patterns` / 各MCの `focus`・`distractors_html` / `one_minute_html` / `checklist` を**必須**とする（詳細は `ops/diagram-theme-definition-of-done.md`）。スキーマの見本は `_example.json`。

## いつ使うか

- **新しいテーマ**を初めて配信するとき
- `publish-html/` にまだ HTML が無いとき

既に HTML があるテーマ（再掲・フォロー）は **spec 不要**。ワークフローはそのまま同期→Discord だけ実行します。

## 手順（完全自動）

1. `schedule/topic-specs/<slug>.json` を作成（HTML を手書きしない場合）
2. `ops/diagram-publish-manifest.json` に `{ "slug", "source" }` を追加
3. `schedule/delivery-queue.json` の `items` に `{ id, slug, title, description }` を追加  
   → **posts.json の日付は cron が自動追記**（`maintain_posts_queue.py`）
4. 日・水・土 9:00 JST に **図解 自動生成→配信** が走る

## ローカルで生成テスト

```bash
python ops/generate_diagram_from_spec.py \
  --spec schedule/topic-specs/_example.json \
  --output /tmp/test-diagram.html
```

## Cursor で作る場合

`.cursor/skills/uscpa-far-diagram-quality/SKILL.md` に沿って HTML を直接 `publish-html/` に書いてもよい。その場合は spec は不要で、push 時に diagram-site 同期されます。
