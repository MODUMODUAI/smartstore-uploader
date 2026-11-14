/* product-manage-fix1 */
// index.html 에서 app-extra-products.js 다음에 불러야 합니다.
// 상품관리 공급처 필터, 케이페이지 완박스 배송비, 이미 등록된 상품의 배송비 재등록.
// 공급처를 고르면 그 공급처 상품이 보여야 하고, 전체는 전부 보여야 합니다.
// 완박스 배송비가 한 금액이면 그 금액을, 범위면 앞 금액만 씁니다.
// 이미 등록된 상품을 다시 등록할 때는 배송비만 바꿉니다. 상품명과 다른 항목은 건드리지 않습니다.

function normalizeSupplierName(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/\s+/g, "")
    .replace(/[()[\]{}._\-/]/g, "");
}

function supplierHost(url) {
  try {
    return new URL(String(url || "")).hostname.toLowerCase();
  } catch (error) {
    return "";
  }
}

function supplierHostsMatch(left, right) {
  if (!left || !right) return false;
  return left === right || left.endsWith(`.${right}`) || right.endsWith(`.${left}`);
}

function supplierRecord(filter, wholesalers) {
  const selected = String(filter || "");
  return (Array.isArray(wholesalers) ? wholesalers : []).find((row) => String(row && row.id) === selected) || null;
}

function productSupplierNames(item) {
  if (!item || typeof item !== "object") return [];
  return [item.wholesale_name, item.supplier_name, item.wholesaler_name, item.vendor_name];
}

function supplierNameMatches(item, supplier) {
  const wanted = normalizeSupplierName(supplier && supplier.name);
  if (!wanted) return false;
  return productSupplierNames(item).some((name) => {
    const got = normalizeSupplierName(name);
    if (!got) return false;
    if (got === wanted) return true;
    const shorter = Math.min(got.length, wanted.length);
    if (shorter < 4) return false;
    return got.includes(wanted) || wanted.includes(got);
  });
}

function supplierUrlMatches(item, supplier) {
  const productHost = supplierHost(item && (item.source_url || item.url || item.market_url));
  const shopHost = supplierHost(supplier && supplier.url);
  return supplierHostsMatch(productHost, shopHost);
}

function supplierMatchesProduct(item, filter, wholesalers) {
  const selected = String(filter || "");
  if (!selected || selected === "all") return true;
  const rows = Array.isArray(wholesalers) ? wholesalers : [];
  const known = new Set(rows.map((row) => String(row && row.id)));
  const saved = String(item && item.wholesale_id || "").trim();
  if (selected === "url") {
    if (saved && known.has(saved)) return false;
    if (saved) return false;
    return !rows.some((row) => supplierUrlMatches(item, row) || supplierNameMatches(item, row));
  }
  if (saved && saved === selected) return true;
  if (saved && known.has(saved)) return false;
  const supplier = supplierRecord(selected, rows);
  if (!supplier) return false;
  return supplierNameMatches(item, supplier) || supplierUrlMatches(item, supplier);
}

function supplierFilterRows(items, filter, wholesalers) {
  const rows = Array.isArray(items) ? items : [];
  const selected = String(filter || "all");
  if (!selected || selected === "all") return rows.slice();
  return rows.filter((item) => supplierMatchesProduct(item, selected, wholesalers));
}

function kpageBoxShippingFee(text) {
  const source = String(text || "");
  const marker = source.search(/완박스\s*배송비/);
  if (marker < 0) return null;
  const label = source.slice(marker).match(/완박스\s*배송비/);
  const tail = source.slice(marker + label[0].length, marker + label[0].length + 80);
  const match = tail.match(/(\d{1,3}(?:,\d{3})+|\d+)\s*원/);
  if (!match) return null;
  const amount = Number(match[1].replace(/,/g, ""));
  if (!Number.isFinite(amount) || amount < 0) return null;
  return Math.round(amount);
}

