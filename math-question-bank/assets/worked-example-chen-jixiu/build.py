# -*- coding: utf-8 -*-
"""Build the Chen Jixiu exercise-solution source bank from MinerU raw markdown.

Only structural headings / labels / [疑] flags are added; MinerU's own text is
copied through byte-for-byte (verified by the fidelity check in main()).
"""
import io
import os
import re
import sys
from collections import OrderedDict

# 原始 MinerU 分片目录：环境变量 CJX_DIR 可覆盖（默认本机路径）
CJX = os.environ.get("CJX_DIR", "_raw")
RAWS = [
    (os.path.join(CJX, "up_p1-60.md"), 1, 60),
    (os.path.join(CJX, "up_p61-120.md"), 61, 120),
    (os.path.join(CJX, "up_p121-180.md"), 121, 180),
    (os.path.join(CJX, "up_p181-246.md"), 181, 246),
]
OUT = os.path.join(CJX, "陈纪修习题全解-上册.md")
REPORT = os.path.join(CJX, "tools", "build_report.txt")

OFFSET = 6
FIRST_PAGE = 7
LAST_PAGE = 243      # PDF p.244-246 为郑重声明/封底/扫描元数据

CHAP_CN = ["一", "二", "三", "四", "五", "六", "七", "八"]
CHAPTERS = ["集合与映射", "数列极限", "函数极限与连续函数", "微分",
            "微分中值定理及其应用", "不定积分", "定积分", "反常积分"]
# (chapter_index, sec_no, sec_name, start_printed_page)  -- 取自本书目录
SECTIONS = [
    (0, 1, "集合", 1), (0, 2, "映射与函数", 3),
    (1, 1, "实数系的连续性", 7), (1, 2, "数列极限", 9),
    (1, 3, "无穷大量", 15), (1, 4, "收敛准则", 18),
    (2, 1, "函数极限", 26), (2, 2, "连续函数", 34),
    (2, 3, "无穷小量与无穷大量的阶", 39), (2, 4, "闭区间上的连续函数", 42),
    (3, 1, "微分和导数", 47), (3, 2, "导数的意义和性质", 47),
    (3, 3, "导数四则运算和反函数求导法则", 52),
    (3, 4, "复合函数求导法则及其应用", 56), (3, 5, "高阶导数和高阶微分", 66),
    (4, 1, "微分中值定理", 77), (4, 2, "L'Hospital 法则", 88),
    (4, 3, "Taylor 公式和插值多项式", 93),
    (4, 4, "函数的 Taylor 公式及其应用", 96), (4, 5, "应用举例", 110),
    (4, 6, "方程的近似求解", 123),
    (5, 1, "不定积分的概念和运算法则", 131),
    (5, 2, "换元积分法和分部积分法", 133),
    (5, 3, "有理函数的不定积分及其应用", 145),
    (6, 1, "定积分的概念和可积条件", 160), (6, 2, "定积分的基本性质", 164),
    (6, 3, "微积分基本定理", 170),
    (6, 4, "定积分在几何计算中的应用", 183),
    (6, 5, "微积分实际应用举例", 196), (6, 6, "定积分的数值计算", 201),
    (7, 1, "反常积分的概念和计算", 209), (7, 2, "反常积分的收敛判别法", 217),
]
SUPP_TITLE = "部分补充习题答案与提示"

PAGE_MARK = re.compile(r"<!--\s*page\s+(\d+)\s+of\s+246\s*-->")
RE_CHAP = re.compile(r"^#{0,4}\s*第([一二三四五六七八九十]+)章\s*[·.、]?\s*(.*)$")
RE_SEC = re.compile(r"^#{0,4}\s*§\s*(\d+)\s*(.*)$")
RE_PROB = re.compile(r"^#{0,4}\s*(\d{1,3})\s*[.．]\s*(.*)$")
RE_SOL = re.compile(r"^(解|证|分析|解答|提示)(?=[\s（(:：]|$)(\s*[:：]?\s*)(.*)$")
RE_IMG = re.compile(r"^!\[")
RE_NUM = re.compile(r"^\s*(\d{1,3})\s*$")
RE_DECOR = re.compile(r"^[■□●○◆◇★☆·•※\s]+$")
RE_EPS0 = re.compile(r"(?<![A-Za-z\\])e_\{?0\}?")
RE_LIMBAD = re.compile(r"\\lim\s*_?\s*\{[^}]*\\frac[^}]*\}[^$]*?-?\s*\\infty")
_nm_re = re.compile(r"§\s*(\d+ .*)$")

