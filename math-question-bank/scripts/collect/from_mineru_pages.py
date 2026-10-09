"""Build one numbered-Markdown question collection from MinerU page-range outputs.

Each MinerU output keeps absolute page markers (`<!-- page N of M -->`), so the
collection preserves the competition textbook's real page numbers. Pages are
grouped by the section headings MinerU detected; every page becomes one entry
(a page usually holds several problems, and the raw text layer of this book is
an ABBYY OCR layer whose formulas must be re-read on the cited page).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

PAGE = re.compile(r"^<!-- page (\d+) of (\d+) -->")
HEADING = re.compile(r"^#{1,3}\s+(.+)$")


def collect(path: Path, label: str) -> list[dict]:
    pages: list[dict] = []
    section = label
    current: dict | None = None
    for raw in path.read_text(encoding="utf-8").split("\n"):
        marker = PAGE.match(raw.strip())
        if marker:
            if current:
                pages.append(current)
            current = {"page": int(marker.group(1)), "section": section, "body": []}
            continue
        heading = HEADING.match(raw.strip())
        if heading:
            text = heading.group(1).strip()
            if len(text) <= 40 and not text.startswith("Maki"):
                section = text
                if current is not None and not current["body"]:
                    current["section"] = section
            continue
        if current is not None:
            current["body"].append(raw.rstrip())
    if current:
        pages.append(current)
    for item in pages:
        while item["body"] and not item["body"][0].strip():
            item["body"].pop(0)
        while item["body"] and not item["body"][-1].strip():
            item["body"].pop()
    return [page for page in pages if page["body"]]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--file-name", default="竞赛教程题源.md")
    parser.add_argument("--sources", nargs="+", required=True,
                        help="形如 label=path 的列表")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    lines: list[str] = ["# 全国大学生数学竞赛解析教程（非数学专业类·第2版）题源", ""]
    index = 1
    records: list[dict] = []
    for item in args.sources:
        label, _, raw_path = item.partition("=")
        path = Path(raw_path)
        if not path.is_file():
            continue
        pages = collect(path, label)
        records.append({"label": label, "path": str(path), "pages": len(pages),
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        last_section = None
        for page in pages:
            if page["section"] != last_section:
                lines += [f"## {page['section']}", ""]
                last_section = page["section"]
            lines.append(f"### {index}")
            lines.append(f"> 竞赛教程 ｜ {page['section']} ｜ 原书页码 {page['page']}")
            lines.append(f"> 标签：知识块={page['section'][:12]} ｜ 类型=页码条目 ｜ 来源=竞赛真题/训练 ｜ 粒度=页")
            lines.append(f"<!-- source-page: {page['page']} -->")
            lines.append("")
            lines.extend(page["body"][:120])
            lines.append("")
            index += 1

    (out_dir / args.file_name).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    manifest = {
        "schema": "mpk-source-manifest/v1",
        "title": "全国大学生数学竞赛解析教程（非数学专业类·第2版）题源",
        "source_format": "numbered-markdown/v1",
        "generator": "competition_book_to_questions.py",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "extraction": {
            "tool": "MinerU 4.0.10 standard tier (local CPU)",
            "fidelity": "LaTeX for formulas; 原书文本层为 ABBYY OCR，公式务必按 source-page 复核",
        },
        "counts": {"sources": len(records), "entries": index - 1},
        "sources_detail": records,
    }
    (out_dir / "source-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"entries": index - 1, "sources": len(records)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
