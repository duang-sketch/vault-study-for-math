# -*- coding: utf-8 -*-
"""Analyze MinerU raw output: detect chapter/section headings, problem starts,
solution labels, running heads, footers, image blocks."""
import re
import io
import os
import sys
from collections import Counter

# 原始 MinerU 分片目录：环境变量 CJX_DIR 可覆盖（默认本机路径）
CJX = os.environ.get("CJX_DIR", "_raw")
RAWS = [
    (os.path.join(CJX, "up_p1-60.md"), 1, 60),
    (os.path.join(CJX, "up_p61-120.md"), 61, 120),
    (os.path.join(CJX, "up_p121-180.md"), 121, 180),
    (os.path.join(CJX, "up_p181-246.md"), 181, 246),
]

PAGE_MARK = re.compile(r"<!--\s*page\s+(\d+)\s+of\s+246\s*-->")
RE_CHAP = re.compile(r"^#{0,4}\s*第([一二三四五六七八九十]+)章\s*(.*)$")
RE_SEC = re.compile(r"^#{0,4}\s*§\s*(\d+)\s*(.*)$")
RE_PROB = re.compile(r"^(\d{1,3})\s*[.．]\s*(.*)$")
RE_SOL = re.compile(r"^(解|证|证明|分析|解答|提示)\s*[:：]?\s*(.*)$")
RE_IMG = re.compile(r"^!\[")
RE_NUM = re.compile(r"^\s*(\d{1,3})\s*$")
RE_ROMAN = re.compile(r"^\s*[ivxlcdm]{1,6}\s*$")


def load_pages(path):
    raw = io.open(path, encoding="utf-8", errors="replace").read()
    parts = PAGE_MARK.split(raw)
    out = []
    i = 1
    while i + 1 < len(parts):
        num = int(parts[i])
        body = parts[i + 1]
        out.append((num, body))
        i += 2
    return out


def classify(pdf, lines):
    """Return list of (pdf, kind, payload)."""
    res = []
    for idx, ln in enumerate(lines):
        s = ln.rstrip()
        if not s.strip():
            res.append((pdf, "blank", s))
            continue
        m = RE_CHAP.match(s.strip())
        if m:
            res.append((pdf, "chap", m.group(1) + "|" + m.group(2).strip()))
            continue
        m = RE_SEC.match(s.strip())
        if m:
            res.append((pdf, "sec", m.group(1) + "|" + m.group(2).strip()))
            continue
        m = RE_PROB.match(s.strip())
        if m:
            res.append((pdf, "prob", m.group(1) + "|" + m.group(2)))
            continue
        m = RE_SOL.match(s.strip())
        if m:
            res.append((pdf, "sol", m.group(1) + "|" + m.group(2)))
            continue
        if RE_IMG.match(s.strip()):
            res.append((pdf, "img", s.strip()))
            continue
        m = RE_NUM.match(s)
        if m:
            res.append((pdf, "num", m.group(1)))
            continue
        if RE_ROMAN.match(s):
            res.append((pdf, "roman", s.strip()))
            continue
        res.append((pdf, "text", s.strip()))
    return res


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"
    outbuf = []
    global print
    _print = print

    def print(*a, **kw):  # noqa: A001
        kw.pop("flush", None)
        outbuf.append(" ".join(str(x) for x in a))
        _print(*a, **kw)

    allitems = []
    for path, a, b in RAWS:
        if not os.path.exists(path):
            continue
        for pdf, body in load_pages(path):
            allitems.append((pdf, body))
    allitems.sort(key=lambda x: x[0])

    seq = []
    for pdf, body in allitems:
        seq.extend(classify(pdf, body.splitlines()))

    if mode == "report":
        counts = Counter(k for _, k, _ in seq)
        print("kind counts:", dict(counts))
        print("\n=== CHAPTER / SECTION headings ===")
        for pdf, k, v in seq:
            if k in ("chap", "sec"):
                print("  pdf %3d  %-6s %s" % (pdf, k, v))
        print("\n=== ALL problem starts ===")
        for pdf, k, v in seq:
            if k == "prob":
                num, rest = v.split("|", 1)
                print("  pdf %3d  #%-4s %s" % (pdf, num, rest[:70]))
        print("\n=== image blocks ===")
        for pdf, k, v in seq:
            if k == "img":
                print("  pdf %3d  %s" % (pdf, v[:110]))
        print("\n=== roman / bare-number anomalies (non-footer) ===")
        for pdf, k, v in seq:
            if k == "num" and int(v) != pdf - 6:
                print("  pdf %3d  num=%s (expect footer %d)" % (pdf, v, pdf - 6))
            if k == "roman":
                print("  pdf %3d  roman=%s" % (pdf, v))
    else:
        for pdf, k, v in seq:
            if k in ("chap", "sec", "prob", "sol"):
                print("%3d %-5s %s" % (pdf, k, v[:80]))
    outp = os.path.join(CJX, "tools", "report_%s.txt" % mode)
    with io.open(outp, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(outbuf) + "\n")
    _print("wrote " + outp)


if __name__ == "__main__":
    main()
