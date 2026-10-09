# math-question-bank（Codex skill）

把散落的数学题（公开题源或本地 PDF）变成**可检索、可打标签、能溯源到出处**的题库。

本仓库是一个 Codex skill 包：技能本体在 [`math-question-bank/`](math-question-bank/)，
入口是 [`SKILL.md`](math-question-bank/SKILL.md)。

## 一键安装

```powershell
# Windows
pwsh -File .\install.ps1
```

```bash
# macOS / Linux
bash ./install.sh
```

脚本会把 `math-question-bank/` 复制到 `$CODEX_HOME/skills/`（默认 `~/.codex/skills`），
检查 Python，并在存在官方校验器时跑一次 `quick_validate`。

也可以手动装：

```bash
python <skill-installer>/scripts/install-skill-from-github.py \
  --repo duang-sketch/vault-study-for-math --path math-question-bank
```

## 它做什么

| 职责 | 入口 |
|---|---|
| 收集（**优先**）：把 web search 找到的公开题规范化为集合 | `scripts/collect/from_web.py` |
| 收集：本地 PDF 的三条通道（文本层 / 分块专题 / MinerU 页段） | `scripts/collect/from_pdf_text.py` 等 |
| 通用文档解析（可被其他 skill 复用） | `scripts/pdfkit.py` |
| 结构化：标签、标签总览、章节题源总表 | `scripts/tag_questions.py` 等 |
| 交付：导出 NDJSON 给 MongoDB / 前端 | `scripts/export_mongo.py` |

规范与边界写在 [`math-question-bank/references/`](math-question-bank/references/)；
自造 demo 在 `assets/example/`。

## 它不包含什么

任何受版权保护的原书内容。仓库里只有工具、规范与自造示例；使用者需自行确保其处理与分发的资料来源合法。

## 仓库约定

- 提交信息遵循 [Conventional Commits](https://www.conventionalcommits.org/)（`feat:` / `fix:` / `docs:` / `refactor:` / `chore:` / `ci:`），详见 [CONTRIBUTING.md](CONTRIBUTING.md)
- `scripts/` 只放单一职责的小工具；书特定的整段管线放 `assets/worked-example-*/`
- 开发计划见 [ROADMAP.md](ROADMAP.md)

## License

MIT，见 [LICENSE](LICENSE)。
