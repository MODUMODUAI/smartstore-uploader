$ErrorActionPreference = 'Stop'
$root = 'C:\smartstore uploader'
if ($args.Count -gt 0) { $root = $args[0] }
$static = Join-Path $root 'app\static'
Write-Host '========================================'
Write-Host ' MODUMODU patch: inquiry answer box + send button'
Write-Host '========================================'
if (-not (Test-Path -LiteralPath $static)) { Write-Host ('[FAIL] not found: ' + $static); exit 1 }

$utf8 = New-Object Text.UTF8Encoding($false)
function Dec([string]$s) { return $utf8.GetString([Convert]::FromBase64String($s)) }
$edits = @(
  @{ File = 'index.html'; Marker = 'inquiryOldWrap'; Old = 'ICAgICAgICAgICAgPGRpdiBjbGFzcz0iaW5xdWlyeS1vbGQiPgogICAgICAgICAgICAgIDxsYWJlbD7ri7Xrs4DrgrTsmqk8dGV4dGFyZWEgaWQ9ImlucXVpcnlBbnN3ZXJWaWV3IiByZWFkb25seT48L3RleHRhcmVhPjwvbGFiZWw+CiAgICAgICAgICAgICAgPGxhYmVsPuuLteuzgOydvDxpbnB1dCBpZD0iaW5xdWlyeUFuc3dlckF0IiByZWFkb25seSAvPjwvbGFiZWw+CiAgICAgICAgICAgIDwvZGl2PgogICAgICAgICAgICA8ZGl2IGNsYXNzPSJpbnF1aXJ5LW5ldyI+CiAgICAgICAgICAgICAgPGxhYmVsPuyDiCDri7Xrs4Ag7KCc66qpPGlucHV0IGlkPSJpbnF1aXJ5QW5zd2VyVGl0bGUiIC8+PC9sYWJlbD4KICAgICAgICAgICAgICA8bGFiZWw+7IOIIOuLteuzgCDrgrTsmqk8dGV4dGFyZWEgaWQ9ImlucXVpcnlBbnN3ZXJEcmFmdCI+PC90ZXh0YXJlYT48L2xhYmVsPgogICAgICAgICAgICA8L2Rpdj4='; New = 'ICAgICAgICAgICAgPGRpdiBjbGFzcz0iaW5xdWlyeS1uZXcgaW5xdWlyeS1hbnN3ZXItYm94Ij4KICAgICAgICAgICAgICA8bGFiZWw+64u167OAIOygnOuqqTxpbnB1dCBpZD0iaW5xdWlyeUFuc3dlclRpdGxlIiBhdXRvY29tcGxldGU9Im9mZiIgLz48L2xhYmVsPgogICAgICAgICAgICAgIDxsYWJlbD7ri7Xrs4DrgrTsmqkgKOyXrOq4sOyXkCDsnoXroKUpPHRleHRhcmVhIGlkPSJpbnF1aXJ5QW5zd2VyRHJhZnQiIHBsYWNlaG9sZGVyPSLsl6zquLDsl5Ag64u167OA7J2EIOyeheugpe2VmOyEuOyalCI+PC90ZXh0YXJlYT48L2xhYmVsPgogICAgICAgICAgICA8L2Rpdj4KICAgICAgICAgICAgPGRpdiBjbGFzcz0iaW5xdWlyeS1vbGQiIGlkPSJpbnF1aXJ5T2xkV3JhcCIgaGlkZGVuPgogICAgICAgICAgICAgIDxsYWJlbD7rs7Trgrgg64u167OAPHRleHRhcmVhIGlkPSJpbnF1aXJ5QW5zd2VyVmlldyIgcmVhZG9ubHkgdGFiaW5kZXg9Ii0xIj48L3RleHRhcmVhPjwvbGFiZWw+CiAgICAgICAgICAgICAgPGxhYmVsPuuLteuzgOydvDxpbnB1dCBpZD0iaW5xdWlyeUFuc3dlckF0IiByZWFkb25seSB0YWJpbmRleD0iLTEiIC8+PC9sYWJlbD4KICAgICAgICAgICAgPC9kaXY+' },
  @{ File = 'index.html'; Marker = 'inquiryOldWrap'; Old = 'ICAgICAgICAgICAgPGJ1dHRvbiB0eXBlPSJidXR0b24iIGlkPSJpbnF1aXJ5QW5zd2VyQnV0dG9uIiBhY2Nlc3NrZXk9InMiPuuLteuzgCDsoITshqEoUyk8L2J1dHRvbj4='; New = 'ICAgICAgICAgICAgPGJ1dHRvbiB0eXBlPSJidXR0b24iIGlkPSJpbnF1aXJ5QW5zd2VyQnV0dG9uIiBhY2Nlc3NrZXk9InMiPuuLteuzgCDrs7TrgrTquLAoUyk8L2J1dHRvbj4=' },
  @{ File = 'app.js'; Marker = 'inquiry-no-old'; Old = 'ICBpZiAoJCgiI2lucXVpcnlBbnN3ZXJBdCIpKSAkKCIjaW5xdWlyeUFuc3dlckF0IikudmFsdWUgPSBpdGVtLmFuc3dlcl9hdCA/IGZvcm1hdE9yZGVyRGF0ZShpdGVtLmFuc3dlcl9hdCkgOiAiIjsKICBpZiAoIXNhbWUpIHsKICAgIGlmICgkKCIjaW5xdWlyeUFuc3dlclRpdGxlIikpICQoIiNpbnF1aXJ5QW5zd2VyVGl0bGUiKS52YWx1ZSA9ICIiOwogICAgaWYgKCQoIiNpbnF1aXJ5QW5zd2VyRHJhZnQiKSkgJCgiI2lucXVpcnlBbnN3ZXJEcmFmdCIpLnZhbHVlID0gIiI7CiAgfQ=='; New = 'ICBpZiAoJCgiI2lucXVpcnlBbnN3ZXJBdCIpKSAkKCIjaW5xdWlyeUFuc3dlckF0IikudmFsdWUgPSBpdGVtLmFuc3dlcl9hdCA/IGZvcm1hdE9yZGVyRGF0ZShpdGVtLmFuc3dlcl9hdCkgOiAiIjsKICBjb25zdCBhbnN3ZXJlZCA9IEJvb2xlYW4oU3RyaW5nKGl0ZW0uYW5zd2VyIHx8ICIiKS50cmltKCkpOwogIGlmICgkKCIjaW5xdWlyeU9sZFdyYXAiKSkgJCgiI2lucXVpcnlPbGRXcmFwIikuaGlkZGVuID0gIWFuc3dlcmVkOwogICQoIiNpbnF1aXJ5UGFuZUJhc2ljIik/LmNsYXNzTGlzdC50b2dnbGUoImlucXVpcnktbm8tb2xkIiwgIWFuc3dlcmVkKTsKICBpZiAoIXNhbWUpIHsKICAgIGlmICgkKCIjaW5xdWlyeUFuc3dlclRpdGxlIikpICQoIiNpbnF1aXJ5QW5zd2VyVGl0bGUiKS52YWx1ZSA9ICIiOwogICAgaWYgKCQoIiNpbnF1aXJ5QW5zd2VyRHJhZnQiKSkgJCgiI2lucXVpcnlBbnN3ZXJEcmFmdCIpLnZhbHVlID0gIiI7CiAgICBjb25zdCBiYXRjaCA9ICQoIiNpbnF1aXJ5UGFuZUJhdGNoIikgJiYgISQoIiNpbnF1aXJ5UGFuZUJhdGNoIikuaGlkZGVuOwogICAgY29uc3QgdGFyZ2V0ID0gYmF0Y2ggPyAkKCIjaW5xdWlyeUJhdGNoQm9keSIpIDogJCgiI2lucXVpcnlBbnN3ZXJEcmFmdCIpOwogICAgcmVxdWVzdEFuaW1hdGlvbkZyYW1lKCgpID0+IHRhcmdldD8uZm9jdXMoeyBwcmV2ZW50U2Nyb2xsOiB0cnVlIH0pKTsKICB9' },
  @{ File = 'styles.css'; Marker = 'inquiry-no-old'; Old = 'I2lucXVpcnlUZW1wbGF0ZSB7IHdpZHRoOiBtaW4oMzYwcHgsIDUwJSk7IH0='; New = 'I2lucXVpcnlUZW1wbGF0ZSB7IHdpZHRoOiBtaW4oMzYwcHgsIDEwMCUpOyBqdXN0aWZ5LXNlbGY6IHN0YXJ0OyB9Ci5pbnF1aXJ5LWRldGFpbC1mb290IHsgZGlzcGxheTogZ3JpZDsgZ3JpZC10ZW1wbGF0ZS1jb2x1bW5zOiAxZnIgYXV0byAxZnI7IHBvc2l0aW9uOiBzdGlja3k7IGJvdHRvbTogLTEwcHg7IHotaW5kZXg6IDI7IHBhZGRpbmc6IDZweCAwOyBiYWNrZ3JvdW5kOiB2YXIoLS1zdXJmYWNlKTsgfQojaW5xdWlyeUFuc3dlckJ1dHRvbiB7IGp1c3RpZnktc2VsZjogY2VudGVyOyBtaW4td2lkdGg6IDE2MHB4OyBwYWRkaW5nOiA3cHggMjhweDsgZm9udC1zaXplOiAxNHB4OyB9Ci5pbnF1aXJ5LW9sZFtoaWRkZW5dIHsgZGlzcGxheTogbm9uZTsgfQouaW5xdWlyeS1zaGVldC5pbnF1aXJ5LW5vLW9sZCB7IGdyaWQtdGVtcGxhdGUtY29sdW1uczogbWlubWF4KDQyMHB4LCAxLjNmcikgbWlubWF4KDI2MHB4LCAxLjJmcik7IH0=' }
)

