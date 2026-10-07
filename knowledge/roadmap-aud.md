# AUD 図解ロードマップ

AUDテキスト（Ch1〜20）から、試験で問われやすく図にすると判断が速くなる論点を選んだ配信順。2026-10-07 作成。

- 配信は**火・金**（週2本。FAR の水・土と重ならない）。`schedule/delivery-queue-aud.json` に同じ順で並べてあり、v2 の topic-spec ができたものから自動でスケジュールされる。
- 2026-10-07 にユーザーが1本目を確認し、10/9（金）から配信開始。
- 投稿先：FAR と同じチャンネル（ユーザー決定 2026-10-07）。
- 素材：`07_ナレッジ/ナレッジ/予備校の教材/AUD論点まとめ/AUD論点まとめ.md`（341 Unit）、過去問 `AUD過去問/`（RQ2025・2026 の MC・TBS）、出題傾向 `AUD_MC出題傾向まとめ.md`。
- **注意**：`AUD_詳細性と網羅性の確認結果.md` で誤要約が見つかった Unit（16-7 レビューの保証水準、19-7 独立性の近親者・借入の例外）と、設例の数字が欠けている Unit（6-23、7-2、7-7・7-8 など）は、録画の原資料で確かめてから使う。
- 章は内部の照合用（図解・投稿には書かない）。

## 配信順

| 順 | 論点 | 章 | 優先度 | メモ | slug |
|---|---|---|---|---|---|
| 1 | 監査意見の種類—限定・不適正・意見差控えの判定 | Ch4 | A | 作成済み | `aud-opinion-types` |
| 2 | 監査リスクモデル—固有・統制・発見リスクと実証手続の量 | Ch2 | A |  | `aud-risk-model` |
| 3 | アサーションと手続の向き—実在性は帳簿から、網羅性は証憑から | Ch2・7 | A |  | `aud-assertions-direction` |
| 4 | 属性サンプリング—逸脱率の上限とサンプル数を動かす要因 | Ch18 | A |  | `aud-attribute-sampling` |
| 5 | 監査報告書の追加区分—強調事項・その他の事項・継続企業・KAM/CAM | Ch3 | A |  | `aud-report-paragraphs` |
| 6 | 内部統制の不備—不備・重要な不備・重大な欠陥と伝達先 | Ch7 | A |  | `aud-control-deficiencies` |
| 7 | 売掛金の確認—積極・消極、未回答への対応、ラッピング | Ch9 | A |  | `aud-ar-confirmation` |
| 8 | 重要性—全体・手続実施上の重要性・明らかに僅少 | Ch2 | A |  | `aud-materiality` |
| 9 | 内部統制監査—トップダウン・アプローチと重大な欠陥があるときの意見 | Ch10 | A |  | `aud-icfr-integrated` |
| 10 | レビュー・調製・作成業務の違い（保証水準と報告書） | Ch15 | A |  | `aud-review-compilation` |
| 11 | 金額単位サンプリング（PPS）—サンプル間隔と虚偽表示の推定 | Ch18 | A |  | `aud-pps-sampling` |
| 12 | 後発事象と監査手続—報告書の日付と二重日付 | Ch11 | A |  | `aud-subsequent-events` |
| 13 | 不正リスク—不正な財務報告と資産の横領、不正リスク要因 | Ch2 | B |  | `aud-fraud-risk` |
| 14 | 売上・購買サイクルの職務分掌と統制テスト | Ch7 | B |  | `aud-revenue-purchase-cycles` |
| 15 | 現金の実証手続—銀行間振替表・カイティング・銀行確認 | Ch9 | B |  | `aud-cash-kiting` |
| 16 | 証明業務—検証・レビュー・合意手続の比較 | Ch16 | B | 16-7 に誤要約あり。録画で確認してから作る | `aud-attestation-types` |
| 17 | 監査契約の締結—前任監査人とのコミュニケーションと契約書 | Ch5 | B |  | `aud-engagement-acceptance` |
| 18 | 独立性—直接・重要な間接的財務利害、近親者、貸付 | Ch19 | B | 19-7 に誤要約あり。録画で確認してから作る | `aud-independence` |
| 19 | 棚卸資産の実証手続—実地棚卸の立会い | Ch9 | B |  | `aud-inventory-observation` |
| 20 | 未記録負債の検索 | Ch9 | B |  | `aud-unrecorded-liabilities` |
| 21 | 経営者確認書とガバナンスに責任を負う者とのコミュニケーション | Ch11 | B |  | `aud-representation-letter` |
| 22 | COSO の5つの構成要素と17原則 | Ch6 | B |  | `aud-coso-components` |
| 23 | IT 全般統制・業務処理統制とコンピュータ利用監査技法 | Ch17 | B |  | `aud-it-controls-caat` |
| 24 | 分析的手続—計画・実証・全体の3段階とデータ分析 | Ch8・20 | B |  | `aud-analytical-procedures` |
| 25 | グループ監査—構成単位の監査人に言及する／しない | Ch4 | B |  | `aud-group-audit` |
| 26 | 専門家・内部監査の利用、弁護士への質問、SOC 報告書 | Ch12 | B |  | `aud-specialists-lawyers` |
| 27 | 監査証拠の十分性と適切性—証拠の信頼性の順番 | Ch8 | B |  | `aud-audit-evidence` |
| 28 | 特別目的の枠組み・単独の財務諸表・要約財務諸表の報告 | Ch4 | B |  | `aud-special-frameworks` |
| 29 | 政府監査基準（GAS）と単一監査 | Ch13 | B |  | `aud-gas-single-audit` |
| 30 | 監査で見つけた虚偽表示の修正（棚卸・収益・偶発損失） | Ch14 | C |  | `aud-substantive-misstatements` |
| 31 | 比較財務諸表の報告—前任監査人がいる場合 | Ch15・4 | C |  | `aud-comparative-reports` |
| 32 | 予測・見積財務情報の証明業務 | Ch16 | C |  | `aud-prospective-info` |
| 33 | 報告書発行後に見つかった手続の欠落・事実 | Ch11 | C |  | `aud-omitted-procedures` |
| 34 | 品質マネジメントと企業改革法・PCAOB・SEC の規制 | Ch10・19 | C |  | `aud-quality-management` |

## 外したもの

- 経済学（Ch21〜23）：現行の AUD 試験範囲ではない（教材に残っている旧範囲）
- 限定報告業務（Ch4 参考）：テキスト上も試験範囲外

## AUD の図解の作り方（FAR との違い）

- 全体図は T勘定ではなく**判定表（`matrix`）と判定の流れ（`flow`）**が中心。
- 「仕訳一覧」の代わりに「報告書の決まり文句」「手続とアサーションの対応」などの表を置く。
- TBS は数字の入力ではなく**選択式**（`tbs` の行に `options` と `ans`、ブロックに `select: true`）。サンプリング・分析的手続など計算がある論点は数字入力も使う。
- spec の先頭に `"subject": "AUD"`、`knowledge` は `aud_text`、`meta.badge` は「AUD 復習シート｜…」。
