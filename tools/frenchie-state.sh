#!/bin/sh
# Claude Code のフックから呼ばれて、犬の状態を書くだけのスクリプト。
#
#   tools/frenchie-state.sh work
#
# 2 か所に書く:
#   $CLAUDE_PROJECT_DIR/.claude/frenchie.state … ステータスライン用 (プロジェクト単位)
#   ~/.claude/frenchie.state                   … デスクトップペット用 (全体で 1 匹)
#
# フックは標準入力に JSON を渡してくるが、ここでは使わないので読み捨てる。
set -eu

state="${1:-idle}"

write_to() {
  mkdir -p "$1" 2>/dev/null || return 0
  printf '%s' "$state" > "$1/frenchie.state" 2>/dev/null || true
}

write_to "${CLAUDE_PROJECT_DIR:-$PWD}/.claude"
write_to "$HOME/.claude"
