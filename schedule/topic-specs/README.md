# topic-specs（図解自動生成用）

`図解 自動生成→配信` ワークフローが、配信日の直前に **HTML を自動生成**するときに読む JSON です。

## いつ使うか

- **新しいテーマ**を初めて配信するとき
- `publish-html/` にまだ HTML が無いとき

既に HTML があるテーマ（再掲・フォロー）は **spec 不要**。ワークフローはそのまま同期→Discord だけ実行します。

## 手順

1. `schedule/topic-specs/<slug>.json` を作成（`_example.json` をコピー）
2. `schedule/posts.json` に日付キーを追加
   - `url` の slug と spec の slug を一致させる
   - 初回のみ `"auto_generate": true` を付けてもよい（HTML が無い場合は自動で true 扱い）
3. `ops/diagram-publish-manifest.json` に `{ "slug", "source" }` があることを確認
4. 日・水・土 9:00 JST に **図解 自動生成→配信** が走る（または手動 Run workflow）

## ローカルで生成テスト

```bash
python ops/generate_diagram_from_spec.py \
  --spec schedule/topic-specs/_example.json \
  --output /tmp/test-diagram.html
```

## Cursor で作る場合

`.cursor/skills/uscpa-far-diagram-quality/SKILL.md` に沿って HTML を直接 `publish-html/` に書いてもよい。その場合は spec は不要で、push 時に diagram-site 同期されます。