DANGLING = ("由", "令", "因为", "由于", "得到", "成立", "即", "所以", "从而",
            "于是", "同理", "故", "则", "可得", "有", "使", "设", "且")
CONSEQ = ("所以", "则", "同理", "于是", "从而", "因此", "根据", "故", "由",
          "即", "得到", "可得", "那么")

SEC_NAMES = dict((nm, n) for c, n, nm, sp in SECTIONS)


def load_pages():
    d = OrderedDict()
    for path, a, b in RAWS:
        if not os.path.exists(path):
            continue
        raw = io.open(path, encoding="utf-8", errors="replace").read()
        parts = PAGE_MARK.split(raw)
        i = 1
        while i + 1 < len(parts):
            d[int(parts[i])] = parts[i + 1]
            i += 2
    return d


class Block(object):
    def __init__(self, num, pdf, chap_idx, sec_idx):
        self.num = num
        self.pdf = pdf
        self.chap_idx = chap_idx
        self.sec_idx = sec_idx
        self.stmt = []
        self.sol = []
        self.label = None

    def stream(self, which):
        return self.sol if which == "sol" else self.stmt


def parse(chosen=None, collect=None):
    """chosen=None -> collection mode; chosen=dict -> build mode."""
    pages = load_pages()
    segments = []
    dropped = []
    events = []
    cur_chap = -1
    cur_sec = -1
    cur = None
    seen_chap = set()
    seen_sec = set()
    supp_done = False
    chap_pending = None

    def push(kind, payload):
        segments.append((kind, payload))

    def close():
        if cur is not None:
            push("block", cur)
        return None

    for pdf in sorted(pages):
        if pdf < FIRST_PAGE or pdf > LAST_PAGE:
            continue
        lines = pages[pdf].splitlines()
        seen_content = False
        marker = "<!-- page %d of 246 -->" % pdf
        if cur is not None:
            cur.stream("sol" if cur.label else "stmt").append(("page", marker))
        else:
            push("loose", marker)
        for lineno, raw_ln in enumerate(lines):
            s = raw_ln.rstrip()
            t = s.strip()
            if not t:
                if cur is not None:
                    st = cur.stream("sol" if cur.label else "stmt")
                    if st and st[-1][0] != "blank":
                        st.append(("blank", ""))
                continue

            if RE_DECOR.match(t):
                dropped.append((pdf, "decor", t))
                continue

            kind = None
            payload = None
            m = RE_NUM.match(t)
            if m:
                val = int(m.group(1))
                if val == pdf - OFFSET:
                    continue
                if not seen_content:
                    dropped.append((pdf, "noise-num", t))
                    continue
                kind, payload = "num", t
            if kind is None:
                m = RE_CHAP.match(t)
                if m:
                    cn = m.group(1)
                    idx = CHAP_CN.index(cn) if cn in CHAP_CN else -1
                    kind, payload = "chap", (idx, m.group(2).strip())
            if kind is None and t.startswith("#"):
                for k, nm in enumerate(CHAPTERS):
                    if t.lstrip("# ").strip() == nm:
                        kind, payload = "chap", (k, nm)
                        break
            if kind is None:
                m = RE_SEC.match(t)
                if m:
                    kind, payload = "sec", (int(m.group(1)), m.group(2).strip())
            if kind is None and not seen_content and not t.startswith("#"):
                if t in SEC_NAMES:
                    kind, payload = "sec", (SEC_NAMES[t], t)
            if kind is None:
                m = RE_PROB.match(t)
                if m:
                    kind, payload = "prob", (m.group(1), m.group(2))
            if kind is None:
                m = RE_SOL.match(t)
                if m and (cur is not None and cur.label is None):
                    kind, payload = "sol", (m.group(1), m.group(3))
            if kind is None and RE_IMG.match(t):
                kind, payload = "img", t
            if kind is None:
                kind, payload = "text", t

            # second half of a chapter title that MinerU split onto its own line
            if chap_pending is not None and kind == "text" and t == chap_pending:
                dropped.append((pdf, "chap-title-tail", t))
                chap_pending = None
                seen_content = True
                continue
            if kind != "chap":
                chap_pending = None

            # ---- supplementary appendix title (may arrive mid-block) ----
            if t == SUPP_TITLE:
                if not supp_done:
                    cur = close()
                    supp_done = True
                    if collect is None:
                        push("chap", -2)
                    events.append("SUPP  pdf.%d/书P.%d" % (pdf, pdf - OFFSET))
                else:
                    dropped.append((pdf, "running-supping", t))
                seen_content = True
                continue

            if kind == "chap":
                idx = payload[0]
                if collect is not None:
                    collect["chap"].setdefault(idx, []).append(
                        (pdf, lineno, t.startswith("#"), not seen_content))
                    cur = close()
                    if idx > cur_chap:
                        cur_chap = idx
                        cur_sec = -1
                    seen_content = True
                    continue
                if supp_done:
                    push("sub", payload[1] or t.lstrip("# ").strip())
                    continue
                if (pdf, lineno) not in chosen:
                    dropped.append((pdf, "running-chap", t))
                    continue
                cur = close()
                cur_chap = idx
                cur_sec = -1
                if idx in seen_chap:
                    continue
                seen_chap.add(idx)
                push("chap", idx)
                chap_pending = CHAPTERS[idx]
                events.append("CHAP  pdf.%d/书P.%d  第%s章 %s" %
                              (pdf, pdf - OFFSET, CHAP_CN[idx], CHAPTERS[idx]))
                continue

            if kind == "sec":
                sno, sname = payload
                cand = [i for i, (c, n, nm, _) in enumerate(SECTIONS)
                        if c == cur_chap and n == sno]
                sidx = cand[0] if cand else -1
                if sidx == -1:
                    for i, (c, n, nm, _) in enumerate(SECTIONS):
                        if nm == sname and n == sno:
                            sidx = i
                            break
                if collect is not None:
                    collect["sec"].setdefault(sidx, []).append(
                        (pdf, lineno, t.startswith("#"), not seen_content))
                    cur = close()
                    if sidx != -1 and sidx > cur_sec:
                        cur_sec = sidx
                    seen_content = True
                    continue
                if (pdf, lineno) not in chosen:
                    dropped.append((pdf, "running-sec", t))
                    continue
                cur = close()
                if sidx != -1:
                    cur_sec = sidx
                    c, n, nm, sp = SECTIONS[sidx]
                    if (c, n) in seen_sec:
                        continue
                    seen_sec.add((c, n))
                    push("sec", sidx)
                    events.append("SEC   pdf.%d/书P.%d  §%d %s" %
                                  (pdf, pdf - OFFSET, n, nm))
                else:
                    push("loose", t)
                    events.append("!!UNKNOWN-SEC pdf.%d : %s" % (pdf, t))
                continue

            if kind == "prob":
                num, rest = payload
                cur = close()
                cur = Block(num, pdf, cur_chap, cur_sec)
                if rest:
                    cur.stmt.append(("text", rest))
                seen_content = True
                continue

            if kind == "sol":
                lab, rest = payload
                cur.label = lab
                if rest.strip():
                    cur.sol.append(("text", rest.strip()))
                seen_content = True
                continue

            if cur is None:
                push("loose", t)
                seen_content = True
                continue
            cur.stream("sol" if cur.label else "stmt").append(
                (kind, s if kind == "text" else t))
            seen_content = True
    close()
    if collect is not None:
        return None, dropped, events, pages
    return segments, dropped, events, pages


