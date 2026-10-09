"""Retag the question collections with accurate structured tags (v2).

Why v2: v1 inferred 知识块 by scanning the *body* for keywords. The bodies come
from a PDF text layer, so words such as 极限/连续/泰勒 appear everywhere and
~30-40% of the 大观 and Maki entries were filed under 极限与连续. v2 uses real
structural signals instead:

* 大观严选题  : 原编号 (1.3.1.6.2 -> 1.3 = 一元积分, 1.3.4 = 定积分 …) plus the
               题型 heading. MinerU garbles some digits into letters, so the
               chapter is forward/back filled from numeric neighbours and from
               the section -> chapter statistics of the same document.
* 竞赛教程题源 : the parent chunk heading (上册/下册 …) decides the chapter.
* Maki 真题   : the 考点 title line + 考点 段落 decides the chapter.
* 大观高数分册 : the document title (3.一元积分…) decides the chapter.

Backs up every original file before writing, then prints block histograms.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter, OrderedDict
from pathlib import Path

ENTRY = re.compile(r"^### (\S+)\s*$")
SECTION = re.compile(r"^## (?!##)(.+?)\s*$")
TAG = re.compile(r"^>\s*标签：\s*(.*)$")
ORIG_NUM = re.compile(r"原编号\s*([0-9]+(?:\.[0-9]+)*)")
STARS = re.compile(r"★")

# Fallback keyword rules, ordered specific -> general.
BLOCK_KEYWORDS = [
    ("反常积分", ("反常积分", "瑕积分", "无穷限积分", "广义积分", "审敛", "敛散")),
    ("曲线曲面积分", ("曲线积分", "曲面积分", "格林公式", "高斯公式", "斯托克斯", "通量", "旋度", "散度", "向量场")),
    ("无穷级数", ("级数", "幂级数", "傅里叶", "Fourier", "收敛域", "收敛半径")),
    ("重积分", ("二重积分", "三重积分", "累次积分", "重积分", "极坐标", "直角坐标", "交换积分次序")),
    ("多元微分", ("多元", "偏导", "全微分", "重极限", "偏微分", "方向导数", "梯度", "切平面", "可微性")),
    ("定积分应用", ("面积", "体积", "弧长", "旋转体", "形心", "平均值", "物理应用", "几何应用", "做功", "引力", "压力", "质心", "转动惯量")),
    ("向量与空间解析几何", ("向量代数", "数量积", "向量积", "平面方程", "空间直线", "旋转曲面", "柱面", "锥面", "空间曲线", "方向余弦", "夹角")),
    ("微分方程", ("微分方程", "差分方程", "特征方程", "一阶方程", "二阶方程", "常微分", "齐次方程")),
    ("不定积分", ("不定积分", "原函数", "凑微分", "换元积分", "分部积分")),
    ("定积分", ("定积分", "变限积分", "积分等式", "积分中值", "积分不等式")),
    ("中值定理与导数应用", ("中值定理", "罗尔", "拉格朗日", "泰勒公式", "泰勒展开", "极值", "最值", "拐点", "单调", "不等式", "零点", "方程根", "渐近线", "曲率", "最大化", "最小化")),
    ("导数与微分", ("导数", "微分", "可导", "求导", "切线", "法线", "参数方程", "隐函数")),
    ("线性代数", ("行列式", "矩阵", "向量组", "方程组", "特征值", "特征向量", "二次型", "伴随", "正交变换", "线性相关", "线性无关", "对角化", "合同", "规范形", "通解", "解的结构", "秩")),
    ("概率论与数理统计", ("概率", "期望", "方差", "协方差", "相关系数", "分布", "估计", "检验", "统计量", "样本", "正态", "取球", "中心矩", "原点矩", "混合矩", "二阶矩", "随机变量")),
    ("极限与连续", ("极限", "无穷小", "无穷大", "连续", "间断", "数列", "夹逼", "洛必达", "等价无穷小")),
    ("函数性质", ("有界", "奇偶", "周期", "函数性质", "映射")),
]

# 大观严选题：原编号 1.x -> 知识块（1.3 再按第三段细化）
DAXI_CHAPTER_BLOCK = {
    "1.1": "极限与连续",
    "1.2": "导数与微分",
    "1.3": "定积分",
    "1.4": "多元微分",
    "1.5": "重积分",
    "1.6": "微分方程",
    "1.7": "无穷级数",
}
DAXI_13_THIRD = {
    "1.3.1": "不定积分",
    "1.3.2": "定积分应用",
    "1.3.3": "反常积分",
    "1.3.4": "定积分",
}
# 章节内的题型例外：section -> (适用章, 知识块)
DAXI_SECTION_RULES = {
    "有界": ("1.1", "函数性质"),
    "奇偶": ("1.1", "函数性质"),
    "周期": ("1.1", "函数性质"),
    "综合": ("1.1", "函数性质"),
    "极最拐": ("1.2", "中值定理与导数应用"),
    "方程根 / 曲线交点 / 函数零点": ("1.2", "中值定理与导数应用"),
    "物理应用": ("1.2", "中值定理与导数应用"),
    "有理函数": ("1.3", "不定积分"),
    "含根式": ("1.3", "不定积分"),
    "两函数相乘": ("1.3", "不定积分"),
    "三角相关": ("1.3", "不定积分"),
    "分段函数": ("1.3", "不定积分"),
    "几何应用": ("1.3", "定积分应用"),
    "物理应用 (数一二)": ("1.3", "定积分应用"),
    "审敛": ("1.3", "反常积分"),
    "敛散性和参数的关系": ("1.3", "反常积分"),
    "反常积分特殊题型": ("1.3", "反常积分"),
}

# 竞赛教程题源：章节块 -> 知识块
COMPETITION_CHUNK_BLOCK = {
    "上册 第1章": "极限与连续",
    "下册 5.3": "向量与空间解析几何",
    "下册 6.3": "多元微分",
    "下册 7.3": "重积分",
    "下册 8.x": "无穷级数",
    "下册 第9章": "综合模拟",
}

# 大观高数分册：文件名序号 -> 知识块
FENCE_FILE_BLOCK = {
    "1": "极限与连续",
    "2": "导数与微分",
    "3": "不定积分",
    "4": "微分方程",
    "5": "多元微分",
    "6": "重积分",
    "7": "无穷级数",
}
FENCE_SECTION_RULES = {
    "特殊反常积分": "反常积分",
    "特殊定积分": "定积分",
    "极坐标": "重积分",
    "直角坐标": "重积分",
    "直接给出累次积分": "重积分",
    "其他题型": "重积分",
}


def keyword_block(text: str) -> str:
    for name, keys in BLOCK_KEYWORDS:
        if any(k in text for k in keys):
            return name
    return "未分类"


def parse_tag(line: str) -> OrderedDict:
    m = TAG.match(line)
    if not m:
        return OrderedDict()
    fields = OrderedDict()
    for part in m.group(1).split("｜"):
        if "=" in part:
            k, v = part.split("=", 1)
            fields[k.strip()] = v.strip()
    return fields


def render_tag(fields: OrderedDict) -> str:
    order = ["知识块", "类型", "来源", "难度"]
    keys = [k for k in order if k in fields] + [k for k in fields if k not in order]
    return "> 标签：" + " ｜ ".join(f"{k}={fields[k]}" for k in keys)


class Entry:
    __slots__ = ("header", "meta_idx", "tag_idx", "old_tag", "meta_text",
                 "section", "chunk", "body", "block", "type", "source", "level")

    def __init__(self, header: str) -> None:
        self.header = header
        self.meta_idx = []
        self.tag_idx = None
        self.old_tag = ""
        self.meta_text = ""
        self.section = ""
        self.chunk = ""
        self.body = []
        self.block = "未分类"
        self.type = "计算"
        self.source = ""
        self.level = ""


def scan(lines):
    """Collect every question entry with its surrounding headings."""
    entries = []
    section = ""
    chunk = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        m_sec = SECTION.match(line)
        if m_sec:
            section = m_sec.group(1).strip()
            if section.startswith("上册") or section.startswith("下册"):
                chunk = section
            i += 1
            continue
        if ENTRY.match(line):
            e = Entry(line)
            e.section = section
            e.chunk = chunk
            j = i + 1
            while j < len(lines) and lines[j].startswith(">"):
                e.meta_idx.append(j)
                if TAG.match(lines[j]):
                    e.tag_idx = j
                    e.old_tag = lines[j]
                j += 1
            e.meta_text = " ".join(lines[k].lstrip("> ").strip() for k in e.meta_idx)
            k = j
            while k < len(lines) and not (ENTRY.match(lines[k]) or SECTION.match(lines[k])):
                e.body.append(lines[k])
                k += 1
            entries.append(e)
            i = k
            continue
        i += 1
    return entries


def chapter_of(meta: str):
    m = ORIG_NUM.search(meta)
    if not m:
        return "", ""
    parts = m.group(1).split(".")
    if len(parts) < 2:
        return "", ""
    return ".".join(parts[:2]), ".".join(parts[:3])


def guess_type(e: Entry) -> str:
    text = e.meta_text + "\n" + "\n".join(e.body[:40])
    letters = {m.group(0)[0] for m in re.finditer(r"[A-D]\s*[.．、]", text)}
    prompt = re.search(r"下列|[（(]\s*[)）]|【\s*】", text)
    if len(letters) >= 3 or (len(letters) >= 2 and prompt):
        return "选择"
    if "证明" in text:
        return "证明"
    return "计算"


def tag_daxi(entries) -> None:
    votes = {}
    for e in entries:
        ch, _ = chapter_of(e.meta_text)
        if ch:
            votes.setdefault(e.section, Counter())[ch] += 1
    section_best = {s: c.most_common(1)[0][0] for s, c in votes.items() if c}
    chapters = []
    for e in entries:
        ch, _ = chapter_of(e.meta_text)
        chapters.append(ch or section_best.get(e.section, ""))
    last = ""
    for i, ch in enumerate(chapters):
        if ch:
            last = ch
        elif last:
            chapters[i] = last
    nxt = ""
    for i in range(len(chapters) - 1, -1, -1):
        if chapters[i]:
            nxt = chapters[i]
        elif nxt:
            chapters[i] = nxt
    for e, ch in zip(entries, chapters):
        _, third = chapter_of(e.meta_text)
        rule = DAXI_SECTION_RULES.get(e.section)
        block = rule[1] if (rule and rule[0] == ch) else ""
        if not block and ch == "1.3" and third in DAXI_13_THIRD:
            block = DAXI_13_THIRD[third]
        if not block:
            block = DAXI_CHAPTER_BLOCK.get(ch, "")
        if not block:
            block = keyword_block(e.section)
        e.block = block or "未分类"
        e.type = guess_type(e)
        e.source = "考研真题（严选题）"
        e.level = "考研真题"


def tag_maki(entries) -> None:
    for e in entries:
        title = e.meta_text.split("｜")[-1]
        title = re.sub(r"^(19|20)\d{2}.*?・\s*[^(]*", "", title)
        kaodian = ""
        for i, line in enumerate(e.body):
            if line.strip() == "考点" and i + 1 < len(e.body):
                kaodian = " ".join(e.body[i + 1:i + 4])
                break
        # 标题优先：考点段落只是补充，避免被段落里的通用词带偏。
        e.block = keyword_block(title)
        if e.block == "未分类":
            e.block = keyword_block(f"{title} {e.meta_text} {kaodian}")
        e.type = guess_type(e)
        e.source = "考研真题（分类精解）"
        stars = len(STARS.findall(e.meta_text + " " + kaodian))
        e.level = f"{min(stars, 5)}星" if stars else ""


def tag_competition(entries) -> None:
    for e in entries:
        key = next((k for k in COMPETITION_CHUNK_BLOCK if e.chunk.startswith(k)), None)
        e.block = COMPETITION_CHUNK_BLOCK[key] if key else "未分类"
        e.type = "页码条目"
        e.source = "竞赛真题/训练"
        e.level = "竞赛"


def tag_fence(entries, doc: str) -> None:
    m = re.match(r"^(\d+)\.", doc)
    base = FENCE_FILE_BLOCK.get(m.group(1), "未分类") if m else "未分类"
    for e in entries:
        e.block = FENCE_SECTION_RULES.get(e.section, base)
        e.type = "专题题库"
        e.source = "题目汇编"
        e.level = "专题"


def profile_for(path: Path) -> str:
    name = path.name
    if name.startswith("大观严选题数"):
        return "daxi"
    if name.startswith("Maki"):
        return "maki"
    if "竞赛教程" in name:
        return "competition"
    return "fence"


def retag_file(path: Path, backup_root: Path) -> Counter:
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    entries = scan(lines)
    if not entries:
        return Counter()
    profile = profile_for(path)
    if profile == "daxi":
        tag_daxi(entries)
    elif profile == "maki":
        tag_maki(entries)
    elif profile == "competition":
        tag_competition(entries)
    else:
        tag_fence(entries, path.name)
    inserts = {}
    appends = {}
    histogram = Counter()
    for e in entries:
        fields = parse_tag(e.old_tag)
        fields["知识块"] = e.block
        fields["类型"] = e.type
        fields["来源"] = e.source
        if e.level:
            fields["难度"] = e.level
        else:
            fields.pop("难度", None)
        text_tag = render_tag(fields)
        histogram[e.block] += 1
        if e.tag_idx is not None:
            inserts[e.tag_idx] = text_tag
        else:
            appends.setdefault(e.meta_idx[-1], []).append(text_tag)
    out = []
    for i, line in enumerate(lines):
        out.append(inserts.get(i, line))
        if i in appends:
            out.extend(appends[i])
    backup_root.mkdir(parents=True, exist_ok=True)
    (backup_root / path.name).write_text(text, encoding="utf-8")
    path.write_text("\n".join(out), encoding="utf-8")
    return histogram


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, help="题库根目录（含各集合子目录）")
    parser.add_argument("--backup", required=True, help="原始文件备份目录")
    args = parser.parse_args()
    root = Path(args.root)
    backup_root = Path(args.backup)
    grand = Counter()
    for note in sorted(root.rglob("*.md")):
        if note.name.startswith("_"):
            continue
        hist = retag_file(note, backup_root)
        if not hist:
            continue
        grand.update(hist)
        print(f"\n== {note.relative_to(root)}  ({sum(hist.values())} 条)")
        for block, count in hist.most_common():
            print(f"   {count:5}  {block}")
    print("\n== 全库知识块分布 ==")
    for block, count in grand.most_common():
        print(f"   {count:5}  {block}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
