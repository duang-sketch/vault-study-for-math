param(
    [string]$MineruHome = $env:MINERU_HOME,
    [string]$MineruExe  = $(if ($env:MINERU_EXE) { $env:MINERU_EXE } else { 'mineru' }),
    [string]$OutDir     = $(if ($env:CJX_DIR) { $env:CJX_DIR } else { './_raw' }),
    [string]$SearchRoot = $(if ($env:SOURCE_ROOT) { $env:SOURCE_ROOT } else { './books' })
)
$ErrorActionPreference = 'Continue'
if ($MineruHome) { $env:MINERU_HOME = $MineruHome }
$mineru = $MineruExe
$out = $OutDir

# Target identity is validated by filename codepoints, so this ASCII-only script
# cannot be corrupted by the ANSI/UTF-8 script-loading mismatch.
$han = [string][char]0x4E60      # xi  (from "chen ji xiu")
$third = [string]([char]0x7B2C + [char]0x4E09 + [char]0x7248)  # "di san ban"
$cand = Get-ChildItem -LiteralPath $SearchRoot -Recurse -Filter '*.pdf' -ErrorAction SilentlyContinue |
        Where-Object { $_.Name.IndexOf($han) -ge 0 -and $_.Name.IndexOf($third) -ge 0 -and
                       $_.Name -notmatch 'ARM|STM32|Cortex' -and
                       $_.Name.IndexOf([char]0x4E0A) -lt 0 }
if ($cand.Count -gt 1) { $cand = $cand | Where-Object { $_.FullName -notmatch [char]0x7ADE + [char]0x8D5B } }
$pdf = ($cand | Select-Object -First 1).FullName

Write-Output ("PDF=" + $pdf)
if (-not $pdf) { Write-Output 'PDF_NOT_FOUND'; exit 1 }

$batches = @(
  @(9, 68),
  @(69, 128),
  @(129, 188),
  @(189, 248),
  @(249, 260)
)

foreach ($b in $batches) {
  $s = $b[0]; $e = $b[1]
  $target = Join-Path $out ("dn_p{0}-{1}.md" -f $s, $e)
  if ((Test-Path $target) -and ((Get-Item $target).Length -gt 2000)) {
    Write-Output "SKIP existing $target"
    continue
  }
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  Write-Output "=== START p$s-$e $(Get-Date -Format o) ==="
  & $mineru parse $pdf -p "$s-$e" --tier standard -o $target --wait 2400 2>&1 | Out-String | Write-Output
  $sw.Stop()
  $len = if (Test-Path $target) { (Get-Item $target).Length } else { 0 }
  Write-Output "=== DONE p$s-$e elapsed=$([int]$sw.Elapsed.TotalSeconds)s bytes=$len ==="
}
Write-Output "ALL_BATCHES_COMPLETE"
