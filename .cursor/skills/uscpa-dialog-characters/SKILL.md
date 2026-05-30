---
name: uscpa-dialog-characters
description: >-
  USCPA FAR 図解 HTML（publish-html）の「受講生×コーチ」対話に、公式キャラクター
  **たくま（受講生）** と **あおい先生（コーチ）** のイラスト基調を適用する。
  キャラ設計図は `publish-html/avatars/uscpa-character-design-sheet.png`。
  ユーザーが図解・対話・publish-html・diagram-site 同期・受講生コーチの見た目と言及したときに読む。
---

# USCPA 図解キャラクター（たくま／あおい先生）

## キャラクター定義（固定）

| 役割 | 名前 | 立ち位置 |
|------|------|----------|
| 受講生 | **たくま** | USCPA 受験生。悩み・誤解を代弁し、共感の入口になる。 |
| コーチ | **あおい先生** | 講師。会計士らしい「型」で整理し、試験英語の読み方を示す。 |

- デザイン意図（ユーザー提供の設計書に準拠）: やわらかく安心感のあるタッチ。受講生は「つまずきへの共感」、コーチは「身近な指導」。
- 色調: USCPA 学習向けにすっきりした知的トーン（紺・オレンジ・白ベースの図解と調和）。

## アセットの置き場所

- **マスター画像（設計シート）:** `publish-html/avatars/uscpa-character-design-sheet.png`
- **対話行の小アイコン（設計シートから切り出し）:**
  - `publish-html/avatars/takuma-dialog.png` … たくま（受講生）
  - `publish-html/avatars/aoi-dialog.png` … あおい先生（コーチ）
- 今後、吹き出し用に **別表情の切り出し PNG** を追加する場合は、同じ `publish-html/avatars/` に置き、ファイル名を `takuma-worry.png` のように役割・表情が分かる英語スネークケースにする。

## HTML での使い方

1. **設計シート全体**（表情一覧・立ち絵の参照）を載せるときは、図解の該当セクションに `figure` + `img` を使う。
   - `src` は **`avatars/ファイル名.png`**（`publish-html` 直下の HTML からの相対パス）。
   - `alt` に「たくま／あおい先生」と簡潔な説明を必ず書く。

2. **吹き出し横の小アイコン**は `avatar-frame` 内を **`<img src="avatars/takuma-dialog.png" ...>`**（受講生）／**`<img src="avatars/aoi-dialog.png" ...>`**（コーチ）にする。`overflow-hidden` と **`object-contain object-center`** で 56×56 に収める（**`object-cover` は頭や顎が欠けやすい**ので使わない）。**`transform: scale()` で無理に拡大しない**。どうしても小さく感じる場合のみ **`scale` を 1.05 前後**に留め、`transform-origin: 50% 50%` を推奨。

### 小アイコン PNG の切り出し（ImageMagick）

マスターは **1024×682**。上部モックは名前帯と干渉しやすいので、**下部「表情バリエーション」列の円1つ分**から切る。

```bash
SRC="publish-html/avatars/uscpa-character-design-sheet.png"
OUT="publish-html/avatars"
# たくま：下部「表情バリエーション」左ストリップの 1 セル（オレンジ見出しの下から切る）
magick "$SRC" -crop 92x118+38+518 +repage -resize 128x128 -background white -gravity center -extent 128x128 "$OUT/takuma-dialog.png"
# あおい先生：同ストリップ右側の 1 セル（幅を狭くして隣キャラを入れない）
magick "$SRC" -crop 74x104+442+526 +repage -resize 128x128 -background white -gravity center -extent 128x128 "$OUT/aoi-dialog.png"
```

シートのレイアウトが変わったら、`magick` の `-crop WxH+X+Y` を微調整する。

3. **ラベル文言**
   - バブル内の肩書きは **`たくま（受講生）`** / **`あおい先生（コーチ）`** を推奨（スキャンしやすい短さとキャラ名の両立）。
   - アバター下の小さな `span` があれば **`あおい先生`** などに揃える。

## diagram-site 同期

- `ops/sync_diagram_site.sh` は、manifest で同期する **各** `topics/<slug>/` に対し、`publish-html/avatars/` 内のファイルを **`topics/<slug>/avatars/`** へコピーする。
- したがって HTML 内の `avatars/...` 参照は、GitHub Pages 上でも **同じ相対パス**で動く。
- **Discord 図解配信**（`.github/workflows/discord-scheduled-post.yml`）は、配信 URL が `diagram-site/topics/…` のとき `ops/screenshot_discord_collage.py` で **会話を除いた本文セクション最大4枚**を 2x2 の PNG にして Webhook に添付する（`main > .section-card` / `main > section` を順に切り出す）。

## エージェント向けルール

- **新規・改稿する図解 HTML**では、構成・日本語・タイトル・誤解ラベルは [uscpa-far-diagram-quality](../uscpa-far-diagram-quality/SKILL.md) を併用する。
- 対話パートでは、Lucide の汎用アイコンだけで済ませず、可能なら本スキルのキャラ名・トーンに合わせる。
- 「さっきコーチが言った」など**前後の発言と矛盾する受け口**を書かない。直前の吹き出しに根拠があるか必ず確認する。
- ユーザーが新しいポーズの切り出し画像を渡したら、`publish-html/avatars/` に保存し、該当 HTML の `img` を差し替える。

## 参照

- 設計書のビジュアルはリポジトリ内 `publish-html/avatars/uscpa-character-design-sheet.png` を開いて確認する。
