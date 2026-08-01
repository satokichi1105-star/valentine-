#!/usr/bin/env python3
"""白黒フレンチブルドッグの SVG フラットベクター版を生成するスクリプト.

ドット絵版 (tools/frenchie_spritesheet.py) と同じ 5 状態
(idle / walk / work / done / sleep) を、フレーム画像ではなく
「パーツをグループ分けした 1 枚の SVG + CSS アニメーション」で表現する。

    python tools/frenchie_svg.py

出力 (既定で assets/frenchie-svg/):

    frenchie-<state>.svg  状態ごとの単体ファイル。<img src> でそのまま動く
    frenchie.svg          全状態入り。ルートの class を frx-walk などに
                          差し替えると切り替わる (インライン埋め込み用)
    preview.html          5 状態を並べた確認ページ + 切り替えデモ

インラインで貼っても埋め込み先を壊さないよう、クラス名・keyframes 名は
すべて frx- 始まり、CSS セレクタは .frenchie 配下に閉じ、clipPath の id は
ファイルごとにユニークにしてある。
"""

from __future__ import annotations

import argparse
from pathlib import Path

# --------------------------------------------------------------------------
# 色。CSS 変数にしてあるので埋め込み先から上書きもできる
# --------------------------------------------------------------------------

COLORS = {
    "ink": "#1b1b24",  # 輪郭線・瞳・鼻
    "dark": "#3c3c4a",  # 黒い毛 (輪郭線と分けて潰れないように)
    "dark2": "#5d5d70",  # 耳の内側・目のふち・閉じ目
    "fur": "#fbfbfd",  # 白い毛
    "shade": "#dcdce6",  # 白い毛の影
}

VIEW = 200  # viewBox は 0 0 200 200

# --------------------------------------------------------------------------
# パーツの形 (すべて viewBox 座標。左右対称のものは x=100 が軸)
# --------------------------------------------------------------------------

HEAD_D = (
    "M100 30 C136 30 158 52 158 80 C158 104 145 121 126 129 "
    "C117 132 108 134 100 134 C92 134 83 132 74 129 "
    "C55 121 42 104 42 80 C42 52 64 30 100 30 Z"
)

# 額から目の上までを覆う黒いマスク。下辺をわざと波打たせている
MASK_D = (
    "M30 8 H170 V92 C156 108 142 96 132 104 C122 112 112 104 100 106 "
    "C88 108 78 112 68 104 C58 96 44 108 30 92 Z"
)

# 額を通る白いブレーズ。写真に合わせて少しだけ左に寄せている
BLAZE_D = (
    "M99 28 C110 31 113 46 109 60 C106 72 105 86 107 104 "
    "L91 104 C89 86 91 72 89 60 C87 46 89 31 99 28 Z"
)

NOSE_D = (
    "M100 88 C110 88 116 94 116 100 C116 107 109 113 100 113 "
    "C91 113 84 107 84 100 C84 94 90 88 100 88 Z"
)

MOUTH_D = "M100 113 V124 M100 124 C95 132 84 132 80 124 M100 124 C105 132 116 132 120 124"

# 耳。基部を原点にして上に伸びる形を作り、左右で反転して使う
EAR_D = "M-20 6 C-27 -18 -21 -50 -5 -59 C2 -62 9 -58 13 -49 C21 -32 23 -12 19 6 Z"

# 胴体の背中側の黒ブチ
BODY_PATCH_D = (
    "M152 104 C163 130 158 162 138 178 C119 190 102 182 98 168 "
    "C93 150 105 128 120 112 C131 101 144 96 152 104 Z"
)

SPARK_D = "M0 -13 Q2 -2 13 0 Q2 2 0 13 Q-2 2 -13 0 Q-2 -2 0 -13 Z"

Z_D = "M0 0 H22 V7 L10 19 H22 V26 H0 V19 L12 7 H0 Z"

