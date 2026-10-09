#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""High-precision anomaly scan -> candidate [疑] spots.

Only patterns that are near-certain OCR/parse artefacts are reported, so the
number of [疑] marks in the deliverable stays small and every one is defensible.
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pagekit import load_ordered

HERE = os.path.dirname(os.path.abspath(__file__))

# (regex, short label, explanation for the [疑] line)
RULES = [
    (re.compile(r'\\overline\s*\{\s*n\s*\}'), 'overline-n',
     '下标 n 疑似误置于 \\overline 内（原式应为下极限）'),
    (re.compile(r'\\underline\s*\{\s*n\s*\}'), 'underline-n',
     '下标 n 疑似误置于 \\underline 内（原式应为上极限）'),
    (re.compile(r'\\lim\s*_\s*\{\s*\\overline\s*\{'), 'overline-in-lim',
     '\\lim 的下标中多出一个 \\overline'),
    (re.compile(r'\\lim\s*_\s*\{\s*\\underline\s*\{'), 'underline-in-lim',
     '\\lim 的下标中多出一个 \\underline'),
    (re.compile(r'\\frac\s*\{\s*\d+\s*\}\s*\{\s*\d+\s+\d+(?![\d}])\s*\}'), 'frac-spaced',
     '分母被 OCR 拆成空格分隔的数字'),
    (re.compile(r'\\sqrt\s*\{\s*\d+\s+\d+(?![\d}])\s*\}'), 'sqrt-spaced',
     '根号内被 OCR 拆成空格分隔的数字'),
    (re.compile(r'(?<![_{^\\a-zA-Z])T(?![a-zA-Z])'), 'stray-T',
     '孤立的 T，疑为识别噪声'),
    (re.compile(r'[\uFFFD\u0000-\u0008\u000B\u000C\u000E-\u001F]'), 'ctrl-char',
     '含控制字符/替换字符，识别失败'),
]

ALT = re.compile(r'&(?:amp|lt|gt|quot|#\d+);')
IMG = re.compile(r'!\[Image block\]\(([^)]*)\)')


def mask_code(s):
    """Replace math delimiters so brace/dollar balance can be judged."""
    return s


def brace_balance(text):
    # `\{` / `\}` are literal braces (\left\{ ...), not grouping -- exclude them
    t = text.replace(r'\{', '').replace(r'\}', '')
    return t.count('{') - t.count('}')


def dollar_parity(text):
    return text.count('$') % 2


def main():
    raws = sorted(
        [os.path.join(HERE, f) for f in os.listdir(HERE)
         if re.match(r'^dn_p\d+-\d+\.md$', f)],
        key=lambda p: int(re.search(r'p(\d+)-', os.path.basename(p)).group(1)))
    ordered = load_ordered(raws)
    have = sorted(p for p, _ in ordered)

    hits = []
    for p, lines in ordered:
        buf = []
        for i, ln in enumerate(lines):
            s = ln.strip()
            if not s:
                continue
            for rx, label, expl in RULES:
                if expl is None:
                    continue
                if rx.search(s):
                    hits.append((p, label, expl, s))
                    break
        # brace balance per page (whole page is a reasonable unit for math)
        page_text = '\n'.join(lines)
        bb = brace_balance(page_text)
        if bb != 0:
            hits.append((p, 'brace-imbalance',
                         '该页 { } 不配对（差 %d），疑有 OCR 截断' % bb, '(page-level)'))
        if dollar_parity(page_text) != 0:
            hits.append((p, 'dollar-odd',
                         '该页 $ 个数为奇数，疑有截断', '(page-level)'))

    out = ['pages: %d (%d..%d)' % (len(have), have[0], have[-1])]
    out.append('anomaly candidates: %d' % len(hits))
    out.append('')
    bykind = {}
    for p, label, expl, s in hits:
        bykind.setdefault(label, []).append((p, expl, s))
    for label in sorted(bykind):
        lst = bykind[label]
        out.append('### %s  (%d)' % (label, len(lst)))
        for p, expl, s in lst[:80]:
            out.append('  scan p.%d (书 P.%d): %s' % (p, p - 4, expl))
            out.append('    | %s' % s[:170])
        if len(lst) > 80:
            out.append('  ... %d more' % (len(lst) - 80))
        out.append('')

    with io.open(os.path.join(HERE, '_anomalies.txt'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(out))
    sys.stderr.write('anomalies: %d  kinds=%s\n'
                     % (len(hits), ','.join('%s:%d' % (k, len(v)) for k, v in sorted(bykind.items()))))


if __name__ == '__main__':
    main()