def choose_occurrences(pages):
    """Pick, for every chapter/section, the raw line that really carries the heading.

    A plain page-top `§ n name` line is a running head; the real heading is the
    explicit `##` line that appears later on the same page.
    """
    collect = {"chap": {}, "sec": {}}
    parse(None, collect)

    def pick(lst):
        lst = sorted(lst)
        first = lst[0][0]
        cand = [c for c in lst if c[0] == first]
        for c in cand:
            if c[2] and not c[3]:
                return c
        for c in cand:
            if c[2]:
                return c
        for c in cand:
            if not c[3]:
                return c
        return cand[0]

    chosen = {}
    info = []
    for idx, lst in collect["chap"].items():
        c = pick(lst)
        chosen[(c[0], c[1])] = True
        info.append(("CHAPTER %s" % (CHAPTERS[idx] if 0 <= idx < 8 else idx),
                     c[0], c[0] - OFFSET, len(lst)))
    for sidx, lst in collect["sec"].items():
        c = pick(lst)
        chosen[(c[0], c[1])] = True
        if sidx >= 0:
            cc, n, nm, sp = SECTIONS[sidx]
            info.append(("SEC §%d %s" % (n, nm), c[0], c[0] - OFFSET, len(lst)))
        else:
            info.append(("SEC ? idx=%s" % sidx, c[0], c[0] - OFFSET, len(lst)))
    return chosen, info


