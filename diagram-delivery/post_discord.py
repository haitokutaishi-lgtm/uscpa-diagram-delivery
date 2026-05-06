#!/usr/bin/env python3
"""
次のキューにあるユニットの図解 URL を Discord Webhook に投稿する。

- 「ボリューム|unit_id」で diagram_urls.json に URL が無い項目は飛ばし、
  その後ろで最初に URL があるユニットだけ投稿する（配信日を空けにくくする）。
- これ以上 URL があるユニットが無い場合・間隔スキップ時は終了 0（CI を赤にしない）。

環境変数: DISCORD_WEBHOOK_URL（本番で必須）
任意: 同ディレクトリの .env

投稿間隔: schedule.config.json の discord.min_days_between_posts。
  --force で間隔無視。--dry-run は間隔無視で次のペイロードを表示。
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parent


def load_env_file() -> None:
    p = ROOT / ".env"
    if not p.is_file():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def unit_key(u: dict) -> str:
    return f"{u['volume']}|{u['unit_id']}"


def parse_iso_date(s: str | None) -> date | None:
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    if len(s) >= 10:
        s = s[:10]
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def post_discord_webhook(webhook: str, payload: dict, retries: int = 3) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    last_err: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(
            webhook,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                if resp.status in (200, 204):
                    return
                body = resp.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"HTTP {resp.status}: {body}")
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, RuntimeError) as e:
            last_err = e
            if attempt + 1 < retries:
                wait = 2**attempt
                print(f"Post retry {attempt + 1}/{retries} after error: {e} (sleep {wait}s)", file=sys.stderr)
                time.sleep(wait)
            else:
                raise last_err from None
    raise last_err  # pragma: no cover


def filtered_indices(units: list, cfg: dict) -> list[int]:
    f = cfg["delivery"].get("filter") or {}
    vol, cf, ct = f.get("volume"), f.get("chapter_from"), f.get("chapter_to")
    out = []
    for i, u in enumerate(units):
        if vol and u["volume"] != vol:
            continue
        if cf is not None and u["chapter"] < cf:
            continue
        if ct is not None and u["chapter"] > ct:
            continue
        out.append(i)
    return out


def main() -> int:
    load_env_file()
    dry = "--dry-run" in sys.argv

    cfg = json.loads((ROOT / "schedule.config.json").read_text(encoding="utf-8"))
    cur = json.loads((ROOT / "curriculum.json").read_text(encoding="utf-8"))
    state_path = ROOT / cfg.get("state_file", "delivery-state.json")
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    units = cur["units"]

    if "--prepare-next-key" in sys.argv:
        i = sys.argv.index("--prepare-next-key")
        if i + 1 >= len(sys.argv):
            print("Usage: ... --prepare-next-key FAR1-3|3-22", file=sys.stderr)
            return 1
        key = sys.argv[i + 1]
        if "|" not in key:
            print("Key must be like FAR1-3|3-22", file=sys.stderr)
            return 1
        vol, uid = key.split("|", 1)
        try:
            idx = next(j for j, u in enumerate(units) if u["volume"] == vol and u["unit_id"] == uid)
        except StopIteration:
            print(f"Unknown unit key {key}", file=sys.stderr)
            return 1
        state["discord_last_announced_index"] = idx - 1
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Next Discord post will be index {idx} ({key}).", file=sys.stderr)
        return 0

    urls_path = ROOT / cfg.get("urls_file", "diagram_urls.json")
    raw_urls = json.loads(urls_path.read_text(encoding="utf-8"))
    url_map = {k: v for k, v in raw_urls.items() if not k.startswith("_")}

    idx_list = filtered_indices(units, cfg)
    if not idx_list:
        print("No units match filter.", file=sys.stderr)
        return 1

    last_ann = int(state.get("discord_last_announced_index", -1))
    pos = 0
    while pos < len(idx_list) and idx_list[pos] <= last_ann:
        pos += 1
    if pos >= len(idx_list):
        print("Discord queue: no units after last announcement (end of filtered list).", file=sys.stderr)
        return 0

    dcfg = cfg.get("discord") or {}
    min_days = int(dcfg.get("min_days_between_posts", 0) or 0)
    if min_days > 0 and not dry and "--force" not in sys.argv:
        last_post = parse_iso_date(state.get("discord_last_post_at"))
        today = date.today()
        if last_post is not None:
            elapsed = (today - last_post).days
            if elapsed < min_days:
                wait = min_days - elapsed
                print(
                    f"Skip: last Discord post was {last_post} ({elapsed} days ago). "
                    f"min_days_between_posts={min_days} → wait {wait} more day(s), or use --force.",
                    file=sys.stderr,
                )
                return 0

    next_i: int | None = None
    u = None
    key = ""
    url = ""
    scan = pos
    while scan < len(idx_list):
        cand_i = idx_list[scan]
        cand_u = units[cand_i]
        cand_key = unit_key(cand_u)
        cand_url = url_map.get(cand_key)
        if cand_url:
            next_i, u, key, url = cand_i, cand_u, cand_key, cand_url
            break
        print(
            f"Skip (no URL): {cand_key} — {cand_u['title_ja']}",
            file=sys.stderr,
        )
        scan += 1

    if next_i is None or u is None:
        print(
            f"No diagram URL ahead in queue (from index position {pos}). "
            f"Add entries to {urls_path.name}.",
            file=sys.stderr,
        )
        return 0

    env_name = dcfg.get("webhook_env", "DISCORD_WEBHOOK_URL")
    webhook = os.environ.get(env_name, "").strip()
    if not webhook and not dry:
        print(f"Set {env_name} (see .env.example).", file=sys.stderr)
        return 1

    title = u["title_ja"]
    desc = f"{u['volume']} · Chapter {u['chapter']} · ユニット {u['unit_id']}"
    color = int(dcfg.get("embed_color_decimal", 5814783))
    username = dcfg.get("bot_username") or "FAR 図解"
    prefix = dcfg.get("content_prefix") or ""

    payload = {
        "username": username,
        "content": prefix,
        "embeds": [
            {
                "title": title[:256],
                "url": url,
                "description": desc[:4096],
                "color": color,
            }
        ],
    }

    if dry:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        print(f"\n-- would announce index={next_i} key={key} --", file=sys.stderr)
        return 0

    try:
        post_discord_webhook(webhook, payload, retries=3)
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        print(f"Discord webhook HTTP {e.code}: {err}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"Discord post failed: {e}", file=sys.stderr)
        return 1

    state["discord_last_announced_index"] = next_i
    state["discord_last_post_at"] = date.today().isoformat()
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Posted {key} to Discord; discord_last_announced_index={next_i}, discord_last_post_at={state['discord_last_post_at']}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
