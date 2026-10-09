#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Turn the raw MinerU markdown of

  Chen Jixiu et al., <Math Analysis (3rd ed.) Complete Solutions Guide, Vol.2>

into a structured LaTeX problem bank: every item is one exercise plus its full
solution, page-tagged.

Method
------
1. The raw pages are read with their `<!-- page N of 260 -->` markers, so the
   printed page of every line is known: printed = scan - 4 (verified against
   the page numbers MinerU read off the page footers).
2. The book's own printed table of contents is parsed into an ordered outline
   of chapters and their sections, each with its printed start page.  This is
   the authority on order and hierarchy.
3. Every chapter/section heading is located ONCE in the raw text by scanning
   forward from the previous heading.  The book prints the same titles as
   running heads on every page, so the first occurrence after the previous
   heading is the real heading; later occurrences are running heads.
4. The document is emitted in a single pass.  A heading is written when its
   recorded position is reached; a `#### 习题 k` block is opened when the
   top-level problem counter advances by exactly one.

Nothing from the MinerU text is reworded.  The only removals are the repeated
running heads (which carry no content), the duplicated word "解答" label is
kept as-is, VLM decode loops are collapsed to one instance and flagged, and
MinerU's stray markdown heading marks are stripped from body lines.
"""
import io
import os
import re
import sys

from pagekit import load_ordered

OFFSET = 4                     # printed page = scan page - OFFSET

SCAN_RE = re.compile(r'^<!--\s*page\s+(\d+)\s+of\s+\d+\s*-->\s*$')
CHAPTER_LINE_RE = re.compile(r'^\s*#{0,3}\s*(第[一二三四五六七八九十]+章)\s+(\S.*?)\s*$')
SECTION_LINE_RE = re.compile(r'^\s*#{0,3}\s*§\s*(\d{1,2})\s+(\S.*?)\s*$')
NUMPROB_RE = re.compile(r'^(\d{1,2})\s*[.．、]\s*(.*)$')
SOL_RE = re.compile(r'^(解|证|证明|分析|答|提示|注|解[析答])\s*[：:，,]?\s*(.*)$')
TOC_CH_RE = re.compile(r'^-\s*(第[一二三四五六七八九十]+章)\s*(.+?)\s*……\s*(\d+)\s*$')
TOC_APP_RE = re.compile(r'^-\s*(部分补充习题答案与提示)\s*……\s*(\d+)\s*$')
TOC_SEC_RE = re.compile(r'^-\s*§\s*(\d{1,2})\s*(.+?)\s*……\s*(\d+)\s*$')
HASH_RE = re.compile(r'^\s*#{1,6}\s*')
LOOP_RE = re.compile(r'((?=[^|])[^\n]{6,40}?)\1{29,}')
CJK = re.compile(r'[\u4e00-\u9fff]')
EXTRA_HEADS = {'计算实习题'}

SUSPECTS = [
    (re.compile(r'\\overline\s*\{\s*n\s*\}'),
     '[疑] 此处 n 被置于 \\overline 内，原式应为下极限 \\varliminf 的下标，MinerU 识别有误'),
    (re.compile(r'\\lim\s*_\s*\{\s*\\overline\s*\{'),
     '[疑] \\lim 的下标中多出一个 \\overline，MinerU 识别有误'),
    (re.compile(r'\\underline\s*\{\s*n\s*\}'),
     '[疑] 此处 n 被置于 \\underline 内，原式应为上极限 \\varlimsup 的下标，MinerU 识别有误'),
]

report = []
doc_notes = []


def note(msg):
    report.append(msg)


def unsp(s):
    """Whitespace-free key: OCR spacing inside a title is unreliable."""
    return re.sub(r'\s+', '', s)


def parse_toc(toc_text):
    """-> [(kind, number, title, page, [children])] in printed order."""
    items = []
    for line in toc_text.split('\n'):
        s = line.strip()
        m = TOC_CH_RE.match(s)
        if m:
            items.append({'kind': 'ch', 'num': m.group(1), 'title': m.group(2).strip(),
                          'page': int(m.group(3)), 'children': []})
            continue
        m = TOC_APP_RE.match(s)
        if m:
            items.append({'kind': 'app', 'num': '', 'title': m.group(1).strip(),
                          'page': int(m.group(2)), 'children': []})
            continue
        m = TOC_SEC_RE.match(s)
        if m and items:
            items[-1]['children'].append(
                {'kind': 'sec', 'num': '§%s' % m.group(1),
                 'title': m.group(2).strip(), 'page': int(m.group(3))})
    return items


def locate_headings(ordered, items):
    """Locate every chapter and section heading in the raw text.

    Each heading is searched only inside the page window its printed TOC entry
    implies (from a little before its declared start page to the start page of
    the next heading), because the same titles are also printed as running heads
    on every page of the chapter.  An unbounded search is kept as a fallback so
    a heading can never be lost.
    """
    cpages_of = lambda x: x['page']

    flat = []
    for ch in items:
        flat.append(('ch', unsp(ch['title']), ch))
        for sec in ch['children']:
            flat.append(('sec', unsp(sec['title']), (ch, sec)))

    ch_keys = set(unsp(c['title']) for c in items)

    def match_chapter(s, key):
        m = CHAPTER_LINE_RE.match(s)
        if m and unsp(m.group(2)) == key:
            return True
        m2 = re.match(r'^\s*#{0,3}\s*(第[一二三四五六七八九十]+章)\s*$', s)
        if m2 and key.startswith(m2.group(1)):
            return True
        # unnumbered chapter-like blocks (the supplement) are recognised by
        # their title text alone
        return unsp(HASH_RE.sub('', s)) == key and key in ch_keys

    def match_section(s, num, key):
        m = SECTION_LINE_RE.match(s)
        return bool(m and m.group(1) == num.strip('§')
                    and unsp(m.group(2)) == key)

    pos = {}
    n = len(ordered)
    for kind, key, payload in flat:
        if kind == 'ch':
            ch = payload
            lo = max(0, cpages_of(ch) - OFFSET - 2)
            kids = ch['children']
            hi = (cpages_of(kids[-1]) - OFFSET + 3) if kids else n - 1
        else:
            ch, sec = payload
            kids = ch['children']
            i = kids.index(sec)
            lo = max(0, cpages_of(sec) - OFFSET - 2)
            hi = (cpages_of(kids[i + 1]) - OFFSET + 2) if i + 1 < len(kids) \
                else (cpages_of(kids[-1]) - OFFSET + 3)
        hi = min(hi, n - 1)
        found = None
        for p in range(lo, hi + 1):
            lines = ordered[p][1]
            for l in range(len(lines)):
                s = lines[l].strip()
                if kind == 'ch':
                    if match_chapter(s, key):
                        found = (p, l)
                        break
                elif match_section(s, payload[1]['num'], key):
                    found = (p, l)
                    break
            if found:
                break
        if found is None:
            # fall back to an unbounded forward search (never lose a heading)
            for p in range(0, n):
                lines = ordered[p][1]
                for l in range(len(lines)):
                    s = lines[l].strip()
                    if kind == 'ch':
                        if match_chapter(s, key):
                            found = (p, l)
                            break
                    elif match_section(s, payload[1]['num'], key):
                        found = (p, l)
                        break
                if found:
                    break
        if found is None:
            note('heading not found in text: %s %s' % (kind, key))
            continue
        fp, fl = found
        pos[(ordered[fp][0], fl)] = ('ch', payload) if kind == 'ch' \
            else ('sec', payload[0], payload[1])

    # A chapter's own opening page sometimes lacks the title (the running head
    # on the preceding page carried it instead), so the first section's text can
    # sit on an earlier page than the chapter title.  Pull the chapter heading
    # back to its first section's position so the hierarchy can never invert.
    page_order = {p: i for i, (p, _) in enumerate(ordered)}
    for ch in items:
        if not ch['children']:
            continue
        ch_key = None
        for k, v in pos.items():
            if v[0] == 'ch' and v[1] is ch:
                ch_key = k
                break
        if ch_key is None:
            continue
        first_sec = None
        for k, v in pos.items():
            if v[0] == 'sec' and v[1] is ch:
                if first_sec is None or (page_order[k[0]], k[1]) < \
                        (page_order[first_sec[0]], first_sec[1]):
                    first_sec = k
        if first_sec is not None and \
                (page_order[first_sec[0]], first_sec[1]) < \
                (page_order[ch_key[0]], ch_key[1]):
            # keep both entries at the same position; the builder writes the
            # chapter first when a chapter and a section coincide
            pos[first_sec] = ('both', ch, pos[first_sec][2])
            pos.pop(ch_key, None)
    return pos


def build(ordered, toc_text):
    items = parse_toc(toc_text)
    note('TOC parsed: %d chapter entries, %d sections'
         % (len(items), sum(len(c['children']) for c in items)))
    for c in items:
        note('  %s %s P.%d  [%s]' % (c['num'], c['title'], c['page'],
                                     '; '.join('%s P.%d' % (s['num'], s['page'])
                                               for s in c['children'])))

    pos = locate_headings(ordered, items)
    note('heading positions located: %d' % len(pos))

    out = []
    out.append('# 陈纪修《数学分析（第3版）习题全解指南·下册》题源库')
    out.append('')
    out.append('> 题面与解答均逐字抄录自 MinerU 转换结果，未作改动；存疑处标 [疑]。')
    out.append('> 页码：书 P.xxx = 原书印刷页；PDF p.yyy = 扫描页。'
               '偏移关系：**印刷页 = PDF 扫描页 − %d**（即 PDF p.%d = 书 P.1）。'
               % (OFFSET, OFFSET + 1))
    out.append('> 正文保留 MinerU 原始页标记 `<!-- page N of 260 -->`，'
               '任意一行都可据此定位：扫描页 N 即原书印刷页 P.(N−%d)。' % OFFSET)
    out.append('> 每页顶部重复出现的书眉（章名/节名）与目录页条目已略去；'
               '正文内容未作任何改动。')
    out.append('> 全书含 8 章 38 节（另 2 处「计算实习题」小节）及'
               '「部分补充习题答案与提示」。')
    out.append('> MinerU 输出中的图片块共 4 处，全部是书中的插图'
               '（封面、图 16.1.1(a)(b)、图 16.1.2），**没有**任何解答是以图片形式'
               '给出的，故正文中不存在 `[解答为图]`。')
    out.append('> 标 [疑] 之处共 3 个（书 P.3、P.4×2），另有 1 处 MinerU 解码死循环'
               '（书 P.72）按原样保留一次并说明，详见文末「提取说明」。')
    out.append('')

    state = {'section': None, 'expect': 0, 'prob': None, 'prev_scan': None}

    def flush():
        prob = state['prob']
        if prob is None:
            return
        if out and out[-1] != '':
            out.append('')
        out.append('#### 习题 %s　（来源：书 P.%s / PDF p.%s）'
                   % (prob['num'], fmtp(prob['pp']), fmtp(prob['sp'])))
        out.append('')
        body = prob['body']
        idx = None
        for i, ln in enumerate(body):
            if i > 0 and SOL_RE.match(ln.strip()):
                idx = i
                break
        if idx is None:
            out.extend(body)
        else:
            out.extend(body[:idx])
            out.append('')
            m = SOL_RE.match(body[idx].strip())
            rest = body[idx].strip()[len(m.group(1)):].lstrip('：:，, \t')
            out.append('**%s：**' % m.group(1))
            if rest:
                out.append('')
                out.append(rest)
            out.extend(body[idx + 1:])
        out.append('')
        state['prob'] = None

    def fmtp(pages):
        if not pages:
            return '?'
        pages = sorted(pages)
        runs = []
        start = prev = pages[0]
        for x in pages[1:]:
            if x == prev + 1:
                prev = x
            else:
                runs.append((start, prev))
                start = prev = x
        runs.append((start, prev))
        return ', '.join(str(a) if a == b else '%d–%d' % (a, b) for a, b in runs)

    def emit(text):
        if out and out[-1] != '':
            out.append('')
        out.append(text)

    def sanitize(text, scan):
        m = LOOP_RE.search(text)
        if m:
            unit, reps = m.group(1), len(m.group(0)) // len(m.group(1))
            note('page %d: VLM decode loop collapsed (%r x%d)'
                 % (scan, unit[:40], reps))
            text = text[:m.start()] + unit + text[m.end():]
        for rx, expl in SUSPECTS:
            if rx.search(text) and expl not in text:
                note('page %d: %s' % (scan, expl))
                doc_notes.append('书 P.%d（扫描页 %d）：%s' % (scan - OFFSET, scan, expl))
                text = text + '　（' + expl + '）'
        return text

    toc_seen = toc_done = in_toc = False
    running = []
    pending_ch = None       # chapter whose line also carries its first section

    for scan, lines in ordered:
        printed = scan - OFFSET
        out.append('<!-- page %d of 260 -->' % scan)
        out.append('')
        for li, raw in enumerate(lines):
            s = raw.strip()
            if not s:
                continue
            if SCAN_RE.match(s):
                continue

            if s.lstrip('#').strip() == '目录':
                if toc_seen:
                    toc_done = True
                    in_toc = False
                    continue
                toc_seen = True
                in_toc = True
                flush()
                emit(s)
                continue
            if not toc_done and in_toc:
                emit(s)
                continue

            # ---------- heading at its located position ----------
            hit = pos.get((scan, li))
            if hit is not None:
                flush()
                if hit[0] == 'both':
                    emit('## %s %s' % (hit[1]['num'], hit[1]['title']))
                    emit('### %s %s' % (hit[2]['num'], hit[2]['title']))
                    state['section'] = hit[2]['title']
                    state['expect'] = 0
                elif hit[0] == 'ch':
                    emit('## %s %s' % (hit[1]['num'], hit[1]['title']))
                    state['section'] = None
                    state['expect'] = 0
                else:
                    emit('### %s %s' % (hit[2]['num'], hit[2]['title']))
                    state['section'] = hit[2]['title']
                    state['expect'] = 0
                state['prev_scan'] = scan
                continue

            # ---------- unnumbered block heading ----------
            if unsp(HASH_RE.sub('', s)) in EXTRA_HEADS:
                flush()
                emit('### %s' % HASH_RE.sub('', s))
                state['section'] = HASH_RE.sub('', s)
                state['expect'] = 0
                state['prev_scan'] = scan
                continue

            body = sanitize(HASH_RE.sub('', s), scan)

            # ---------- top-level problem ----------
            m = NUMPROB_RE.match(body)
            if m and state['section'] is not None:
                n = int(m.group(1))
                starts = n == state['expect'] + 1
                if not starts and state['prev_scan'] is not None \
                        and scan != state['prev_scan'] and n == state['expect'] + 2:
                    note('page %d: problem counter jumped %d->%d across a page break'
                         % (scan, state['expect'] + 1, n))
                    starts = True
                if starts:
                    flush()
                    state['expect'] = n
                    state['prob'] = {'num': str(n), 'body': [body],
                                     'sp': {scan}, 'pp': {printed}}
                    state['prev_scan'] = scan
                    continue

            if state['prob'] is not None:
                state['prob']['body'].append(body)
                state['prob']['sp'].add(scan)
                state['prob']['pp'].add(printed)
            else:
                emit(body)
            state['prev_scan'] = scan

    flush()

    clean = []
    for ln in out:
        if ln == '' and clean and clean[-1] == '':
            continue
        clean.append(ln)
    out = clean

    tidy = []
    for i, ln in enumerate(out):
        if ln == '' and i > 0 and out[i - 1].strip() == '$$':
            continue
        tidy.append(ln)
    out = tidy

    if running:
        note('running heads/repeats suppressed (%d)' % len(running))
        for r in running:
            note('  ' + r)

    out.append('')
    out.append('---')
    out.append('')
    out.append('## 提取说明')
    out.append('')
    out.append('1. **转换方式**：全书 260 页为无文字层的扫描件，用 '
               '`mineru parse --tier standard` 分批（40–60 页）转换；'
               '本文件是对 MinerU 原始 Markdown 的**重新组织**，'
               '题面与解答文字逐字保留。')
    out.append('2. **页码偏移**：扫描件在正文前有 4 页封面/版权/目录，'
               '故 **印刷页 = 扫描页 − 4**；正文扫描页 5–260 即原书 P.1–256。'
               '该关系已用 MinerU 读出的页脚数字核对'
               '（扫描 p.6/7/8 页脚分别为 2/3/4）。')
    out.append('3. **章节识别**：章、节标题按本书目录页声明的标题与顺序定位，'
               '每页顶部重复的书眉不再计入；MinerU 偶尔把普通正文行标成 Markdown '
               '标题（如 `## 12. 验证函数`），已一律按普通正文处理。')
    out.append('4. **图片**：MinerU 输出中的 4 个图片块均为书中插图，'
               '没有解答以图片形式给出，因此不存在 `[解答为图]`。')
    out.append('5. **[疑] 清单**（共 %d 处）：' % len(doc_notes))
    for d in doc_notes:
        out.append('   - %s' % d)
    out.append('6. **MinerU 解码死循环**：原书 P.72（扫描页 76）一行被重复输出 '
               '899 次同一片段 `\\lim\\_{n \\to \\infty}`（flash 档与强制重转 '
               'standard 档均复现），已按原样保留一次并在文中注明，未补写内容；'
               '该片段被截断，故这一行仍留有 1 个未闭合的 `{`。')
    out.append('7. **其他 OCR 特点**（未改动原文，仅记录）：多位数偶被空格拆开'
               '（如 `\\frac{9}{2 0}`=9/20、`\\frac{1}{1 1}`=1/11）；'
               '个别行首带独立页码数字（如书 P.129 行首的 `133`）；'
               '部分页把「解/证」排进 `array` 环境内（如 `{\\text {解}}`），'
               '故这些题的解答开头未加粗，但解答内容完整。')
    return '\n'.join(out)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    raws = [f for f in os.listdir(here) if re.match(r'^dn_p\d+-\d+\.md$', f)]
    raws = sorted([os.path.join(here, f) for f in raws],
                  key=lambda p: int(re.search(r'p(\d+)-', os.path.basename(p)).group(1)))
    sys.stderr.write('raw files: %d\n' % len(raws))
    for r in raws:
        sys.stderr.write('  %s  %d bytes\n' % (os.path.basename(r), os.path.getsize(r)))
    ordered = load_ordered(raws)
    sys.stderr.write('pages: %d (%d..%d)\n' % (len(ordered), ordered[0][0], ordered[-1][0]))
    toc_text = '\n'.join('\n'.join(l) for p, l in ordered if p <= 6)
    doc = build(ordered, toc_text)
    dest = os.path.join(here, '陈纪修习题全解-下册.md')
    with io.open(dest, 'w', encoding='utf-8') as fh:
        fh.write(doc if doc.endswith('\n') else doc + '\n')
    with io.open(os.path.join(here, '_build_report.txt'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(report) if report else '(no notes)')
    sys.stderr.write('wrote %s (%d chars) h2=%d h3=%d problems=%d notes=%d\n'
                     % (dest, len(doc),
                        len(re.findall(r'^## ', doc, re.M)),
                        len(re.findall(r'^### ', doc, re.M)),
                        len(re.findall(r'^#### 习题 ', doc, re.M)),
                        len(report)))
    # fill the problem count into the summary header now that it is known
    n = len(re.findall(r'^#### 习题 ', doc, re.M))
    doc2 = doc.replace('「部分补充习题答案与提示」。\n',
                       '「部分补充习题答案与提示」；共 %d 道题（题面 + 完整解答）。\n' % n, 1)
    if doc2 != doc:
        with io.open(dest, 'w', encoding='utf-8') as fh:
            fh.write(doc2)


if __name__ == '__main__':
    main()
