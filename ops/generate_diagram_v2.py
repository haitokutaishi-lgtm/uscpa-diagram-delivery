#!/usr/bin/env python3
"""Build 復習シート型（v2）diagram HTML from a topic-spec with "version": 2.

v1（10部構成・対話形式）は generate_diagram_from_spec.py。spec に "version": 2 があれば
そちらから自動でこのモジュールに切り替わる。

構成はセクションの並びを spec 側で持つ（番号・目次は自動採番）。標準の並び:
  1 全体図（1枚で論点の全体が分かる図＋例題の数字）
  2 判定・前提（いつこの処理になるか）
  3 仕訳一覧
  4 差がつく論点（ルール → 数字 → こう間違える）
  5 引っかけ一覧（問題文の英語 → 確認すること → よくある誤答）
  6 確認問題（初見の数字の英語MC＋和訳トグル＋TBS入力式）
  7 見ないで言えるかチェック

各セクションは blocks の配列。block の type は BLOCKS を参照。
文字列は HTML としてそのまま埋め込む（spec は自分たちで書く前提）。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FOOTER = "オリジナル教材。第三者問題・商用テキストの転載なし。"


def _facts(b: dict) -> str:
    items = "".join(f"<li>{x}</li>" for x in b["items"])
    title = f'<p class="font-bold mb-1">{b["title_html"]}</p>' if b.get("title_html") else ""
    return f'<div class="facts">{title}<ul>{items}</ul></div>'


def _trow(r: dict) -> str:
    calc = f'<br><span class="en">{r["calc"]}</span>' if r.get("calc") else ""
    tag = ""
    if r.get("tag"):
        cls = "tag-pl" if r["tag"] == "pl" else "tag-nopl"
        text = r.get("tag_text") or ("P/Lへ" if r["tag"] == "pl" else "P/Lに入らない")
        tag = f'<span class="tag {cls}">{text}</span>'
    return f'<div class="t-row row-{r.get("style", "base")}">{r["label_html"]}{calc}<span class="amt">{r["amt"]}</span>{tag}</div>'


def _side(s: dict) -> str:
    kind = s["kind"]
    if kind == "pl":
        lines = "".join(f'<div class="pl-line"><span>{a}</span><span class="en">{b}</span></div>' for a, b in s["lines"])
        if s.get("total"):
            a, b = s["total"]
            lines += f'<div class="pl-line total"><span>{a}</span><span class="en">{b}</span></div>'
        return f'<div class="pl-box mb-3"><h3 class="text-teal-800">{s["title_html"]}</h3>{lines}</div>'
    if kind == "cash":
        return f'<div class="cash-box mb-3"><h3 class="text-amber-800">{s["title_html"]}</h3><p class="text-xs leading-relaxed">{s["body_html"]}</p></div>'
    return f'<p class="text-xs text-slate-600 mt-3 leading-relaxed">{s["body_html"]}</p>'


def _taccount_map(b: dict) -> str:
    dr = "".join(_trow(r) for r in b["dr"])
    cr = "".join(_trow(r) for r in b["cr"])
    side = "".join(_side(s) for s in b.get("side", []))
    return f"""<div class="map-grid diagram-visual">
        <div class="taccount">
          <div class="taccount-title en">{b["account_title"]}</div>
          <div class="taccount-body">
            <div class="t-side"><div class="t-head">{b.get("dr_head", "増える（Dr）")}</div>{dr}</div>
            <div class="t-side"><div class="t-head">{b.get("cr_head", "減る（Cr）")}</div>{cr}</div>
          </div>
          <div class="t-balance"><span>{b["balance_label"]}</span><span class="amt">{b["balance_amt"]}</span></div>
        </div>
        <div>{side}</div>
      </div>"""


def _formulas(b: dict) -> str:
    lines = "".join(f'<p class="en text-[13px]">{x}</p>' for x in b["lines"])
    return f'<div class="mt-4 text-sm leading-relaxed bg-slate-50 border border-slate-200 rounded-lg p-3"><p class="font-bold mb-1">{b["title"]}</p>{lines}</div>'


def _ruler(b: dict) -> str:
    segs = b["segments"]
    cols = " ".join(s.get("width", "minmax(0,1fr)") for s in segs)
    cells = "".join(f'<div class="{s.get("style", "r1")}"><b>{s["head"]}</b>{s["body_html"]}</div>' for s in segs)
    return f'<div class="ruler mb-4 diagram-visual" style="grid-template-columns:{cols}">{cells}</div>'


def _rule(b: dict) -> str:
    return f'<div class="rule">{b["html"]}</div>'


def _note(b: dict) -> str:
    return f'<p class="text-[13px] text-slate-600 mt-3 leading-relaxed">{b["html"]}</p>'


def _cards2(b: dict) -> str:
    tone = {"teal": "text-teal-800", "red": "text-red-700", "navy": "text-slate-800"}
    cards = ""
    for c in b["cards"]:
        items = "".join(f"<li>{x}</li>" for x in c["items"])
        cards += f'<div class="point mb-0"><p class="font-bold {tone.get(c.get("tone", "teal"))} mb-1">{c["title"]}</p><ul class="list-disc ml-5 text-[13px]">{items}</ul></div>'
    return f'<div class="grid md:grid-cols-2 gap-3 mt-3 text-sm leading-relaxed">{cards}</div>'


def _table(b: dict) -> str:
    head = "".join(f"<th>{h}</th>" for h in b["head"])
    rows = ""
    for r in b["rows"]:
        cells = ""
        for i, c in enumerate(r):
            cls = ' class="en"' if i in b.get("en_cols", []) else ""
            cells += f"<td{cls}>{c}</td>"
        rows += f"<tr>{cells}</tr>"
    return f'<div class="table-wrap"><table class="{b.get("class", "je")}"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'


def _point(b: dict) -> str:
    parts = f'<div class="point-head"><span class="point-no">{b["no"]}</span>{b["title_html"]}</div>'
    if b.get("rule_html"):
        parts += f'<div class="rule">{b["rule_html"]}</div>'
    if b.get("calc_html"):
        parts += f'<div class="calc">{b["calc_html"]}</div>'
    if b.get("list"):
        parts += '<ul class="list-disc ml-5 text-[13px] leading-relaxed space-y-1">' + "".join(f"<li>{x}</li>" for x in b["list"]) + "</ul>"
    if b.get("miss_html"):
        parts += f'<div class="miss"><b>こう間違える：</b>{b["miss_html"]}</div>'
    return f'<div class="point">{parts}</div>'


def _traps(b: dict) -> str:
    return _table({"head": ["問題文の言葉", "確認すること", "よくある誤答"], "rows": b["rows"], "class": "traps"})


def _mcq(b: dict) -> str:
    choices = "<br>".join(b["choices"])
    return f"""<div class="mc-card">
        <p class="mc-label">{b["label"]}</p>
        <p class="en-stem">{b["stem"]}</p>
        <div class="choices">{choices}</div>
        <details><summary>和訳を見る</summary><div class="body">{b["ja_html"]}</div></details>
        <details><summary>正解と解説を見る</summary><div class="body">{b["answer_html"]}</div></details>
      </div>"""


def _tbs(b: dict, idx: int) -> str:
    rows = ""
    for r in b["rows"]:
        tag = "th" if r.get("head") else "td"
        if "options" in r:
            opts = '<option value="">選ぶ</option>' + "".join(f'<option value="{o}">{o}</option>' for o in r["options"])
            val = f'<select data-ans="{r["ans"]}" aria-label="{r["label"]}">{opts}</select>'
        elif "ans" in r:
            val = f'<input inputmode="numeric" data-ans="{r["ans"]}" aria-label="{r["label"]}">'
        else:
            val = r.get("value", "")
        rows += f'<tr><{tag}>{r["label"]}</{tag}><td class="num">{val}</td></tr>'
    return f"""<div class="mc-card tbs-block" data-tbs="{idx}">
        <p class="mc-label">{b["label"]}</p>
        <p class="text-[13px] leading-relaxed mb-2">{b["intro_html"]}{"" if b.get("select") else "（マイナスは「-」を付けて入力）"}</p>
        <div class="table-wrap"><table class="tbs"><thead><tr><th>項目</th><th class="text-right">{b.get("value_head", "金額")}</th></tr></thead><tbody>{rows}</tbody></table></div>
        <div class="mt-3 flex flex-wrap items-center gap-3">
          <button type="button" class="btn tbs-check"><i data-lucide="check-circle" class="w-4 h-4"></i>答え合わせ</button>
          <span class="tbs-result text-sm font-bold"></span>
        </div>
        <details><summary>解説を見る</summary><div class="body">{b["explain_html"]}</div></details>
      </div>"""


def _checklist(b: dict, idx: int) -> str:
    items = "".join(
        f'<li><input type="checkbox" id="c{idx}-{i}"><label for="c{idx}-{i}">{x}</label></li>' for i, x in enumerate(b["items"], 1)
    )
    return f'<ul class="check">{items}</ul>'


def _timeline(b: dict) -> str:
    items = "".join(
        f'<div class="tl-item {i.get("tone", "")}"><span class="tl-date">{i["date"]}</span>{i["label_html"]}</div>' for i in b["items"]
    )
    window = f'<div class="tl-window">{b["window_html"]}</div>' if b.get("window_html") else ""
    return f'<div class="diagram-visual mb-3"><div class="tl">{items}</div>{window}</div>'


SPLIT_COLORS = {"teal": "#0f766e", "navy": "#1e3a5f", "sky": "#0284c7", "amber": "#d97706", "red": "#dc2626", "gray": "#94a3b8"}


def _splitbar(b: dict) -> str:
    """bars: [{title, parts: [{label, amt, pct, color}]}]。pct は幅（%）。凡例に金額を出す。"""
    out = ""
    for bar in b["bars"]:
        segs = "".join(
            f'<div class="s-{p.get("color", "teal")}" style="width:{p["pct"]}%">{p.get("short", p["label"]) if p["pct"] >= 12 else ""}</div>'
            for p in bar["parts"]
        )
        legend = "".join(
            f'<span style="--c:{SPLIT_COLORS[p.get("color", "teal")]}">{p["label"]} <b class="en">{p["amt"]}</b></span>' for p in bar["parts"]
        )
        out += f'<div class="split-wrap"><p class="split-title">{bar["title"]}</p><div class="split">{segs}</div><div class="split-legend">{legend}</div></div>'
    return f'<div class="diagram-visual">{out}</div>'


def _flow(b: dict) -> str:
    """steps: [{head, body_html, tone}]。縦に並ぶ手順（矢印つき）。判定フローなら body に分岐を書く。"""
    steps = "".join(
        f'<div class="flow-step {s.get("tone", "")}"><span class="flow-no">{i}</span><div><b>{s["head"]}</b><p>{s["body_html"]}</p></div></div>'
        for i, s in enumerate(b["steps"], 1)
    )
    return f'<div class="flow diagram-visual">{steps}</div>'


def _matrix(b: dict) -> str:
    """2軸の判定表。col_heads / row_heads と cells[行][列] = {html, tone}。"""
    head = f'<div class="mx-corner">{b.get("corner_html", "")}</div>' + "".join(f'<div class="mx-col">{h}</div>' for h in b["col_heads"])
    body = ""
    for rh, row in zip(b["row_heads"], b["cells"]):
        body += f'<div class="mx-row">{rh}</div>' + "".join(f'<div class="mx-cell {c.get("tone", "")}">{c["html"]}</div>' for c in row)
    cols = len(b["col_heads"])
    return f'<div class="matrix diagram-visual" style="grid-template-columns:minmax(4.2rem,.7fr) repeat({cols},minmax(0,1fr))">{head}{body}</div>'


def _html(b: dict) -> str:
    return b["html"]


BLOCKS = {
    "facts": _facts,
    "taccount_map": _taccount_map,
    "formulas": _formulas,
    "ruler": _ruler,
    "rule": _rule,
    "note": _note,
    "cards2": _cards2,
    "table": _table,
    "point": _point,
    "traps": _traps,
    "mcq": _mcq,
    "timeline": _timeline,
    "splitbar": _splitbar,
    "flow": _flow,
    "matrix": _matrix,
    "html": _html,
}


def render_block(b: dict, idx: int) -> str:
    t = b["type"]
    if t == "tbs":
        return _tbs(b, idx)
    if t == "checklist":
        return _checklist(b, idx)
    if t not in BLOCKS:
        raise ValueError(f"unknown block type: {t}")
    return BLOCKS[t](b)


SCRIPT = """
  <script>
    lucide.createIcons();
    document.querySelectorAll('.tbs-block').forEach((box) => {
      box.querySelector('.tbs-check').addEventListener('click', () => {
        const inputs = box.querySelectorAll('table.tbs input, table.tbs select');
        let ok = 0;
        inputs.forEach((el) => {
          if (el.tagName === 'SELECT') {
            const hitSel = el.value !== '' && el.value === el.dataset.ans;
            el.classList.toggle('ok', hitSel);
            el.classList.toggle('ng', !hitSel);
            if (hitSel) ok++;
            return;
          }
          const v = Number(String(el.value).replace(/[,\\s$＄]/g, '').replace(/[−ー–]/g, '-').replace(/^\\((.*)\\)$/, '-$1'));
          const hit = el.value.trim() !== '' && v === Number(el.dataset.ans);
          el.classList.toggle('ok', hit);
          el.classList.toggle('ng', !hit);
          if (hit) ok++;
        });
        box.querySelector('.tbs-result').textContent = `${inputs.length}問中 ${ok}問正解`;
      });
    });
  </script>"""


def build_html(spec: dict, styles: str) -> str:
    meta = spec["meta"]
    nav = ""
    body = ""
    counter = 0
    for n, sec in enumerate(spec["sections"], 1):
        nav += f'<a href="#{sec["id"]}">{n} {sec["nav"]}</a>'
        lead = f'<p class="lead">{sec["lead_html"]}</p>' if sec.get("lead_html") else ""
        blocks = ""
        for b in sec.get("blocks", []):
            counter += 1
            blocks += "\n      " + render_block(b, counter)
        footer = f'<p class="text-xs text-slate-500 mt-4">{FOOTER}</p>' if n == len(spec["sections"]) else ""
        body += f"""
    <section id="{sec["id"]}" class="section-card">
      <h2><span class="sec-no">{n}</span>{sec["title_html"]}</h2>
      {lead}{blocks}
      {footer}
    </section>
"""
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{meta["page_title"]}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/lucide@latest"></script>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
{styles}
  </style>
</head>
<body>
  <header class="header-gradient text-white">
    <div class="max-w-4xl mx-auto px-4 py-7">
      <p class="text-xs font-bold bg-white/20 inline-block rounded px-2 py-1 mb-3">{meta["badge"]}</p>
      <h1 class="text-xl md:text-2xl font-bold leading-snug">{meta["h1_html"]}</h1>
      <p class="text-sm mt-3 leading-relaxed text-white/90">{meta["lead_html"]}</p>
    </div>
  </header>

  <main class="max-w-4xl mx-auto px-4 py-6 space-y-6">
    <nav class="toc" aria-label="目次">{nav}</nav>
{body}
  </main>
{SCRIPT}
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--styles", default="ops/diagram_v2_styles.css")
    args = ap.parse_args()
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    styles = Path(args.styles).read_text(encoding="utf-8")
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_html(spec, styles), encoding="utf-8")
    print(f"Wrote {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
