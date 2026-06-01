#!/usr/bin/env python3
"""Check GitHub Actions secrets for diagram Discord delivery (presence + light smoke tests)."""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def check_discord_webhook(url: str) -> tuple[str, str]:
    if not url.strip():
        return "fail", "未設定（DISCORD_WEBHOOK_URL）"
    req = urllib.request.Request(url.strip(), method="GET", headers={"User-Agent": "uscpa-diagram-delivery-health"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            if resp.status == 200:
                return "ok", "Webhook GET 200 — URL は有効"
            return "warn", f"Webhook GET HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 404):
            return "fail", f"Webhook 無効または失効（HTTP {e.code}）"
        return "fail", f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return "fail", f"接続失敗: {e}"


def check_github_pat(token: str, repo: str) -> tuple[str, str]:
    if not token.strip():
        return "warn", "未設定（diagram-site 同期はスキップされます）"
    url = f"https://api.github.com/repos/{repo}"
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {token.strip()}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "uscpa-diagram-delivery-health",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            if resp.status == 200:
                return "ok", f"{repo} への contents 読取 OK"
            return "warn", f"HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return "fail", "PAT 無効または期限切れ（HTTP 401）"
        if e.code == 403:
            return "fail", "PAT の権限不足（diagram-site へ write が必要）"
        if e.code == 404:
            return "fail", f"リポジトリ未検出: {repo}"
        return "fail", f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return "fail", f"接続失敗: {e}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--diagram-site-repo", default="haitokutaishi-lgtm/diagram-site")
    ap.add_argument("--summary-file", default=os.environ.get("GITHUB_STEP_SUMMARY", ""))
    ap.add_argument("--json-out", default="")
    args = ap.parse_args()

    discord_url = os.environ.get("DISCORD_WEBHOOK_URL", "")
    pat = os.environ.get("DIAGRAM_SITE_PUSH_TOKEN", "")

    checks = [
        ("DISCORD_WEBHOOK_URL", *check_discord_webhook(discord_url), True),
        ("DIAGRAM_SITE_PUSH_TOKEN", *check_github_pat(pat, args.diagram_site_repo), False),
    ]

    lines = [
        "## 図解配信 Secrets ヘルスチェック",
        "",
        "| Secret | 結果 | 詳細 |",
        "|--------|------|------|",
    ]
    failed_required = False
    result = {}
    for name, status, detail, required in checks:
        icon = {"ok": "✅", "warn": "⚠️", "fail": "❌"}.get(status, "❓")
        lines.append(f"| `{name}` | {icon} {status} | {detail} |")
        result[name] = {"status": status, "detail": detail, "required": required}
        if required and status == "fail":
            failed_required = True

    lines.extend(
        [
            "",
            "手動で GitHub の Settings を開く必要はありません。",
            "このワークフローが週1回・配信 cron の直前に自動実行されます。",
        ]
    )
    body = "\n".join(lines)
    print(body)

    if args.summary_file:
        Path = __import__("pathlib").Path
        Path(args.summary_file).write_text(body + "\n", encoding="utf-8")

    if args.json_out:
        __import__("pathlib").Path(args.json_out).write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    if failed_required:
        print("::error::必須 Secret が未設定または無効です。", file=sys.stderr)
        return 1
    if result["DIAGRAM_SITE_PUSH_TOKEN"]["status"] == "fail":
        print("::error::DIAGRAM_SITE_PUSH_TOKEN が無効です。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
