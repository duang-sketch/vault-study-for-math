#!/usr/bin/env bash
# 一键安装 math-question-bank skill（macOS / Linux）
#
#   bash ./install.sh                    # 装到 $CODEX_HOME/skills（默认 ~/.codex/skills）
#   bash ./install.sh --force            # 已存在时覆盖
#   bash ./install.sh --dest /opt/skills # 指定目标
set -euo pipefail

SKILL_NAME="math-question-bank"
DEST=""
FORCE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --force) FORCE=1; shift ;;
    --dest)  DEST="$2"; shift 2 ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "未知参数：$1" >&2; exit 2 ;;
  esac
done

SRC="$(cd "$(dirname "$0")" && pwd)/$SKILL_NAME"
[ -d "$SRC" ] || { echo "找不到技能目录：$SRC" >&2; exit 1; }

if [ -z "$DEST" ]; then
  DEST="${CODEX_HOME:-$HOME/.codex}/skills"
fi
TARGET="$DEST/$SKILL_NAME"

if [ -e "$TARGET" ]; then
  if [ "$FORCE" -ne 1 ]; then echo "已存在：$TARGET（加 --force 覆盖）" >&2; exit 1; fi
  rm -rf "$TARGET"
fi
mkdir -p "$DEST"
cp -R "$SRC" "$TARGET"
echo "[1/3] 已安装到 $TARGET"

PY="$(command -v python3 || command -v python || true)"
if [ -n "$PY" ]; then echo "[2/3] Python: $PY"; else echo "[2/3] 警告：没找到 python3，脚本需要 Python 3.10+" >&2; fi
command -v pdftotext >/dev/null 2>&1 \
  && echo "      pdftotext: 已就绪" \
  || echo "      pdftotext 不在 PATH：装 poppler，或设 PDFTOTEXT（文本层通道需要）"
[ -n "${MINERU_HOME:-}" ] || command -v mineru >/dev/null 2>&1 \
  && echo "      MinerU: 已配置（净通道可用）" \
  || echo "      MinerU 未配置：净通道需要 MINERU_HOME / MINERU_EXE"

VALIDATOR="$(dirname "$DEST")/skills/.system/skill-creator/scripts/quick_validate.py"
if [ -n "$PY" ] && [ -f "$VALIDATOR" ]; then
  "$PY" -B "$VALIDATOR" "$TARGET" && echo "[3/3] 已通过 quick_validate"
else
  echo "[3/3] 跳过 quick_validate（未安装 skill-creator）"
fi

echo
echo "完成。下一轮对话即可用 \$math-question-bank 调用。"
