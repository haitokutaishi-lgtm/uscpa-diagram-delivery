#!/usr/bin/env python3
"""posts.json の1件から Discord Webhook の payload（content + embed）を作る。

v2 の topic-spec に "post" があれば、問いかけ＋できること＋リアクションの選択肢つきの投稿にする。
無ければ従来どおり「【図解配信】タイトル」＋ embed（title / description / url）。

spec の "post":
  name      … 論点名（例：短期債務の借換え）
  text_ref  … テキストの章（例：テキスト4-7）。未収録なら省略
  minutes   … 目安の所要時間（分）
  hook_q    … 開く前に考えてほしい問い（1〜2文）
  hook_where… 答えがページのどこにあるか（例：差がつく論点2と問題2）
  bullets   … このページでできること（3つ）
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REACTIONS = "解いたらリアクションで教えてください\n✅ 全問正解　🤔 間違えた問題があった　📌 あとで解く"
LEGACY_TAIL = "参考になった場合はいいね👍でリアクションください！"


def build(entry: dict, spec: dict | None) -> dict:
    post = (spec or {}).get("post")
    if not post:
        return {
            "content": f"【図解配信】 {entry['title']}\n\n{LEGACY_TAIL}",
            "embeds": [{"title": entry["title"], "description": entry.get("description", ""), "url": entry["url"], "color": 3447003}],
        }
    meta = "・".join(x for x in [post.get("text_ref", ""), f"約{post['minutes']}分" if post.get("minutes") else ""] if x)
    head = f"📘 **FAR図解｜{post['name']}**" + (f"（{meta}）" if meta else "")
    if entry.get("revised"):
        head += "　※改訂版"
    lines = [head, "", f"**Q.** {post['hook_q']}", f"→ 答えは図解の「{post['hook_where']}」で", "", "**このページでできること**"]
    lines += [f"・{b}" for b in post["bullets"]]
    lines += ["", REACTIONS]
    content = "\n".join(lines)
    if len(content) > 1900:
        raise SystemExit(f"content too long: {len(content)}")
    return {
        "content": content,
        "embeds": [{
            "title": f"{post['name']}｜復習シートを開く",
            "description": spec["meta"]["lead_html"].replace("<br>", "\n"),
            "url": entry["url"],
            "color": 0x0F766E,
        }],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--posts", default="schedule/posts.json")
    ap.add_argument("--date", required=True)
    ap.add_argument("--specs-dir", default="schedule/topic-specs")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    posts = json.loads(Path(args.posts).read_text(encoding="utf-8"))
    entry = posts.get(args.date)
    if not entry:
        print(f"No post entry for {args.date}", file=sys.stderr)
        return 3
    spec_path = Path(args.specs_dir) / f"{entry.get('slug', '')}.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8")) if spec_path.is_file() else None
    payload = build(entry, spec)
    Path(args.output).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(payload["content"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
