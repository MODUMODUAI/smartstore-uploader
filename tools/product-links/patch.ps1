$ErrorActionPreference = 'Stop'
$root = 'C:\smartstore uploader'
if ($args.Count -gt 0) { $root = $args[0] }
$static = Join-Path $root 'app\static'
Write-Host '========================================'
Write-Host ' MODUMODU patch: product and order number links'
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

$js = Read-Doc (Join-Path $static 'app.js')
if ($js.Text -match 'function openProductHref' -and $js.Text -match 'function inquiryOrderCell') {
  Write-Host '[-] already patched'
  exit 0
}

$start = $js.Text.IndexOf('function linkedNumberCell(number, href, title)')
$end = $js.Text.IndexOf('function productFromRow(')
if ($start -lt 0 -or $end -lt $start) { Write-Host '[FAIL] app.js: linkedNumberCell not found. Nothing changed.'; exit 1 }
$js.Text = $js.Text.Substring(0, $start) + (Dec 'ZnVuY3Rpb24gb3BlblByb2R1Y3RIcmVmKGhyZWYsIGVtcHR5TWVzc2FnZSkgewogIGNvbnN0IHVybCA9IFN0cmluZyhocmVmIHx8ICIiKS50cmltKCk7CiAgaWYgKCF1cmwpIHsKICAgIHRvYXN0KGVtcHR5TWVzc2FnZSB8fCAi7IOB7ZKIIO2OmOydtOyngCDso7zshozqsIAg7JeG7Iq164uI64ukLiIsIHRydWUpOwogICAgcmV0dXJuIGZhbHNlOwogIH0KICBjb25zdCBwb3B1cCA9IHdpbmRvdy5vcGVuKHVybCwgIl9ibGFuayIsICJub29wZW5lcixub3JlZmVycmVyIik7CiAgaWYgKHBvcHVwKSB7CiAgICB0cnkgeyBwb3B1cC5mb2N1cygpOyB9IGNhdGNoIChfKSB7fQogICAgcmV0dXJuIHRydWU7CiAgfQogIGNvbnN0IGFuY2hvciA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoImEiKTsKICBhbmNob3IuaHJlZiA9IHVybDsKICBhbmNob3IudGFyZ2V0ID0gIl9ibGFuayI7CiAgYW5jaG9yLnJlbCA9ICJub29wZW5lciBub3JlZmVycmVyIjsKICBkb2N1bWVudC5ib2R5LmFwcGVuZENoaWxkKGFuY2hvcik7CiAgYW5jaG9yLmNsaWNrKCk7CiAgYW5jaG9yLnJlbW92ZSgpOwogIHJldHVybiB0cnVlOwp9CgpmdW5jdGlvbiBsaW5rZWROdW1iZXJDZWxsKG51bWJlciwgaHJlZiwgdGl0bGUpIHsKICBjb25zdCBjZWxsID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudCgidGQiKTsKICBjb25zdCBubyA9IFN0cmluZyhudW1iZXIgfHwgIiIpLnRyaW0oKTsKICBjZWxsLnRpdGxlID0gdGl0bGUgfHwgbm87CiAgaWYgKCFubykgcmV0dXJuIGNlbGw7CiAgaWYgKCFocmVmKSB7CiAgICBjZWxsLnRleHRDb250ZW50ID0gbm87CiAgICByZXR1cm4gY2VsbDsKICB9CiAgY29uc3QgYnV0dG9uID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudCgiYnV0dG9uIik7CiAgYnV0dG9uLnR5cGUgPSAiYnV0dG9uIjsKICBidXR0b24uY2xhc3NOYW1lID0gIm9yZGVyLXByb2R1Y3QtbGluayBwcm9kdWN0LW5vLWxpbmsiOwogIGJ1dHRvbi50ZXh0Q29udGVudCA9IG5vOwogIGJ1dHRvbi50aXRsZSA9IHRpdGxlIHx8ICLsg4Htkogg7Y6Y7J207KeAIOyXtOq4sCI7CiAgYnV0dG9uLmFkZEV2ZW50TGlzdGVuZXIoImNsaWNrIiwgKGV2ZW50KSA9PiB7CiAgICBldmVudC5wcmV2ZW50RGVmYXVsdCgpOwogICAgZXZlbnQuc3RvcFByb3BhZ2F0aW9uKCk7CiAgICBvcGVuUHJvZHVjdEhyZWYoaHJlZiwgIuyDge2SiCDtjpjsnbTsp4Ag7KO87IaM6rCAIOyXhuyKteuLiOuLpC4iKTsKICB9KTsKICBjZWxsLmFwcGVuZENoaWxkKGJ1dHRvbik7CiAgcmV0dXJuIGNlbGw7Cn0KCmZ1bmN0aW9uIHNldExpbmtlZFRleHQobm9kZSwgdGV4dCwgaHJlZiwgdGl0bGUpIHsKICBpZiAoIW5vZGUpIHJldHVybjsKICBub2RlLnJlcGxhY2VDaGlsZHJlbigpOwogIGNvbnN0IHZhbHVlID0gU3RyaW5nKHRleHQgfHwgIiIpOwogIGlmICghdmFsdWUpIHJldHVybjsKICBpZiAoIWhyZWYpIHsKICAgIG5vZGUudGV4dENvbnRlbnQgPSB2YWx1ZTsKICAgIHJldHVybjsKICB9CiAgY29uc3QgYnV0dG9uID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudCgiYnV0dG9uIik7CiAgYnV0dG9uLnR5cGUgPSAiYnV0dG9uIjsKICBidXR0b24uY2xhc3NOYW1lID0gIm9yZGVyLXByb2R1Y3QtbGluayBwcm9kdWN0LW5vLWxpbmsiOwogIGJ1dHRvbi50ZXh0Q29udGVudCA9IHZhbHVlOwogIGJ1dHRvbi50aXRsZSA9IHRpdGxlIHx8ICLsg4Htkogg7Y6Y7J207KeAIOyXtOq4sCI7CiAgYnV0dG9uLmFkZEV2ZW50TGlzdGVuZXIoImNsaWNrIiwgKGV2ZW50KSA9PiB7CiAgICBldmVudC5wcmV2ZW50RGVmYXVsdCgpOwogICAgZXZlbnQuc3RvcFByb3BhZ2F0aW9uKCk7CiAgICBvcGVuUHJvZHVjdEhyZWYoaHJlZiwgIuyDge2SiCDtjpjsnbTsp4Ag7KO87IaM6rCAIOyXhuyKteuLiOuLpC4iKTsKICB9KTsKICBub2RlLmFwcGVuZENoaWxkKGJ1dHRvbik7Cn0KCg==') + $js.Text.Substring($end)

