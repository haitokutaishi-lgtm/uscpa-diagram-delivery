#!/usr/bin/env python3
"""knowledge/ の索引を topic-spec から自動生成する。

- knowledge/index.md        … 全テーマの一覧（v1/v2、FARテキストの該当箇所、ASC、更新日、ノートの有無）
- knowledge/traps-index.md  … v2 spec の「引っかけ一覧」と「こう間違える」をテーマ横断で1か所に集めたもの

手で書くのは knowledge/topics/<slug>.md と knowledge/lessons.md だけ。この2つ以外は編集しない。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPECS = ROOT / "schedule" / "topic-specs"
MANIFEST = ROOT / "ops" / "diagram-publish-manifest.json"
KN = ROOT / "knowledge"
SITE = "https://haitokutaishi-lgtm.github.io/diagram-site/topics"
HEADER = "<!-- 自動生成（ops/build_knowledge_index.py）。手で編集しない -->\n"


def plain(s: str) -> str:
    s = re.sub(r"<br\s*/?>", " ", s)
    s = re.sub(r"<[^>]+>", "", s)
    return s.replace("|", "／").strip()


def load_specs() -> dict[str, dict]:
    out = {}
    for p in sorted(SPECS.glob("*.json")):
        if p.name.startswith("_"):
            continue
        out[p.stem] = json.loads(p.read_text(encoding="utf-8"))
    return out


def build_index(specs: dict[str, dict]) -> str:
    rows = []
    for row in json.loads(MANIFEST.read_text(encoding="utf-8")):
        slug = row["slug"]
        spec = specs.get(slug, {})
        ver = "v2" if spec.get("version") == 2 else ("v1(spec)" if spec else "v1")
        k = spec.get("knowledge", {})
        note = f"[ノート](topics/{slug}.md)" if (KN / "topics" / f"{slug}.md").is_file() else "—"
        title = plain(spec.get("meta", {}).get("h1_html", "")) or slug
        rows.append(
            f"| [{slug}]({SITE}/{slug}/) | {spec.get('subject', 'FAR')} | {ver} | {title} | {k.get('far_text') or k.get('aud_text', '')} | {k.get('asc', '')} | {k.get('updated', '')} | {note} |"
        )
    v2 = sum(1 for r in rows if "| v2 |" in r)
    return (
        HEADER
        + f"# 図解ナレッジ索引\n\n全 {len(rows)} テーマ／v2（復習シート型）{v2} 本。\n\n"
        + "| slug | 科目 | 型 | タイトル | テキスト | 基準 | 更新日 | ノート |\n|---|---|---|---|---|---|---|---|\n"
        + "\n".join(rows)
        + "\n"
    )


def build_traps(specs: dict[str, dict]) -> str:
    parts = [HEADER, "# 引っかけ・誤答パターン索引（テーマ横断）\n\n新しい図解を作るときに、似た論点の引っかけを探すために使う。\n"]
    for slug, spec in specs.items():
        if spec.get("version") != 2:
            continue
        traps, misses = [], []
        for sec in spec["sections"]:
            for b in sec.get("blocks", []):
                if b["type"] == "traps":
                    traps += b["rows"]
                if b["type"] == "point" and b.get("miss_html"):
                    misses.append((plain(b["title_html"]), plain(b["miss_html"])))
        parts.append(f"\n## {slug}（{spec.get('knowledge', {}).get('asc', '')}）\n")
        if traps:
            parts.append("\n| 問題文の言葉 | 確認すること | よくある誤答 |\n|---|---|---|\n")
            parts += [f"| {plain(a)} | {plain(b)} | {plain(c)} |\n" for a, b, c in traps]
        if misses:
            parts.append("\n**こう間違える**\n\n")
            parts += [f"- {t}：{m}\n" for t, m in misses]
    return "".join(parts)


def main() -> int:
    specs = load_specs()
    (KN / "index.md").write_text(build_index(specs), encoding="utf-8")
    (KN / "traps-index.md").write_text(build_traps(specs), encoding="utf-8")
    print("knowledge index updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
