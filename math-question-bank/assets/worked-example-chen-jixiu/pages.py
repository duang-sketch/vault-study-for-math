# -*- coding: utf-8 -*-
"""Print raw MinerU content for given PDF pages. usage: pages.py 18 19 21"""
import io
import os
import re
import sys

# 原始 MinerU 分片目录：环境变量 CJX_DIR 可覆盖（默认本机路径）
CJX = os.environ.get("CJX_DIR", "_raw")
RAWS = ["up_p1-60.md", "up_p61-120.md", "up_p121-180.md", "up_p181-246.md"]
PAGE_MARK = re.compile(r"<!--\s*page\s+(\d+)\s+of\s+246\s*-->")


def all_pages():
    d = {}
    for name in RAWS:
        p = os.path.join(CJX, name)
        if not os.path.exists(p):
            continue
        raw = io.open(p, encoding="utf-8", errors="replace").read()
        parts = PAGE_MARK.split(raw)
        i = 1
        while i + 1 < len(parts):
            d[int(parts[i])] = parts[i + 1]
            i += 2
    return d


def main():
    d = all_pages()
    for a in sys.argv[1:]:
        n = int(a)
        print("=" * 20 + " PDF page %d (book P.%d) " % (n, n - 6) + "=" * 20)
        print(d.get(n, "<MISSING>").strip("\n"))


if __name__ == "__main__":
    main()
