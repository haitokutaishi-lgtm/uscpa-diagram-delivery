// ============================================================
// 品質チェック（Quality Gate）— AUD 毎日問題
// 2026-10-07 追加。既存のコードは変更せず、このファイルを追加するだけで動く。
//
// やること（毎日 5:00 と 21:00 に自動実行）
//  1. 今日〜3日先の問題バンクを確認し、問題が無い日は新しく作る
//  2. まだ確認していない問題を、別のAIに「正解を見せずに解かせて」確認する
//     - 解いた答えが作問者の正解と一致するか
//     - 正解が1つに決まるか／計算に必要な条件が全部書いてあるか
//     - 解説・誤答の説明に誤りがないか
//  3. 不合格の問題は同じテーマで作り直して再確認（最大3回）
//  4. 当日5:00の時点で不合格のままの問題は配信から外す
//
// 設定（スクリプト プロパティ）
//  GROQ_API_KEY        既存。作問・確認に使う（無料）
//  ANTHROPIC_API_KEY（または Claude_key）  任意。あれば作問・確認に Claude を使う（精度が上がる。おすすめ）
//  COACH_WEBHOOK_URL   任意。不合格・作り直し失敗をコーチ用チャンネルに通知（無ければシステムログのみ）
//
// 問題バンクに2列追加して記録する：O列「品質チェック」（PASS / FAIL）・P列「チェック記録」
// 初回はメニュー「🛡 品質チェック」→「① 自動実行を設定」を1回だけ実行する
// ============================================================

// ─────────────────────────────────────────────
// 初回はこれを実行するだけ（エディタの「実行」で最初に選ばれる関数）
// 自動実行の設定 → 3日先までの確認・補充を1回まわす
// ─────────────────────────────────────────────
function QG_install() {
  QG_setupTriggers();
  var r = QG_run(false);
  Logger.log('品質チェック：' + r.summary + (r.timedOut ? '（時間切れ。もう一度 QG_install か QG_runNow を実行すると続きから）' : ''));
}

var QG = {
  SUBJECT: 'AUD',
  BANK: '問題バンク',
  SYSLOG: 'システムログ',
  COL_STATUS: 15,   // O列
  COL_NOTE: 16,     // P列
  DAYS_AHEAD: 3,
  MAX_TRY: 3,
  TIME_LIMIT_MS: 290 * 1000,
  CLAUDE_MODEL: 'claude-sonnet-5-5',
  GROQ_MODEL: 'openai/gpt-oss-120b',
  POSTS_URL: 'https://raw.githubusercontent.com/haitokutaishi-lgtm/uscpa-diagram-delivery/main/schedule/posts.json',
  SITE_URL: 'https://haitokutaishi-lgtm.github.io/diagram-site/topics/',
};

