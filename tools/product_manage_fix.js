/* product-manage-fix3 */
// index.html 에서 app-extra-products.js 다음에 불러야 합니다.
// 공급처 드롭다운은 상품 목록에 보이는 공급처 이름과 맞춥니다. 주소 링크로 공급처를 정하지 않습니다.
// 상품등록 화면의 항목 체크리스트는 없습니다. 배송/가격은 판매정보 업데이트에서 고르고, 배송지는 배송지 목록에서 고릅니다.
// 완박스 배송비가 한 금액이면 그 금액을, 범위면 앞 금액만 씁니다.

function normalizeSupplierName(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/\s+/g, "")
    .replace(/[()[\]{}._\-/]/g, "");
}

function listSupplierName(item) {
  if (!item || typeof item !== "object") return "";
  return String(item.wholesale_name || item.supplier_name || item.wholesaler_name || "").trim();
}

function nameMatchRank(listName, supplierName) {
  const shown = normalizeSupplierName(listName);
  const wanted = normalizeSupplierName(supplierName);
  if (!shown || !wanted) return 0;
  if (shown === wanted) return 2;
  if (shown.length >= 2 && wanted.length >= 2 && (shown.startsWith(wanted) || wanted.startsWith(shown))) return 1;
  return 0;
}

function supplierChoices(wholesalers, products) {
  const counts = new Map();
  const listNames = [];
  (Array.isArray(products) ? products : []).forEach((item) => {
    const name = listSupplierName(item);
    const key = normalizeSupplierName(name);
    if (!key) return;
    counts.set(key, (counts.get(key) || 0) + 1);
    if (!listNames.some((existing) => normalizeSupplierName(existing) === key)) listNames.push(name);
  });
  const choices = [];
  const used = new Set();
  (Array.isArray(wholesalers) ? wholesalers : []).forEach((row) => {
    const exact = listNames.find((name) => normalizeSupplierName(name) === normalizeSupplierName(row && row.name));
    const lined = listNames.filter((name) => nameMatchRank(name, row && row.name) > 0);
    lined.sort((left, right) => (counts.get(normalizeSupplierName(right)) || 0) - (counts.get(normalizeSupplierName(left)) || 0));
    const label = exact || lined[0] || String(row && (row.name || row.id) || "").trim();
    const key = normalizeSupplierName(label);
    if (!label || used.has(key)) return;
    used.add(key);
    choices.push({ id: String(row.id), label, name: label });
  });
  listNames.forEach((name) => {
    const key = normalizeSupplierName(name);
    if (!key || used.has(key)) return;
    used.add(key);
    choices.push({ id: `name:${key}`, label: name, name });
  });
  choices.sort((left, right) => String(left.label).localeCompare(String(right.label), "ko"));
  return choices;
}

function bestSupplierChoice(item, choices) {
  const shown = listSupplierName(item);
  if (!shown) return null;
  let best = null;
  let rank = 0;
  (choices || []).forEach((choice) => {
    const score = nameMatchRank(shown, choice.name);
    const longer = best && normalizeSupplierName(choice.name).length > normalizeSupplierName(best.name).length;
    if (score > rank || (score === rank && score > 0 && longer)) {
      rank = score;
      best = choice;
    }
  });
  return rank ? best : null;
}

function supplierMatchesProduct(item, filter, wholesalers, products) {
  const selected = String(filter || "");
  if (!selected || selected === "all") return true;
  const pool = Array.isArray(products) ? products : [];
  const choices = supplierChoices(wholesalers, pool);
  if (selected === "url") return !listSupplierName(item);
  const choice = choices.find((row) => row.id === selected)
    || choices.find((row) => normalizeSupplierName(row.name) === normalizeSupplierName(selected));
  if (!choice) return false;
  if (!listSupplierName(item)) return String(item && item.wholesale_id || "") === choice.id;
  const best = bestSupplierChoice(item, choices);
  return !!best && best.id === choice.id;
}

