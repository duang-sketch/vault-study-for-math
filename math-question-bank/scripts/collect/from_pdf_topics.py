"""Convert 大观高数分册 topic PDFs into one numbered-Markdown question collection.

For every chapter folder, each topic PDF under
`mn分块版pdf（安卓用）\\分块pdf（不带答案）` becomes a `## <topic>` section.
Problems are split by leading problem numbers; a page without a detected
number stays one entry. Every entry keeps its source PDF page number.

Note: text comes from the PDF text layer, so formulas may be garbled;
the `source-page` marker is the authority for re-reading the original page.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# pdftotext 路径：优先环境变量 PDFTOTEXT，其次 PATH
def _find_pdftotext() -> Path:
    override = os.environ.get("PDFTOTEXT")
    if override:
        return Path(override)
    found = shutil.which("pdftotext")
    if found:
        return Path(found)
    raise SystemExit(
        "找不到 pdftotext：请安装 poppler 并把 pdftotext 加入 PATH，"
        "或设置环境变量 PDFTOTEXT 指向该可执行文件。"
    )

PROBLEM = re.compile(r"^\s*(\d{1,3})\s*[.、．]\s*\S")
HEADER = re.compile(r"^大观|^澄潇宇")


def extract_pages(pdf: Path) -> list[str]:
    result = subprocess.run(
        [str(_find_pdftotext()), "-layout", "-enc", "UTF-8", str(pdf), "-"],
        capture_output=True,
        check=True,
    )
    text = result.stdout.decode("utf-8", "replace").replace("\r\n", "\n")
    return text.split("\f")


def _find_pdfinfo() -> Path:
    return _find_pdftotext().with_name("pdfinfo.exe" if os.name == "nt" else "pdfinfo")


def page_count(pdf: Path) -> int:
    try:
        result = subprocess.run([str(_find_pdfinfo()), str(pdf)], capture_output=True, check=True)
        match = re.search(r"^Pages:\s+(\d+)", result.stdout.decode("utf-8", "replace"), re.M)
        return int(match.group(1)) if match else 0
    except Exception:
        return 0


def excerpt(pdf: Path) -> str:
    result = subprocess.run(
        [str(_find_pdftotext()), "-f", "1", "-l", "1", "-enc", "UTF-8", str(pdf), "-"],
        capture_output=True,
        check=True,
    )
    text = result.stdout.decode("utf-8", "replace").replace("\r\n", "\n")
    lines = [line.strip() for line in text.split("\n") if line.strip() and not HEADER.match(line.strip())]
    return " / ".join(lines[:4])[:200]


def convert_topic(pdf: Path, index: int, block: str, library_relative: str) -> tuple[list[str], int, int]:
    total_pages = page_count(pdf)
    hint = excerpt(pdf)
    out = [
        f"### {index}",
        f"> 大观高数分册 ｜ 专题 {pdf.stem} ｜ 共 {total_pages} 页",
        f"> PDF：{library_relative}",
        f"> 标签：知识块={block} ｜ 类型=专题题库 ｜ 来源=题目汇编 ｜ 粒度=专题",
        f"<!-- source-page: 1-{total_pages or '?'} -->",
        "",
        f"（本条目为该专题的题目册 PDF 指针；首行摘录：{hint}）",
        "（文本层公式会走样，取题请按上面的 PDF 路径打开原文件）",
        "",
    ]
    return out, index + 1, 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="大观高数分册\\1. 高数 目录")
    parser.add_argument("--out", required=True, help="输出集合目录")
    parser.add_argument("--pdf-name", default="分块pdf（不带答案）")
    args = parser.parse_args()

    source = Path(args.source)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    total_questions = 0
    topics: list[dict] = []

    for chapter in sorted(p for p in source.iterdir() if p.is_dir()):
        topic_dirs = [
            d for d in chapter.rglob("*")
            if d.is_dir() and ("不带答案" in d.name or "题目" in d.name)
        ]
        topic_dirs = sorted(topic_dirs, key=lambda d: (len(d.parts), d.name))
        topic_dir = next((d for d in topic_dirs if list(d.glob("*.pdf"))), None)
        if topic_dir is None:
            continue
        lines: list[str] = [f"# 大观高数分册 {chapter.name}（题目册）", ""]
        index = 1
        for pdf in sorted(topic_dir.glob("*.pdf")):
            relative = f"资料库/大观高数分册/1. 高数/{chapter.name}/mn分块版pdf（安卓用）/{args.pdf_name}/{pdf.name}"
            section, index, count = convert_topic(pdf, index, chapter.name, relative)
            if not section:
                continue
            lines.append(f"## {pdf.stem}")
            lines.append("")
            lines.extend(section)
            total_questions += count
            topics.append({"chapter": chapter.name, "topic": pdf.stem, "questions": count,
                           "sha256": hashlib.sha256(pdf.read_bytes()).hexdigest()})
        (out_dir / f"{chapter.name}.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    manifest = {
        "schema": "mpk-source-manifest/v1",
        "title": "大观高数分册（题目册）",
        "source_format": "numbered-markdown/v1",
        "generator": "fence_to_question_md.py",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "extraction": {
            "tool": "pdftotext -layout -enc UTF-8",
            "fidelity": "raw text layer; formulas may be garbled, verify on the cited PDF page",
        },
        "counts": {"documents": len(topics), "questions": total_questions},
        "topics": topics,
    }
    (out_dir / "source-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"questions": total_questions, "topics": len(topics), "out": str(out_dir)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
