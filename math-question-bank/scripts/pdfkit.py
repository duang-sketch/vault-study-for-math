#!/usr/bin/env python3
"""pdfkit —— 通用文档解析 CLI（可被任何 skill / agent 复用）。

只做一件事：把 MinerU 之类工具产出的"带页标记的 markdown"当成可寻址的文档来用。
MinerU 会在每页开头写 `<!-- page N of M -->`，本工具据此提供：

    pdfkit.py markers  raw.md                  # 列出页标记（第几页开始）
    pdfkit.py pages    raw.md --pages 18,19    # 打印指定 PDF 页的原文
    pdfkit.py slice    raw.md --pages 18-24 --out part.md
    pdfkit.py offset   raw.md                  # 统计 印刷页 = PDF 页 - ? 的偏移分布

约定：
  * 页码一律是 **1-based PDF 页**（扫描页），不是书里的印刷页
  * 偏移必须实测：offset 子命令从每页页脚数字里投票，输出候选偏移及支持页数
  * 没有页标记的文件不猜页码，直接报错

输出：默认人读文本；加 --json 输出机器可读结果（便于被其他 agent 当 tool 调用）。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

MARK = re.compile(r"<!--\s*page\s+(\d+)\s+of\s+(\d+)\s*-->")
FOOTER = re.compile(r"^\s*(\d{1,4})\s*$")


def load_pages(paths: list[Path]) -> dict[int, str]:
    """把多个 raw 文件按页标记拼成 {pdf_page: text}。"""
    pages: dict[int, str] = {}
    for path in paths:
        raw = path.read_text(encoding="utf-8", errors="replace")
        parts = MARK.split(raw)
        if len(parts) < 4:
            sys.exit(f"{path.name}: 找不到 `<!-- page N of M -->` 页标记，"
                     f"该文件不是逐页输出，无法寻址")
        for i in range(1, len(parts) - 2, 3):
            try:
                num = int(parts[i])
            except ValueError:
                continue
            pages[num] = parts[i + 2]
    return pages


def parse_range(spec: str) -> list[int]:
    out: list[int] = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            a, b = chunk.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(chunk))
    return out


def cmd_markers(args) -> int:
    pages = load_pages([Path(p) for p in args.files])
    keys = sorted(pages)
    if args.json:
        print(json.dumps({"pages": keys, "count": len(keys),
                          "first": keys[0] if keys else None,
                          "last": keys[-1] if keys else None}, ensure_ascii=False))
        return 0
    print(f"{len(keys)} 页：{keys[0]}–{keys[-1]}" if keys else "没有页标记")
    return 0


def cmd_pages(args) -> int:
    pages = load_pages([Path(p) for p in args.files])
    wanted = parse_range(args.pages)
    if args.json:
        print(json.dumps(
            [{"page": n, "text": pages.get(n, "")} for n in wanted],
            ensure_ascii=False))
        return 0
    for n in wanted:
        print("=" * 24 + f" PDF page {n} " + "=" * 24)
        print(pages.get(n, "<MISSING>").strip("\n"))
    return 0


def cmd_slice(args) -> int:
    pages = load_pages([Path(p) for p in args.files])
    wanted = parse_range(args.pages)
    missing = [n for n in wanted if n not in pages]
    if missing:
        sys.exit(f"这些页不存在：{missing}")
    chunks = []
    for n in wanted:
        chunks.append(f"<!-- page {n} -->\n{pages[n].strip(chr(10))}")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n\n".join(chunks) + "\n", encoding="utf-8", newline="\n")
    print(f"已写出 {out}（{len(wanted)} 页，{out.stat().st_size} 字节）")
    return 0


def cmd_offset(args) -> int:
    """从每页页脚数字投票，推断 印刷页 = PDF 页 − offset。"""
    pages = load_pages([Path(p) for p in args.files])
    votes: Counter = Counter()
    detail = []
    for num in sorted(pages):
        candidates = [int(m.group(1)) for m in
                      (FOOTER.match(line) for line in pages[num].splitlines()[-6:]) if m]
        for printed in candidates:
            delta = num - printed
            if 0 <= delta <= 60:
                votes[delta] += 1
                detail.append({"pdf_page": num, "printed_page": printed, "offset": delta})
                break
    best = votes.most_common(1)
    result = {
        "pages_with_footer": len(detail),
        "best_offset": best[0][0] if best else None,
        "best_support": best[0][1] if best else 0,
        "distribution": dict(votes.most_common(6)),
    }
    if args.json:
        print(json.dumps({**result, "detail": detail[:50]}, ensure_ascii=False))
        return 0
    if not best:
        print("没找到可用的页脚数字，无法推断偏移")
        return 1
    print(f"候选偏移（印刷页 = PDF 页 − offset）：")
    for delta, n in votes.most_common(6):
        print(f"   -{delta:<4} 支持 {n} 页")
    print(f"\n最佳：offset={best[0]}（{best[1]}/{len(detail)} 页支持）"
          f"{'  ⚠ 支持率不足，建议抽查' if best[1] < max(3, len(detail) * 0.6) else ''}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="pdfkit", description="带页标记 markdown 的通用解析 CLI")
    ap.add_argument("--json", action="store_true", help="输出 JSON（供其他 agent 当 tool 调用）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("markers", help="列出页标记")
    p.add_argument("files", nargs="+")
    p.set_defaults(func=cmd_markers)

    p = sub.add_parser("pages", help="打印指定页的原文")
    p.add_argument("files", nargs="+")
    p.add_argument("--pages", required=True, help="如 18,19 或 18-24")
    p.set_defaults(func=cmd_pages)

    p = sub.add_parser("slice", help="按页范围切片成新文件")
    p.add_argument("files", nargs="+")
    p.add_argument("--pages", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_slice)

    p = sub.add_parser("offset", help="推断印刷页与 PDF 页的偏移")
    p.add_argument("files", nargs="+")
    p.set_defaults(func=cmd_offset)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