# 丸まった寝姿 (立ちポーズとは別構成)
CURL_BODY_D = (
    "M62 176 C40 176 26 162 30 146 C34 128 52 118 78 116 "
    "C104 114 136 116 156 126 C176 136 180 156 168 168 "
    "C158 178 138 180 118 178 Z"
)
CURL_HEAD_D = (
    "M56 100 C80 100 96 116 96 136 C96 156 80 170 56 170 "
    "C32 170 18 156 18 136 C18 116 32 100 56 100 Z"
)
CURL_MASK_D = "M6 90 H102 V144 C88 154 72 142 56 146 C40 150 20 144 6 136 Z"


# --------------------------------------------------------------------------
# マークアップ組み立て
# --------------------------------------------------------------------------


def ear(side: str) -> str:
    """立ちポーズの耳 1 つ。side は 'l' / 'r'.

    配置用の <g> と、アニメーション用の <g> を分けているのが大事なところ。
    transform 属性を持つ要素に CSS の transform-origin を効かせると、原点の
    ぶんだけ二重に移動してしまうので、回すグループには transform 属性を
    持たせない。右耳は scale(-1,1) の中にいるので、回転角は左右対称になる。
    """
    tf = (
        "translate(66,58) rotate(-17) scale(.9)"
        if side == "l"
        else "translate(134,58) scale(-1,1) rotate(-17) scale(.9)"
    )
    return f"""      <g transform="{tf}">
        <g class="frx-ear frx-ear-{side}">
          <path class="frx-line" fill="var(--frx-dark)" d="{EAR_D}"/>
          <path fill="var(--frx-dark2)" d="{EAR_D}" transform="translate(0,-14) scale(.54)"/>
        </g>
      </g>"""


def eyes() -> str:
    """まん丸の目と笑った目 (^) の両方を持たせて、state で出し分ける."""
    out = []
    for cx in (70, 130):
        out.append(
            f"""        <g class="frx-eye">
          <circle cx="{cx}" cy="76" r="14" fill="var(--frx-dark2)"/>
          <circle cx="{cx}" cy="76" r="11" fill="var(--frx-ink)"/>
          <circle cx="{cx - 4}" cy="72" r="3.6" fill="#fff"/>
          <circle cx="{cx + 3}" cy="81" r="1.8" fill="#fff" opacity=".7"/>
        </g>"""
        )
        out.append(
            f"""        <path class="frx-eye-happy" fill="none" stroke="var(--frx-dark2)"
          stroke-width="6" stroke-linecap="round" d="M{cx - 12} 80 Q{cx} 65 {cx + 12} 80"/>"""
        )
    return "\n".join(out)


def head(uid: str) -> str:
    return f"""      <g class="frx-head">
        <path class="frx-line" fill="var(--frx-fur)" d="{HEAD_D}"/>
        <g clip-path="url(#{uid}-head)">
          <path fill="var(--frx-dark)" d="{MASK_D}"/>
          <path fill="var(--frx-fur)" d="{BLAZE_D}"/>
          <ellipse cx="100" cy="103" rx="35" ry="25" fill="var(--frx-shade)"/>
          <ellipse cx="100" cy="107" rx="34" ry="24" fill="var(--frx-fur)"/>
        </g>
{eyes()}
        <path fill="var(--frx-ink)" d="{NOSE_D}"/>
        <ellipse cx="93" cy="99" rx="3.4" ry="4.2" fill="var(--frx-dark2)" opacity=".5"/>
        <ellipse cx="107" cy="99" rx="3.4" ry="4.2" fill="var(--frx-dark2)" opacity=".5"/>
        <path fill="none" stroke="var(--frx-ink)" stroke-width="3.4" stroke-linecap="round"
          d="{MOUTH_D}"/>
        <path class="frx-tongue" fill="var(--frx-shade)" stroke="var(--frx-ink)"
          stroke-width="3" stroke-linejoin="round"
          d="M91 126 H109 C109 137 102 143 100 143 C98 143 91 137 91 126 Z"/>
      </g>"""


def leg(side: str) -> str:
    cx = 78 if side == "l" else 122
    return f"""      <g class="frx-leg frx-leg-{side}">
        <ellipse class="frx-line" cx="{cx}" cy="170" rx="18" ry="13" fill="var(--frx-fur)"/>
        <path fill="none" stroke="var(--frx-shade)" stroke-width="3" stroke-linecap="round"
          d="M{cx - 5} 167 V177 M{cx + 5} 167 V177"/>
      </g>"""


