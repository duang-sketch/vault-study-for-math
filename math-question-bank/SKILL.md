---
name: math-question-bank
description: Build or maintain a searchable, tagged, page-traceable math question collection (numbered-markdown/v1) from public sources found via web search, or from local textbook/workbook/exam PDFs. Use for 题目收集与规范化、题干与解答的逐字转录、题目标签（知识块/类型/难度）、按页码或 URL 定位题目来源、导出给数据库或知识库。Not for solving or explaining individual math problems.
metadata:
  short-description: 收集/规范化/打标签数学题库
---

# Math Question Bank

把散落的数学题（公开题源或本地 PDF）变成一份**可检索、可打标签、能溯源到出处**的题库。
产物是纯 markdown（`numbered-markdown/v1`）加 manifest，不依赖商业工具。
核心原则：**宁可粒度粗，也不编内容；每条都要能回到出处核对。**

## 职责分区（scripts/ 只放单一职责的小工具）

| 职责 | 入口 | 说明 |
|---|---|---|
| 通用文档解析 | `scripts/pdfkit.py` | 页面标记、按页取文、切片、印刷页偏移检测。**别的 skill/agent 可直接复用** |
| 收集（优先） | `scripts/collect/from_web.py` | 把 web search 找到的题目规范化为集合 |
| 收集（本地 PDF） | `scripts/collect/from_pdf_text.py`、`from_pdf_topics.py`、`from_mineru_pages.py` | 文本层 / 分块专题 / MinerU 页段三条本地通道 |
| 结构化 | `scripts/tag_questions.py`、`build_tag_overview.py`、`build_chapter_index.py` | 打标签、统计、章节题源总表 |
| 交付 | `scripts/export_mongo.py` | 导出 NDJSON 供 MongoDB / 后续前端使用 |

书特定的整段管线（含章节表）放在 `assets/worked-example-*/`，不进 `scripts/`。

## 收集策略：先 Web，后本地

1. **优先用 Coding Agent 自带的 web search** 去公开题源找题（公开试题、竞赛官网、开放许可题集、作者授权讲义）。
2. 记录**出处 URL、来源名、检索日期、许可**；许可不明时只记录出处与页码，**不要**复制原文。
3. 用 `scripts/collect/from_web.py` 规范化成集合，条目抓 `<!-- source: URL -->` 溯源。
4. 只有本地自有/已授权材料才走 PDF 通道；受版权保护的教辅**不得**批量转录后分发。
5. 细则见 [references/source-collection.md](references/source-collection.md)。

## 本地 PDF 通道选择

| 你要的 | 通道 | 入口 |
|---|---|---|
| 只想知道"哪一页有哪些题" | 文本层（快，公式走样） | `scripts/collect/from_pdf_text.py` |
| 题面要直接抄进卷子 | MinerU（净，干净 LaTeX） | `scripts/pdfkit.py` + `scripts/collect/from_mineru_pages.py` |
| 分块专题 PDF、一页多题 | 页级 / 专题级 | `scripts/collect/from_pdf_topics.py` |

选择判据与粒度差异见 [references/two-pipelines.md](references/two-pipelines.md)。

## 环境依赖

- 文本层通道：`pdftotext`（poppler）在 PATH 中，或设 `PDFTOTEXT`
- 净通道：`MINERU_HOME` / `MINERU_EXE`，工作目录 `CJX_DIR`（默认 `./_raw`）
- 路径缺失时脚本会明确报错。不要改成别的路径硬跑，也不要静默跳过。

## 硬约束

1. **逐字抄录**：题面与解答必须与来源一致，不改错、不润色、不补写；判断可疑就在**紧后**标 `[疑]`
   并写一句极简说明，绝不"顺手改错"。
2. **每条必带溯源**：本地来源写 `<!-- source-page: N -->`（1-based PDF 页），网络来源写
   `<!-- source: URL -->`。没有出处的条目无法复核，等于没有价值。
3. **加工只许删版式噪声**（页眉、页脚页码、装饰行），并能逐行回查原始输出。
4. **打标签用结构信号**：原书编号的章号、题型标题、章节块、考点标题。**不要**扫正文关键词——文本层里
   "极限/连续/泰勒"到处都是，实测会造成 30–40% 的题被误归到"极限与连续"。
5. **写前备份**：改动已有集合先备份（`scripts/tag_questions.py --backup`）。
6. **导入知识库两段式**：先预览拿 `plan_sha256`，再用 `--write --expect-plan-sha256 <sha>`；
   哈希不一致或来源变了必须停下，不要自动重试。

## 常用流程

```bash
# 1) 收集：把 web search 结果规范化（items.json 由 agent 检索后生成）
python scripts/collect/from_web.py --items items.json --out-dir 题库/公开题源 --title "公开题源"

# 2) 本地 PDF：文本层通道
python scripts/collect/from_pdf_text.py --pdf book.pdf --out-dir 题库/我的集合 --title "习题册名"

# 3) 结构化
python scripts/tag_questions.py --root 题库 --backup 备份
python scripts/build_tag_overview.py --root 题库 --out 题库标签总览.md

# 4) 交付给数据库 / 前端
python scripts/export_mongo.py --root 题库 --out 题库.ndjson --indexes 索引建议.json
```

```bash
# 净通道：MinerU 原始输出 → 按页取文 / 偏移核验 / 切片
mineru parse book.pdf -p 44-66 --tier standard -o raw.md
export CJX_DIR=$PWD/_raw
python scripts/pdfkit.py markers raw.md            # 有哪些页标记
python scripts/pdfkit.py pages raw.md --pages 18,19 # 抽查原页
python scripts/pdfkit.py offset raw.md             # 印刷页 = PDF 页 − ?
python scripts/pdfkit.py slice raw.md --pages 18-24 --out part.md
```

## 参考（按需读，不要一次全载）

- [references/numbered-markdown-v1.md](references/numbered-markdown-v1.md) —— 集合格式契约、标签字段、manifest 结构。**写集合前必读。**
- [references/source-collection.md](references/source-collection.md) —— web 优先策略、署名与版权边界。**收集前必读。**
- [references/page-traceability.md](references/page-traceability.md) —— 印刷页/PDF 页偏移怎么实测、`[疑]` 规则。**本地通道必读。**
- [references/two-pipelines.md](references/two-pipelines.md) —— 通道选择与粒度（逐题 / 页级 / 专题级）。
- [references/mongo-schema.md](references/mongo-schema.md) —— 集合 → MongoDB 文档与索引设计（做前端/服务时读）。
- `assets/example/` —— 13 道自造 demo 集合（格式样例）。
- `assets/worked-example-chen-jixiu/` —— 一段真实书特定管线（含章节表），看"净通道"怎么落地。

## 完成标准

- 集合能按 `### <纯数字>` 正确切题，且每条都带 `source-page` 或 `source`
- 标签行齐全（知识块 / 类型 / 来源 / 难度；难度可以是来源级别而非逐题实测）
- 统计文件（题量、知识块分布）与集合实际内容一致
- 交付时主动说明已知限制：哪些公式走样、哪些条目不是逐题、难度口径是什么
