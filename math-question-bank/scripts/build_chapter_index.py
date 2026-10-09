"""Generate the chapter→source mapping note (教材 / 竞赛教程 / 题库 / 分册)."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

CHAPTERS_UP = [
    "第一章函数与极限", "第二章导数与微分", "第三章微分中值定理与导数的应用",
    "第四章不定积分", "第五章定积分", "第六章定积分的应用", "第七章微分方程",
]
CHAPTERS_DOWN = [
    "第八章向量代数与空间解析几何", "第九章多元函数微分法及其应用", "第十章重积分",
    "第十一章曲线积分与曲面积分", "第十二章无穷级数",
]
COMP_UP = {
    "第1章 极限、函数与连续": "p10 起（要点 p10–11｜范例 p11–43｜真题 p44–60｜训练 p61–66｜全解 p67–89）",
    "第2章 一元函数微分学": "p90 起（要点 p90–91｜范例 p91–133｜真题 p134–150｜训练 p151–156｜全解 p157–178）",
    "第3章 一元函数积分学": "p179 起（要点 p179–182｜范例 p182–225｜真题 p226–249｜训练/全解 p250–266）",
    "第4章 常微分方程": "p267 起（要点 p267–269｜范例 p269–295｜真题 p296–309｜训练 p310–313｜全解 p314–323）",
}
PAGE_MARK = re.compile(r"^## 第 (\d+) 页")
TITLE = re.compile(r"第[一二三四五六七八九十]+章[^\s，。]*")
QUESTION = re.compile(r"^### (\S+)")
SECTION = re.compile(r"^## (.+)$")


def book_chapter_pages(md: Path, titles: list[str], start_page: int) -> dict[str, int]:
    pages: dict[str, int] = {}
    current = 0
    for line in md.read_text(encoding="utf-8").split("\n"):
        mark = PAGE_MARK.match(line.strip())
        if mark:
            current = int(mark.group(1))
            continue
        if current < start_page:
            continue
        for title in titles:
            if title in pages:
                continue
            if title[:4] in line and line.strip().startswith(title[:4]):
                pages[title] = current
    return pages


def competition_down(md: Path) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    current = 0
    pattern = re.compile(r"^\s*(第[5-9]\s*章|5\.3|5\.4|6\.3|6\.4|7\.3|7\.4|8\.3|8\.4)")
    for line in md.read_text(encoding="utf-8").split("\n"):
        mark = PAGE_MARK.match(line.strip())
        if mark:
            current = int(mark.group(1))
            continue
        m = pattern.match(line.strip())
        if m and current:
            text = line.strip()
            hits.append((current, text[:24]))
    deduped: list[tuple[int, str]] = []
    seen: set[str] = set()
    for page, text in hits:
        key = re.sub(r"[^\w.]", "", text)[:6]
        if key in seen:
            continue
        seen.add(key)
        deduped.append((page, text))
    return deduped[:24]


def collection_ranges(root: Path) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    for note in sorted(root.glob("*/*.md")):
        section = ""
        first = last = ""
        per_section: dict[str, list[str]] = {}
        for line in note.read_text(encoding="utf-8").split("\n"):
            s = SECTION.match(line)
            if s and not line.startswith("### "):
                section = s.group(1).strip()
                continue
            q = QUESTION.match(line)
            if q and section:
                per_section.setdefault(section, []).append(q.group(1))
        for name, ids in list(per_section.items())[:200]:
            rows.append((note.parent.name, name, ids[0], ids[-1]))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--library", required=True, help="资料库目录（含教材 md 与竞赛教程 md）")
    parser.add_argument("--questions", required=True, help="题库根目录")
    parser.add_argument("--fence", required=True, help="分册题库集合目录")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    library = Path(args.library)
    questions_root = Path(args.questions)

    up_md = next(library.glob("高等数学 上册 第八版*.md"))
    down_md = next(library.glob("高等数学 下册 第八版*.md"))
    comp_down_md = next(library.glob("全国大学生数学竞赛解析教程(非数学专业类)(下册)*.md"))

    up_pages = book_chapter_pages(up_md, CHAPTERS_UP, start_page=16)
    down_pages = book_chapter_pages(down_md, CHAPTERS_DOWN, start_page=8)
    comp_down = competition_down(comp_down_md)
    ranges = collection_ranges(questions_root)
    fence_files = sorted(Path(args.fence).glob("*.md"))

    lines = [
        "# 章节题源总表（教材 / 竞赛教程 / 题库 / 分册）",
        "",
        f"来源：`{library}`、题库 `{questions_root}`、分册集合 `{args.fence}`",
        "",
        "说明：页码为该文件自身的 PDF 页码；题库题号是集合内的顺序编号（条目内含原编号与源页码）。",
        "",
        "## 一、教材章节起始页（同济第八版）",
        "",
        "| 章 | 上册页码 |",
        "| --- | --- |",
    ]
    for title in CHAPTERS_UP:
        lines.append(f"| {title} | {up_pages.get(title, '—')} |")
    lines += ["", "| 章 | 下册页码 |", "| --- | --- |"]
    for title in CHAPTERS_DOWN:
        lines.append(f"| {title} | {down_pages.get(title, '—')} |")

    lines += ["", "## 二、竞赛教程页码（非数学专业类·第2版）", "", "### 上册（323 页）", ""]
    for name, page in COMP_UP.items():
        lines.append(f"- {name}：{page}")
    lines += ["", "### 下册（387 页，实测页码）", ""]
    for page, text in comp_down:
        lines.append(f"- p{page}：{text}")

    lines += ["", "## 三、题库章节与题号范围", ""]
    current_collection = None
    for collection, section, first, last in ranges:
        if collection != current_collection:
            lines += ["", f"### {collection}", "", "| 章节 | 题号范围 |", "| --- | --- |"]
            current_collection = collection
        lines.append(f"| {section} | {first}–{last} |")

    lines += ["", "## 四、大观高数分册（专题级）", ""]
    for note in fence_files:
        text = note.read_text(encoding="utf-8")
        topics = len(re.findall(r"^## ", text, re.M))
        entries = len(re.findall(r"^### ", text, re.M))
        lines.append(f"- {note.stem}：{topics} 个专题 / {entries} 条")

    Path(args.out).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"写入 {args.out}（{len(lines)} 行）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
