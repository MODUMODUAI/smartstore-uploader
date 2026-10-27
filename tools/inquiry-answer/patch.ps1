$ErrorActionPreference = 'Stop'
$root = 'C:\smartstore uploader'
if ($args.Count -gt 0) { $root = $args[0] }
$static = Join-Path $root 'app\static'
Write-Host '========================================'
Write-Host ' MODUMODU patch: inquiry answer + send button'
Write-Host '========================================'
if (-not (Test-Path -LiteralPath $static)) { Write-Host ('[FAIL] not found: ' + $static); exit 1 }

$utf8 = New-Object Text.UTF8Encoding($false)
function Dec([string]$s) { return $utf8.GetString([Convert]::FromBase64String($s)) }
function Read-Doc([string]$path) {
  $bytes = [IO.File]::ReadAllBytes($path)
  $bom = $bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF
  $off = 0; if ($bom) { $off = 3 }
  $raw = $utf8.GetString($bytes, $off, $bytes.Length - $off)
  return @{ Path = $path; Bom = $bom; Crlf = $raw.Contains("`r`n"); Text = $raw.Replace("`r`n", "`n") }
}
function Write-Doc($d) {
  $out = $d.Text
  if ($d.Crlf) { $out = $out.Replace("`n", "`r`n") }
  [IO.File]::WriteAllText($d.Path, $out, (New-Object Text.UTF8Encoding($d.Bom)))
}

$idx = Read-Doc (Join-Path $static 'index.html')
$js  = Read-Doc (Join-Path $static 'app.js')
$css = Read-Doc (Join-Path $static 'styles.css')

if ($idx.Text -match 'inquiry-answer-box' -and $idx.Text -match 'inquiryOldWrap') {
  Write-Host '[-] already patched'
  exit 0
}

# Match by element ids only (no Korean in the pattern)
$htmlPat = '(?s)<div class="inquiry-old">\s*<label>[^<]*<textarea id="inquiryAnswerView"[^>]*>.*?</textarea></label>\s*<label>[^<]*<input id="inquiryAnswerAt"[^>]*/?>\s*</label>\s*</div>\s*<div class="inquiry-new">\s*<label>[^<]*<input id="inquiryAnswerTitle"[^>]*/?>\s*</label>\s*<label>[^<]*<textarea id="inquiryAnswerDraft"[^>]*>.*?</textarea></label>\s*</div>'
$htmlOld = [regex]::Match($idx.Text, $htmlPat)
if (-not $htmlOld.Success) {
  Write-Host '[FAIL] index.html: inquiry old/new block not found. Nothing changed.'
  exit 1
}
$htmlNew = Dec 'ICAgICAgICAgICAgPGRpdiBjbGFzcz0iaW5xdWlyeS1uZXcgaW5xdWlyeS1hbnN3ZXItYm94Ij4KICAgICAgICAgICAgICA8bGFiZWw+64u167OAIOygnOuqqTxpbnB1dCBpZD0iaW5xdWlyeUFuc3dlclRpdGxlIiBhdXRvY29tcGxldGU9Im9mZiIgLz48L2xhYmVsPgogICAgICAgICAgICAgIDxsYWJlbD7ri7Xrs4DrgrTsmqkgKOyXrOq4sOyXkCDsnoXroKUpPHRleHRhcmVhIGlkPSJpbnF1aXJ5QW5zd2VyRHJhZnQiIHBsYWNlaG9sZGVyPSLsl6zquLDsl5Ag64u167OA7J2EIOyeheugpe2VmOyEuOyalCI+PC90ZXh0YXJlYT48L2xhYmVsPgogICAgICAgICAgICA8L2Rpdj4KICAgICAgICAgICAgPGRpdiBjbGFzcz0iaW5xdWlyeS1vbGQiIGlkPSJpbnF1aXJ5T2xkV3JhcCIgaGlkZGVuPgogICAgICAgICAgICAgIDxsYWJlbD7rs7Trgrgg64u167OAPHRleHRhcmVhIGlkPSJpbnF1aXJ5QW5zd2VyVmlldyIgcmVhZG9ubHkgdGFiaW5kZXg9Ii0xIj48L3RleHRhcmVhPjwvbGFiZWw+CiAgICAgICAgICAgICAgPGxhYmVsPuuLteuzgOydvDxpbnB1dCBpZD0iaW5xdWlyeUFuc3dlckF0IiByZWFkb25seSB0YWJpbmRleD0iLTEiIC8+PC9sYWJlbD4KICAgICAgICAgICAgPC9kaXY+'
$idx.Text = $idx.Text.Substring(0, $htmlOld.Index) + $htmlNew.TrimEnd() + $idx.Text.Substring($htmlOld.Index + $htmlOld.Length)

