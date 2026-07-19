#!/usr/bin/env python3
"""Build 10-part diagram HTML from schedule/topic-specs/<slug>.json (uscpa-far-diagram-quality).

構成（S5 FAR論点解説スタイルを反映）:
  ① 30秒でわかるこのページ  ② 先に言葉をそろえる  ③ よくある悩み
  ④ 会計の背景と仕訳        ⑤ 計算の型            ⑥ 対話で整理
  ⑦ 横串マップ              ⑧ 出題パターンの引き出し
  ⑨ 理解確認MC（ここで見るポイント＋誤答の作られ方）
  ⑩ まとめ（1分で人に説明できる形＋今日のチェックリスト）

glossary / crossmap / patterns / one_minute_html / checklist が無い spec でも
落ちないよう、該当セクションは省略される（番号は自動で詰まる）。
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫"


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def dlg(student_html: str, coach_html: str, mistake_label: str | None = None) -> str:
    label = ""
    if mistake_label:
        label = f'<span class="mistake-label">{esc(mistake_label)}</span>\n          '
    return f"""
      <div class="dlg-row">
        <div class="avatar-col"><div class="avatar-frame overflow-hidden border border-sky-100 bg-sky-50 p-0" aria-hidden="true"><img src="avatars/takuma-dialog.png" alt="たくま" width="56" height="56" class="h-full w-full object-contain object-center"></div></div>
        <div class="student-bubble mb-0">
          <p class="role-line">たくま（受講生）</p>
          {label}<p class="text-sm leading-relaxed">{student_html}</p>
        </div>
      </div>
      <div class="dlg-row">
        <div class="avatar-col"><div class="avatar-frame overflow-hidden border border-slate-200 bg-slate-100 p-0" aria-hidden="true"><img src="avatars/aoi-dialog.png" alt="あおい先生" width="56" height="56" class="h-full w-full object-contain object-center"></div></div>
        <div class="coach-bubble mb-0">
          <p class="role-line">あおい先生（コーチ）</p>
          <p class="text-sm leading-relaxed">{coach_html}</p>
        </div>
      </div>"""


def _summary30_section(spec: dict) -> tuple[str, str, str] | None:
    rows = ""
    for i, pt in enumerate(spec["three"], 1):
        rows += f"""
        <div class="flex items-start gap-4 bg-red-50 rounded-xl p-4">
          <span class="badge-essential flex-shrink-0">{i}</span>
          <p class="text-sm text-slate-700 leading-relaxed"><strong>{pt["title"]}</strong>　{pt["body_html"]}</p>
        </div>"""
    body = f"""
      <p class="text-sm text-slate-700 leading-relaxed mb-4">{spec["three_lead_html"]}</p>
      <div class="space-y-3">{rows}
      </div>"""
    return ("summary30", "30秒でわかるこのページ", "zap", body)


def _glossary_section(spec: dict) -> tuple[str, str, str] | None:
    items = spec.get("glossary", [])
    if not items:
        return None
    cards = ""
    for g in items:
        cards += f"""
        <div class="glossary-card">
          <p class="glossary-term">{g["term_html"]}</p>
          <p class="text-sm text-slate-700 leading-relaxed">{g["body_html"]}</p>
        </div>"""
    body = f"""
      <p class="part-lead">本文の前に、この{len(items)}語だけ意味を固定します。</p>
      <div class="grid md:grid-cols-{min(len(items), 3)} gap-4">{cards}
      </div>"""
    return ("glossary", f"先に言葉をそろえる（{len(items)}語だけ）", "book-open", body)


def _worries_section(spec: dict) -> tuple[str, str, str]:
    choices_preview = "\n".join(
        f'          <li><strong>{esc(c[:2])}.</strong> {esc(c[3:].strip())}</li>'
        if len(c) > 2 and c[1] == "."
        else f"          <li>{esc(c)}</li>"
        for c in spec["mc_preview"]["choices"]
    )
    misconceptions = ""
    for item in spec["misconceptions"]:
        misconceptions += dlg(
            item["student_html"],
            item["coach_html"],
            item.get("label"),
        )
    body = f"""
      <div class="mc-preview-box">
        <h3><i data-lucide="file-question" class="w-4 h-4"></i> 試験でよく出る問題文の例</h3>
        <div class="en-stem mb-3">{spec["mc_preview"]["stem_html"]}</div>
        <ul class="text-sm space-y-1.5">
{choices_preview}
        </ul>
      </div>
      <p class="text-sm text-amber-950/90 mb-4 leading-relaxed">このあと、たくまがつまずきやすい<strong>3つの考え方の誤り</strong>を対話で整理します。<strong>誤解①〜③</strong>は、試験でよく見かける間違いの番号です（選択肢 A〜D の記号とは別です）。</p>
{misconceptions}"""
    return ("worries", "よくある悩み", "coffee", body)


def _theory_section(spec: dict) -> tuple[str, str, str]:
    theory_blocks = ""
    for block in spec["theory"].get("blocks", []):
        lines = "".join(f'<p class="je-line">{line}</p>' for line in block.get("je_lines", []))
        theory_blocks += f"""
      <div class="theory-block">
        <h3><i data-lucide="{esc(block.get('icon', 'book-open'))}" class="w-4 h-4 text-indigo-600"></i> {esc(block["heading"])}</h3>
        <p class="text-sm text-slate-700 leading-relaxed">{block["body_html"]}</p>
        {lines}
      </div>"""
    body = f"""
      <p class="part-lead">{spec["theory"]["lead_html"]}</p>
{theory_blocks}
      <p class="timeline-mini"><strong>処理の順序：</strong> {spec["theory"]["timeline_html"]}</p>
      <p class="text-sm text-slate-700 leading-relaxed mt-4">{spec["theory"]["bridge_to_calc_html"]}</p>"""
    return ("theory", "会計の背景と仕訳", "landmark", body)


def _calc_section(spec: dict) -> tuple[str, str, str]:
    steps = ""
    for i, step in enumerate(spec["calc"]["steps"], 1):
        steps += f"""
        <li class="flex gap-2 items-start"><span class="step-pill">{i}</span><span>{step}</span></li>"""
    calc_extra = spec["calc"].get("extra_html", "")
    body = f"""
      <p class="text-sm text-slate-700 mb-4 leading-relaxed">{spec["calc"]["intro_html"]}</p>
      <ol class="space-y-3 text-sm text-slate-800 mb-6 leading-relaxed">{steps}
      </ol>
      {calc_extra}"""
    return ("reading", "計算の型", "calculator", body)


def _process_section(spec: dict) -> tuple[str, str, str]:
    persona = spec.get("process_persona_strip", {})
    persona_html = ""
    if persona:
        persona_html = f"""
      <div class="persona-strip">
        <span><strong>たくま</strong>：{persona.get("takuma", "")}</span>
        <span><strong>あおい先生</strong>：{persona.get("aoi", "")}</span>
      </div>"""
    process_dlgs = ""
    for pair in spec.get("process_dialogues", []):
        process_dlgs += dlg(pair["student_html"], pair["coach_html"])
    return ("process", "対話で整理", "message-circle", persona_html + process_dlgs)


def _crossmap_section(spec: dict) -> tuple[str, str, str] | None:
    cm = spec.get("crossmap")
    if not cm:
        return None
    items = ""
    for it in cm.get("items", []):
        items += f"""
        <div class="crossmap-item">
          <p class="crossmap-title"><i data-lucide="link" class="w-4 h-4"></i> {it["title_html"]}</p>
          <p class="text-sm text-slate-700 leading-relaxed">{it["body_html"]}</p>
        </div>"""
    body = f"""
      <p class="part-lead">{cm.get("lead_html", "この論点は単独では出ません。つながる論点をまとめて回路にします。")}</p>
      <div class="space-y-3">{items}
      </div>"""
    return ("crossmap", "横串マップ（他の論点とのつながり）", "network", body)


def _patterns_section(spec: dict) -> tuple[str, str, str] | None:
    pt = spec.get("patterns")
    if not pt:
        return None
    mc_items = ""
    for p in pt.get("mc_patterns", []):
        mc_items += f"""
          <li class="flex items-start gap-2"><i data-lucide="circle-dot" class="w-4 h-4 text-violet-600 mt-0.5 flex-shrink-0"></i><span>{p}</span></li>"""
    solve = pt.get("solve", {})
    solve_steps = "".join(f"\n            <li>{s}</li>" for s in solve.get("steps", []))
    solve_card = ""
    if solve_steps:
        solve_card = f"""
        <div class="pattern-card">
          <p class="font-bold text-violet-900 mb-3">{solve.get("title_html", "解く手順は毎回同じ")}</p>
          <ol class="text-sm text-slate-700 space-y-2 list-decimal list-inside leading-relaxed">{solve_steps}
          </ol>
        </div>"""
    body = f"""
      <p class="part-lead">{pt.get("lead_html", "出題側の引き出しを先に知っておくと、問題文の狙いが読めます。")}</p>
      <div class="grid md:grid-cols-2 gap-4">
        <div class="pattern-card">
          <p class="font-bold text-violet-900 mb-3">MC の出方</p>
          <ul class="text-sm text-slate-700 space-y-2 leading-relaxed">{mc_items}
          </ul>
        </div>{solve_card}
      </div>"""
    return ("patterns", "出題パターンの引き出し", "file-question", body)


def _mc_section(spec: dict) -> tuple[str, str, str]:
    mc_cards = ""
    for q in spec["mc"]:
        ch = "\n".join(f'          <li>{esc(c)}</li>' for c in q["choices"])
        focus_html = ""
        if q.get("focus"):
            focus_items = "".join(f"\n            <li>{f}</li>" for f in q["focus"])
            focus_html = f"""
        <div class="focus-box">
          <p class="focus-title"><i data-lucide="target" class="w-4 h-4"></i> ここで見るポイント（読む前に）</p>
          <ul class="list-disc list-inside text-sm text-slate-600 space-y-1">{focus_items}
          </ul>
        </div>"""
        distractor_html = ""
        if q.get("distractors_html"):
            d_items = "".join(f"\n              <li>{d}</li>" for d in q["distractors_html"])
            distractor_html = f"""
            <p class="font-bold text-slate-900 mt-3 mb-1">誤答の作られ方</p>
            <ul class="distractor-list">{d_items}
            </ul>"""
        mc_cards += f"""
      <div class="mc-card">
        <p class="font-bold text-slate-900 mb-2">{esc(q["title"])}</p>{focus_html}
        <div class="en-stem mb-4">{q["stem_html"]}</div>
        <ul class="text-sm space-y-2 mb-4">{ch}</ul>
        <details>
          <summary>解説を開く</summary>
          <div class="mt-3 text-sm text-slate-700 border-t pt-3 space-y-2 leading-relaxed">{q["explain_html"]}{distractor_html}</div>
        </details>
      </div>"""
    intro = spec.get("mc_intro_html", "オリジナル問題です。")
    body = f"""
      <p class="text-sm text-slate-600 mb-6 leading-relaxed">{intro}</p>
{mc_cards}"""
    return ("mc", "理解確認MC", "clipboard-check", body)


def _summary_section(spec: dict) -> tuple[str, str, str]:
    parts = ""
    one_minute = spec.get("one_minute_html")
    if one_minute:
        parts += f"""
      <p class="text-sm font-bold text-slate-700 mb-2">1分で人に説明できる形</p>
      <div class="one-minute mb-6">
        <p class="text-sm text-slate-700 leading-relaxed">{one_minute}</p>
      </div>"""
    summary_list = spec.get("summary", [])
    if summary_list and not one_minute:
        rows = "\n".join(f"        <li>{s}</li>" for s in summary_list)
        parts += f"""
      <ol class="list-decimal list-inside space-y-3 text-sm text-slate-700 leading-relaxed mb-6">
{rows}
      </ol>"""
    checklist = spec.get("checklist", [])
    if checklist:
        items = "".join(
            f"""
          <li class="flex items-start gap-2"><i data-lucide="square" class="w-4 h-4 text-emerald-600 mt-0.5 flex-shrink-0"></i><span>{c}</span></li>"""
            for c in checklist
        )
        parts += f"""
      <div class="checklist-box">
        <p class="font-bold text-emerald-900 mb-3 flex items-center gap-2"><i data-lucide="check-circle" class="w-5 h-5"></i> 今日のチェックリスト</p>
        <ul class="space-y-2 text-sm text-slate-700 leading-relaxed">{items}
        </ul>
      </div>"""
    return ("summary", "まとめ：1分で人に説明できる形", "award", parts)


SECTION_ICON_COLOR = {
    "summary30": "text-blue-600",
    "glossary": "text-emerald-600",
    "worries": "",
    "theory": "text-indigo-600",
    "reading": "text-indigo-600",
    "process": "text-rose-500",
    "crossmap": "text-amber-600",
    "patterns": "text-violet-600",
    "mc": "text-teal-600",
    "summary": "text-emerald-600",
}

SECTION_CARD_CLASS = {
    "summary30": "section-card border-2 border-blue-200",
    "worries": "section-card worries-box border-amber-300",
    "theory": "section-card border-indigo-100",
    "crossmap": "section-card border-2 border-amber-200",
    "patterns": "section-card border-2 border-violet-200",
    "summary": "section-card border-2 border-emerald-300",
}


def build_html(spec: dict, styles: str) -> str:
    m = spec["meta"]

    builders = [
        _summary30_section,
        _glossary_section,
        _worries_section,
        _theory_section,
        _calc_section,
        _process_section,
        _crossmap_section,
        _patterns_section,
        _mc_section,
        _summary_section,
    ]
    sections = [s for s in (b(spec) for b in builders) if s is not None]

    nav_items = ""
    section_html = ""
    for idx, (sec_id, title, icon, body) in enumerate(sections):
        num = CIRCLED[idx]
        nav_items += f'\n        <li><a href="#{sec_id}" class="text-blue-700 hover:underline">{num} {title}</a></li>'
        card_class = SECTION_CARD_CLASS.get(sec_id, "section-card")
        icon_color = SECTION_ICON_COLOR.get(sec_id, "text-slate-600")
        icon_class = f"w-6 h-6 {icon_color}".strip()
        heading_class = (
            "text-lg font-bold text-amber-950 mb-3 flex items-center gap-2"
            if sec_id == "worries"
            else "text-xl font-bold text-slate-900 mb-4 flex items-center gap-2"
        )
        section_html += f"""
    <section id="{sec_id}" class="{card_class}">
      <h2 class="{heading_class}"><i data-lucide="{icon}" class="{icon_class}"></i> {num} {title}</h2>{body}
    </section>