function kpageTextFrom(value, depth, seen) {
  if (value == null || depth > 4) return "";
  if (typeof value === "string") return value.includes("완박스") ? value : "";
  if (typeof value !== "object") return "";
  if (seen.has(value)) return "";
  seen.add(value);
  const parts = [];
  if (Array.isArray(value)) {
    value.forEach((entry) => {
      const text = kpageTextFrom(entry, depth + 1, seen);
      if (text) parts.push(text);
    });
    return parts.join("\n");
  }
  Object.keys(value).forEach((key) => {
    if (key === "images" || key === "image" || key === "thumbnail") return;
    const text = kpageTextFrom(value[key], depth + 1, seen);
    if (text) parts.push(text);
  });
  return parts.join("\n");
}

function kpageFeeFromProduct(item) {
  return kpageBoxShippingFee(kpageTextFrom(item, 0, new Set()));
}

function isAlreadyRegistered(item) {
  if (!item || typeof item !== "object") return false;
  if (String(item.origin_product_no || "").trim()) return true;
  if (String(item.channel_product_no || "").trim()) return true;
  return String(item.status || "") === "registered";
}

function shippingOnlyPatch(fee) {
  const amount = typeof fee === "number"
    ? fee
    : Number(String(fee == null ? "" : fee).replace(/,/g, "").replace(/원/g, "").trim());
  if (!Number.isFinite(amount) || amount < 0) {
    throw new Error("배송비를 숫자로 입력해 주세요.");
  }
  return { shipping_fee: Math.round(amount) };
}

function applyShippingPatch(product, fee) {
  const patch = shippingOnlyPatch(fee);
  const next = Object.assign({}, product, patch);
  Object.keys(patch).forEach((key) => {
    if (key !== "shipping_fee") delete next[key];
  });
  return { patch, product: next };
}

function splitReregister(items) {
  const rows = Array.isArray(items) ? items : [];
  return {
    registered: rows.filter((item) => isAlreadyRegistered(item)),
    fresh: rows.filter((item) => !isAlreadyRegistered(item)),
  };
}

function readBinding(name) {
  try {
    return (0, eval)(name);
  } catch (error) {
    return globalThis[name];
  }
}

function writeBinding(name, value) {
  globalThis.__pmAssign = value;
  try {
    (0, eval)(`${name} = globalThis.__pmAssign`);
  } catch (error) {}
  try {
    globalThis[name] = value;
  } catch (error) {}
  delete globalThis.__pmAssign;
}

function installSupplierFilter() {
  function wrap(name) {
    const original = readBinding(name);
    if (typeof original !== "function" || original.productManageFix) return;
    const wrapped = function supplierFiltered() {
      const filter = String(readBinding("productFilter") || "all");
      if (!filter || filter === "all" || filter === "url") return original.apply(this, arguments);
      const previous = readBinding("productFilter");
      writeBinding("productFilter", "all");
      let rows;
      try {
        rows = original.apply(this, arguments);
      } finally {
        writeBinding("productFilter", previous);
      }
      return supplierFilterRows(rows, filter, readBinding("wholesalers"));
    };
    wrapped.productManageFix = true;
    writeBinding(name, wrapped);
  }
  wrap("scopedProducts");
  wrap("currentMarketStatusRows");
}

function installKpageFee() {
  const original = readBinding("wholesaleShipAmount");
  if (typeof original === "function" && !original.productManageFix) {
    const wrapped = function kpageShipAmount(item) {
      if (item && item._shipManual) return original.apply(this, arguments);
      const parsed = kpageFeeFromProduct(item);
      if (parsed != null) return parsed;
      return original.apply(this, arguments);
    };
    wrapped.productManageFix = true;
    writeBinding("wholesaleShipAmount", wrapped);
  }
  ["loadProducts", "ensureProductFull"].forEach((name) => {
    const inner = readBinding(name);
    if (typeof inner !== "function" || inner.productManageFix) return;
    const wrapped = async function persistAfterLoad() {
      const result = await inner.apply(this, arguments);
      if (name === "ensureProductFull") await persistKpageFee(result);
      else await persistKpageFees();
      return result;
    };
    wrapped.productManageFix = true;
    writeBinding(name, wrapped);
  });
}