// テキスト（予備校教材）の範囲から選んだ出題テーマ。slug は図解配信と同じ（図解があれば解説にリンクを付ける）
var QG_TOPICS = [
  {
    "slug": "aud-opinion-types",
    "name": "監査意見の種類—限定・不適正・意見差控え",
    "std": "AU-C 705",
    "area": "report",
    "calc": false,
    "focus": ""
  },
  {
    "slug": "aud-report-paragraphs",
    "name": "監査報告書の追加区分—強調事項・その他の事項・継続企業",
    "std": "AU-C 706 / AU-C 570",
    "area": "report",
    "calc": false,
    "focus": ""
  },
  {
    "slug": "aud-risk-model",
    "name": "監査リスクモデル—発見リスクと実証手続",
    "std": "AU-C 200 / 315 / 330",
    "area": "risk",
    "calc": true,
    "focus": ""
  },
  {
    "slug": "aud-materiality",
    "name": "重要性—全体・手続実施上の重要性",
    "std": "AU-C 320",
    "area": "risk",
    "calc": true,
    "focus": ""
  },
  {
    "slug": "aud-fraud-risk",
    "name": "不正リスク—不正な財務報告と資産の横領",
    "std": "AU-C 240",
    "area": "risk",
    "calc": false,
    "focus": ""
  },
  {
    "slug": "aud-assertions-direction",
    "name": "アサーションと手続の向き",
    "std": "AU-C 315 / 500",
    "area": "evidence",
    "calc": false,
    "focus": ""
  },
  {
    "slug": "aud-audit-evidence",
    "name": "監査証拠の十分性と適切性",
    "std": "AU-C 500",
    "area": "evidence",
    "calc": false,
    "focus": ""
  },
  {
    "slug": "aud-ar-confirmation",
    "name": "売掛金の確認",
    "std": "AU-C 505",
    "area": "evidence",
    "calc": false,
    "focus": ""
  },
  {
    "slug": "aud-cash-kiting",
    "name": "現金の実証手続—銀行間振替表・カイティング",
    "std": "AU-C 500",
    "area": "evidence",
    "calc": false,
    "focus": ""
  },
  {
    "slug": "aud-inventory-observation",
    "name": "棚卸資産の実地棚卸の立会い",
    "std": "AU-C 501",
    "area": "evidence",
    "calc": false,
    "focus": ""
  },
  {
    "slug": "aud-unrecorded-liabilities",
    "name": "未記録負債の検索",
    "std": "AU-C 500",
    "area": "evidence",
    "calc": false,
    "focus": ""
  },
  {
    "slug": "aud-analytical-procedures",
    "name": "分析的手続",
    "std": "AU-C 520",
    "area": "evidence",
    "calc": true,
    "focus": ""
  },
  {
    "slug": "aud-attribute-sampling",
    "name": "属性サンプリング",
    "std": "AU-C 530",
    "area": "sampling",
    "calc": true,
    "focus": ""
  },
  {
    "slug": "aud-pps-sampling",
    "name": "金額単位サンプリング（PPS）",
    "std": "AU-C 530",
    "area": "sampling",
    "calc": true,
    "focus": ""
  },
  {
    "slug": "aud-control-deficiencies",
    "name": "内部統制の不備・重要な不備・重大な欠陥",
    "std": "AU-C 265",
    "area": "ic",
    "calc": false,
    "focus": ""
  },
  {
    "slug": "aud-coso-components",
    "name": "COSO の5つの構成要素",
    "std": "COSO 2013",
    "area": "ic",
    "calc": false,
    "focus": ""
  },
  {
    "slug": "aud-revenue-purchase-cycles",
    "name": "売上・購買サイクルの職務分掌と統制テスト",
    "std": "AU-C 315 / 330",
    "area": "ic",
    "calc": false,
    "focus": ""
  },
  {
    "slug": "aud-it-controls-caat",
    "name": "IT 全般統制・業務処理統制と CAAT",
    "std": "AU-C 315",
    "area": "ic",
    "calc": false,
    "focus": ""
  },
  {
    "slug": "aud-icfr-integrated",
    "name": "内部統制監査（統合監査）",
    "std": "PCAOB AS 2201",
    "area": "ic",
    "calc": false,
    "focus": ""
  },
  {
    "slug": "aud-subsequent-events",
    "name": "後発事象と監査報告書の日付",
    "std": "AU-C 560",
    "area": "completion",
    "calc": false,
    "focus": ""
  },
  {
    "slug": "aud-representation-letter",
    "name": "経営者確認書",
    "std": "AU-C 580",
    "area": "completion",
    "calc": false,
    "focus": ""
  },
  {
    "slug": "aud-engagement-acceptance",
    "name": "監査契約の締結と前任監査人とのコミュニケーション",
    "std": "AU-C 210 / 300",
    "area": "planning",
    "calc": false,
    "focus": ""
  },
  {
    "slug": "aud-group-audit",
    "name": "グループ監査—構成単位の監査人",
    "std": "AU-C 600",
    "area": "report",
    "calc": false,
    "focus": ""
  },
  {
    "slug": "aud-special-frameworks",
    "name": "特別目的の枠組み・単独の財務諸表",
    "std": "AU-C 800 / 805",
    "area": "report",
    "calc": false,
    "focus": ""
  },
  {
    "slug": "aud-specialists-lawyers",
    "name": "専門家・内部監査の利用、弁護士への質問、SOC 報告書",
    "std": "AU-C 620 / 610 / 501 / 402",
    "area": "evidence",
    "calc": false,
    "focus": ""
  },
  {
    "slug": "aud-review-compilation",
    "name": "レビュー・調製・作成業務の違い",
    "std": "AR-C 70 / 80 / 90",
    "area": "other",
    "calc": false,
    "focus": ""
  },
  {
    "slug": "aud-attestation-types",
    "name": "証明業務—検証・レビュー・合意手続",
    "std": "AT-C 205 / 210 / 215",
    "area": "other",
    "calc": false,
    "focus": ""
  },
  {
    "slug": "aud-independence",
    "name": "独立性—財務的利害・近親者・貸付",
    "std": "AICPA Code of Professional Conduct",
    "area": "ethics",
    "calc": false,
    "focus": ""
  },
  {
    "slug": "aud-gas-single-audit",
    "name": "政府監査基準（GAS）と単一監査",
    "std": "Government Auditing Standards / Uniform Guidance",
    "area": "other",
    "calc": false,
    "focus": ""
  },
  {
    "slug": "aud-quality-management",
    "name": "品質マネジメントと PCAOB・SEC の規制",
    "std": "SQMS / PCAOB",
    "area": "ethics",
    "calc": false,
    "focus": ""
  }
];