"""

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(m["page_title"])}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/lucide@latest"></script>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
{styles}
  </style>
</head>
<body class="bg-slate-50 text-slate-800">
  <header class="header-gradient text-white py-10 px-4">
    <div class="max-w-3xl mx-auto">
      <p class="text-xs font-semibold tracking-wide uppercase opacity-95 mb-3 py-2 px-3 rounded-lg bg-white/15 border border-white/20 inline-block">今回のテーマ：{m["theme_line_html"]}</p>
      <p class="text-sm opacity-90 mb-2 flex items-center gap-2"><i data-lucide="book-marked" class="w-5 h-5"></i> {esc(m["subject_line"])}</p>
      <h1 class="text-2xl md:text-3xl font-bold leading-snug">{m["h1_html"]}</h1>
      <p class="mt-3 text-sm opacity-95 max-w-2xl leading-relaxed">{m["lead_html"]}</p>
    </div>
  </header>

  <main class="max-w-3xl mx-auto px-4 py-10 space-y-10">
    <nav class="rounded-xl bg-white border border-slate-200 p-4 text-sm">
      <ul class="list-disc list-inside space-y-1 text-slate-600">{nav_items}
      </ul>
    </nav>
{section_html}
    <footer class="text-center text-xs text-slate-500 pb-12"><p>オリジナル教材。第三者問題・商用テキストの転載なし。</p></footer>
  </main>
  <script>lucide.createIcons();</script>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--styles", default="ops/diagram_shared_styles.css")
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
