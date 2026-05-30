#!/usr/bin/env python3
"""
図解ページ（GitHub Pages）を開き、会話を除いた**ビジュアル中心**のブロックを最大4枚キャプチャし
2x2 の 1枚 PNG に合成する。Discord Webhook 用。

優先: SVGフロー / pattern-bar / 分岐図 / 3パターン格子 など。
テキストだけのセクション（悩み・まとめ）はビジュアルが無いページでのみフォールバック。
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

# セクション内の「図」だけを抜き出してプレビュー用 DOM に載せる
BUILD_VISUAL_PREVIEW_JS = r"""
(specs) => {
  document.getElementById('discord-stitch-preview')?.remove();
  const root = document.createElement('div');
  root.id = 'discord-stitch-preview';
  root.style.cssText =
    'position:absolute;left:0;top:0;z-index:99999;background:#fff;' +
    'padding:6px 8px;max-width:720px;box-sizing:border-box;' +
    'font-family:\"Noto Sans JP\",sans-serif';

  const visualSel = [
    '.diagram-visual',
    '.reflow-root',
    '.bar-split',
    '.cl-bar-split',
    '.grid.md\\:grid-cols-2',
    '.grid.md\\:grid-cols-3',
    '.flex.flex-col.items-center.gap-1',
    '.flex.flex-col.items-center.gap-2',
  ].join(',');

  for (const spec of specs) {
    const sec = document.getElementById(spec.id);
    if (!sec) continue;
    const wrap = document.createElement('div');
    wrap.style.marginBottom = '10px';
    const h = sec.querySelector('h2');
    if (h && spec.id !== 'fork') {
      const ht = document.createElement('div');
      ht.style.cssText = 'font-size:1rem;font-weight:700;color:#0f172a;margin-bottom:6px';
      ht.textContent = h.textContent.trim();
      wrap.appendChild(ht);
    }
    let nodes = sec.querySelectorAll(visualSel);
    if (spec.id === 'fork') {
      nodes = sec.querySelectorAll('.diagram-visual--flow');
    }
    if (!nodes.length && spec.fallbackWhole) {
      const clone = sec.cloneNode(true);
      clone.querySelectorAll('.dlg-row,.persona-strip,.part-lead,p.text-sm.text-slate-600').forEach((e) => e.remove());
      wrap.appendChild(clone);
    } else {
      nodes.forEach((n) => {
        if (n.closest('.dlg-row')) return;
        const c = n.cloneNode(true);
        c.querySelectorAll('.diagram-visual--flow, .diagram-visual').forEach((dv) => {
          dv.style.padding = '4px 6px';
          dv.style.margin = '0';
          const cap = dv.querySelector(':scope > p');
          if (cap && cap.classList.contains('text-center')) cap.style.marginBottom = '2px';
        });
        wrap.appendChild(c);
      });
      if (spec.includePatternBars) {
        sec.querySelectorAll('.pattern-bar').forEach((n) => {
          if (!wrap.contains(n) && !Array.from(wrap.querySelectorAll('.pattern-bar')).some((x) => x.textContent === n.textContent)) {
            const p = n.parentElement?.classList?.contains('space-y-2')
              ? n.parentElement.cloneNode(true)
              : n.cloneNode(true);
            if (p.classList?.contains('space-y-2')) wrap.appendChild(p);
          }
        });
      }
    }
    const hasTitle = h && spec.id !== 'fork';
    if (wrap.childNodes.length > (hasTitle ? 1 : 0)) root.appendChild(wrap);
  }
  document.body.appendChild(root);
  return root.scrollHeight;
}
"""

REMOVE_STITCH_JS = r"""
() => { document.getElementById('discord-stitch-preview')?.remove(); }
"""

# ビジュアルキャプチャの優先順（図解セクション）
VISUAL_PANEL_SPECS = [
    {"id": "reading", "fallbackWhole": True, "includePatternBars": False},
    {"id": "fork", "fallbackWhole": False, "includePatternBars": False},
    {"id": "patterns", "fallbackWhole": False, "includePatternBars": True},
    {"id": "group-b", "fallbackWhole": False, "includePatternBars": True},
    {"id": "group-a", "fallbackWhole": False, "includePatternBars": False},
    {"id": "terms", "fallbackWhole": True, "includePatternBars": False},
]

# 図が無いページ用フォールバック
TEXT_FALLBACK_IDS = ("worries", "three", "theory", "reading", "mc", "summary")

SKIP_IDS = frozenset({"intro", "process"})
SKIP_HEADING = ("対話", "悩みが解ける")

CELL_W = 680
GAP = 16
MAX_CELL_H = 920
MIN_PANEL_H = 120
TRIM_THRESHOLD = 248
TRIM_MARGIN = 2


def _trim_whitespace(im: Image.Image) -> Image.Image:
    """白〜近白の余白を四辺から切り落とす（フローチャートのキャプチャ用）。"""
    im = im.convert("RGB")
    w, h = im.size
    if w < 2 or h < 2:
        return im
    pix = im.load()

    def content(px: int, py: int) -> bool:
        r, g, b = pix[px, py]
        return r < TRIM_THRESHOLD or g < TRIM_THRESHOLD or b < TRIM_THRESHOLD

    top = 0
    while top < h and not any(content(x, top) for x in range(w)):
        top += 1
    bottom = h - 1
    while bottom >= top and not any(content(x, bottom) for x in range(w)):
        bottom -= 1
    left = 0
    while left < w and not any(content(left, y) for y in range(top, bottom + 1)):
        left += 1
    right = w - 1
    while right >= left and not any(content(right, y) for y in range(top, bottom + 1)):
        right -= 1
    if left >= right or top >= bottom:
        return im
    m = TRIM_MARGIN
    left = max(0, left - m)
    top = max(0, top - m)
    right = min(w - 1, right + m)
    bottom = min(h - 1, bottom + m)
    return im.crop((left, top, right + 1, bottom + 1))


def _resize_cell(im: Image.Image) -> Image.Image:
    if im.width <= 0 or im.height <= 0:
        return im
    scale = CELL_W / im.width
    h = max(1, int(im.height * scale))
    if h > MAX_CELL_H:
        scale2 = MAX_CELL_H / im.height
        w2 = max(1, int(im.width * scale2))
        return im.resize((w2, MAX_CELL_H), Image.Resampling.LANCZOS)
    return im.resize((CELL_W, h), Image.Resampling.LANCZOS)


def compose_grid(paths: list[Path], out: Path) -> None:
    if len(paths) < 1:
        raise ValueError("no shots")
    imgs = [_resize_cell(_trim_whitespace(Image.open(p))) for p in paths]
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


SCORE_VISUAL_JS = r"""
() => {
  const ids = ['fork','patterns','group-a','group-b','terms','exam','reading','three','worries','mc','summary'];
  const score = (el) => {
    if (!el) return 0;
    let s = 0;
    if (el.querySelector('svg[viewBox]')) s += 50;
    if (el.querySelectorAll('.pattern-bar').length) s += 30 + el.querySelectorAll('.pattern-bar').length * 4;
    if (el.querySelector('.reflow-root, .bar-split, .cl-bar-split, .diagram-visual')) s += 25;
    if (el.querySelector('.grid.md\\:grid-cols-2, .grid.md\\:grid-cols-3')) s += 15;
    if (el.dataset.diagram) s += 20;
    return s;
  };
  return Object.fromEntries(ids.map((id) => {
    const el = document.getElementById(id);
    return [id, score(el)];
  }));
}
"""


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
            await page.wait_for_timeout(600)

            scores: dict[str, int] = await page.evaluate(SCORE_VISUAL_JS)
            shots: dict[str, Path] = {}

            # 0) 代表MCプレビュー（①よくある悩み内）— 改訂図解の差分が Discord で分かるように最優先
            preview = page.locator("#worries .mc-preview-box, main .mc-preview-box").first
            if await preview.count():
                pth = Path("/tmp/_discord_cap_mc_preview.png")
                await preview.screenshot(path=str(pth), type="png")
                if pth.stat().st_size >= 1200:
                    shots["mc-preview"] = pth

            async def shot_preview(specs: list[dict], key: str) -> bool:
                h = await page.evaluate(BUILD_VISUAL_PREVIEW_JS, specs)
                if not h or h < MIN_PANEL_H:
                    await page.evaluate(REMOVE_STITCH_JS)
                    return False
                loc = page.locator("#discord-stitch-preview")
                pth = Path(f"/tmp/_discord_cap_{key}.png")
                await loc.screenshot(path=str(pth), type="png")
                await page.evaluate(REMOVE_STITCH_JS)
                if pth.stat().st_size >= 1200:
                    shots[key] = pth
                    return True
                return False

            # 1) 図解セクションを1コマずつ（スコア順）
            ranked = sorted(
                [s for s in VISUAL_PANEL_SPECS if scores.get(s["id"], 0) > 0],
                key=lambda s: scores.get(s["id"], 0),
                reverse=True,
            )
            for spec in ranked:
                if len(shots) >= 4:
                    break
                await shot_preview([spec], spec["id"])

            # 2) まだ足りなければ fork+patterns を1コマに結合
            if len(shots) < 4 and scores.get("fork", 0) and scores.get("patterns", 0):
                if "fork-patterns" not in shots:
                    specs = [s for s in VISUAL_PANEL_SPECS if s["id"] in ("fork", "patterns")]
                    await shot_preview(specs, "fork-patterns")

            # 3) MC（問題文＋選択肢）— 図が少ないページの主役
            if len(shots) < 4:
                mc = page.locator("#mc")
                if await mc.count():
                    first = mc.locator(".mc-card").first
                    if await first.count():
                        pth = Path("/tmp/_discord_cap_mc.png")
                        await first.screenshot(path=str(pth), type="png")
                        if pth.stat().st_size >= 1200:
                            shots["mc"] = pth

            # 4) テキストフォールバック（図がほぼ無い旧ページ）
            if len(shots) < 2:
                cards = page.locator("main > div.section-card, main > section")
                n = await cards.count()
                for i in range(n):
                    if len(shots) >= 4:
                        break
                    el = cards.nth(i)
                    eid = await el.evaluate("el => el.id || ''")
                    if eid in SKIP_IDS or eid in shots or eid not in TEXT_FALLBACK_IDS:
                        continue
                    ht = await el.locator("h2").first.inner_text() if await el.locator("h2").count() else ""
                    if any(s in ht for s in SKIP_HEADING):
                        continue
                    box = await el.bounding_box()
                    if not box or box["height"] < MIN_PANEL_H:
                        continue
                    pth = Path(f"/tmp/_discord_cap_{eid or i}.png")
                    await el.screenshot(path=str(pth), type="png")
                    if pth.stat().st_size >= 1200:
                        shots[eid or f"_{i}"] = pth

            if not shots:
                raise RuntimeError("no sections captured")

            order_keys = [
                "mc-preview",
                "fork",
                "patterns",
                "fork-patterns",
                "group-b",
                "group-a",
                "terms",
                "exam",
                "reading",
                "mc",
                "worries",
                "three",
                "summary",
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
            ordered = (ordered + [ordered[-1]] * 4)[:4]
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