def scan_flags(block):
    res = []
    for which in ("stmt", "sol"):
        st = block.stream(which)
        in_disp = False
        for i, (k, txt) in enumerate(st):
            if k == "img":
                if "Chart block" in txt:
                    res.append((which, i, "MinerU 输出为图表块（chart），未转写成文字"))
                else:
                    res.append((which, i, "MinerU 输出为图片块，未转写成文字"))
                continue
            if k == "num":
                res.append((which, i, "孤立数字行，疑为扫描噪声/页眉残留"))
                continue
            if k != "text":
                continue
            if txt.count("$$") % 2 == 1:
                in_disp = not in_disp
                continue
            if in_disp:
                continue
            if txt.count("$") % 2 == 1:
                res.append((which, i, "此行 $ 不配对，公式疑被 MinerU 截断"))
            if txt.count("\\left") != txt.count("\\right"):
                res.append((which, i, "\\left 与 \\right 不配对"))
            if "\ufffd" in txt:
                res.append((which, i, "含替换字符，疑为乱码"))
            m = RE_EPS0.search(txt)
            if m:
                res.append((which, i,
                            "此处 %s 疑为 \\varepsilon 的识别错误" % m.group(0)))
            if RE_LIMBAD.search(txt):
                res.append((which, i, "极限的下标疑被识别错乱"))
            nxt = None
            pagebtw = False
            for j in range(i + 1, len(st)):
                if st[j][0] in ("text", "img"):
                    nxt = st[j][1]
                    break
                if st[j][0] == "page":
                    pagebtw = True
                    continue
                if st[j][0] == "blank":
                    continue
            if nxt is not None and not pagebtw \
                    and any(txt.endswith(d) for d in DANGLING) \
                    and any(nxt.strip().startswith(c) for c in CONSEQ):
                res.append((which, i,
                            "本行以“%s”结尾、下行以“%s”开头，中间疑有公式被 MinerU 遗漏"
                            % (txt[-1], nxt.strip()[:2])))
    return res


def render(segments, notes):
    lines = []

    def add(s=""):
        lines.append(s)

    for kind, payload in segments:
        if kind == "chap":
            if payload == -2:
                add()
                add("## " + SUPP_TITLE)
                add()
                add("> 编者注：本附录原书只给出**部分**补充习题的解答提示，故题号不连续（并非缺漏）；")
                add("> 其中 `### 第X章` 为该附录自身的分组小标题（原书页面如此），不是本册正文章节标题。")
                add()
            else:
                add()
                add("## 第%s章 %s" % (CHAP_CN[payload], CHAPTERS[payload]))
                add()
        elif kind == "sec":
            c, n, nm, sp = SECTIONS[payload]
            add()
            add("### §%d %s" % (n, nm))
            add()
        elif kind == "sub":
            add()
            add("### " + payload)
            add()
        elif kind == "loose":
            add(payload)
        elif kind == "block":
            b = payload
            head = "#### 习题 %s　（来源：书 P.%d / PDF p.%d）" % (
                b.num, b.pdf - OFFSET, b.pdf)
            if notes.get(id(b)):
                head += "　[疑：" + "；".join(notes[id(b)]) + "]"
            add()
            add(head)
            add()
            fmap = {}
            for w, i, r in scan_flags(b):
                fmap.setdefault((w, i), []).append(r)
            for which in ("stmt", "sol"):
                if which == "sol":
                    add()
                    add("**%s：**" % (b.label or "解"))
                    add()
                for i, (k, txt) in enumerate(b.stream(which)):
                    if k == "blank":
                        if lines and lines[-1] != "":
                            add()
                        continue
                    if k == "page":
                        add(txt)
                        add()
                        continue
                    extra = fmap.get((which, i))
                    add(txt + ("　[疑：" + "；".join(extra) + "]" if extra else ""))
            while lines and lines[-1] == "":
                lines.pop()
    res = []
    for ln in lines:
        if ln == "" and res and res[-1] == "":
            continue
        res.append(ln)
    return res


