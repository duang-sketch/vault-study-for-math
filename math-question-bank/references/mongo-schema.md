# MongoDB 数据结构与索引（给 P2 的前后端用）

`scripts/export_mongo.py` 把集合导出成 NDJSON，一题一条文档，可直接 `mongoimport`。

## 文档字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `collection` | string | 集合名（题库子目录名） |
| `number` | string | 集合内题号（`###` 后面的纯数字） |
| `section` | string \| null | `##` 章节 / 考点 |
| `knowledge_block` | string \| null | 知识块（来自标签行） |
| `type` | string \| null | 选择 / 计算 / 证明 / 页码条目 / 专题题库 |
| `source` | string \| null | 来源（考研真题 / 竞赛 / 自造 demo …） |
| `difficulty` | string \| null | 难度（星级或来源级别） |
| `tags` | object | 全部标签键值，保留扩展 |
| `source_page` | string \| null | 本地来源的 PDF 页码（可能是 `12-13`） |
| `source_url` | string \| null | 网络来源 URL |
| `statement_md` | string | 题面 markdown（含 LaTeX） |
| `solution_md` | string \| null | 解答（若集合里有 `**解答**` 段） |
| `sha256` | string | 条目原始文本哈希，用于去重与变更检测 |
| `meta_raw` | string \| null | `>` 元信息原文，便于回溯 |
| `imported_at` | string | 导出时间（UTC ISO8601） |

## 示例文档

```json
{
  "collection": "公开题源",
  "number": "7",
  "section": "极限与连续",
  "knowledge_block": "极限与连续",
  "type": "计算",
  "source": "2023 年 XX 竞赛初赛",
  "difficulty": "竞赛",
  "tags": {"知识块": "极限与连续", "类型": "计算", "难度": "竞赛"},
  "source_page": null,
  "source_url": "https://example.org/p/7",
  "statement_md": "求 $\\lim_{x\\to 0}\\dfrac{\\sin x-x}{x^{3}}$。",
  "solution_md": null,
  "sha256": "…",
  "meta_raw": "来源=2023 年 XX 竞赛初赛 ｜ URL=https://example.org/p/7",
  "imported_at": "2026-10-09T00:00:00+00:00"
}
```

## 索引（`--indexes` 写出的建议）

| 索引 | 用途 |
|---|---|
| `{knowledge_block: 1, type: 1}` | 按知识块 + 题型筛题（出卷最主要入口） |
| `{collection: 1, number: 1}`（unique） | 幂等导入 / 更新单题 |
| `{source_page: 1}` | 从页码反查题目 |
| `{tags: 1}` | 任意扩展标签过滤 |
| `{statement_md: "text", solution_md: "text"}` | 全文检索（中文建议用 Atlas Search，Mongo 默认分词对中文不友好） |

## 导入与自检

```bash
python scripts/export_mongo.py --root 题库 --out 题库.ndjson --indexes indexes.json
mongoimport --uri "$MONGO_URI" --collection questions --type json --file 题库.ndjson
```

- 重复导入同一集合：用 `collection + number` 做 upsert，或先按 `sha256` 去重
- 题目详情页直接渲染 `statement_md` / `solution_md`；出处用 `source_page`（本地）或 `source_url`（网络）
- 规则化配置（知识块字典、标签枚举、来源白名单）建议单独存 `configs` 集合，供前端配置页读写
