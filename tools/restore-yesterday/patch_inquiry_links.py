"""Turn inquiry order and product numbers into links. Leaves the rest of the program alone."""

from __future__ import annotations

import re
import sys
from pathlib import Path

MARKER = "/* inquiry-number-links */"

HELPERS = r"""
/* inquiry-number-links */
function inquiryNumberButtonCell(label, className, onClick) {
  const cell = document.createElement("td");
  const text = String(label || "").trim();
  cell.title = text;
  if (!text) return cell;
  const button = document.createElement("button");
  button.type = "button";
  button.className = className;
  button.textContent = text;
  button.addEventListener("click", (event) => {
    event.stopPropagation();
    onClick();
  });
  cell.appendChild(button);
  return cell;
}

function inquiryStoreSlug(item) {
  const market = typeof inquiryMarketOf === "function" ? inquiryMarketOf(item) : null;
  const slug = String(market?.slug || "").trim();
  if (slug) return slug;
  const url = String(market?.url || "");
  const match = url.match(/smartstore\.naver\.com\/([^/?#]+)/);
  return match ? match[1] : "";
}

function findProductByInquiryNumber(number) {
  const no = String(number || "").trim();
  if (!no || !Array.isArray(products)) return null;
  return products.find((row) => String(row.channel_product_no || "") === no || String(row.origin_product_no || "") === no) || null;
}

function openInquiryProduct(item) {
  const number = String(item?.product_no || "").trim();
  if (!number) {
    toast("상품번호가 없습니다.", true);
    return;
  }
  const product = findProductByInquiryNumber(number);
  const channelNo = product?.channel_product_no || number;
  const originNo = product?.origin_product_no || "";
  if (product && originNo && String(product.channel_product_no || "") !== number && String(originNo) === number) {
    window.open(`https://sell.smartstore.naver.com/#/products/origin-product/${originNo}`, "_blank", "noopener");
    return;
  }
  const slug = product && typeof storeSlug === "function" ? storeSlug(product.source_url) : inquiryStoreSlug(item);
  const url = slug
    ? `https://smartstore.naver.com/${slug}/products/${channelNo}`
    : `https://smartstore.naver.com/main/products/${channelNo}`;
  window.open(url, "_blank", "noopener");
}

function findOrderByNumber(number) {
  const no = String(number || "").trim();
  if (!no || !Array.isArray(orders)) return null;
  return orders.find((row) => String(row.order_id || "") === no || String(row.product_order_id || "") === no) || null;
}

async function openInquiryOrder(item) {
  const number = String(item?.order_id || item?.product_order_id || "").trim();
  if (!number) {
    toast("주문번호가 없습니다.", true);
    return;
  }
  let order = findOrderByNumber(number);
  if (!order) {
    try {
      orders = await api("/api/orders");
    } catch (error) {
      order = null;
    }
    order = findOrderByNumber(number);
  }
  if (!order || typeof openOrderInfo !== "function") {
    toast("이 주문번호의 주문 내용을 찾지 못했습니다.", true);
    return;
  }
  openOrderInfo(order);
}

function fillInquiryProductLink(item) {
  const cell = $("#inquiryProductNo");
  if (!cell) return;
  const number = String(item?.product_no || "").trim();
  cell.replaceChildren();
  if (!number) return;
  const button = document.createElement("button");
  button.type = "button";
  button.className = "order-product-link";
  button.textContent = number;
  button.addEventListener("click", (event) => {
    event.stopPropagation();
    openInquiryProduct(item);
  });
  cell.appendChild(button);
}

"""

