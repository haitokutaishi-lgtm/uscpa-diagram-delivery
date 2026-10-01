# knowledge — 図解づくりのナレッジ置き場

図解を作るたびに分かったこと（テキストとの対応、確かめた基準、受講生の反応、決めたこと）をここに残し、次の図解に生かす。

## 何がどこにあるか

| ファイル | 書き方 | 中身 |
|---|---|---|
| `lessons.md` | 手で書く | テーマをまたいで使える教訓・方針（なぜ旧型をやめたか、受講生の反応、ユーザーの指示） |
| `topics/<slug>.md` | 手で書く | テーマごとのノート（FARテキストの該当箇所、確かめた基準、出典、決めたこと、改訂履歴、宿題） |
| `index.md` | **自動生成** | 全テーマの一覧（型・FARテキスト・ASC・更新日） |
| `traps-index.md` | **自動生成** | v2 図解の「引っかけ一覧」と「こう間違える」をテーマ横断で集めたもの |

自動生成の2つは `ops/build_knowledge_index.py` が topic-spec から作る。push すると GitHub Actions（`knowledge-index.yml`）が作り直してコミットするので、手で直さない。

## 使い方

**図解を作る前**
1. `lessons.md` を読む
2. `topics/<slug>.md` があれば読む（前回の宿題・決めたこと）
3. `traps-index.md` で近い論点の引っかけを探す

**図解を作った後**
1. topic-spec の `knowledge`（`far_text` / `asc` / `updated` / `sources`）を埋める
2. `topics/<slug>.md` を `topics/_template.md` から作る／追記する
3. テーマをまたいで使える気づきがあれば `lessons.md` に1行足す

**受講生の反応・質問が来たら**
該当テーマの `topics/<slug>.md` の「受講生の反応」に日付つきで残す。複数テーマに効くものは `lessons.md` にも。
