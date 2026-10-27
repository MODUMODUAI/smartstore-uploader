$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$root = 'C:\smartstore uploader'
if ($args.Count -gt 0) { $root = $args[0] }
$static = Join-Path $root 'app\static'
Write-Host '========================================'
Write-Host ' MODUMODU patch: inquiry answer + send button'
Write-Host '========================================'
if (-not (Test-Path -LiteralPath $static)) { Write-Host ('[FAIL] not found: ' + $static); exit 1 }

$utf8 = New-Object Text.UTF8Encoding($false)
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

# --- index.html: replace old/new answer blocks ---
$htmlOld = [regex]::Match($idx.Text, '(?s)<div class="inquiry-old">\s*<label>답변내용<textarea id="inquiryAnswerView"[^>]*>.*?</textarea></label>\s*<label>답변일<input id="inquiryAnswerAt"[^>]*/?>\s*</label>\s*</div>\s*<div class="inquiry-new">\s*<label>새 답변 제목<input id="inquiryAnswerTitle"[^>]*/?>\s*</label>\s*<label>새 답변 내용<textarea id="inquiryAnswerDraft"[^>]*>.*?</textarea></label>\s*</div>')
if (-not $htmlOld.Success) {
  Write-Host '[FAIL] index.html: inquiry old/new block not found. Nothing changed.'
  exit 1
}
$htmlNew = @"
            <div class="inquiry-new inquiry-answer-box">
              <label>답변 제목<input id="inquiryAnswerTitle" autocomplete="off" /></label>
              <label>답변내용 (여기에 입력)<textarea id="inquiryAnswerDraft" placeholder="여기에 답변을 입력하세요"></textarea></label>
            </div>
            <div class="inquiry-old" id="inquiryOldWrap" hidden>
              <label>보낸 답변<textarea id="inquiryAnswerView" readonly tabindex="-1"></textarea></label>
              <label>답변일<input id="inquiryAnswerAt" readonly tabindex="-1" /></label>
            </div>
"@
$idx.Text = $idx.Text.Substring(0, $htmlOld.Index) + $htmlNew.TrimEnd() + $idx.Text.Substring($htmlOld.Index + $htmlOld.Length)

# button label -> 답변 보내기(S) if present
$btn = [regex]::Match($idx.Text, '<button type="button" id="inquiryAnswerButton"[^>]*>.*?</button>')
if (-not $btn.Success) { Write-Host '[FAIL] index.html: send button not found. Nothing changed.'; exit 1 }
$idx.Text = $idx.Text.Substring(0, $btn.Index) + '<button type="button" id="inquiryAnswerButton" accesskey="s">답변 보내기(S)</button>' + $idx.Text.Substring($btn.Index + $btn.Length)

# --- app.js: show/hide old answer + focus draft ---
$jsPat = '(?s)if \(\$\("#inquiryAnswerView"\)\) \$\("#inquiryAnswerView"\)\.value = item\.answer \|\| "";\s*if \(\$\("#inquiryAnswerAt"\)\) \$\("#inquiryAnswerAt"\)\.value = item\.answer_at \? formatOrderDate\(item\.answer_at\) : "";\s*if \(!same\) \{\s*if \(\$\("#inquiryAnswerTitle"\)\) \$\("#inquiryAnswerTitle"\)\.value = "";\s*if \(\$\("#inquiryAnswerDraft"\)\) \$\("#inquiryAnswerDraft"\)\.value = "";\s*\}'
$jsM = [regex]::Match($js.Text, $jsPat)
if (-not $jsM.Success) {
  Write-Host '[FAIL] app.js: fillInquiryDetail answer block not found. Nothing changed.'
  exit 1
}
$jsNew = @'
  if ($("#inquiryAnswerView")) $("#inquiryAnswerView").value = item.answer || "";
  if ($("#inquiryAnswerAt")) $("#inquiryAnswerAt").value = item.answer_at ? formatOrderDate(item.answer_at) : "";
  const answered = Boolean(String(item.answer || "").trim());
  if ($("#inquiryOldWrap")) $("#inquiryOldWrap").hidden = !answered;
  $("#inquiryPaneBasic")?.classList.toggle("inquiry-no-old", !answered);
  if (!same) {
    if ($("#inquiryAnswerTitle")) $("#inquiryAnswerTitle").value = "";
    if ($("#inquiryAnswerDraft")) $("#inquiryAnswerDraft").value = "";
    const batch = $("#inquiryPaneBatch") && !$("#inquiryPaneBatch").hidden;
    const target = batch ? $("#inquiryBatchBody") : $("#inquiryAnswerDraft");
    requestAnimationFrame(() => target?.focus({ preventScroll: true }));
  }
'@
$js.Text = $js.Text.Substring(0, $jsM.Index) + $jsNew.TrimEnd() + $js.Text.Substring($jsM.Index + $jsM.Length)

# --- styles.css: center sticky send button + layout ---
if ($css.Text -notmatch 'inquiry-no-old') {
  $css.Text = $css.Text.TrimEnd() + @"

/* inquiry-answer-fix */
.inquiry-old[hidden] { display: none; }
.inquiry-sheet.inquiry-no-old { grid-template-columns: minmax(420px, 1.3fr) minmax(260px, 1.2fr); }
.inquiry-answer-box textarea { min-height: 170px; }
.inquiry-detail-foot {
  display: flex !important;
  justify-content: center;
  align-items: center;
  gap: 8px;
  position: sticky;
  bottom: -10px;
  z-index: 2;
  padding: 6px 0;
  background: var(--surface);
}
.inquiry-detail-foot #inquiryTemplate {
  position: absolute;
  left: 0;
  width: min(360px, 45%);
}
#inquiryAnswerButton {
  min-width: 160px;
  padding: 7px 28px;
  font-size: 14px;
}
#inquiryAnswerDraft,
#inquiryBatchBody,
#inquiryAnswerTitle,
#inquiryBatchTitle {
  pointer-events: auto !important;
  user-select: text !important;
  -webkit-user-select: text !important;
}
"@
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
