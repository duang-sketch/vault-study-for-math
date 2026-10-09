# build_package.example.ps1 —— 示例：把散落目录增量同步成一个交付包（MANIFEST sha256 + zip）
# 用途：把分散在各处的数学题源 / 笔记 / 试卷 / LaTeX 转换件 / 工具脚本
#      增量同步到一个交付包目录，重建 MANIFEST.json，并重新打包 zip。
# 用法（示例）：
#   pwsh assets/worked-example-delivery/build_package.example.ps1 -OpenCodeRoot "D:\src" -NewProjectRoot "D:\proj" `
#        -KbRoot "D:\kb" -MineruOut "D:\mineru-out" -Pkg ".\dist"
#   也可先用环境变量 MPK_OPENCODE_ROOT / MPK_NEWPROJECT_ROOT / MPK_KB_ROOT / MPK_MINERU_OUT 给出
#
# 说明：本脚本只做「新增 / 覆盖」，不删除目标目录里的任何文件（重建 zip 时除外）。
[CmdletBinding()]
param(
    [string]$Pkg = $(if ($env:MPK_PKG) { $env:MPK_PKG } else { './dist' }),
    [string]$Zip = $(if ($env:MPK_ZIP) { $env:MPK_ZIP } else { './dist.zip' }),
    [string]$OpenCodeRoot   = $env:MPK_OPENCODE_ROOT,
    [string]$NewProjectRoot = $env:MPK_NEWPROJECT_ROOT,
    [string]$KbRoot         = $env:MPK_KB_ROOT,
    [string]$MineruOut      = $env:MPK_MINERU_OUT,
    [switch]$NoZip
)
$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$scriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$exportRoot = Split-Path -Parent $scriptDir
# 根目录集中在参数区：用 -OpenCodeRoot / -NewProjectRoot / -KbRoot / -MineruOut 覆盖，
# 或用环境变量 MPK_OPENCODE_ROOT / MPK_NEWPROJECT_ROOT / MPK_KB_ROOT / MPK_MINERU_OUT 覆盖。
$missing = @()
if (-not $OpenCodeRoot)   { $missing += 'OpenCodeRoot'   }
if (-not $NewProjectRoot) { $missing += 'NewProjectRoot' }
if (-not $KbRoot)         { $missing += 'KbRoot'         }
if (-not $MineruOut)      { $missing += 'MineruOut'      }
if ($missing.Count) { throw ("缺少来源目录参数：{0}（用参数或 MPK_* 环境变量给出）" -f ($missing -join ', ')) }
$openCode   = $OpenCodeRoot
$newProject = $NewProjectRoot
$kbRoot     = $KbRoot
$mineruOut  = $MineruOut
$copied  = 0
$skipped = New-Object System.Collections.Generic.List[string]
function Copy-One {
    param([string]$Src, [string]$DstDir)
    if (-not (Test-Path -LiteralPath $Src)) { $script:skipped.Add($Src); return }
    if (-not (Test-Path -LiteralPath $DstDir)) { $null = New-Item -ItemType Directory -Path $DstDir -Force }
    Copy-Item -LiteralPath $Src -Destination $DstDir -Force
    $script:copied++
}
function Copy-Glob {
    param([string]$Dir, [string]$Filter, [string]$DstDir, [switch]$Recurse)
    if (-not (Test-Path -LiteralPath $Dir)) { $script:skipped.Add($Dir); return }
    $items = Get-ChildItem -LiteralPath $Dir -Filter $Filter -File -Recurse:$Recurse -ErrorAction SilentlyContinue
    foreach ($i in $items) {
        $rel = $i.FullName.Substring($Dir.Length).TrimStart('\')
        $target = Join-Path $DstDir (Split-Path -Parent $rel)
        Copy-One -Src $i.FullName -DstDir $target
    }
}
Write-Host "== 同步到 $Pkg ==" -ForegroundColor Cyan
if (-not (Test-Path -LiteralPath $Pkg)) { $null = New-Item -ItemType Directory -Path $Pkg -Force }
# 1) 题库（6 个集合，每个含 .md + source-manifest.json）
Copy-Glob -Dir (Join-Path $openCode '数据\题库') -Filter '*' -DstDir (Join-Path $Pkg '题库') -Recurse
# 2) 笔记（两个 vault 的 高等数学 目录合流 + 草稿本）
Copy-Glob -Dir (Join-Path $openCode 'obsidian笔记\高等数学') -Filter '*.md' -DstDir (Join-Path $Pkg '笔记\高等数学')
Copy-Glob -Dir (Join-Path $kbRoot   'obsidian笔记\高等数学') -Filter '*.md' -DstDir (Join-Path $Pkg '笔记\高等数学')
Copy-Glob -Dir (Join-Path $openCode 'obsidian笔记\草稿本')   -Filter '*.md' -DstDir (Join-Path $Pkg '笔记\草稿本')
# 2b) 题库标签总览（生成件，放 vault 与包内笔记目录）
$overview = Join-Path $exportRoot '题库标签总览.md'
if (Test-Path -LiteralPath $overview) {
    Copy-One -Src $overview -DstDir (Join-Path $Pkg '笔记\高等数学')
    Copy-One -Src $overview -DstDir (Join-Path $openCode 'obsidian笔记\高等数学')
    Copy-One -Src $overview -DstDir (Join-Path $kbRoot   'obsidian笔记\高等数学')
}
# 3) 试卷（自出卷 + 考研真题 + 浙大期末模拟）
$paper = Join-Path $Pkg '试卷'
foreach ($f in @('卷二.md','卷三.md','高数上期末模拟卷.md')) {
    Copy-One -Src (Join-Path $newProject "高等数学\$f") -DstDir $paper
}
Copy-One -Src (Join-Path $newProject '2025年考研数学一真题.md') -DstDir $paper
Copy-Glob -Dir (Join-Path $newProject '高等数学\浙大-微积分甲上') -Filter '*' -DstDir (Join-Path $paper '浙大-微积分甲上') -Recurse
# 4) LaTeX 转换（MinerU 输出）
Copy-Glob -Dir $mineruOut -Filter 'js_*.md'   -DstDir (Join-Path $Pkg 'LaTeX转换')
Copy-Glob -Dir $mineruOut -Filter 'ch1_*.md'  -DstDir (Join-Path $Pkg 'LaTeX转换')
Copy-Glob -Dir $mineruOut -Filter 'shu1_*.md' -DstDir (Join-Path $Pkg 'LaTeX转换')
Copy-Glob -Dir $mineruOut -Filter '数一第一章_p13-32.md' -DstDir (Join-Path $Pkg 'LaTeX转换')
# 5) 工具脚本（含本脚本自身，方便对方重跑）
$toolDir = Join-Path $Pkg '工具'
Copy-One -Src (Join-Path $newProject '高等数学\_tools\pdf_to_question_md.py') -DstDir $toolDir
Copy-Glob -Dir (Join-Path $exportRoot 'tools') -Filter '*.py' -DstDir $toolDir
Copy-One -Src $MyInvocation.MyCommand.Path -DstDir $toolDir
# 6) README（源在 导出包\README.md）
Copy-One -Src (Join-Path $exportRoot 'README.md') -DstDir $Pkg
Write-Host ("同步文件数：{0}" -f $copied) -ForegroundColor Green
if ($skipped.Count -gt 0) {
    Write-Host "以下来源不存在（已跳过）：" -ForegroundColor Yellow
    $skipped | Sort-Object -Unique | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
}
# 7) 重建 MANIFEST.json（不含 MANIFEST.json 自身）
$files = Get-ChildItem -LiteralPath $Pkg -Recurse -File |
    Where-Object { $_.Name -ne 'MANIFEST.json' } | Sort-Object FullName
$rows = foreach ($f in $files) {
    [pscustomobject]@{
        relative = $f.FullName.Substring($Pkg.Length + 1).Replace('\','/')
        bytes    = $f.Length
        sha256   = (Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash
    }
}
$manifestPath = Join-Path $Pkg 'MANIFEST.json'
$rows | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
Write-Host ("MANIFEST.json：{0} 个文件" -f $rows.Count) -ForegroundColor Green
# 8) 同步 README / MANIFEST 回源目录
Copy-Item -LiteralPath (Join-Path $Pkg 'README.md') -Destination $exportRoot -Force
Copy-Item -LiteralPath $manifestPath -Destination $exportRoot -Force
# 9) 重新打包 zip
if (-not $NoZip) {
    if (Test-Path -LiteralPath $Zip) { Remove-Item -LiteralPath $Zip -Force }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::CreateFromDirectory(
        $Pkg, $Zip, [System.IO.Compression.CompressionLevel]::Optimal, $false)
    $z = Get-Item -LiteralPath $Zip
    Write-Host ("压缩包：{0}  {1:N2} MB" -f $z.FullName, ($z.Length / 1MB)) -ForegroundColor Green
}
$sum = ($files | Measure-Object -Property Length -Sum).Sum
Write-Host ("资料包：{0} 个文件 / {1:N2} MB" -f $files.Count, ($sum / 1MB)) -ForegroundColor Green