$btn = [regex]::Match($idx.Text, '<button type="button" id="inquiryAnswerButton"[^>]*>.*?</button>')
if (-not $btn.Success) { Write-Host '[FAIL] index.html: send button not found. Nothing changed.'; exit 1 }
$idx.Text = $idx.Text.Substring(0, $btn.Index) + (Dec 'PGJ1dHRvbiB0eXBlPSJidXR0b24iIGlkPSJpbnF1aXJ5QW5zd2VyQnV0dG9uIiBhY2Nlc3NrZXk9InMiPuuLteuzgCDrs7TrgrTquLAoUyk8L2J1dHRvbj4=') + $idx.Text.Substring($btn.Index + $btn.Length)

$jsPat = '(?s)if \(\$\("#inquiryAnswerView"\)\) \$\("#inquiryAnswerView"\)\.value = item\.answer \|\| "";\s*if \(\$\("#inquiryAnswerAt"\)\) \$\("#inquiryAnswerAt"\)\.value = item\.answer_at \? formatOrderDate\(item\.answer_at\) : "";\s*if \(!same\) \{\s*if \(\$\("#inquiryAnswerTitle"\)\) \$\("#inquiryAnswerTitle"\)\.value = "";\s*if \(\$\("#inquiryAnswerDraft"\)\) \$\("#inquiryAnswerDraft"\)\.value = "";\s*\}'
$jsM = [regex]::Match($js.Text, $jsPat)
if (-not $jsM.Success) {
  Write-Host '[FAIL] app.js: fillInquiryDetail answer block not found. Nothing changed.'
  exit 1
}
$js.Text = $js.Text.Substring(0, $jsM.Index) + (Dec 'ICBpZiAoJCgiI2lucXVpcnlBbnN3ZXJWaWV3IikpICQoIiNpbnF1aXJ5QW5zd2VyVmlldyIpLnZhbHVlID0gaXRlbS5hbnN3ZXIgfHwgIiI7CiAgaWYgKCQoIiNpbnF1aXJ5QW5zd2VyQXQiKSkgJCgiI2lucXVpcnlBbnN3ZXJBdCIpLnZhbHVlID0gaXRlbS5hbnN3ZXJfYXQgPyBmb3JtYXRPcmRlckRhdGUoaXRlbS5hbnN3ZXJfYXQpIDogIiI7CiAgY29uc3QgYW5zd2VyZWQgPSBCb29sZWFuKFN0cmluZyhpdGVtLmFuc3dlciB8fCAiIikudHJpbSgpKTsKICBpZiAoJCgiI2lucXVpcnlPbGRXcmFwIikpICQoIiNpbnF1aXJ5T2xkV3JhcCIpLmhpZGRlbiA9ICFhbnN3ZXJlZDsKICAkKCIjaW5xdWlyeVBhbmVCYXNpYyIpPy5jbGFzc0xpc3QudG9nZ2xlKCJpbnF1aXJ5LW5vLW9sZCIsICFhbnN3ZXJlZCk7CiAgaWYgKCFzYW1lKSB7CiAgICBpZiAoJCgiI2lucXVpcnlBbnN3ZXJUaXRsZSIpKSAkKCIjaW5xdWlyeUFuc3dlclRpdGxlIikudmFsdWUgPSAiIjsKICAgIGlmICgkKCIjaW5xdWlyeUFuc3dlckRyYWZ0IikpICQoIiNpbnF1aXJ5QW5zd2VyRHJhZnQiKS52YWx1ZSA9ICIiOwogICAgY29uc3QgYmF0Y2ggPSAkKCIjaW5xdWlyeVBhbmVCYXRjaCIpICYmICEkKCIjaW5xdWlyeVBhbmVCYXRjaCIpLmhpZGRlbjsKICAgIGNvbnN0IHRhcmdldCA9IGJhdGNoID8gJCgiI2lucXVpcnlCYXRjaEJvZHkiKSA6ICQoIiNpbnF1aXJ5QW5zd2VyRHJhZnQiKTsKICAgIHJlcXVlc3RBbmltYXRpb25GcmFtZSgoKSA9PiB0YXJnZXQ/LmZvY3VzKHsgcHJldmVudFNjcm9sbDogdHJ1ZSB9KSk7CiAgfQ==').TrimEnd() + $js.Text.Substring($jsM.Index + $jsM.Length)

