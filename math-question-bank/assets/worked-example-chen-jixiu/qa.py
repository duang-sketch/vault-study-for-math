#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QA scan over the assembled document + raw MinerU batches.

Reports:
  * coverage: scan pages present / missing, per raw file
  * image-block references (possible "[解答为图]" spots)
  * suspicious OCR tokens worth a [疑] marker
  * problems with no solution opener (statement-only)
  * duplicate / out-of-order problem counters
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pagekit import load_ordered

HERE = os.path.dirname(os.path.abspath(__file__))
TOTAL = 260

SUSPECT = [
    (re.compile(r'\bT\b\s*\$\s*\$'), 'stray T'),
    (re.compile(r'\\\\begin\{array\}'), 'array env'),
    (re.compile(r'\\boldsymbol\{'), 'boldsymbol'),
    (re.compile(r'\\tag\s*\{'), 'tag'),
    (re.compile(r'[\uFFFD]'), 'replacement char U+FFFD'),
    (re.compile(r'\$[^$]*\$\s*\$[^$]*\$'), 'adjacent inline math'),
    (re.compile(r'\\varlimsup|\\varliminf'), 'varlimsup'),
    (re.compile(r'\\overline\{\\lim'), 'overline lim'),
    (re.compile(r'\\lim_\{n\s*\\to\s*\\infty\}x_n'), 'lim x_n'),
    (re.compile(r'e_?\{?0\}?'), 'e0 typo?'),
    (re.compile(r'\\mathrm\{d\}'), 'mathrm d'),
    (re.compile(r'\\dots'), 'dots'),
]


def main():
    raws = sorted(
        [os.path.join(HERE, f) for f in os.listdir(HERE)
         if re.match(r'^dn_p\d+-\d+\.md$', f)],
        key=lambda p: int(re.search(r'p(\d+)-', os.path.basename(p)).group(1)))
    ordered = load_ordered(raws)
    have = set(p for p, _ in ordered)
    missing = [p for p in range(1, TOTAL + 1) if p not in have]

    out = []
    out.append('raw files: %d' % len(raws))
    for r in raws:
        out.append('  %s  %d bytes' % (os.path.basename(r), os.path.getsize(r)))
    out.append('scan pages present: %d / %d' % (len(have), TOTAL))
    out.append('missing scan pages: %s' % (missing if missing else 'none'))
    out.append('')

    img = []
    suspects = []
    for p, lines in ordered:
        for i, ln in enumerate(lines):
            s = ln.strip()
            if not s:
                continue
            if '![Image block' in s:
                img.append('page %d: %s' % (p, s[:100]))
            for rx, why in SUSPECT:
                if rx.search(s):
                    suspects.append('p.%d [%s] %s' % (p, why, s[:150]))
                    break
    out.append('=== image blocks: %d ===' % len(img))
    out.extend(img)
    out.append('')
    out.append('=== suspect tokens: %d ===' % len(suspects))
    out.extend(suspects[:200])
    out.append('')

    doc = io.open(os.path.join(HERE, '陈纪修习题全解-下册.md'), encoding='utf-8').read()
    blocks = re.split(r'\n(?=#### 习题 )', doc)
    hdr = re.compile(r'^#### 习题 (\d+)　（来源：书 P\.([^)]*) / PDF p\.([^)]*)）')
    nosol = []
    nprob = 0
    for b in blocks:
        m = hdr.match(b)
        if not m:
            continue
        nprob += 1
        if '**解：**' not in b and '**证：**' not in b and '**分析：**' not in b \
                and '**答：**' not in b and '**提示：**' not in b and '**证明：**' not in b:
            nosol.append('probl. %s (book P.%s / scan p.%s)' % (m.group(1), m.group(2), m.group(3)))
    out.append('=== assembled problems: %d ===' % nprob)
    out.append('=== problems without a solution opener: %d ===' % len(nosol))
    out.extend(nosol[:120])

    with io.open(os.path.join(HERE, '_qa_report.txt'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(out))
    sys.stderr.write('QA written: pages=%d problems=%d images=%d suspects=%d nosol=%d\n'
                     % (len(have), nprob, len(img), len(suspects), len(nosol)))


if __name__ == '__main__':
    main()