// 実際に起きた不良問題（作問・確認の両方に「これをやらない」例として渡す）
var QG_BAD_EXAMPLES = [
  "「most likely」「primary purpose」と聞きながら、判断の手がかりが問題文になく、複数の選択肢が正しいと読めた",
  "AICPA と PCAOB で扱いが違う論点なのに、どちらの基準で答えるかを書かなかった",
  "正解がほぼ毎回 A に偏っていた（答えを見なくても A を選べば当たる）",
  "実在しない基準番号をトピックに書いた",
  "変動対価で期待値法か最頻値法かを書かずに、期待値の答えだけを正解にした（結果が3通りなら最頻値法も成り立つ）",
  "リースのフリーレントを「インセンティブ」と呼び、「無償期間の支払の現在価値だけ減らす」という不正確な選択肢を正解にした。別の選択肢も正しいと読めた",
  "転換社債の希薄化EPSで、税引後の支払利息を分子に足し戻さず、分母に株数を足すだけで正解を作った（利率・税率も書いていない）"
];

// ─────────────────────────────────────────────
// メニュー（既存の onOpen とは別。スプレッドシートを開くと追加される）
// ─────────────────────────────────────────────
function QG_onOpenMenu() {
  try { QG_buildMenu(); } catch (e) {}   // エディタから実行したときは UI が無いので何もしない
}
function QG_buildMenu() {
  SpreadsheetApp.getUi()
    .createMenu('🛡 品質チェック')
    .addItem('① 自動実行を設定（初回のみ）', 'QG_setupTriggers')
    .addItem('② 今すぐ確認・補充を実行', 'QG_runNow')
    .addItem('③ 設定の確認', 'QG_checkConfig')
    .addToUi();
}

