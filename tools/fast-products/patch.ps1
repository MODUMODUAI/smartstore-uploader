$ErrorActionPreference = 'Stop'
$root = 'C:\smartstore uploader'
if ($args.Count -gt 0) { $root = $args[0] }
$js = Join-Path $root 'app\static\app.js'
$css = Join-Path $root 'app\static\styles.css'
Write-Host '========================================'
Write-Host ' MODUMODU patch: fast product list + dark text'
Write-Host '========================================'
if (-not (Test-Path -LiteralPath $js)) { Write-Host ('[FAIL] not found: ' + $js); exit 1 }

function Read-Text([string]$path) {
  $bytes = [IO.File]::ReadAllBytes($path)
  $bom = $bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF
  return @{ Text = (New-Object Text.UTF8Encoding($false)).GetString($bytes, $(if ($bom) { 3 } else { 0 }), $bytes.Length - $(if ($bom) { 3 } else { 0 })); Bom = $bom }
}
function Write-Text([string]$path, $doc, [string]$text) {
  [IO.File]::WriteAllText($path, $text, (New-Object Text.UTF8Encoding($doc.Bom)))
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$block = @'
const PRODUCT_CACHE_DB = "modumodu-product-cache";
const PRODUCT_CACHE_STORE = "products";
const PRODUCT_FULL_RELOAD_LIMIT = 150;
const productCache = new Map();
let productCacheReady = null;

function openProductCacheDb() {
  return new Promise((resolve) => {
    if (!window.indexedDB) {
      resolve(null);
      return;
    }
    let request;
    try {
      request = indexedDB.open(PRODUCT_CACHE_DB, 1);
    } catch {
      resolve(null);
      return;
    }
    request.onupgradeneeded = () => request.result.createObjectStore(PRODUCT_CACHE_STORE);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => resolve(null);
    request.onblocked = () => resolve(null);
  });
}

async function readProductCache() {
  const db = await openProductCacheDb();
  if (!db) return;
  await new Promise((resolve) => {
    const tx = db.transaction(PRODUCT_CACHE_STORE, "readonly");
    const request = tx.objectStore(PRODUCT_CACHE_STORE).openCursor();
    request.onsuccess = () => {
      const cursor = request.result;
      if (!cursor) return;
      if (cursor.value?.product) productCache.set(cursor.key, cursor.value);
      cursor.continue();
    };
    tx.oncomplete = resolve;
    tx.onerror = resolve;
    tx.onabort = resolve;
  });
  db.close();
}

async function writeProductCache(changedIds, removedIds) {
  if (!changedIds.length && !removedIds.length) return;
  const db = await openProductCacheDb();
  if (!db) return;
  await new Promise((resolve) => {
    const tx = db.transaction(PRODUCT_CACHE_STORE, "readwrite");
    const store = tx.objectStore(PRODUCT_CACHE_STORE);
    changedIds.forEach((id) => {
      const entry = productCache.get(id);
      if (entry) store.put(entry, id);
    });
    removedIds.forEach((id) => store.delete(id));
    tx.oncomplete = resolve;
    tx.onerror = resolve;
    tx.onabort = resolve;
  });
  db.close();
}

async function runLimited(items, limit, worker) {
  let next = 0;
  const lanes = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (next < items.length) {
      const item = items[next++];
      await worker(item);
    }
  });
  await Promise.all(lanes);
}

