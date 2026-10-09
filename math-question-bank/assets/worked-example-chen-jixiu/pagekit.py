#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Page-tracking helper for the MinerU raw markdown.

The raw .md files emitted by `mineru parse` carry `<!-- page N of 260 -->`
markers (scan page index).  This module loads one or more raw files, splits
them on those markers, and exposes per-page text plus the printed-page
offset (printed = scan - OFFSET).
"""
import re
import sys
import io

MARKER = re.compile(r'^<!--\s*page\s+(\d+)\s+of\s+\d+\s*-->\s*$')


def load_pages(paths):
    """Return {scan_page_number: [lines...]} merged across raw files."""
    pages = {}
    for path in paths:
        cur = None
        with io.open(path, encoding='utf-8') as fh:
            for raw in fh:
                line = raw.rstrip('\n')
                m = MARKER.match(line.strip())
                if m:
                    cur = int(m.group(1))
                    pages.setdefault(cur, [])
                    continue
                if cur is not None:
                    pages[cur].append(line)
    return pages


def load_ordered(paths):
    """Return [(scan_page, [lines...])] in scan order."""
    pages = load_pages(paths)
    return [(p, pages[p]) for p in sorted(pages)]


if __name__ == '__main__':
    ordered = load_ordered(sys.argv[1:])
    print('pages loaded: %d' % len(ordered))
    if ordered:
        print('range: %d .. %d' % (ordered[0][0], ordered[-1][0]))
    for p, lines in ordered:
        txt = '\n'.join(lines)
        nz = [l for l in lines if l.strip()]
        print('---- scan p.%d (%d non-empty lines) ----' % (p, len(nz)))
        print(nz[0][:90] if nz else '(empty)')
