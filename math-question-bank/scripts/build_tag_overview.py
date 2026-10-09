"""Summarise the 知识块 / 类型 / 难度 tags of every question collection.

Writes 题库标签总览.md next to the collections (and is copied into the Vault by
build_package.ps1). Run after tag_questions.py so the numbers reflect the files.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter, OrderedDict
from pathlib import Path

ENTRY = re.compile(r"^### (\S+)\s*$")
TAG = re.compile(r"^>\s*标签：\s*(.*)$")


def collect(path: Path) -> dict:
    blocks, types, levels = Counter(), Counter(), Counter()
    total = 0
    for line in path.read_text(encoding="utf-8").split("\n"):
        if ENTRY.match(line):
            total += 1
            continue
        m = TAG.match(line)
        if not m:
            continue
        fields = {}
        for part in m.group(1).split("｜"):
            if "=" in part:
                k, v = part.split("=", 1)
                fields[k.strip()] = v.strip()
        blocks[fields.get("知识块", "未标注")] += 1
        types[fields.get("类型", "未标注")] += 1
        levels[fields.get("难度", "—")] += 1
    return {"total": total, "blocks": blocks, "types": types, "levels": levels}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, help="题库根目录")
    parser.add_argument("--out", required=True, help="输出的 md 文件")
    args = parser.parse_args()
    root = Path(args.root)

    rows: "OrderedDict[str, dict]" = OrderedDict()
    for note in sorted(root.rglob("*.md")):
        if note.name.startswith("_"):
            continue
        data = collect(note)
        if not data["total"]:
            continue
        key = str(note.relative_to(root).parent).replace("\\", "/")
        if key not in rows:
            rows[key] = {"total": 0, "blocks": Counter(), "types": Counter(),
                         "levels": Counter()}
        row = rows[key]
        row["total"] += data["total"]
        row["blocks"].update(data["blocks"])
        row["types"].update(data["types"])
        row["levels"].update(data["levels"])

    total = sum(d["total"] for d in rows.values())
    grand_blocks: Counter = Counter()
    grand_types: Counter = Counter()
    grand_levels: Counter = Counter()
    for d in rows.values():
        grand_blocks.update(d["blocks"])
        grand_types.update(d["types"])
        grand_levels.update(d["levels"])

    lines = [
        "# 题库标签总览",
        "",
        f"题目总数：**{total}**（{len(rows)} 个集合）",
        "",
        "标签由 `工具/tag_questions.py`（v2）生成：知识块按章节 / 原编号判定，"
        "类型按选项与「证明」字样判定，难度是来源级别（不是逐题实测）。",
        "",
        "## 一、各集合题量",
        "",
        "| 集合 | 题量 |",
        "| --- | ---: |",
    ]
    for name, d in sorted(rows.items(), key=lambda kv: -kv[1]["total"]):
        lines.append(f"| {name} | {d['total']} |")

    lines += ["", "## 二、知识块分布（全库）", "", "| 知识块 | 题量 |", "| --- | ---: |"]
    for block, count in grand_blocks.most_common():
        lines.append(f"| {block} | {count} |")

    lines += ["", "## 三、各集合的知识块分布", ""]
    for name, d in rows.items():
        detail = "、".join(f"{k} {v}" for k, v in d["blocks"].most_common())
        lines.append(f"- **{name}**：{detail}")

    lines += ["", "## 四、题型分布（全库）", "", "| 类型 | 题量 |", "| --- | ---: |"]
    for kind, count in grand_types.most_common():
        lines.append(f"| {kind} | {count} |")

    lines += ["", "## 五、难度标记分布（全库）", "", "| 难度 | 题量 |", "| --- | ---: |"]
    for level, count in grand_levels.most_common():
        lines.append(f"| {level} | {count} |")

    lines += [
        "",
        "## 六、取题提醒",
        "",
        "- 大观严选题、Maki 是逐题条目（一题一条），题面来自 PDF 文本层，公式会走样："
        "按条目里的 `<!-- source-page -->` 回看原页，或对该页跑 MinerU 取干净 LaTeX。",
        "- 大观高数分册是**专题级指针**，竞赛教程题源是**页级条目**，两者都不是逐题。",
        "",
    ]
    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:20]))
    print(f"...\n写入 {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
