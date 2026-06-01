#!/usr/bin/env python3
"""Fill schedule/posts.json from delivery-queue.json for upcoming Sun/Wed/Sat slots."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path


def parse_date(s: str) -> date:
    y, m, d = (int(x) for x in s.split("-"))
    return date(y, m, d)


def slug_from_url(url: str) -> str | None:
    m = re.search(r"/topics/([^/?#]+)", url)
    return m.group(1) if m else None


def title_from_html(path: Path) -> str | None:
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"<title>([^<]+)</title>", text, re.I)
    return m.group(1).strip() if m else None


def next_cadence_dates(
    start: date, count: int, weekdays: set[int], taken: set[str]
) -> list[str]:
    out: list[str] = []
    cur = start
    for _ in range(500):
        if cur.weekday() in weekdays:
            key = cur.isoformat()
            if key not in taken:
                out.append(key)
                if len(out) >= count:
                    break
        cur += timedelta(days=1)
    return out


def scheduled_queue_ids(posts: dict) -> set[str]:
    ids: set[str] = set()
    for key, val in posts.items():
        if key.startswith("_") or not isinstance(val, dict):
            continue
        qid = val.get("queue_id")
        if qid:
            ids.add(qid)
    return ids


def pending_post_dates(posts: dict, last_posted: str) -> list[str]:
    keys = sorted(
        k for k in posts.keys() if not k.startswith("_") and re.fullmatch(r"\d{4}-\d{2}-\d{2}", k)
    )
    return [k for k in keys if not last_posted or k > last_posted]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--posts", default="schedule/posts.json")
    ap.add_argument("--state", default="schedule/discord-post-state.json")
    ap.add_argument("--config", default="schedule/delivery-config.json")
    ap.add_argument("--queue", default="schedule/delivery-queue.json")
    ap.add_argument("--manifest", default="ops/diagram-publish-manifest.json")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--github-output", default=os.environ.get("GITHUB_OUTPUT", ""))
    args = ap.parse_args()

    posts_path = Path(args.posts)
    posts = json.loads(posts_path.read_text(encoding="utf-8"))
    state = json.loads(Path(args.state).read_text(encoding="utf-8"))
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    queue = json.loads(Path(args.queue).read_text(encoding="utf-8"))
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))

    slug_to_src = {row["slug"]: row["source"] for row in manifest}
    excluded = set(config.get("excluded_slugs") or [])
    weekdays = set(config.get("post_weekdays") or [6, 2, 5])
    lookahead = int(config.get("lookahead_slots") or 6)
    base_url = config.get("topics_base_url", "").rstrip("/") + "/"
    require_ready = bool(config.get("require_html_or_topic_spec", True))

    last_posted = state.get("last_posted_date") or ""
    scheduled_ids = scheduled_queue_ids(posts)
    pending = pending_post_dates(posts, last_posted)
    need = max(0, lookahead - len(pending))

    if need == 0:
        print(f"Queue OK: {len(pending)} pending (lookahead={lookahead}), nothing to add.")
        _emit(args.github_output, queue_updated="false", added_count="0")
        return 0

    remaining = [
        item
        for item in queue.get("items", [])
        if item.get("id") not in scheduled_ids and item.get("slug") not in excluded
    ]

    post_keys = {k for k in posts if re.fullmatch(r"\d{4}-\d{2}-\d{2}", k)}
    if post_keys:
        anchor = max(parse_date(k) for k in post_keys)
    elif last_posted:
        anchor = parse_date(last_posted)
    else:
        anchor = date.today()
    start = anchor + timedelta(days=1)

    new_dates = next_cadence_dates(start, need, weekdays, post_keys)
    if len(new_dates) < need:
        print(
            f"::warning::配信枠は {need} 件必要ですが、日付を {len(new_dates)} 件しか確保できません。",
            file=sys.stderr,
        )

    added = 0
    for post_date, item in zip(new_dates, remaining):
        slug = item["slug"]
        src = slug_to_src.get(slug)
        spec = Path(f"schedule/topic-specs/{slug}.json")
        html_ok = src and Path(src).is_file()
        spec_ok = spec.is_file()
        if require_ready and not html_ok and not spec_ok:
            print(
                f"::warning::スキップ {item.get('id')}: HTML も topic-spec も無い ({slug})",
                file=sys.stderr,
            )
            continue

        title = item.get("title") or ""
        if not title and src:
            title = title_from_html(Path(src)) or slug
        url = f"{base_url}{slug}/"
        posts[post_date] = {
            "title": title,
            "description": item.get("description", ""),
            "url": url,
            "slug": slug,
            "queue_id": item["id"],
            "_auto": True,
        }
        if spec_ok and not html_ok:
            posts[post_date]["auto_generate"] = True
            posts[post_date]["topic_spec"] = str(spec)
        scheduled_ids.add(item["id"])
        added += 1
        print(f"Scheduled {post_date}: {item['id']} ({slug})")

    if added == 0 and need > 0:
        print(
            "::warning::delivery-queue の残りが無いか、HTML/spec 未準備のため posts.json を追加できませんでした。",
            file=sys.stderr,
        )
        _emit(args.github_output, queue_updated="false", added_count="0")
        return 0

    if args.dry_run:
        print(json.dumps({k: posts[k] for k in new_dates[:added]}, ensure_ascii=False, indent=2))
        _emit(args.github_output, queue_updated="false", added_count=str(added))
        return 0

    posts_path.write_text(json.dumps(posts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _emit(args.github_output, queue_updated="true", added_count=str(added))
    print(f"Added {added} entries to {posts_path}")
    return 0


def _emit(path: str, **kwargs: str) -> None:
    if not path:
        for k, v in kwargs.items():
            print(f"{k}={v}")
        return
    with open(path, "a", encoding="utf-8") as f:
        for k, v in kwargs.items():
            f.write(f"{k}={v}\n")


if __name__ == "__main__":
    raise SystemExit(main())
