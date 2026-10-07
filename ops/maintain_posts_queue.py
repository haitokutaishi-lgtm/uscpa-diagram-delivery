#!/usr/bin/env python3
"""Fill schedule/posts.json from each subject's queue (FAR: 日水土, AUD: 火金 など delivery-config.json の subjects)."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")


def today_jst() -> date:
    return datetime.now(JST).date()


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


def subject_of(entry: dict) -> str:
    return entry.get("subject") or "FAR"


def is_v2_spec(slug: str) -> bool:
    spec = Path(f"schedule/topic-specs/{slug}.json")
    if not spec.is_file():
        return False
    try:
        return json.loads(spec.read_text(encoding="utf-8")).get("version") == 2
    except json.JSONDecodeError:
        return False


def subjects_from_config(config: dict, default_queue: str) -> dict:
    """旧形式（post_weekdays だけ）の設定も FAR 1科目として読む。"""
    if config.get("subjects"):
        return config["subjects"]
    return {
        "FAR": {
            "enabled": True,
            "post_weekdays": config.get("post_weekdays") or [6, 2, 5],
            "queue": default_queue,
            "lookahead_slots": config.get("lookahead_slots") or 6,
        }
    }


def fill_subject(
    name: str,
    sub: dict,
    posts: dict,
    last_posted: str,
    today: date,
    config: dict,
    slug_to_src: dict,
) -> int:
    queue = json.loads(Path(sub["queue"]).read_text(encoding="utf-8"))
    excluded = set(config.get("excluded_slugs") or [])
    weekdays = set(sub["post_weekdays"])
    lookahead = int(sub.get("lookahead_slots") or config.get("lookahead_slots") or 6)
    base_url = config.get("topics_base_url", "").rstrip("/") + "/"
    require_ready = bool(config.get("require_html_or_topic_spec", True))
    require_v2 = bool(sub.get("require_v2"))

    date_keys = [k for k in posts if re.fullmatch(r"\d{4}-\d{2}-\d{2}", k)]
    mine = [k for k in date_keys if subject_of(posts[k]) == name]
    pending = [k for k in mine if not last_posted or k > last_posted]
    need = max(0, lookahead - len(pending))
    if need == 0:
        print(f"[{name}] Queue OK: {len(pending)} pending (lookahead={lookahead}).")
        return 0

    scheduled_ids = scheduled_queue_ids(posts)
    remaining = [
        item
        for item in queue.get("items", [])
        if item.get("id") not in scheduled_ids and item.get("slug") not in excluded
    ]

    if mine:
        anchor = max(parse_date(k) for k in mine)
    elif last_posted:
        anchor = parse_date(last_posted)
    else:
        anchor = today
    # 停止期間の過去枠は埋めない。取りこぼしは posts.json に既にある日付だけ catch-up する。
    start = max(anchor + timedelta(days=1), today)
    new_dates = next_cadence_dates(start, need, weekdays, set(date_keys))

    added = 0
    for post_date, item in zip(new_dates, remaining):
        slug = item["slug"]
        src = slug_to_src.get(slug)
        spec = Path(f"schedule/topic-specs/{slug}.json")
        html_ok = bool(src) and Path(src).is_file()
        spec_ok = spec.is_file()
        if require_v2 and not is_v2_spec(slug):
            # 順番を守るため、v2 の spec ができていないテーマで止める（旧型は配信しない）
            print(f"::warning::[{name}] {item.get('id')} の v2 spec がまだ無いので補充をここで止めます ({slug})", file=sys.stderr)
            break
        if require_ready and not html_ok and not spec_ok:
            print(f"::warning::[{name}] スキップ {item.get('id')}: HTML も topic-spec も無い ({slug})", file=sys.stderr)
            break

        title = item.get("title") or ""
        if not title and src:
            title = title_from_html(Path(src)) or slug
        posts[post_date] = {
            "title": title,
            "description": item.get("description", ""),
            "url": f"{base_url}{slug}/",
            "slug": slug,
            "queue_id": item["id"],
            "subject": name,
            "_auto": True,
        }
        if item.get("revised"):
            posts[post_date]["revised"] = True
        if spec_ok and not html_ok:
            posts[post_date]["auto_generate"] = True
            posts[post_date]["topic_spec"] = str(spec)
        scheduled_ids.add(item["id"])
        added += 1
        print(f"[{name}] Scheduled {post_date}: {item['id']} ({slug})")
    if added < need:
        print(f"::warning::[{name}] 配信枠 {need} 件のうち {added} 件だけ補充しました（キューの残りか v2 spec が不足）", file=sys.stderr)
    return added


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
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    slug_to_src = {row["slug"]: row["source"] for row in manifest}
    last_posted = state.get("last_posted_date") or ""
    today = today_jst()

    before = set(posts)
    added = 0
    for name, sub in subjects_from_config(config, args.queue).items():
        if not sub.get("enabled", True):
            print(f"[{name}] enabled=false — 補充しません")
            continue
        added += fill_subject(name, sub, posts, last_posted, today, config, slug_to_src)

    if added == 0:
        _emit(args.github_output, queue_updated="false", added_count="0")
        return 0
    if args.dry_run:
        print(json.dumps({k: posts[k] for k in sorted(set(posts) - before)}, ensure_ascii=False, indent=2))
        _emit(args.github_output, queue_updated="false", added_count=str(added))
        return 0
    ordered = {k: posts[k] for k in sorted(posts, key=lambda k: (not k.startswith("_"), k))}
    posts_path.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