ROW_RE = re.compile(
    r'textCell\(\s*item\.(?:order_id|orderId)\s*\|\|\s*["\']["\']\s*\)\s*,\s*'
    r'textCell\(\s*item\.(?:product_no|productNo)\s*\|\|\s*["\']["\']\s*\)\s*,'
)
DETAIL_RE = re.compile(
    r'if \(\$\("#inquiryProductNo"\)\)\s*\$\("#inquiryProductNo"\)\.textContent\s*=\s*item\.(?:product_no|productNo)\s*\|\|\s*["\']["\']\s*;'
)
ROW_NEW = (
    'inquiryNumberButtonCell(item.order_id || "", "order-no-link", () => openInquiryOrder(item)),\n'
    '      inquiryNumberButtonCell(item.product_no || "", "order-product-link", () => openInquiryProduct(item)),'
)
DETAIL_OLD = 'if ($("#inquiryProductNo")) $("#inquiryProductNo").textContent = item.product_no || "";'
DETAIL_NEW = "fillInquiryProductLink(item);"
ANSWER_MARKER = "/* inquiry-simple2 */"
SCREEN_VERSION = "2026.10.28.6"
SIMPLE1_RE = re.compile(
    r"/\* inquiry-simple1 \*/\s*\(function \(\) \{.*?\n\}\)\(\);\s*",
    re.S,
)
OLD_ANSWER_RE = re.compile(
    r"/\* inquiry-answer-place \*/\s*\(function \(\) \{.*?\n\}\)\(\);\s*",
    re.S,
)
PLACE2_RE = re.compile(
    r"/\* inquiry-answer-place2 \*/\s*\(function \(\) \{.*?\n\}\)\(\);\s*",
    re.S,
)
ANSWER_JS = r"""
/* inquiry-simple2 */
(function () {
  const fieldIds = ["inquiryAnswerDraft", "inquiryAnswerTitle", "inquiryBatchBody", "inquiryBatchTitle"];
  function unlock(field) {
    if (!field) return;
    field.readOnly = false;
    field.disabled = false;
    field.removeAttribute("readonly");
    field.removeAttribute("disabled");
    field.style.pointerEvents = "auto";
    field.style.userSelect = "text";
  }
  function typingTarget(node) {
    if (!node || !node.closest) return null;
    return node.closest("#inquiryAnswerDraft, #inquiryAnswerTitle, #inquiryBatchBody, #inquiryBatchTitle");
  }
  function arm(field) {
    if (!field || field.dataset.inquiryKeys === "1") return;
    field.dataset.inquiryKeys = "1";
    unlock(field);
    const stop = (event) => event.stopPropagation();
    field.addEventListener("keydown", stop, true);
    field.addEventListener("keypress", stop, true);
    field.addEventListener("keyup", stop, true);
    field.addEventListener("beforeinput", stop, true);
  }
  window.addEventListener("keydown", (event) => {
    if (!typingTarget(event.target)) return;
    event.stopPropagation();
  }, true);
  function hideMiddleColumn() {
    const view = document.getElementById("inquiryAnswerView");
    const date = document.getElementById("inquiryAnswerAt");
    const draft = document.getElementById("inquiryAnswerDraft");
    const button = document.getElementById("inquiryAnswerButton");
    let box = (view && view.closest(".inquiry-old")) || (date && date.closest(".inquiry-old"));
    if (!box && view) {
      let node = view.parentElement;
      while (node && node !== document.body) {
        const holdsDate = !date || node.contains(date);
        const holdsDraft = draft && node.contains(draft);
        if (holdsDate && !holdsDraft) {
          box = node;
          break;
        }
        node = node.parentElement;
      }
    }
    const foot = document.querySelector(".inquiry-detail-foot");
    if (button) {
      const host = foot || document.getElementById("inquiryDetail");
      if (host && box && box.contains(button)) host.appendChild(button);
      else if (foot && button.parentElement !== foot) foot.appendChild(button);
      button.classList.add("inquiry-send-under-date");
      button.style.display = "block";
      button.style.width = "fit-content";
      button.style.maxWidth = "100%";
      button.style.margin = "8px auto 0";
      button.style.alignSelf = "center";
    }
    if (box) box.hidden = true;
    document.querySelectorAll(".inquiry-sheet").forEach((sheet) => sheet.classList.add("inquiry-no-old"));
  }
  function simplifyInquiry() {
    document.querySelectorAll("[data-inquiry-pane='batch']").forEach((el) => { el.hidden = true; });
    const batch = document.getElementById("inquiryPaneBatch");
    if (batch) batch.hidden = true;
    const basic = document.getElementById("inquiryPaneBasic");
    if (basic) basic.hidden = false;
    document.querySelectorAll("#viewInquiries p, .inquiry-page p").forEach((node) => {
      if (String(node.textContent || "").includes("일괄 입력")) node.hidden = true;
    });
    document.querySelector(".inquiry-page")?.classList.add("inquiry-simple");
    const reset = document.getElementById("resetInquiriesButton");
    if (reset) reset.hidden = true;
    const title = document.getElementById("inquiryAnswerTitle");
    const titleLabel = title ? (title.closest("label") || title) : null;
    if (titleLabel) titleLabel.hidden = true;
    simplifyPeriods();
    hideMiddleColumn();
  }
  function simplifyPeriods() {
    const select = document.getElementById("inquiryPeriod");
    if (!select) return;
    const keep = [
      ["custom", "기간지정"],
      ["today", "오늘"],
      ["yesterday", "어제"],
      ["week", "1주일"],
      ["month", "1개월"],
      ["3months", "3개월"],
      ["year", "1년"],
    ];
    const current = select.value;
    select.innerHTML = "";
    keep.forEach(([value, label]) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      select.appendChild(option);
    });
    const known = keep.some((item) => item[0] === current);
    select.value = known ? current : "month";
    document.querySelectorAll("[data-inquiry-period]").forEach((button) => {
      button.hidden = !["today", "yesterday", "week", "month"].includes(button.dataset.inquiryPeriod);
    });
    if (!known && typeof setInquiryPeriod === "function") setInquiryPeriod("month");
  }
  function showScreenVersion() {
    const version = "2026.10.28.2";
    const label = document.getElementById("appVersion");
    if (label) {
      label.hidden = false;
      label.textContent = `v${version}`;
      label.title = `버전 ${version}`;
    }
    const test = document.body.classList.contains("edition-test");
    document.title = `모두모두AI ${test ? "배포용" : "마스터"} v${version}`;
  }
  function watchIdleReload() {
    if (window.__inquiryIdleWatch) return;
    window.__inquiryIdleWatch = true;
    let last = Date.now();
    let hiddenAt = 0;
    const mark = () => { last = Date.now(); };
    ["pointerdown", "keydown", "input"].forEach((type) => document.addEventListener(type, mark, true));
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) hiddenAt = Date.now();
      else if (hiddenAt && Date.now() - hiddenAt >= 60 * 60 * 1000) location.reload();
    });
    setInterval(() => {
      if (Date.now() - last >= 60 * 60 * 1000) location.reload();
    }, 60 * 1000);
  }
  function openTyping() {
    fieldIds.forEach((id) => arm(document.getElementById(id)));
    simplifyInquiry();
    showScreenVersion();
  }
  function hookFill() {
    if (typeof fillInquiryDetail !== "function" || fillInquiryDetail.inquiryAnswerHook2) return;
    const inner = fillInquiryDetail;
    function wrapped(item) {
      const result = inner.apply(this, arguments);
      openTyping();
      requestAnimationFrame(openTyping);
      return result;
    }
    wrapped.inquiryAnswerHook2 = true;
    fillInquiryDetail = wrapped;
  }
  function hookEdition() {
    if (typeof applyEdition !== "function" || applyEdition.inquiryVersion) return;
    const inner = applyEdition;
    function wrapped(edition, version) {
      const result = inner.apply(this, arguments);
      showScreenVersion();
      return result;
    }
    wrapped.inquiryVersion = true;
    applyEdition = wrapped;
  }
  function hookPeriods() {
    if (typeof fillPeriodSelect !== "function" || fillPeriodSelect.inquirySimple) return;
    const inner = fillPeriodSelect;
    function wrapped(select, selected) {
      const result = inner.apply(this, arguments);
      if (select && select.id === "inquiryPeriod") simplifyPeriods();
      return result;
    }
    wrapped.inquirySimple = true;
    fillPeriodSelect = wrapped;
  }
  function start() {
    openTyping();
    hookFill();
    hookEdition();
    hookPeriods();
    watchIdleReload();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
  setTimeout(start, 0);
})();
"""
ANSWER_CSS = """
/* inquiry-answer-place */
#inquiryAnswerButton.inquiry-send-under-date {
  display: block;
  width: fit-content;
  max-width: 100%;
  margin: 8px auto 0;
  align-self: center;
}
#inquiryAnswerDraft,
#inquiryAnswerTitle,
#inquiryBatchBody,
#inquiryBatchTitle {
  pointer-events: auto !important;
  user-select: text !important;
  -webkit-user-select: text !important;
}
"""
ANSWER_CSS2 = """
/* inquiry-answer-place2 */
.inquiry-sheet.inquiry-no-old {
  grid-template-columns: minmax(420px, 1.5fr) minmax(280px, 1fr) !important;
}
.inquiry-sheet.inquiry-no-old .inquiry-old {
  display: none !important;
}
.inquiry-detail-foot {
  justify-content: center !important;
}
"""
SIMPLE_CSS = """
/* inquiry-simple1 */
.inquiry-page.inquiry-simple {
  background: #f6f4f0;
  gap: 14px;
  padding: 16px 18px 18px;
}
.inquiry-simple .inquiry-card {
  border: 1px solid #e8e2d8;
  border-radius: 18px;
  box-shadow: 0 12px 32px rgba(48, 38, 22, 0.04);
}
.inquiry-simple .inquiry-head { padding: 16px 18px 14px; }
.inquiry-simple .inquiry-head h3 {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: #1c1917;
}
.inquiry-simple .inquiry-notice select {
  color: #8a8175;
  background: transparent;
  border: 0;
  padding-left: 0;
  margin-bottom: 6px;
}
.inquiry-simple .inquiry-filters input,
.inquiry-simple .inquiry-filters select,
.inquiry-simple .inquiry-result-filters select {
  border: 1px solid #e4ddd2;
  border-radius: 9px;
  background: #fff;
  color: #1c1917;
}
.inquiry-simple .inquiry-periods { margin: 10px 0 0; gap: 6px; }
.inquiry-simple .inquiry-periods button {
  border-radius: 999px;
  border: 1px solid #e4ddd2;
  background: transparent;
  color: #5f584e;
  padding: 4px 11px;
}
.inquiry-simple .inquiry-periods button.active {
  background: #1c1917;
  border-color: #1c1917;
  color: #f7f4ee;
  font-weight: 600;
}
.inquiry-simple .inquiry-reset,
.inquiry-simple .inquiry-collect-outline {
  border-radius: 999px;
  background: #fff;
  color: #1c1917;
  border: 1px solid #d9d2c6;
  font-weight: 600;
}
.inquiry-simple .inquiry-warn { display: none; }
.inquiry-simple .inquiry-excel {
  border-radius: 999px;
  background: #fff;
  color: #1c1917;
  border: 1px solid #d9d2c6;
}
.inquiry-simple .inquiry-results .grid-wrap { border-top: 0; }
.inquiry-simple .inquiry-detail {
  border-top: 1px solid #eeeae3;
  background: transparent;
  padding: 14px 6px 16px;
}
.inquiry-simple .inquiry-detail-tabs,
.inquiry-simple [data-inquiry-pane="batch"],
.inquiry-simple #inquiryPaneBatch { display: none !important; }
.inquiry-simple .inquiry-sheet,
.inquiry-simple .inquiry-sheet.inquiry-no-old {
  grid-template-columns: minmax(0, 1.45fr) minmax(260px, 0.8fr) !important;
  gap: 18px;
}
.inquiry-simple .inquiry-form th,
.inquiry-simple .inquiry-form td {
  border: 0;
  border-bottom: 1px solid #efeae3;
  background: transparent;
  padding: 8px 10px;
}
.inquiry-simple .inquiry-form th {
  width: 72px;
  color: #8d867b;
  font-size: 12px;
  font-weight: 500;
}
.inquiry-simple .inquiry-form textarea,
.inquiry-simple .inquiry-new textarea,
.inquiry-simple .inquiry-new input {
  border: 1px solid #e6e0d6;
  border-radius: 12px;
  background: #fcfbf9;
  color: #1c1917;
}
.inquiry-simple .inquiry-new {
  background: transparent;
  border: 0;
  padding: 0;
}
.inquiry-simple .inquiry-new label {
  color: #8d867b;
  font-size: 12px;
}
.inquiry-simple #inquiryAnswerButton {
  background: #1f3a32;
  color: #f6f3ee;
  border: 0;
  border-radius: 999px;
  padding: 8px 22px;
  font-weight: 600;
  letter-spacing: 0.02em;
}
html[data-theme="dark"] .inquiry-page.inquiry-simple { background: #141414; }
html[data-theme="dark"] .inquiry-simple .inquiry-card {
  background: #1c1c1c;
  border-color: #2c2c2c;
  box-shadow: none;
}
html[data-theme="dark"] .inquiry-simple .inquiry-head h3,
html[data-theme="dark"] .inquiry-simple .inquiry-form td,
html[data-theme="dark"] .inquiry-simple .inquiry-new textarea,
html[data-theme="dark"] .inquiry-simple .inquiry-new input { color: #f3f0ea; }
html[data-theme="dark"] .inquiry-simple .inquiry-notice select,
html[data-theme="dark"] .inquiry-simple .inquiry-form th,
html[data-theme="dark"] .inquiry-simple .inquiry-new label { color: #a39b90; }
html[data-theme="dark"] .inquiry-simple .inquiry-filters input,
html[data-theme="dark"] .inquiry-simple .inquiry-filters select,
html[data-theme="dark"] .inquiry-simple .inquiry-result-filters select,
html[data-theme="dark"] .inquiry-simple .inquiry-form textarea,
html[data-theme="dark"] .inquiry-simple .inquiry-new textarea,
html[data-theme="dark"] .inquiry-simple .inquiry-new input {
  background: #161616;
  border-color: #333;
  color: #f3f0ea;
}
html[data-theme="dark"] .inquiry-simple .inquiry-periods button,
html[data-theme="dark"] .inquiry-simple .inquiry-reset,
html[data-theme="dark"] .inquiry-simple .inquiry-collect-outline,
html[data-theme="dark"] .inquiry-simple .inquiry-excel {
  background: transparent;
  color: #ece8e1;
  border-color: #3a3a3a;
}
html[data-theme="dark"] .inquiry-simple .inquiry-periods button.active {
  background: #f3f0ea;
  color: #1c1917;
  border-color: #f3f0ea;
}
html[data-theme="dark"] .inquiry-simple .inquiry-form td,
html[data-theme="dark"] .inquiry-simple .inquiry-detail { border-color: #2c2c2c; }
html[data-theme="dark"] .inquiry-simple #inquiryAnswerButton {
  background: #d7c4a3;
  color: #1c1917;
}
"""
SIMPLE_CSS2 = """
/* inquiry-simple2 */
.inquiry-simple .inquiry-reset,
.inquiry-simple #resetInquiriesButton { display: none !important; }
.inquiry-simple .inquiry-new label:has(#inquiryAnswerTitle) { display: none !important; }
.inquiry-simple [data-inquiry-period="3days"],
.inquiry-simple [data-inquiry-period="3months"],
.inquiry-simple [data-inquiry-period="halfYear"],
.inquiry-simple [data-inquiry-period="year"] { display: none !important; }
.inquiry-simple .inquiry-sheet,
.inquiry-simple .inquiry-sheet.inquiry-no-old {
  grid-template-columns: minmax(280px, 0.8fr) minmax(460px, 1.4fr) !important;
}
.inquiry-simple #inquiryAnswerDraft {
  width: 100%;
  min-height: 220px;
}
"""
SIMPLE3_JS = r"""
/* inquiry-simple3 */
(function () {
  const version = "2026.10.28.3";
  function showStoreLabel() {
    document.querySelectorAll(".inquiry-form th").forEach((th) => {
      const text = th.textContent.replace(/\s+/g, "");
      if (text === "쇼핑몰ID") th.textContent = "스토어명";
    });
  }
  function storeName(item) {
    if (!item) return "";
    let name = "";
    if (typeof inquiryStoreName === "function") name = inquiryStoreName(item) || "";
    if (!name) {
      const market = typeof inquiryMarketOf === "function" ? inquiryMarketOf(item) : null;
      name = item.store_name || (market && market.name) || item.market_name || "";
    }
    return String(name || "").trim();
  }
  function fillStore(item) {
    showStoreLabel();
    const cell = document.getElementById("inquiryMallId");
    const name = storeName(item);
    if (cell && name) cell.textContent = name;
  }
  function showVersion() {
    const label = document.getElementById("appVersion");
    if (label) {
      label.hidden = false;
      label.textContent = "v" + version;
      label.title = "버전 " + version;
    }
    const test = document.body.classList.contains("edition-test");
    document.title = "모두모두AI " + (test ? "배포용" : "마스터") + " v" + version;
  }
  function hook() {
    showStoreLabel();
    showVersion();
    if (typeof fillInquiryDetail === "function" && !fillInquiryDetail.inquiryStoreName) {
      const inner = fillInquiryDetail;
      function wrapped(item) {
        const result = inner.apply(this, arguments);
        fillStore(item);
        showVersion();
        return result;
      }
      wrapped.inquiryStoreName = true;
      wrapped.inquiryAnswerHook2 = true;
      fillInquiryDetail = wrapped;
    }
    if (typeof applyEdition === "function" && !applyEdition.inquiryVersion3) {
      const inner = applyEdition;
      function wrapped() {
        const result = inner.apply(this, arguments);
        showVersion();
        return result;
      }
      wrapped.inquiryVersion = true;
      wrapped.inquiryVersion3 = true;
      applyEdition = wrapped;
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", hook);
  else hook();
  setTimeout(hook, 0);
  setTimeout(showVersion, 50);
})();
"""
SIMPLE3_CSS = """
/* inquiry-simple3 */
.inquiry-page.inquiry-simple { font-size: 110%; }
.inquiry-simple textarea,
.inquiry-simple input,
.inquiry-simple select,
.inquiry-simple button,
.inquiry-simple .inquiry-form th,
.inquiry-simple .inquiry-form td,
.inquiry-simple .grid th,
.inquiry-simple .grid td { font-size: inherit; }
.inquiry-simple .inquiry-head h3 { font-size: 16.5px; }
.inquiry-simple .inquiry-form th,
.inquiry-simple .inquiry-new label { font-size: 13.2px; }
"""
MARGIN_JS = r"""
/* product-margin1 */
(function () {
  const version = "2026.10.28.4";
  function num(value) {
    const text = String(value ?? "").replace(/,/g, "").replace(/%/g, "").trim();
    if (!text) return 0;
    const number = Number(text);
    return Number.isFinite(number) ? number : 0;
  }
  function rateNumber(value) {
    const text = String(value ?? "").trim();
    if (!text) return 0;
    const number = num(text);
    if (!(number > 0)) return 0;
    if (text.includes("%") || number > 1) return number / 100;
    return number;
  }
  function isMaster(item) {
    if (typeof isMasterProduct === "function") return Boolean(isMasterProduct(item));
    return !(item && (item.master_id || item.market_id));
  }
  function rowPrice(item, row) {
    const input = row && row.querySelector ? row.querySelector("[data-field='price']") : null;
    if (input && String(input.value).trim() !== "") return num(input.value);
    return num(item && item.price);
  }
  function supplyCost(item, row) {
    const input = row && row.querySelector ? row.querySelector("[data-field='cost']") : null;
    let cost = input && String(input.value).trim() !== "" ? num(input.value) : num(item && item.cost);
    if (cost > 0 || !item || !item.master_id || typeof products === "undefined") return cost;
    const master = products.find((rowItem) => rowItem && rowItem.id === item.master_id);
    const masterCost = num(master && master.cost);
    return masterCost > 0 ? masterCost : cost;
  }
  function productShip(item) {
    if (!item) return null;
    const keys = ["parcel_fee", "courier_fee", "shipping_fee", "delivery_fee", "shipping"];
    for (const key of keys) {
      if (item[key] == null || item[key] === "") continue;
      const amount = num(item[key]);
      if (amount < 0) continue;
      if (key === "shipping") {
        const type = String(item.shipping_type || "").toUpperCase();
        if (type === "F" || type === "C") return 0;
      }
      return amount;
    }
    return null;
  }
  function templateFee() {
    const list = typeof deliveryTemplates !== "undefined" && Array.isArray(deliveryTemplates) ? deliveryTemplates : [];
    const template = list.find((item) => item && item.is_default) || list[0];
    if (!template) return 0;
    if (String(template.delivery_fee_type || "") === "FREE") return 0;
    const amount = num(template.base_fee);
    return amount > 0 ? amount : 0;
  }
  function shippingCost(item) {
    const own = productShip(item);
    return own == null ? templateFee() : own;
  }
  function marketFeeRate(item) {
    if (!item || isMaster(item)) return 0;
    const market = typeof markets !== "undefined" && Array.isArray(markets)
      ? markets.find((row) => row && row.id === item.market_id)
      : null;
    const candidates = [
      item.fee_rate, item.commission_rate, item.market_fee_rate, item.fee_percent,
      market && market.fee_rate, market && market.commission_rate, market && market.fee_percent, market && market.market_fee_rate,
    ];
    for (const value of candidates) {
      const rate = rateNumber(value);
      if (rate > 0 && rate < 1) return rate;
    }
    const known = feeOrders();
    if (!known.length || !item.market_id) return 0;
    let fee = 0;
    let gross = 0;
    known.forEach((order) => {
      if (!order || String(order.market_id || "") !== String(item.market_id)) return;
      const commission = num(order.commission);
      let base = typeof orderGrossAmount === "function" ? num(orderGrossAmount(order)) : 0;
      if (!(base > 0)) base = num(order.payment_amount || order.total_payment_amount || order.order_amount);
      if (commission > 0 && base > 0) {
        fee += commission;
        gross += base;
      }
    });
    if (!(gross > 0)) return 0;
    const rate = fee / gross;
    return rate > 0 && rate < 1 ? rate : 0;
  }
  function marginNumber(item, row) {
    const price = rowPrice(item, row);
    if (!(price > 0)) return NaN;
    const cost = supplyCost(item, row);
    const ship = shippingCost(item);
    const fee = price * marketFeeRate(item);
    return (price - fee - cost - ship) / price * 100;
  }
  function marginTip(item, row) {
    const price = rowPrice(item, row);
    const cost = supplyCost(item, row);
    const ship = shippingCost(item);
    const rate = marketFeeRate(item);
    const fee = Math.round(price * rate);
    if (isMaster(item)) return "마스터 (판매가 " + price + " - 공급가 " + cost + " - 택배비 " + ship + ") / 판매가";
    return "마켓 (판매가 " + price + " - 수수료 " + fee + " - 공급가 " + cost + " - 배송비 " + ship + ") / 판매가";
  }
  function productTableEl() {
    return document.getElementById("productGrid")
      || (document.getElementById("productTable") && document.getElementById("productTable").closest("table"));
  }
  function ensureHeader() {
    const table = productTableEl();
    if (!table || table.querySelector("thead th[data-margin-col='1']")) return;
    const priceTh = [...table.querySelectorAll("thead th")].find((th) => {
      return th.dataset.sort === "price" || th.textContent.replace(/\s+/g, "") === "판매가";
    });
    if (!priceTh) return;
    const th = document.createElement("th");
    th.dataset.marginCol = "1";
    th.dataset.sort = "margin";
    th.className = "sortable";
    th.title = "마스터는 (판매가-공급가-택배비)/판매가, 마켓은 (판매가-수수료-공급가-배송비)/판매가";
    th.textContent = "마진율";
    priceTh.after(th);
    const priceCol = table.querySelector("col[data-col='price']");
    if (priceCol && !table.querySelector("col[data-col='margin']")) {
      const col = document.createElement("col");
      col.dataset.col = "margin";
      col.style.width = "84px";
      priceCol.after(col);
    }
  }
  function itemForRow(row, index) {
    const list = typeof visibleProducts === "function" ? visibleProducts() : [];
    if (list[index]) return list[index];
    if (typeof products === "undefined" || !row) return null;
    return products.find((item) => item && String(item.id) === String(row.dataset.id)) || null;
  }
  function paintRow(row, item) {
    if (!row) return;
    const priceInput = row.querySelector("[data-field='price']");
    let priceCell = priceInput ? priceInput.closest("td") : null;
    if (!priceCell) {
      const table = productTableEl();
      const ths = table ? [...table.querySelectorAll("thead th")] : [];
      const priceAt = ths.findIndex((th) => th.dataset.sort === "price" || th.textContent.replace(/\s+/g, "") === "판매가");
      if (priceAt >= 0) priceCell = row.children[priceAt] || null;
    }
    if (!priceCell) return;
    let cell = priceCell.nextElementSibling;
    if (!cell || cell.dataset.margin !== "1") {
      cell = document.createElement("td");
      cell.dataset.margin = "1";
      priceCell.after(cell);
    }
    const value = marginNumber(item, row);
    const price = rowPrice(item, row);
    cell.textContent = price > 0 && Number.isFinite(value) ? value.toFixed(2) + "%" : "";
    cell.title = marginTip(item, row);
    cell.classList.toggle("margin-neg", Number.isFinite(value) && value < 0);
  }
  function paintRows() {
    ensureHeader();
    const body = document.getElementById("productTable");
    if (!body) return;
    [...body.querySelectorAll("tr")].forEach((row, index) => paintRow(row, itemForRow(row, index)));
  }
  function listenEdits() {
    const body = document.getElementById("productTable");
    if (!body || body.dataset.marginListen === "1") return;
    body.dataset.marginListen = "1";
    const onEdit = (event) => {
      const field = event.target && event.target.dataset ? event.target.dataset.field : "";
      if (field !== "price" && field !== "cost") return;
      const row = event.target.closest("tr");
      if (!row) return;
      const rows = [...body.querySelectorAll("tr")];
      paintRow(row, itemForRow(row, rows.indexOf(row)));
    };
    body.addEventListener("input", onEdit);
    body.addEventListener("change", onEdit);
  }
  let templateAsked = false;
  let marketFeeOrders = null;
  function feeOrders() {
    if (typeof orders !== "undefined" && Array.isArray(orders) && orders.length) return orders;
    return Array.isArray(marketFeeOrders) ? marketFeeOrders : [];
  }
  function warmTemplate() {
    if (templateAsked || typeof currentDeliveryTemplate !== "function") return;
    templateAsked = true;
    Promise.resolve(currentDeliveryTemplate()).then(() => paintRows()).catch(() => {});
  }
  function warmFeeOrders() {
    if (marketFeeOrders || typeof api !== "function") return;
    if (typeof orders !== "undefined" && orders.length) return;
    marketFeeOrders = [];
    api("/api/orders", { quiet: true }).then((rows) => {
      if (Array.isArray(rows)) marketFeeOrders = rows;
      paintRows();
    }).catch(() => {});
  }
  function showVersion() {
    const label = document.getElementById("appVersion");
    if (label) {
      label.hidden = false;
      label.textContent = "v" + version;
      label.title = "버전 " + version;
    }
    const test = document.body.classList.contains("edition-test");
    document.title = "모두모두AI " + (test ? "배포용" : "마스터") + " v" + version;
  }
  function hook() {
    ensureHeader();
    showVersion();
    if (typeof renderProductSheet === "function" && !renderProductSheet.marginCol) {
      const inner = renderProductSheet;
      function wrapped() {
        ensureHeader();
        const result = inner.apply(this, arguments);
        paintRows();
        return result;
      }
      wrapped.marginCol = true;
      renderProductSheet = wrapped;
    }
    if (typeof productSortValue === "function" && !productSortValue.marginSort) {
      const inner = productSortValue;
      function wrapped(item, key) {
        if (key === "margin") {
          const value = marginNumber(item, null);
          return Number.isFinite(value) ? value : 0;
        }
        return inner.call(this, item, key);
      }
      wrapped.marginSort = true;
      productSortValue = wrapped;
    }
    if (typeof applyEdition === "function" && !applyEdition.inquiryVersion4) {
      const inner = applyEdition;
      function wrapped() {
        const result = inner.apply(this, arguments);
        showVersion();
        return result;
      }
      wrapped.inquiryVersion = true;
      wrapped.inquiryVersion3 = true;
      wrapped.inquiryVersion4 = true;
      wrapped.inquiryStoreName = true;
      wrapped.inquiryAnswerHook2 = true;
      applyEdition = wrapped;
    }
    listenEdits();
    paintRows();
    warmTemplate();
    warmFeeOrders();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", hook);
  else hook();
  setTimeout(hook, 0);
  setTimeout(showVersion, 120);
  setTimeout(showVersion, 600);
})();
"""
MARGIN_CSS = """
/* product-margin1 */
#productGrid td[data-margin="1"] {
  text-align: right;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  padding-right: 8px;
}
#productGrid td[data-margin="1"].margin-neg { color: #c2410c; }
html[data-theme="dark"] #productGrid td[data-margin="1"].margin-neg { color: #fb923c; }
"""
IMAGE_JS = r"""
/* image-work1 */
(function () {
  const version = "2026.10.28.5";
  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }
  function stayOnEscape(dialog) {
    if (!dialog || dialog.dataset.stayEsc === "1") return;
    dialog.dataset.stayEsc = "1";
    dialog.addEventListener("cancel", (event) => event.preventDefault());
    dialog.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
    });
  }
  function zoomBar(id, label, min, max, step, value) {
    let bar = document.getElementById(id);
    if (bar) return bar;
    bar = document.createElement("div");
    bar.id = id;
    bar.className = "work-zoom";
    bar.innerHTML = '<span>' + label + '</span><button type="button" data-zoom="-1" aria-label="축소">−</button><input type="range" min="' + min + '" max="' + max + '" step="' + step + '" value="' + value + '" /><button type="button" data-zoom="1" aria-label="확대">+</button><b data-zoom-label>' + value + '%</b>';
    return bar;
  }
  function bindZoom(bar, read, write, step) {
    if (!bar || bar.dataset.bound === "1") return;
    bar.dataset.bound = "1";
    const range = bar.querySelector("input");
    const label = bar.querySelector("[data-zoom-label]");
    const paint = (value) => {
      const next = write(value);
      range.value = String(next);
      label.textContent = next + "%";
    };
    range.addEventListener("input", () => paint(Number(range.value)));
    bar.querySelectorAll("[data-zoom]").forEach((button) => {
      button.addEventListener("click", () => paint(read() + Number(button.dataset.zoom) * step));
    });
    paint(read());
  }
  let detailZoom = 100;
  let thumbZoom = 25;
  function applyDetailZoom(value) {
    detailZoom = clamp(Math.round(value), 50, 200);
    const box = document.getElementById("detailVisual");
    if (box) box.style.zoom = String(detailZoom / 100);
    return detailZoom;
  }
  function applyThumbZoom(value) {
    thumbZoom = clamp(Math.round(value), 20, 120);
    const size = Math.round(500 * thumbZoom / 100);
    document.documentElement.style.setProperty("--image-slot-size", size + "px");
    return thumbZoom;
  }
  function mountZoom() {
    const detail = document.getElementById("detailDialog");
    const visual = document.getElementById("detailVisual");
    if (detail && visual) {
      const bar = zoomBar("detailZoomBar", "화면", 50, 200, 2, detailZoom);
      if (!bar.isConnected) visual.before(bar);
      bindZoom(bar, () => detailZoom, applyDetailZoom, 2);
      if (visual.dataset.zoomWheel !== "1") {
        visual.dataset.zoomWheel = "1";
        visual.addEventListener("wheel", (event) => {
          if (!event.ctrlKey && !event.metaKey) return;
          event.preventDefault();
          applyDetailZoom(detailZoom + (event.deltaY > 0 ? -2 : 2));
          const range = bar.querySelector("input");
          const label = bar.querySelector("[data-zoom-label]");
          if (range) range.value = String(detailZoom);
          if (label) label.textContent = detailZoom + "%";
        }, { passive: false });
      }
    }
    const image = document.getElementById("imageDialog");
    const thumbs = document.getElementById("imageThumbs");
    if (image && thumbs) {
      const bar = zoomBar("imageZoomBar", "이미지", 20, 120, 1, thumbZoom);
      const drop = document.getElementById("imageDrop") || thumbs;
      if (!bar.isConnected) drop.before(bar);
      bindZoom(bar, () => thumbZoom, applyThumbZoom, 1);
      if (drop.dataset.zoomWheel !== "1") {
        drop.dataset.zoomWheel = "1";
        drop.addEventListener("wheel", (event) => {
          if (!event.ctrlKey && !event.metaKey) return;
          event.preventDefault();
          applyThumbZoom(thumbZoom + (event.deltaY > 0 ? -1 : 1));
          const range = bar.querySelector("input");
          const label = bar.querySelector("[data-zoom-label]");
          if (range) range.value = String(thumbZoom);
          if (label) label.textContent = thumbZoom + "%";
        }, { passive: false });
      }
    }
  }
  function watchButton(button, status) {
    if (!button || !status || button.dataset.workWatch === "1") return;
    button.dataset.workWatch = "1";
    const paint = () => {
      const text = button.textContent.replace(/\s+/g, " ").trim();
      status.textContent = button.disabled ? text : status.dataset.idle || "";
    };
    new MutationObserver(paint).observe(button, { attributes: true, childList: true, characterData: true, subtree: true });
  }
  function polishFoot(dialogId, statusId, buttonId) {
    const dialog = document.getElementById(dialogId);
    if (!dialog) return;
    const actions = dialog.querySelector(".dialog-actions");
    if (!actions) return;
    actions.classList.add("work-foot");
    let status = statusId ? document.getElementById(statusId) : null;
    if (!status) status = actions.querySelector(".work-status");
    if (!status) {
      status = document.createElement("p");
      status.className = "work-status";
    }
    status.classList.add("work-status");
    if (status.parentElement !== actions) actions.prepend(status);
    if (!actions.querySelector(".work-close")) {
      const close = document.createElement("button");
      close.type = "button";
      close.className = "work-close";
      close.textContent = "닫기";
      close.addEventListener("click", () => {
        const headerClose = dialog.querySelector("header button");
        if (headerClose) headerClose.click();
        else dialog.close();
      });
      const save = actions.querySelector("button[type='submit'], .btn-apply, button");
      if (save) save.before(close);
      else actions.append(close);
      if (save) save.classList.add("work-save");
    }
    if (!statusId) watchButton(document.getElementById(buttonId), status);
  }
  function showVersion() {
    const label = document.getElementById("appVersion");
    if (label) {
      label.hidden = false;
      label.textContent = "v" + version;
      label.title = "버전 " + version;
    }
    const test = document.body.classList.contains("edition-test");
    document.title = "모두모두AI " + (test ? "배포용" : "마스터") + " v" + version;
  }
  function hook() {
    stayOnEscape(document.getElementById("detailDialog"));
    stayOnEscape(document.getElementById("imageDialog"));
    mountZoom();
    polishFoot("detailDialog", "", "detailIntroAi");
    polishFoot("imageDialog", "imageTextJobStatus", "removeImageTextButton");
    showVersion();
    if (typeof applyEdition === "function" && !applyEdition.inquiryVersion5) {
      const inner = applyEdition;
      function wrapped() {
        const result = inner.apply(this, arguments);
        showVersion();
        return result;
      }
      wrapped.inquiryVersion = true;
      wrapped.inquiryVersion3 = true;
      wrapped.inquiryVersion4 = true;
      wrapped.inquiryVersion5 = true;
      wrapped.inquiryStoreName = true;
      wrapped.inquiryAnswerHook2 = true;
      applyEdition = wrapped;
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", hook);
  else hook();
  setTimeout(hook, 0);
  setTimeout(showVersion, 700);
  setTimeout(showVersion, 1200);
})();
"""
IMAGE_CSS = """
/* image-work1 */
#detailDialog,
#imageDialog {
  width: 100vw;
  height: 100vh;
  max-width: 100vw;
  max-height: 100vh;
  margin: 0;
  inset: 0;
  border: 0;
}
#detailDialog form,
#imageDialog form {
  height: 100%;
  max-height: none;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-sizing: border-box;
}
#detailDialog .detail-visual,
#detailDialog .detail-source {
  flex: 1 1 auto;
  min-height: 0;
  max-height: none;
}
#imageDialog .image-drop {
  flex: 1 1 auto;
  min-height: 120px;
  display: flex;
  flex-direction: column;
}
#imageDialog .image-thumbs {
  flex: 1 1 auto;
  max-height: none;
  align-content: flex-start;
}
#imageDialog .image-slot {
  width: var(--image-slot-size, 125px);
  height: var(--image-slot-size, 125px);
  flex-basis: var(--image-slot-size, 125px);
}
#imageDialog .option-list-wrap {
  flex: 0 1 28vh;
  min-height: 96px;
  max-height: none;
}
.work-zoom {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0 0 8px;
  color: #5c564c;
  font-size: 12px;
}
.work-zoom input[type="range"] { width: 180px; accent-color: #1f6b4a; }
.work-zoom button {
  min-width: 28px;
  height: 26px;
  padding: 0 6px;
}
.work-zoom b { min-width: 42px; font-weight: 650; }
#detailDialog .work-foot,
#imageDialog .work-foot {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px solid #e6e1d8;
}
#detailDialog .work-status,
#imageDialog .work-status {
  flex: 1 1 auto;
  margin: 0 auto 0 0;
  min-height: 1.2em;
  color: #5c564c;
  font-size: 13px;
  font-weight: 600;
}
#detailDialog .work-close,
#imageDialog .work-close,
#detailDialog .work-save,
#imageDialog .work-save {
  min-width: 88px;
  height: 34px;
}
#detailDialog .work-save,
#imageDialog .work-save {
  background: #1f6b4a;
  color: #fff;
  border-color: #1f6b4a;
}
html[data-theme="dark"] .work-zoom { color: #d6d3cd; }
html[data-theme="dark"] #detailDialog .work-foot,
html[data-theme="dark"] #imageDialog .work-foot { border-top-color: #2c2c2c; }
html[data-theme="dark"] #detailDialog .work-status,
html[data-theme="dark"] #imageDialog .work-status { color: #d6d3cd; }
html[data-theme="dark"] #detailDialog .work-save,
html[data-theme="dark"] #imageDialog .work-save {
  background: #d7c4a3;
  color: #1c1917;
  border-color: #d7c4a3;
}
"""
INVITE_JS = r"""
/* admin-invite1 */
(function () {
  const version = "2026.10.28.6";
  const roleKey = "modumodu-invite-role";
  const state = { role: "", remote: false, owner: false, pending: false };
  function readRole() {
    const params = new URLSearchParams(location.search);
    const fromUrl = params.get("role");
    if (fromUrl === "products" || fromUrl === "orders") {
      try { sessionStorage.setItem(roleKey, fromUrl); } catch (error) {}
      return fromUrl;
    }
    try {
      const saved = sessionStorage.getItem(roleKey);
      if (saved === "products" || saved === "orders") return saved;
    } catch (error) {}
    return "";
  }
  function locked() {
    return state.remote || (state.pending && !state.owner);
  }
  function allowed(name) {
    if (!locked()) return name;
    if (name === "help") return "help";
    if (state.role === "products") {
      if (name === "orders" || name === "inquiries") return "products";
      return name;
    }
    if (state.role === "orders") {
      if (name === "products" || name === "collect" || name === "wholesalers") return "orders";
      return name;
    }
    return name;
  }
  function currentView() {
    const names = [
      ["products", "viewProducts"],
      ["orders", "viewOrders"],
      ["inquiries", "viewInquiries"],
      ["collect", "viewCollect"],
      ["wholesalers", "viewWholesalers"],
      ["settings", "viewSettings"],
      ["help", "viewHelp"],
    ];
    for (const [name, id] of names) {
      const el = document.getElementById(id);
      if (el && !el.hidden) return name;
    }
    return "products";
  }
  function isSecretHeader(cell) {
    const text = (cell.textContent || "").replace(/\s+/g, "");
    if (!text || text.length > 24) return false;
    return /아이디|패스워드|비밀번호|아이디키|시크릿키|업체코드|ESMID|쇼핑몰ID/i.test(text);
  }
  function blankCell(cell) {
    if (!cell || cell.querySelector("input, select, textarea")) return;
    cell.classList.add("invite-secret");
    if (state.remote && cell.textContent) cell.textContent = "";
  }
  function hideSecretColumns() {
    if (!locked()) return;
    document.querySelectorAll("table").forEach((table) => {
      const headerRows = table.tHead ? [...table.tHead.rows] : [];
      const secretIndex = new Set();
      headerRows.forEach((row) => {
        [...row.cells].forEach((cell, index) => {
          if (!isSecretHeader(cell)) return;
          secretIndex.add(index);
          cell.classList.add("invite-secret");
        });
      });
      if (secretIndex.size) {
        const cols = table.querySelectorAll("colgroup col");
        secretIndex.forEach((index) => {
          if (cols[index]) cols[index].classList.add("invite-secret");
        });
        [...table.tBodies].forEach((body) => {
          [...body.rows].forEach((row) => {
            if (row.cells.length === 1 && row.cells[0].colSpan > 1) return;
            secretIndex.forEach((index) => blankCell(row.cells[index]));
          });
        });
      }
      [...table.rows].forEach((row) => {
        const cells = [...row.cells];
        for (let index = 0; index < cells.length; index += 1) {
          const cell = cells[index];
          if (cell.tagName !== "TH" || !isSecretHeader(cell)) continue;
          cell.classList.add("invite-secret");
          const next = cells[index + 1];
          if (next && next.tagName === "TD") blankCell(next);
        }
      });
    });
    if (!state.remote) return;
    const secrets = new Map();
    const lists = [];
    if (typeof markets !== "undefined" && Array.isArray(markets)) lists.push(markets);
    if (typeof wholesalers !== "undefined" && Array.isArray(wholesalers)) lists.push(wholesalers);
    lists.forEach((list) => {
      list.forEach((item) => {
        if (!item || !item.login_id) return;
        const secret = String(item.login_id).trim();
        if (secret.length < 3) return;
        const label = item.name || item.store_name || item.channel_name || "스토어";
        secrets.set(secret, label === secret ? "스토어" : label);
      });
    });
    document.querySelectorAll("option").forEach((option) => {
      const text = option.textContent.trim();
      if (secrets.has(text)) {
        option.textContent = secrets.get(text);
        return;
      }
      secrets.forEach((label, secret) => {
        if (text.endsWith(" " + secret)) option.textContent = text.slice(0, text.length - secret.length) + label;
      });
    });
    const account = document.getElementById("orderInfoAccount");
    if (account) {
      secrets.forEach((label, secret) => {
        if (account.textContent.includes(secret)) account.textContent = account.textContent.split(secret).join(label);
      });
    }
  }
  function revealSecrets() {
    document.querySelectorAll(".invite-secret").forEach((el) => el.classList.remove("invite-secret"));
  }
  function paintBadge() {
    let badge = document.getElementById("inviteRoleBadge");
    const show = locked() && (state.role === "products" || state.role === "orders");
    if (!show) {
      if (badge) badge.remove();
      return;
    }
    if (!badge) {
      badge = document.createElement("span");
      badge.id = "inviteRoleBadge";
      const tabs = document.querySelector(".app-tabs");
      if (tabs) tabs.after(badge);
    }
    badge.textContent = state.role === "orders" ? "주문관리" : "상품관리";
  }
  function withRole(link, role) {
    try {
      const url = new URL(link, location.href);
      url.searchParams.set("role", role);
      return url.toString();
    } catch (error) {
      return link + (link.indexOf("?") >= 0 ? "&" : "?") + "role=" + role;
    }
  }
  async function copyLink(url) {
    try {
      if (typeof copyText === "function") await copyText(url);
      else if (navigator.clipboard) await navigator.clipboard.writeText(url);
      if (typeof toast === "function") toast("링크를 복사했습니다.");
    } catch (error) {
      if (typeof toast === "function") toast("복사에 실패했습니다.", true);
    }
  }
  function paintInvitePanel() {
    const box = document.getElementById("helpShare");
    if (!box || !state.owner) return;
    let panel = document.getElementById("invitePanel");
    if (!panel) {
      panel = document.createElement("div");
      panel.id = "invitePanel";
      panel.className = "invite-panel";
    }
    panel.replaceChildren();
    const head = document.createElement("p");
    head.className = "share-link-head";
    head.textContent = "상품관리와 주문관리를 나눠 보냅니다. 초대받은 화면에는 마켓과 공급사 로그인 정보가 나오지 않습니다.";
    panel.append(head);
    const links = (typeof cachedShareLinks !== "undefined" && cachedShareLinks) || [];
    [["products", "상품관리 초대"], ["orders", "주문관리 초대"]].forEach(([role, title]) => {
      const block = document.createElement("div");
      block.className = "invite-block";
      const label = document.createElement("p");
      label.className = "invite-title";
      label.textContent = title;
      block.append(label);
      if (!links.length) {
        const empty = document.createElement("p");
        empty.textContent = "공유 주소를 찾지 못했습니다.";
        block.append(empty);
      }
      links.forEach((link) => {
        const row = document.createElement("div");
        row.className = "share-link-row";
        const url = withRole(link, role);
        const anchor = document.createElement("a");
        anchor.className = "share-link-url";
        anchor.href = url;
        anchor.textContent = url;
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = "복사";
        button.addEventListener("click", () => copyLink(url));
        row.append(anchor, button);
        block.append(row);
      });
      panel.append(block);
    });
    box.append(panel);
  }
  function watchTables() {
    ["marketTableBody", "wholesaleTable", "orderTable", "inquiryTable", "orderDetailBody"].forEach((id) => {
      const el = document.getElementById(id);
      if (!el || el.dataset.inviteWatch === "1") return;
      el.dataset.inviteWatch = "1";
      new MutationObserver(() => {
        if (locked()) hideSecretColumns();
      }).observe(el, { childList: true });
    });
  }
  function wrapAfter(name) {
    const fn = window[name];
    if (typeof fn !== "function" || fn.inviteHook) return;
    function wrapped() {
      const result = fn.apply(this, arguments);
      const finish = () => { if (locked()) hideSecretColumns(); };
      if (result && typeof result.then === "function") {
        return result.then((value) => { finish(); return value; }, (error) => { finish(); throw error; });
      }
      finish();
      return result;
    }
    wrapped.inviteHook = true;
    window[name] = wrapped;
  }
  function wrapShow() {
    if (typeof showAppView !== "function" || showAppView.inviteHook) return;
    const inner = showAppView;
    function wrapped(name) {
      const result = inner.call(this, allowed(name));
      if (locked()) hideSecretColumns();
      paintBadge();
      return result;
    }
    wrapped.inviteHook = true;
    window.showAppView = wrapped;
  }
  function wrapShare() {
    if (typeof loadShareLinks !== "function" || loadShareLinks.inviteHook) return;
    const inner = loadShareLinks;
    async function wrapped() {
      try {
        return await inner.apply(this, arguments);
      } finally {
        if (state.owner) paintInvitePanel();
      }
    }
    wrapped.inviteHook = true;
    window.loadShareLinks = wrapped;
  }
  function wrapMallId() {
    if (typeof inquiryMallId !== "function" || inquiryMallId.inviteHook) return;
    const inner = inquiryMallId;
    function wrapped(item) {
      if (state.remote) return "";
      return inner.apply(this, arguments);
    }
    wrapped.inviteHook = true;
    window.inquiryMallId = wrapped;
  }
  function showVersion() {
    const label = document.getElementById("appVersion");
    if (label) {
      label.hidden = false;
      label.textContent = "v" + version;
      label.title = "버전 " + version;
    }
    const test = document.body.classList.contains("edition-test");
    document.title = "모두모두AI " + (test ? "배포용" : "마스터") + " v" + version;
  }
  function apply() {
    const on = locked();
    document.body.classList.toggle("invite-remote", on);
    document.body.classList.toggle("invite-products", on && state.role === "products");
    document.body.classList.toggle("invite-orders", on && state.role === "orders");
    document.body.classList.toggle("invite-locked", on && (state.role === "products" || state.role === "orders"));
    document.body.dataset.inviteState = state.remote ? "remote" : state.owner ? "owner" : state.pending ? "pending" : "open";
    if (on) hideSecretColumns();
    else revealSecrets();
    paintBadge();
    if (state.owner) paintInvitePanel();
    const next = allowed(currentView());
    if (next !== currentView() && typeof showAppView === "function") showAppView(next);
  }
  async function detect() {
    if (typeof api !== "function") {
      state.pending = false;
      apply();
      return;
    }
    try {
      await api("/api/share-link", { quiet: true });
      state.owner = true;
      state.remote = false;
    } catch (error) {
      const message = String(error && error.message || "");
      if (/이 컴퓨터에서만|공유 주소/.test(message)) {
        state.remote = true;
        state.owner = false;
      }
    }
    state.pending = false;
    apply();
    watchTables();
  }
  function hook() {
    wrapShow();
    wrapShare();
    wrapMallId();
    ["fillMarketTable", "renderWholesalerSheet", "renderOrders", "renderInquiryRows", "renderOrderDetail"].forEach(wrapAfter);
    showVersion();
    if (typeof applyEdition === "function" && !applyEdition.inquiryVersion6) {
      const inner = applyEdition;
      function wrapped() {
        const result = inner.apply(this, arguments);
        showVersion();
        return result;
      }
      wrapped.inquiryVersion = true;
      wrapped.inquiryVersion3 = true;
      wrapped.inquiryVersion4 = true;
      wrapped.inquiryVersion5 = true;
      wrapped.inquiryVersion6 = true;
      wrapped.inquiryStoreName = true;
      wrapped.inquiryAnswerHook2 = true;
      window.applyEdition = wrapped;
    }
    state.role = readRole();
    if (!state.owner && !state.remote) state.pending = Boolean(state.role);
    apply();
    watchTables();
    if (!state.owner && !state.remote) detect();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", hook);
  else hook();
  setTimeout(hook, 0);
  setTimeout(showVersion, 1400);
  setTimeout(showVersion, 1800);
})();
"""
INVITE_CSS = """
/* admin-invite1 */
body.invite-products #appTabOrders,
body.invite-products #appTabInquiries,
body.invite-products #viewOrders,
body.invite-products #viewInquiries,
body.invite-orders #appTabProducts,
body.invite-orders #appTabCollect,
body.invite-orders #appTabWholesalers,
body.invite-orders #viewProducts,
body.invite-orders #viewCollect,
body.invite-orders #viewWholesalers,
body.invite-remote #marketLoginIdRow,
body.invite-remote #marketLoginPwRow,
body.invite-remote #marketApiKeyRow,
body.invite-remote #marketApiSecretRow,
body.invite-remote #marketVendorRow,
body.invite-remote #marketEsmRow,
body.invite-remote #marketApiAccountRow,
body.invite-remote #marketForm label:has(input[name="login_id"]),
body.invite-remote #marketForm label:has(input[name="login_password"]),
body.invite-remote #marketForm label:has(input[name="api_key"]),
body.invite-remote #marketForm label:has(input[name="api_secret"]),
body.invite-remote #marketForm label:has(input[name="vendor_code"]),
body.invite-remote #marketForm label:has(input[name="esm_id"]),
body.invite-remote #marketForm label:has(input[name="naver_account_id"]),
body.invite-remote #wholesaleForm label:has(input[name="login_id"]),
body.invite-remote #wholesaleForm label:has(input[name="login_password"]),
body.invite-remote .invite-secret {
  display: none !important;
}
.invite-panel { margin-top: 14px; }
.invite-title { margin: 10px 0 6px; font-weight: 700; }
#inviteRoleBadge {
  margin-left: 8px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #1f6b4a;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
}
html[data-theme="dark"] #inviteRoleBadge {
  background: #d7c4a3;
  color: #1c1917;
}
"""


