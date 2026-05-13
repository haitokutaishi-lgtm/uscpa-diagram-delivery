#!/usr/bin/env python3
"""
図解ページ（GitHub Pages）を開き、会話パートを除いた本文セクションを最大4枚キャプチャして
2x2 の 1枚 PNG に合成する。Discord Webhook の attachments 用。

使い方:
  python ops/screenshot_discord_collage.py --url https://.../topics/foo/ --output /tmp/collage.png

終了コード:
  0 … 成功
  2 … キャプチャ失敗（呼び出し側でテキストのみ投稿にフォールバック）
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from PIL import Image

try:
    from playwright.async_api import async_playwright
except ImportError as e:
    print("playwright がインストールされていません。", file=sys.stderr)
    raise SystemExit(2) from e

# 会話・導入の対話ブロックをレイアウトから外す（図・MC・用語など本文だけ残す）
HIDE_DIALOGUE_JS = r"""
() => {
  document.querySelectorAll('#intro').forEach((e) => {
    e.style.setProperty('display', 'none', 'important');
  });
  document.querySelectorAll('main .dlg-row').forEach((e) => {
    e.style.setProperty('display', 'none', 'important');
  });
  document.querySelectorAll('main .flex.items-start.gap-4').forEach((row) => {
    if (row.querySelector('.char-bubble, .student-bubble, .coach-bubble')) {
      row.style.setProperty('display', 'none', 'important');
    }
  });
}
"""

CELL_W = 560
GAP = 14
MAX_CELL_H = 720


def _resize_cell(im: Image.Image) -> Image.Image:
    if im.width <= 0 or im.height <= 0:
        return im
    scale = CELL_W / im.width
    h = max(1, int(im.height * scale))
    if h > MAX_CELL_H:
        scale2 = MAX_CELL_H / im.height
        w2 = max(1, int(im.width * scale2))
        h2 = MAX_CELL_H
        return im.resize((w2, h2), Image.Resampling.LANCZOS)
    return im.resize((CELL_W, h), Image.Resampling.LANCZOS)


def compose_grid(paths: list[Path], out: Path) -> None:
    if len(paths) < 1:
        raise ValueError("no shots")
    imgs = [_resize_cell(Image.open(p).convert("RGB")) for p in paths]
    while len(imgs) < 4:
        imgs.append(imgs[-1].copy())
    imgs = imgs[:4]
    row1_h = max(imgs[0].height, imgs[1].height)
    row2_h = max(imgs[2].height, imgs[3].height)
    total_w = CELL_W * 2 + GAP
    total_h = row1_h + row2_h + GAP
    canvas = Image.new("RGB", (total_w, total_h), (255, 255, 255))

    def paste(idx: int, x: int, y: int, row_h: int) -> None:
        im = imgs[idx]
        y_off = y + max(0, (row_h - im.height) // 2)
        canvas.paste(im, (x, y_off))

    paste(0, 0, 0, row1_h)
    paste(1, CELL_W + GAP, 0, row1_h)
    paste(2, 0, row1_h + GAP, row2_h)
    paste(3, CELL_W + GAP, row1_h + GAP, row2_h)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, "PNG", optimize=True)


async def capture(url: str, out: Path) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page(
                viewport={"width": 1320, "height": 900},
                device_scale_factor=1.25,
            )
            await page.goto(url, wait_until="networkidle", timeout=120_000)
            await page.wait_for_timeout(2800)
            await page.evaluate(HIDE_DIALOGUE_JS)
            await page.wait_for_timeout(400)

            cards = page.locator("main > div.section-card, main > section")
            n = await cards.count()
            tmp_paths: list[Path] = []
            for i in range(n):
                el = cards.nth(i)
                if not await el.is_visible():
                    continue
                eid = await el.evaluate("el => el.id || ''")
                if eid == "intro":
                    continue
                box = await el.bounding_box()
                if not box or box["height"] < 100:
                    continue
                pth = Path(f"/tmp/_discord_cap_{i}.png")
                await el.screenshot(path=str(pth), type="png")
                if pth.stat().st_size < 800:
                    pth.unlink(missing_ok=True)
                    continue
                tmp_paths.append(pth)
                if len(tmp_paths) >= 4:
                    break

            if not tmp_paths:
                raise RuntimeError("no sections captured")

            while len(tmp_paths) < 4:
                tmp_paths.append(tmp_paths[-1])

            compose_grid(tmp_paths[:4], out)
        finally:
            await browser.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    try:
        asyncio.run(capture(args.url, args.output))
    except Exception as e:
        print(f"screenshot_collage: {e}", file=sys.stderr)
        raise SystemExit(2)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
