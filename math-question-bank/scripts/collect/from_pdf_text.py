"""Convert a question-workbook PDF into a numbered-Markdown question collection.

Output shape required by manage-personal-knowledge `question-import`:
  # <doc title>
  ## <section>
  ### <pure dotted number>
  <question text lines>
  <!-- source-page: <1-based pdf page> -->

The extraction keeps the raw pdftotext text: formulas may be garbled, so each
entry always carries its original code, year, paper and PDF page for lookup.
"""

from __future__ import annotations

import argparse
import hashlib
import html
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


QUESTION_START = re.compile(r"^\(\s*([0-9a-zA-Z.]{3,})\s*\)\s*(.*)$")
SECTION_NUM = re.compile(r"^(\d+(?:\.\d+){2,4})\s*[.．]?\s*([^\d\s].{0,40})$")
SECTION_LETTER = re.compile(r"^([a-z](?:\.[a-z]){2,})\)\s*([^\d].{0,40})$")
MAKI_LECTURE = re.compile(r"^第[一二三四五六七八九十百]+讲\s*([^\s].{0,40})$")
MAKI_SECTION = re.compile(r"^(\d+\.\d+)\s+([^\d].{0,40})$")
MAKI_QUESTION = re.compile(r"^题\s*(\d+(?:\.\d+)+)\s*(.*)$")
MAKI_RUNNING_HEAD = re.compile(r"^(第[一二三四五六七八九十百]+讲|Maki\s*的完美算术教室)")
YEAR = re.compile(r"(?:19|20)\d{2}")
LEADER = re.compile(r"[.．·…\ue000-\uf8ff]{4,}")
HEADER = re.compile(r"^大观严选题|^澄潇宇")
TRAILING_PAGE = re.compile(r"[\s.．]{4,}\d{1,3}\s*$")
PRIVATE_USE = re.compile(r"[\ue000-\uf8ff]")


def extract_pages(pdf: Path) -> list[str]:
    result = subprocess.run(
        [str(_find_pdftotext()), "-layout", "-enc", "UTF-8", str(pdf), "-"],
        capture_output=True,
        check=True,
    )
    text = result.stdout.decode("utf-8", "replace").replace("\r\n", "\n")
    return text.split("\f")


def clean_lines(page_text: str) -> list[str]:
    lines: list[str] = []
    for raw in page_text.split("\n"):
        line = PRIVATE_USE.sub(" ", LEADER.sub(" ", raw).replace("\u200b", " ")).rstrip()
        stripped = line.strip()
        if not stripped or HEADER.match(stripped):
            continue
        if set(stripped) <= set(".．·-—_ "):
            continue
        lines.append(stripped)
    return lines


def page_is_toc(page_text: str) -> bool:
    """Table-of-contents pages carry many leader lines with a trailing page number."""

    raw = [line for line in page_text.split("\n") if line.strip()]
    if not raw:
        return True
    indexed = sum(1 for line in raw if LEADER.search(line) or TRAILING_PAGE.search(line))
    return indexed / len(raw) > 0.25


