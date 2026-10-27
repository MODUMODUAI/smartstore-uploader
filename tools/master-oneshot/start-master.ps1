Set-Location -LiteralPath $PSScriptRoot
$Host.UI.RawUI.WindowTitle = 'MODUMODU Master Start'
Write-Host '========================================'
Write-Host ' MODUMODU Master  http://127.0.0.1:8787'
Write-Host '========================================'
Write-Host ("Folder: " + $PWD)
Write-Host ''

$exe = Join-Path $PWD 'MODUMODU.exe'
if (-not (Test-Path -LiteralPath $exe)) {
  Write-Host '[FAIL] MODUMODU.exe not found. Put this file next to MODUMODU.exe.'
  exit 1
}

Set-Content -LiteralPath (Join-Path $PWD 'edition.txt') -Value "master" -Encoding Ascii
Write-Host '[1] edition.txt = master'

Write-Host '[2] stop old MODUMODU'
Get-Process -Name 'MODUMODU' -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

Write-Host '[3] start (update check ON, auto apply)'
Remove-Item Env:\UPLOADER_SKIP_UPDATE -ErrorAction SilentlyContinue
Remove-Item Env:\UPLOADER_FORCE_UPDATE -ErrorAction SilentlyContinue
Remove-Item Env:\UPLOADER_PORT -ErrorAction SilentlyContinue
$env:UPLOADER_UPDATE_AUTO = 'yes'
Start-Process -FilePath $exe -WorkingDirectory $PWD | Out-Null

Write-Host ''
Write-Host 'If a new version exists it updates and restarts by itself.'
Write-Host 'Browser opens http://127.0.0.1:8787 automatically.'
Write-Host 'Next time: just double-click MODUMODU.exe in this folder.'
Start-Sleep -Seconds 5
exit 0
