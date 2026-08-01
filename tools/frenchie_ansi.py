#!/usr/bin/env python3
"""ドット絵をターミナル用の ANSI 文字列に焼いておくスクリプト.

ステータスラインは新しいメッセージのたびに走るので、毎回 Pillow を読み込んで
スプライトを組み立て直すと遅い。そこで全フレームをあらかじめ ANSI 文字列に
変換して JSON に書き出しておき、表示側 (tools/frenchie_statusline.py) は
標準ライブラリだけで読んで出すだけにする。

    python tools/frenchie_ansi.py        # assets/frenchie/frenchie_ansi.json

1 文字で上下 2 ドットを表す半角ブロック (▀) を使う。ターミナルの 1 セルは
だいたい「横 1 : 縦 2」なので、これでドットがほぼ正方形に見える。

サイズは 2 種類:

    full     32x32 をそのまま      → 16 行
    compact  状態ごとに顔まわりを切り出す → 9 行

1/2 に縮小する案は、2x2 を多数決で潰すと顔が崩れて犬に見えなくなったので
やめた (ドット絵は非整数倍の縮小に耐えない)。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from frenchie_spritesheet import PALETTE, STATES, TRANSPARENT, Canvas

# 状態ごとの切り出し範囲 (x0, y0, x1, y1 / 終端は含まない)。
# 立ちポーズは顔まわり、寝ポーズは丸まった体の部分を取る。
COMPACT_CROP = {
    "idle": (6, 0, 26, 18),
    "walk": (6, 0, 26, 18),
    "work": (5, 0, 31, 18),  # 考え中のドットまで入れる
    "done": (4, 0, 28, 18),
    "sleep": (2, 13, 30, 31),
}

RESET = "\x1b[0m"


def crop(cv: Canvas, box: tuple[int, int, int, int]) -> list[list[str]]:
    x0, y0, x1, y1 = box
    return [row[x0:x1] for row in cv.g[y0:y1]]


def fg(color: str) -> str:
    r, g, b, _ = PALETTE[color]
    return f"\x1b[38;2;{r};{g};{b}m"


def bg(color: str) -> str:
    r, g, b, _ = PALETTE[color]
    return f"\x1b[48;2;{r};{g};{b}m"


def to_ansi(grid: list[list[str]]) -> str:
    """上下 2 ドットを 1 文字 (▀ / ▄) に詰めて ANSI 文字列にする.

    色が変わったときだけエスケープを出す。全セルに出すと JSON が 3 倍以上に
    膨らむし、端末に流す量も増えて表示が遅くなる。
    """
    lines = []
    for y in range(0, len(grid), 2):
        top = grid[y]
        bottom = grid[y + 1] if y + 1 < len(grid) else [TRANSPARENT] * len(top)
        out: list[str] = []
        cur_fg = cur_bg = None
        for x in range(len(top)):
            t, b = top[x], bottom[x]
            if t == TRANSPARENT and b == TRANSPARENT:  # 透明は端末の地を見せる
                if cur_fg is not None or cur_bg is not None:
                    out.append(RESET)
                    cur_fg = cur_bg = None
                out.append(" ")
                continue
            # 上が空なら ▄ にして下半分だけを前景色で塗る
            char, want_fg, want_bg = ("▀", t, b) if t != TRANSPARENT else ("▄", b, None)
            if t != TRANSPARENT and b == TRANSPARENT:
                want_bg = None
            if want_fg != cur_fg:
                out.append(fg(want_fg))
                cur_fg = want_fg
            if want_bg != cur_bg:
                out.append(bg(want_bg) if want_bg else "\x1b[49m")
                cur_bg = want_bg
            out.append(char)
        lines.append("".join(out) + RESET)
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="ドット絵を ANSI 文字列に焼く")
    ap.add_argument(
        "-o", "--out", default="assets/frenchie/frenchie_ansi.json", help="出力先"
    )
    args = ap.parse_args()

    data: dict[str, dict[str, list[str]]] = {"full": {}, "compact": {}}
    for name, meta in STATES.items():
        canvases = meta["build"]()
        data["full"][name] = [to_ansi(cv.g) for cv in canvases]
        data["compact"][name] = [to_ansi(crop(cv, COMPACT_CROP[name])) for cv in canvases]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "fps": {name: meta["fps"] for name, meta in STATES.items()},
        "frames": data,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    rows = {k: len(v["idle"][0].split("\n")) for k, v in data.items()}
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")
    for size, n in rows.items():
        print(f"  {size:<8} {n} 行")


if __name__ == "__main__":
    main()