if ($js.Text -notmatch 'function inquiryOrderCell') {
  $at = $js.Text.IndexOf('function textCell(value)')
  if ($at -lt 0) { Write-Host '[FAIL] app.js: textCell not found. Nothing changed.'; exit 1 }
  $js.Text = $js.Text.Substring(0, $at) + (Dec 'CmZ1bmN0aW9uIGZpbmRPcmRlckJ5TnVtYmVyKG51bWJlciwgbWFya2V0SWQpIHsKICBjb25zdCBubyA9IFN0cmluZyhudW1iZXIgfHwgIiIpLnRyaW0oKTsKICBpZiAoIW5vKSByZXR1cm4gbnVsbDsKICBjb25zdCBtYXRjaGVzID0gKG9yZGVycyB8fCBbXSkuZmlsdGVyKChpdGVtKSA9PiB7CiAgICBjb25zdCBpZHMgPSBbaXRlbS5vcmRlcl9pZCwgaXRlbS5wcm9kdWN0X29yZGVyX2lkXS5tYXAoKHZhbHVlKSA9PiBTdHJpbmcodmFsdWUgfHwgIiIpLnRyaW0oKSk7CiAgICByZXR1cm4gaWRzLmluY2x1ZGVzKG5vKTsKICB9KTsKICBpZiAoIW1hdGNoZXMubGVuZ3RoKSByZXR1cm4gbnVsbDsKICBpZiAobWFya2V0SWQpIHsKICAgIGNvbnN0IGxvY2FsID0gbWF0Y2hlcy5maW5kKChpdGVtKSA9PiBpdGVtLm1hcmtldF9pZCA9PT0gbWFya2V0SWQpOwogICAgaWYgKGxvY2FsKSByZXR1cm4gbG9jYWw7CiAgfQogIHJldHVybiBtYXRjaGVzWzBdOwp9Cgphc3luYyBmdW5jdGlvbiBvcGVuT3JkZXJCeU51bWJlcihudW1iZXIsIG1hcmtldElkKSB7CiAgY29uc3Qgbm8gPSBTdHJpbmcobnVtYmVyIHx8ICIiKS50cmltKCk7CiAgaWYgKCFubykgewogICAgdG9hc3QoIuyjvOusuOuyiO2YuOqwgCDsl4bsirXri4jri6QuIiwgdHJ1ZSk7CiAgICByZXR1cm47CiAgfQogIGxldCBpdGVtID0gZmluZE9yZGVyQnlOdW1iZXIobm8sIG1hcmtldElkKTsKICBpZiAoIWl0ZW0pIHsKICAgIHRyeSB7CiAgICAgIHNldEJ1c3kodHJ1ZSwgIuyjvOusuCDrgrTsmqnsnYQg7LC+64qUIOykkeyeheuLiOuLpC4iKTsKICAgICAgYXdhaXQgbG9hZE9yZGVycyh7IHF1aWV0OiB0cnVlIH0pOwogICAgICBpdGVtID0gZmluZE9yZGVyQnlOdW1iZXIobm8sIG1hcmtldElkKTsKICAgIH0gY2F0Y2ggKGVycm9yKSB7CiAgICAgIHRvYXN0KGVycm9yLm1lc3NhZ2UgfHwgIuyjvOusuOydhCDrtojrn6zsmKTsp4Ag66q77ZaI7Iq164uI64ukLiIsIHRydWUpOwogICAgICByZXR1cm47CiAgICB9IGZpbmFsbHkgewogICAgICBzZXRCdXN5KGZhbHNlKTsKICAgIH0KICB9CiAgaWYgKCFpdGVtKSB7CiAgICB0b2FzdCgi7IiY7KeR65CcIOyjvOusuOyXkOyEnCDsnbQg67KI7Zi466W8IOywvuyngCDrqrvtlojsirXri4jri6QuIOyjvOusuOq0gOumrOyXkOyEnCDrqLzsoIAg7KO866y47J2EIOyImOynke2VtCDso7zshLjsmpQuIiwgdHJ1ZSk7CiAgICByZXR1cm47CiAgfQogIG9wZW5PcmRlckluZm8oaXRlbSk7Cn0KCmZ1bmN0aW9uIGlucXVpcnlPcmRlckNlbGwoaXRlbSkgewogIGNvbnN0IG51bWJlciA9IGl0ZW0ub3JkZXJfaWQgfHwgaXRlbS5wcm9kdWN0X29yZGVyX2lkIHx8ICIiOwogIGlmICghU3RyaW5nKG51bWJlcikudHJpbSgpKSByZXR1cm4gdGV4dENlbGwoIiIpOwogIGNvbnN0IGNlbGwgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KCJ0ZCIpOwogIGNvbnN0IGJ1dHRvbiA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoImJ1dHRvbiIpOwogIGJ1dHRvbi50eXBlID0gImJ1dHRvbiI7CiAgYnV0dG9uLmNsYXNzTmFtZSA9ICJvcmRlci1uby1saW5rIjsKICBidXR0b24udGV4dENvbnRlbnQgPSBudW1iZXI7CiAgYnV0dG9uLnRpdGxlID0gIuyjvOusuCDrgrTsmqkg67O06riwIjsKICBidXR0b24uYWRkRXZlbnRMaXN0ZW5lcigiY2xpY2siLCAoZXZlbnQpID0+IHsKICAgIGV2ZW50LnN0b3BQcm9wYWdhdGlvbigpOwogICAgb3Blbk9yZGVyQnlOdW1iZXIobnVtYmVyLCBpdGVtLm1hcmtldF9pZCkuY2F0Y2goKGVycm9yKSA9PiB0b2FzdChlcnJvci5tZXNzYWdlLCB0cnVlKSk7CiAgfSk7CiAgY2VsbC5hcHBlbmRDaGlsZChidXR0b24pOwogIHJldHVybiBjZWxsOwp9Cgo=') + $js.Text.Substring($at)
}

