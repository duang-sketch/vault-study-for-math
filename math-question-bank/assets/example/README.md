# assets/example/ —— 自造 demo 数据集

这里的 13 道题**全部由本项目自造**，不含任何教材、辅导书或真题集的内容，仅用于演示
`numbered-markdown/v1` 的写法与 `source-manifest.json` 的结构。

真实的题库集合应该：

- 每道题都带 `<!-- source-page: N -->`，指向题面在原书 PDF 里的页码；
- 公式走样时按该页码回原页核对；
- 集合目录里同时有 `.md` 与 `source-manifest.json` 才会被下游工具识别。
