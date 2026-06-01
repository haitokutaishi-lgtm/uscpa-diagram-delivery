#!/usr/bin/env python3
"""Build 7-part diagram HTML from schedule/topic-specs/<slug>.json (uscpa-far-diagram-quality)."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path


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


def build_html(spec: dict, styles: str) -> str:
    m = spec["meta"]
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

    three_items = ""
    colors = ["red-600", "blue-600", "emerald-600"]
    for i, pt in enumerate(spec["three"], 1):
        three_items += f"""
        <li class="flex gap-3">
          <span class="w-8 h-8 rounded-full bg-{colors[i-1]} text-white flex items-center justify-center font-bold flex-shrink-0">{i}</span>
          <div>
            <p class="font-bold text-slate-900">{pt["title"]}</p>
            <p class="text-slate-600 mt-1">{pt["body_html"]}</p>
          </div>
        </li>"""

    theory_blocks = ""
    for block in spec["theory"].get("blocks", []):
        lines = "".join(f'<p class="je-line">{line}</p>' for line in block.get("je_lines", []))
        theory_blocks += f"""
      <div class="theory-block">
        <h3><i data-lucide="{esc(block.get('icon', 'book-open'))}" class="w-4 h-4 text-indigo-600"></i> {esc(block["heading"])}</h3>
        <p class="text-sm text-slate-700 leading-relaxed">{block["body_html"]}</p>
        {lines}
      </div>"""

    steps = ""
    for i, step in enumerate(spec["calc"]["steps"], 1):
        steps += f"""
        <li class="flex gap-2 items-start"><span class="step-pill">{i}</span><span>{step}</span></li>"""

    calc_extra = spec["calc"].get("extra_html", "")

    process_dlgs = ""
    for pair in spec.get("process_dialogues", []):
        process_dlgs += dlg(pair["student_html"], pair["coach_html"])

    mc_cards = ""
    for j, q in enumerate(spec["mc"], 1):
        ch = "\n".join(f'          <li>{esc(c)}</li>' for c in q["choices"])
        mc_cards += f"""
      <div class="mc-card">
        <p class="font-bold text-slate-900 mb-2">{esc(q["title"])}</p>
        <div class="en-stem mb-4">{q["stem_html"]}</div>
        <ul class="text-sm space-y-2 mb-4">{ch}</ul>
        <details>
          <summary>解説を開く</summary>
          <div class="mt-3 text-sm text-slate-700 border-t pt-3 space-y-2 leading-relaxed">{q["explain_html"]}</div>
        </details>
      </div>"""

    summary = "\n".join(f"        <li>{s}</li>" for s in spec["summary"])

    persona = spec.get("process_persona_strip", {})
    persona_html = ""
    if persona:
        persona_html = f"""
      <div class="persona-strip">
        <span><strong>たくま</strong>：{persona.get("takuma", "")}</span>
        <span><strong>あおい先生</strong>：{persona.get("aoi", "")}</span>
      </div>"""

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
      <ul class="list-disc list-inside space-y-1 text-slate-600">
        <li><a href="#worries" class="text-blue-700 hover:underline">① よくある悩み</a></li>
        <li><a href="#three" class="text-blue-700 hover:underline">② まず覚える3つ</a></li>
        <li><a href="#theory" class="text-blue-700 hover:underline">③ 会計の背景と仕訳</a></li>
        <li><a href="#reading" class="text-blue-700 hover:underline">④ 計算の型</a></li>
        <li><a href="#process" class="text-blue-700 hover:underline">⑤ 対話で整理</a></li>
        <li><a href="#mc" class="text-blue-700 hover:underline">⑥ 理解確認MC</a></li>
        <li><a href="#summary" class="text-blue-700 hover:underline">⑦ まとめ</a></li>
      </ul>
    </nav>

    <section id="worries" class="section-card worries-box border-amber-300">
      <h2 class="text-lg font-bold text-amber-950 mb-3 flex items-center gap-2"><i data-lucide="coffee" class="w-5 h-5"></i> ① よくある悩み</h2>
      <div class="mc-preview-box">
        <h3><i data-lucide="file-question" class="w-4 h-4"></i> 試験でよく出る問題文の例</h3>
        <div class="en-stem mb-3">{spec["mc_preview"]["stem_html"]}</div>
        <ul class="text-sm space-y-1.5">
{choices_preview}
        </ul>
      </div>
      <p class="text-sm text-amber-950/90 mb-4 leading-relaxed">このあと、たくまがつまずきやすい<strong>3つの考え方の誤り</strong>を対話で整理します。<strong>誤解①〜③</strong>は、試験でよく見かける間違いの番号です（選択肢 A〜D の記号とは別です）。</p>
{misconceptions}
    </section>

    <section id="three" class="section-card">
      <h2 class="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2"><i data-lucide="star" class="w-6 h-6 text-amber-500"></i> ② まず覚える3つ</h2>
      <p class="part-lead">{spec["three_lead_html"]}</p>
      <ol class="space-y-5 text-sm leading-relaxed">
{three_items}
      </ol>
    </section>

    <section id="theory" class="section-card border-indigo-100">
      <h2 class="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2"><i data-lucide="landmark" class="w-6 h-6 text-indigo-600"></i> ③ 会計の背景と仕訳</h2>
      <p class="part-lead">{spec["theory"]["lead_html"]}</p>
{theory_blocks}
      <p class="timeline-mini"><strong>処理の順序：</strong> {spec["theory"]["timeline_html"]}</p>
      <p class="text-sm text-slate-700 leading-relaxed mt-4">{spec["theory"]["bridge_to_calc_html"]}</p>
    </section>

    <section id="reading" class="section-card">
      <h2 class="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2"><i data-lucide="calculator" class="w-6 h-6 text-indigo-600"></i> ④ 計算の型</h2>
      <p class="text-sm text-slate-700 mb-4 leading-relaxed">{spec["calc"]["intro_html"]}</p>
      <ol class="space-y-3 text-sm text-slate-800 mb-6 leading-relaxed">
{steps}
      </ol>
      {calc_extra}
    </section>

    <section id="process" class="section-card">
      <h2 class="text-xl font-bold text-slate-900 mb-2 flex items-center gap-2"><i data-lucide="message-circle" class="w-6 h-6 text-rose-500"></i> ⑤ 対話で整理</h2>
{persona_html}
{process_dlgs}
    </section>

    <section id="mc" class="section-card">
      <h2 class="text-xl font-bold text-slate-900 mb-2 flex items-center gap-2"><i data-lucide="clipboard-check" class="w-6 h-6 text-teal-600"></i> ⑥ 理解確認MC</h2>
      <p class="text-sm text-slate-600 mb-6 leading-relaxed">{spec.get("mc_intro_html", "オリジナル問題です。")}</p>
{mc_cards}
    </section>

    <section id="summary" class="section-card border-2 border-slate-300">
      <h2 class="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2"><i data-lucide="circle-check" class="w-6 h-6 text-emerald-600"></i> ⑦ この図解のまとめ</h2>
      <ol class="list-decimal list-inside space-y-3 text-sm text-slate-700 leading-relaxed">
{summary}
      </ol>
    </section>

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
