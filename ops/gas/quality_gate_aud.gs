// ============================================================
// 毎日問題の補充（ストックから選ぶ）— AUD
// 2026-10-08 版。AI は呼ばない（費用ゼロ）。既存のコードは変更せず、このファイルを置くだけで動く。
//
// 問題のストック：図解（復習シート）の確認問題と、週1回まとめて作って検算した追加問題。
//   https://raw.githubusercontent.com/haitokutaishi-lgtm/uscpa-diagram-delivery/main/schedule/daily-question-bank.json
// やること（毎日 5:00 と 21:00 に自動実行）
//   今日〜3日先で問題が入っていない日に、ストックから1日2問を選んで問題バンクに入れる
//   - 2問は別のテーマから選ぶ
//   - 直近28日に出した問題は避ける（ストックが足りないときは一番前に出したものから再出題）
//   - 朝の配信が終わった後は、今日の分は入れない（夕方に答えだけ流れるのを防ぐ）
// 問題バンクの O列「品質チェック」に PASS、P列に「出典：<問題ID>」を書く（再出題の管理に使う）
// 初回は QG_install を1回実行する（先頭の関数なのでエディタの「実行」でそのまま動く）
// ============================================================

function QG_install() {
  QG_setupTriggers();
  var r = QG_run(false);
  Logger.log('毎日問題の補充：' + r.summary);
}

var QG = {
  SUBJECT: 'AUD',
  PER_DAY: 2,
  DAYS_AHEAD: 3,
  COOLDOWN_DAYS: 28,
  LOW_STOCK_DAYS: 7,
  BANK: '問題バンク',
  SYSLOG: 'システムログ',
  COL_STATUS: 15,   // O列
  COL_NOTE: 16,     // P列
  STOCK_URL: 'https://raw.githubusercontent.com/haitokutaishi-lgtm/uscpa-diagram-delivery/main/schedule/daily-question-bank.json',
};

function QG_onOpenMenu() {
  try { QG_buildMenu(); } catch (e) {}   // エディタから実行したときは UI が無いので何もしない
}
function QG_buildMenu() {
  SpreadsheetApp.getUi()
    .createMenu('🛡 毎日問題の補充')
    .addItem('① 自動実行を設定（初回のみ）', 'QG_setupTriggers')
    .addItem('② 今すぐ補充', 'QG_runNow')
    .addItem('③ ストックの残りを確認', 'QG_checkConfig')
    .addToUi();
}

