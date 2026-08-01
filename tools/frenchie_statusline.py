#!/usr/bin/env python3
"""Claude Code のステータスラインにフレンチブルドッグを住まわせるスクリプト.

Claude Code は新しいアシスタントメッセージのたびにステータスラインの
コマンドを実行し、標準入力にセッション情報の JSON を渡してくる。
このスクリプトはそれを読んで、いまの状態に合ったコマを 1 枚描くだけ。

    # 状態を確認する (ターミナルで直接叩ける)
    python tools/frenchie_statusline.py --demo
    python tools/frenchie_statusline.py --state work

犬の状態はフック側が書いた状態ファイル (既定で
$CLAUDE_PROJECT_DIR/.claude/frenchie.state) から読む。設定方法は
assets/frenchie/README.md を参照。

依存は標準ライブラリのみ。ドット絵は tools/frenchie_ansi.py で
あらかじめ ANSI 文字列に焼いてあるので、毎回描き直すことはしない
(ステータスラインは頻繁に走るので、起動が重いと表示が遅れる)。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ANSI_JSON = Path(__file__).resolve().parent.parent / "assets/frenchie/frenchie_ansi.json"

STATES = ("idle", "walk", "work", "done", "sleep")

# 状態ファイルが古くなったときの遷移 (秒, 次の状態)
AGE_RULES = {
    "done": (6, "idle"),  # 完了ジャンプはすぐ待機に戻す
    "walk": (30, "idle"),  # フックを取りこぼしたとき用の保険
    "work": (600, "idle"),
    "idle": (300, "sleep"),  # 5 分ほうっておくと寝る
}

LABEL = {
    "idle": "待機",
    "walk": "受付",
    "work": "作業中",
    "done": "完了",
    "sleep": "スリープ",
}


def state_file() -> Path:
    if env := os.environ.get("FRENCHIE_STATE_FILE"):
        return Path(env)
    root = os.environ.get("CLAUDE_PROJECT_DIR")
    if root:
        return Path(root) / ".claude/frenchie.state"
    return Path.home() / ".claude/frenchie.state"


def current_state() -> str:
    """状態ファイルの中身と更新時刻から、いまの状態を決める."""
    path = state_file()
    try:
        name = path.read_text(encoding="utf-8").strip()
        age = time.time() - path.stat().st_mtime
    except OSError:
        return "idle"
    if name not in STATES:
        return "idle"
    # 古くなっていたら順に落としていく (done -> idle -> sleep)
    while name in AGE_RULES:
        limit, nxt = AGE_RULES[name]
        if age < limit:
            break
        name = nxt
    return name


def info_line(data: dict) -> str:
    """モデル名とコンテキスト使用率の 1 行. 情報が無ければ空文字."""
    bits = []
    if model := data.get("model", {}).get("display_name"):
        bits.append(model)
    ctx = data.get("context_window", {}).get("used_percentage")
    if ctx is not None:
        bits.append(f"ctx {ctx:.0f}%")
    if cost := data.get("cost", {}).get("total_cost_usd"):
        bits.append(f"${cost:.2f}")
    return "\x1b[2m" + "  ".join(bits) + "\x1b[0m" if bits else ""


def render(state: str, size: str, frame: int | None = None) -> str:
    payload = json.loads(ANSI_JSON.read_text(encoding="utf-8"))
    frames = payload["frames"][size][state]
    if frame is None:
        # 壁時計でコマを進める。ステータスラインは基本イベント駆動なので、
        # settings.json の refreshInterval を入れておくとゆっくり動く。
        frame = int(time.time() * payload["fps"][state]) % len(frames)
    return frames[frame % len(frames)]


def main() -> None:
    ap = argparse.ArgumentParser(description="ステータスライン用のフレンチブルドッグ")
    ap.add_argument("--size", choices=("compact", "full"), default="compact",
                    help="compact = 9 行 (顔まわり) / full = 16 行 (全身)")
    ap.add_argument("--state", choices=STATES, help="状態を直接指定 (確認用)")
    ap.add_argument("--frame", type=int, help="コマを直接指定 (確認用)")
    ap.add_argument("--no-info", action="store_true", help="モデル名などの行を出さない")
    ap.add_argument("--demo", action="store_true", help="5 状態を並べて表示する")
    args = ap.parse_args()

    if args.demo:
        for state in STATES:
            print(f"\x1b[1m{state}\x1b[0m ({LABEL[state]})")
            print(render(state, args.size, args.frame or 0))
            print()
        return

    data = {}
    if not sys.stdin.isatty():  # Claude Code から呼ばれたときだけ JSON が来る
        try:
            data = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            data = {}

    state = args.state or current_state()
    print(render(state, args.size, args.frame))
    if not args.no_info:
        line = info_line(data)
        print(f"\x1b[2m{LABEL[state]}\x1b[0m" + (f"  {line}" if line else ""))


if __name__ == "__main__":
    main()