function supplierFilterRows(items, filter, wholesalers) {
  const rows = Array.isArray(items) ? items : [];
  const selected = String(filter || "all");
  if (!selected || selected === "all") return rows.slice();
  return rows.filter((item) => supplierMatchesProduct(item, selected, wholesalers, rows));
}

const SHIP_PRICE_KEYS = ["shipping_fee", "price", "cost", "discount_price", "discount_unit"];

function saleUpdatePlan(input) {
  const price = !!(input && input.price);
  const option = !!(input && input.option);
  const shipPrice = !!(input && input.shipPrice);
  const addressId = String(input && input.addressId || "").trim();
  const addresses = Array.isArray(input && input.addresses) ? input.addresses : [];
  const fields = [];
  if (price) fields.push("price");
  if (option) fields.push("option");
  const patch = {};
  if (shipPrice) {
    const known = !addresses.length || addresses.some((item) => String(item && item.id) === addressId);
    if (!addressId || !known) {
      return { ok: false, error: "배송지 목록에서 배송지를 골라 주세요.", fields: [], patch: {} };
    }
    fields.push("ship_price");
    const product = input.product || {};
    SHIP_PRICE_KEYS.forEach((key) => {
      if (Object.prototype.hasOwnProperty.call(product, key)) patch[key] = product[key];
    });
    const parsed = kpageFeeFromProduct(product);
    if (parsed != null) patch.shipping_fee = parsed;
    patch.shipping_address_id = addressId;
  }
  delete patch.name;
  if (!fields.length) return { ok: false, error: "가격, 옵션, 배송/가격 중 하나를 선택해 주세요.", fields: [], patch: {} };
  return { ok: true, error: "", fields, patch };
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

const REREGISTER_FIELDS = [
  { id: "name", label: "상품명", keys: ["name"] },
  { id: "attributes", label: "속성", keys: ["attributes", "naver_attributes"] },
  { id: "ship_price", label: "배송/가격", keys: ["shipping_fee", "price", "cost", "discount_price", "discount_unit"] },
  { id: "options", label: "옵션", keys: ["options", "option_combinations", "option_type"] },
  { id: "detail", label: "상세설명", keys: ["detail_html", "summary"] },
  { id: "images", label: "이미지", keys: ["images"] },
  { id: "stock", label: "재고/판매상태", keys: ["stock", "sale_status"] },
  { id: "category", label: "카테고리/태그", keys: ["category_id", "category_name", "tags"] },
];

function fieldValueChanged(current, previous) {
  if (previous == null || previous === "") return false;
  if (typeof current === "object" || typeof previous === "object") {
    try {
      return JSON.stringify(current) !== JSON.stringify(previous);
    } catch (error) {
      return current !== previous;
    }
  }
  return String(current) !== String(previous);
}

function changedFieldGroups(product) {
  const item = product || {};
  const changed = [];
  if (fieldValueChanged(item.name, item.original_name)) changed.push("name");
  if (
    fieldValueChanged(item.attributes, item.original_attributes)
    || fieldValueChanged(item.naver_attributes, item.original_naver_attributes)
  ) changed.push("attributes");
  if (
    fieldValueChanged(item.price, item.original_price)
    || fieldValueChanged(item.shipping_fee, item.original_shipping_fee)
    || fieldValueChanged(item.shipping_fee, item.wholesale_shipping_fee)
    || fieldValueChanged(item.cost, item.original_cost)
  ) changed.push("ship_price");
  if (
    fieldValueChanged(item.options, item.original_options)
    || fieldValueChanged(item.option_combinations, item.original_option_combinations)
  ) changed.push("options");
  if (
    fieldValueChanged(item.detail_html, item.original_detail_html)
    || fieldValueChanged(item.summary, item.original_summary)
  ) changed.push("detail");
  if (fieldValueChanged(item.images, item.original_images)) changed.push("images");
  if (
    fieldValueChanged(item.stock, item.original_stock)
    || fieldValueChanged(item.sale_status, item.original_sale_status)
  ) changed.push("stock");
  if (
    fieldValueChanged(item.category_id, item.original_category_id)
    || fieldValueChanged(item.tags, item.original_tags)
  ) changed.push("category");
  return changed;
}

function selectiveReregisterPatch(product, groupIds) {
  const wanted = new Set(Array.isArray(groupIds) ? groupIds : []);
  const patch = {};
  REREGISTER_FIELDS.forEach((group) => {
    if (!wanted.has(group.id)) return;
    group.keys.forEach((key) => {
      if (product && Object.prototype.hasOwnProperty.call(product, key)) patch[key] = product[key];
    });
  });
  return patch;
}

function fieldGroupLabels(groupIds) {
  const wanted = new Set(groupIds || []);
  return REREGISTER_FIELDS.filter((group) => wanted.has(group.id)).map((group) => group.label);
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

function restoreUnselected(item, before, patch) {
  const products = readBinding("products");
  const index = Array.isArray(products) ? products.findIndex((row) => row && row.id === item.id) : -1;
  const current = index >= 0 ? products[index] : item;
  const selected = patch || {};
  Object.keys(before).forEach((key) => {
    if (Object.prototype.hasOwnProperty.call(selected, key)) return;
    current[key] = before[key];
  });
  Object.keys(selected).forEach((key) => {
    current[key] = selected[key];
  });
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
  return restoreUnselected(item, before, plan.patch);
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

async function applySelectedReregister(item, groupIds) {
  const patch = selectiveReregisterPatch(item, groupIds);
  const before = Object.assign({}, item);
  if (Object.prototype.hasOwnProperty.call(patch, "shipping_fee")) rememberManualShip(item, patch.shipping_fee);
  Object.keys(patch).forEach((key) => {
    item[key] = patch[key];
  });
  const isMasterProduct = readBinding("isMasterProduct");
  const master = typeof isMasterProduct === "function" && isMasterProduct(item);
  const saveProduct = readBinding("saveProduct");
  if (!master && typeof saveProduct === "function") {
    try {
      await saveProduct(item, patch, true);
    } catch (error) {
      const toast = readBinding("toast");
      if (typeof toast === "function") toast(error.message || "고른 항목을 저장하지 못했습니다.", true);
    }
  }
  const current = restoreUnselected(item, before, patch);
  if (Object.prototype.hasOwnProperty.call(patch, "shipping_fee")) current._shipManual = true;
  const renderProductSheet = readBinding("renderProductSheet");
  if (typeof renderProductSheet === "function") renderProductSheet();
  return { patch, product: current };
}

function dialogPart(dialog, key, selector) {
  if (dialog && dialog[key]) return dialog[key];
  return dialog && typeof dialog.querySelector === "function" ? dialog.querySelector(selector) : null;
}

function ensureFieldDialog(documentRef) {
  let dialog = documentRef.getElementById("fieldReregisterDialog");
  if (dialog) return dialog;
  dialog = documentRef.createElement("dialog");
  dialog.id = "fieldReregisterDialog";
  const form = documentRef.createElement("form");
  const title = documentRef.createElement("h2");
  title.textContent = "바꾼 내용 다시 등록";
  const count = documentRef.createElement("p");
  count.id = "fieldReregisterCount";
  count.className = "hint";
  const rule = documentRef.createElement("p");
  rule.className = "register-choice-rule";
  rule.textContent = "고른 항목만 다시 등록합니다. 고르지 않은 항목은 바꾸지 않습니다.";
  const choices = documentRef.createElement("div");
  choices.id = "fieldReregisterChoices";
  const message = documentRef.createElement("p");
  message.id = "fieldReregisterMessage";
  message.className = "hint";
  const actions = documentRef.createElement("div");
  actions.className = "delivery-actions";
  const submit = documentRef.createElement("button");
  submit.type = "submit";
  submit.className = "btn-naver-register";
  submit.textContent = "선택 항목 등록";
  const cancel = documentRef.createElement("button");
  cancel.type = "button";
  cancel.setAttribute("data-cancel", "1");
  cancel.textContent = "취소";
  actions.appendChild(submit);
  actions.appendChild(cancel);
  form.appendChild(title);
  form.appendChild(count);
  form.appendChild(rule);
  form.appendChild(choices);
  form.appendChild(message);
  form.appendChild(actions);
  dialog.appendChild(form);
  dialog._form = form;
  dialog._count = count;
  dialog._choices = choices;
  dialog._message = message;
  dialog._cancel = cancel;
  documentRef.body.appendChild(dialog);
  return dialog;
}

function fillFieldChoices(choices, documentRef, items) {
  if (choices.textContent != null) choices.textContent = "";
  if (typeof choices.replaceChildren === "function") choices.replaceChildren();
  else if (Array.isArray(choices.children)) choices.children.length = 0;
  const changed = new Set();
  (items || []).forEach((item) => changedFieldGroups(item).forEach((id) => changed.add(id)));
  REREGISTER_FIELDS.forEach((group) => {
    const label = documentRef.createElement("label");
    const input = documentRef.createElement("input");
    input.type = "checkbox";
    input.value = group.id;
    input.checked = changed.has(group.id);
    const text = documentRef.createElement("span");
    text.textContent = group.label;
    label.appendChild(input);
    label.appendChild(text);
    choices.appendChild(label);
  });
}

function askFieldSelection(items) {
  const documentRef = typeof document !== "undefined" ? document : null;
  if (!documentRef) return Promise.resolve(null);
  return new Promise((resolve) => {
    const dialog = ensureFieldDialog(documentRef);
    const form = dialogPart(dialog, "_form", "form");
    const choices = dialogPart(dialog, "_choices", "#fieldReregisterChoices");
    const message = dialogPart(dialog, "_message", "#fieldReregisterMessage");
    const count = dialogPart(dialog, "_count", "#fieldReregisterCount");
    const cancel = dialogPart(dialog, "_cancel", "[data-cancel]");
    fillFieldChoices(choices, documentRef, items);
    if (message) message.textContent = "";
    if (count) {
      count.textContent = items.length > 1
        ? `선택한 등록 상품 ${items.length}개에서 다시 등록할 항목을 고르세요.`
        : "다시 등록할 항목을 고르세요. 바뀐 항목은 미리 체크되어 있습니다.";
    }
    let settled = false;
    const finish = (value) => {
      if (settled) return;
      settled = true;
      if (typeof dialog.close === "function") dialog.close();
      resolve(value);
    };
    form.onsubmit = (event) => {
      if (event && typeof event.preventDefault === "function") event.preventDefault();
      const boxes = typeof choices.querySelectorAll === "function"
        ? Array.from(choices.querySelectorAll("input"))
        : (choices.children || []).reduce((list, label) => list.concat(label.children || []), []).filter((node) => node && node.type === "checkbox");
      const picked = boxes.filter((box) => box.checked).map((box) => box.value);
      if (!picked.length) {
        if (message) message.textContent = "다시 등록할 항목을 하나 이상 골라 주세요.";
        return;
      }
      finish(picked);
    };
    if (cancel) cancel.onclick = () => finish(null);
    dialog.oncancel = (event) => {
      if (event && typeof event.preventDefault === "function") event.preventDefault();
      finish(null);
    };
    if (typeof dialog.showModal === "function") dialog.showModal();
  });
}

function installShippingReregister() {
  // 상품등록 화면의 항목 체크리스트는 제거했습니다.
}

function alignSupplierDropdown() {
  if (typeof document === "undefined") return;
  const select = document.getElementById("productWholesalerFilter");
  if (!select) return;
  const choices = supplierChoices(readBinding("wholesalers") || [], readBinding("products") || []);
  const current = String(readBinding("productFilter") || select.value || "all");
  const kept = [];
  Array.prototype.forEach.call(select.options || [], (option) => {
    if (option.value === "all" || option.value === "url") kept.push(option);
  });
  select.innerHTML = "";
  kept.forEach((option) => select.appendChild(option));
  choices.forEach((choice) => {
    const option = document.createElement("option");
    option.value = choice.id;
    option.textContent = choice.label;
    option.dataset.supplierName = choice.name;
    select.appendChild(option);
  });
  const values = Array.prototype.map.call(select.options || [], (option) => option.value);
  select.value = values.indexOf(current) >= 0 ? current : "all";
  writeBinding("productFilter", select.value || "all");
}

function installSupplierDropdown() {
  const original = readBinding("fillProductFilter");
  if (typeof original !== "function" || original.productManageFix) return;
  const wrapped = function alignedFillProductFilter() {
    const result = original.apply(this, arguments);
    alignSupplierDropdown();
    return result;
  };
  wrapped.productManageFix = true;
  writeBinding("fillProductFilter", wrapped);
  alignSupplierDropdown();
}

function saleAddressList() {
  const loaded = readBinding("deliveryAddresses");
  return Array.isArray(loaded) ? loaded : [];
}

function ensureSaleUpdateControls() {
  if (typeof document === "undefined") return null;
  const dialog = document.getElementById("marketApplyDialog");
  const box = dialog && (dialog.querySelector(".replace-options") || dialog);
  if (!dialog || !box) return null;
  let ship = document.getElementById("marketApplyShipPrice");
  if (!ship) {
    const label = document.createElement("label");
    ship = document.createElement("input");
    ship.type = "checkbox";
    ship.id = "marketApplyShipPrice";
    label.appendChild(ship);
    label.appendChild(document.createTextNode(" 배송/가격"));
    box.appendChild(label);
  }
  let row = document.getElementById("marketApplyAddressRow");
  if (!row) {
    row = document.createElement("label");
    row.id = "marketApplyAddressRow";
    row.appendChild(document.createTextNode("배송지 "));
    const select = document.createElement("select");
    select.id = "marketApplyAddress";
    row.appendChild(select);
    box.appendChild(row);
  }
  const select = document.getElementById("marketApplyAddress");
  if (ship && !ship.productManageFix) {
    ship.productManageFix = true;
    ship.addEventListener("change", () => {
      row.hidden = !ship.checked;
    });
  }
  row.hidden = !(ship && ship.checked);
  if (select) {
    const current = select.value;
    select.innerHTML = "";
    const blank = document.createElement("option");
    blank.value = "";
    blank.textContent = "배송지 목록에서 선택";
    select.appendChild(blank);
    saleAddressList().forEach((item) => {
      const option = document.createElement("option");
      option.value = String(item.id);
      const kind = item.type_label || item.type;
      option.textContent = kind ? `${item.name} (${kind})` : (item.name || `주소 ${item.id}`);
      select.appendChild(option);
    });
    if (current) select.value = current;
  }
  return { ship, select, row };
}

function installSaleUpdate() {
  if (typeof document === "undefined") return;
  ensureSaleUpdateControls();
  const original = readBinding("askMarketApply");
  if (typeof original !== "function" || original.productManageFix) return;
  const wrapped = async function askMarketApplyWithShip(count) {
    if (!saleAddressList().length) {
      const api = readBinding("api");
      if (typeof api === "function") {
        try {
          const rows = await api("/api/addresses", { quiet: true });
          if (Array.isArray(rows)) writeBinding("deliveryAddresses", rows);
        } catch (error) {}
      }
    }
    const controls = ensureSaleUpdateControls();
    const dialog = document.getElementById("marketApplyDialog");
    if (!dialog || !controls) return original.apply(this, arguments);
    const price = document.getElementById("marketApplyPrice");
    const option = document.getElementById("marketApplyOption");
    const note = document.getElementById("marketApplyNote");
    if (note) note.textContent = `등록 상품 ${count}개에 업데이트 적용할까요?`;
    if (price) price.checked = true;
    if (option) option.checked = true;
    controls.ship.checked = false;
    controls.row.hidden = true;
    return new Promise((resolve) => {
      const finish = (fields) => {
        if (typeof dialog.close === "function") dialog.close();
        resolve(fields);
      };
      const ok = document.getElementById("marketApplyOk");
      const cancel = document.getElementById("marketApplyCancel");
      if (ok) ok.onclick = async () => {
        const plan = saleUpdatePlan({
          price: !!(price && price.checked),
          option: !!(option && option.checked),
          shipPrice: !!controls.ship.checked,
          addressId: controls.select && controls.select.value,
          addresses: saleAddressList(),
        });
        if (!plan.ok) {
          const toast = readBinding("toast");
          if (typeof toast === "function") toast(plan.error, true);
          return;
        }
        writeBinding("marketShipPlan", plan);
        if (plan.fields.indexOf("ship_price") >= 0) await applySaleShipPatch(plan);
        finish(plan.fields);
      };
      if (cancel) cancel.onclick = () => finish([]);
      dialog.oncancel = (event) => {
        if (event && typeof event.preventDefault === "function") event.preventDefault();
        finish([]);
      };
      if (typeof dialog.showModal === "function") dialog.showModal();
    });
  };
  wrapped.productManageFix = true;
  writeBinding("askMarketApply", wrapped);
  const api = readBinding("api");
  if (typeof api === "function" && !api.productManageFix) {
    const wrappedApi = async function salePushApi(path, options) {
      const plan = readBinding("marketShipPlan");
      if (plan && options && options.body && String(path || "").indexOf("/push") >= 0) {
        try {
          const body = JSON.parse(options.body);
          body.fields = (body.fields || []).filter((field) => field !== "name");
          if (body.fields.indexOf("ship_price") >= 0 && plan.patch && plan.patch.shipping_address_id) {
            body.shipping_address_id = plan.patch.shipping_address_id;
          }
          delete body.name;
          options = Object.assign({}, options, { body: JSON.stringify(body) });
        } catch (error) {}
      }
      return api.call(this, path, options);
    };
    wrappedApi.productManageFix = true;
    writeBinding("api", wrappedApi);
  }
}

async function applySaleShipPatch(plan) {
  const selected = typeof readBinding("selectedProducts") === "function" ? readBinding("selectedProducts")() : [];
  const visible = typeof readBinding("visibleProducts") === "function" ? readBinding("visibleProducts")() : [];
  const pool = selected.length ? selected : visible;
  const saveProduct = readBinding("saveProduct");
  for (const item of pool) {
    const one = saleUpdatePlan({
      shipPrice: true,
      addressId: plan.patch && plan.patch.shipping_address_id,
      addresses: saleAddressList(),
      product: item,
    });
    if (!one.ok) continue;
    const before = Object.assign({}, item);
    if (typeof saveProduct === "function") {
      const master = typeof readBinding("isMasterProduct") === "function" && readBinding("isMasterProduct")(item);
      if (!master) {
        try { await saveProduct(item, one.patch, true); } catch (error) {}
      }
    }
    const current = restoreUnselected(item, before, one.patch);
    if (Object.prototype.hasOwnProperty.call(one.patch, "shipping_fee")) current._shipManual = true;
  }
  const renderProductSheet = readBinding("renderProductSheet");
  if (typeof renderProductSheet === "function") renderProductSheet();
}

function installProductManageFix() {
  installSupplierFilter();
  installSupplierDropdown();
  installKpageFee();
  installSaleUpdate();
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    normalizeSupplierName,
    supplierMatchesProduct,
    supplierFilterRows,
    supplierChoices,
    saleUpdatePlan,
    kpageBoxShippingFee,
    kpageFeeFromProduct,
    isAlreadyRegistered,
    shippingOnlyPatch,
    applyShippingPatch,
    splitReregister,
    REREGISTER_FIELDS,
    changedFieldGroups,
    selectiveReregisterPatch,
    installProductManageFix,
  };
}

if (typeof document !== "undefined") installProductManageFix();
