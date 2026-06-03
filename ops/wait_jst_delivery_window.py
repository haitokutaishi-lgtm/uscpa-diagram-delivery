#!/usr/bin/env python3
"""On scheduled runs, wait until 09:00 Asia/Tokyo before posting (avoids 3am drift posts)."""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
DELIVERY_HOUR = int(os.environ.get("DELIVERY_JST_HOUR", "9"))
DELIVERY_MINUTE = int(os.environ.get("DELIVERY_JST_MINUTE", "0"))
MAX_SLEEP_SEC = int(os.environ.get("MAX_SLEEP_SEC", str(6 * 3600)))


def delivery_moment(day: datetime) -> datetime:
    return day.replace(
        hour=DELIVERY_HOUR, minute=DELIVERY_MINUTE, second=0, microsecond=0, tzinfo=JST
    )


def main() -> int:
    if os.environ.get("GITHUB_EVENT_NAME", "") != "schedule":
        print("Not a scheduled event — skip wait.")
        return 0

    now = datetime.now(JST)
    target = delivery_moment(now)

    # 早朝〜8:59（GitHub cron の遅延で 3:00 頃に走った場合など）→ 9:00 まで待つ
    if now < target:
        sleep_sec = min(int((target - now).total_seconds()), MAX_SLEEP_SEC)
        print(
            f"JST now={now:%Y-%m-%d %H:%M} — waiting {sleep_sec}s until "
            f"{target:%Y-%m-%d %H:%M} JST"
        )
        time.sleep(sleep_sec)
        now = datetime.now(JST)

    # 9:00〜12:00 はそのまま配信（軽い遅延は許容）
    if DELIVERY_HOUR <= now.hour < 12:
        print(f"JST now={now:%Y-%m-%d %H:%M} — within delivery window, proceeding.")
        return 0

    # 12:00 以降に初めて起動した場合（大幅遅延）— 当日 9:00 は過ぎているので即配信
    if now.hour >= 12:
        print(
            f"::warning::JST now={now:%Y-%m-%d %H:%M} — scheduled run is late; posting without further wait.",
            file=sys.stderr,
        )
        return 0

    # 0:00〜8:59 の別経路（念のため）
    target = delivery_moment(now)
    if now < target:
        sleep_sec = min(int((target - now).total_seconds()), MAX_SLEEP_SEC)
        print(f"Waiting {sleep_sec}s until {target:%H:%M} JST")
        time.sleep(sleep_sec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