function QG_setupTriggers() {
  ScriptApp.getProjectTriggers().forEach(function(t) {
    var fn = t.getHandlerFunction();
    // 旧来の週次一括生成は確認を通らないので止める（品質チェックが毎日補充する）
    if (fn === 'QG_runScheduled' || fn === 'generateNextWeekQuestions' || fn === 'QG_onOpenMenu') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('QG_runScheduled').timeBased().everyDays(1).atHour(5).create();
  ScriptApp.newTrigger('QG_runScheduled').timeBased().everyDays(1).atHour(21).create();
  ScriptApp.newTrigger('QG_onOpenMenu').forSpreadsheet(SpreadsheetApp.getActive()).onOpen().create();
  QG_log('品質チェックの自動実行を設定（毎日5時・21時）。週次一括生成のトリガーは解除');
  QG_alert('✅ 設定しました\n\n毎日5時と21時に、3日先までの問題を確認・補充します。\n（週1回の一括生成トリガーは解除しました）\n\n続けて「② 今すぐ確認・補充を実行」を押すと、今ある問題の確認を始めます。');
}

function QG_checkConfig() {
  var p = PropertiesService.getScriptProperties();
  var msg = 'GROQ_API_KEY：' + (p.getProperty('GROQ_API_KEY') ? '設定済み' : '未設定') + '\n' +
    'Claude のキー：' + ((p.getProperty('ANTHROPIC_API_KEY') || p.getProperty('Claude_key')) ? '設定済み（Claude で作問・確認）' : '未設定（Groq で作問・確認）') + '\n' +
    'COACH_WEBHOOK_URL：' + (p.getProperty('COACH_WEBHOOK_URL') ? '設定済み' : '未設定（通知はシステムログのみ）') + '\n' +
    '出題テーマ：' + QG_TOPICS.length + '件';
  QG_alert(msg);
}

function QG_runNow() {
  var r = QG_run(false);
  QG_alert('品質チェック完了\n\n' + r.summary + (r.timedOut ? '\n\n⏱ 時間切れで途中まで。もう一度実行すると続きから確認します。' : ''));
}

function QG_runScheduled() {
  var hour = Number(Utilities.formatDate(new Date(), 'Asia/Tokyo', 'H'));
  QG_run(hour < 6);   // 朝の実行では、今日の不合格問題を配信から外す
}

// ─────────────────────────────────────────────
// 本体
// ─────────────────────────────────────────────
function QG_run(finalForToday) {
  var started = Date.now();
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(QG.BANK);
  QG_ensureHeader(sheet);
  var stats = { checked: 0, passed: 0, regenerated: 0, generated: 0, failed: 0, removed: 0 };
  var timedOut = false;
  var diagrams = QG_recentDiagrams();

  for (var d = 0; d <= QG.DAYS_AHEAD; d++) {
    var dateStr = QG_dateStr(QG_addDays(new Date(), d));
    var rows = QG_rowsForDate(sheet, dateStr);

    // 問題が無い日は3問を新しく作る
    if (rows.length === 0) {
      if (d === 0 && !finalForToday) continue;   // 朝の配信が終わった後に今日の分を作ると、夕方に「答えだけ」が流れてしまう
      var topics = QG_pickTopics(sheet, dateStr, 3, diagrams);
      for (var i = 0; i < topics.length; i++) {
        if (Date.now() - started > QG.TIME_LIMIT_MS) { timedOut = true; break; }
        var made;
        try { made = QG_makeVerified(topics[i], i, null); } catch (e) { QG_log('作問でエラー（次回に回す）：' + e.message); continue; }
        QG_appendRow(sheet, dateStr, i + 1, made);
        stats.generated++;
        if (made.status !== 'PASS') stats.failed++;
      }
      if (timedOut) break;
      continue;
    }

    for (var j = 0; j < rows.length; j++) {
      if (Date.now() - started > QG.TIME_LIMIT_MS) { timedOut = true; break; }
      var row = rows[j];
      if (row.sentMorning) continue;
      if (row.status === 'PASS') continue;
      if (row.status === 'FAIL' && !(finalForToday && d === 0) && row.note.indexOf('作り直し済') >= 0) continue;

      stats.checked++;
      var q = row.q;
      var v;
      try { v = QG_verify(q); } catch (e) { QG_log('確認でエラー（次回に回す）：' + dateStr + ' Q' + q.qNum + ' ' + e.message); stats.checked--; continue; }
      if (v.pass) {
        QG_writeStatus(sheet, row.rowIndex, 'PASS', QG_noteOf(v));
        stats.passed++;
        continue;
      }
      // 不合格 → 同じテーマで作り直す
      var topic = QG_topicForRow(q.topic, diagrams);
      var remade;
      try { remade = QG_makeVerified(topic, j, v); } catch (e) { QG_log('作り直しでエラー（次回に回す）：' + e.message); continue; }
      if (remade.status === 'PASS') {
        QG_overwriteRow(sheet, row.rowIndex, remade);
        stats.regenerated++;
      } else if (finalForToday && d === 0) {
        sheet.deleteRow(row.rowIndex);
        rows = QG_rowsForDate(sheet, dateStr); j = -1;   // 行番号がずれるので読み直す
        stats.removed++;
        QG_notify('⚠️ ' + QG.SUBJECT + ' ' + dateStr + ' の問題を1問、配信から外しました（確認に通らず作り直しも失敗）\nトピック：' + q.topic + '\n理由：' + QG_noteOf(v));
      } else {
        QG_writeStatus(sheet, row.rowIndex, 'FAIL', '作り直し済・不合格：' + QG_noteOf(v));
        stats.failed++;
        QG_notify('⚠️ ' + QG.SUBJECT + ' ' + dateStr + ' Q' + q.qNum + ' が確認に通りません（作り直しも不合格）。問題バンクを確認してください。\n理由：' + QG_noteOf(v));
      }
    }
    if (timedOut) break;
  }

  var summary = '確認 ' + stats.checked + '問（合格 ' + stats.passed + '・作り直して合格 ' + stats.regenerated + '）／新規作成 ' + stats.generated + '問／不合格のまま ' + stats.failed + '問／配信から除外 ' + stats.removed + '問';
  QG_log('品質チェック：' + summary + (timedOut ? '（時間切れで中断）' : ''));
  return { summary: summary, timedOut: timedOut };
}

// テーマを1つ受け取り、作問 → 確認 → 不合格なら理由を渡して作り直し（最大 MAX_TRY 回）
function QG_makeVerified(topic, index, prevVerdict) {
  var feedback = prevVerdict ? QG_noteOf(prevVerdict) : '';
  var last = null;
  for (var t = 1; t <= QG.MAX_TRY; t++) {
    var q;
    try {
      q = QG_generate(topic, index, feedback);
    } catch (e) {
      feedback = '前回は JSON が壊れていた：' + e.message;
      continue;
    }
    var v;
    try { v = QG_verify(q); } catch (e) { feedback = ''; continue; }
    last = { q: q, verdict: v };
    if (v.pass) {
      QG_attachDiagramLink(q, topic);
      return { q: q, status: 'PASS', note: '作り直し' + t + '回目で合格。' + QG_noteOf(v) };
    }
    feedback = QG_noteOf(v);
  }
  if (last) {
    QG_attachDiagramLink(last.q, topic);
    return { q: last.q, status: 'FAIL', note: '作り直し済・不合格：' + QG_noteOf(last.verdict) };
  }
  throw new Error('作問に ' + QG.MAX_TRY + ' 回失敗：' + topic.name);
}

// ─────────────────────────────────────────────
// 作問
// ─────────────────────────────────────────────
function QG_generate(topic, index, feedback) {
  var type = topic.calc ? '計算問題' : '暗記問題';
  var target = 'ABCD'.charAt(Math.floor(Math.random() * 4));   // 正解の位置を毎回ランダムにする（以前は A に偏っていた）
  var prompt =
    'あなたは USCPA 試験（' + QG.SUBJECT + '）の作問者です。次のテーマで、本番レベルの4択問題を1問だけ作ってください。\n\n' +
    '## テーマ\n' + topic.name + '（基準：' + topic.std + '）\n' +
    (topic.focus ? '狙う論点：' + topic.focus + '\n' : '') +
    '種別：' + type + '\n\n' +
    '## 必ず守ること\n' +
    '1. 問題文だけで正解が1つに決まること。計算に必要な数字・利率・税率・期間・日付をすべて書く\n' +
    '2. 会計方針や見積方法に選択肢がある論点（期待値法か最頻値法か、間接法か直接法か、など）は、どれを使うかを問題文に書く\n' +
    '3. 誤答の選択肢3つは、それぞれ「受験生が実際にやる典型的な間違い1つ」から作る。wrongAnswers には、その選択肢がどの間違いから出る数字・記述かを書く\n' +
    '4. 単純な定義の確認だけで終わらせない。2段階以上の判断や計算を入れる\n' +
    '5. 計算問題は、途中も答えも割り切れる数字にする。steps に全部の計算を書き、最後にもう一度検算する\n' +
    '6. 現行の基準で書く（ASC 842・ASC 326・ASC 606 など。ASC 840 などの旧基準は使わない）。基準番号に自信がなければ書かない\n' +
    '7. topic は「' + topic.name + '」をそのまま使う\n' +
    '8. 問題文・選択肢は自然な英語。解説（explanation・richData）は日本語\n' +
    '9. 正解は必ず選択肢 ' + target + ' に置く（correctAnswer は ' + target + '）\n\n' +
    '## やってはいけない例（実際に配信して不良だった問題）\n' + QG_BAD_EXAMPLES.map(function(b) { return '- ' + b; }).join('\n') + '\n' +
    (feedback ? '\n## 前回の問題は確認で不合格だった。理由を直して作り直すこと\n' + feedback + '\n' : '') +
    '\n## 出力（JSONのみ）\n' +
    '{"topic":"...","questionType":"' + type + '","text":"English stem","choiceA":"...","choiceB":"...","choiceC":"...","choiceD":"...","correctAnswer":"A-Dのどれか",' +
    '"explanation":"正解X：〜（日本語・60字以内）","richData":{"questionType":"' + type + '","conceptTitle":"...","conceptBody":"日本語で論点の説明（400字以内）",' +
    '"formula":"計算式（計算問題のみ。暗記問題は空文字）","diagram":null,"steps":"①…②…③…（数値代入）","wrongAnswers":"**A)…**：…\\n**B)…**：…\\n**C)…**：…\\n**D)…**：…","memoryTip":"**試験ポイント💡**…\\n**ひっかけ対策⚠️**…"}}';
  var raw = QG_llm(prompt, 0.5, 5000);
  var q = QG_parseJSON(raw);
  if (!q || !q.text || !q.choiceA || !q.correctAnswer) throw new Error('作問の JSON を読めない');
  q.correctAnswer = String(q.correctAnswer).trim().charAt(0).toUpperCase();
  q.topic = topic.name;
  q.qNum = index + 1;
  return q;
}

// ─────────────────────────────────────────────
// 確認（2段階：①正解を見せずに解く ②正解・解説を見せて誤りを探す）
// ─────────────────────────────────────────────
function QG_verify(q) {
  var stem = q.text + '\n\nA) ' + q.choiceA + '\nB) ' + q.choiceB + '\nC) ' + q.choiceC + '\nD) ' + q.choiceD;
  var solvePrompt =
    'あなたは USCPA ' + QG.SUBJECT + ' の採点者です。次の4択問題を、現行の基準（U.S. GAAP / GAAS / PCAOB）で解いてください。作問者の正解は見せません。\n\n' +
    stem + '\n\n' +
    '次を確認して JSON だけを返してください。\n' +
    '- solvedAnswer：あなたが選ぶ答え（A〜D）。計算は途中式を workings に書く\n' +
    '- uniqueAnswer：問題文の条件だけで正解が1つに決まるか（true/false）\n' +
    '- missingInfo：正解を出すのに足りない条件（利率・税率・方法の指定など）。無ければ []\n' +
    '- otherDefensible：正解と言える別の選択肢があれば、その記号と理由。無ければ []\n' +
    '- outdated：旧基準や試験範囲外の内容を前提にしていれば true\n\n' +
    '{"solvedAnswer":"A","workings":"...","uniqueAnswer":true,"missingInfo":[],"otherDefensible":[],"outdated":false}';
  var s = QG_parseJSON(QG_llm(solvePrompt, 0, 3000)) || {};
  var solved = String(s.solvedAnswer || '').trim().charAt(0).toUpperCase();
  var reasons = [];
  if (solved !== q.correctAnswer) reasons.push('別のAIが解くと ' + (solved || '?') + '（作問の正解は ' + q.correctAnswer + '）');
  if (s.uniqueAnswer === false) reasons.push('正解が1つに決まらない');
  (s.missingInfo || []).forEach(function(m) { reasons.push('条件不足：' + m); });
  (s.otherDefensible || []).forEach(function(m) { reasons.push('別解：' + (typeof m === 'string' ? m : JSON.stringify(m))); });
  if (s.outdated === true) reasons.push('旧基準・範囲外の可能性');

  if (reasons.length === 0) {
    var rich = q.richData || {};
    var reviewPrompt =
      'USCPA ' + QG.SUBJECT + ' の問題の解説を校閲してください。事実・計算・基準の誤りだけを指摘し、好みの問題は指摘しないこと。\n\n' +
      stem + '\n\n作問者の正解：' + q.correctAnswer + '\n解説：' + (q.explanation || '') + '\n' +
      '計算式：' + (rich.formula || '') + '\n解き方：' + (rich.steps || '') + '\n各選択肢：' + (rich.wrongAnswers || '') + '\n覚え方：' + (rich.memoryTip || '') + '\n\n' +
      'JSON だけを返す：{"errors":["誤りの内容（無ければ空配列）"]}';
    var r = QG_parseJSON(QG_llm(reviewPrompt, 0, 2000)) || {};
    (r.errors || []).forEach(function(e) { if (e) reasons.push('解説の誤り：' + e); });
  }
  return { pass: reasons.length === 0, solved: solved, reasons: reasons };
}

function QG_noteOf(v) {
  if (!v) return '';
  var by = QG_ENGINE ? '[' + QG_ENGINE + '] ' : '';
  return by + (v.pass ? '確認OK（別のAIの答えが一致）' : v.reasons.join(' / ').slice(0, 450));
}

// ─────────────────────────────────────────────
// テーマ選び（直近30日に出したテーマを避け、直近7日の図解テーマを1問入れる）
// ─────────────────────────────────────────────
function QG_pickTopics(sheet, dateStr, n, diagrams) {
  var recent = QG_recentTopicNames(sheet, dateStr, 30);
  var pool = QG_TOPICS.filter(function(t) { return recent.indexOf(t.name) < 0; });
  if (pool.length < n) pool = QG_TOPICS.slice();
  var picked = [];
  var fromDiagram = diagrams.filter(function(dg) {
    return pool.some(function(t) { return t.slug === dg.slug; });
  });
  if (fromDiagram.length > 0) {
    var dg = fromDiagram[Math.floor(Math.random() * fromDiagram.length)];
    picked.push(pool.filter(function(t) { return t.slug === dg.slug; })[0]);
  }
  QG_shuffle(pool);
  for (var i = 0; i < pool.length && picked.length < n; i++) {
    if (picked.indexOf(pool[i]) < 0 && picked.every(function(p) { return p.area !== pool[i].area; })) picked.push(pool[i]);
  }
  for (var k = 0; k < pool.length && picked.length < n; k++) if (picked.indexOf(pool[k]) < 0) picked.push(pool[k]);
  return picked;
}

function QG_topicForRow(topicText, diagrams) {
  var hit = QG_TOPICS.filter(function(t) { return t.name === topicText; })[0];
  if (hit) return hit;
  return { name: topicText, std: '現行の基準', area: 'other', calc: /計算|EPS|Lease|Bond|Tax|Depreciation|Sampling/i.test(topicText), slug: '' };
}

function QG_recentTopicNames(sheet, dateStr, days) {
  var data = sheet.getDataRange().getValues();
  var target = new Date(dateStr), cutoff = QG_addDays(new Date(dateStr), -days), out = [];
  for (var i = 1; i < data.length; i++) {
    var d = data[i][0] instanceof Date ? data[i][0] : new Date(data[i][0]);
    if (d >= cutoff && d <= target && data[i][2]) out.push(String(data[i][2]));
  }
  return out;
}

// 図解配信（posts.json）から、この科目の直近7日〜3日先の図解を取る
function QG_recentDiagrams() {
  try {
    var res = UrlFetchApp.fetch(QG.POSTS_URL, { muteHttpExceptions: true });
    if (res.getResponseCode() !== 200) return [];
    var posts = JSON.parse(res.getContentText());
    var from = QG_dateStr(QG_addDays(new Date(), -7)), to = QG_dateStr(QG_addDays(new Date(), 3));
    return Object.keys(posts).filter(function(k) {
      var p = posts[k];
      return /^\d{4}-\d{2}-\d{2}$/.test(k) && k >= from && k <= to && p && (p.subject || 'FAR') === QG.SUBJECT;
    }).map(function(k) { return { date: k, slug: posts[k].slug }; });
  } catch (e) {
    return [];
  }
}

function QG_attachDiagramLink(q, topic) {
  if (!topic || !topic.slug || !q.richData) return;
  var link = '\n\n📘 図解で復習：' + QG.SITE_URL + topic.slug + '/';
  q.richData.memoryTip = String(q.richData.memoryTip || '').slice(0, 400 - link.length) + link;
}

// ─────────────────────────────────────────────
// 問題バンクの読み書き
// ─────────────────────────────────────────────
function QG_ensureHeader(sheet) {
  if (sheet.getRange(1, QG.COL_STATUS).getValue() !== '品質チェック') {
    sheet.getRange(1, QG.COL_STATUS, 1, 2).setValues([['品質チェック', 'チェック記録']]);
  }
}

function QG_rowsForDate(sheet, dateStr) {
  var data = sheet.getDataRange().getValues();
  var out = [];
  for (var i = 1; i < data.length; i++) {
    var r = data[i];
    var rowDate = r[0] instanceof Date ? QG_dateStr(r[0]) : String(r[0]).trim();
    if (rowDate !== dateStr) continue;
    var rich = null;
    try { if (r[13]) rich = JSON.parse(r[13]); } catch (e) {}
    out.push({
      rowIndex: i + 1,
      sentMorning: String(r[11]) === '✅' || r[11] === true || String(r[11]).toUpperCase() === 'TRUE',
      status: String(r[QG.COL_STATUS - 1] || ''),
      note: String(r[QG.COL_NOTE - 1] || ''),
      q: {
        qNum: Number(r[1]), topic: String(r[2]), text: String(r[3]),
        choiceA: String(r[4]), choiceB: String(r[5]), choiceC: String(r[6]), choiceD: String(r[7]),
        correctAnswer: String(r[8]).trim().toUpperCase(), explanation: String(r[9]), richData: rich,
      },
    });
  }
  return out;
}

function QG_rowValues(dateStr, qNum, made) {
  var q = made.q, rich = '';
  try { rich = q.richData ? JSON.stringify(q.richData) : ''; } catch (e) {}
  return [dateStr, qNum, q.topic, q.text, q.choiceA, q.choiceB, q.choiceC, q.choiceD, q.correctAnswer, q.explanation, '✅', 'FALSE', 'FALSE', rich, made.status, made.note];
}

function QG_appendRow(sheet, dateStr, qNum, made) {
  sheet.appendRow(QG_rowValues(dateStr, qNum, made));
}

function QG_overwriteRow(sheet, rowIndex, made) {
  var cur = sheet.getRange(rowIndex, 1, 1, 2).getValues()[0];
  var dateStr = cur[0] instanceof Date ? QG_dateStr(cur[0]) : String(cur[0]);
  var vals = QG_rowValues(dateStr, Number(cur[1]), made);
  vals[11] = sheet.getRange(rowIndex, 12).getValue();
  vals[12] = sheet.getRange(rowIndex, 13).getValue();
  sheet.getRange(rowIndex, 1, 1, vals.length).setValues([vals]);
}

function QG_writeStatus(sheet, rowIndex, status, note) {
  sheet.getRange(rowIndex, QG.COL_STATUS, 1, 2).setValues([[status, String(note).slice(0, 500)]]);
}

// ─────────────────────────────────────────────
// AI 呼び出し（Claude があれば Claude、無ければ Groq）
// ─────────────────────────────────────────────
var QG_ENGINE = '';   // 直近の呼び出しに使ったAI（記録用）
function QG_llm(prompt, temperature, maxTokens) {
  var p = PropertiesService.getScriptProperties();
  var claudeKey = p.getProperty('ANTHROPIC_API_KEY') || p.getProperty('Claude_key');   // どちらの名前で登録しても使う
  if (claudeKey) {
    var res = UrlFetchApp.fetch('https://api.anthropic.com/v1/messages', {
      method: 'post',
      headers: { 'x-api-key': claudeKey, 'anthropic-version': '2023-06-01', 'content-type': 'application/json' },
      payload: JSON.stringify({ model: QG.CLAUDE_MODEL, max_tokens: maxTokens, temperature: temperature, messages: [{ role: 'user', content: prompt }] }),
      muteHttpExceptions: true,
    });
    var data = JSON.parse(res.getContentText());
    if (data && data.content && data.content[0]) QG_ENGINE = 'Claude';
    if (data && data.content && data.content[0]) return data.content.map(function(c) { return c.text || ''; }).join('');
    QG_log('Claude API エラー（Groq に切り替え）：' + res.getContentText().slice(0, 200));
  }
  var key = p.getProperty('GROQ_API_KEY');
  if (!key) throw new Error('GROQ_API_KEY も ANTHROPIC_API_KEY も未設定');
  QG_ENGINE = 'Groq';
  for (var attempt = 1; attempt <= 4; attempt++) {
    var r2 = UrlFetchApp.fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'post',
      headers: { 'Authorization': 'Bearer ' + key, 'content-type': 'application/json' },
      payload: JSON.stringify({ model: QG.GROQ_MODEL, messages: [{ role: 'user', content: prompt }], max_tokens: maxTokens, temperature: temperature }),
      muteHttpExceptions: true,
    });
    if (r2.getResponseCode() === 429 && attempt < 4) { Utilities.sleep(20000 * attempt); continue; }   // 無料枠の1分あたり上限。待って再試行
    var d2 = JSON.parse(r2.getContentText());
    if (!d2.choices || !d2.choices[0]) throw new Error('Groq API エラー：' + r2.getContentText().slice(0, 200));
    return d2.choices[0].message.content;
  }
}