$docs = @{}
foreach ($e in $edits) {
  $f = $e.File
  if (-not $docs.ContainsKey($f)) {
    $path = Join-Path $static $f
    if (-not (Test-Path -LiteralPath $path)) { Write-Host ('[FAIL] not found: ' + $path); exit 1 }
    $bytes = [IO.File]::ReadAllBytes($path)
    $bom = $bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF
    $off = 0; if ($bom) { $off = 3 }
    $raw = $utf8.GetString($bytes, $off, $bytes.Length - $off)
    $docs[$f] = @{ Path = $path; Bom = $bom; Crlf = $raw.Contains("`r`n"); Text = $raw.Replace("`r`n", "`n"); Skip = $false }
    if ($docs[$f].Text.Contains($e.Marker)) { $docs[$f].Skip = $true }
  }
}

foreach ($e in $edits) {
  $d = $docs[$e.File]
  if ($d.Skip) { continue }
  $old = Dec $e.Old
  $count = ([regex]::Matches($d.Text, [regex]::Escape($old))).Count
  if ($count -ne 1) { Write-Host ('[FAIL] ' + $e.File + ': expected text found ' + $count + ' times. Nothing changed.'); exit 1 }
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
foreach ($e in $edits) {
  $d = $docs[$e.File]
  if ($d.Skip) { continue }
  $d.Text = $d.Text.Replace((Dec $e.Old), (Dec $e.New))
  $d.Changed = $true
}
foreach ($f in $docs.Keys) {
  $d = $docs[$f]
  if ($d.Skip) { Write-Host ('[-] ' + $f + ' already patched'); continue }
  Copy-Item -LiteralPath $d.Path -Destination ($d.Path + '.bak-' + $stamp)
  $out = $d.Text
  if ($d.Crlf) { $out = $out.Replace("`n", "`r`n") }
  [IO.File]::WriteAllText($d.Path, $out, (New-Object Text.UTF8Encoding($d.Bom)))
  Write-Host ('[OK] ' + $f + ' patched (backup .bak-' + $stamp + ')')
}
Write-Host ''
Write-Host '[OK] Done. In the MODUMODU browser window press Ctrl+Shift+R.'