def stand_pose(uid: str) -> str:
    return f"""    <g class="frx-pose frx-stand">
      <g class="frx-tail">
        <path class="frx-line" fill="var(--frx-dark)"
          d="M139 124 C151 117 163 123 162 134 C161 145 150 148 140 143 Z"/>
      </g>
{ear("l")}
{ear("r")}
      <g class="frx-body">
        <ellipse class="frx-line" cx="100" cy="138" rx="45" ry="40" fill="var(--frx-fur)"/>
        <g clip-path="url(#{uid}-body)">
          <path fill="var(--frx-dark)" d="{BODY_PATCH_D}"/>
        </g>
      </g>
{leg("l")}
{leg("r")}
{head(uid)}
    </g>"""


def curl_ear(x: int, y: int, rot: int) -> str:
    return f"""        <g transform="translate({x},{y}) rotate({rot})">
          <path class="frx-line" fill="var(--frx-dark)" d="{EAR_D}" transform="scale(.62)"/>
          <path fill="var(--frx-dark2)" d="{EAR_D}" transform="translate(0,-10) scale(.34)"/>
        </g>"""


def curl_pose(uid: str) -> str:
    """丸まって寝ているポーズ。頭を左に置いた横向き."""
    return f"""    <g class="frx-pose frx-curl">
      <g class="frx-breath">
        <path class="frx-line" fill="var(--frx-dark)"
          d="M168 142 C182 138 190 148 186 158 C182 167 170 168 164 161 Z"/>
{curl_ear(36, 116, -24)}
{curl_ear(78, 108, 12)}
        <path class="frx-line" fill="var(--frx-fur)" d="{CURL_BODY_D}"/>
        <g clip-path="url(#{uid}-curlbody)">
          <path fill="var(--frx-dark)"
            d="M92 110 C130 108 164 120 178 136 C186 148 180 162 168 168 L92 170 Z"/>
        </g>
        <path class="frx-line" fill="var(--frx-fur)" d="{CURL_HEAD_D}"/>
        <g clip-path="url(#{uid}-curlhead)">
          <path fill="var(--frx-dark)" d="{CURL_MASK_D}"/>
          <path fill="var(--frx-fur)"
            d="M52 96 C60 98 62 112 58 122 L46 120 C44 110 44 96 52 96 Z"/>
          <ellipse cx="42" cy="152" rx="29" ry="17" fill="var(--frx-shade)"/>
          <ellipse cx="42" cy="155" rx="29" ry="17" fill="var(--frx-fur)"/>
        </g>
        <path fill="none" stroke="var(--frx-dark2)" stroke-width="5" stroke-linecap="round"
          d="M32 134 Q41 143 50 134 M68 130 Q77 139 86 130"/>
        <ellipse cx="20" cy="150" rx="10" ry="8" fill="var(--frx-ink)"/>
        <ellipse class="frx-line" cx="84" cy="174" rx="17" ry="10" fill="var(--frx-fur)"/>
        <path fill="none" stroke="var(--frx-shade)" stroke-width="3" stroke-linecap="round"
          d="M84 170 V181"/>
      </g>
    </g>"""


def effects() -> str:
    dots = "\n".join(
        f'      <circle class="frx-dot frx-dot-{i}" cx="{cx}" cy="{cy}" r="{r}" '
        f'fill="var(--frx-fur)" stroke="var(--frx-ink)" stroke-width="3"/>'
        for i, (cx, cy, r) in enumerate(((150, 56, 5), (168, 38, 7), (187, 17, 9)))
    )
    sparks = "\n".join(
        f'      <g transform="translate({x},{y}) scale({s})">'
        f'<path class="frx-spark frx-spark-{i}" fill="var(--frx-fur)" d="{SPARK_D}"/></g>'
        for i, (x, y, s) in enumerate(((26, 60, 1.0), (176, 44, 1.25), (170, 132, 0.85)))
    )
    zzz = "\n".join(
        f'      <g transform="translate({x},{y}) scale({s})">'
        f'<path class="frx-zzz frx-zzz-{i}" fill="var(--frx-fur)" stroke="var(--frx-ink)" '
        f'stroke-width="4" stroke-linejoin="round" d="{Z_D}"/></g>'
        for i, (x, y, s) in enumerate(((112, 76, 0.55), (136, 48, 0.8), (164, 16, 1.05)))
    )
    return f"""    <g class="frx-fx frx-fx-dots">
{dots}
    </g>
    <g class="frx-fx frx-fx-sparks">
{sparks}
    </g>
    <g class="frx-fx frx-fx-zzz">
{zzz}
    </g>"""


