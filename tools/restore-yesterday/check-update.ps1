param(
  [Parameter(Mandatory = $true, Position = 0)]
  [string]$Mode,
  [Parameter(Mandatory = $true, Position = 1)]
  [string]$Dir
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$manifestUrl = 'https://github.com/ibccomae-cpu/smartstore-uploader/releases/latest/download/latest.json'

function Get-Parts([string]$text) {
  if (-not $text) { return @() }
  $text = $text.Trim().TrimStart([char]0xFEFF)
  $text = $text.Replace('-', '.').Replace('_', '.')
  $parts = @()
  foreach ($chunk in $text.Split('.')) {
    $digits = -join ($chunk.ToCharArray() | Where-Object { $_ -match '\d' })
    if ($digits) { $parts += [int]$digits }
  }
  return $parts
}

function Test-Newer([string]$remote, [string]$local) {
  $rp = @(Get-Parts $remote)
  $lp = @(Get-Parts $local)
  $n = [Math]::Min($rp.Count, $lp.Count)
  for ($i = 0; $i -lt $n; $i++) {
    if ($rp[$i] -ne $lp[$i]) { return $rp[$i] -gt $lp[$i] }
  }
  return $rp.Count -gt $lp.Count
}

function Get-Manifest {
  $headers = @{ 'User-Agent' = 'MODUMODU-Updater/1.0' }
  return Invoke-RestMethod -Uri $manifestUrl -Headers $headers -TimeoutSec 15
}

function Find-PackageRoot([string]$extracted) {
  $exe = Get-ChildItem -LiteralPath $extracted -Recurse -Filter 'MODUMODU.exe' -File | Select-Object -First 1
  if (-not $exe) { throw 'package has no program' }
  return $exe.DirectoryName
}

if ($Mode -eq '-Check') {
  try {
    $local = '0'
    $verFile = Join-Path $Dir 'version.txt'
    if (Test-Path -LiteralPath $verFile) {
      $local = [IO.File]::ReadAllText($verFile).Trim().TrimStart([char]0xFEFF)
      if (-not $local) { $local = '0' }
    }
    $info = Get-Manifest
    if (-not (Test-Newer $info.version $local)) { exit 0 }
    $offer = Join-Path $Dir 'data'
    New-Item -ItemType Directory -Force -Path $offer | Out-Null
    $body = ($info.version, $local, [string]$info.notes) -join "`n"
    [IO.File]::WriteAllText((Join-Path $offer 'update-offer.txt'), $body, [Text.Encoding]::Unicode)
    exit 2
  } catch {
    exit 0
  }
}

if ($Mode -eq '-Apply') {
  $tempRoot = Join-Path $env:TEMP ('modumodu-update-' + [guid]::NewGuid().ToString('n'))
  New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
  try {
    $info = Get-Manifest
    $zip = Join-Path $tempRoot 'update.zip'
    Invoke-WebRequest -Uri $info.url -OutFile $zip -Headers @{ 'User-Agent' = 'MODUMODU-Updater/1.0' } -TimeoutSec 180
    $hash = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLower()
    if ($hash -ne ([string]$info.sha256).ToLower()) { throw 'sha256 mismatch' }
    $extracted = Join-Path $tempRoot 'extracted'
    New-Item -ItemType Directory -Force -Path $extracted | Out-Null
    & tar.exe -xf $zip -C $extracted
    if ($LASTEXITCODE -ne 0) { throw 'extract failed' }
    $src = Find-PackageRoot $extracted
    & robocopy.exe $src $Dir /E /XD data /XF edition.txt update_url.txt license_url.txt launcher.log /R:8 /W:2 /NFL /NDL /NJH /NJS /NP
    if ($LASTEXITCODE -ge 8) { throw 'copy failed' }
    exit 0
  } catch {
    exit 1
  } finally {
    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
  }
}

exit 0
