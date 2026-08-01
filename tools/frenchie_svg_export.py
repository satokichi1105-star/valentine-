#!/usr/bin/env python3
"""SVG 版のアニメーションを GIF / PNG に書き出すおまけスクリプト.

SVG をそのまま開けない環境 (チャットのプレビュー、資料への貼り付け、
GitHub の README など) 向けの保険。本体の tools/frenchie_svg.py は
標準ライブラリだけで動くが、こちらは実際にブラウザで描画するので
Playwright と Pillow が要る。

    pip install playwright pillow
    playwright install chromium      # 環境によっては不要
    python tools/frenchie_svg_export.py

各コマは CSS アニメーションを Web Animations API で一時停止し、
currentTime を進めながら撮っている。animation-delay を上書きする方法だと
ドットや Zzz のずらしが消えてしまうので、この方法にしてある。
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from frenchie_svg import STATES, build_svg  # noqa: E402

# 状態ごとの (ループ長 [秒], コマ数)。ループ長は一番長いアニメーションに合わせる
TIMING = {
    "idle": (4.4, 22),
    "walk": (0.56, 8),
    "work": (2.8, 20),
    "done": (1.1, 14),
    "sleep": (3.4, 17),
}

PAGE = """<!doctype html><meta charset="utf-8">
<style>
  html, body {{ margin: 0; background: {bg}; }}
  #stage {{ width: {size}px; height: {size}px; }}
  #stage svg {{ width: {size}px; height: {size}px; display: block; }}
</style>
<div id="stage">{svg}</div>
"""


def main() -> None:
    ap = argparse.ArgumentParser(description="SVG 版を GIF / PNG に書き出す")
    ap.add_argument("-o", "--out", default="assets/frenchie-svg/raster", help="出力先")
    ap.add_argument("-s", "--size", type=int, default=240, help="1 コマの一辺 (px)")
    ap.add_argument("--bg", default="#1a1b3a", help="背景色 (GIF は透過を使わない)")
    ap.add_argument(
        "--chromium",
        default=os.environ.get("CHROMIUM_PATH"),
        help="Chromium の実行ファイル。既定は Playwright が持っているもの",
    )
    args = ap.parse_args()

    try:
        from PIL import Image
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # 依存が無いときは何をすればいいか出して終わる
        sys.exit(f"{exc}\npip install playwright pillow を実行してください")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    shot = out / "_frame.png"

    launch_args = {"executable_path": args.chromium} if args.chromium else {}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(**launch_args)
        page = browser.new_page(viewport={"width": args.size, "height": args.size})

        for state in STATES:
            duration, count = TIMING[state]
            page.set_content(
                PAGE.format(svg=build_svg(state), size=args.size, bg=args.bg)
            )
            page.wait_for_timeout(120)
            stage = page.locator("#stage")
            frames = []
            for i in range(count):
                t = duration * i / count * 1000
                page.evaluate(
                    "t => document.getAnimations().forEach(a => {"
                    " a.pause(); a.currentTime = t; })",
                    t,
                )
                stage.screenshot(path=str(shot))
                frames.append(Image.open(shot).convert("RGB"))
                if i == 0:
                    frames[0].save(out / f"{state}.png")

            # 全コマを 1 つのパレットに揃えてから保存する。コマごとに
            # ローカルパレットを持たせると GIF が倍以上に膨らむため
            base = frames[0].quantize(colors=32, method=Image.Quantize.MEDIANCUT)
            paletted = [base] + [f.quantize(palette=base) for f in frames[1:]]
            paletted[0].save(
                out / f"{state}.gif",
                save_all=True,
                append_images=paletted[1:],
                duration=int(duration * 1000 / count),
                loop=0,
                optimize=True,
            )
            size_kb = (out / f"{state}.gif").stat().st_size // 1024
            print(f"  {state:<6} {count:>2} frames / {duration}s  ({size_kb} KB)")

        browser.close()

    shot.unlink(missing_ok=True)
    print(f"wrote {out}/<state>.gif + <state>.png")


if __name__ == "__main__":
    main()
