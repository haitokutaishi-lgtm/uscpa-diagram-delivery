---
name: uscpa-far-diagram-quality
description: >-
  USCPA FAR 向け publish-html 図解の品質基準（7部構成・理論・仕訳・誤解①〜③・平易な日本語・英語用語・MC・Discord配信）。
  図解の新規作成・全面改稿・読みやすさ改善・配信予定確認・diagram-site 同期のときは必ず使用。
  キャラは uscpa-dialog-characters と併用。完成形は asset-group-relative-sales-value.html と warranty-liability.html。
---

# USCPA FAR 図解品質（読者目線）

`publish-html/*.html` を作る・直すときの**固定ルール**。

| 参照 | パス |
|------|------|
| キャラ | [uscpa-dialog-characters](../uscpa-dialog-characters/SKILL.md) |
| 按分・取得（完成形） | `publish-html/asset-group-relative-sales-value.html` |
| 製品保証（完成形） | `publish-html/warranty-liability.html` |
| 配信カレンダー | `schedule/posts.json` |
| 配信状態 | `schedule/discord-post-state.json` |
| slug 一覧 | `ops/diagram-publish-manifest.json` |

## いつ使うか

- 図解の新規・改稿・「もう一度出力」「読みやすく」「skill 更新」
- `schedule/posts.json` の title / description を書くとき
- 「今週の配信は何か」を答えるとき（cron ＋ `last_posted_date` を読む）
- Discord 配信・diagram-site 同期の前チェック

---

## 7部構成（必須）

| # | id | 見出し | 内容 |
|---|-----|--------|------|
| ① | `worries` | よくある悩み | 試験問題文の例（`mc-preview-box`）＋誤解①〜③の対話 |
| ② | `three` | まず覚える3つ | 概念の芯3点（計算前の地図） |
| ③ | `theory` | **会計の背景と仕訳** | **②と④の間に必須**（下記テンプレ） |
| ④ | `reading` | 計算の型 | 手順（4〜5ステップ）＋表・SVG |
| ⑤ | `process` | 対話で整理 | ①の誤解を解くたくま×あおい先生 |
| ⑥ | `mc` | 理解確認MC | オリジナルMC 2問（英語 stem） |
| ⑦ | `summary` | この図解のまとめ | 箇条書き5〜6点 |

**書かないこと**: 「⑤と同じを先に読んで」等のメタ説明、「使う」「罠」タグ、間違いA/B/C、説明なしの業界カタカナ（ロールフォワード・履行・レール等）

### ③ 会計の背景と仕訳（テンプレ）

1. **背景（なぜ）** — 経済実態・GAAP の趣旨（資産の個別計上、費用と売上の期間一致など）
2. **いつ** — `timeline-mini` で処理順（取得時／販売時／期末…）
3. **仕訳** — `theory-block` 内に `je-line` で Dr/Cr（勘定名は英語）。①の数字と一致
4. **②との接続** — part-lead「②の3つは、ここでの〇〇に対応」
5. **④への接続** — 締め「④は、この仕訳の金額を求める手順」

**CSS（head に追加）**: `.theory-block`, `.je-line`, `.timeline-mini` — 完成形 HTML をコピー可

---

## タイトル・ヘッダー

- **Discord・h1**: 試験で想像できる日本語（「バンドル購入」だけ等は NG）
- テーマバッジ: `今回のテーマ：{英語科目} — {英語キーワード（日本語補足）}`
- リード: です・ます調。試験の**英文・数字の型**を1文

---

## 日本語

- **です・ます調**（対話含む）
- 動詞は具体化: 計上する／配分する／減らす／足し引きする
- NG → OK の例:
  - 一つの現金 → 一度の現金払い
  - 載せる → 計上する
  - 拾う → 問題文から読み取る
  - ロールフォワード → 期首残高に認識を足し、支出を引いて期末残高を求める
  - 履行 → 引当を減らす
  - マッチング・レール・ドリル → 平易な説明に言い換え
  - ④ 悩みが解けるまで → ⑤ 対話で整理

## 専門用語

- 試験・ASC の語は `<span class="term-en">英語</span>` を主とする
- 誤解ラベル: **`誤解①　…`**（全角スペース）。凡例「選択肢 A〜D とは別」

## 対話・キャラ

- たくま（受講生）／あおい先生（コーチ）、`avatars/takuma-dialog.png` / `aoi-dialog.png`
- 誤解①〜③はたくまの `mistake-label` → あおい先生が訂正
- 直前のコーチ発言と矛盾する受け口を書かない

## MC

- ①の stem と ⑥ 問題1は同型でよい（重複メタ説明は不要）
- ⑥: 計算1＋概念1。解説に Step または誤解番号
- `ASC ○○○` に沿う旨を1文

---

## Discord 自動配信（読み方）

- **cron**: 日・水・土 9:00 JST（`.github/workflows/discord-scheduled-post.yml`）
- **キュー**: `schedule/posts.json` の日付キー（昇順）
- **次に出す1件**: `last_posted_date` **より後**で、**今日（JST）以前**のキーのうち**最古**
- **手動再投稿**: `gh workflow run "Discord 図解配信" -f post_date=YYYY-MM-DD`（`last_posted_date` は巻き戻さない）
- **diagram-site**: 配信前に `ops/sync_diagram_site.sh` で `topics/<slug>/index.html` を更新

ユーザーに「今後1週間の配信」を示すときは、上記ロジックで **次の cron 日ごとに何が出るか** を表にする。HTML が旧型のテーマは「図解は未改稿・再掲のみ」と明記する。

---

## 配信前ワークフロー

1. `manifest` に slug / `publish-html/*.html` があるか
2. 図解が本スキルの **7部構成・完成度** か確認（未改稿なら改稿 or 再掲のみと記載）
3. `posts.json` の title / description を図解トーンに合わせる（平易な日本語）
4. `bash ops/sync_diagram_site.sh <FAR_ROOT> <diagram-site clone>` → push
5. ユーザー依頼時のみ Discord workflow 実行

---

## 改稿チェックリスト

```
- [ ] タイトルが初見で「何の試験問題か」分かる
- [ ] ① 試験問題例 + 誤解①〜③ + 凡例
- [ ] ③ 背景・処理順・仕訳（je-line）・②④への接続
- [ ] ④ 計算手順 + 表 or 図
- [ ] 使う/罠/間違いA なし、ロールフォワード等の不透明語なし
- [ ] です・ます、term-en 中心
- [ ] 7部・section-card・ナビ番号①〜⑦
- [ ] たくま/あおい・avatar・alt
- [ ] MC2問・ASC言及
- [ ] posts.json と URL が manifest と一致
```

## 図解の改稿状況（目安）

| slug | 7部+理論+品質 | 備考 |
|------|----------------|------|
| asset-group-relative-sales-value | 済 | 按分・参照実装 |
| warranty-liability | 済 | 製品保証・参照実装 |
| refinancing-current-liabilities | 要改稿 | 再掲予定あり |
| current-liabilities-classification | 要改稿 | |
| treasury-stock-par-value | 要改稿 | |
| notes-payable-accrued-interest | 要改稿 | |
| involuntary-conversion-gain | 要改稿 | |
| income-taxes-dta / inventory-lcm-* | 配信キュー外方針 | posts.json にキーなし |

未改稿テーマを配信する前に、可能なら本スキルで HTML を更新してから出す。
