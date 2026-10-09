#!/usr/bin/env python3
"""from_web.py —— 把 web search 收集到的公开题目规范化为 numbered-markdown/v1 集合。

分工：**检索由 Coding Agent 的 web search 工具完成**，本脚本只负责把结果规范化、
校验、补溯源，产出可以被下游打标签/检索/导入的集合。

输入 items.json（数组，或每行一个对象的 .ndjson）：
  [
    {
      "section": "极限与连续",          # 可选，缺省用 --default-section
      "statement": "求 $\\lim_{x\\to0}...(题干 markdown)",
      "answer": "可选，解答或答案要点",   # 不作必填；没有就不写
      "source": "2023 年 XX 竞赛初赛",   # 来源名（必填）
      "url": "https://example.org/p/1", # 出处链接（强烈建议）
      "license": "CC BY 4.0",           # 许可（拿不准就写 unknown）
      "tags": {"知识块": "极限与连续", "类型": "计算", "难度": "竞赛"}  # 可选
    },
    ...
  ]

许可策略：`license` 缺失或为 unknown/unclear 时，脚本**照常收录但打警告**，并且
只在条目里写来源名与 URL（不复制原书排版），提示使用者自行判断可否再分发。

用法：
  python from_web.py --items items.json --out-dir 题库/公开题源 --title "公开题源"
  python from_web.py --items items.ndjson --out-dir 题库/公开题源 --title "公开题源" --strict
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

OK_LICENSES = ("cc0", "cc by", "cc-by", "public domain", "publicdomain",
               "mit", "apache", "bsd", "gfdl", "open government")


def load_items(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8-sig")
    stripped = text.lstrip()
    if stripped.startswith("["):
        return json.loads(text)
    items = []
    for line in text.splitlines():
        line = line.strip().rstrip(",")
        if line:
            items.append(json.loads(line))
    return items


def license_ok(value: str) -> bool:
    v = (value or "").strip().lower()
    return any(k in v for k in OK_LICENSES)


def build(items: list[dict], title: str, default_section: str, strict: bool):
    warnings: list[str] = []
    sections: dict[str, list[dict]] = {}
    for idx, item in enumerate(items, 1):
        statement = (item.get("statement") or "").strip()
        if not statement:
            sys.exit(f"第 {idx} 条没有 statement，无法收录")
        source = (item.get("source") or "").strip()
        url = (item.get("url") or "").strip()
        if not source:
            sys.exit(f"第 {idx} 条缺少 source（来源名），没有出处就不收录")
        lic = (item.get("license") or "unknown").strip()
        if not url:
            warnings.append(f"第 {idx} 条没有 url，只有来源名「{source}」")
        if not license_ok(lic):
            msg = f"第 {idx} 条许可未确认（license={lic}，来源「{source}」）"
            warnings.append(msg)
            if strict:
                sys.exit("--strict 模式下拒绝收录：" + msg)
        sections.setdefault((item.get("section") or default_section).strip(), []).append(
            {**item, "statement": statement, "source": source, "url": url, "license": lic})
    return sections, warnings


def render(title: str, sections: dict[str, list[dict]]) -> str:
    lines = [f"# {title}",
             "",
             "> 由 `scripts/collect/from_web.py` 规范化；题目来自公开题源，逐条溯源见 `source` 标记。",
             ""]
    number = 0
    for section, items in sections.items():
        lines.append(f"## {section}")
        lines.append("")
        for item in items:
            number += 1
            lines.append(f"### {number}")
            tags = item.get("tags") or {}
            tag_line = " ｜ ".join(f"{k}={v}" for k, v in tags.items())
            meta = f"> 来源={item['source']}"
            if item.get("url"):
                meta += f" ｜ URL={item['url']}"
            meta += f" ｜ 许可={item['license']}"
            if item.get("year"):
                meta += f" ｜ 年份={item['year']}"
            lines.append(meta)
            if tag_line:
                lines.append(f"> 标签：{tag_line}")
            marker = f"<!-- source: {item['url']} -->" if item.get("url") \
                else f"<!-- source: {item['source']} -->"
            lines.append(marker)
            lines.append("")
            lines.append(item["statement"].rstrip())
            if item.get("answer"):
                lines.append("")
                lines.append("**解答**")
                lines.append("")
                lines.append(str(item["answer"]).rstrip())
            lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="公开题源 → numbered-markdown 集合")
    ap.add_argument("--items", required=True, help="items.json 或 .ndjson")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--default-section", default="未分组")
    ap.add_argument("--strict", action="store_true", help="许可未确认就拒绝收录")
    args = ap.parse_args()

    items = load_items(Path(args.items))
    sections, warnings = build(items, args.title, args.default_section, args.strict)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    body = render(args.title, sections)
    md = out_dir / f"{args.title}.md"
    md.write_text(body, encoding="utf-8", newline="\n")

    total = sum(len(v) for v in sections.values())
    manifest = {
        "schema": "mpk-source-manifest/v1",
        "title": args.title,
        "source_format": "numbered-markdown/v1",
        "generator": "from_web.py",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "extraction": {"tool": "Coding Agent web search", "fidelity": "题面由检索结果整理，未做二次改写"},
        "counts": {"sources": len({i["source"] for v in sections.values() for i in v}),
                   "entries": total},
        "sources_detail": [
            {"label": i["source"], "path": i.get("url") or "(no url)",
             "license": i["license"]}
            for v in sections.values() for i in v
        ],
    }
    (out_dir / "source-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"写出 {md}（{total} 题，{len(sections)} 个分组）")
    print(f"md5(内容)={hashlib.md5(body.encode('utf-8')).hexdigest()}")
    if warnings:
        print(f"\n{len(warnings)} 条警告（许可/出处需要你确认）：")
        for w in warnings:
            print("  - " + w)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
