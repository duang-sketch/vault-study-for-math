#!/usr/bin/env python3
"""export_mongo.py —— 把 numbered-markdown 集合导出为 MongoDB 可直接吃的 NDJSON。

每道题一条文档，字段与索引设计见 references/mongo-schema.md。前端/服务端只要读这个
NDJSON 就能建库，不必再解析 markdown。

用法：
  python export_mongo.py --root 题库 --out 题库.ndjson --indexes 索引建议.json
  python export_mongo.py --root 题库 --out -            # 输出到 stdout

导入示例：
  mongoimport --uri "$MONGO_URI" --collection questions --type json --file 题库.ndjson
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ENTRY = re.compile(r"^### (\S+)\s*$")
SECTION = re.compile(r"^## (?!##)(.+?)\s*$")
TAG = re.compile(r"^>\s*标签：\s*(.*)$")
META = re.compile(r"^>\s*(.*)$")
SOURCE_PAGE = re.compile(r"<!--\s*source-page:\s*([0-9\-]+)\s*-->")
SOURCE_URL = re.compile(r"<!--\s*source:\s*(.+?)\s*-->")

INDEXES = [
    {"keys": {"knowledge_block": 1, "type": 1}, "name": "kb_type"},
    {"keys": {"collection": 1, "number": 1}, "name": "coll_number", "unique": True},
    {"keys": {"source_page": 1}, "name": "src_page"},
    {"keys": {"tags": 1}, "name": "tags_multi"},
    {"keys": {"statement_md": "text", "solution_md": "text"}, "name": "fulltext",
     "note": "文本索引；中文建议同时建 Atlas Search 索引"},
]


def parse_collection(path: Path, collection: str):
    docs, section, number, meta, tags, body, in_entry = [], "", None, "", {}, [], False
    def flush():
        nonlocal number, meta, tags, body, in_entry
        if number is None:
            return
        text = "\n".join(body).strip("\n")
        src_page = SOURCE_PAGE.search(text)
        src_url = SOURCE_URL.search(text)
        solution = ""
        if "\n**解答**\n" in text:
            statement, solution = text.split("\n**解答**\n", 1)
        else:
            statement = text
        docs.append({
            "collection": collection,
            "number": number,
            "section": section or None,
            "knowledge_block": tags.get("知识块"),
            "type": tags.get("类型"),
            "source": tags.get("来源"),
            "difficulty": tags.get("难度"),
            "tags": {k: v for k, v in tags.items()},
            "source_page": src_page.group(1) if src_page else None,
            "source_url": src_url.group(1) if src_url else None,
            "statement_md": statement.strip(),
            "solution_md": solution.strip() or None,
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "meta_raw": meta.strip() or None,
            "imported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
        number, meta, tags, body, in_entry = None, "", {}, [], False

    for line in path.read_text(encoding="utf-8-sig").splitlines():
        m_sec = SECTION.match(line)
        if m_sec:
            flush()
            section = m_sec.group(1).strip()
            continue
        m_entry = ENTRY.match(line)
        if m_entry:
            flush()
            number = m_entry.group(1)
            in_entry = True
            continue
        if not in_entry:
            continue
        m_tag = TAG.match(line)
        if m_tag:
            for part in m_tag.group(1).split("｜"):
                if "=" in part:
                    k, v = part.split("=", 1)
                    tags[k.strip()] = v.strip()
            continue
        m_meta = META.match(line)
        if m_meta and not body:
            meta += " " + m_meta.group(1).strip()
            continue
        body.append(line)
    flush()
    return docs


def main() -> int:
    ap = argparse.ArgumentParser(description="题源集合 → MongoDB NDJSON")
    ap.add_argument("--root", required=True, help="题库根目录（含各集合子目录）")
    ap.add_argument("--out", required=True, help="输出 .ndjson，或 - 表示 stdout")
    ap.add_argument("--indexes", help="把索引建议写到这个 json 文件")
    args = ap.parse_args()

    root = Path(args.root)
    all_docs = []
    for note in sorted(root.rglob("*.md")):
        if note.name.startswith("_"):
            continue
        collection = note.parent.name if note.parent != root else note.stem
        docs = parse_collection(note, collection)
        if docs:
            all_docs.extend(docs)
            print(f"  {collection}: {len(docs)} 条", file=sys.stderr)

    payload = "\n".join(json.dumps(d, ensure_ascii=False) for d in all_docs) + "\n"
    if args.out == "-":
        sys.stdout.write(payload)
    else:
        Path(args.out).write_text(payload, encoding="utf-8", newline="\n")
        print(f"写出 {args.out}（{len(all_docs)} 条文档）")
    if args.indexes:
        Path(args.indexes).write_text(
            json.dumps({"collection": "questions", "indexes": INDEXES},
                       ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"写出索引建议 {args.indexes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
