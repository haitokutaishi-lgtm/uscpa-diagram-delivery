#!/usr/bin/env python3
"""Discord Webhook に embed + 画像1枚を正しい multipart で投稿する。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import requests
except ImportError as e:
    print("requests が必要です: pip install requests", file=sys.stderr)
    raise SystemExit(2) from e


def post(webhook_url: str, payload: dict, image_path: Path | None) -> int:
    if image_path and image_path.is_file() and image_path.stat().st_size > 2000:
        fn = image_path.name
        body = dict(payload)
        embeds = list(body.get("embeds") or [])
        if embeds:
            embeds[0] = {**embeds[0], "image": {"url": f"attachment://{fn}"}}
        else:
            embeds = [{"image": {"url": f"attachment://{fn}"}}]
        body["embeds"] = embeds
        body["attachments"] = [{"id": 0, "filename": fn}]
        with image_path.open("rb") as f:
            resp = requests.post(
                webhook_url,
                data={"payload_json": json.dumps(body, ensure_ascii=False)},
                files={"file": (fn, f, "image/png")},
                timeout=60,
            )
    else:
        resp = requests.post(
            webhook_url,
            json=payload,
            timeout=60,
        )
    print(resp.text[:500] if resp.text else "(empty body)")
    return resp.status_code


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--webhook-url", required=True)
    ap.add_argument("--payload-json", required=True, type=Path, help="投稿 JSON（content+embeds）")
    ap.add_argument("--image", type=Path, default=None)
    args = ap.parse_args()

    payload = json.loads(args.payload_json.read_text(encoding="utf-8"))
    code = post(args.webhook_url, payload, args.image)
    if code < 200 or code >= 300:
        print(f"Discord HTTP {code}", file=sys.stderr)
        raise SystemExit(1)
    print(f"OK Discord HTTP {code}")


if __name__ == "__main__":
    main()