def read_text(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    newline = "\r\n" if "\r\n" in text else "\n"
    return text.replace("\r\n", "\n"), newline


def write_text(path: Path, text: str, newline: str) -> None:
    data = text.replace("\n", newline) if newline == "\r\n" else text
    path.write_bytes(data.encode("utf-8"))


def _patch_inquiry_function(text: str) -> tuple[str, int]:
    start = text.find("function renderInquiryRows")
    if start < 0:
        return text, 0
    end = text.find("\nfunction ", start + 1)
    if end < 0:
        end = len(text)
    body = text[start:end]
    loose = re.compile(
        r'textCell\(\s*item\.(?:order_id|orderId)\s*(?:\|\|\s*["\']["\'])?\s*\)\s*,\s*'
        r'textCell\(\s*item\.(?:product_no|productNo)\s*(?:\|\|\s*["\']["\'])?\s*\)\s*,'
    )
    body, count = loose.subn(ROW_NEW, body, count=1)
    if count != 1:
        return text, 0
    return text[:start] + body + text[end:], 1


def patch_js(text: str) -> str:
    if MARKER in text and "fillInquiryProductLink(item);" in text and "openInquiryOrder(item)" in text:
        return text
    if "function renderInquiryRows" not in text:
        raise SystemExit("renderInquiryRows not found")
    if MARKER not in text:
        text = text.replace("function renderInquiryRows", HELPERS + "function renderInquiryRows", 1)
    if "inquiryNumberButtonCell(item.order_id" not in text:
        text, count = ROW_RE.subn(ROW_NEW, text, count=1)
        if count != 1:
            text, count = _patch_inquiry_function(text)
        if count != 1:
            raise SystemExit("inquiry order/product cells not found")
    if "fillInquiryProductLink(item);" not in text:
        if DETAIL_OLD in text:
            text = text.replace(DETAIL_OLD, DETAIL_NEW, 1)
        else:
            text, count = DETAIL_RE.subn(DETAIL_NEW, text, count=1)
            if count != 1:
                raise SystemExit("inquiry product number cell not found")
    return text


def bump_asset(text: str, name: str, version: str) -> str:
    pattern = re.compile(rf"({re.escape(name)})(?:\?v=[^\"']*)?")
    updated, count = pattern.subn(lambda match: f"{match.group(1)}?v={version}", text, count=1)
    if count != 1 and name == "app.js":
        raise SystemExit("app.js script tag not found")
    return updated


def patch_store_label(text: str) -> str:
    pattern = re.compile(r"(<th>)\s*쇼핑몰\s*ID\s*(</th>\s*<td id=\"inquiryMallId\")")
    return pattern.sub(r"\1스토어명\2", text, count=1)


def patch_html(text: str) -> str:
    text = patch_store_label(text)
    text = bump_asset(text, "styles.css", "admin-invite1")
    return bump_asset(text, "app.js", "admin-invite1")


def patch_answer(text: str) -> str:
    if "/* inquiry-simple2 */" not in text:
        replaced = False
        for pattern in (SIMPLE1_RE, PLACE2_RE, OLD_ANSWER_RE):
            updated, count = pattern.subn(ANSWER_JS.strip() + "\n", text, count=1)
            if count == 1:
                text = updated
                replaced = True
                break
        if not replaced:
            text = text.rstrip() + "\n" + ANSWER_JS
    if "/* inquiry-simple3 */" not in text:
        text = text.rstrip() + "\n" + SIMPLE3_JS
    if "/* product-margin1 */" not in text:
        text = text.rstrip() + "\n" + MARGIN_JS
    if "/* image-work1 */" not in text:
        text = text.rstrip() + "\n" + IMAGE_JS
    if "/* admin-invite1 */" not in text:
        text = text.rstrip() + "\n" + INVITE_JS
    return text


def patch_css(text: str) -> str:
    extra = ""
    if "/* inquiry-simple3 */" not in text:
        if "inquiry-send-under-date" not in text:
            extra += ANSWER_CSS
        if "inquiry-answer-place2" not in text:
            extra += ANSWER_CSS2
        if "/* inquiry-simple1 */" not in text:
            extra += SIMPLE_CSS
        if "/* inquiry-simple2 */" not in text:
            extra += SIMPLE_CSS2
        extra += SIMPLE3_CSS
    if "/* product-margin1 */" not in text:
        extra += MARGIN_CSS
    if "/* image-work1 */" not in text:
        extra += IMAGE_CSS
    if "/* admin-invite1 */" not in text:
        extra += INVITE_CSS
    if not extra:
        return text
    return text.rstrip() + "\n" + extra


def write_screen_version(root: Path) -> bool:
    targets = [root / "version.txt"]
    app_version = root / "app" / "version.txt"
    if app_version.is_file():
        targets.append(app_version)
    changed = False
    payload = (SCREEN_VERSION + "\r\n").encode("utf-8")
    for path in targets:
        current = path.read_text(encoding="utf-8-sig").strip() if path.is_file() else ""
        if current == SCREEN_VERSION:
            continue
        path.write_bytes(payload)
        changed = True
    return changed


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\smartstore uploader")
    static = root / "app" / "static"
    js_path = static / "app.js"
    html_path = static / "index.html"
    css_path = static / "styles.css"
    if not js_path.is_file() or not html_path.is_file():
        raise SystemExit(f"static files not found: {static}")
    js, js_nl = read_text(js_path)
    html, html_nl = read_text(html_path)
    css, css_nl = read_text(css_path) if css_path.is_file() else ("", "\n")
    try:
        new_js = patch_js(js)
    except SystemExit as exc:
        print(exc)
        new_js = js
    new_js = patch_answer(new_js)
    new_html = patch_html(html)
    new_css = patch_css(css) if css else css
    version_changed = write_screen_version(root)
    if new_js == js and new_html == html and new_css == css and not version_changed:
        print("already linked")
        return
    for path in (js_path, html_path, css_path):
        if not path.is_file():
            continue
        backup = path.with_name(path.name + ".bak-inquiry-links")
        if not backup.exists():
            backup.write_bytes(path.read_bytes())
    write_text(js_path, new_js, js_nl)
    write_text(html_path, new_html, html_nl)
    if css_path.is_file():
        write_text(css_path, new_css, css_nl)
    print("inquiry links on")
    raise SystemExit(10)


if __name__ == "__main__":
    main()
