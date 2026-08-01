#!/bin/sh
# Claude Code のフックから呼ばれて、犬の状態を 1 ファイルに書くだけのスクリプト。
#
#   tools/frenchie-state.sh work
#
# ステータスライン側 (tools/frenchie_statusline.py) がこのファイルを読んで、
# 中身と更新時刻から表示するコマを決める。フックは標準入力に JSON を渡して
# くるが、ここでは使わないので読み捨てる。
set -eu

dir="${CLAUDE_PROJECT_DIR:-$PWD}/.claude"
mkdir -p "$dir"
printf '%s' "${1:-idle}" > "$dir/frenchie.state"