function manualShipLocked(item) {
  if (!item || item._shipManual) return true;
  try {
    const stored = localStorage.getItem(`modumodu-manual-ship:${item.id}`);
    return stored != null && stored !== "";
  } catch (error) {
    return false;
  }
}

function keepOtherFields(item, before, fee) {
  const products = readBinding("products");
  const index = Array.isArray(products) ? products.findIndex((row) => row && row.id === item.id) : -1;
  const current = index >= 0 ? products[index] : item;
  Object.keys(before).forEach((key) => {
    if (key === "shipping_fee" || key === "_shipManual") return;
    current[key] = before[key];
  });
  current.shipping_fee = fee;
  if (before.name !== undefined) current.name = before.name;
  return current;
}

async function persistKpageFee(item) {
  if (!item || manualShipLocked(item)) return item;
  const parsed = kpageFeeFromProduct(item);
  if (parsed == null || Number(item.shipping_fee) === parsed) return item;
  const plan = applyShippingPatch(item, parsed);
  const before = Object.assign({}, item);
  item.shipping_fee = plan.patch.shipping_fee;
  const isMasterProduct = readBinding("isMasterProduct");
  const master = typeof isMasterProduct === "function" && isMasterProduct(item);
  const saveProduct = readBinding("saveProduct");
  if (!master && typeof saveProduct === "function") {
    try {
      await saveProduct(item, plan.patch, true);
    } catch (error) {}
  }
  return keepOtherFields(item, before, plan.patch.shipping_fee);
}

async function persistKpageFees() {
  const products = readBinding("products");
  if (!Array.isArray(products)) return;
  for (const item of products) await persistKpageFee(item);
}

function rememberManualShip(item, amount) {
  item.shipping_fee = amount;
  item._shipManual = true;
  try {
    localStorage.setItem(`modumodu-manual-ship:${item.id}`, String(amount));
  } catch (error) {}
}

async function applyShippingReregister(item, fee) {
  const plan = applyShippingPatch(item, fee);
  const name = item.name;
  const before = Object.assign({}, item);
  rememberManualShip(item, plan.patch.shipping_fee);
  const isMasterProduct = readBinding("isMasterProduct");
  const master = typeof isMasterProduct === "function" && isMasterProduct(item);
  const saveProduct = readBinding("saveProduct");
  if (!master && typeof saveProduct === "function") {
    try {
      await saveProduct(item, plan.patch, true);
    } catch (error) {
      const toast = readBinding("toast");
      if (typeof toast === "function") toast(error.message || "배송비를 저장하지 못했습니다.", true);
    }
  }
  const current = keepOtherFields(item, before, plan.patch.shipping_fee);
  current._shipManual = true;
  if (current.name !== name) current.name = name;
  const renderProductSheet = readBinding("renderProductSheet");
  if (typeof renderProductSheet === "function") renderProductSheet();
  return plan;
}