# --------------------------------------------------------------------------
# CSS。{p} には状態セレクタ (".frx-idle " など) が入る
# --------------------------------------------------------------------------

BASE_CSS = f"""  svg.frenchie {{
    --frx-ink: {COLORS["ink"]};
    --frx-dark: {COLORS["dark"]};
    --frx-dark2: {COLORS["dark2"]};
    --frx-fur: {COLORS["fur"]};
    --frx-shade: {COLORS["shade"]};
  }}
  .frenchie .frx-line {{
    stroke: var(--frx-ink); stroke-width: 4; stroke-linejoin: round;
  }}
  .frenchie .frx-dog, .frenchie .frx-pose, .frenchie .frx-tail,
  .frenchie .frx-leg, .frenchie .frx-head, .frenchie .frx-body,
  .frenchie .frx-breath {{ transform-box: view-box; }}
  .frenchie .frx-dot, .frenchie .frx-spark, .frenchie .frx-zzz,
  .frenchie .frx-eye {{ transform-box: fill-box; transform-origin: center; }}
  .frenchie .frx-ear {{ transform-box: fill-box; transform-origin: 50% 100%; }}
  .frenchie .frx-dog {{ transform-origin: 100px 184px; }}
  .frenchie .frx-tail {{ transform-origin: 141px 141px; }}
  .frenchie .frx-head {{ transform-origin: 100px 128px; }}
  .frenchie .frx-body {{ transform-origin: 100px 178px; }}
  .frenchie .frx-leg-l {{ transform-origin: 78px 150px; }}
  .frenchie .frx-leg-r {{ transform-origin: 122px 150px; }}
  .frenchie .frx-breath {{ transform-origin: 100px 178px; }}
  .frenchie .frx-curl, .frenchie .frx-eye-happy,
  .frenchie .frx-tongue, .frenchie .frx-fx {{ display: none; }}
  @media (prefers-reduced-motion: reduce) {{
    .frenchie * {{ animation: none !important; }}
  }}"""