$rowPat = 'textCell\(inquiryMemo\(item\)\),\s*textCell\(item\.order_id \|\| ""\),'
$rowHits = [regex]::Matches($js.Text, $rowPat)
if ($rowHits.Count -ne 1 -and $js.Text -notmatch 'inquiryOrderCell\(item\)') {
  Write-Host ('[FAIL] app.js: inquiry order cell found ' + $rowHits.Count + ' times. Nothing changed.')
  exit 1
}
if ($rowHits.Count -eq 1) {
  $js.Text = [regex]::Replace($js.Text, $rowPat, "textCell(inquiryMemo(item)),`n      inquiryOrderCell(item),", 1)
}

$js.Text = $js.Text.Replace('button.addEventListener("click", () => openOrderInfo(item));', 'button.addEventListener("click", (event) => { event.stopPropagation(); openOrderInfo(item); });')

$detailPat = '(?s)        const anchor = document\.createElement\("a"\);\s*anchor\.href = href;\s*anchor\.target = "_blank";\s*anchor\.rel = "noopener noreferrer";\s*anchor\.className = "product-no-link";.*?cell\.appendChild\(anchor\);'
$detailHits = [regex]::Matches($js.Text, $detailPat)
if ($detailHits.Count -gt 1) { Write-Host ('[FAIL] app.js: product link block found ' + $detailHits.Count + ' times. Nothing changed.'); exit 1 }
if ($detailHits.Count -eq 1) {
  $js.Text = [regex]::Replace($js.Text, $detailPat, (Dec 'ICAgICAgICBjb25zdCBidXR0b24gPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KCJidXR0b24iKTsKICAgICAgICBidXR0b24udHlwZSA9ICJidXR0b24iOwogICAgICAgIGJ1dHRvbi5jbGFzc05hbWUgPSAib3JkZXItcHJvZHVjdC1saW5rIHByb2R1Y3Qtbm8tbGluayI7CiAgICAgICAgYnV0dG9uLnRleHRDb250ZW50ID0gdGV4dDsKICAgICAgICBidXR0b24udGl0bGUgPSAi7Iqk66eI7Yq47Iqk7Yag7Ja0IOyDge2SiCDtjpjsnbTsp4AiOwogICAgICAgIGJ1dHRvbi5hZGRFdmVudExpc3RlbmVyKCJjbGljayIsIChldmVudCkgPT4gewogICAgICAgICAgZXZlbnQucHJldmVudERlZmF1bHQoKTsKICAgICAgICAgIGV2ZW50LnN0b3BQcm9wYWdhdGlvbigpOwogICAgICAgICAgb3BlblByb2R1Y3RIcmVmKGhyZWYsICLsg4Htkogg7Y6Y7J207KeAIOyjvOyGjOqwgCDsl4bsirXri4jri6QuIik7CiAgICAgICAgfSk7CiAgICAgICAgY2VsbC5hcHBlbmRDaGlsZChidXR0b24pOw==').TrimEnd(), 1)
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
Copy-Item -LiteralPath $js.Path -Destination ($js.Path + '.bak-' + $stamp)
Write-Doc $js
Write-Host ('[OK] app.js patched (backup .bak-' + $stamp + ')')
Write-Host ''
Write-Host '[OK] Done. In the MODUMODU browser window press Ctrl+Shift+R.'