function askShippingFee(items) {
  const documentRef = typeof document !== "undefined" ? document : null;
  if (!documentRef) return Promise.resolve(null);
  return new Promise((resolve) => {
    let dialog = documentRef.getElementById("shippingReregisterDialog");
    if (!dialog) {
      dialog = documentRef.createElement("dialog");
      dialog.id = "shippingReregisterDialog";
      dialog.innerHTML = [
        "<form method=\"dialog\" autocomplete=\"off\">",
        "<header><h2>배송비 다시 등록</h2></header>",
        "<p class=\"hint\" id=\"shippingReregisterCount\"></p>",
        "<p class=\"register-choice-rule\">이미 등록된 상품은 배송비만 바꿉니다. 상품명과 다른 내용은 바꾸지 않습니다.</p>",
        "<label class=\"register-choice-label\" for=\"shippingReregisterFee\">배송비</label>",
        "<input id=\"shippingReregisterFee\" name=\"shipping_fee\" inputmode=\"numeric\" autocomplete=\"off\" />",
        "<p id=\"shippingReregisterMessage\" class=\"hint\"></p>",
        "<div class=\"delivery-actions\">",
        "<button type=\"submit\" class=\"btn-naver-register\" value=\"ok\">배송비 등록</button>",
        "<button type=\"button\" data-cancel>취소</button>",
        "</div></form>",
      ].join("");
      documentRef.body.appendChild(dialog);
    }
    const input = dialog.querySelector("#shippingReregisterFee");
    const message = dialog.querySelector("#shippingReregisterMessage");
    const count = dialog.querySelector("#shippingReregisterCount");
    const first = items[0] || {};
    const parsed = kpageFeeFromProduct(first);
    const shown = parsed != null ? parsed : first.shipping_fee;
    input.value = shown == null || shown === "" ? "" : String(shown);
    message.textContent = "";
    count.textContent = items.length > 1
      ? `선택한 등록 상품 ${items.length}개의 배송비만 다시 등록합니다.`
      : "이미 등록된 상품의 배송비만 다시 등록합니다.";
    const form = dialog.querySelector("form");
    const cancel = dialog.querySelector("[data-cancel]");
    let settled = false;
    const finish = (value) => {
      if (settled) return;
      settled = true;
      dialog.close();
      resolve(value);
    };
    form.onsubmit = (event) => {
      event.preventDefault();
      try {
        finish(shippingOnlyPatch(input.value).shipping_fee);
      } catch (error) {
        message.textContent = error.message;
      }
    };
    cancel.onclick = () => finish(null);
    dialog.oncancel = (event) => {
      event.preventDefault();
      finish(null);
    };
    dialog.showModal();
    input.focus();
    if (typeof input.select === "function") input.select();
  });
}

function installShippingReregister() {
  const original = readBinding("registerSelected");
  if (typeof original !== "function" || original.productManageFix) return;
  const wrapped = async function shippingReregister() {
    const requireSelected = readBinding("requireSelected");
    const items = typeof requireSelected === "function" ? requireSelected() : [];
    if (!items.length) return original.apply(this, arguments);
    const parts = splitReregister(items);
    if (!parts.registered.length) return original.apply(this, arguments);
    const fee = await askShippingFee(parts.registered);
    if (fee == null) return;
    for (const item of parts.registered) await applyShippingReregister(item, fee);
    const toast = readBinding("toast");
    if (!parts.fresh.length) {
      if (typeof toast === "function") {
        toast(parts.registered.length > 1
          ? `등록 상품 ${parts.registered.length}개의 배송비만 바꿨습니다.`
          : "배송비만 다시 등록했습니다.");
      }
      return;
    }
    const selectedIds = readBinding("selectedIds");
    const snapshot = selectedIds instanceof Set ? Array.from(selectedIds) : null;
    if (snapshot) writeBinding("selectedIds", new Set(parts.fresh.map((item) => item.id)));
    try {
      return await original.apply(this, arguments);
    } finally {
      if (snapshot) writeBinding("selectedIds", new Set(snapshot));
    }
  };
  wrapped.productManageFix = true;
  writeBinding("registerSelected", wrapped);
}

function installProductManageFix() {
  installSupplierFilter();
  installKpageFee();
  installShippingReregister();
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    normalizeSupplierName,
    supplierMatchesProduct,
    supplierFilterRows,
    kpageBoxShippingFee,
    kpageFeeFromProduct,
    isAlreadyRegistered,
    shippingOnlyPatch,
    applyShippingPatch,
    splitReregister,
    installProductManageFix,
  };
}

if (typeof document !== "undefined") installProductManageFix();