STATE_CSS = {
    "idle": """  {p}.frx-tail {{ animation: frx-idle-wag .8s ease-in-out infinite; }}
  {p}.frx-body {{ animation: frx-idle-breath 2.6s ease-in-out infinite; }}
  {p}.frx-head {{ animation: frx-idle-nod 2.6s ease-in-out infinite; }}
  {p}.frx-eye {{ animation: frx-idle-blink 4.4s infinite; }}
  @keyframes frx-idle-wag {{
    0%, 100% {{ transform: rotate(-20deg); }}
    50%      {{ transform: rotate(20deg); }}
  }}
  @keyframes frx-idle-breath {{
    0%, 100% {{ transform: scale(1, 1); }}
    50%      {{ transform: scale(1.015, 1.03); }}
  }}
  @keyframes frx-idle-nod {{
    0%, 100% {{ transform: translateY(0); }}
    50%      {{ transform: translateY(2px); }}
  }}
  @keyframes frx-idle-blink {{
    0%, 92%, 100% {{ transform: scaleY(1); }}
    95%           {{ transform: scaleY(.08); }}
  }}""",
    "walk": """  {p}.frx-dog {{ animation: frx-walk-bob .56s ease-in-out infinite; }}
  {p}.frx-leg-l {{ animation: frx-walk-step .56s ease-in-out infinite; }}
  {p}.frx-leg-r {{ animation: frx-walk-step .56s ease-in-out infinite;
    animation-delay: -.28s; }}
  {p}.frx-ear-l, {p}.frx-ear-r {{ animation: frx-walk-flap .56s ease-in-out infinite; }}
  {p}.frx-tail {{ animation: frx-walk-wag .28s ease-in-out infinite; }}
  @keyframes frx-walk-bob {{
    0%, 50%, 100% {{ transform: translateY(0); }}
    25%, 75%      {{ transform: translateY(-6px); }}
  }}
  @keyframes frx-walk-step {{
    0%, 100% {{ transform: rotate(16deg) translateY(-3px); }}
    50%      {{ transform: rotate(-16deg) translateY(0); }}
  }}
  @keyframes frx-walk-flap {{
    0%, 100% {{ transform: rotate(0deg); }}
    50%      {{ transform: rotate(7deg); }}
  }}
  @keyframes frx-walk-wag {{
    0%, 100% {{ transform: rotate(-14deg); }}
    50%      {{ transform: rotate(14deg); }}
  }}""",
    "work": """  {p}.frx-fx-dots {{ display: block; }}
  {p}.frx-head {{ animation: frx-work-tilt 2.8s ease-in-out infinite; }}
  {p}.frx-ear-l {{ animation: frx-work-ear-l 2.8s ease-in-out infinite; }}
  {p}.frx-ear-r {{ animation: frx-work-ear-r 2.8s ease-in-out infinite; }}
  {p}.frx-tail {{ animation: frx-work-wag 1.6s ease-in-out infinite; }}
  {p}.frx-dot {{ animation: frx-work-dot 1.8s ease-in-out infinite; opacity: 0; }}
  {p}.frx-dot-1 {{ animation-delay: .3s; }}
  {p}.frx-dot-2 {{ animation-delay: .6s; }}
  @keyframes frx-work-tilt {{
    0%, 15%, 100% {{ transform: rotate(0deg); }}
    45%, 75%      {{ transform: rotate(-13deg); }}
  }}
  @keyframes frx-work-ear-l {{
    0%, 15%, 100% {{ transform: rotate(0deg); }}
    45%, 75%      {{ transform: rotate(-17deg); }}
  }}
  @keyframes frx-work-ear-r {{
    0%, 15%, 100% {{ transform: rotate(0deg); }}
    45%, 75%      {{ transform: rotate(9deg); }}
  }}
  @keyframes frx-work-wag {{
    0%, 100% {{ transform: rotate(-8deg); }}
    50%      {{ transform: rotate(8deg); }}
  }}
  @keyframes frx-work-dot {{
    0%, 20%   {{ opacity: 0; transform: translateY(6px) scale(.6); }}
    45%       {{ opacity: 1; transform: translateY(0) scale(1); }}
    80%, 100% {{ opacity: 0; transform: translateY(-6px) scale(.9); }}
  }}""",
    "done": """  {p}.frx-eye {{ display: none; }}
  {p}.frx-eye-happy, {p}.frx-tongue, {p}.frx-fx-sparks {{ display: block; }}
  {p}.frx-dog {{ animation: frx-done-hop 1.1s cubic-bezier(.32,.72,.36,1) infinite; }}
  {p}.frx-leg-l {{ animation: frx-done-tuck-l 1.1s ease-in-out infinite; }}
  {p}.frx-leg-r {{ animation: frx-done-tuck-r 1.1s ease-in-out infinite; }}
  {p}.frx-ear-l, {p}.frx-ear-r {{ animation: frx-done-ear 1.1s ease-in-out infinite; }}
  {p}.frx-tail {{ animation: frx-done-wag .22s ease-in-out infinite; }}
  {p}.frx-spark {{ animation: frx-done-spark 1.1s ease-out infinite; opacity: 0; }}
  {p}.frx-spark-1 {{ animation-delay: .06s; }}
  {p}.frx-spark-2 {{ animation-delay: .12s; }}
  @keyframes frx-done-hop {{
    0%   {{ transform: translateY(0) scale(1, 1); }}
    14%  {{ transform: translateY(4px) scale(1.09, .89); }}
    32%  {{ transform: translateY(-24px) scale(.93, 1.1); }}
    50%  {{ transform: translateY(-30px) scale(1, 1); }}
    72%  {{ transform: translateY(0) scale(1.02, .98); }}
    82%  {{ transform: translateY(3px) scale(1.1, .88); }}
    100% {{ transform: translateY(0) scale(1, 1); }}
  }}
  @keyframes frx-done-tuck-l {{
    0%, 14%, 82%, 100% {{ transform: rotate(0deg) translateY(0); }}
    40%, 60%           {{ transform: rotate(26deg) translateY(-14px); }}
  }}
  @keyframes frx-done-tuck-r {{
    0%, 14%, 82%, 100% {{ transform: rotate(0deg) translateY(0); }}
    40%, 60%           {{ transform: rotate(-26deg) translateY(-14px); }}
  }}
  @keyframes frx-done-ear {{
    0%, 14%, 100% {{ transform: rotate(0deg); }}
    40%, 60%      {{ transform: rotate(-15deg) translateY(-4px); }}
  }}
  @keyframes frx-done-wag {{
    0%, 100% {{ transform: rotate(-18deg); }}
    50%      {{ transform: rotate(18deg); }}
  }}
  @keyframes frx-done-spark {{
    0%, 20%   {{ opacity: 0; transform: scale(.3) rotate(0deg); }}
    45%       {{ opacity: 1; transform: scale(1) rotate(35deg); }}
    75%, 100% {{ opacity: 0; transform: scale(.5) rotate(60deg); }}
  }}""",
    "sleep": """  {p}.frx-stand {{ display: none; }}
  {p}.frx-curl, {p}.frx-fx-zzz {{ display: block; }}
  {p}.frx-breath {{ animation: frx-sleep-breath 3.4s ease-in-out infinite; }}
  {p}.frx-zzz {{ animation: frx-sleep-zzz 3.4s ease-in-out infinite; opacity: 0; }}
  {p}.frx-zzz-1 {{ animation-delay: 1.1s; }}
  {p}.frx-zzz-2 {{ animation-delay: 2.2s; }}
  @keyframes frx-sleep-breath {{
    0%, 100% {{ transform: scale(1, 1); }}
    50%      {{ transform: scale(1.012, 1.035); }}
  }}
  @keyframes frx-sleep-zzz {{
    0%   {{ opacity: 0; transform: translate(0, 10px) scale(.8); }}
    25%  {{ opacity: 1; }}
    70%  {{ opacity: .9; }}
    100% {{ opacity: 0; transform: translate(10px, -18px) scale(1.1); }}
  }}""",
}