function QG_parseJSON(raw) {
  if (!raw) return null;
  var m = String(raw).match(/```(?:json)?\s*([\s\S]*?)```/);
  var s = m ? m[1] : String(raw);
  var a = s.indexOf('{'), b = s.lastIndexOf('}');
  if (a < 0 || b < 0) return null;
  s = s.slice(a, b + 1);
  try { return JSON.parse(s); } catch (e) {}
  try { return JSON.parse(s.replace(/[\u0000-\u001f]/g, function(c) { return c === '\n' ? '\\n' : ' '; })); } catch (e2) { return null; }
}

// ─────────────────────────────────────────────
// 小物
// ─────────────────────────────────────────────
function QG_notify(text) {
  QG_log(text);
  var url = PropertiesService.getScriptProperties().getProperty('COACH_WEBHOOK_URL');
  if (!url) return;
  UrlFetchApp.fetch(url, { method: 'post', contentType: 'application/json', payload: JSON.stringify({ content: text.slice(0, 1900) }), muteHttpExceptions: true });
}

function QG_log(msg) {
  try { SpreadsheetApp.getActiveSpreadsheet().getSheetByName(QG.SYSLOG).appendRow([new Date().toLocaleString('ja-JP'), '[品質チェック] ' + msg]); } catch (e) {}
  Logger.log(msg);
}

function QG_alert(msg) {
  try { SpreadsheetApp.getUi().alert(msg); } catch (e) { Logger.log(msg); }   // エディタから実行したときはログに出す
}
function QG_dateStr(d) { return Utilities.formatDate(d, 'Asia/Tokyo', 'yyyy-MM-dd'); }
function QG_addDays(d, n) { var x = new Date(d.getTime()); x.setDate(x.getDate() + n); return x; }
function QG_shuffle(a) { for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; } return a; }
