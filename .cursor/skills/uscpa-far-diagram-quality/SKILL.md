---
name: uscpa-far-diagram-quality
description: >-
  USCPA FAR 向け publish-html 図解の品質基準。2026-10 から「復習シート型（v2）」が標準
  （全体図1枚・差がつく論点・引っかけ一覧・初見の数字のMC＋TBS入力式）。
  図解の新規作成・全面改稿・読みやすさ改善・配信予定確認・diagram-site 同期のときは必ず使用。
  完成形は equity-method-basic（topic-spec v2）。旧10部構成（対話形式）は新規では使わない。
---

# USCPA FAR 図解品質（読者目線）

`publish-html/*.html` を作る・直すときの**固定ルール**。

| 参照 | パス |
|------|------|
| 完成形（v2） | `schedule/topic-specs/equity-method-basic.json` → `publish-html/equity-method-basic.html` |
| v2 生成 | `ops/generate_diagram_v2.py`（spec に `"version": 2` があれば `generate_diagram_from_spec.py` から自動で切替） |
| v2 スタイル | `ops/diagram_v2_styles.css` |
| 配信カレンダー | `schedule/posts.json`（**自動補充**あり） |
| 配信バックログ | `schedule/delivery-queue.json` |
| 自動化設定 | `schedule/delivery-config.json` |
| 配信状態 | `schedule/discord-post-state.json` |
| slug 一覧 | `ops/diagram-publish-manifest.json` |

## いつ使うか

- 図解の新規・改稿・「もう一度出力」「読みやすく」「skill 更新」
- `schedule/posts.json` の title / description を書くとき
- 「今週の配信は何か」を答えるとき（cron ＋ `last_posted_date` を読む）
- Discord 配信・diagram-site 同期の前チェック

---

## 方針：受講生が「復習でまた開く」ページにする

2026-10 に見直し。旧型（10部構成・たくま×あおい先生の対話）は閲覧の反応がなく、原因は
「図がない文章の壁」「同じ例題の繰り返し」「テキストの焼き直しで差がつく論点がない」「毎回同じテンプレ」だった。
v2 はテキストで一度学んだ受講生の**復習ツール**として作る。

- **図が主役**：冒頭の全体図1枚でその論点の計算・処理の全体が分かること。スクショして保存できる完成度にする
- **例題は1つ**：全体図の数字を仕訳一覧・差がつく論点・TBS でも使い回す。同じ問題を2回出さない
- **試験範囲は全部載せる**：基本だけで終わらせず、テキストで「発展」扱いの論点も入れる
- **確認問題は初見の数字**：本文に出した問題・答えを再利用しない
- **FARテキストに合わせる**：`07_ナレッジ/ナレッジ/予備校の教材/OCR済みMarkdown/` に該当章があれば用語・論点の範囲をそろえる（転載はしない）

## ナレッジの読み書き（必須）

`knowledge/` に図解づくりの知見を貯めている（使い方は `knowledge/README.md`）。

- **作る前**：`knowledge/lessons.md` → `knowledge/topics/<slug>.md`（あれば）→ `knowledge/traps-index.md`（近い論点の引っかけ）を読む
- **作った後**：topic-spec の `knowledge`（`far_text` / `asc` / `updated` / `sources`）を埋め、`knowledge/topics/<slug>.md` を `_template.md` から作るか追記する。テーマ横断の気づきは `lessons.md` に追記
- **受講生の反応**：該当テーマのノートの「受講生の反応」に日付つきで残す
- `knowledge/index.md` と `traps-index.md` は push 時に自動生成（`knowledge-index.yml`）。手で直さない

## Discord の投稿文（spec の "post"）

投稿文は `ops/build_discord_payload.py` が spec の `post` から組み立てる（無いと旧来の1行投稿になる）。v2 では必ず書く。

| キー | 書くこと |
|---|---|
| `name` | 論点名（例：短期債務の借換え） |
| `text_ref` | テキストの章（例：テキスト4-7）。未収録なら書かない |
| `minutes` | 目安の所要時間（分） |
| `hook_q` | 開く前に考えてほしい問い。基本ではなく「差がつく論点」から、二択・三択で答えが割れるものを選ぶ |
| `hook_where` | 答えのある場所（例：差がつく論点2と問題2）。答えそのものは投稿に書かない |
| `bullets` | このページでできること3つ。最後は「初見の英語MC◯問＋TBS（入力すると自動で答え合わせ）」 |

改訂した図解を再配信するときは posts.json の該当日に `"revised": true` を付ける（見出しに「※改訂版」が付く）。
リアクションは ✅ 全問正解／🤔 間違えた問題があった／📌 あとで解く の3択で固定（反応を比べるため変えない）。

## v2 の標準構成（spec の sections に並べる。番号・目次は自動）

| # | id | 見出しの例 | 中身 | 主な block |
|---|----|-----------|------|-----------|
| 1 | `map` | 全体図：〇〇はこの5つで動く | 例題の前提（facts）＋図＋覚える式 | `facts` `taccount_map` / `html`（SVG等） `formulas` |
| 2 | `judge` | いつ〇〇か | 適用の判定・前提（比率・条件・例外） | `ruler` `rule` `cards2` `note` |
| 3 | `je` | 仕訳一覧（1の例の数字） | 場面ごとの仕訳とポイント | `table`（`en_cols: [1]`） |
| 4 | `points` | 差がつく論点 | 1論点＝ルール → 数字 → こう間違える | `point`（`rule_html` `calc_html` `miss_html`） |
| 5 | `traps` | 引っかけ一覧 | 問題文の英語 → 確認すること → よくある誤答（6〜8行） | `traps` |
| 6 | `mc` | 確認問題（初見の数字） | 英語MC 3〜4問（うち複合1問以上）＋TBS形式1問 | `mcq` `tbs` |
| 7 | `check` | 見ないで言えるかチェック | 5項目前後 | `checklist` |