def convert(
    pdf: Path, title: str, dialect: str = "workbook", body_limit: int | None = None
) -> tuple[str, dict]:
    limit = body_limit or (80 if dialect == "maki" else 60)
    pages = extract_pages(pdf)
    sections: list[dict] = []
    current_section = "未分类"
    questions: list[dict] = []
    current: dict | None = None

    skipped_toc = 0
    for page_number, page_text in enumerate(pages, start=1):
        if page_is_toc(page_text):
            skipped_toc += 1
            continue
        for line in clean_lines(page_text):
            if dialect == "maki":
                if MAKI_RUNNING_HEAD.match(line):
                    continue
                lecture = MAKI_LECTURE.match(line)
                if lecture:
                    questions.append(current) if current is not None else None
                    current = None
                    current_section = line.strip()
                    sections.append({"name": current_section, "page": page_number})
                    continue
                numeric = MAKI_SECTION.match(line)
                if numeric:
                    questions.append(current) if current is not None else None
                    current = None
                    current_section = line.strip()
                    sections.append({"name": current_section, "page": page_number})
                    continue
                marker = MAKI_QUESTION.match(line)
                if marker:
                    if current is not None:
                        questions.append(current)
                    tail = marker.group(2).strip()
                    year_match = YEAR.search(tail)
                    current = {
                        "code": marker.group(1),
                        "tail": tail,
                        "year": year_match.group(0) if year_match else "",
                        "section": current_section,
                        "page": page_number,
                        "body": [],
                    }
                    continue
                if current is not None:
                    current["body"].append(line)
                continue

            section = SECTION_NUM.match(line) or SECTION_LETTER.match(line)
            if section:
                if current is not None:
                    questions.append(current)
                    current = None
                tail = (section.group(2) or "").strip()
                name = f"{section.group(1)} {tail}".strip() if section.re is SECTION_NUM else (tail or section.group(1))
                current_section = name
                sections.append({"name": current_section, "page": page_number})
                continue

            start = QUESTION_START.match(line)
            if start:
                if current is not None:
                    questions.append(current)
                tail = start.group(2).strip()
                year_match = YEAR.search(tail)
                current = {
                    "code": start.group(1),
                    "tail": tail,
                    "year": year_match.group(0) if year_match else "",
                    "section": current_section,
                    "page": page_number,
                    "body": [],
                }
                continue

            if current is None:
                continue

            current["body"].append(line)

    if current is not None:
        questions.append(current)

    out: list[str] = [f"# {title}", ""]
    last_section = None
    for index, item in enumerate(questions, start=1):
        if item["section"] != last_section:
            out += [f"## {item['section']}", ""]
            last_section = item["section"]
        meta = " ｜ ".join(
            part
            for part in (
                f"原编号 {item['code']}",
                f"年份 {item['year']}" if item["year"] else "",
                item["tail"] or "",
            )
            if part
        )
        out += [f"### {index}", f"> {meta}", f"<!-- source-page: {item['page']} -->", ""]
        body = item["body"]
        trimmed = body[:limit]
        if trimmed:
            out += trimmed
            out += [""]
        if len(body) > len(trimmed):
            out += ["（其余文本见 PDF 对应页）", ""]

    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    manifest = {
        "schema": "mpk-source-manifest/v1",
        "title": title,
        "source_format": "numbered-markdown/v1",
        "generator": "pdf_to_question_md.py",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_pdf": {
            "absolute_path": str(pdf),
            "sha256": digest,
            "bytes": pdf.stat().st_size,
            "pages": len(pages),
        },
        "extraction": {
            "tool": "pdftotext -layout -enc UTF-8",
            "fidelity": "raw text layer; mathematical formulas may be garbled and must be re-read on the cited PDF page",
        },
        "counts": {
            "sections": len({item["section"] for item in questions}),
            "questions": len(questions),
            "skipped_toc_pages": skipped_toc,
        },
    }
    return "\n".join(out).rstrip() + "\n", manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--file-name", default="题库.md")
    parser.add_argument("--dialect", choices=("workbook", "maki"), default="workbook")
    parser.add_argument("--body-lines", type=int, default=0)
    args = parser.parse_args()

    pdf = Path(args.pdf)
    out_dir = Path(args.out_dir)
    if not pdf.is_file():
        print(f"pdf not found: {pdf}", file=sys.stderr)
        return 2
    markdown, manifest = convert(pdf, args.title, args.dialect, args.body_lines or None)
    out_dir.mkdir(parents=True, exist_ok=True)
    note = out_dir / args.file_name
    note.write_text(markdown, encoding="utf-8")
    (out_dir / "source-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "note": str(note),
                "questions": manifest["counts"]["questions"],
                "sections": manifest["counts"]["sections"],
                "characters": len(markdown),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
