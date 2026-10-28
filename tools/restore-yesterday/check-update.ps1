param(
  [Parameter(Mandatory = $true, Position = 0)]
  [string]$Mode,
  [Parameter(Mandatory = $true, Position = 1)]
  [string]$Dir
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$manifestUrl = 'https://github.com/MODUMODUAI/smartstore-uploader/releases/latest/download/latest.json'
$urlFile = Join-Path $Dir 'update_url.txt'
if (Test-Path -LiteralPath $urlFile) {
  $custom = [IO.File]::ReadAllText($urlFile).Trim().TrimStart([char]0xFEFF)
  if ($custom -match '^https://') { $manifestUrl = $custom }
}

function Repair-BrokenNames([string]$Folder) {
  if (-not (Test-Path -LiteralPath $Folder)) { return }
  $cp866 = [Text.Encoding]::GetEncoding(866)
  $utf8 = [Text.Encoding]::UTF8
  Get-ChildItem -LiteralPath $Folder -File -Force | ForEach-Object {
    $bytes = $cp866.GetBytes($_.Name)
    $fixed = $utf8.GetString($bytes)
    if ($fixed -eq $_.Name) { return }
    if ($fixed -notmatch '[\uAC00-\uD7A3]') { return }
    if ($fixed -match '[\\/]') { return }
    $dest = Join-Path $Folder $fixed
    try {
      $_.Attributes = 'Archive'
      if (Test-Path -LiteralPath $dest) {
        $keep = Get-Item -LiteralPath $dest -Force
        if ($keep.FullName -eq $_.FullName) { return }
        $keep.Attributes = 'Archive'
        if ($keep.Length -ge $_.Length) { Remove-Item -LiteralPath $_.FullName -Force }
        else { Remove-Item -LiteralPath $dest -Force; Move-Item -LiteralPath $_.FullName -Destination $dest -Force }
      } else {
        Move-Item -LiteralPath $_.FullName -Destination $dest -Force
      }
    } catch {}
  }
}

try {
  Repair-BrokenNames $Dir
  $spread = Join-Path $Dir '배포'
  if (Test-Path -LiteralPath $spread) {
    Get-ChildItem -LiteralPath $spread -Directory -Force | ForEach-Object { Repair-BrokenNames $_.FullName }
  }
} catch {}

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

function Test-ProgramExe([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) { return $false }
  $fs = [System.IO.File]::Open($Path, 'Open', 'Read', 'ReadWrite')
  try {
    $buf = New-Object byte[] 1048576
    $carry = ''
    while (($n = $fs.Read($buf, 0, $buf.Length)) -gt 0) {
      $window = $carry + [System.Text.Encoding]::ASCII.GetString($buf, 0, $n)
      if ($window.Contains('PyInstaller') -or $window.Contains('python313.dll')) { return $true }
      if ($window.Length -gt 64) { $carry = $window.Substring($window.Length - 64) } else { $carry = $window }
    }
  } finally {
    $fs.Close()
  }
  return $false
}

function Repair-MasterShortcut([string]$Folder) {
  $vbs = Join-Path $Folder '어제오후9시.vbs'
  if (-not (Test-Path -LiteralPath $vbs)) { return }
  $desk = [Environment]::GetFolderPath('Desktop')
  if (-not $desk) { return }
  $wscript = Join-Path $env:SystemRoot 'System32\wscript.exe'
  $shell = New-Object -ComObject WScript.Shell
  $link = $shell.CreateShortcut((Join-Path $desk '모두모두AI 마스터.lnk'))
  $link.TargetPath = $wscript
  $link.Arguments = "//nologo `"$vbs`""
  $link.WorkingDirectory = $Folder
  $exe = Join-Path $Folder 'MODUMODU.exe'
  if (Test-Path -LiteralPath $exe) { $link.IconLocation = "$exe,0" }
  $link.WindowStyle = 1
  $link.Description = '모두모두AI'
  $link.Save()
  Get-ChildItem -LiteralPath $desk -Filter *.lnk -File -ErrorAction SilentlyContinue | ForEach-Object {
    if ($_.Name -eq '모두모두AI 마스터.lnk') { return }
    $item = $shell.CreateShortcut($_.FullName)
    $target = [string]$item.TargetPath
    if (-not $target.ToLower().EndsWith('\modumodu.exe')) { return }
    $targetDir = [System.IO.Path]::GetDirectoryName($target)
    $script = Join-Path $targetDir '어제오후9시.vbs'
    if (-not (Test-Path -LiteralPath $script)) { return }
    $item.TargetPath = $wscript
    $item.Arguments = "//nologo `"$script`""
    $item.WorkingDirectory = $targetDir
    $targetExe = Join-Path $targetDir 'MODUMODU.exe'
    if (Test-Path -LiteralPath $targetExe) { $item.IconLocation = "$targetExe,0" }
    $item.WindowStyle = 1
    $item.Save()
  }
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
    $exclude = @('edition.txt', 'update_url.txt', 'license_url.txt', 'launcher.log')
    if (Test-ProgramExe (Join-Path $Dir 'MODUMODU.exe')) { $exclude += 'MODUMODU.exe' }
    $roboArgs = @($src, $Dir, '/E', '/XD', 'data', '/XF') + $exclude + @('/R:8', '/W:2', '/NFL', '/NDL', '/NJH', '/NJS', '/NP')
    & robocopy.exe @roboArgs
    if ($LASTEXITCODE -ge 8) { throw 'copy failed' }
    Repair-BrokenNames $Dir
    Repair-MasterShortcut $Dir
    exit 0
  } catch {
    exit 1
  } finally {
    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
  }
}

exit 0
