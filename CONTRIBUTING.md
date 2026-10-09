# 贡献约定

## 提交信息：Conventional Commits

格式：`<type>(<scope>): <summary>`，summary 用祈使句、说清"做了什么"。

| type | 用在 |
|---|---|
| `feat` | 新增能力（新收集器、新导出器、新子命令） |
| `fix` | 修 bug（解析错、路径错、页码错） |
| `docs` | 只改文档 / 规范 / 示例 |
| `refactor` | 不改行为的重组（移动文件、抽函数） |
| `chore` | 杂务（依赖、忽略文件） |
| `ci` | 工作流改动 |

示例：

```
feat(collect): 新增 from_web.py，支持把 web search 结果规范化为集合
fix(pdfkit): offset 投票改为按页取最后一个页脚数字
refactor(scripts): 按职责拆分为 collect/ pdfkit tag report export
docs(references): 补充 web 题源署名与许可边界
```

## scripts/ 的单一职责原则

- 一个脚本只干一件事，名字说明它干什么；跨脚本的公共逻辑抽到 `pdfkit.py` 或独立 CLI。
- **不要**把某本书专用的章节表、页段清单写进 `scripts/`——那属于 `assets/worked-example-*/`。
- 新增脚本必须：`--help` 可跑、不依赖网络、路径靠参数或环境变量（`PDFTOTEXT` / `MINERU_HOME` /
  `MINERU_EXE` / `CJX_DIR`），缺失时明确报错。

## 内容边界（重要）

本仓库只收工具、规范与自造示例。**不要**提交任何教材、辅导书、真题集的原文转录。
公开题源要记录 `source` / `url` / `license`（见 `references/source-collection.md`）。

## 改动之后

1. 跑一遍冒烟：`python scripts/<改了谁>.py --help`
2. 跑官方校验：`python <skill-creator>/scripts/quick_validate.py math-question-bank`
3. 用 conventional commit 提交