// /api/products?full=1 re-reads every product file on each call; reuse full copies whose summary row is unchanged.
async function fetchProductList() {
  const summaries = await api("/api/products");
  if (!Array.isArray(summaries)) return api("/api/products?full=1");
  if (!productCacheReady) productCacheReady = readProductCache().catch(() => {});
  await productCacheReady;
  const sigs = new Map(summaries.map((item) => [item.id, JSON.stringify(item)]));
  const stale = summaries.filter((item) => productCache.get(item.id)?.sig !== sigs.get(item.id)).map((item) => item.id);
  const changed = [];
  if (stale.length > PRODUCT_FULL_RELOAD_LIMIT) {
    const full = await api("/api/products?full=1");
    full.forEach((product) => {
      if (!sigs.has(product.id)) return;
      productCache.set(product.id, { sig: sigs.get(product.id), product });
      changed.push(product.id);
    });
  } else {
    await runLimited(stale, 6, async (id) => {
      try {
        const product = await api(`/api/products/${id}`, { quiet: true });
        productCache.set(id, { sig: sigs.get(id), product });
        changed.push(id);
      } catch {
        productCache.delete(id);
      }
    });
  }
  const removed = [...productCache.keys()].filter((id) => !sigs.has(id));
  removed.forEach((id) => productCache.delete(id));
  writeProductCache(changed, removed).catch(() => {});
  return summaries
    .filter((item) => productCache.has(item.id))
    .map((item) => structuredClone(productCache.get(item.id).product));
}

async function refreshCachedProduct(id) {
  const entry = productCache.get(id);
  if (!entry) return;
  let fresh;
  try {
    fresh = await api(`/api/products/${id}`, { quiet: true });
  } catch {
    return;
  }
  if (JSON.stringify(fresh) === JSON.stringify(entry.product)) return;
  productCache.set(id, { sig: entry.sig, product: fresh });
  writeProductCache([id], []).catch(() => {});
  const index = products.findIndex((item) => item.id === id);
  if (index >= 0) products[index] = structuredClone(fresh);
  if (current?.id === id) {
    current = products[index] || structuredClone(fresh);
    fillPreview();
  }
}


