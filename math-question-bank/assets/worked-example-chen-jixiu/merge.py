# -*- coding: utf-8 -*-
"""Merge part files produced by per-batch restructuring into the final question bank."""
import sys
import os
import io

# 原始 MinerU 分片目录：环境变量 CJX_DIR 可覆盖（默认本机路径）
CJX = os.environ.get("CJX_DIR", "_raw")
PARTS = [
    os.path.join(CJX, "part_1_p1-60.md"),
    os.path.join(CJX, "part_2_p61-120.md"),
    os.path.join(CJX, "part_3_p121-180.md"),
    os.path.join(CJX, "part_4_p181-246.md"),
]

HEADER = """# 陈纪修《数学分析（第3版）习题全解指南·上册》题源库

> 题面与解答均逐字抄录自 MinerU 转换结果，未作改动；存疑处标 [疑]。
> 页码：书 P.xxx = 原书印刷页；PDF p.yyy = 扫描页。偏移关系：{offset}
> 转换方式：MinerU `parse --tier standard`，PDF 共 246 页，分 4 批转换后按页序拼接。

"""


def main():
    out_path = os.environ.get("CJX_OUT", os.path.join(CJX, "陈纪修习题全解-上册.md"))
    offset = sys.argv[1] if len(sys.argv) > 1 else "印刷页 = PDF 页 - 6"
    chunks = [HEADER.format(offset=offset)]
    for p in PARTS:
        if not os.path.exists(p):
            sys.stderr.write("MISSING: %s\n" % p)
            continue
        txt = io.open(p, encoding="utf-8").read().strip("\n")
        chunks.append(txt)
        chunks.append("\n")
    with io.open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(chunks))
    print("wrote %s (%d bytes)" % (out_path, os.path.getsize(out_path)))


if __name__ == "__main__":
    main()
