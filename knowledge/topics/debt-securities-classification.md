# debt-securities-classification（ASC 320 / ASC 326-20 / ASC 326-30）

- 公開URL：https://haitokutaishi-lgtm.github.io/diagram-site/topics/debt-securities-classification/
- FARテキスト：FAR Ch13 13-1〜13-4（分類・評価・売却）、信用損失、保有目的の変更。ローカルの FAR_Ch13_詳細ナレッジ.md を参照。

## 確かめた基準・出典

- ASC 320-10-25 / 35。HTM・AFS・トレーディングの分類と評価。AFS は公正価値、HTM は償却原価から引当金を控除して表示。 [FASB Debt Securities Implementation Guide](https://xbrl.fasb.org/ix/?doc=..%2Fimpdocs%2FDS2_TIG%2Fdebtsecurities.htm)
- ASC 326-20-30、326-30-35-2〜3、35-10。HTM の期待信用損失、AFS の信用損失引当金の上限と売却意思・売却必要性による直接切下げ。 [FASB ASU 2016-13](https://storage.fasb.org/ASU%202016-13.pdf)
- ASC 320-10-35-10A〜10B。HTM・AFS 間の振替と信用損失引当金の再評価。 [FASB ASU 2019-04](https://storage.fasb.org/ASU%202019-04.pdf)

## 決めたこと

- 冒頭は同一条件を3区分に当てはめ、期末の資産・損益・OCI を横並びにした。税効果を外し、信用損失が出る AFS と売却時の AOCI 取り崩しを分けて説明した。
- AFS の上限超過は初見の TBS で扱い、上限前の見積額・認識する引当金・OCI を個別に入力する。

## 受講生の反応

- 配信後に記録。

## 改訂履歴

- 2026-11-07 図解の復習シートと演習を新規作成。