'@
$cssBlock = @'
html[data-theme="dark"] button.stop-job { background: #471f22; color: #eea5a0; }
html[data-theme="dark"] button.stop-job:disabled { background: #452121; color: var(--text); }
html[data-theme="dark"] .titlebar .brand-a { color: #8bbdee; }
html[data-theme="dark"] .titlebar .brand-ai { color: #8bbdee; }
html[data-theme="dark"] .product-status-filters button[data-status-filter="error"] strong { color: #ee8c8c; }
html[data-theme="dark"] .product-status-filters button[data-status-filter="registered"] strong { color: #8beecd; }
html[data-theme="dark"] .product-status-filters button[data-status-filter="waiting"] strong { color: #eec48b; }
html[data-theme="dark"] #registerButton:disabled,
html[data-theme="dark"] .context-menu > button[data-action="register"]:disabled { background: #1f4730; color: #a0eec0; }
html[data-theme="dark"] button.tool-danger { color: #ee928b; }
html[data-theme="dark"] .arrival-notice strong { color: #8bbdee; }
html[data-theme="dark"] .help-body a { color: #8bc2ee; }
html[data-theme="dark"] .setup-help-links a { color: #8bc2ee; }
html[data-theme="dark"] .ownerclan-parent.active { color: #8ba8ee; }
html[data-theme="dark"] .ownerclan-child.picked,
html[data-theme="dark"] .ownerclan-child.viewing { color: #8ba8ee; }
html[data-theme="dark"] #ownerclanSelectAll { background: #1f3247; color: #a0c7ee; }
html[data-theme="dark"] .ownerclan-page-num.active { color: #8bc2ee; }
html[data-theme="dark"] .ownerclan-product .sale { color: #ee8b9a; }
html[data-theme="dark"] .order-detail-table td.emphasis { color: #ee8b8b; }
html[data-theme="dark"] .order-status-new { color: #ee8bc3; }
html[data-theme="dark"] .grid td.emphasis { color: #ee8b8b; }
html[data-theme="dark"] .order-detail-table a { color: #8baaee; }
html[data-theme="dark"] #orderTable tr.order-current { background: #1f3047; color: var(--text); }
html[data-theme="dark"] .cs-memo-title { background: #1f3347; color: var(--text); }
html[data-theme="dark"] .cs-status-open { color: #90e9a3; }
html[data-theme="dark"] .cs-status-done { color: #8baaee; }
html[data-theme="dark"] .cs-status-ready { color: #eeb68b; }
html[data-theme="dark"] .cs-link { color: #8baaee; }
html[data-theme="dark"] tr.order-current .order-cancel-link,
html[data-theme="dark"] tr.selected .order-cancel-link { color: #8baaee; }
html[data-theme="dark"] .order-info-table th { background: #272f3f; color: var(--text); }
html[data-theme="dark"] .order-menu-panel button:hover { background: #1f2f47; color: var(--text); }
html[data-theme="dark"] .replace-warn { color: #ee8b8b; }
html[data-theme="dark"] .excel-add-head p { color: #b4bac5; }
html[data-theme="dark"] .excel-add-fields label,
html[data-theme="dark"] .excel-add-label { color: #adb9cc; }
html[data-theme="dark"] #excelColumnTable tr.excel-row-current td { background: #1f2e47; color: var(--text); }
html[data-theme="dark"] .excel-separator-row label { color: #b4bac5; }
html[data-theme="dark"] .excel-export-dialog { background: #1f2c47; color: #bbc2d3; }
html[data-theme="dark"] .excel-export-kicker { color: #b4b9c5; }
html[data-theme="dark"] .excel-export-head p { color: #b4bac5; }
html[data-theme="dark"] .excel-autosave { color: #8beeaf; }
html[data-theme="dark"] .excel-export-help { color: #adb8cc; }
html[data-theme="dark"] .excel-target.active { background: #1f2c47; color: var(--text); }
html[data-theme="dark"] .excel-target small,
html[data-theme="dark"] .excel-card .hint { color: #b4b9c5; }
html[data-theme="dark"] .excel-form-picked { color: #8beeaf; }
html[data-theme="dark"] .excel-file-label { color: #b4bac5; }
html[data-theme="dark"] .excel-file-name em { color: #b4bac5; }
html[data-theme="dark"] .excel-preview-list dt { color: #b4bac5; }
html[data-theme="dark"] .excel-file-note { background: #47391f; color: #eed4a0; }
html[data-theme="dark"] .inquiry-page { background: #2c313a; color: var(--text); }
html[data-theme="dark"] .inquiry-notice select { background: #47241f; color: #eea5a0; }
html[data-theme="dark"] .inquiry-periods button.active { background: #1f2f47; color: #a0b4ee; }
html[data-theme="dark"] .inquiry-warn { background: #473f1f; color: #c7c7c7; }
html[data-theme="dark"] .inquiry-form textarea,
html[data-theme="dark"] .inquiry-old textarea,
html[data-theme="dark"] .inquiry-new textarea,
html[data-theme="dark"] .inquiry-batch textarea { background: #1f2d47; color: var(--text); }
html[data-theme="dark"] .inquiry-old,
html[data-theme="dark"] .inquiry-new { background: #473f1f; color: var(--text); }
html[data-theme="dark"] #inquiryGrid a { color: #8baaee; }
html[data-theme="dark"] .grid tr.collected-row { color: #8beecd; }
html[data-theme="dark"] .grid th.sortable.sort-asc::after { color: #8bc2ee; }
html[data-theme="dark"] .grid th.sortable.sort-desc::after { color: #8bc2ee; }
html[data-theme="dark"] .job-spinner p { background: #333333; color: var(--text); }
html[data-theme="dark"] .image-text-job { color: #8eafeb; }
html[data-theme="dark"] .log-box li.ok { color: #8beecd; }
html[data-theme="dark"] .log-box li.err { color: #ee928b; }
html[data-theme="dark"] .result-box { background: #1f4736; color: #a0eed4; }
html[data-theme="dark"] .name-mode-choices button span { color: #bdbdbd; }
html[data-theme="dark"] .name-suggest-keywords span { background: #1f2f47; color: var(--text); }
html[data-theme="dark"] .name-suggest-keywords em { color: #9fdbb7; }
html[data-theme="dark"] .notice-item img { background: #333333; color: var(--text); }
html[data-theme="dark"] .pick-list li:hover { background: #1f3047; color: var(--text); }
html[data-theme="dark"] .attribute-table .attribute-section th { background: #333333; color: var(--text); }
html[data-theme="dark"] .detail-sep { background: #333333; color: var(--text); }
html[data-theme="dark"] .detail-size-menu button:hover { background: #1f2d47; color: var(--text); }
html[data-theme="dark"] .benefit-note { color: #8beecd; }
html[data-theme="dark"] .delivery-delete { color: #ee928b; }
html[data-theme="dark"] .tag-chip:hover { background: #471f1f; color: #eea5a0; }
html[data-theme="dark"] .tag-help { color: #8beecd; }
html[data-theme="dark"] .tag-chip-on:hover { background: #1f472e; color: #a0eed4; }
html[data-theme="dark"] .image-drop.dragover { background: #1f3247; color: var(--text); }
html[data-theme="dark"] .price-actions button.is-on { background: #333333; color: var(--text); }
html[data-theme="dark"] .app-quit { background: #471f1f; color: #eea5a0; }
html[data-theme="dark"] .app-quit:hover:not(:disabled) { background: #471f1f; color: var(--text); }
html[data-theme="dark"] .share-link-url { color: #8bc2ee; }
html[data-theme="dark"] .job-spinner-ring { border-color: #3a4a5c; border-top-color: #4ea1ff; box-shadow: 0 0 0 6px rgba(0, 0, 0, 0.55); }
html[data-theme="dark"] .job-spinner p { border-color: #555; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.5); }
'@

$doc = Read-Text $js
$text = $doc.Text
if ($text.Contains('function fetchProductList')) {
  Write-Host '[1] app.js already patched'
} else {
  $nl = "`n"
  if ($text.Contains("`r`n")) { $nl = "`r`n" }
  $old = 'products = await api("/api/products?full=1");'
  $count = ([regex]::Matches($text, [regex]::Escape($old))).Count
  if ($count -ne 1) { Write-Host ('[FAIL] app.js: product load line found ' + $count + ' times. Nothing changed.'); exit 1 }
  $pattern = '(async function selectProduct\(id, rerender = true, additive = false\) \{\r?\n(\s*)current = products\.find\(\(item\) => item\.id === id\) \|\| await api\(`/api/products/\$\{id\}`\);)'
  $m = [regex]::Matches($text, $pattern)
  if ($m.Count -ne 1) { Write-Host '[FAIL] app.js: selectProduct not matched. Nothing changed.'; exit 1 }
  Copy-Item -LiteralPath $js -Destination ($js + '.bak-' + $stamp)
  $text = $text.Replace($old, 'products = await fetchProductList();')
  $insert = ($block -replace "`r?`n", $nl)
  $match = [regex]::Match($text, $pattern)
  $text = $text.Substring(0, $match.Index) + $insert + $match.Value + $nl + $match.Groups[2].Value + 'refreshCachedProduct(id);' + $text.Substring($match.Index + $match.Length)
  Write-Text $js $doc $text
  Write-Host ('[1] app.js patched (backup: app.js.bak-' + $stamp + ')')
}

if (Test-Path -LiteralPath $css) {
  $cdoc = Read-Text $css
  if ($cdoc.Text.Contains('/* dark-contrast-fix */')) {
    Write-Host '[2] styles.css already patched'
  } else {
    Copy-Item -LiteralPath $css -Destination ($css + '.bak-' + $stamp)
    $nl = "`n"
    if ($cdoc.Text.Contains("`r`n")) { $nl = "`r`n" }
    $add = $nl + '/* dark-contrast-fix */' + $nl + ($cssBlock -replace "`r?`n", $nl)
    Write-Text $css $cdoc ($cdoc.Text.TrimEnd() + $nl + $add)
    Write-Host ('[2] styles.css patched (backup: styles.css.bak-' + $stamp + ')')
  }
}
Write-Host ''
Write-Host '[OK] Done. In the MODUMODU browser window press Ctrl+Shift+R.'
Write-Host 'First load is slow once; after that the product list is fast.'
