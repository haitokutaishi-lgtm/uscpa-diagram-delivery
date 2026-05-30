---
name: uscpa-far-diagram-quality
description: >-
  USCPA FAR 向け publish-html 図解の品質基準（タイトル・日本語・誤解ラベル・英語用語・7部構成・理論・仕訳・MC・配信）。
  図解の新規作成・全面改稿・読みやすさ改善・Discord/diagram-site 反映・「別テーマも出力」と言われたときは必ず使用。
  uscpa-dialog-characters と併用する。
---

# USCPA FAR 図解品質（読者目線）

`publish-html/*.html` を作る・直すときの**固定ルール**。キャラ見た目は [uscpa-dialog-characters](../uscpa-dialog-characters/SKILL.md)、HTMLの骨格は `publish-html/asset-group-relative-sales-value.html` を**リファレンス実装**とする。

## いつ使うか

- 図解の新規・改稿・「もう一度出力」「読みやすく」「skill化」
- `schedule/posts.json` のタイトル／概要を書くとき
- Discord 配信前の最終チェック

## 7部構成（必須）

| # | id | 見出し | 内容 |
|---|-----|--------|------|
| ① | `worries` | よくある悩み | 試験問題文の例（`mc-preview-box`）＋誤解①〜③の対話 |
| ② | `three` | まず覚える3つ | 概念の芯3点（計算前の地図） |
| ③ | `theory` | **会計の背景と仕訳** | **②と④の間に必須**。GAAPの目的・いつ・なぜ・仕訳レベル |
| ④ | `reading` | 計算の型／読む順 | 手順＋表・SVG |
| ⑤ | `process` | 対話で整理 | ①の誤解を解くたくま×あおい先生 |
| ⑥ | `mc` | 理解確認MC | オリジナルMC 2問（英語 stem） |
| ⑦ | `summary` | この図解のまとめ | 箇条書き5点前後 |

### ③ 会計の背景と仕訳（書く内容）

1. **背景（なぜ）**: 取引の経済実態・会計原則（例: 資産は個別に計上、費用は発生期間にマッチング）
2. **いつ**: 取得時／販売時／期末など、イベントの順序を短いタイムライン or 箇条書き
3. **仕訳**: 典型2〜4本を `je-line` で明示（Dr/Cr・勘定名は英語）。金額例は①の数字と整合
4. **②との接続**: part-lead で「②の3つが、仕訳のどこに対応するか」1文
5. **④への接続**: 締めで「次の計算の型は、この仕訳の金額を求める作業です」

- ナビ・各 `section` は `section-card`（①は `worries-box` 併用可）
- CSS: `.theory-block`, `.je-line`（リファレンス HTML 参照）
- **書かないこと**: 「⑤と同じ問題を先に読んで」などメタ説明、「使う」「罠」タグ、間違いA/B/C ラベル

## タイトル・ヘッダー

**Discord・h1 は試験でイメージできる日本語**。専門の俗称だけにしない。

| NG | OK の例 |
|----|---------|
| バンドル購入、製品保証引当だけ | 土地・建物を一括購入したときの按分／売上に連動する製品保証の引当 |
| 見積りー実支出ー期末（記号だらけ） | 見積り→実際の支出→期末残高の流れ |

ヘッダー subs:
- テーマバッジ: `今回のテーマ：{科目英語} — {英語キーワード（日本語補足）}`
- リード: です・ます調。試験でよく出る**英文・数字の型**を1文で示す

## 日本語

- **です・ます調**で統一（対話も同様）
- 避ける言い回し: 一つの現金、載せる、拾う、セット1回、割る（→按分する／振り分ける）、④悩みが解けるまで（→対話で整理）
- **パッと見て分かりにくい日本語・カタカナは使わない**（説明なしで置かない）:
  - NG例: ロールフォワード、履行、マッチング、レール、フロー、ドリル
  - OK例: 「期首残高に当期の認識を足し、支出を引いて期末残高を求める」「引当を減らして現金を支払う」
- 会計処理は **計上する／配分する／減らす** など動詞をはっきり
- 英語用語は `<span class="term-en">...</span>`。初出のみ短い日本語補足可（試験英語は英語のまま可）

## 専門用語

- 試験・ASC で使う語は **英語表記を主**（`carrying amount`, `warranty expense`, `estimated warranty liability`）
- 日本語だけの造語（歴史コスト、公正価値按分だけ等）に寄せない
- 誤解ラベル: **`誤解①　…`**（全角スペース）。凡例1文「選択肢 A〜D とは別」

## 対話・キャラ

- たくま／あおい先生、`avatars/takuma-dialog.png` / `aoi-dialog.png`（characters スキル準拠）
- 誤解①〜③は**たくまの吹き出し**に `mistake-label`、あおい先生が訂正
- 直前のコーチ発言と矛盾する受け口を書かない

## MC

- ①に代表 stem（⑥の問題1と同型でよい。同じ文言の重複説明は不要）
- ⑥は計算1＋概念1。解説に Step または誤解番号への対応
- ファクトチェック: 該当 ASC（例 460, 360）に沿う旨を1文

## 配信・同期

1. `ops/diagram-publish-manifest.json` に slug / source があるか確認
2. `schedule/posts.json` の `title`・`description` を図解と同じトーンに
3. `bash ops/sync_diagram_site.sh <FAR_ROOT> <diagram-site clone>`
4. Discord: `gh workflow run "Discord 図解配信" -f post_date=YYYY-MM-DD`（ユーザーが配信を依頼したときのみ）

## 改稿前チェックリスト

```
- [ ] タイトルは「何の試験問題か」が初見で分かる
- [ ] ①に試験問題例＋誤解①〜③＋凡例
- [ ] 使う／罠／間違いA なし
- [ ] 日本語はです・ます・自然な動詞（ロールフォワード・履行など見慣れないカタカナなし）
- [ ] 用語は term-en 中心
- [ ] 7部構成（③理論・仕訳あり）・section-card・numbered nav
- [ ] たくま／あおい・avatar img・alt 正しい
- [ ] MC2問・オリジナル・ASC 言及
```

## 参照ファイル

| 用途 | パス |
|------|------|
| 品質の完成形 | `publish-html/asset-group-relative-sales-value.html` |
| キャラ | `.cursor/skills/uscpa-dialog-characters/SKILL.md` |
| マニフェスト | `ops/diagram-publish-manifest.json` |
| 配信予定 | `schedule/posts.json` |
