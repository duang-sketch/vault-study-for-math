# -*- coding: utf-8 -*-
"""Parse MinerU raw markdown, extract per-page candidate printed page numbers
and report the printed-page vs PDF-page offset distribution."""
import re
import sys
import glob
import os
from collections import Counter

MARK = re.compile(r"<!--\s*page\s+(\d+)\s+of\s+(\d+)\s*-->")
NUMLINE = re.compile(r"^\s*(\d{1,3})\s*$")


def pages_of(path):
    raw = open(path, encoding="utf-8", errors="replace").read()
    parts = MARK.split(raw)
    # parts: [pre, num, total, body, num, total, body, ...]
    out = []
    i = 1
    while i + 2 < len(parts) + 1 and i + 1 < len(parts):
        try:
            num = int(parts[i])
        except (ValueError, IndexError):
            break
        body = parts[i + 2] if i + 2 < len(parts) else ""
        out.append((num, body))
        i += 3
    return out


def main():
    default_dir = os.environ.get("CJX_DIR", "_raw")
    files = sys.argv[1:] or sorted(glob.glob(os.path.join(default_dir, "up_p*.md")))
    allpg = []
    for f in files:
        pg = pages_of(f)
        print("== %s : %d page blocks (%d..%d)" % (
            os.path.basename(f), len(pg),
            pg[0][0] if pg else -1, pg[-1][0] if pg else -1))
        allpg.extend(pg)

    print("\n-- per-page trailing numeric candidates --")
    diffs = Counter()
    for num, body in allpg:
        lines = [l.strip() for l in body.strip().splitlines() if l.strip()]
        cands = []
        for l in lines[-3:]:
            m = NUMLINE.match(l)
            if m:
                cands.append(int(m.group(1)))
        if cands:
            d = cands[-1] - num
            diffs[d] += 1
            print("pdf %3d -> cand %-18s diff %+d" % (num, cands, d))
        else:
            print("pdf %3d -> cand -" % num)

    print("\n-- offset histogram (printed - pdf) --")
    for d, c in sorted(diffs.items()):
        print("  %+d : %d pages" % (d, c))


if __name__ == "__main__":
    main()