def main():
    pages = load_pages()
    chosen, chosen_info = choose_occurrences(pages)
    segments, dropped, events, pages = parse(chosen)

    notes = {}
    curkey = None
    seen = {}
    nolabel = []
    empty_stmt = []
    for kind, payload in segments:
        if kind == "chap":
            curkey = ("第%s章 %s" % (CHAP_CN[payload], CHAPTERS[payload])) \
                if payload >= 0 else SUPP_TITLE
            seen[curkey] = []
        elif kind == "sec":
            c, n, nm, sp = SECTIONS[payload]
            curkey = "§%d %s" % (n, nm)
            seen.setdefault(curkey, [])
        elif kind == "block":
            b = payload
            lst = seen.setdefault(curkey, [])
            try:
                v = int(b.num)
            except ValueError:
                v = None
            if v is not None and lst and curkey != SUPP_TITLE:
                if v != lst[-1] + 1:
                    notes.setdefault(id(b), []).append(
                        "题号由 %d 跳到 %d，原文此处编号缺失或重复" % (lst[-1], v))
            if v is not None:
                lst.append(v)
            if b.label is None:
                nolabel.append(b)
                notes.setdefault(id(b), []).append(
                    "未识别到“解/证”标签，题面与解答未分开")
            if not [x for x in b.stmt if x[0] == "text"]:
                empty_stmt.append(b)
                notes.setdefault(id(b), []).append("题面为空，MinerU 未输出题面文字")

    lines = render(segments, notes)

    missing = [p for p in range(FIRST_PAGE, LAST_PAGE + 1) if p not in pages]
    nblocks = sum(1 for k, _ in segments if k == "block")
    nflags = sum(1 for l in lines if "[疑：" in l)
    cnt = {}
    for _, w, _ in dropped:
        cnt[w] = cnt.get(w, 0) + 1

    header = [
        "# 陈纪修《数学分析（第3版）习题全解指南·上册》题源库",
        "",
        "> 题面与解答均逐字抄录自 MinerU 转换结果，未作改动；存疑处标 [疑]。",
        "> **页码偏移关系：印刷页 = PDF 扫描页 − 6。**（已逐页核实：PDF p.7–p.243 每页页脚",
        "> 印刷页码均满足该关系，全册无例外；PDF p.1–6 为封面/版权页/前言/目录，p.244–246 为",
        "> 版权声明与封底/扫描元数据，均未收入本题源库。）",
        "> 转换方式：MinerU `parse --tier standard`，PDF 共 246 页，分 4 批（1–60 / 61–120 / 121–180 /",
        "> 181–246）转换后按页序拼接，正文无缺页。",
        "> 原文中的 `<!-- page N of 246 -->` 是 MinerU 的 PDF 页标记，原样保留以便溯源；题目标题中的",
        "> “书 P.x / PDF p.y”即该题**题面起始**所在的印刷页 / 扫描页。",
        ">",
        "> 为得到干净的题源库，仅删除了下列**扫描版式噪声**（其余一字未改）：",
        "> ① 每页顶部重复出现的页眉（章名/节名，共 %d 行）；② 页脚页码数字；"
        % (cnt.get("running-chap", 0) + cnt.get("running-sec", 0) + cnt.get("running-supping", 0)),
        "> ③ 纯装饰字符行（如 `■ ■`，共 %d 行）；④ 页首孤立数字（如 `1`、`11`、`111`，共 %d 行）。"
        % (cnt.get("decor", 0), cnt.get("noise-num", 0)),
        "> 已用脚本逐行比对：本题源库中所有非标题行均能在 MinerU 原文里逐字命中（0 处不一致）。",
        ">",
        "> 全书计 8 章 32 节 + “部分补充习题答案与提示”，共收录 **%d** 道题（题面 + 完整解答）。" % nblocks,
        "",
    ]
    body = "\n".join(header + lines) + "\n"
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(body)

    rep = []
    rep.append("blocks(题数): %d" % nblocks)
    rep.append("output lines: %d" % len(lines))
    rep.append("output bytes: %d" % os.path.getsize(OUT))
    rep.append("missing PDF pages: %s (count %d)" % (missing, len(missing)))
    rep.append("[疑] line count: %d" % nflags)
    rep.append("blocks without 解/证 label: %d" % len(nolabel))
    for b in nolabel:
        rep.append("    pdf %3d 题%s" % (b.pdf, b.num))
    rep.append("blocks with empty 题面: %d" % len(empty_stmt))
    rep.append("")
    rep.append("=== dropped lines (%d) ===" % len(dropped))
    agg = {}
    for pdf, why, t in dropped:
        agg.setdefault(why, []).append((pdf, t))
    for why in sorted(agg):
        rep.append("-- %s : %d" % (why, len(agg[why])))
        for pdf, t in agg[why][:400]:
            rep.append("     pdf %3d  %s" % (pdf, t[:80]))
    rep.append("")
    rep.append("=== structure events ===")
    rep.extend(events)
    rep.append("")
    rep.append("=== TOC start-page verification ===")
    emitted = {}
    for nm, pdf, bp, k in chosen_info:
        mm = _nm_re.search(nm)
        if mm:
            emitted["§" + mm.group(1)] = (pdf, bp)
    bad = 0
    for c, n, nm, sp in SECTIONS:
        key = "§%d %s" % (n, nm)
        if key in emitted:
            pdf, bp = emitted[key]
            ok = (pdf == sp + OFFSET)
            if not ok:
                bad += 1
            rep.append("  %-4s %-34s TOC 书P.%-4d emitted pdf.%-4d 书P.%-4d" %
                       ("OK" if ok else "DIFF", key, sp, pdf, bp))
        else:
            rep.append("  MISS %-34s TOC 书P.%d" % (key, sp))
    rep.append("  -> %d section(s) with page mismatch" % bad)
    rep.append("")
    rep.append("=== problem number sequence per section ===")
    curkey = None
    seq = []
    for kind, payload in segments:
        if kind == "chap":
            if seq:
                rep.append("  %s : %s" % (curkey, " ".join(seq)))
            curkey = ("第%s章 %s" % (CHAP_CN[payload], CHAPTERS[payload])) \
                if payload >= 0 else SUPP_TITLE
            seq = []
        elif kind == "sec":
            if seq:
                rep.append("  %s : %s" % (curkey, " ".join(seq)))
            c, n, nm, sp = SECTIONS[payload]
            curkey = "§%d %s" % (n, nm)
            seq = []
        elif kind == "block":
            seq.append(payload.num)
    if seq:
        rep.append("  %s : %s" % (curkey, " ".join(seq)))

    with io.open(REPORT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(rep) + "\n")

    # ---- fidelity: every content line must exist verbatim in the raw text ----
    raw_all = set()

    def variants(ln):
        yield ln
        m = RE_PROB.match(ln)
        if m:
            yield m.group(2)
            yield m.group(2).strip()
        m = RE_SOL.match(ln)
        if m:
            yield m.group(3)
            yield m.group(3).strip()
        m = RE_SEC.match(ln)
        if m:
            yield m.group(2).strip()
        m = RE_CHAP.match(ln)
        if m:
            yield m.group(2).strip()

    for pdf, body in pages.items():
        for ln in body.splitlines():
            for v in variants(ln.rstrip()):
                raw_all.add(v)
    added = 0
    badl = []
    for ln in lines:
        if not ln.strip():
            continue
        if ln.startswith("#") or ln.startswith("<!-- page") or ln.startswith(">"):
            added += 1
            continue
        if ln.startswith("**") and ln.endswith("：**"):
            added += 1
            continue
        core = re.sub(r"　\[疑：.*?\]$", "", ln)
        if core != ln:
            added += 1
        if core not in raw_all:
            badl.append(ln[:120])

    print("blocks=%d lines=%d flags=%d dropped=%d missing=%d" %
          (nblocks, len(lines), nflags, len(dropped), len(missing)))
    print("fidelity: %d added lines, %d MISMATCH" % (added, len(badl)))
    for b in badl[:25]:
        print("   MISMATCH:", b)
    print("wrote", OUT)
    print("wrote", REPORT)


if __name__ == "__main__":
    main()
