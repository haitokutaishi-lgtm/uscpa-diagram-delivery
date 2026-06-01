#!/usr/bin/env python3
"""Resolve next Discord post date and whether to auto-generate HTML from topic-spec."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


def slug_from_url(url: str) -> str | None:
    m = re.search(r"/topics/([^/?#]+)", url)
    return m.group(1) if m else None


def resolve_post_date(posts: dict, state: dict, today: str, manual: str | None) -> str | None:
    if manual:
        return manual.strip()
    last = state.get("last_posted_date") or ""
    keys = sorted(
        k for k in posts.keys() if k not in ("_comment", "_last_posted_date") and k <= today
    )
    for k in keys:
        if not last or k > last:
            return k
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--posts", default="schedule/posts.json")
    ap.add_argument("--state", default="schedule/discord-post-state.json")
    ap.add_argument("--manifest", default="ops/diagram-publish-manifest.json")
    ap.add_argument("--today", default=os.environ.get("CALENDAR_TODAY", ""))
    ap.add_argument("--manual-date", default=os.environ.get("MANUAL_POST_DATE", ""))
    ap.add_argument(
        "--force-regenerate",
        action="store_true",
        default=os.environ.get("FORCE_REGENERATE", "").lower() in ("1", "true", "yes"),
    )
    ap.add_argument("--github-output", default=os.environ.get("GITHUB_OUTPUT", ""))
    args = ap.parse_args()

    posts = json.loads(Path(args.posts).read_text(encoding="utf-8"))
    state = json.loads(Path(args.state).read_text(encoding="utf-8"))
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    slug_to_src = {row["slug"]: row["source"] for row in manifest}

    post_date = resolve_post_date(posts, state, args.today, args.manual_date or None)
    if not post_date:
        _emit(args.github_output, post_date="", slug="", source="", run_generate="false", skip="true")
        print("No queued post.", file=sys.stderr)
        return 0

    entry = posts.get(post_date)
    if not entry:
        _emit(args.github_output, post_date=post_date, slug="", source="", run_generate="false", skip="true")
        print(f"No posts entry for {post_date}", file=sys.stderr)
        return 0

    url = entry.get("url", "")
    slug = entry.get("slug") or slug_from_url(url) or ""
    source = slug_to_src.get(slug, "")
    if not source:
        print(f"::warning::manifest に slug がありません: {slug}", file=sys.stderr)
        _emit(args.github_output, post_date=post_date, slug=slug, source="", run_generate="false", skip="true")
        return 0

    spec_path = entry.get("topic_spec") or f"schedule/topic-specs/{slug}.json"
    spec_file = Path(spec_path)
    html_file = Path(source)
    auto_flag = entry.get("auto_generate")
    if auto_flag is None:
        auto_flag = not html_file.is_file()

    if args.force_regenerate and not spec_file.is_file():
        print(f"::error::force_regenerate ですが topic-spec がありません: {spec_file}", file=sys.stderr)
        return 1
    run_generate = spec_file.is_file() and (auto_flag or args.force_regenerate)

    skip = "false"
    _emit(
        args.github_output,
        post_date=post_date,
        slug=slug,
        source=source,
        topic_spec=str(spec_file),
        run_generate="true" if run_generate else "false",
        skip=skip,
    )
    print(f"post_date={post_date} slug={slug} source={source} run_generate={run_generate}")
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