if ($css.Text -notmatch 'inquiry-no-old') {
  $css.Text = $css.Text.TrimEnd() + (Dec 'Ci8qIGlucXVpcnktYW5zd2VyLWZpeCAqLwouaW5xdWlyeS1vbGRbaGlkZGVuXSB7IGRpc3BsYXk6IG5vbmU7IH0KLmlucXVpcnktc2hlZXQuaW5xdWlyeS1uby1vbGQgeyBncmlkLXRlbXBsYXRlLWNvbHVtbnM6IG1pbm1heCg0MjBweCwgMS4zZnIpIG1pbm1heCgyNjBweCwgMS4yZnIpOyB9Ci5pbnF1aXJ5LWFuc3dlci1ib3ggdGV4dGFyZWEgeyBtaW4taGVpZ2h0OiAxNzBweDsgfQouaW5xdWlyeS1kZXRhaWwtZm9vdCB7CiAgZGlzcGxheTogZmxleCAhaW1wb3J0YW50OwogIGp1c3RpZnktY29udGVudDogY2VudGVyOwogIGFsaWduLWl0ZW1zOiBjZW50ZXI7CiAgZ2FwOiA4cHg7CiAgcG9zaXRpb246IHN0aWNreTsKICBib3R0b206IC0xMHB4OwogIHotaW5kZXg6IDI7CiAgcGFkZGluZzogNnB4IDA7CiAgYmFja2dyb3VuZDogdmFyKC0tc3VyZmFjZSk7Cn0KLmlucXVpcnktZGV0YWlsLWZvb3QgI2lucXVpcnlUZW1wbGF0ZSB7CiAgcG9zaXRpb246IGFic29sdXRlOwogIGxlZnQ6IDA7CiAgd2lkdGg6IG1pbigzNjBweCwgNDUlKTsKfQojaW5xdWlyeUFuc3dlckJ1dHRvbiB7CiAgbWluLXdpZHRoOiAxNjBweDsKICBwYWRkaW5nOiA3cHggMjhweDsKICBmb250LXNpemU6IDE0cHg7Cn0KI2lucXVpcnlBbnN3ZXJEcmFmdCwKI2lucXVpcnlCYXRjaEJvZHksCiNpbnF1aXJ5QW5zd2VyVGl0bGUsCiNpbnF1aXJ5QmF0Y2hUaXRsZSB7CiAgcG9pbnRlci1ldmVudHM6IGF1dG8gIWltcG9ydGFudDsKICB1c2VyLXNlbGVjdDogdGV4dCAhaW1wb3J0YW50OwogIC13ZWJraXQtdXNlci1zZWxlY3Q6IHRleHQgIWltcG9ydGFudDsKfQo=')
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
Copy-Item -LiteralPath $idx.Path -Destination ($idx.Path + '.bak-' + $stamp)
Copy-Item -LiteralPath $js.Path  -Destination ($js.Path  + '.bak-' + $stamp)
Copy-Item -LiteralPath $css.Path -Destination ($css.Path + '.bak-' + $stamp)
Write-Doc $idx; Write-Host ('[OK] index.html patched (backup .bak-' + $stamp + ')')
Write-Doc $js;  Write-Host ('[OK] app.js patched (backup .bak-' + $stamp + ')')
Write-Doc $css; Write-Host ('[OK] styles.css patched (backup .bak-' + $stamp + ')')
Write-Host ''
Write-Host '[OK] Done. In the MODUMODU browser window press Ctrl+Shift+R.'
