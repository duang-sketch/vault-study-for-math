# 一键安装 math-question-bank skill（Windows / PowerShell）
#
#   pwsh -File .\install.ps1                 # 装到 $CODEX_HOME/skills（默认 ~/.codex/skills）
#   pwsh -File .\install.ps1 -Force          # 已存在时覆盖
#   pwsh -File .\install.ps1 -Dest D:\skills # 指定目标
[CmdletBinding()]
param(
    [string]$Dest,
    [switch]$Force
)
$ErrorActionPreference = 'Stop'

if (-not $Dest) {
    $codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' }
    $Dest = Join-Path $codexHome 'skills'
}

$skillName = 'math-question-bank'
$src = Join-Path $PSScriptRoot $skillName
if (-not (Test-Path -LiteralPath $src)) { throw "找不到技能目录：$src" }

$target = Join-Path $Dest $skillName
if (Test-Path -LiteralPath $target) {
    if (-not $Force) { throw "已存在：$target（加 -Force 覆盖）" }
    Remove-Item -LiteralPath $target -Recurse -Force
}
New-Item -ItemType Directory -Path $Dest -Force | Out-Null
Copy-Item -LiteralPath $src -Destination $target -Recurse -Force
Write-Host "[1/3] 已安装到 $target" -ForegroundColor Green

# 依赖自检（缺了只提示，不阻断安装）
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
if ($py) { Write-Host "[2/3] Python: $($py.Source)" -ForegroundColor Green }
else { Write-Warning "[2/3] 没找到 python：脚本需要 Python 3.10+ 才能运行" }

if (Get-Command pdftotext -ErrorAction SilentlyContinue) {
    Write-Host "      pdftotext: 已就绪（文本层通道可用）"
} else {
    Write-Warning "      pdftotext 不在 PATH：装 poppler 后加入 PATH，或设环境变量 PDFTOTEXT"
}
if ($env:MINERU_HOME -or (Get-Command mineru -ErrorAction SilentlyContinue)) {
    Write-Host "      MinerU: 已配置（净通道可用）"
} else {
    Write-Warning "      MinerU 未配置：净通道需要 MINERU_HOME / MINERU_EXE（或 mineru 在 PATH）"
}

# 官方校验（如果装了 skill-creator）
$validator = Join-Path $Dest '.system' 'skill-creator' 'scripts' 'quick_validate.py'
if ($py -and (Test-Path -LiteralPath $validator)) {
    & $py.Source -B $validator $target
    Write-Host "[3/3] 已通过 quick_validate" -ForegroundColor Green
} else {
    Write-Host "[3/3] 跳过 quick_validate（未安装 skill-creator）"
}

Write-Host ""
Write-Host "完成。下一轮对话即可用 \$math-question-bank 调用，或直接说：把这本书的 PDF 转成题库。" -ForegroundColor Cyan
