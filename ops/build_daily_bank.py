#!/usr/bin/env python3
"""図解（v2 topic-spec）の確認問題（MC）を、毎日問題配信（Apps Script）用のストックにまとめる。

出力：schedule/daily-question-bank.json
  Apps Script の QualityGate.gs が raw.githubusercontent.com から読み、1日2問を選んで問題バンクに入れる。
  追加の問題（図解にない論点）は schedule/daily-extra-questions.json に同じ形で書く（週1回まとめて作成）。

1問の形：
  id, subject, slug, topic, text, choiceA〜D, correctAnswer, explanation, richData（conceptTitle 等）
"""
from __future__ import annotations

import hashlib
import html
import json
import random
import re
from pathlib import Path

SPECS = Path("schedule/topic-specs")
MANIFEST = Path("ops/diagram-publish-manifest.json")
EXTRA = Path("schedule/daily-extra-questions.json")
OUT = Path("schedule/daily-question-bank.json")
SITE = "https://haitokutaishi-lgtm.github.io/diagram-site/topics/"


def plain(s: str) -> str:
    s = re.sub(r"<br\s*/?>", "\n", s or "")
    s = re.sub(r"<[^>]+>", "", s)
    return html.unescape(s).strip()


def choice_text(c: str) -> str:
    return re.sub(r"^[A-D][.)]\s*", "", plain(c))


LETTER = re.compile(r"(?<![A-Za-z])([A-D])(?=[：:（()）．.、　 ]|$)", re.M)


def shuffle_choices(q: dict) -> dict:
    """図解の問題は正解が B に偏っているので、問題ごとに決まった順で選択肢を入れ替える（記号の言及も付け替える）。"""
    rnd = random.Random(int(hashlib.md5(q["id"].encode()).hexdigest(), 16))
    old = ["A", "B", "C", "D"]
    new = old[:]
    rnd.shuffle(new)
    mapping = dict(zip(old, new))
    texts = {mapping[o]: q["choice" + o] for o in old}
    for l in old:
        q["choice" + l] = texts[l]
    q["correctAnswer"] = mapping[q["correctAnswer"]]
    sub = lambda t: LETTER.sub(lambda m: mapping[m.group(1)], t)
    q["explanation"] = sub(q["explanation"])
    lines = sub(q["richData"]["steps"]).split("\n")
    # 誤答の説明行（X：…）を記号順に並べ直す
    head = [l for l in lines if not re.match(r"^[A-D]：", l)]
    wrong = sorted([l for l in lines if re.match(r"^[A-D]：", l)])
    q["richData"]["steps"] = "\n".join(head + wrong)
    return q


def from_spec(slug: str, spec: dict) -> list[dict]:
    subject = spec.get("subject", "FAR")
    name = (spec.get("post") or {}).get("name") or slug
    out = []
    n = 0
    for sec in spec["sections"]:
        for b in sec.get("blocks", []):
            if b.get("type") != "mcq" or len(b.get("choices", [])) != 4:
                continue
            n += 1
            ans = plain(b["answer_html"])
            m = re.search(r"正解：\s*([A-D])", ans)
            if not m:
                raise SystemExit(f"{slug} {b['label']}: 正解の記号が読めない")
            first, _, rest = ans.partition("\n")
            label = b["label"].split("｜", 1)[-1]
            out.append({
                "id": f"{slug}#{n}",
                "subject": subject,
                "slug": slug,
                "topic": f"{name}｜{label}",
                "text": b["stem"],
                "choiceA": choice_text(b["choices"][0]),
                "choiceB": choice_text(b["choices"][1]),
                "choiceC": choice_text(b["choices"][2]),
                "choiceD": choice_text(b["choices"][3]),
                "correctAnswer": m.group(1),
                "explanation": first,
                "richData": {
                    "questionType": "図解の確認問題",
                    "conceptTitle": f"{name}｜{label}",
                    "conceptBody": "【和訳】\n" + plain(b["ja_html"].split("<br>")[0]),
                    "steps": rest.strip(),
                    "wrongAnswers": "",
                    "memoryTip": f"📘 図解で復習：{SITE}{slug}/",
                },
            })
            shuffle_choices(out[-1])
    return out


def main() -> int:
    published = {row["slug"] for row in json.loads(MANIFEST.read_text(encoding="utf-8"))}
    bank = []
    for p in sorted(SPECS.glob("*.json")):
        if p.name.startswith("_"):
            continue
        spec = json.loads(p.read_text(encoding="utf-8"))
        if spec.get("version") != 2 or p.stem not in published:
            continue
        bank += from_spec(p.stem, spec)
    if EXTRA.is_file():
        extra = json.loads(EXTRA.read_text(encoding="utf-8")).get("questions", [])
        bank += extra
    ids = [q["id"] for q in bank]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        raise SystemExit(f"id が重複: {sorted(dup)}")
    counts = {}
    for q in bank:
        counts[q["subject"]] = counts.get(q["subject"], 0) + 1
    OUT.write_text(json.dumps({"_comment": "自動生成（ops/build_daily_bank.py）。手で直さない。追加の問題は daily-extra-questions.json へ。", "counts": counts, "questions": bank}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
