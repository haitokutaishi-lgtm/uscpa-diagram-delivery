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


def check_deploy_key(key: str, repo: str) -> tuple[str, str]:
    if not key.strip():
        return "warn", "未設定（diagram-site 同期はスキップされます）"
    if "PRIVATE KEY" not in key:
        return "fail", "SSH 秘密鍵の形式ではありません（-----BEGIN ... PRIVATE KEY----- が必要）"
    import subprocess
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".key", delete=False) as f:
        f.write(key.strip() + "\n")
        key_path = f.name
    os.chmod(key_path, 0o600)
    try:
        proc = subprocess.run(
            ["git", "ls-remote", f"git@github.com:{repo}.git", "HEAD"],
            env={
                **os.environ,
                "GIT_SSH_COMMAND": f"ssh -i {key_path} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new",
            },
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode == 0:
            return "ok", f"{repo} への SSH 接続 OK（Deploy Key 有効）"
        return "fail", f"SSH 接続失敗（Deploy Key の登録・権限を確認）: {proc.stderr.strip()[:200]}"
    except Exception as e:
        return "fail", f"接続失敗: {e}"
    finally:
        try:
            os.unlink(key_path)
        except OSError:
            pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--diagram-site-repo", default="haitokutaishi-lgtm/diagram-site")
    ap.add_argument("--summary-file", default=os.environ.get("GITHUB_STEP_SUMMARY", ""))
    ap.add_argument("--json-out", default="")
    args = ap.parse_args()

    discord_url = os.environ.get("DISCORD_WEBHOOK_URL", "")
    deploy_key = os.environ.get("DIAGRAM_SITE_DEPLOY_KEY", "")

    checks = [
        ("DISCORD_WEBHOOK_URL", *check_discord_webhook(discord_url), True),
        ("DIAGRAM_SITE_DEPLOY_KEY", *check_deploy_key(deploy_key, args.diagram_site_repo), False),
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
    if result["DIAGRAM_SITE_DEPLOY_KEY"]["status"] == "fail":
        print("::error::DIAGRAM_SITE_DEPLOY_KEY が無効です。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