論点によって 2 は省略してよい。1 の図が T勘定に向かない論点（分類・判定フローなど）は `html` block で SVG やフローを直接書く（`.diagram-visual` を付ける：Discord 画像の対象になる）。

### 書き方のルール

- **です・ます調**。格言調の締め、独自造語、「〜しろ」の命令調は書かない
- 試験・ASC の語は英語（`term-en`）、説明は平易な日本語。ロールフォワード・レール等の説明なしカタカナは使わない
- 「よく出る」「頻出」は書かない
- **差がつく論点**の「こう間違える」は具体的な数字の誤答で書く（例：「$100,000 全体を10年で割る」）
- **MC**：問題文・選択肢は英語で常時表示。「和訳を見る」と「正解と解説を見る」は別の折りたたみ。解説には各誤答がどう作られたかを1行ずつ
- **TBS**：`ans` に正解の数値（マイナスは負数）。入力は「1,000」「(6,000)」「-6000」どれでも判定される
- 公開前に**全ての数字を計算し直す**（例題・MC・TBS）。基準改正で結論が変わった論点（例：ASU 2016-07）は現行基準で書き、旧基準との違いを「こう間違える」で触れる

---

## 完全自動配信（標準運用）

ワークフロー名: **`図解 自動生成→配信`**（`.github/workflows/discord-scheduled-post.yml`）

| 順 | 処理 |
|----|------|
| 0 | `maintain_posts_queue.py` … `delivery-queue.json` から **未投稿枠を6件先まで** `posts.json` に自動追記 |
| 1 | `pipeline_resolve_post.py` で次の `post_date` と slug を決定 |
| 2 | HTML が無く topic-spec あり → `generate_diagram_from_spec.py` で生成・commit |
| 3 | `diagram-site` 同期・push |
| 4 | Pages 200 確認 → Discord（コラージュ付き） |
| 5 | `discord-post-state.json` 更新 |

**人がやること（新テーマ追加時のみ）**

1. `publish-html/` または `schedule/topic-specs/<slug>.json` を用意
2. `ops/diagram-publish-manifest.json` に slug を追加
3. `schedule/delivery-queue.json` の `items` 末尾に `{ id, slug, title, description }` を1行追加

`posts.json` の日付キーは **書かなくてよい**（cron が補充）。除外テーマは `delivery-config.json` の `excluded_slugs`。

- **cron**: 日・水・土 9:00 JST
- **手動**: `gh workflow run "図解 自動生成→配信" -f post_date=YYYY-MM-DD`

---

## 配信前ワークフロー（人が触るとき）

1. 新規: `topic-specs/<slug>.json` 作成（`_example.json` 参照）又は Cursor で `publish-html/` を直接改稿
2. `manifest` + `posts.json` を整合
3. push → Actions が残りを実行（ローカルだけなら `sync_diagram_site.sh`）

---

## 改稿チェックリスト（v2）

```
- [ ] topic-spec に "version": 2 と knowledge、publish-html は spec から生成（手書きしない）
- [ ] knowledge/topics/<slug>.md を作成・追記した
- [ ] 1 全体図だけで計算・処理の全体が分かる。例題の数字は1セットのみ
- [ ] 差がつく論点に「ルール → 数字 → こう間違える」がそろっている
- [ ] 引っかけ一覧の英語は実際の問題文に出る言い回し
- [ ] MC は初見の数字・英語・和訳トグル・誤答の作られ方つき。複合問題1問以上
- [ ] TBS の答え合わせが全問正解になる（ブラウザで確認）
- [ ] 例題・MC・TBS の数字を計算し直した
- [ ] スマホ幅（375px）で横スクロールが出ない
- [ ] Discord 用コラージュ（ops/screenshot_discord_collage.py）に全体図が入る
```

## 図解の改稿状況

v2 化の状況は `knowledge/index.md`（自動生成）を見る。

### 旧型時代の記録（manifest 全10件）

| slug | 7部+理論+品質 | source HTML |
|------|----------------|-------------|
| asset-group-relative-sales-value | 済 | `publish-html/asset-group-relative-sales-value.html` |
| warranty-liability | 済 | `publish-html/warranty-liability.html` |
| refinancing-current-liabilities | 済 | `publish-html/theme-refinancing-current-liabilities.html` |
| current-liabilities-classification | 済 | `publish-html/current-liabilities-classification.html` |
| treasury-stock-par-value | 済 | `publish-html/treasury-stock-par-value.html` |
| notes-payable-accrued-interest | 済 | `publish-html/notes-payable-accrued-interest.html` |
| involuntary-conversion-gain | 済 | `publish-html/involuntary-conversion-gain.html` |
| deferred-tax-asset-dta | 済 | `publish-html/income-taxes-dta.html` |
| inventory-lcm-reading-drill | 済 | `publish-html/inventory-lcm-reading-drill.html` |
| ppe-impairment-held-for-use | 済 | `publish-html/ppe-impairment-held-for-use.html` |

`posts.json` にキーがない slug（DTA・LCM・減損）は Discord 自動キュー対象外の方針を維持。

未改稿テーマを配信する前に、可能なら本スキルで HTML を更新してから出す。
