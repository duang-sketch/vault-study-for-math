# Roadmap

按"先能跑通，再可复用，再做应用"的顺序推进。

## P0 —— 已完成（v2）

- [x] `scripts/` 按职责拆分：`collect/`（收集）、`pdfkit.py`（通用解析）、标签与统计、`export_mongo.py`（交付），
      书特定管线移出到 `assets/worked-example-chen-jixiu/`
- [x] 收集策略改为 **web 优先**（`scripts/collect/from_web.py` + `references/source-collection.md`）
- [x] 通用文档解析抽成独立 CLI：`scripts/pdfkit.py`（`markers` / `pages` / `slice` / `offset`，支持 `--json`）
- [x] 一键安装：`install.ps1` / `install.sh`
- [x] 提交规范：Conventional Commits（见 `CONTRIBUTING.md`）
- [x] MongoDB 交付路径：`scripts/export_mongo.py` + `references/mongo-schema.md`

## P1 —— 让组件真正"可当 tool 调用"

- [ ] 所有 CLI 统一 `--json` 输出与退出码约定（`0` 成功 / `2` 参数错 / `3` 缺少依赖 / `4` 数据不合法）
- [ ] `pdfkit` 独立成仓库并发布（PyPI 或单文件分发），其他 skill 用 `pipx install` / 直接引用即可
- [ ] 收集器插件化：`collect/adapters/<source>.py`，新题源零改核心代码接入
- [ ] 跨卷重复题聚类（数一/二/三同题），用于去重与"同题不同年"标注
- [ ] OCR 通道：无文本层扫描件直接进净通道；难度初判（题型 + 步数）

## P2 —— 前后端应用

- [ ] 后端：FastAPI + MongoDB，读 `export_mongo.py` 产出的 NDJSON 建库；提供 `/questions`（检索、分页、
      按知识块/类型/难度/来源过滤）、`/collections`、`/configs`
- [ ] 数据模型：题目详情按 `references/mongo-schema.md`；规则化配置（知识块字典、标签枚举、来源白名单）
      存 `configs` 集合，前端可改
- [ ] 前端：题目列表 + 详情（题面/解答/出处页或 URL）、全文与结构化检索、标签与配置管理页
- [ ] 检索：MongoDB Atlas Search（中文分词）或 `text` 索引 + n-gram；命中后回链 `source_page` / `source_url`

## P3 —— LangGraph 编排

前提是 P1 的"统一 --json / 统一退出码"完成，每个脚本都能当 tool 调。

- [ ] 把 `collect → normalize → tag → validate → export` 串成 LangGraph 流水线，节点失败可重试/回滚
- [ ] 人工审核节点：`[疑]` 条目、许可未确认条目必须人工确认后才入库
- [ ] 多 agent 分工：检索 agent（web search）、整理 agent（规范化）、审核 agent（逐条对源）、发布 agent（入库）

## 持续

- [ ] 更多公开题源适配器（竞赛官网、开放课程、作者授权讲义）
- [ ] 题库统计报告的可视化（题量/知识块分布/难度分布）