STATES = {
    "idle": "待機 (座って尻尾振り)",
    "walk": "歩行",
    "work": "作業中 (首かしげ)",
    "done": "完了 (ジャンプ)",
    "sleep": "スリープ (丸まる)",
}


def build_svg(state: str | None) -> str:
    """state を指定すると単体ファイル、None なら全状態入りを返す."""
    uid = f"frx-{state or 'all'}"
    css = "\n".join(
        STATE_CSS[s].format(p=f".frx-{s} ")
        for s in (STATES if state is None else [state])
    )
    root = f"frenchie frx-{state or 'idle'}"

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VIEW} {VIEW}"
  width="{VIEW}" height="{VIEW}" class="{root}" role="img"
  aria-label="French Bulldog">
  <style>
{BASE_CSS}
{css}
  </style>
  <defs>
    <clipPath id="{uid}-head"><path d="{HEAD_D}"/></clipPath>
    <clipPath id="{uid}-body"><ellipse cx="100" cy="138" rx="45" ry="40"/></clipPath>
    <clipPath id="{uid}-curlbody"><path d="{CURL_BODY_D}"/></clipPath>
    <clipPath id="{uid}-curlhead"><path d="{CURL_HEAD_D}"/></clipPath>
  </defs>
  <g class="frx-dog">
{stand_pose(uid)}
{curl_pose(uid)}
  </g>
{effects()}
</svg>
"""


def build_preview(files: dict[str, str], inline_svg: str) -> str:
    cards = "\n".join(
        f"""      <figure class="card">
        <img src="{files[s]}" alt="{s}" width="200" height="200">
        <figcaption><b>{s}</b><br>{label}</figcaption>
      </figure>"""
        for s, label in STATES.items()
    )
    buttons = "\n".join(f'        <button data-state="{s}">{s}</button>' for s in STATES)
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>French Bulldog — SVG flat</title>
<style>
  body {{ margin: 0; padding: 32px; background: #12131f; color: #fff;
    font-family: system-ui, -apple-system, "Hiragino Sans", "Noto Sans JP", sans-serif; }}
  h1 {{ font-size: 20px; margin: 0 0 6px; }}
  p.lead {{ margin: 0 0 22px; color: #ffffff99; font-size: 13px; line-height: 1.7; }}
  .grid {{ display: flex; flex-wrap: wrap; gap: 18px; margin-bottom: 34px; }}
  .card {{ margin: 0; padding: 14px; width: 228px; text-align: center;
    background: #ffffff10; border: 1px solid #ffffff22; border-radius: 16px; }}
  figcaption {{ margin-top: 8px; font-size: 12px; line-height: 1.6; color: #ffffffcc; }}
  .card.light {{ background: #eef0f6; }}
  .card.light figcaption {{ color: #33344a; }}
  .switch {{ display: flex; gap: 20px; align-items: center; padding: 18px;
    background: #ffffff10; border: 1px solid #ffffff22; border-radius: 16px;
    width: max-content; }}
  .switch svg {{ width: 220px; height: 220px; }}
  button {{ display: block; width: 100%; margin-bottom: 6px; padding: 7px 18px;
    background: #ffffff18; color: #fff; border: 1px solid #ffffff2a;
    border-radius: 9px; font: inherit; font-size: 13px; cursor: pointer; }}
  button[aria-pressed="true"] {{ background: #fff; color: #12131f; }}
</style>
</head>
<body>
<h1>🐶 French Bulldog — SVG flat vector</h1>
<p class="lead">上段は状態ごとの単体ファイルを &lt;img&gt; で読み込んだもの。<br>
下段は全状態入りの 1 枚をインラインし、ルートの class を差し替えて切り替えている。</p>
<div class="grid">
{cards}
  <figure class="card light">
    <img src="{files["idle"]}" alt="idle on light" width="200" height="200">
    <figcaption><b>明るい背景でも</b><br>輪郭線があるので崩れない</figcaption>
  </figure>
</div>
<div class="switch">
  <div id="host">{inline_svg}</div>
  <div>
{buttons}
  </div>
</div>
<script>
// 全状態入りの SVG はここに直接インラインしてある (file:// でも動くように)。
// 状態の切り替えはルートの class を差し替えるだけ。
const svg = document.querySelector("#host svg");
const buttons = document.querySelectorAll("button");
buttons.forEach(b => {{
  b.onclick = () => {{
    svg.setAttribute("class", "frenchie frx-" + b.dataset.state);
    buttons.forEach(o => o.setAttribute("aria-pressed", String(o === b)));
  }};
}});
buttons[0].setAttribute("aria-pressed", "true");
</script>
</body>
</html>
"""


def main() -> None:
    ap = argparse.ArgumentParser(description="白黒フレンチブルドッグの SVG 版を生成")
    ap.add_argument("-o", "--out", default="assets/frenchie-svg", help="出力ディレクトリ")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    files = {}
    for state in STATES:
        name = f"frenchie-{state}.svg"
        (out / name).write_text(build_svg(state), encoding="utf-8")
        files[state] = name
    (out / "frenchie.svg").write_text(build_svg(None), encoding="utf-8")
    (out / "preview.html").write_text(
        build_preview(files, build_svg(None)), encoding="utf-8"
    )

    total = sum((out / f).stat().st_size for f in files.values())
    print(f"wrote {out}/frenchie.svg + 状態別 {len(files)} 枚 (計 {total // 1024} KB)")
    for state, label in STATES.items():
        print(f"  {state:<6} {label}")


if __name__ == "__main__":
    main()
