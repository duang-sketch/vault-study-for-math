#!/usr/bin/env python3
"""CI 自检：用合成数据验证 pdfkit / from_web / export_mongo 真的能跑。

不依赖网络、不依赖 poppler 与 MinerU，可在 GitHub Actions 上直接执行。
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "math-question-bank" / "scripts"
failed = []


def run(label, *args, expect=0):
    proc = subprocess.run([sys.executable, "-B", *map(str, args)], capture_output=True)
    out = (proc.stdout + proc.stderr).decode("utf-8", "replace")
    if proc.returncode != expect:
        failed.append(label)
        print(f"FAIL {label} (exit={proc.returncode}, 期望 {expect})")
        print(out[:800])
    else:
        print(f"ok   {label}")
    return out


with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    raw = tmp / "raw.md"
    raw.write_text(
        "<!-- page 4 of 6 -->\n开头\n\n1\n"
        "<!-- page 5 of 6 -->\n中间 $a^2+b^2$\n\n2\n"
        "<!-- page 6 of 6 -->\n末页\n\n3\n", encoding="utf-8")

    out = run("pdfkit markers", SCRIPTS / "pdfkit.py", "--json", "markers", raw)
    if '"count":3' not in out.replace(" ", ""):
        failed.append("markers 页数")
    run("pdfkit pages", SCRIPTS / "pdfkit.py", "pages", raw, "--pages", "5")
    run("pdfkit slice", SCRIPTS / "pdfkit.py", "slice", raw, "--pages", "5-6", "--out", tmp / "part.md")
    out = run("pdfkit offset", SCRIPTS / "pdfkit.py", "--json", "offset", raw)
    if '"best_offset":3' not in out.replace(" ", ""):
        failed.append("offset 推断")

    items = tmp / "items.json"
    items.write_text(json.dumps([
        {"statement": "求 $\\lim_{x\\to0}\\sin x/x$。", "source": "公开题源 A",
         "url": "https://example.org/a/1", "license": "CC BY 4.0"},
        {"statement": "证明：$\\sqrt{2}$ 不是有理数。", "source": "公开题源 B",
         "license": "unknown"},
    ], ensure_ascii=False), encoding="utf-8")
    out = run("from_web", SCRIPTS / "collect" / "from_web.py", "--items", items,
              "--out-dir", tmp / "web", "--title", "公开题源")
    if "2 题" not in out:
        failed.append("from_web 收录数")
    run("from_web strict 拒绝", SCRIPTS / "collect" / "from_web.py", "--items", items,
        "--out-dir", tmp / "web2", "--title", "公开题源", "--strict", expect=1)

    run("export_mongo", SCRIPTS / "export_mongo.py",
        "--root", REPO / "math-question-bank" / "assets" / "example",
        "--out", tmp / "q.ndjson", "--indexes", tmp / "idx.json")
    docs = [json.loads(line) for line in (tmp / "q.ndjson").read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(docs) != 13:
        failed.append(f"导出条数={len(docs)}（期望 13）")

print()
if failed:
    print("自检失败：" + ", ".join(failed))
    sys.exit(1)
print("自检全部通过")