function QG_setupTriggers() {
  ScriptApp.getProjectTriggers().forEach(function(t) {
    var fn = t.getHandlerFunction();
    // 旧来の AI 一括生成は止める（ストックから補充する）
    if (fn === 'QG_runScheduled' || fn === 'generateNextWeekQuestions' || fn === 'QG_onOpenMenu') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('QG_runScheduled').timeBased().everyDays(1).atHour(5).create();
  ScriptApp.newTrigger('QG_runScheduled').timeBased().everyDays(1).atHour(21).create();
  ScriptApp.newTrigger('QG_onOpenMenu').forSpreadsheet(SpreadsheetApp.getActive()).onOpen().create();
  QG_log('自動実行を設定（毎日5時・21時にストックから補充）。AI一括生成のトリガーは解除');
}

function QG_checkConfig() {
  var stock = QG_loadStock();
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(QG.BANK);
  var fresh = QG_freshCount(stock, QG_lastUsed(sheet));
  QG_alert('ストック：' + stock.length + '問（' + QG.SUBJECT + '）\n直近' + QG.COOLDOWN_DAYS + '日に出していない問題：' + fresh + '問（約' + Math.floor(fresh / QG.PER_DAY) + '日分）');
}

function QG_runNow() {
  var r = QG_run(false);
  QG_alert('補充しました\n\n' + r.summary);
}

function QG_runScheduled() {
  var hour = Number(Utilities.formatDate(new Date(), 'Asia/Tokyo', 'H'));
  QG_run(hour < 6);
}

// ─────────────────────────────────────────────
// 本体
// ─────────────────────────────────────────────
function QG_run(beforeMorning) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(QG.BANK);
  QG_ensureHeader(sheet);
  var stock = QG_loadStock();
  if (stock.length < QG.PER_DAY) {
    QG_notify('⚠️ ' + QG.SUBJECT + ' の毎日問題のストックが読めません（' + stock.length + '問）');
    return { summary: 'ストックが読めない' };
  }
  var lastUsed = QG_lastUsed(sheet);
  var filled = [];
  for (var d = 0; d <= QG.DAYS_AHEAD; d++) {
    var dateStr = QG_dateStr(QG_addDays(new Date(), d));
    if (QG_countForDate(sheet, dateStr) > 0) continue;
    if (d === 0 && !beforeMorning) continue;
    var picked = QG_pick(stock, lastUsed, dateStr);
    picked.forEach(function(q, i) {
      sheet.appendRow(QG_rowValues(dateStr, i + 1, q));
      lastUsed[q.id] = dateStr;
    });
    filled.push(dateStr);
  }
  var fresh = QG_freshCount(stock, lastUsed);
  if (fresh < QG.PER_DAY * QG.LOW_STOCK_DAYS) {
    QG_notify('📦 ' + QG.SUBJECT + ' の毎日問題：直近' + QG.COOLDOWN_DAYS + '日に出していない問題が残り ' + fresh + '問です（' + QG.LOW_STOCK_DAYS + '日分を切りました）。追加問題の作成をお願いします。');
  }
  var summary = (filled.length ? filled.join('・') + ' に' + QG.PER_DAY + '問ずつ入れました' : '補充が必要な日はありません') + '／未出題の残り ' + fresh + '問';
  QG_log(summary);
  return { summary: summary };
}

// 直近 COOLDOWN 日に出していないものを優先し、2問は別テーマにする
function QG_pick(stock, lastUsed, dateStr) {
  var cutoff = QG_dateStr(QG_addDays(new Date(dateStr), -QG.COOLDOWN_DAYS));
  var ranked = QG_shuffle(stock.slice()).sort(function(a, b) {
    var la = lastUsed[a.id] || '', lb = lastUsed[b.id] || '';
    return la < lb ? -1 : la > lb ? 1 : 0;   // 出していない（''）→ 古い順
  });
  var picked = [];
  ranked.forEach(function(q) {
    if (picked.length >= QG.PER_DAY) return;
    if (picked.some(function(p) { return p.slug === q.slug; })) return;
    picked.push(q);
  });
  if (picked.some(function(q) { return lastUsed[q.id] && lastUsed[q.id] > cutoff; })) {
    QG_notify('♻️ ' + QG.SUBJECT + ' ' + dateStr + '：未出題のストックが足りないため、' + QG.COOLDOWN_DAYS + '日以内に出した問題を再出題します。');
  }
  return picked;
}

function QG_loadStock() {
  try {
    var res = UrlFetchApp.fetch(QG.STOCK_URL + '?t=' + Date.now(), { muteHttpExceptions: true });
    if (res.getResponseCode() !== 200) return [];
    return (JSON.parse(res.getContentText()).questions || []).filter(function(q) { return q.subject === QG.SUBJECT; });
  } catch (e) {
    QG_log('ストックの読み込みに失敗：' + e.message);
    return [];
  }
}

function QG_lastUsed(sheet) {
  var data = sheet.getDataRange().getValues(), out = {};
  for (var i = 1; i < data.length; i++) {
    var m = String(data[i][QG.COL_NOTE - 1] || '').match(/出典：(\S+)/);
    if (!m) continue;
    var dt = data[i][0] instanceof Date ? QG_dateStr(data[i][0]) : String(data[i][0]).trim();
    if (!out[m[1]] || out[m[1]] < dt) out[m[1]] = dt;
  }
  return out;
}

function QG_freshCount(stock, lastUsed) {
  var cutoff = QG_dateStr(QG_addDays(new Date(), -QG.COOLDOWN_DAYS));
  return stock.filter(function(q) { return !lastUsed[q.id] || lastUsed[q.id] <= cutoff; }).length;
}

function QG_countForDate(sheet, dateStr) {
  var data = sheet.getDataRange().getValues(), n = 0;
  for (var i = 1; i < data.length; i++) {
    var dt = data[i][0] instanceof Date ? QG_dateStr(data[i][0]) : String(data[i][0]).trim();
    if (dt === dateStr) n++;
  }
  return n;
}

function QG_rowValues(dateStr, qNum, q) {
  var rich = '';
  try { rich = JSON.stringify(q.richData || {}); } catch (e) {}
  return [dateStr, qNum, q.topic, q.text, q.choiceA, q.choiceB, q.choiceC, q.choiceD, q.correctAnswer, q.explanation, '✅', 'FALSE', 'FALSE', rich, 'PASS', '出典：' + q.id];
}

function QG_ensureHeader(sheet) {
  if (sheet.getRange(1, QG.COL_STATUS).getValue() !== '品質チェック') {
    sheet.getRange(1, QG.COL_STATUS, 1, 2).setValues([['品質チェック', 'チェック記録']]);
  }
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
  try { SpreadsheetApp.getActiveSpreadsheet().getSheetByName(QG.SYSLOG).appendRow([new Date().toLocaleString('ja-JP'), '[毎日問題の補充] ' + msg]); } catch (e) {}
  Logger.log(msg);
}
function QG_alert(msg) {
  try { SpreadsheetApp.getUi().alert(msg); } catch (e) { Logger.log(msg); }
}
function QG_dateStr(d) { return Utilities.formatDate(d, 'Asia/Tokyo', 'yyyy-MM-dd'); }
function QG_addDays(d, n) { var x = new Date(d.getTime()); x.setDate(x.getDate() + n); return x; }
function QG_shuffle(a) { for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; } return a; }
