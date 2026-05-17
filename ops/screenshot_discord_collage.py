#!/usr/bin/env python3
"""
図解ページ（GitHub Pages）を開き、会話パートを除いた本文を最大4枚キャプチャして
2x2 の 1枚 PNG に合成する。Discord Webhook 用。

会話（.dlg-row / .char-bubble）は非表示。薄い「読む順」だけのセクションは
「まず覚える3つ」と縦に結合して1コマにする。
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

PREPARE_PAGE_JS = r"""
() => {
  document.querySelectorAll('nav.toc, main > nav').forEach((e) => {
    e.style.setProperty('display', 'none', 'important');
  });
  ['#intro', '#process'].forEach((sel) => {
    document.querySelectorAll(sel).forEach((e) => {
      e.style.setProperty('display', 'none', 'important');
    });
  });
  document.querySelectorAll('main .dlg-row, main .persona-strip').forEach((e) => {
    e.style.setProperty('display', 'none', 'important');
  });
  document.querySelectorAll('main .flex.items-start.gap-4').forEach((row) => {
    if (row.querySelector('.char-bubble, .student-bubble, .coach-bubble')) {
      row.style.setProperty('display', 'none', 'important');
    }
  });
  document.querySelectorAll('#mc details').forEach((d, i) => {
    if (i === 0) d.open = true;
  });
}
"""

STITCH_IDS_JS = r"""
(ids) => {
  document.getElementById('discord-stitch-preview')?.remove();
  const box = document.createElement('div');
  box.id = 'discord-stitch-preview';
  box.style.cssText =
    'position:absolute;left:0;top:0;z-index:99999;background:#fff;' +
    'padding:20px 24px;max-width:760px;box-sizing:border-box;' +
    'font-family:\"Noto Sans JP\",sans-serif';
  ids.forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    const wrap = document.createElement('div');
    wrap.style.marginBottom = '20px';
    wrap.appendChild(el.cloneNode(true));
    box.appendChild(wrap);
  });
  document.body.appendChild(box);
  return box.scrollHeight;
}
"""

REMOVE_STITCH_JS = r"""
() => { document.getElementById('discord-stitch-preview')?.remove(); }
"""

SKIP_IDS = frozenset({"intro", "process"})
SKIP_HEADING = ("対話", "悩みが解ける")
# 単体キャプチャの優先順（厚いブロックを先に）
SOLO_PRIORITY = (
    "worries",
    "three",
    "fork",
    "patterns",
    "group-a",
    "group-b",
    "terms",
    "exam",
    "mc",
    "summary",
    "reading",
)

CELL_W = 680
GAP = 16
MAX_CELL_H = 920
MIN_PANEL_H = 140
READING_STITCH_MAX_H = 420


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
                viewport={"width": 1400, "height": 1000},
                device_scale_factor=1.5,
            )
            await page.goto(url, wait_until="networkidle", timeout=120_000)
            await page.wait_for_timeout(2800)
            await page.evaluate(PREPARE_PAGE_JS)
            await page.wait_for_timeout(500)

            cards = page.locator("main > div.section-card, main > section")
            n = await cards.count()
            meta: dict[str, dict] = {}

            async def heading_text(el) -> str:
                h = el.locator("h2").first
                if await h.count():
                    return (await h.inner_text()).strip()
                return ""

            for i in range(n):
                el = cards.nth(i)
                if not await el.is_visible():
                    continue
                eid = await el.evaluate("el => el.id || ''")
                if eid in SKIP_IDS:
                    continue
                ht = await heading_text(el)
                if any(s in ht for s in SKIP_HEADING):
                    continue
                box = await el.bounding_box()
                if not box or box["height"] < MIN_PANEL_H:
                    continue
                meta[eid or f"_idx{i}"] = {"el": el, "height": box["height"]}

            shots: dict[str, Path] = {}
            tmp_i = 0

            async def shot_element(el, key: str) -> None:
                nonlocal tmp_i
                pth = Path(f"/tmp/_discord_cap_{key}.png")
                await el.screenshot(path=str(pth), type="png")
                if pth.stat().st_size >= 1200:
                    shots[key] = pth
                    tmp_i += 1

            async def shot_stitch(ids: list[str], key: str) -> None:
                h = await page.evaluate(STITCH_IDS_JS, ids)
                if not h or h < MIN_PANEL_H:
                    await page.evaluate(REMOVE_STITCH_JS)
                    return
                loc = page.locator("#discord-stitch-preview")
                pth = Path(f"/tmp/_discord_cap_{key}.png")
                await loc.screenshot(path=str(pth), type="png")
                await page.evaluate(REMOVE_STITCH_JS)
                if pth.stat().st_size >= 1200:
                    shots[key] = pth

            # 1) よくある悩み：要点ボックス中心（会話は既に非表示）
            if "worries" in meta:
                inner = page.locator("#worries .worries-inner")
                if await inner.count() and await inner.is_visible():
                    h2 = page.locator("#worries > h2").first
                    if await h2.count():
                        await shot_stitch(["worries"], "worries")
                    else:
                        await shot_element(meta["worries"]["el"], "worries")
                else:
                    await shot_element(meta["worries"]["el"], "worries")

            # 2) まず覚える3つ + 読む順（薄いページは結合）
            reading_h = meta.get("reading", {}).get("height", 0) if "reading" in meta else 0
            if "three" in meta and "reading" in meta and reading_h < READING_STITCH_MAX_H:
                await shot_stitch(["three", "reading"], "three-reading")
            elif "three" in meta:
                await shot_element(meta["three"]["el"], "three")

            # 3–4) 分岐・パターン・MC など厚いブロック
            for pid in SOLO_PRIORITY:
                if pid in ("worries", "three", "reading"):
                    continue
                if pid in shots or pid not in meta:
                    continue
                await shot_element(meta[pid]["el"], pid)
                if len(shots) >= 4:
                    break

            # まだ足りなければ reading / three を単体で
            for pid in ("reading", "three", "summary"):
                if len(shots) >= 4:
                    break
                if pid in meta and pid not in shots:
                    await shot_element(meta[pid]["el"], pid)

            if not shots:
                raise RuntimeError("no sections captured")

            # 表示順を固定
            order_keys = [
                "worries",
                "three-reading",
                "three",
                "fork",
                "patterns",
                "group-a",
                "group-b",
                "terms",
                "exam",
                "mc",
                "summary",
                "reading",
            ]
            ordered: list[Path] = []
            for k in order_keys:
                if k in shots:
                    ordered.append(shots[k])
                if len(ordered) >= 4:
                    break
            for k, p in shots.items():
                if p not in ordered:
                    ordered.append(p)
                if len(ordered) >= 4:
                    break
            ordered = ordered[:4]
            while len(ordered) < 4:
                ordered.append(ordered[-1])

            compose_grid(ordered, out)
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
