Set-Location -LiteralPath $PSScriptRoot
$Host.UI.RawUI.WindowTitle = 'MODUMODU Restore Data'
$here = (Resolve-Path -LiteralPath $PSScriptRoot).Path.TrimEnd('\')

Write-Host '========================================'
Write-Host ' MODUMODU - restore login/product data'
Write-Host '========================================'
Write-Host ('Target folder: ' + $here)
Write-Host ''

if (-not (Test-Path -LiteralPath (Join-Path $here 'MODUMODU.exe'))) {
  Write-Host '[FAIL] Put this file inside the new MODUMODU folder (next to MODUMODU.exe).'
  exit 1
}

function Get-DataSize([string]$dir) {
  $sum = (Get-ChildItem -LiteralPath $dir -Recurse -File -Force -ErrorAction SilentlyContinue |
    Measure-Object -Property Length -Sum).Sum
  if ($null -eq $sum) { return 0 }
  return [int64]$sum
}

$roots = New-Object System.Collections.Generic.List[string]
foreach ($r in @(
    [Environment]::GetFolderPath('Desktop'),
    [Environment]::GetFolderPath('MyDocuments'),
    (Join-Path $env:USERPROFILE 'Downloads'),
    $env:USERPROFILE,
    $env:LOCALAPPDATA,
    $env:APPDATA,
    $env:ProgramFiles,
    ${env:ProgramFiles(x86)},
    'C:\', 'D:\', 'E:\')) {
  if ($r -and (Test-Path -LiteralPath $r)) { $roots.Add($r) }
}

$found = @{}

$shell = New-Object -ComObject WScript.Shell
$lnkDirs = @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('CommonDesktopDirectory'),
  [Environment]::GetFolderPath('StartMenu'), [Environment]::GetFolderPath('CommonStartMenu'))
foreach ($d in $lnkDirs) {
  if (-not $d -or -not (Test-Path -LiteralPath $d)) { continue }
  Get-ChildItem -LiteralPath $d -Filter *.lnk -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
    try {
      $t = $shell.CreateShortcut($_.FullName)
      foreach ($p in @($t.WorkingDirectory, (Split-Path -Parent $t.TargetPath))) {
        if ($p -and (Test-Path -LiteralPath (Join-Path $p 'MODUMODU.exe'))) { $found[(Resolve-Path -LiteralPath $p).Path.TrimEnd('\')] = 1 }
      }
    } catch {}
  }
}

Write-Host 'Searching for old MODUMODU folders (may take a minute)...'
foreach ($r in $roots) {
  $depth = 5
  if ($r -match '^[A-Z]:\\$') { $depth = 3 }
  Get-ChildItem -LiteralPath $r -Filter 'MODUMODU.exe' -Recurse -Depth $depth -File -Force -ErrorAction SilentlyContinue |
    ForEach-Object { $found[$_.DirectoryName.TrimEnd('\')] = 1 }
}

$cands = @()
foreach ($dir in $found.Keys) {
  if ($dir -ieq $here) { continue }
  $data = Join-Path $dir 'data'
  if (-not (Test-Path -LiteralPath $data)) { continue }
  $size = Get-DataSize $data
  if ($size -le 0) { continue }
  $ed = ''
  if (Test-Path -LiteralPath (Join-Path $dir 'edition.txt')) { $ed = (Get-Content -LiteralPath (Join-Path $dir 'edition.txt') -Raw).Trim() }
  $ver = ''
  if (Test-Path -LiteralPath (Join-Path $dir 'version.txt')) { $ver = (Get-Content -LiteralPath (Join-Path $dir 'version.txt') -Raw).Trim() }
  $last = (Get-ChildItem -LiteralPath $data -Recurse -File -Force -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1).LastWriteTime
  $cands += [pscustomobject]@{ Dir = $dir; Data = $data; SizeMB = [math]::Round($size / 1MB, 1); Edition = $ed; Version = $ver; LastWrite = $last
    HasSettings = (Test-Path -LiteralPath (Join-Path $data 'settings.json')) }
}

if ($cands.Count -eq 0) {
  Write-Host ''
  Write-Host '[FAIL] No old MODUMODU data folder found.'
  Write-Host 'Find your old folder (the one you used before), and copy its "data" folder'
  Write-Host ('into: ' + $here)
  exit 1
}

$cands = @($cands | Sort-Object -Property @{Expression = 'HasSettings'; Descending = $true}, @{Expression = 'SizeMB'; Descending = $true})
Write-Host ''
Write-Host 'Found:'
for ($i = 0; $i -lt $cands.Count; $i++) {
  $c = $cands[$i]
  Write-Host ('  [' + ($i + 1) + '] ' + $c.SizeMB + ' MB  edition=' + $c.Edition + '  ver=' + $c.Version + '  last=' + $c.LastWrite)
  Write-Host ('      ' + $c.Dir)
}
Write-Host ''
$ans = Read-Host ('Number to restore (Enter = 1)')
if (-not $ans) { $ans = '1' }
$n = 0
if (-not [int]::TryParse($ans, [ref]$n) -or $n -lt 1 -or $n -gt $cands.Count) {
  Write-Host '[FAIL] wrong number'
  exit 1
}
$src = $cands[$n - 1]

Write-Host ''
Write-Host 'Stopping MODUMODU...'
Get-Process -Name 'MODUMODU' -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

$dst = Join-Path $here 'data'
if (Test-Path -LiteralPath $dst) {
  $bak = Join-Path $here ('data_before_restore_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
  Move-Item -LiteralPath $dst -Destination $bak
  Write-Host ('Old new-folder data moved to: ' + $bak)
}

Write-Host ('Copying from: ' + $src.Data)
robocopy $src.Data $dst /E /R:1 /W:1 /NFL /NDL /NJH /NP | Out-Null
if ($LASTEXITCODE -ge 8) {
  Write-Host ('[FAIL] copy error (robocopy ' + $LASTEXITCODE + ')')
  exit 1
}
Write-Host ('[OK] copied ' + [math]::Round((Get-DataSize $dst) / 1MB, 1) + ' MB')
Write-Host ''

if (Test-Path -LiteralPath (Join-Path $here 'start-master.ps1')) {
  Write-Host 'Starting master on 8787...'
  & (Join-Path $here 'start-master.ps1')
}
exit 0
