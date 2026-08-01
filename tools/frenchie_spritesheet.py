#!/usr/bin/env python3
"""32x32 白黒フレンチブルドッグのドット絵スプライトシート生成スクリプト.

5 つの状態 (idle / walk / work / done / sleep) を各 3〜4 フレームで描き、
スプライトシート・個別フレーム・拡大プレビュー・状態ごとの GIF・
メタデータ JSON・プレビュー用 HTML を書き出す。

    pip install Pillow
    python tools/frenchie_spritesheet.py

絵は「シルエットを塗る → 自動で 1px の黒フチを付ける → 下端に影を入れる」を
パーツ単位のレイヤーで繰り返して組み立てている。パーツを重ねる順番がそのまま
前後関係になるので、頭が胴体に重なる部分にもきちんと輪郭線が入る。
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

# --------------------------------------------------------------------------
# 基本設定
# --------------------------------------------------------------------------

SIZE = 32  # 1 フレームの一辺 (px)

TRANSPARENT = "."
K = "K"  # 輪郭線・黒ブチ
D = "D"  # 濃いグレー (耳の内側など)
G = "G"  # 明るいグレー (影・マズル)
W = "W"  # 白い毛

PALETTE: dict[str, tuple[int, int, int, int]] = {
    TRANSPARENT: (0, 0, 0, 0),
    K: (26, 26, 32, 255),
    D: (70, 70, 82, 255),
    G: (168, 170, 182, 255),
    W: (248, 248, 250, 255),
}

INK = (K, D, G, W)  # 「何か塗られている」色の集合


# --------------------------------------------------------------------------
# ドット絵用の極小キャンバス
# --------------------------------------------------------------------------


class Canvas:
    """文字 1 つ = 1 ドットのグリッド."""

    def __init__(self, w: int = SIZE, h: int = SIZE) -> None:
        self.w = w
        self.h = h
        self.g = [[TRANSPARENT] * w for _ in range(h)]

    # -- 基本操作 ---------------------------------------------------------
    def inside(self, x: int, y: int) -> bool:
        return 0 <= x < self.w and 0 <= y < self.h

    def get(self, x: int, y: int) -> str:
        return self.g[y][x] if self.inside(x, y) else TRANSPARENT

    def put(self, x, y, c: str, over: tuple[str, ...] | None = None) -> None:
        """over を指定すると、その色の上にしか塗らない (クリッピング)."""
        x, y = int(round(x)), int(round(y))
        if not self.inside(x, y):
            return
        if over is not None and self.g[y][x] not in over:
            return
        self.g[y][x] = c

    def ellipse(self, cx, cy, rx, ry, c: str, over: tuple[str, ...] | None = None) -> None:
        for y in range(math.floor(cy - ry), math.ceil(cy + ry) + 1):
            for x in range(math.floor(cx - rx), math.ceil(cx + rx) + 1):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                    self.put(x, y, c, over)

    def rect(self, x0, y0, x1, y1, c: str, over: tuple[str, ...] | None = None) -> None:
        for y in range(int(round(y0)), int(round(y1)) + 1):
            for x in range(int(round(x0)), int(round(x1)) + 1):
                self.put(x, y, c, over)

    def blit(self, other: "Canvas") -> None:
        """透明でないドットだけを上書きコピーする."""
        for y in range(self.h):
            for x in range(self.w):
                c = other.g[y][x]
                if c != TRANSPARENT:
                    self.g[y][x] = c

    # -- 仕上げ -----------------------------------------------------------
    def shade_bottom(self) -> None:
        """白い毛の下端 1px をグレーにして立体感を出す."""
        for y in range(self.h):
            for x in range(self.w):
                if self.g[y][x] == W and self.get(x, y + 1) == TRANSPARENT:
                    self.g[y][x] = G

    def outline(self) -> None:
        """塗られた領域の外周 (4 近傍) に黒フチを足す."""
        edge = []
        for y in range(self.h):
            for x in range(self.w):
                if self.g[y][x] != TRANSPARENT:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if self.get(x + dx, y + dy) in INK:
                        edge.append((x, y))
                        break
        for x, y in edge:
            self.g[y][x] = K

    def to_image(self) -> Image.Image:
        img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        px = img.load()
        for y in range(self.h):
            for x in range(self.w):
                px[x, y] = PALETTE[self.g[y][x]]
        return img


def finish(layer: Canvas, shade: bool = True) -> Canvas:
    """1 パーツ分のレイヤーに影とフチを入れる."""
    if shade:
        layer.shade_bottom()
    layer.outline()
    return layer


# --------------------------------------------------------------------------
# ポーズ定義
# --------------------------------------------------------------------------


@dataclass
class Pose:
    """立ち / 座りポーズのパラメータ (数値は全部ドット単位)."""

    dy: float = 0.0  # 全体の上下オフセット (ジャンプ用)

    body_cx: float = 15.5
    body_cy: float = 23.0
    body_rx: float = 6.0
    body_ry: float = 5.0

    head_cx: float = 15.5
    head_cy: float = 12.5
    head_rx: float = 7.0
    head_ry: float = 6.0

    ear_ry: float = 4.0
    ear_out: float = 0.0  # 耳の開き具合
    ear_dy_l: float = 0.0
    ear_dy_r: float = 0.0

    eyes: str = "open"  # open / closed / happy
    eye_l_dy: float = 0.0
    eye_r_dy: float = 0.0
    tongue: bool = False

    paw_l: tuple[float, float] = (12.5, 27.5)
    paw_r: tuple[float, float] = (18.5, 27.5)
    tail: tuple[float, float] = (22.2, 22.0)


def draw_eye(cv: Canvas, x0: int, y0: int, style: str) -> None:
    """3x3 の目. 黒ブチの上に来たときは自動でグレー目にして見えるようにする."""
    x0, y0 = int(round(x0)), int(round(y0))
    dark_bg = cv.get(x0 + 1, y0 + 1) == K
    main = G if dark_bg else K

    if style == "closed":  # ∪ … 寝ている / 目を閉じている
        cv.put(x0, y0 + 1, main)
        cv.put(x0 + 1, y0 + 2, main)
        cv.put(x0 + 2, y0 + 1, main)
        return
    if style == "happy":  # ^ … 嬉しい
        cv.put(x0, y0 + 2, main)
        cv.put(x0 + 1, y0 + 1, main)
        cv.put(x0 + 2, y0 + 2, main)
        return

    cv.rect(x0, y0, x0 + 2, y0 + 2, main)  # open
    if dark_bg:
        cv.put(x0 + 1, y0 + 1, K)  # 瞳
    cv.put(x0, y0, W)  # ハイライト


def build_dog(p: Pose) -> Canvas:
    """front-view のフレンチブルドッグを 1 フレーム分描く."""
    base = Canvas()
    dy = p.dy

    # --- しっぽ (いちばん奥) ---
    lay = Canvas()
    lay.ellipse(p.tail[0], p.tail[1] + dy, 1.9, 1.4, W)
    base.blit(finish(lay))

    # --- 耳 (頭の後ろ) ---
    lay = Canvas()
    for side in (-1, 1):
        ex = p.head_cx + side * (5.0 + p.ear_out)
        ey = p.head_cy - 6.5 + (p.ear_dy_l if side < 0 else p.ear_dy_r) + dy
        lay.ellipse(ex, ey, 2.6, p.ear_ry, K)
        lay.ellipse(ex + side * 0.4, ey + 0.8, 1.1, max(1.2, p.ear_ry - 2.0), D)
    base.blit(finish(lay, shade=False))

    # --- 胴体 ---
    lay = Canvas()
    lay.ellipse(p.body_cx, p.body_cy + dy, p.body_rx, p.body_ry, W)
    lay.ellipse(  # 背中側の黒ブチ
        p.body_cx + 3.6, p.body_cy + dy - 1.2, p.body_rx * 0.62, p.body_ry * 0.85, K, over=(W,)
    )
    base.blit(finish(lay))

    # --- 前あし ---
    lay = Canvas()
    for paw in (p.paw_l, p.paw_r):
        lay.ellipse(paw[0], paw[1] + dy, 2.3, 1.8, W)
    base.blit(finish(lay))
    for paw in (p.paw_l, p.paw_r):  # 指の切れ込み
        base.put(paw[0], paw[1] + dy + 0.5, G, over=(W,))
        base.put(paw[0], paw[1] + dy + 1.5, G, over=(W, G))

    # --- 頭 ---
    lay = Canvas()
    hx, hy = p.head_cx, p.head_cy + dy
    lay.ellipse(hx, hy, p.head_rx, p.head_ry, W)
    # 額の黒ブチ。目にかからない高さで止めて、左右非対称にしてブチ犬らしく
    lay.ellipse(hx - 2.2, hy - 7.0, 6.2, 3.6, K, over=(W,))
    # マズル: 下にずらした同じ楕円を白で重ね、上辺 1px だけ影を残す = 鼻の上のシワ
    lay.ellipse(hx, hy + 3.0, 4.8, 3.0, G, over=(W, K))
    lay.ellipse(hx, hy + 3.6, 4.8, 3.0, W, over=(W, K, G))

    draw_eye(lay, hx - 4.5, hy - 2.5 + p.eye_l_dy, p.eyes)
    draw_eye(lay, hx + 2.5, hy - 2.5 + p.eye_r_dy, p.eyes)

    lay.ellipse(hx, hy + 2.0, 2.1, 1.1, K)  # 鼻
    lay.put(hx - 1.5, hy + 1.5, W, over=(K,))  # 鼻のツヤ

    my = hy + 3.5  # 口 (小さい w)
    for ox in (-0.5, 0.5):
        lay.put(hx + ox, my, K, over=(W, G))
    for ox in (-1.5, 1.5):
        lay.put(hx + ox, my + 1, K, over=(W, G))
    if p.tongue:
        lay.rect(hx - 0.5, my + 1, hx + 0.5, my + 2, G)
        lay.put(hx - 0.5, my + 2, D, over=(G,))
        lay.put(hx + 0.5, my + 2, D, over=(G,))

    base.blit(finish(lay))
    return base


# --------------------------------------------------------------------------
# 小物 (Zzz・考え中のドット・キラキラ)
# --------------------------------------------------------------------------

Z_SMALL = ("XXX", ".X.", "XXX")
Z_BIG = ("XXXX", "..X.", ".X..", "XXXX")


def draw_glyph(cv: Canvas, rows: tuple[str, ...], x: int, y: int, c: str = W) -> None:
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch != ".":
                cv.put(x + i, y + j, c)


def sparkle(cv: Canvas, x: int, y: int, c: str = W) -> None:
    cv.put(x, y, c)
    cv.put(x - 1, y, c)
    cv.put(x + 1, y, c)
    cv.put(x, y - 1, c)
    cv.put(x, y + 1, c)


# --------------------------------------------------------------------------
# 各ステートのフレーム生成
# --------------------------------------------------------------------------


def frames_idle() -> list[Canvas]:
    """待機: 座って尻尾をふりふり + たまにまばたき."""
    wag = [(22.6, 22.4), (23.2, 21.2), (23.6, 22.2), (23.2, 21.2)]
    out = []
    for i in range(4):
        breath = 0.0 if i % 2 == 0 else -0.4  # ゆっくり呼吸
        p = Pose(
            dy=breath,
            body_ry=5.0 + (0.0 if i % 2 == 0 else 0.3),
            tail=wag[i],
            eyes="closed" if i == 3 else "open",
            ear_dy_l=0.0 if i % 2 == 0 else 0.3,
            ear_dy_r=0.0 if i % 2 == 0 else 0.3,
        )
        out.append(build_dog(p))
    return out


def frames_walk() -> list[Canvas]:
    """歩行: 上下にはずみながら前あしを交互に上げる."""
    steps = [
        ((11.8, 26.3), (18.8, 27.5), -1.0),
        ((12.5, 27.5), (18.5, 27.5), 0.0),
        ((12.2, 27.5), (19.2, 26.3), -1.0),
        ((12.5, 27.5), (18.5, 27.5), 0.0),
    ]
    out = []
    for i, (pl, pr, bob) in enumerate(steps):
        p = Pose(
            dy=bob,
            body_rx=5.7,
            tail=(23.4, 20.6 + (0.0 if i % 2 else -0.4)),
            paw_l=pl,
            paw_r=pr,
            ear_dy_l=0.6 if bob else 0.0,
            ear_dy_r=0.6 if bob else 0.0,
            ear_out=0.3 if bob else 0.0,
        )
        cv = build_dog(p)
        if bob:  # 足元のほこり
            cv.put(8, 30, G)
            cv.put(23, 30, G)
        out.append(cv)
    return out


def frames_work() -> list[Canvas]:
    """作業中: 首をかしげて考える. 右上のドットが増えていく."""
    tilts = [0.0, 1.0, 2.0, 1.0]
    dots = [1, 2, 3, 3]
    out = []
    for tilt, n in zip(tilts, dots):
        p = Pose(
            head_cx=15.5 - tilt * 0.6,
            head_cy=12.5 + tilt * 0.15,
            ear_dy_l=tilt * 0.5,
            ear_dy_r=-tilt * 0.3,
            ear_out=tilt * 0.25,
            eye_l_dy=tilt * 0.5,
            eye_r_dy=-tilt * 0.5,
            tail=(22.8, 22.6),
            paw_l=(12.0, 27.5),
            paw_r=(18.2, 27.5),
        )
        cv = build_dog(p)
        lay = Canvas()
        for i, (x, y) in enumerate(((25, 8), (27, 5), (29, 2))):
            if i < n:
                lay.put(x, y, W)
                lay.put(x + 1, y, W)
                lay.put(x, y + 1, W)
                lay.put(x + 1, y + 1, W)
        cv.blit(finish(lay, shade=False))
        out.append(cv)
    return out


def frames_done() -> list[Canvas]:
    """完了: しゃがむ → 飛ぶ → 頂点 → 着地."""
    out = []

    # 0: しゃがみ (つぶれる)
    p0 = Pose(
        dy=1.0,
        body_ry=4.2,
        body_rx=6.5,
        body_cy=24.2,
        head_cy=14.2,
        head_ry=5.6,
        head_rx=7.2,
        ear_ry=3.4,
        ear_dy_l=1.0,
        ear_dy_r=1.0,
        eyes="happy",
        paw_l=(11.8, 28.2),
        paw_r=(19.2, 28.2),
        tail=(22.8, 23.2),
    )
    out.append(build_dog(p0))

    # 1: 踏み切り (のびる)
    p1 = Pose(
        dy=-4.0,
        body_ry=5.6,
        body_rx=5.4,
        head_ry=6.2,
        head_rx=6.6,
        ear_ry=4.6,
        ear_dy_l=-1.0,
        ear_dy_r=-1.0,
        eyes="happy",
        tongue=True,
        paw_l=(12.8, 28.0),
        paw_r=(18.2, 28.0),
        tail=(23.2, 21.0),
    )
    cv1 = build_dog(p1)
    for x in (7, 24):  # 砂ぼこり
        cv1.put(x, 30, G)
        cv1.put(x + (1 if x < 16 else -1), 31, G)
    out.append(cv1)

    # 2: 頂点 (足をたたんで空中)
    p2 = Pose(
        dy=-6.0,
        body_ry=5.2,
        body_rx=6.0,
        ear_dy_l=-1.4,
        ear_dy_r=-1.4,
        ear_out=1.0,
        eyes="happy",
        tongue=True,
        paw_l=(10.6, 26.0),
        paw_r=(20.4, 26.0),
        tail=(23.6, 20.4),
    )
    cv2 = build_dog(p2)
    lay = Canvas()
    sparkle(lay, 4, 8)
    sparkle(lay, 28, 6)
    sparkle(lay, 26, 20)
    cv2.blit(finish(lay, shade=False))
    out.append(cv2)

    # 3: 着地 (軽くつぶれる)
    p3 = Pose(
        dy=0.0,
        body_ry=4.7,
        body_rx=6.3,
        head_cy=13.0,
        ear_dy_l=0.4,
        ear_dy_r=0.4,
        eyes="happy",
        paw_l=(12.0, 27.8),
        paw_r=(19.0, 27.8),
        tail=(23.0, 22.0),
    )
    cv3 = build_dog(p3)
    cv3.put(7, 29, G)
    cv3.put(24, 29, G)
    out.append(cv3)
    return out


def frames_sleep() -> list[Canvas]:
    """スリープ: 丸まってすやすや. 呼吸で少しふくらむ + Zzz."""
    out = []
    for i, breath in enumerate((0.0, 0.6, 0.3)):
        base = Canvas()

        # しっぽを体に巻きつける
        lay = Canvas()
        lay.ellipse(24.6, 22.6 - breath * 0.5, 2.1, 1.6, W)
        base.blit(finish(lay))

        # 耳 (頭より奥。寝ているので少しねかせる)
        lay = Canvas()
        lay.ellipse(6.0, 15.8, 2.5, 2.7, K)
        lay.ellipse(5.8, 16.2, 1.1, 1.4, D)
        lay.ellipse(12.6, 14.6, 2.4, 2.9, K)
        lay.ellipse(12.8, 15.0, 1.1, 1.5, D)
        base.blit(finish(lay, shade=False))

        # 丸まった胴体
        lay = Canvas()
        lay.ellipse(17.6, 24.2 - breath, 8.2, 4.6 + breath, W)
        lay.ellipse(20.4, 22.0 - breath, 5.0, 3.4, K, over=(W,))  # 背中の黒ブチ
        base.blit(finish(lay))

        # 体にあずけた頭
        lay = Canvas()
        hx, hy = 9.6, 20.8 - breath * 0.5
        lay.ellipse(hx, hy, 5.8, 5.2, W)
        lay.ellipse(hx - 0.4, hy - 5.4, 5.4, 3.4, K, over=(W,))  # 額の黒ブチ
        lay.ellipse(hx - 1.0, hy + 2.2, 4.4, 2.6, G, over=(W, K))  # マズル
        lay.ellipse(hx - 1.0, hy + 2.7, 4.4, 2.6, W, over=(W, K, G))
        draw_eye(lay, hx - 4.4, hy - 1.6, "closed")
        draw_eye(lay, hx + 1.4, hy - 2.0, "closed")
        lay.ellipse(hx - 3.6, hy + 2.0, 1.7, 1.0, K)  # 鼻 (左向き)
        lay.put(hx - 4.6, hy + 1.6, W, over=(K,))
        base.blit(finish(lay))

        # あごの下にたたんだ前あし
        lay = Canvas()
        lay.ellipse(14.8, 27.0, 2.5, 1.7, W)
        base.blit(finish(lay))
        base.put(14.8, 27.6, G, over=(W,))

        # Zzz (フレームごとに上へ)
        lay = Canvas()
        draw_glyph(lay, Z_SMALL, 23, 11 - i)
        draw_glyph(lay, Z_BIG, 26, 6 - i)
        base.blit(finish(lay, shade=False))
        out.append(base)
    return out


STATES: dict[str, dict] = {
    "idle": {"build": frames_idle, "fps": 4, "label": "待機 (座って尻尾振り)"},
    "walk": {"build": frames_walk, "fps": 8, "label": "歩行"},
    "work": {"build": frames_work, "fps": 5, "label": "作業中 (首かしげ)"},
    "done": {"build": frames_done, "fps": 8, "label": "完了 (ジャンプ)"},
    "sleep": {"build": frames_sleep, "fps": 2, "label": "スリープ (丸まる)"},
}


# --------------------------------------------------------------------------
# 書き出し
# --------------------------------------------------------------------------


def scaled(img: Image.Image, factor: int) -> Image.Image:
    return img.resize((img.width * factor, img.height * factor), Image.NEAREST)


def flatten(img: Image.Image, bg: tuple[int, int, int]) -> Image.Image:
    """GIF 用に背景色でフラット化する (GIF の透過は扱いが面倒なので)."""
    out = Image.new("RGB", img.size, bg)
    out.paste(img, (0, 0), img)
    return out


def write_preview_html(path: Path, sheet_name: str, cols: int, scale: int) -> None:
    cards, styles = [], []
    for row, (name, meta) in enumerate(STATES.items()):
        n = len(meta["build"]())
        dur = round(n / meta["fps"], 3)
        styles.append(
            f"    .sp-{name}{{background-position-y:{-row * SIZE * scale}px;"
            f"animation:run-{name} {dur}s steps({n}) infinite}}\n"
            f"    @keyframes run-{name}{{to{{background-position-x:{-n * SIZE * scale}px}}}}"
        )
        cards.append(
            f'    <figure class="card"><div class="sprite sp-{name}"></div>'
            f'<figcaption><b>{name}</b><br>{meta["label"]}<br>'
            f'<small>{n} frames / {meta["fps"]}fps</small></figcaption></figure>'
        )
    html = f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>French Bulldog Sprite Preview</title>
<style>
    body{{margin:0;padding:32px;background:#12131f;color:#fff;
        font-family:system-ui,-apple-system,"Hiragino Sans","Noto Sans JP",sans-serif}}
    h1{{font-size:20px;margin:0 0 20px}}
    .grid{{display:flex;flex-wrap:wrap;gap:18px}}
    .card{{margin:0;background:#ffffff10;border:1px solid #ffffff22;border-radius:14px;
        padding:14px;text-align:center;width:{SIZE * scale + 28}px}}
    .sprite{{width:{SIZE * scale}px;height:{SIZE * scale}px;
        background-image:url("{sheet_name}");
        background-size:{cols * SIZE * scale}px {len(STATES) * SIZE * scale}px;
        image-rendering:pixelated}}
    figcaption{{margin-top:10px;font-size:12px;line-height:1.6;color:#ffffffcc}}
    small{{color:#ffffff88}}
{chr(10).join(styles)}
</style>
</head>
<body>
<h1>🐶 French Bulldog — 32x32 sprite sheet</h1>
<div class="grid">
{chr(10).join(cards)}
</div>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="32x32 白黒フレンチブルドッグのスプライト生成")
    ap.add_argument("-o", "--out", default="assets/frenchie", help="出力ディレクトリ")
    ap.add_argument("-s", "--scale", type=int, default=8, help="プレビューの拡大率")
    ap.add_argument("--no-gif", action="store_true", help="GIF を書き出さない")
    ap.add_argument("--gif-bg", default="#1a1b3a", help="GIF の背景色")
    args = ap.parse_args()

    out = Path(args.out)
    (out / "frames").mkdir(parents=True, exist_ok=True)

    built = {name: meta["build"]() for name, meta in STATES.items()}
    cols = max(len(f) for f in built.values())
    rows = len(built)

    sheet = Image.new("RGBA", (cols * SIZE, rows * SIZE), (0, 0, 0, 0))
    meta_states = {}

    for row, (name, canvases) in enumerate(built.items()):
        for col, cv in enumerate(canvases):
            img = cv.to_image()
            sheet.paste(img, (col * SIZE, row * SIZE))
            img.save(out / "frames" / f"{name}_{col}.png")
        meta_states[name] = {
            "row": row,
            "frames": len(canvases),
            "fps": STATES[name]["fps"],
            "label": STATES[name]["label"],
            "loop": name != "done",
        }

    sheet.save(out / "frenchie_sheet.png")
    scaled(sheet, args.scale).save(out / f"frenchie_sheet@{args.scale}x.png")

    (out / "frenchie.json").write_text(
        json.dumps(
            {
                "image": "frenchie_sheet.png",
                "frameWidth": SIZE,
                "frameHeight": SIZE,
                "columns": cols,
                "rows": rows,
                "states": meta_states,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    if not args.no_gif:
        bg = args.gif_bg.lstrip("#")
        rgb = tuple(int(bg[i : i + 2], 16) for i in (0, 2, 4))
        for name, canvases in built.items():
            imgs = [flatten(scaled(cv.to_image(), args.scale), rgb) for cv in canvases]
            imgs[0].save(
                out / f"{name}.gif",
                save_all=True,
                append_images=imgs[1:],
                duration=int(1000 / STATES[name]["fps"]),
                loop=0,
            )

    write_preview_html(out / "preview.html", "frenchie_sheet.png", cols, args.scale)

    print(f"wrote {out}/frenchie_sheet.png  ({cols * SIZE}x{rows * SIZE}, {rows} states)")
    for name, canvases in built.items():
        print(f"  {name:<6} {len(canvases)} frames @ {STATES[name]['fps']}fps")


if __name__ == "__main__":
    main()
