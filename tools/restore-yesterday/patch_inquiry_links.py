"""Turn inquiry order and product numbers into links. Leaves the rest of the program alone."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import zipfile
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
SCREEN_VERSION = "2026.10.28.25"
SELLER_UPDATE_URL = "https://github.com/MODUMODUAI/smartstore-uploader/releases/latest/download/latest.json"
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
NAME_JS = r"""
/* name-fix1 */
(function () {
  const version = "2026.10.28.7";
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
    showVersion();
    if (typeof applyEdition === "function" && !applyEdition.inquiryVersion7) {
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
      wrapped.inquiryVersion7 = true;
      wrapped.inquiryStoreName = true;
      wrapped.inquiryAnswerHook2 = true;
      window.applyEdition = wrapped;
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", hook);
  else hook();
  setTimeout(hook, 0);
  setTimeout(showVersion, 2000);
  setTimeout(showVersion, 2400);
})();
"""
NAME_JS2 = r"""
/* name-fix2 */
(function () {
  const version = "2026.10.28.8";
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
    showVersion();
    if (typeof applyEdition === "function" && !applyEdition.inquiryVersion8) {
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
      wrapped.inquiryVersion7 = true;
      wrapped.inquiryVersion8 = true;
      wrapped.inquiryStoreName = true;
      wrapped.inquiryAnswerHook2 = true;
      window.applyEdition = wrapped;
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", hook);
  else hook();
  setTimeout(hook, 0);
  setTimeout(showVersion, 2800);
  setTimeout(showVersion, 3200);
})();
"""
INVITE_SETTINGS_JS = r"""
/* invite-settings1 */
(function () {
  const version = "2026.10.28.9";
  let owner = false;
  let links = [];

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

  function hideHelpCopy() {
    document.querySelectorAll("#helpShare #invitePanel").forEach((el) => el.remove());
  }

  function watchHelp() {
    const help = document.getElementById("helpShare");
    if (!help || help.dataset.inviteSettingsWatch === "1") return;
    help.dataset.inviteSettingsWatch = "1";
    new MutationObserver(() => hideHelpCopy()).observe(help, { childList: true });
    hideHelpCopy();
  }

  function paint() {
    const page = document.querySelector("#viewSettings .settings-page");
    if (!page || !owner) {
      const stale = document.getElementById("settingsInvite");
      if (stale) stale.remove();
      return;
    }
    let card = document.getElementById("settingsInvite");
    if (!card) {
      card = document.createElement("div");
      card.id = "settingsInvite";
      card.className = "settings-card";
      const theme = document.getElementById("setup-theme");
      if (theme && theme.parentElement === page) page.insertBefore(card, theme);
      else page.prepend(card);
    }
    card.replaceChildren();
    const title = document.createElement("h3");
    title.textContent = "관리자초대";
    const head = document.createElement("p");
    head.className = "hint";
    head.textContent = "상품관리와 주문관리를 나눠 보냅니다. 초대받은 화면에는 마켓과 공급사 로그인 정보가 나오지 않습니다.";
    card.append(title, head);
    const rows = links.length ? links : ((typeof cachedShareLinks !== "undefined" && cachedShareLinks) || []);
    [["products", "상품관리 초대"], ["orders", "주문관리 초대"]].forEach(([role, labelText]) => {
      const block = document.createElement("div");
      block.className = "invite-block";
      const label = document.createElement("p");
      label.className = "invite-title";
      label.textContent = labelText;
      block.append(label);
      if (!rows.length) {
        const empty = document.createElement("p");
        empty.className = "hint";
        empty.textContent = "공유 주소를 찾지 못했습니다.";
        block.append(empty);
      }
      rows.forEach((link) => {
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
      card.append(block);
    });
  }

  async function load() {
    watchHelp();
    hideHelpCopy();
    if (typeof api !== "function") return;
    try {
      const data = await api("/api/share-link", { quiet: true });
      owner = true;
      links = (data && data.links) || [];
      if (typeof cachedShareLinks !== "undefined" && links.length) cachedShareLinks = links.slice();
    } catch (error) {
      const message = String((error && error.message) || "");
      if (/이 컴퓨터에서만|공유 주소/.test(message)) {
        owner = false;
        const stale = document.getElementById("settingsInvite");
        if (stale) stale.remove();
      }
      return;
    }
    paint();
  }

  function wrapShow() {
    if (typeof showAppView !== "function" || showAppView.inviteSettingsHook) return;
    const inner = showAppView;
    function wrapped(name) {
      const result = inner.apply(this, arguments);
      hideHelpCopy();
      const view = document.getElementById("viewSettings");
      if (name === "settings" || (view && !view.hidden)) load();
      return result;
    }
    wrapped.inviteHook = true;
    wrapped.inviteSettingsHook = true;
    window.showAppView = wrapped;
  }

  function hook() {
    showVersion();
    if (typeof applyEdition === "function" && !applyEdition.inquiryVersion9) {
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
      wrapped.inquiryVersion7 = true;
      wrapped.inquiryVersion8 = true;
      wrapped.inquiryVersion9 = true;
      wrapped.inquiryStoreName = true;
      wrapped.inquiryAnswerHook2 = true;
      window.applyEdition = wrapped;
    }
    wrapShow();
    watchHelp();
    hideHelpCopy();
    load();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", hook);
  else hook();
  setTimeout(hook, 0);
  setTimeout(showVersion, 3600);
  setTimeout(showVersion, 4000);
})();
"""
INVITE_SETTINGS_CSS = """
/* invite-settings1 */
#helpShare #invitePanel { display: none !important; }
body.invite-remote #settingsInvite { display: none !important; }
#settingsInvite { margin-bottom: 12px; }
#settingsInvite .invite-title { margin: 12px 0 6px; font-weight: 700; }
"""

ADMIN_MENU_JS = r"""
/* admin-menu1 */
(function () {
  const version = "2026.10.28.10";
  const storeKey = "modumodu-admin-managers";
  const rolesKey = "modumodu-invite-roles";
  const legacyRoleKey = "modumodu-invite-role";
  const duties = [
    { id: "products", label: "상품관리", views: ["products", "collect"] },
    { id: "orders", label: "주문관리", views: ["orders"] },
    { id: "inquiries", label: "문의관리", views: ["inquiries"] },
  ];
  const dutyIds = duties.map((item) => item.id);
  const state = { roles: new Set(), owner: false, remote: false, pending: false, links: [] };
  let editingId = "";

  function parseDuties(value) {
    const found = new Set();
    String(value || "").split(/[,\s]+/).forEach((item) => {
      if (dutyIds.includes(item)) found.add(item);
    });
    return found;
  }

  function rememberRoles(roles) {
    const list = dutyIds.filter((id) => roles.has(id));
    try {
      if (list.length) sessionStorage.setItem(rolesKey, list.join(","));
      else sessionStorage.removeItem(rolesKey);
    } catch (error) {}
  }

  function readRoles() {
    const params = new URLSearchParams(location.search);
    const listed = parseDuties(params.get("roles"));
    if (listed.size) {
      rememberRoles(listed);
      return listed;
    }
    const legacy = params.get("role");
    if (legacy === "products" || legacy === "orders") {
      const roles = new Set([legacy]);
      if (legacy === "orders") roles.add("inquiries");
      rememberRoles(roles);
      return roles;
    }
    try {
      const saved = parseDuties(sessionStorage.getItem(rolesKey));
      if (saved.size) return saved;
      const old = sessionStorage.getItem(legacyRoleKey);
      if (old === "products") return new Set(["products"]);
      if (old === "orders") return new Set(["orders", "inquiries"]);
    } catch (error) {}
    return new Set();
  }

  function isLocked() {
    if (state.owner || !state.roles.size) return false;
    return state.remote || state.pending;
  }

  function viewAllowed(name) {
    if (name === "help") return true;
    return duties.some((item) => state.roles.has(item.id) && item.views.includes(name));
  }

  function gate(name) {
    if (!isLocked()) return name;
    if (viewAllowed(name)) return name;
    for (const item of duties) {
      if (state.roles.has(item.id)) return item.views[0];
    }
    return "help";
  }

  function showVersion() {
    const label = document.getElementById("appVersion");
    if (label && label.textContent !== "v" + version) {
      label.hidden = false;
      label.textContent = "v" + version;
      label.title = "버전 " + version;
    }
    const test = document.body.classList.contains("edition-test");
    const title = "모두모두AI " + (test ? "배포용" : "마스터") + " v" + version;
    if (document.title !== title) document.title = title;
  }

  function paintLock() {
    const locked = isLocked();
    document.body.classList.toggle("admin-locked", locked);
    duties.forEach((item) => {
      const on = locked && state.roles.has(item.id);
      item.views.forEach((view) => document.body.classList.toggle("admin-allow-" + view, on));
    });
    const badge = document.getElementById("inviteRoleBadge");
    if (!locked) {
      if (badge && badge.dataset.adminMenu === "1") badge.remove();
      return;
    }
    let chip = badge;
    if (!chip) {
      chip = document.createElement("span");
      chip.id = "inviteRoleBadge";
      const tabs = document.querySelector(".app-tabs");
      if (tabs) tabs.after(chip);
    }
    if (chip) {
      chip.dataset.adminMenu = "1";
      chip.textContent = duties.filter((item) => state.roles.has(item.id)).map((item) => item.label).join(" · ");
    }
  }

  function currentView() {
    const names = ["products", "orders", "inquiries", "collect", "wholesalers", "settings", "help"];
    for (const name of names) {
      const el = document.getElementById("view" + name.charAt(0).toUpperCase() + name.slice(1));
      if (el && !el.hidden) return name;
    }
    return "products";
  }

  function settleView() {
    if (!isLocked() || typeof showAppView !== "function") return;
    const now = currentView();
    const next = gate(now);
    if (next !== now) showAppView(next);
  }

  function productWrite(item) {
    return item.includes("/products")
      || item.includes("/images")
      || item.includes("/register")
      || item.includes("/notices")
      || item.includes("/delivery")
      || item.includes("/price-sets")
      || item.includes("/excel-forms")
      || item.includes("/stock-jobs")
      || item.includes("/product-refresh")
      || item.includes("/product-market");
  }

  function denied(path, method) {
    if (!isLocked()) return "";
    const item = String(path || "").split("?")[0];
    const write = method !== "GET" && method !== "HEAD";
    const credential = "아이디, 패스워드, 관리자키는 그대로 둡니다.";
    if (write && (item === "/api/settings" || item.startsWith("/api/settings/"))) return credential;
    if (write && (item === "/api/markets" || /^\/api\/markets\/[^/]+$/.test(item) || /^\/api\/markets\/[^/]+\/test$/.test(item))) return credential;
    if (write && (item === "/api/wholesalers" || /^\/api\/wholesalers\/[^/]+$/.test(item))) return "공급처 로그인 정보는 바꿀 수 없습니다.";
    if (item.includes("/wholesalers/") && item.endsWith("/login")) return "공급처 로그인 정보는 바꿀 수 없습니다.";
    if (write && !state.roles.has("products") && productWrite(item)) return "상품관리 권한이 없습니다.";
    if (write && !state.roles.has("products") && item.includes("/wholesalers/") && /\/(import|collect|stock-check|catalog|categories|open-product)/.test(item)) return "상품관리 권한이 없습니다.";
    if (write && !state.roles.has("orders") && item.includes("/orders")) return "주문관리 권한이 없습니다.";
    if (write && !state.roles.has("inquiries") && (item.includes("/inquiries") || /\/answer$/.test(item))) return "문의관리 권한이 없습니다.";
    return "";
  }

  function wrapApi() {
    if (typeof api !== "function" || api.adminMenuHook) return;
    const inner = api;
    async function wrapped(path, options) {
      const method = String((options && options.method) || "GET").toUpperCase();
      const reason = denied(path, method);
      if (reason) throw new Error(reason);
      return inner.apply(this, arguments);
    }
    wrapped.adminMenuHook = true;
    window.api = wrapped;
  }

  function wrapShow() {
    if (typeof showAppView !== "function" || showAppView.adminMenuHook) return;
    const inner = showAppView;
    function wrapped(name) {
      const next = gate(name);
      const result = inner.call(this, next);
      paintLock();
      if (next === "settings" && state.owner) ensureOwnerUi();
      return result;
    }
    wrapped.adminMenuHook = true;
    wrapped.inviteHook = true;
    wrapped.inviteSettingsHook = true;
    window.showAppView = wrapped;
  }

  function hideOldCard() {
    document.querySelectorAll("#settingsInvite, #helpShare #invitePanel").forEach((el) => el.remove());
  }

  function watchOldCard() {
    const page = document.querySelector("#viewSettings .settings-page");
    if (page && page.dataset.adminMenuWatch !== "1") {
      page.dataset.adminMenuWatch = "1";
      new MutationObserver(() => hideOldCard()).observe(page, { childList: true });
    }
    const help = document.getElementById("helpShare");
    if (help && help.dataset.adminMenuWatch !== "1") {
      help.dataset.adminMenuWatch = "1";
      new MutationObserver(() => hideOldCard()).observe(help, { childList: true });
    }
    hideOldCard();
  }

  function loadManagers() {
    try {
      const parsed = JSON.parse(localStorage.getItem(storeKey) || "[]");
      return Array.isArray(parsed) ? parsed.filter((item) => item && item.id && Array.isArray(item.duties)) : [];
    } catch (error) {
      return [];
    }
  }

  function saveManagers(items) {
    localStorage.setItem(storeKey, JSON.stringify(items));
  }

  function dutyLabel(list) {
    return duties.filter((item) => list.includes(item.id)).map((item) => item.label).join(", ");
  }

  function formatDate(iso) {
    const text = new Intl.DateTimeFormat("en-CA", {
      timeZone: "Asia/Seoul",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(new Date(iso));
    return text.replaceAll("-", ".") + ".";
  }

  function buildUrl(base, list) {
    const url = new URL(base, location.href);
    const chosen = dutyIds.filter((id) => list.includes(id));
    url.searchParams.set("roles", chosen.join(","));
    url.searchParams.delete("role");
    if (chosen.length === 1 && chosen[0] === "products") url.searchParams.set("role", "products");
    if (chosen.includes("orders") && chosen.includes("inquiries") && !chosen.includes("products")) url.searchParams.set("role", "orders");
    return url.toString();
  }

  function defaultName(list) {
    const labels = duties.filter((item) => list.includes(item.id)).map((item) => item.label);
    return (labels.join("·") || "매니저") + " 매니저";
  }

  async function copyLink(url) {
    if (typeof copyText === "function") await copyText(url);
    else if (navigator.clipboard) await navigator.clipboard.writeText(url);
    else throw new Error("copy");
  }

  function selectedDuties() {
    return [...document.querySelectorAll("#adminInviteForm input[name='adminDuty']:checked")].map((input) => input.value);
  }

  function fillDuties(list) {
    document.querySelectorAll("#adminInviteForm input[name='adminDuty']").forEach((input) => {
      input.checked = list.includes(input.value);
    });
  }

  function renderManagers() {
    const body = document.querySelector("#adminManagerTable tbody");
    const count = document.getElementById("adminManagerCount");
    if (!body) return;
    const items = loadManagers();
    if (count) count.textContent = "관리자 " + items.length + "명";
    body.replaceChildren();
    if (!items.length) {
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = 5;
      cell.textContent = "초대한 관리자가 없습니다. 관리자 초대로 매니저를 보내세요.";
      row.append(cell);
      body.append(row);
      return;
    }
    items.forEach((item) => {
      const row = document.createElement("tr");
      const name = document.createElement("td");
      name.textContent = item.name || defaultName(item.duties);
      const work = document.createElement("td");
      const workText = document.createElement("span");
      workText.textContent = dutyLabel(item.duties);
      const change = document.createElement("button");
      change.type = "button";
      change.textContent = "변경";
      change.addEventListener("click", () => openForm(item));
      work.append(workText, change);
      const link = document.createElement("td");
      const url = buildUrl(item.base, item.duties);
      const shown = document.createElement("span");
      shown.className = "admin-link";
      shown.textContent = url;
      shown.title = url;
      const copy = document.createElement("button");
      copy.type = "button";
      copy.textContent = "복사";
      copy.addEventListener("click", async () => {
        try {
          await copyLink(url);
          if (typeof toast === "function") toast("초대 링크를 복사했습니다.");
        } catch (error) {
          if (typeof toast === "function") toast("복사에 실패했습니다.", true);
        }
      });
      link.append(shown, copy);
      const date = document.createElement("td");
      date.textContent = item.created ? formatDate(item.created) : "";
      const removeCell = document.createElement("td");
      const remove = document.createElement("button");
      remove.type = "button";
      remove.textContent = "삭제";
      remove.addEventListener("click", () => {
        if (!window.confirm("이 관리자를 목록에서 지울까요? 이미 보낸 주소는 계속 열립니다.")) return;
        saveManagers(loadManagers().filter((saved) => saved.id !== item.id));
        renderManagers();
      });
      removeCell.append(remove);
      row.append(name, work, link, date, removeCell);
      body.append(row);
    });
  }

  function openForm(item) {
    const form = document.getElementById("adminInviteForm");
    const name = document.getElementById("adminInviteName");
    const submit = document.getElementById("adminInviteSubmit");
    if (!form || !name || !submit) return;
    editingId = item ? item.id : "";
    name.value = item ? item.name : "";
    fillDuties(item ? item.duties : []);
    const picker = document.getElementById("adminInviteBase");
    if (picker) {
      picker.replaceChildren();
      state.links.forEach((link) => {
        const option = document.createElement("option");
        option.value = link;
        option.textContent = link;
        picker.append(option);
      });
      picker.closest("label").hidden = state.links.length < 2;
      if (item && item.base) picker.value = item.base;
    }
    submit.textContent = item ? "수정 링크 복사" : "초대 링크 복사";
    form.hidden = false;
    name.focus();
  }

  function closeForm() {
    const form = document.getElementById("adminInviteForm");
    if (form) form.hidden = true;
    editingId = "";
  }

  async function submitInvite(event) {
    event.preventDefault();
    const chosen = dutyIds.filter((id) => selectedDuties().includes(id));
    if (!chosen.length) {
      if (typeof toast === "function") toast("담당업무를 하나 이상 고르세요.", true);
      return;
    }
    const picker = document.getElementById("adminInviteBase");
    const base = (picker && picker.value) || state.links[0] || "";
    if (!base) {
      if (typeof toast === "function") toast("공유 주소를 찾지 못했습니다.", true);
      return;
    }
    const name = document.getElementById("adminInviteName");
    const items = loadManagers();
    const current = editingId ? items.find((item) => item.id === editingId) : null;
    const record = {
      id: current ? current.id : String(Date.now()),
      name: (name && name.value.trim()) || defaultName(chosen),
      duties: chosen,
      base,
      created: current ? current.created : new Date().toISOString(),
    };
    const next = current ? items.map((item) => item.id === record.id ? record : item) : [record, ...items];
    saveManagers(next);
    renderManagers();
    const url = buildUrl(base, chosen);
    try {
      await copyLink(url);
      if (typeof toast === "function") toast(current ? "담당업무를 바꿔 링크를 복사했습니다." : "관리자 초대 링크를 복사했습니다.");
    } catch (error) {
      if (typeof toast === "function") toast("목록에는 넣었지만 복사에 실패했습니다.", true);
    }
    closeForm();
  }

  function ensureOwnerUi() {
    const tabs = document.querySelector("#viewSettings .settings-tabs");
    const page = document.querySelector("#viewSettings .settings-page");
    if (!tabs || !page) return;
    if (!document.getElementById("settingsTabAdmins")) {
      const button = document.createElement("button");
      button.type = "button";
      button.id = "settingsTabAdmins";
      button.className = "tab";
      button.textContent = "관리자 관리";
      button.addEventListener("click", () => showAdminPane());
      tabs.append(button);
    }
    if (document.getElementById("settingsPaneAdmins")) return;
    const pane = document.createElement("div");
    pane.id = "settingsPaneAdmins";
    pane.className = "settings-pane";
    pane.hidden = true;
    const card = document.createElement("div");
    card.className = "settings-card";
    const head = document.createElement("div");
    head.className = "settings-card-head";
    const title = document.createElement("h3");
    title.textContent = "관리자 목록";
    const invite = document.createElement("button");
    invite.type = "button";
    invite.id = "adminInviteOpen";
    invite.textContent = "관리자 초대";
    invite.addEventListener("click", () => openForm(null));
    head.append(title, invite);
    const notes = document.createElement("ul");
    notes.className = "admin-manager-notes";
    [
      "상품관리, 주문관리, 문의관리 매니저를 나눠 초대합니다.",
      "아이디, 패스워드, 관리자키는 그대로입니다. 초대받은 화면에는 나오지 않고 바꿀 수 없습니다.",
      "초대받은 관리자는 맡은 기능만 사용할 수 있습니다. 상품관리에는 상품담기가 포함됩니다.",
      "목록에서 지워도 이미 보낸 주소는 계속 열립니다.",
    ].forEach((text) => {
      const item = document.createElement("li");
      item.textContent = text;
      notes.append(item);
    });
    const form = document.createElement("form");
    form.id = "adminInviteForm";
    form.className = "admin-invite-form";
    form.hidden = true;
    const nameLabel = document.createElement("label");
    nameLabel.textContent = "이름";
    const nameInput = document.createElement("input");
    nameInput.id = "adminInviteName";
    nameInput.maxLength = 40;
    nameInput.placeholder = "예: 상품관리 매니저";
    nameLabel.append(nameInput);
    const work = document.createElement("div");
    work.className = "admin-duty-list";
    duties.forEach((item) => {
      const label = document.createElement("label");
      label.className = "check";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.name = "adminDuty";
      input.value = item.id;
      label.append(input, document.createTextNode(item.label));
      work.append(label);
    });
    const baseLabel = document.createElement("label");
    baseLabel.textContent = "보낼 주소";
    const base = document.createElement("select");
    base.id = "adminInviteBase";
    baseLabel.append(base);
    baseLabel.hidden = true;
    const actions = document.createElement("div");
    actions.className = "settings-actions";
    const submit = document.createElement("button");
    submit.type = "submit";
    submit.id = "adminInviteSubmit";
    submit.textContent = "초대 링크 복사";
    const cancel = document.createElement("button");
    cancel.type = "button";
    cancel.textContent = "취소";
    cancel.addEventListener("click", () => closeForm());
    actions.append(submit, cancel);
    form.append(nameLabel, work, baseLabel, actions);
    form.addEventListener("submit", (event) => {
      submitInvite(event).catch((error) => {
        if (typeof toast === "function") toast(error.message || "초대에 실패했습니다.", true);
      });
    });
    const count = document.createElement("p");
    count.id = "adminManagerCount";
    count.className = "admin-manager-count";
    const wrap = document.createElement("div");
    wrap.className = "delivery-table-wrap admin-manager-table-wrap";
    const table = document.createElement("table");
    table.className = "delivery-table";
    table.id = "adminManagerTable";
    const headRow = document.createElement("tr");
    ["이름", "담당업무", "초대 링크", "초대일", "삭제"].forEach((text) => {
      const cell = document.createElement("th");
      cell.textContent = text;
      headRow.append(cell);
    });
    const thead = document.createElement("thead");
    thead.append(headRow);
    const tbody = document.createElement("tbody");
    table.append(thead, tbody);
    wrap.append(table);
    card.append(head, notes, form, count, wrap);
    pane.append(card);
    page.append(pane);
    renderManagers();
  }

  function showAdminPane() {
    ensureOwnerUi();
    const pane = document.getElementById("settingsPaneAdmins");
    const form = document.getElementById("settingsForm");
    const market = document.getElementById("marketForm");
    const theme = document.getElementById("setup-theme");
    if (form) form.hidden = true;
    if (market) market.hidden = true;
    if (theme) theme.hidden = true;
    if (pane) pane.hidden = false;
    ["settingsTabApi", "settingsTabMarkets", "settingsTabLicense"].forEach((id) => {
      const tab = document.getElementById(id);
      if (tab) tab.classList.remove("active");
    });
    const tab = document.getElementById("settingsTabAdmins");
    if (tab) tab.classList.add("active");
    renderManagers();
  }

  function hideAdminPane() {
    const pane = document.getElementById("settingsPaneAdmins");
    const theme = document.getElementById("setup-theme");
    const tab = document.getElementById("settingsTabAdmins");
    if (pane) pane.hidden = true;
    if (theme) theme.hidden = false;
    if (tab) tab.classList.remove("active");
  }

  function wrapSettings() {
    if (typeof showSettingsPane !== "function" || showSettingsPane.adminMenuHook) return;
    const inner = showSettingsPane;
    function wrapped(name) {
      if (name === "admins") {
        showAdminPane();
        return;
      }
      hideAdminPane();
      return inner.apply(this, arguments);
    }
    wrapped.adminMenuHook = true;
    window.showSettingsPane = wrapped;
  }

  function watchVersion() {
    const label = document.getElementById("appVersion");
    if (!label || label.dataset.adminMenuVersion === "1") return;
    label.dataset.adminMenuVersion = "1";
    new MutationObserver(() => showVersion()).observe(label, { childList: true, characterData: true, subtree: true });
  }

  function watchTabs() {
    const tabs = document.querySelector(".app-tabs");
    if (!tabs || tabs.dataset.adminMenuClick === "1") return;
    tabs.dataset.adminMenuClick = "1";
    const viewById = {
      appTabProducts: "products",
      appTabOrders: "orders",
      appTabInquiries: "inquiries",
      appTabCollect: "collect",
      appTabWholesalers: "wholesalers",
      appTabSettings: "settings",
      appTabHelp: "help",
    };
    tabs.addEventListener("click", (event) => {
      if (!isLocked()) return;
      const button = event.target.closest("button");
      const name = button && viewById[button.id];
      if (!name || gate(name) === name) return;
      event.preventDefault();
      event.stopPropagation();
      if (typeof showAppView === "function") showAppView(gate(name));
    }, true);
  }

  async function detect() {
    if (typeof api !== "function") {
      state.pending = false;
      paintLock();
      settleView();
      document.documentElement.dataset.adminMenu = "ready";
      return;
    }
    try {
      const data = await api("/api/share-link", { quiet: true });
      state.owner = true;
      state.remote = false;
      state.pending = false;
      state.links = (data && data.links) || [];
      if (typeof cachedShareLinks !== "undefined" && state.links.length) cachedShareLinks = state.links.slice();
      ensureOwnerUi();
    } catch (error) {
      const message = String((error && error.message) || "");
      if (/이 컴퓨터에서만|공유 주소/.test(message)) {
        state.remote = true;
        state.owner = false;
      }
      state.pending = false;
    }
    paintLock();
    settleView();
    document.documentElement.dataset.adminMenu = "ready";
  }

  function hook() {
    state.roles = readRoles();
    if (!state.owner && !state.remote && state.roles.size) state.pending = true;
    showVersion();
    watchVersion();
    wrapApi();
    wrapShow();
    wrapSettings();
    watchTabs();
    watchOldCard();
    paintLock();
    if (typeof applyEdition === "function" && !applyEdition.adminMenuHook) {
      const inner = applyEdition;
      function wrapped() {
        const result = inner.apply(this, arguments);
        showVersion();
        return result;
      }
      wrapped.inquiryVersion9 = true;
      wrapped.inquiryVersion10 = true;
      wrapped.adminMenuHook = true;
      window.applyEdition = wrapped;
    }
    if (!state.owner && !state.remote) detect();
    else document.documentElement.dataset.adminMenu = "ready";
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", hook);
  else hook();
  setTimeout(hook, 0);
  setTimeout(paintLock, 400);
  setTimeout(paintLock, 1400);
  setTimeout(showVersion, 6500);
  setTimeout(showVersion, 8000);
})();
"""
ADMIN_MENU_CSS = """
/* admin-menu1 */
#settingsInvite { display: none !important; }
#helpShare #invitePanel { display: none !important; }
.admin-manager-count { margin: 0 0 8px; font-weight: 700; }
.admin-manager-notes {
  margin: 0 0 12px;
  padding: 8px 12px 8px 28px;
  border: 1px solid var(--line);
  background: var(--surface);
}
.admin-duty-list { display: flex; gap: 14px; flex-wrap: wrap; margin: 4px 0 8px; }
.admin-invite-form { margin-bottom: 8px; }
.admin-manager-table-wrap { height: auto; max-height: none; }
#adminManagerTable { table-layout: auto; }
#adminManagerTable tbody tr { cursor: default; }
#adminManagerTable td { white-space: normal; }
#adminManagerTable .admin-link {
  display: inline-block;
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
  margin-right: 6px;
}
#adminManagerTable button { margin-left: 6px; }
body.admin-locked:not(.admin-allow-products) #appTabProducts,
body.admin-locked:not(.admin-allow-products) #viewProducts,
body.admin-locked:not(.admin-allow-collect) #appTabCollect,
body.admin-locked:not(.admin-allow-collect) #viewCollect,
body.admin-locked:not(.admin-allow-orders) #appTabOrders,
body.admin-locked:not(.admin-allow-orders) #viewOrders,
body.admin-locked:not(.admin-allow-inquiries) #appTabInquiries,
body.admin-locked:not(.admin-allow-inquiries) #viewInquiries,
body.admin-locked #appTabWholesalers,
body.admin-locked #viewWholesalers,
body.admin-locked #appTabSettings,
body.admin-locked #viewSettings,
body.admin-locked #marketSidebarSettings,
body.admin-locked #collectOpenWholesalers,
body.admin-locked #collectEmptyOpenWholesalers,
body.admin-locked #marketLoginIdRow,
body.admin-locked #marketLoginPwRow,
body.admin-locked #marketApiKeyRow,
body.admin-locked #marketApiSecretRow,
body.admin-locked #marketVendorRow,
body.admin-locked #marketEsmRow,
body.admin-locked #marketApiAccountRow,
body.admin-locked #marketForm label:has(input[name="login_id"]),
body.admin-locked #marketForm label:has(input[name="login_password"]),
body.admin-locked #marketForm label:has(input[name="api_key"]),
body.admin-locked #marketForm label:has(input[name="api_secret"]),
body.admin-locked #marketForm label:has(input[name="vendor_code"]),
body.admin-locked #marketForm label:has(input[name="esm_id"]),
body.admin-locked #marketForm label:has(input[name="naver_account_id"]),
body.admin-locked #wholesaleForm label:has(input[name="login_id"]),
body.admin-locked #wholesaleForm label:has(input[name="login_password"]) {
  display: none !important;
}
"""


_OLD_LINK = "모두모두AI 배포용".encode("utf-8")
_NEW_LINK = "모두모두AI 셀러용".encode("utf-8")
if len(_OLD_LINK) != len(_NEW_LINK):
    raise RuntimeError("seller shortcut byte length mismatch")

SELLER_JS = r"""
/* seller-edition1 */
(function () {
  const version = "2026.10.28.11";
  const secretNames = ["login_id", "login_password", "api_key", "api_secret", "vendor_code", "esm_id", "naver_account_id"];

  function isSeller() {
    return document.body.classList.contains("edition-seller") || document.body.classList.contains("edition-test");
  }

  function showVersion() {
    const label = document.getElementById("appVersion");
    const seller = isSeller();
    const editionName = seller ? "셀러용" : "마스터";
    if (label && label.textContent !== "v" + version) {
      label.hidden = false;
      label.textContent = "v" + version;
      label.title = "버전 " + version;
    }
    const badge = document.getElementById("appEdition");
    if (badge && seller && badge.textContent !== "셀러용") badge.textContent = "셀러용";
    const title = "모두모두AI " + editionName + " v" + version;
    if (document.title !== title) document.title = title;
  }

  function takeVersionLabel() {
    const label = document.getElementById("appVersion");
    if (!label || label.dataset.sellerVersion === "1") return;
    const fresh = label.cloneNode(true);
    fresh.dataset.sellerVersion = "1";
    label.replaceWith(fresh);
    new MutationObserver(() => showVersion()).observe(fresh, { childList: true, characterData: true, subtree: true });
  }

  function isSecretHeader(cell) {
    const text = (cell.textContent || "").replace(/\s+/g, "");
    if (!text || text.length > 24) return false;
    return /아이디|패스워드|비밀번호|아이디키|시크릿키|관리자키|업체코드|ESMID|로그인/.test(text);
  }

  function hideSecrets() {
    if (!isSeller()) return;
    secretNames.forEach((name) => {
      document.querySelectorAll("[name='" + name + "']").forEach((input) => {
        const row = input.closest(".delivery-row, label, tr");
        if (row) row.classList.add("seller-secret");
        input.disabled = true;
        input.readOnly = true;
      });
    });
    document.querySelectorAll("table").forEach((table) => {
      const headerRows = table.tHead ? [...table.tHead.rows] : [...table.rows].filter((row) => [...row.cells].some((cell) => cell.tagName === "TH"));
      const secretIndex = new Set();
      headerRows.forEach((row) => {
        [...row.cells].forEach((cell, index) => {
          if (!isSecretHeader(cell)) return;
          secretIndex.add(index);
          cell.classList.add("seller-secret");
        });
      });
      if (!secretIndex.size) return;
      [...table.tBodies].forEach((body) => {
        [...body.rows].forEach((row) => {
          if (row.cells.length === 1 && row.cells[0].colSpan > 1) return;
          secretIndex.forEach((index) => {
            const cell = row.cells[index];
            if (!cell || cell.querySelector("input, select, textarea")) return;
            cell.classList.add("seller-secret");
            cell.textContent = "";
          });
        });
      });
    });
  }

  function watchTables() {
    ["marketTableBody", "wholesaleTable"].forEach((id) => {
      const el = document.getElementById(id);
      if (!el || el.dataset.sellerWatch === "1") return;
      el.dataset.sellerWatch = "1";
      new MutationObserver(() => hideSecrets()).observe(el, { childList: true });
    });
  }

  function ensureHelp() {
    const overview = document.getElementById("help-overview");
    if (overview && !document.getElementById("sellerHelpNote")) {
      const note = document.createElement("p");
      note.id = "sellerHelpNote";
      note.textContent = "셀러용에는 로그인 정보와 상품 URL 수집이 없습니다. 마켓 아이디, 패스워드, 관리자키, 공급처 로그인 칸이 없고, 주소로 상품을 수집하는 칸도 없습니다.";
      overview.append(note);
    }
    if (overview && !document.getElementById("sellerInstallNote")) {
      const install = document.createElement("p");
      install.id = "sellerInstallNote";
      install.textContent = "구매자는 모두모두AI-셀러용-설치.exe 로 설치합니다. 설치한 뒤에는 실행할 때 업데이트를 받을 수 있습니다.";
      const note = document.getElementById("sellerHelpNote");
      if (note) note.after(install);
      else overview.append(install);
    }
    const nav = document.getElementById("helpNav");
    if (nav && !nav.querySelector("[data-help='help-admins']")) {
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.help = "help-admins";
      button.textContent = "관리자 관리";
      const data = nav.querySelector("[data-help='help-data']");
      if (data) data.before(button);
      else nav.append(button);
    }
    const body = document.getElementById("helpBody");
    if (body && !document.getElementById("help-admins")) {
      const section = document.createElement("section");
      section.className = "help-panel";
      section.id = "help-admins";
      section.dataset.helpPanel = "help-admins";
      section.hidden = true;
      const title = document.createElement("h2");
      title.textContent = "관리자 관리";
      const lead = document.createElement("p");
      lead.textContent = "설정 > 관리자 관리에서 상품관리, 주문관리, 문의관리 매니저를 초대합니다. 아이디, 패스워드, 관리자키는 그대로 두고, 초대받은 관리자는 맡은 기능만 사용합니다. 상품관리에는 상품담기가 포함됩니다. 목록에서 지워도 이미 보낸 주소는 계속 열립니다.";
      const extra = document.createElement("p");
      extra.textContent = "셀러용 화면에는 로그인 정보와 상품 URL 수집이 없습니다.";
      section.append(title, lead, extra);
      const data = document.getElementById("help-data");
      if (data) data.before(section);
      else body.append(section);
    }
  }

  function deny(message) {
    const error = new Error(message);
    if (typeof toast === "function") toast(message, true);
    throw error;
  }

  function wrapNamed(name, message) {
    const fn = window[name];
    if (typeof fn !== "function" || fn.sellerHook) return;
    function wrapped() {
      if (isSeller()) deny(message);
      return fn.apply(this, arguments);
    }
    wrapped.sellerHook = true;
    window[name] = wrapped;
  }

  function blockSecretSaves() {
    ["marketForm", "wholesaleForm"].forEach((id) => {
      const form = document.getElementById(id);
      if (!form || form.dataset.sellerBlock === "1") return;
      form.dataset.sellerBlock = "1";
      form.addEventListener("submit", (event) => {
        if (!isSeller()) return;
        event.preventDefault();
        event.stopImmediatePropagation();
        deny("셀러용에는 로그인 정보를 넣을 수 없습니다.");
      }, true);
    });
    const collect = document.getElementById("collectForm");
    if (collect && collect.dataset.sellerBlock !== "1") {
      collect.dataset.sellerBlock = "1";
      collect.addEventListener("submit", (event) => {
        if (!isSeller()) return;
        event.preventDefault();
        event.stopImmediatePropagation();
        deny("셀러용에는 상품 URL 수집이 없습니다.");
      }, true);
    }
  }

  function wrapEdition() {
    if (typeof applyEdition !== "function" || applyEdition.sellerHook) return;
    const inner = applyEdition;
    function wrapped(edition, screenVersion) {
      const seller = edition === "test" || edition === "seller";
      const result = inner.call(this, seller ? "test" : edition, screenVersion);
      document.body.classList.toggle("edition-seller", seller);
      if (seller) document.body.classList.add("edition-test");
      paint();
      return result;
    }
    wrapped.sellerHook = true;
    wrapped.inquiryVersion = true;
    wrapped.inquiryVersion10 = true;
    wrapped.adminMenuHook = true;
    window.applyEdition = wrapped;
  }

  function paint() {
    showVersion();
    ensureHelp();
    blockSecretSaves();
    if (isSeller()) hideSecrets();
    watchTables();
  }

  function hook() {
    takeVersionLabel();
    wrapEdition();
    wrapNamed("saveMarketForm", "셀러용에는 로그인 정보를 넣을 수 없습니다.");
    wrapNamed("saveWholesalerForm", "셀러용에는 로그인 정보를 넣을 수 없습니다.");
    wrapNamed("collectNow", "셀러용에는 상품 URL 수집이 없습니다.");
    paint();
    if (typeof loadEdition === "function" && !loadEdition.sellerHook) {
      const inner = loadEdition;
      function wrapped() {
        const result = inner.apply(this, arguments);
        const finish = () => paint();
        if (result && typeof result.then === "function") {
          return result.then((value) => { finish(); return value; }, (error) => { finish(); throw error; });
        }
        finish();
        return result;
      }
      wrapped.sellerHook = true;
      window.loadEdition = wrapped;
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", hook);
  else hook();
  setTimeout(hook, 0);
  setTimeout(showVersion, 9000);
  setTimeout(showVersion, 11000);
})();
"""

SELLER_CSS = """
/* seller-edition1 */
body.edition-seller #collectForm,
body.edition-seller #helpUrlCollect,
body.edition-seller #marketLoginIdRow,
body.edition-seller #marketLoginPwRow,
body.edition-seller #marketApiKeyRow,
body.edition-seller #marketApiSecretRow,
body.edition-seller #marketVendorRow,
body.edition-seller #marketEsmRow,
body.edition-seller #marketApiAccountRow,
body.edition-seller #marketForm label:has(input[name="login_id"]),
body.edition-seller #marketForm label:has(input[name="login_password"]),
body.edition-seller #marketForm label:has(input[name="api_key"]),
body.edition-seller #marketForm label:has(input[name="api_secret"]),
body.edition-seller #marketForm label:has(input[name="vendor_code"]),
body.edition-seller #marketForm label:has(input[name="esm_id"]),
body.edition-seller #marketForm label:has(input[name="naver_account_id"]),
body.edition-seller #wholesaleForm label:has(input[name="login_id"]),
body.edition-seller #wholesaleForm label:has(input[name="login_password"]),
body.edition-seller #collectOpenWholesalers,
body.edition-seller #collectEmptyOpenWholesalers,
body.edition-seller .seller-secret {
  display: none !important;
}
"""

SELLER_LOGIN_JS = r"""
/* seller-login1 */
(function () {
  const storageKey = "modumodu-seller-session";

  function isSeller() {
    return document.body.classList.contains("edition-seller") || document.body.classList.contains("edition-test");
  }

  function digits(value) {
    let number = String(value || "").replace(/\D/g, "");
    if (number.startsWith("82") && number.length >= 11) number = "0" + number.slice(2);
    return number;
  }

  function validPhone(value) {
    return /^01[016789]\d{7,8}$/.test(digits(value));
  }

  function formatPhone(value) {
    const number = digits(value);
    if (number.length === 11) return number.slice(0, 3) + "-" + number.slice(3, 7) + "-" + number.slice(7);
    if (number.length === 10) return number.slice(0, 3) + "-" + number.slice(3, 6) + "-" + number.slice(6);
    return number;
  }

  function readPhone() {
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey) || "");
      if (saved && validPhone(saved.phone)) return digits(saved.phone);
    } catch (error) {}
    return "";
  }

  function savePhone(phone) {
    localStorage.setItem(storageKey, JSON.stringify({ phone: digits(phone) }));
  }

  function clearPhone() {
    localStorage.removeItem(storageKey);
  }

  function field(labelText, id, type, autocomplete) {
    const label = document.createElement("label");
    label.htmlFor = id;
    label.textContent = labelText;
    const input = document.createElement("input");
    input.id = id;
    input.type = type;
    input.autocomplete = autocomplete;
    input.required = true;
    if (type === "tel") input.inputMode = "numeric";
    label.append(input);
    return label;
  }

  function ensureGate() {
    let gate = document.getElementById("sellerLogin");
    if (gate) return gate;
    gate = document.createElement("div");
    gate.id = "sellerLogin";
    gate.role = "dialog";
    gate.setAttribute("aria-modal", "true");
    gate.setAttribute("aria-labelledby", "sellerLoginTitle");
    const card = document.createElement("form");
    card.className = "seller-login-card";
    const title = document.createElement("h1");
    title.id = "sellerLoginTitle";
    const a = document.createElement("span");
    a.className = "brand-a";
    a.textContent = "모두";
    const b = document.createElement("span");
    b.className = "brand-b";
    b.textContent = "모두";
    const ai = document.createElement("span");
    ai.className = "brand-ai";
    ai.textContent = "AI";
    title.append(a, b, ai, document.createTextNode(" 셀러용"));
    const lead = document.createElement("p");
    lead.textContent = "시험 단계입니다. 본인 전화번호와 비밀번호를 입력하면 들어갑니다.";
    const error = document.createElement("p");
    error.id = "sellerLoginError";
    error.setAttribute("role", "alert");
    const submit = document.createElement("button");
    submit.type = "submit";
    submit.textContent = "들어가기";
    card.append(title, lead, field("전화번호", "sellerLoginPhone", "tel", "tel"), field("비밀번호", "sellerLoginPassword", "password", "current-password"), error, submit);
    card.addEventListener("submit", (event) => {
      event.preventDefault();
      const phone = document.getElementById("sellerLoginPhone").value;
      const password = document.getElementById("sellerLoginPassword").value;
      if (!validPhone(phone)) {
        error.textContent = "본인 전화번호를 입력해 주세요.";
        return;
      }
      if (!String(password || "").trim()) {
        error.textContent = "비밀번호를 입력해 주세요.";
        return;
      }
      savePhone(phone);
      document.getElementById("sellerLoginPassword").value = "";
      error.textContent = "";
      paint();
    });
    gate.append(card);
    document.body.append(gate);
    return gate;
  }

  function ensureAccount() {
    let account = document.getElementById("sellerAccount");
    if (account) return account;
    const bar = document.querySelector(".titlebar");
    if (!bar) return null;
    account = document.createElement("span");
    account.id = "sellerAccount";
    account.className = "seller-account";
    const phone = document.createElement("span");
    phone.id = "sellerAccountPhone";
    const button = document.createElement("button");
    button.type = "button";
    button.id = "sellerLogout";
    button.textContent = "로그아웃";
    button.addEventListener("click", () => {
      clearPhone();
      paint();
    });
    account.append(phone, button);
    const quit = document.getElementById("appQuit");
    if (quit) quit.before(account);
    else bar.append(account);
    return account;
  }

  function ensureLoginNote() {
    const overview = document.getElementById("help-overview");
    if (!overview || document.getElementById("sellerLoginNote")) return;
    const note = document.createElement("p");
    note.id = "sellerLoginNote";
    note.textContent = "프로그램에 들어갈 때는 본인 전화번호와 비밀번호를 입력합니다. 시험 단계에서는 그 번호와 비밀번호로 바로 들어갑니다.";
    const install = document.getElementById("sellerInstallNote");
    const help = document.getElementById("sellerHelpNote");
    if (install) install.after(note);
    else if (help) help.after(note);
    else overview.append(note);
  }

  function paint() {
    const seller = isSeller();
    const phone = seller ? readPhone() : "";
    const locked = seller && !phone;
    document.body.classList.toggle("seller-locked", locked);
    if (locked) {
      const gate = ensureGate();
      gate.hidden = false;
      const input = document.getElementById("sellerLoginPhone");
      if (input && document.activeElement === document.body) input.focus();
    } else {
      const gate = document.getElementById("sellerLogin");
      if (gate) gate.hidden = true;
    }
    const account = seller && phone ? ensureAccount() : document.getElementById("sellerAccount");
    if (account) {
      account.hidden = !phone;
      const label = document.getElementById("sellerAccountPhone");
      if (label) label.textContent = formatPhone(phone);
    }
    if (seller) ensureLoginNote();
    [...document.body.children].forEach((child) => {
      if (child.id === "sellerLogin") return;
      if (locked) child.setAttribute("inert", "");
      else child.removeAttribute("inert");
    });
  }

  function hook() {
    paint();
    if (document.body.dataset.sellerLoginWatch === "1") return;
    document.body.dataset.sellerLoginWatch = "1";
    new MutationObserver(() => paint()).observe(document.body, { attributes: true, attributeFilter: ["class"] });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", hook);
  else hook();
  setTimeout(hook, 0);
  setTimeout(paint, 400);
  setTimeout(paint, 1200);
})();
"""

SELLER_LOGIN_CSS = """
/* seller-login1 */
body.seller-locked { overflow: hidden; }
#sellerLogin {
  position: fixed;
  inset: 0;
  z-index: 8000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(17, 17, 17, 0.48);
}
#sellerLogin[hidden] { display: none !important; }
.seller-login-card {
  width: min(420px, 100%);
  margin: 0;
  padding: 28px 24px 22px;
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--line);
  border-radius: 16px;
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.18);
}
.seller-login-card h1 {
  margin: 0 0 8px;
  font-size: 22px;
  letter-spacing: -0.04em;
}
.seller-login-card .brand-a { color: #0b5cab; }
.seller-login-card .brand-b { color: #3d9eed; }
.seller-login-card .brand-ai { color: #111; }
.seller-login-card p { margin: 0 0 14px; color: var(--muted); font-size: 13px; line-height: 1.5; font-weight: 400; }
.seller-login-card label { font-size: 13px; font-weight: 700; }
.seller-login-card input { font-size: 16px; padding: 8px 10px; border-radius: 8px; }
.seller-login-card button[type="submit"] {
  width: 100%;
  margin-top: 6px;
  padding: 10px 12px;
  background: #0b5cab;
  border-color: #084a8a;
  border-radius: 8px;
  color: #fff;
  font-size: 15px;
  font-weight: 700;
}
#sellerLoginError { min-height: 1.2em; color: #b42318; font-weight: 700; }
.seller-account { display: inline-flex; align-items: center; gap: 6px; }
#sellerAccount[hidden] { display: none !important; }
#sellerLogout { padding: 3px 8px; }
"""

SELLER_LOGIN2_JS = r"""
/* seller-login2 */
(function () {
  let accountURL = "http://127.0.0.1:8790";
  const loginPorts = [8790, 8791, 8792, 8793, 8794, 8795, 18790, 28790, 9876, 18081, 29170];
  async function useAccount() {
    if (window.__sellerLoginTest) return accountURL;
    try {
      const response = await fetch("/static/seller-login-port.txt?v=" + Date.now(), { cache: "no-store" });
      if (response.ok) {
        const port = String(await response.text()).trim();
        if (/^\d+$/.test(port)) {
          accountURL = "http://127.0.0.1:" + port;
          return accountURL;
        }
      }
    } catch (error) {}
    for (const port of loginPorts) {
      try {
        const response = await fetch("http://127.0.0.1:" + port + "/api/seller-status", { cache: "no-store" });
        if (response.ok) {
          accountURL = "http://127.0.0.1:" + port;
          return accountURL;
        }
      } catch (error) {}
    }
    throw new Error(offlineMessage);
  }
  const sessionKey = "modumodu-seller-session";
  const accountKey = "modumodu-seller-account";
  const offlineMessage = "로그인 서비스를 찾지 못했습니다. 모두모두AI-셀러용-설치.exe 를 다시 실행해 주세요.";

  function isSeller() {
    return document.body.classList.contains("edition-seller") || document.body.classList.contains("edition-test");
  }

  function digits(value) {
    let number = String(value || "").replace(/\D/g, "");
    if (number.startsWith("82") && number.length >= 11) number = "0" + number.slice(2);
    return number;
  }

  function validPhone(value) {
    return /^01[016789]\d{7,8}$/.test(digits(value));
  }

  function formatPhone(value) {
    const number = digits(value);
    if (number.length === 11) return number.slice(0, 3) + "-" + number.slice(3, 7) + "-" + number.slice(7);
    if (number.length === 10) return number.slice(0, 3) + "-" + number.slice(3, 6) + "-" + number.slice(6);
    return number;
  }

  function formatCode(password) {
    const code = String(password || "").replace(/\s+/g, "");
    if (code.length === 8) return code.slice(0, 4) + " " + code.slice(4);
    return code;
  }

  function postSync(path, body) {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", accountURL + path, false);
    xhr.setRequestHeader("Content-Type", "application/json");
    try {
      xhr.send(JSON.stringify(body || {}));
    } catch (error) {
      throw new Error(offlineMessage);
    }
    const data = JSON.parse(xhr.responseText || "{}");
    if (xhr.status < 200 || xhr.status >= 300) throw new Error(data.error || "로그인하지 못했습니다.");
    return data;
  }

  async function post(path, body) {
    if (window.__sellerLoginTest) return postSync(path, body);
    await useAccount();
    let response;
    try {
      response = await fetch(accountURL + path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body || {})
      });
    } catch (error) {
      throw new Error(offlineMessage);
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || "로그인하지 못했습니다.");
    return data;
  }

  function showError(message) {
    const box = document.getElementById("sellerLoginError");
    if (box) box.textContent = message || "";
  }

  function remember(phone) {
    const number = digits(phone);
    localStorage.setItem(sessionKey, JSON.stringify({ phone: number }));
    localStorage.setItem(accountKey, number);
  }

  function forget() {
    localStorage.removeItem(sessionKey);
    localStorage.removeItem(accountKey);
  }

  function refreshOldGate() {
    document.body.classList.toggle("seller-login-sync");
  }

  function labelWrap(text, id, input) {
    const label = document.createElement("label");
    label.id = id;
    label.textContent = text;
    label.append(input);
    return label;
  }

  function rebuild() {
    const gate = document.getElementById("sellerLogin");
    if (!gate || gate.dataset.login2 === "1") return;
    gate.dataset.login2 = "1";
    while (gate.firstChild) gate.removeChild(gate.firstChild);
    const card = document.createElement("form");
    card.className = "seller-login-card";
    const title = document.createElement("h1");
    title.id = "sellerLoginTitle";
    const a = document.createElement("span");
    a.className = "brand-a";
    a.textContent = "모두";
    const b = document.createElement("span");
    b.className = "brand-b";
    b.textContent = "모두";
    const ai = document.createElement("span");
    ai.className = "brand-ai";
    ai.textContent = "AI";
    title.append(a, b, ai, document.createTextNode(" 셀러용"));
    const lead = document.createElement("p");
    lead.textContent = "전화번호를 입력하면 비밀번호를 발급합니다. 같은 전화번호와 그 비밀번호로 들어오면 같은 데이터가 열립니다.";
    const phone = document.createElement("input");
    phone.id = "sellerLoginPhone";
    phone.type = "tel";
    phone.autocomplete = "off";
    phone.setAttribute("name", "modumodu-seller-phone");
    phone.inputMode = "numeric";
    phone.required = true;
    const check = document.createElement("button");
    check.type = "button";
    check.id = "sellerLoginCheck";
    check.textContent = "확인";
    const issued = document.createElement("div");
    issued.id = "sellerIssued";
    issued.hidden = true;
    const issuedLead = document.createElement("p");
    issuedLead.textContent = "이 전화번호의 비밀번호입니다. 적어 두세요.";
    const issuedPassword = document.createElement("p");
    issuedPassword.id = "sellerIssuedPassword";
    issued.append(issuedLead, issuedPassword);
    const password = document.createElement("input");
    password.id = "sellerLoginPassword";
    password.type = "password";
    password.autocomplete = "current-password";
    const passwordRow = labelWrap("비밀번호", "sellerPasswordRow", password);
    passwordRow.hidden = true;
    const error = document.createElement("p");
    error.id = "sellerLoginError";
    error.setAttribute("role", "alert");
    const enter = document.createElement("button");
    enter.type = "button";
    enter.id = "sellerLoginEnter";
    enter.hidden = true;
    enter.textContent = "들어가기";
    card.append(title, lead, labelWrap("전화번호", "sellerPhoneRow", phone), check, issued, passwordRow, error, enter);
    check.addEventListener("click", async () => {
      showError("");
      if (!validPhone(phone.value)) {
        showError("본인 전화번호를 입력해 주세요.");
        return;
      }
      check.disabled = true;
      try {
        const data = await post("/api/seller-login", { phone: phone.value });
        issued.hidden = data.status !== "new";
        passwordRow.hidden = data.status === "new";
        enter.hidden = false;
        if (data.status === "new") {
          issuedPassword.textContent = formatCode(data.password);
          enter.dataset.password = data.password;
          enter.textContent = "이 비밀번호로 들어가기";
        } else {
          issuedPassword.textContent = "";
          delete enter.dataset.password;
          enter.textContent = "들어가기";
          password.value = "";
          password.focus();
        }
      } catch (error) {
        showError(error.message);
      } finally {
        check.disabled = false;
      }
    });
    enter.addEventListener("click", async () => {
      showError("");
      const typed = enter.dataset.password || password.value;
      if (!String(typed || "").trim()) {
        showError("비밀번호를 입력해 주세요.");
        return;
      }
      enter.disabled = true;
      try {
        await post("/api/seller-enter", { phone: phone.value, password: typed });
        remember(phone.value);
        if (window.__sellerLoginTest) {
          document.body.dataset.sellerEntered = digits(phone.value);
          refreshOldGate();
          return;
        }
        location.reload();
      } catch (error) {
        showError(error.message);
      } finally {
        enter.disabled = false;
      }
    });
    gate.append(card);
  }

  async function syncStatus() {
    if (!isSeller()) return;
    rebuild();
    try {
      let data = {};
      if (window.__sellerLoginTest) {
        const xhr = new XMLHttpRequest();
        xhr.open("GET", accountURL + "/api/seller-status", false);
        xhr.send();
        data = JSON.parse(xhr.responseText || "{}");
      } else {
        await useAccount();
        const response = await fetch(accountURL + "/api/seller-status");
        data = await response.json();
      }
      if (data.phone && validPhone(data.phone)) remember(data.phone);
      else forget();
    } catch (error) {
      forget();
    }
    const note = document.getElementById("sellerLoginNote");
    if (note) note.textContent = "처음 쓰는 전화번호에는 비밀번호를 발급합니다. 같은 전화번호와 그 비밀번호로 다시 들어오면 같은 데이터가 열립니다.";
    refreshOldGate();
  }

  document.addEventListener("click", async (event) => {
    const button = event.target && event.target.closest ? event.target.closest("#sellerLogout") : null;
    if (!button || !isSeller()) return;
    event.preventDefault();
    event.stopPropagation();
    try { await post("/api/seller-logout", {}); } catch (error) {}
    forget();
    if (window.__sellerLoginTest) {
      document.body.dataset.sellerEntered = "";
      refreshOldGate();
      return;
    }
    location.reload();
  }, true);

  function hook() {
    if (!document.body.dataset.sellerLogin2Watch) {
      document.body.dataset.sellerLogin2Watch = "1";
      new MutationObserver(() => hook()).observe(document.body, { attributes: true, attributeFilter: ["class"] });
    }
    if (!isSeller()) return;
    rebuild();
    if (document.body.dataset.sellerStatus === "1") return;
    document.body.dataset.sellerStatus = "1";
    syncStatus();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", hook);
  else hook();
  setTimeout(hook, 0);
})();
"""

SELLER_PHONE_JS = r"""
/* seller-phone1 */
(function () {
  function mailFilled(value) {
    return /[A-Za-z@]/.test(String(value || ""));
  }

  function clearMail(input) {
    if (!mailFilled(input.value) && !mailFilled(input.getAttribute("value"))) return;
    input.value = "";
    input.setAttribute("value", "");
  }

  function harden(input) {
    if (!input || input.dataset.sellerPhoneGuard === "1") return;
    input.dataset.sellerPhoneGuard = "1";
    input.autocomplete = "off";
    input.setAttribute("autocomplete", "off");
    input.setAttribute("name", "modumodu-seller-phone");
    input.readOnly = true;
    const unlock = () => { input.readOnly = false; };
    input.addEventListener("pointerdown", unlock);
    input.addEventListener("focus", unlock);
    input.addEventListener("input", () => clearMail(input));
    clearMail(input);
    setTimeout(() => clearMail(input), 50);
    setTimeout(() => clearMail(input), 400);
    setTimeout(() => clearMail(input), 1200);
  }

  function sweep() {
    document.querySelectorAll("#sellerLoginPhone").forEach(harden);
    const form = document.querySelector("#sellerLogin form");
    if (form) form.setAttribute("autocomplete", "off");
  }

  function hook() {
    sweep();
    if (document.body.dataset.sellerPhoneGuard === "1") return;
    document.body.dataset.sellerPhoneGuard = "1";
    new MutationObserver(() => sweep()).observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", hook);
  else hook();
  setTimeout(hook, 0);
  setTimeout(sweep, 300);
})();
"""

SELLER_PEEK_JS = r"""
/* seller-peek1 */
(function () {
  function attach(input) {
    if (!input || input.dataset.sellerPeek === "1") return;
    input.dataset.sellerPeek = "1";
    input.type = "password";
    const line = document.createElement("span");
    line.className = "seller-password-line";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "seller-peek";
    button.textContent = "미리보기";
    button.setAttribute("aria-pressed", "false");
    button.addEventListener("click", () => {
      const open = input.type === "password";
      input.type = open ? "text" : "password";
      button.textContent = open ? "가리기" : "미리보기";
      button.setAttribute("aria-pressed", open ? "true" : "false");
    });
    input.before(line);
    line.append(input, button);
  }

  function sweep() {
    document.querySelectorAll("#sellerLoginPassword").forEach(attach);
  }

  function hook() {
    sweep();
    if (document.body.dataset.sellerPeekWatch === "1") return;
    document.body.dataset.sellerPeekWatch = "1";
    new MutationObserver(() => sweep()).observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", hook);
  else hook();
  setTimeout(hook, 0);
  setTimeout(sweep, 300);
})();
"""

SELLER_PEEK_CSS = """
/* seller-peek1 */
.seller-password-line {
  display: flex;
  gap: 8px;
  align-items: center;
  width: 100%;
}
.seller-password-line input {
  flex: 1;
  min-width: 0;
  width: auto;
}
.seller-peek {
  flex: 0 0 auto;
  margin-top: 0;
  padding: 8px 10px;
  border-radius: 8px;
  background: #fff;
  color: #0b5cab;
  border: 1px solid #0b5cab;
  font-size: 13px;
  font-weight: 700;
}
"""

SELLER_PORT_JS = r"""
/* seller-port1 */
(function () {
  function onSellerPort() {
    return String(location.port || "") === "8788";
  }

  function markSeller() {
    document.body.classList.add("edition-seller");
    document.body.classList.add("edition-test");
    const badge = document.getElementById("appEdition");
    if (badge) badge.textContent = "셀러용";
    const shown = (document.getElementById("appVersion") || {}).textContent || "";
    const version = String(shown).replace(/^v/, "").trim();
    document.title = version ? "모두모두AI 셀러용 v" + version : "모두모두AI 셀러용";
  }

  if (typeof applyEdition === "function" && !applyEdition.sellerPortHook) {
    const inner = applyEdition;
    function wrapped(edition, screenVersion) {
      if (onSellerPort()) edition = "test";
      const result = inner.call(this, edition, screenVersion);
      if (onSellerPort()) markSeller();
      return result;
    }
    wrapped.sellerPortHook = true;
    window.applyEdition = wrapped;
  }

  function force() {
    if (!onSellerPort() || typeof applyEdition !== "function") return;
    const label = document.getElementById("appVersion");
    const version = label ? String(label.textContent || "").replace(/^v/, "").trim() : "";
    applyEdition("test", version);
    markSeller();
  }

  force();
  setTimeout(force, 0);
  setTimeout(force, 400);
  setTimeout(force, 1200);
})();
"""

MASTER_LOGIN_JS = r"""
/* master-login1 */
(function () {
  const storageKey = "modumodu-master-gate";
  const password = "9020917";

  function isSellerScreen() {
    if (String(location.port || "") === "8788") return true;
    return document.body.classList.contains("edition-seller") || document.body.classList.contains("edition-test");
  }

  function unlocked() {
    try {
      return sessionStorage.getItem(storageKey) === "1";
    } catch (error) {
      return false;
    }
  }

  function ensureGate() {
    let gate = document.getElementById("masterLogin");
    if (gate) return gate;
    gate = document.createElement("div");
    gate.id = "masterLogin";
    gate.role = "dialog";
    gate.setAttribute("aria-modal", "true");
    gate.setAttribute("aria-labelledby", "masterLoginTitle");
    const card = document.createElement("form");
    card.className = "master-login-card";
    const title = document.createElement("h1");
    title.id = "masterLoginTitle";
    const a = document.createElement("span");
    a.className = "brand-a";
    a.textContent = "모두";
    const b = document.createElement("span");
    b.className = "brand-b";
    b.textContent = "모두";
    const ai = document.createElement("span");
    ai.className = "brand-ai";
    ai.textContent = "AI";
    title.append(a, b, ai, document.createTextNode(" 마스터"));
    const lead = document.createElement("p");
    lead.textContent = "비밀번호를 입력하면 들어갑니다.";
    const label = document.createElement("label");
    label.htmlFor = "masterLoginPassword";
    label.textContent = "비밀번호";
    const input = document.createElement("input");
    input.id = "masterLoginPassword";
    input.type = "password";
    input.autocomplete = "current-password";
    input.required = true;
    label.append(input);
    const error = document.createElement("p");
    error.id = "masterLoginError";
    error.setAttribute("role", "alert");
    const submit = document.createElement("button");
    submit.type = "submit";
    submit.textContent = "들어가기";
    card.append(title, lead, label, error, submit);
    card.addEventListener("submit", (event) => {
      event.preventDefault();
      const typed = String(input.value || "").trim();
      if (typed !== password) {
        error.textContent = "비밀번호가 맞지 않습니다.";
        input.focus();
        return;
      }
      try { sessionStorage.setItem(storageKey, "1"); } catch (error) {}
      input.value = "";
      error.textContent = "";
      document.body.dataset.masterEntered = "1";
      paint();
    });
    gate.append(card);
    document.body.append(gate);
    return gate;
  }

  function paint() {
    const locked = !isSellerScreen() && !unlocked();
    document.body.classList.toggle("master-locked", locked);
    if (locked) {
      const gate = ensureGate();
      gate.hidden = false;
      const input = document.getElementById("masterLoginPassword");
      if (input && document.activeElement === document.body) input.focus();
    } else {
      const gate = document.getElementById("masterLogin");
      if (gate) gate.hidden = true;
    }
    [...document.body.children].forEach((child) => {
      if (child.id === "masterLogin" || child.id === "sellerLogin") return;
      if (locked) child.setAttribute("inert", "");
      else if (!document.body.classList.contains("seller-locked")) child.removeAttribute("inert");
    });
  }

  function hook() {
    paint();
    if (document.body.dataset.masterLoginWatch === "1") return;
    document.body.dataset.masterLoginWatch = "1";
    new MutationObserver(() => paint()).observe(document.body, { attributes: true, attributeFilter: ["class"] });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", hook);
  else hook();
  setTimeout(hook, 0);
  setTimeout(paint, 400);
})();
"""

MASTER_LOGIN_CSS = """
/* master-login1 */
body.master-locked { overflow: hidden; }
#masterLogin {
  position: fixed;
  inset: 0;
  z-index: 8100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(17, 17, 17, 0.48);
}
#masterLogin[hidden] { display: none !important; }
.master-login-card {
  width: min(420px, 100%);
  margin: 0;
  padding: 28px 24px 22px;
  background: #fff;
  color: #111;
  border: 1px solid #e4e4e4;
  border-radius: 16px;
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.18);
}
.master-login-card h1 {
  margin: 0 0 8px;
  font-size: 22px;
  letter-spacing: -0.04em;
}
.master-login-card .brand-a { color: #0b5cab; }
.master-login-card .brand-b { color: #3d9eed; }
.master-login-card .brand-ai { color: #111; }
.master-login-card p { margin: 0 0 14px; color: #667085; font-size: 13px; line-height: 1.5; font-weight: 400; }
.master-login-card label { display: block; font-size: 13px; font-weight: 700; }
.master-login-card input {
  display: block;
  width: 100%;
  box-sizing: border-box;
  margin-top: 6px;
  font-size: 16px;
  padding: 8px 10px;
  border: 1px solid #d0d5dd;
  border-radius: 8px;
}
.master-login-card button[type="submit"] {
  width: 100%;
  margin-top: 6px;
  padding: 10px 12px;
  background: #0b5cab;
  border: 1px solid #084a8a;
  border-radius: 8px;
  color: #fff;
  font-size: 15px;
  font-weight: 700;
}
#masterLoginError { min-height: 1.2em; color: #b42318; font-weight: 700; }
"""

SELLER_LOGIN2_CSS = """
/* seller-login2 */
#sellerIssuedPassword {
  margin: 8px 0 12px;
  padding: 12px 8px;
  font-size: 28px;
  letter-spacing: 0.14em;
  text-align: center;
  font-weight: 800;
  font-family: Consolas, "Malgun Gothic", monospace;
  background: var(--soft);
  border-radius: 8px;
}
#sellerLoginCheck, #sellerLoginEnter {
  width: 100%;
  margin-top: 6px;
  padding: 10px 12px;
  background: #0b5cab;
  border-color: #084a8a;
  border-radius: 8px;
  color: #fff;
  font-size: 15px;
  font-weight: 700;
}
"""

SELLER_LOGIN_NOTE = (
    '<p id="sellerLoginNote">처음 쓰는 전화번호에는 비밀번호를 발급합니다. '
    "같은 전화번호와 그 비밀번호로 다시 들어오면 같은 데이터가 열립니다.</p>"
)

SELLER_HELP = """모두모두AI 셀러용

구매자가 설치해서 쓰는 판매용 프로그램입니다.
처음 쓰는 전화번호에는 비밀번호를 발급합니다. 같은 전화번호와 그 비밀번호로 다시 들어오면 같은 데이터가 열립니다.
마켓 아이디, 패스워드, 관리자키, 공급처 로그인, 상품 URL 수집은 없습니다.
상품담기, 상품관리, 주문관리, 문의관리, 공급처, 설정은 사용할 수 있습니다.

설치
1. 모두모두AI-셀러용-설치.exe 를 더블클릭합니다.
2. 설치가 끝나면 바탕화면의 모두모두AI 셀러용을 누릅니다.
3. 브라우저에서 셀러용 로그인 창이 열립니다. 주소는 http://127.0.0.1:8788 입니다.
4. 프로그램을 끝낼 때는 화면 위쪽의 종료를 누릅니다.

업데이트
새 버전이 있으면 모두모두AI 셀러용을 실행할 때 안내가 나옵니다.
동의하면 파일을 받고, 이 컴퓨터의 상품과 설정은 그대로 둡니다.

마켓 아이디, 패스워드, 관리자키, 공급처 로그인은 나오지 않습니다.
"""

SELLER_README = """모두모두AI 셀러용 설치

1. 모두모두AI-셀러용-설치.exe 를 더블클릭합니다.
2. 설치가 끝나면 바탕화면의 모두모두AI 셀러용을 누릅니다.
3. 브라우저에서 셀러용 로그인 창이 열립니다. 주소는 http://127.0.0.1:8788 입니다.
4. 새 버전이 있으면 실행할 때 업데이트 안내가 나옵니다. 상품과 설정은 그대로 둡니다.
로그인 창이 뜨지 않으면 모두모두AI-셀러용-설치.exe 를 다시 실행합니다.
5. 처음 쓰는 전화번호에는 비밀번호를 발급합니다. 같은 전화번호와 그 비밀번호로 다시 들어오면 같은 데이터가 열립니다.

마켓 아이디, 패스워드, 관리자키, 공급처 로그인, 상품 URL 수집은 없습니다.
"""

SELLER_INSTALL_NOTE = (
    '<p id="sellerInstallNote">구매자는 모두모두AI-셀러용-설치.exe 로 설치합니다. '
    "설치한 뒤에는 실행할 때 업데이트를 받을 수 있습니다.</p>"
)

SELLER_NOTE_HTML = (
    "<!-- seller-help1 -->\n"
    '<p id="sellerHelpNote">셀러용에는 로그인 정보와 상품 URL 수집이 없습니다. '
    "마켓 아이디, 패스워드, 관리자키, 공급처 로그인 칸이 없고, 주소로 상품을 수집하는 칸도 없습니다.</p>"
)
ADMIN_HELP_BUTTON = '<button type="button" data-help="help-admins">관리자 관리</button>'
ADMIN_HELP_SECTION = """<section class="help-panel" id="help-admins" data-help-panel="help-admins" hidden>
<h2>관리자 관리</h2>
<p>설정 &gt; 관리자 관리에서 상품관리, 주문관리, 문의관리 매니저를 초대합니다. 아이디, 패스워드, 관리자키는 그대로 두고, 초대받은 관리자는 맡은 기능만 사용합니다. 상품관리에는 상품담기가 포함됩니다. 목록에서 지워도 이미 보낸 주소는 계속 열립니다.</p>
<p>셀러용 화면에는 로그인 정보와 상품 URL 수집이 없습니다.</p>
</section>
"""
SETTINGS_HELP_NOTE = "셀러용에는 아이디, 패스워드, 아이디키, 시크릿키, 업체코드, ESM ID, 판매자 account_id 칸이 없습니다."
WHOLESALE_HELP_NOTE = "셀러용에는 로그인 아이디와 비밀번호 칸이 없습니다."


def patch_help(text: str) -> str:
    text = text.replace("배포용", "셀러용")
    if 'id="sellerHelpNote"' not in text:
        closing = "프로그램을 끝낼 때는 위쪽의 종료를 누릅니다.</p>"
        if closing in text:
            text = text.replace(closing, closing + "\n" + SELLER_NOTE_HTML, 1)
        else:
            token = 'id="help-overview"'
            pos = text.find(token)
            if pos >= 0:
                end = text.find(">", pos)
                if end >= 0:
                    text = text[: end + 1] + "\n" + SELLER_NOTE_HTML + text[end + 1 :]
    if 'id="sellerInstallNote"' not in text and 'id="sellerHelpNote"' in text:
        pos = text.find('id="sellerHelpNote"')
        end = text.find("</p>", pos)
        if end >= 0:
            text = text[: end + 4] + "\n" + SELLER_INSTALL_NOTE + text[end + 4 :]
    if 'id="sellerLoginNote"' not in text and 'id="sellerHelpNote"' in text:
        anchor = 'id="sellerInstallNote"' if 'id="sellerInstallNote"' in text else 'id="sellerHelpNote"'
        pos = text.find(anchor)
        end = text.find("</p>", pos)
        if end >= 0:
            text = text[: end + 4] + "\n" + SELLER_LOGIN_NOTE + text[end + 4 :]
    text = text.replace(
        "프로그램에 들어갈 때는 본인 전화번호와 비밀번호를 입력합니다. 시험 단계에서는 그 번호와 비밀번호로 바로 들어갑니다.",
        "처음 쓰는 전화번호에는 비밀번호를 발급합니다. 같은 전화번호와 그 비밀번호로 다시 들어오면 같은 데이터가 열립니다.",
    )
    if 'data-help="help-admins"' not in text:
        needle = 'data-help="help-data"'
        pos = text.find(needle)
        if pos >= 0:
            start = text.rfind("<button", 0, pos)
            if start >= 0:
                text = text[:start] + ADMIN_HELP_BUTTON + "\n        " + text[start:]
    if 'id="help-admins"' not in text:
        needle = 'id="help-data"'
        pos = text.find(needle)
        if pos >= 0:
            start = text.rfind("<section", 0, pos)
            if start >= 0:
                text = text[:start] + ADMIN_HELP_SECTION + text[start:]
    if SETTINGS_HELP_NOTE not in text:
        old = "저장 후 연동 테스트를 누릅니다."
        if old in text:
            text = text.replace(old, old + " " + SETTINGS_HELP_NOTE, 1)
    if WHOLESALE_HELP_NOTE not in text:
        old = "상품 검색·담기는 <strong>상품담기</strong> 메뉴에서 합니다."
        if old in text:
            text = text.replace(old, old + " " + WHOLESALE_HELP_NOTE, 1)
    text = text.replace(
        "품절/재판매: 고른 상품의 공급처 재고를 확인한 뒤, 품절로 바꾸기 또는 재판매로 바꾸기를 누릅니다.",
        "품절/재판매: 품절상품 조회하기 또는 재판매상품 조회하기로 목록을 본 뒤, 모두 선택한 상태에서 품절진행 또는 재판매진행을 누릅니다.",
    )
    return text


def _is_program_dir(path: Path) -> bool:
    return (
        (path / "MODUMODU.exe").is_file()
        or (path / "launcher.py").is_file()
        or (path / "app" / "static" / "index.html").is_file()
    )


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
    except (ValueError, OSError):
        return False
    return True


def _protected_dir(path: Path, root: Path) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        return True
    script_dir = Path(__file__).resolve().parent
    if resolved == script_dir or resolved == root.resolve():
        return True
    return _inside(script_dir, resolved)


def _search_bases(root: Path) -> list[Path]:
    bases = [root, root / "배포", root / "dist"]
    parent = root.parent
    if parent.name in {"배포", "dist"}:
        bases.append(parent)
    return bases


def _program_dirs(root: Path) -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()
    for base in _search_bases(root):
        if not base.exists():
            continue
        candidates = [base]
        if base.is_dir():
            try:
                candidates.extend(child for child in base.iterdir() if child.is_dir())
            except OSError:
                continue
        for path in candidates:
            try:
                key = path.resolve()
            except OSError:
                continue
            if key in seen or not _is_program_dir(path):
                continue
            seen.add(key)
            found.append(path)
    return found


def _crlf_bytes(text: str) -> bytes:
    return text.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")


def _same_text(path: Path, expected: str) -> bool:
    if not path.is_file():
        return False
    current = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    return current == expected.replace("\r\n", "\n")


def prepare_seller_folder(folder: Path) -> bool:
    changed = False
    edition = folder / "edition.txt"
    current = edition.read_text(encoding="utf-8-sig").strip() if edition.is_file() else ""
    if current != "test":
        edition.write_bytes(b"test\r\n")
        changed = True
    exe = folder / "MODUMODU.exe"
    if exe.is_file():
        data = exe.read_bytes()
        if _OLD_LINK in data:
            exe.write_bytes(data.replace(_OLD_LINK, _NEW_LINK))
            changed = True
    help_path = folder / "사용방법-셀러용.txt"
    if not _same_text(help_path, SELLER_HELP):
        help_path.write_bytes(_crlf_bytes(SELLER_HELP))
        changed = True
    for name in ("사용방법-배포용.txt", "사용방법-테스트용.txt", "사용방법-마스터.txt"):
        old_help = folder / name
        if old_help.is_file():
            old_help.unlink()
            changed = True
    if _ensure_seller_update_url(folder):
        changed = True
    bat = folder / "설치.bat"
    if bat.is_file():
        bat.unlink()
        changed = True
    return changed


def _ensure_seller_update_url(folder: Path) -> bool:
    path = folder / "update_url.txt"
    current = path.read_text(encoding="utf-8-sig").strip() if path.is_file() else ""
    if current == SELLER_UPDATE_URL:
        return False
    if current.startswith("https://") and "ibccomae-cpu/smartstore-uploader" not in current:
        return False
    path.write_bytes((SELLER_UPDATE_URL + "\r\n").encode("utf-8"))
    return True


def _installer_exe() -> Path | None:
    env = os.environ.get("MODUMODU_SELLER_SETUP_EXE", "").strip()
    candidates = [Path(env)] if env else []
    candidates.append(Path(__file__).resolve().parent / "셀러용-설치.exe")
    for path in candidates:
        if path.is_file():
            return path
    return None


def _setup_dir(root: Path) -> Path:
    parent = root / "배포"
    if root.parent.name in {"배포", "dist"} and root.resolve() != root.parent.resolve():
        parent = root.parent
    return parent / "모두모두AI-셀러용-설치"


def _sync_program(src: Path, dest: Path) -> bool:
    changed = False
    skip = {"data", "launcher.log", "__pycache__", "설치.bat"}
    dest.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    for path in src.rglob("*"):
        rel = path.relative_to(src)
        if any(part in skip for part in rel.parts):
            continue
        if _inside(path, dest) or path.resolve() == dest.resolve():
            continue
        seen.add(rel.as_posix())
        target = dest / rel
        if path.is_dir():
            if not target.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                changed = True
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        same = False
        if target.is_file():
            src_stat = path.stat()
            dst_stat = target.stat()
            same = src_stat.st_size == dst_stat.st_size and int(src_stat.st_mtime) == int(dst_stat.st_mtime)
        if not same:
            shutil.copy2(path, target)
            changed = True
    for path in list(dest.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(dest)
        if any(part in skip for part in rel.parts):
            continue
        if rel.as_posix() not in seen:
            path.unlink()
            changed = True
    data_dir = dest / "data"
    if data_dir.exists():
        shutil.rmtree(data_dir)
        changed = True
    return changed


def _write_setup_zip(setup: Path, dest: Path) -> bool:
    signature = hashlib.sha256()
    files = [path for path in sorted(setup.rglob("*")) if path.is_file() and path.name != ".seller-setup.sha"]
    for path in files:
        stat = path.stat()
        signature.update(path.relative_to(setup).as_posix().encode("utf-8"))
        signature.update(str(stat.st_size).encode("ascii"))
        signature.update(str(int(stat.st_mtime)).encode("ascii"))
    digest = signature.hexdigest()
    stamp = setup / ".seller-setup.sha"
    if dest.is_file() and stamp.is_file() and stamp.read_text(encoding="utf-8").strip() == digest:
        return False
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            info = zipfile.ZipInfo(path.relative_to(setup).as_posix(), date_time=(2026, 10, 28, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.flag_bits |= 0x800
            archive.writestr(info, path.read_bytes())
    stamp.write_text(digest + "\n", encoding="utf-8")
    return True


def build_seller_setup(root: Path, source: Path) -> bool:
    if "셀러용" in root.name:
        return False
    setup = _setup_dir(root)
    if source.resolve() == setup.resolve() or _inside(source.resolve(), setup.resolve()):
        return False
    setup.mkdir(parents=True, exist_ok=True)
    payload = setup / "프로그램"
    changed = _sync_program(source, payload)
    if prepare_seller_folder(payload):
        changed = True
    readme = setup / "읽어주세요.txt"
    if not _same_text(readme, SELLER_README):
        readme.write_bytes(_crlf_bytes(SELLER_README))
        changed = True
    exe = _installer_exe()
    if exe is not None:
        dest = setup / "모두모두AI-셀러용-설치.exe"
        data = exe.read_bytes()
        if not dest.is_file() or dest.read_bytes() != data:
            dest.write_bytes(data)
            changed = True
    zip_path = setup.parent / "모두모두AI-셀러용-설치.zip"
    if _write_setup_zip(setup, zip_path):
        changed = True
    return changed


def _copy_ignore(dest: Path):
    dest_resolved = dest.resolve()

    def ignore(dirpath: str, names: list[str]) -> set[str]:
        skip = {name for name in names if name in {"data", "launcher.log", "__pycache__"}}
        parent = Path(dirpath)
        for name in names:
            candidate = parent / name
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved == dest_resolved or _inside(dest_resolved, resolved):
                skip.add(name)
        return skip

    return ignore


def _seller_destination(root: Path) -> Path:
    parent = root.parent
    if parent.name in {"배포", "dist"} and root.resolve() != parent.resolve():
        return parent / "MODUMODU-셀러용"
    return root / "배포" / "MODUMODU-셀러용"


def _remove_old_editions(root: Path, keep: set[Path]) -> bool:
    changed = False
    keep_resolved = {path.resolve() for path in keep}
    for base in _search_bases(root):
        if not base.is_dir():
            continue
        targets = []
        if "배포용" in base.name or "테스트용" in base.name:
            targets.append(base)
        try:
            children = list(base.iterdir())
        except OSError:
            continue
        for child in children:
            if child.is_dir() and ("배포용" in child.name or "테스트용" in child.name):
                targets.append(child)
        for target in targets:
            if not target.exists():
                continue
            if "마스터" in target.name:
                continue
            try:
                resolved = target.resolve()
            except OSError:
                continue
            if resolved in keep_resolved or _protected_dir(target, root):
                continue
            shutil.rmtree(target)
            changed = True
    return changed


def _desktop_dirs(desktops) -> list[Path]:
    if desktops is not None:
        return [Path(path) for path in desktops]
    if os.name != "nt":
        return []
    found = []
    home = Path.home()
    for name in ("Desktop", "바탕 화면"):
        path = home / name
        if path.is_dir():
            found.append(path)
    public = Path(os.environ.get("PUBLIC", r"C:\Users\Public")) / "Desktop"
    if public.is_dir():
        found.append(public)
    return found


def _create_seller_shortcut(desktop: Path, folder: Path) -> bool:
    if os.name != "nt":
        return False
    exe = folder / "셀러실행.exe"
    if not exe.is_file():
        exe = folder / "MODUMODU.exe"
    if not exe.is_file():
        return False
    link = desktop / "모두모두AI 셀러용.lnk"
    script = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:SELLER_LINK); "
        "$s.TargetPath=$env:SELLER_TARGET; $s.WorkingDirectory=$env:SELLER_WORK; "
        "$s.IconLocation=$env:SELLER_ICON; $s.Description='모두모두AI 셀러용'; $s.Save()"
    )
    env = os.environ.copy()
    env.update(
        {
            "SELLER_LINK": str(link),
            "SELLER_TARGET": str(exe),
            "SELLER_WORK": str(folder),
            "SELLER_ICON": str(exe) + ",0",
        }
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", script], env=env, check=False)
    return link.is_file()


def _refresh_shortcuts(seller_dirs: list[Path], desktops) -> bool:
    changed = False
    for desktop in _desktop_dirs(desktops):
        if not desktop.is_dir():
            continue
        for name in (
            "모두모두AI 배포용.lnk",
            "모두모두AI 테스트용.lnk",
            "모두모두AI 배포용.url",
            "모두모두AI 테스트용.url",
        ):
            path = desktop / name
            if path.is_file():
                path.unlink()
                changed = True
        if seller_dirs and _create_seller_shortcut(desktop, seller_dirs[0]):
            changed = True
    return changed


def arrange_seller_copies(root: Path, desktops=None) -> bool:
    if not root.exists():
        return False
    root = root.resolve()
    changed = False
    dirs = _program_dirs(root)
    seller_dirs = [path for path in dirs if "셀러용" in path.name]
    removable: list[Path] = []
    for path in dirs:
        if "배포용" not in path.name and "테스트용" not in path.name:
            continue
        if _protected_dir(path, root):
            if path not in seller_dirs:
                seller_dirs.append(path)
            continue
        removable.append(path)
    if not seller_dirs:
        prefer = [path for path in removable if "배포용" in path.name]
        pick = prefer[0] if prefer else (removable[0] if removable else None)
        if pick is not None:
            new_name = pick.name.replace("배포용", "셀러용").replace("테스트용", "셀러용")
            dest = pick.with_name(new_name)
            if not dest.exists():
                pick.rename(dest)
                removable = [path for path in removable if path != pick]
                seller_dirs.append(dest)
                changed = True
        else:
            source = next((path for path in dirs if "마스터" in path.name), None)
            if source is None and _is_program_dir(root) and "셀러용" not in root.name:
                source = root
            if source is not None:
                dest = _seller_destination(root)
                dest.parent.mkdir(parents=True, exist_ok=True)
                if not dest.exists():
                    shutil.copytree(source, dest, ignore=_copy_ignore(dest))
                    seller_dirs.append(dest)
                    changed = True
                elif dest not in seller_dirs:
                    seller_dirs.append(dest)
    keep = set(seller_dirs)
    for seller in seller_dirs:
        if prepare_seller_folder(seller):
            changed = True
        if seller.resolve() != root:
            if apply_static_patches(seller):
                changed = True
            if write_screen_version(seller):
                changed = True
    if _remove_old_editions(root, keep):
        changed = True
    if _refresh_shortcuts(seller_dirs, desktops):
        changed = True
    setup = _setup_dir(root)
    sources = []
    for path in seller_dirs:
        resolved = path.resolve()
        if resolved == setup.resolve() or _inside(resolved, setup.resolve()):
            continue
        sources.append(path)
    if sources and build_seller_setup(root, sources[0]):
        changed = True
    return changed


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
    text = patch_help(text)
    text = bump_asset(text, "styles.css", "stock-list1")
    return bump_asset(text, "app.js", "stock-list1")


COLLECT_URL_JS = r"""
/* collect-url1 */
function collectIdentity(url) {
  const raw = String(url || "").trim();
  if (!raw) return { key: "", no: "" };
  let parsed = null;
  try { parsed = new URL(raw); } catch (error) { parsed = null; }
  const idNames = ["product_no", "productno", "goods_no", "goodsno", "it_id", "product_id", "prdno", "item_id", "branduid", "idx"];
  if (!parsed) {
    const plain = raw.replace(/\/+$/, "").toLowerCase().split("?")[0];
    return { key: plain, no: "" };
  }
  let found = "";
  let foundName = "";
  idNames.forEach((name) => {
    if (found) return;
    const value = parsed.searchParams.get(name);
    if (value && String(value).trim()) {
      found = String(value).trim();
      foundName = name;
    }
  });
  const path = parsed.pathname.replace(/\/+$/, "");
  const pretty = path.match(/\/product\/[^/]+\/(\d+)(?:\/|$)/i);
  const no = found || (pretty ? pretty[1] : "");
  const key = found
    ? `${parsed.origin}${path}?${foundName}=${found}`.toLowerCase()
    : `${parsed.origin}${path}`.toLowerCase();
  return { key, no };
}
function normalizeCollectUrl(url) {
  return collectIdentity(url).key;
}
function cafe24CollectedKeys(wholesalerId) {
  const nos = new Set();
  const urls = new Set();
  const id = String(wholesalerId || "");
  products.forEach((item) => {
    if (!isMasterProduct(item)) return;
    if (id && productWholesalerId(item) !== id) return;
    const no = String(item.wholesale_product_no || "").trim();
    if (no) nos.add(no);
    const ident = collectIdentity(item.source_url);
    if (ident.no) nos.add(ident.no);
    if (ident.key) urls.add(ident.key);
  });
  return { nos, urls };
}
function isCafe24AlreadyCollected(item, keys) {
  const no = String(item?.product_no || "").trim();
  const ident = collectIdentity(item?.url);
  const itemNo = no || ident.no;
  if (itemNo && keys.nos.has(itemNo)) return true;
  if (!ident.key || !keys.urls.has(ident.key)) return false;
  if (itemNo && !ident.key.includes(itemNo)) return false;
  return true;
}
"""


STOCK_LIST_JS = r"""
/* stock-list1 */
let stockSupplierId = "";
let stockPicked = new Set();
let stockSeenIds = new Set();
let stockListQuery = "";
let stockListStamp = "";

function stockLookupLabel() {
  if (stockJob && stockJob.status === "running") return "조회 중";
  if (stockJob && stockJob.status && stockJob.status !== "running") return "다시 조회하기";
  return stockMode === "resale" ? "재판매상품 조회하기" : "품절상품 조회하기";
}

function stockProceedLabel() {
  return stockMode === "resale" ? "재판매진행" : "품절진행";
}

function stockServerIds() {
  if (!stockJob) return null;
  const key = stockMode === "resale" ? "resale_ids" : "soldout_ids";
  const ids = stockJob[key];
  if (!Array.isArray(ids)) return null;
  return ids.map((id) => String(id || "")).filter(Boolean);
}

function stockRows() {
  const id = String(stockSupplierId || "");
  const rows = products.filter((item) => id && !item.market_id && productWholesalerId(item) === id);
  const seen = new Set();
  const unique = [];
  rows.forEach((item) => {
    const key = String(item.id || "");
    if (!key || seen.has(key)) return;
    seen.add(key);
    unique.push(item);
  });
  unique.sort((a, b) => {
    const sold = (item) => (item.wholesale_soldout ? 0 : 1);
    if (sold(a) !== sold(b)) return sold(a) - sold(b);
    return String(a.name || "").localeCompare(String(b.name || ""), "ko");
  });
  return unique;
}

function stockListedRows() {
  const rows = stockRows();
  const ids = stockServerIds();
  if (!ids) return rows;
  const wanted = new Set(ids);
  const matched = rows.filter((item) => wanted.has(String(item.id)));
  ids.forEach((id) => {
    if (matched.some((item) => String(item.id) === id)) return;
    const found = products.find((item) => String(item.id) === id);
    matched.push(found || { id, name: `상품 ${id}`, wholesale_soldout: stockMode === "soldout" });
  });
  return matched;
}

function adoptStockRows() {
  stockListedRows().forEach((item) => {
    const id = String(item.id || "");
    if (!id || stockSeenIds.has(id)) return;
    stockSeenIds.add(id);
    stockPicked.add(id);
  });
}

function stockSelectionComplete() {
  const rows = stockListedRows();
  if (!rows.length) return true;
  return rows.every((item) => stockPicked.has(String(item.id)));
}

function stockResultCount() {
  if (!stockJob) return 0;
  return stockMode === "resale" ? Number(stockJob.resale_count || 0) : Number(stockJob.soldout_count || 0);
}

function stockProceedReady() {
  if (!stockJob || stockJob.status === "running" || stockJob.status === "error" || stockJob.status === "cancelled") return false;
  const kind = stockMode === "resale" ? "resale" : "soldout";
  if ((stockJob.applied || {})[kind] != null) return false;
  if (!stockResultCount()) return false;
  return stockSelectionComplete();
}

function stockEscape(value) {
  return String(value ?? "").replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
}

function stockSummaryText() {
  const rows = stockListedRows();
  const kind = stockMode === "resale" ? "resale" : "soldout";
  const applied = stockJob?.applied || {};
  if (!stockJob) {
    const noun = stockMode === "resale" ? "재판매상품 조회하기" : "품절상품 조회하기";
    return `아래는 이 공급처에 담아 둔 상품입니다. ${noun}를 누른 뒤, 모두 선택한 상태에서 ${stockProceedLabel()}을 누르세요.`;
  }
  if (stockJob.status === "running") return "공급처 상품을 확인하는 중입니다. 목록에서 상품을 미리 볼 수 있습니다.";
  if (stockJob.status === "cancelled") return "조회를 중지했습니다.";
  if (stockJob.status === "error") return stockJob.message || "조회하지 못했습니다.";
  if (applied[kind] != null) {
    return kind === "resale"
      ? `${applied.resale}개 상품을 재판매로 바꿨습니다.`
      : `${applied.soldout}개 상품을 품절로 바꿨습니다.`;
  }
  const count = stockResultCount();
  if (!count) {
    return kind === "resale" ? "재판매로 바꿀 상품이 없습니다." : "품절로 바꿀 상품이 없습니다.";
  }
  const named = stockServerIds()
    ? "조회된 상품입니다."
    : `담아 둔 상품 ${rows.length}개입니다.`;
  const action = kind === "resale"
    ? `공급처에서 다시 판매하는 상품 ${count}개를 재판매로 바꿉니다.`
    : `공급처에서 품절로 확인된 상품 ${count}개를 품절로 바꿉니다.`;
  if (!stockSelectionComplete()) {
    return "지금은 조회된 상품 중 일부만 따로 바꿀 수 없습니다. 목록을 모두 선택한 뒤 진행해 주세요.";
  }
  return `${named} ${action} 모두 선택된 상태에서 ${stockProceedLabel()}을 누르세요.`;
}

function ensureStockList() {
  const form = $("#stockForm");
  if (!form || $("#stockList")) return;
  const box = document.createElement("div");
  box.innerHTML = `
    <div class="stock-lookup-row">
      <button type="button" id="stockLookup">품절상품 조회하기</button>
    </div>
    <p id="stockListSummary" class="hint"></p>
    <div class="stock-list-tools">
      <label><input type="checkbox" id="stockListAll" /> 전체선택</label>
      <input type="search" id="stockListSearch" placeholder="상품명, 상품번호" autocomplete="off" />
      <span id="stockListCount"></span>
    </div>
    <div id="stockList" class="stock-list"></div>
  `;
  const anchor = form.querySelector(".delivery-actions");
  if (anchor) form.insertBefore(box, anchor);
  else form.append(box);
  $("#stockLookup").addEventListener("click", () => {
    startStockLookup().catch((error) => toast(error.message, true));
  });
  $("#stockListAll").addEventListener("change", () => {
    const on = $("#stockListAll").checked;
    stockListedRows().forEach((item) => {
      const id = String(item.id);
      stockSeenIds.add(id);
      if (on) stockPicked.add(id);
      else stockPicked.delete(id);
    });
    stockListStamp = "";
    renderStockList(true);
  });
  $("#stockListSearch").addEventListener("input", () => {
    stockListQuery = $("#stockListSearch").value || "";
    stockListStamp = "";
    renderStockList(true);
  });
  $("#stockList").addEventListener("change", (event) => {
    const boxInput = event.target.closest("input[data-stock-id]");
    if (!boxInput) return;
    const id = boxInput.getAttribute("data-stock-id") || "";
    stockSeenIds.add(id);
    if (boxInput.checked) stockPicked.add(id);
    else stockPicked.delete(id);
    syncStockSelection();
  });
  const soldBtn = $("#stockApplySoldout");
  const resaleBtn = $("#stockApplyResale");
  if (soldBtn) soldBtn.textContent = "품절진행";
  if (resaleBtn) resaleBtn.textContent = "재판매진행";
}

function renderStockList(force) {
  ensureStockList();
  adoptStockRows();
  const stamp = [
    stockMode,
    stockSupplierId,
    stockListQuery,
    stockJob?.id || "",
    stockJob?.status || "",
    stockJob?.soldout_count || 0,
    stockJob?.resale_count || 0,
    stockListedRows().length,
  ].join("|");
  const list = $("#stockList");
  if (list && (force || stamp !== stockListStamp)) {
    stockListStamp = stamp;
    const query = stockListQuery.trim().toLowerCase();
    const rows = stockListedRows().filter((item) => {
      if (!query) return true;
      const hay = `${item.name || ""} ${item.wholesale_product_no || ""} ${item.seller_code || ""}`.toLowerCase();
      return hay.includes(query);
    });
    if (!rows.length) {
      const empty = stockListQuery.trim() ? "찾는 상품이 없습니다." : "이 공급처에 담아 둔 상품이 없습니다.";
      list.innerHTML = `<p class="stock-list-empty">${stockEscape(empty)}</p>`;
    } else {
      list.innerHTML = rows.map((item) => {
        const id = String(item.id);
        const checked = stockPicked.has(id) ? " checked" : "";
        const sold = item.wholesale_soldout ? " is-soldout" : "";
        const no = String(item.wholesale_product_no || "").trim();
        const price = Number(item.price || 0).toLocaleString("ko-KR");
        const state = item.wholesale_soldout ? "품절" : "정상";
        const meta = [no, `${price}원`, state].filter(Boolean).join(" · ");
        return `<label class="stock-list-row${sold}"><input type="checkbox" data-stock-id="${stockEscape(id)}"${checked} /><span class="stock-list-name">${stockEscape(item.name || "이름 없는 상품")}</span><span class="stock-list-meta">${stockEscape(meta)}</span></label>`;
      }).join("");
    }
  }
  syncStockSelection();
}

function syncStockSelection() {
  const summary = $("#stockListSummary");
  if (summary) summary.textContent = stockSummaryText();
  const rows = stockListedRows();
  const picked = rows.filter((item) => stockPicked.has(String(item.id))).length;
  const count = $("#stockListCount");
  if (count) count.textContent = rows.length ? `${picked} / ${rows.length}` : "";
  const all = $("#stockListAll");
  if (all) {
    all.checked = rows.length > 0 && picked === rows.length;
    all.indeterminate = picked > 0 && picked < rows.length;
    all.disabled = !rows.length;
  }
  const lookup = $("#stockLookup");
  if (lookup) {
    lookup.textContent = stockLookupLabel();
    lookup.disabled = stockJob?.status === "running";
  }
  const soldBtn = $("#stockApplySoldout");
  const resaleBtn = $("#stockApplyResale");
  if (soldBtn) soldBtn.textContent = "품절진행";
  if (resaleBtn) resaleBtn.textContent = "재판매진행";
  if (stockJob && $("#stockApplySoldout") && $("#stockApplyResale")) {
    const running = stockJob.status === "running";
    const applied = stockJob.applied || {};
    const readySold = !running && stockMode === "soldout" && stockProceedReady();
    const readyResale = !running && stockMode === "resale" && stockProceedReady();
    $("#stockApplySoldout").disabled = !readySold || applied.soldout != null;
    $("#stockApplyResale").disabled = !readyResale || applied.resale != null;
  }
}

async function openStockDialog(mode = "soldout") {
  const id = (productFilter && productFilter !== "all" && productFilter !== "url")
    ? productFilter
    : selectedWholesalerId();
  if (!id) throw new Error("공급처를 먼저 선택하거나, 상품관리에서 공급처 필터를 고르세요.");
  if (wholesalers.find((row) => row.id === id)?.type === "ownerclan") {
    throw new Error("오너클랜 상품은 상품담기에서 확인합니다.");
  }
  const supplier = wholesalers.find((row) => row.id === id);
  clearTimeout(stockTimer);
  stockJob = null;
  stockMode = mode === "resale" ? "resale" : "soldout";
  stockSupplierId = id;
  stockListQuery = "";
  stockListStamp = "";
  stockPicked = new Set();
  stockSeenIds = new Set();
  ensureStockList();
  const search = $("#stockListSearch");
  if (search) search.value = "";
  $("#stockTitle").textContent = stockModeLabel();
  $("#stockRowSoldout").hidden = stockMode !== "soldout";
  $("#stockRowResale").hidden = stockMode !== "resale";
  $("#stockSupplier").textContent = stockMode === "resale"
    ? `${supplier?.name || "공급처"}에 담아 둔 품절상품을 조회한 뒤, 재판매진행으로 다시 판매합니다.`
    : `${supplier?.name || "공급처"}에 담아 둔 상품을 조회한 뒤, 품절진행으로 품절 처리합니다.`;
  $("#stockMessage").textContent = "";
  $("#stockPhase").textContent = "조회 전";
  $("#stockStep").textContent = "";
  $("#stockChecked").textContent = "";
  $("#stockProgress").value = 0;
  $("#stockSoldoutText").textContent = "조회 전";
  $("#stockResaleText").textContent = "조회 전";
  $("#stockStop").disabled = true;
  adoptStockRows();
  renderStockList(true);
  const dialog = $("#stockDialog");
  if (dialog.open) dialog.close();
  dialog.showModal();
}

async function startStockLookup() {
  const id = stockSupplierId;
  if (!id) throw new Error("공급처를 먼저 선택하거나, 상품관리에서 공급처 필터를 고르세요.");
  if (stockJob?.status === "running") return;
  $("#stockMessage").textContent = "";
  $("#stockPhase").textContent = "작업을 시작하는 중입니다.";
  $("#stockStop").disabled = true;
  syncStockSelection();
  setBusy(true, `${stockModeLabel()} 상품을 조회하는 중입니다.`);
  try {
    stockJob = await api(`/api/wholesalers/${id}/stock-check`, { method: "POST", scope: "products" });
  } catch (error) {
    setBusy(false);
    stockJob = { status: "error", phase: "시작하지 못했습니다.", done: 0, total: 0, checked: 0, products: 0, soldout_total: 0, soldout_count: 0, resale_count: 0, applied: {}, message: error.message };
    renderStockJob(stockJob);
    throw error;
  }
  log(`${stockModeLabel()} 상품 조회를 시작했습니다.`);
  renderStockJob(stockJob);
  pollStockJob();
}

function renderStockJob(job) {
  const running = job.status === "running";
  const total = Number(job.total || 0);
  const done = Number(job.done || 0);
  const progress = $("#stockProgress");
  if (running && !total) progress.removeAttribute("value");
  else progress.value = total ? Math.round((done / total) * 100) : (job.status === "done" || job.status === "cancelled" ? 100 : 0);
  $("#stockPhase").textContent = job.phase || (running ? "조회 중" : "");
  $("#stockStep").textContent = total ? `${done.toLocaleString("ko-KR")} / ${total.toLocaleString("ko-KR")}` : "";
  $("#stockChecked").textContent = job.products ? `상품 ${job.products}개 중 ${job.checked || 0}개 확인` : "";
  const applied = job.applied || {};
  $("#stockSoldoutText").textContent = applied.soldout != null
    ? `${applied.soldout}개를 품절로 바꿨습니다`
    : `새로 품절 ${Number(job.soldout_count || 0)}개`;
  $("#stockResaleText").textContent = applied.resale != null
    ? `${applied.resale}개를 재판매로 바꿨습니다`
    : `재판매 가능 ${Number(job.resale_count || 0)}개`;
  $("#stockStop").disabled = !running || !stockJob;
  if (job.message) $("#stockMessage").textContent = job.message;
  renderStockList(false);
}

async function applyStockJob(kind) {
  if (!stockJob) return;
  const expected = kind === "resale" ? "resale" : "soldout";
  if (stockMode !== expected) return;
  if (!stockProceedReady()) {
    renderStockList(false);
    toast("지금은 조회된 상품 중 일부만 따로 바꿀 수 없습니다. 목록을 모두 선택한 뒤 진행해 주세요.", true);
    return;
  }
  stockJob = await api(`/api/stock-jobs/${stockJob.id}/apply`, { method: "POST", body: JSON.stringify({ kind }) });
  await loadProducts();
  stockListStamp = "";
  renderStockJob(stockJob);
  const count = stockJob.applied?.[kind] || 0;
  const message = kind === "soldout" ? `${count}개 상품을 품절로 바꿨습니다.` : `${count}개 상품을 재판매로 바꿨습니다.`;
  $("#stockMessage").textContent = message;
  log(message, "ok");
  toast(message);
}
"""


STOCK_LIST_CSS = """
/* stock-list1 */
#stockDialog { width: min(760px, calc(100vw - 24px)); }
.stock-lookup-row { margin: 8px 0 4px; }
.stock-list-tools { display: flex; gap: 8px; align-items: center; margin: 6px 0; }
.stock-list-tools input[type="search"] { flex: 1; min-width: 0; }
.stock-list {
  max-height: min(420px, 48vh);
  overflow: auto;
  border: 1px solid #c8c8c8;
  background: #fff;
}
.stock-list-row {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  padding: 6px 8px;
  border-bottom: 1px solid #eee;
}
.stock-list-row:last-child { border-bottom: 0; }
.stock-list-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.stock-list-meta { color: #666; font-size: 12px; white-space: nowrap; }
.stock-list-row.is-soldout .stock-list-meta { color: #a33; }
.stock-list-empty { margin: 0; padding: 16px 8px; color: #666; }
"""


def patch_seller_login_port(text: str) -> str:
    if "async function useAccount()" in text:
        return text
    block = SELLER_LOGIN2_JS
    start = block.find("  let accountURL")
    end = block.find("  const sessionKey")
    old = '  const accountURL = "http://127.0.0.1:8790";\n'
    if start < 0 or end < 0 or old not in text:
        return text
    text = text.replace(old, block[start:end], 1)
    text = text.replace(
        "    if (window.__sellerLoginTest) return postSync(path, body);\n    let response;",
        "    if (window.__sellerLoginTest) return postSync(path, body);\n    await useAccount();\n    let response;",
        1,
    )
    text = text.replace(
        '        const response = await fetch(accountURL + "/api/seller-status");',
        '        await useAccount();\n        const response = await fetch(accountURL + "/api/seller-status");',
        1,
    )
    return text


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
    if "/* name-fix1 */" not in text:
        text = text.rstrip() + "\n" + NAME_JS
    if "/* name-fix2 */" not in text:
        text = text.rstrip() + "\n" + NAME_JS2
    if "/* invite-settings1 */" not in text:
        text = text.rstrip() + "\n" + INVITE_SETTINGS_JS
    if "/* admin-menu1 */" not in text:
        text = text.rstrip() + "\n" + ADMIN_MENU_JS
    if "/* seller-edition1 */" not in text:
        text = text.rstrip() + "\n" + SELLER_JS.replace("2026.10.28.11", SCREEN_VERSION)
    if "/* seller-login1 */" not in text:
        text = text.rstrip() + "\n" + SELLER_LOGIN_JS
    if "/* seller-login2 */" not in text:
        text = text.rstrip() + "\n" + SELLER_LOGIN2_JS
    if "/* seller-port1 */" not in text:
        text = text.rstrip() + "\n" + SELLER_PORT_JS
    if "/* master-login1 */" not in text:
        text = text.rstrip() + "\n" + MASTER_LOGIN_JS
    if "/* seller-phone1 */" not in text:
        text = text.rstrip() + "\n" + SELLER_PHONE_JS
    if "/* seller-peek1 */" not in text:
        text = text.rstrip() + "\n" + SELLER_PEEK_JS
    text = patch_seller_login_port(text)
    if "/* collect-url1 */" not in text:
        text = text.rstrip() + "\n" + COLLECT_URL_JS
    if "/* stock-list1 */" not in text:
        text = text.rstrip() + "\n" + STOCK_LIST_JS
    text = text.replace("배포용", "셀러용")
    for old in ("2026.10.28.10", "2026.10.28.11", "2026.10.28.12", "2026.10.28.13", "2026.10.28.14", "2026.10.28.15", "2026.10.28.16", "2026.10.28.17", "2026.10.28.18", "2026.10.28.19", "2026.10.28.20", "2026.10.28.21", "2026.10.28.22", "2026.10.28.23", "2026.10.28.24"):
        if old != SCREEN_VERSION:
            text = text.replace(old, SCREEN_VERSION)
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
    if "/* invite-settings1 */" not in text:
        extra += INVITE_SETTINGS_CSS
    if "/* admin-menu1 */" not in text:
        extra += ADMIN_MENU_CSS
    if "/* seller-edition1 */" not in text:
        extra += SELLER_CSS
    if "/* seller-login1 */" not in text:
        extra += SELLER_LOGIN_CSS
    if "/* seller-login2 */" not in text:
        extra += SELLER_LOGIN2_CSS
    if "/* master-login1 */" not in text:
        extra += MASTER_LOGIN_CSS
    if "/* seller-peek1 */" not in text:
        extra += SELLER_PEEK_CSS
    if "/* stock-list1 */" not in text:
        extra += STOCK_LIST_CSS
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


def repaired_filename(name: str) -> str:
    try:
        raw = name.encode("cp866")
    except UnicodeEncodeError:
        return ""
    try:
        fixed = raw.decode("utf-8")
    except UnicodeDecodeError:
        return ""
    if fixed == name or not any("\uac00" <= char <= "\ud7a3" for char in fixed):
        return ""
    if "/" in fixed or "\\" in fixed or fixed in {".", ".."}:
        return ""
    return fixed


def repair_broken_names(folder: Path) -> None:
    if not folder.is_dir():
        return
    for path in list(folder.iterdir()):
        if not path.is_file():
            continue
        fixed = repaired_filename(path.name)
        if not fixed:
            continue
        dest = folder / fixed
        try:
            path.chmod(0o666)
            if dest.exists() and dest.resolve() != path.resolve():
                dest.chmod(0o666)
                if dest.read_bytes() == path.read_bytes() or dest.stat().st_size >= path.stat().st_size:
                    path.unlink()
                else:
                    dest.unlink()
                    path.rename(dest)
            elif not dest.exists():
                path.rename(dest)
        except OSError:
            continue


def repair_known_folders(root: Path) -> None:
    folders = [Path(__file__).resolve().parent, root, root / "배포"]
    for folder in folders:
        repair_broken_names(folder)
        if folder.name != "배포" or not folder.is_dir():
            continue
        for child in folder.iterdir():
            repair_broken_names(child)


def iter_static_dirs(root: Path) -> list[Path]:
    found = []
    for static in (root / "app" / "static", root / "_internal" / "app" / "static"):
        if (static / "app.js").is_file() and (static / "index.html").is_file():
            found.append(static)
    return found


def apply_static_patches(root: Path) -> bool:
    changed = False
    for static in iter_static_dirs(root):
        if _apply_one_static(static):
            changed = True
    return changed


def _apply_one_static(static: Path) -> bool:
    js_path = static / "app.js"
    html_path = static / "index.html"
    css_path = static / "styles.css"
    if not js_path.is_file() or not html_path.is_file():
        return False
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
    changed = False
    for path, new, old, newline in (
        (js_path, new_js, js, js_nl),
        (html_path, new_html, html, html_nl),
        (css_path, new_css, css, css_nl),
    ):
        if not path.is_file() or new == old:
            continue
        backup = path.with_name(path.name + ".bak-inquiry-links")
        if not backup.exists():
            backup.write_bytes(path.read_bytes())
        write_text(path, new, newline)
        changed = True
    return changed


def main() -> None:
    seller_only = "--seller-only" in sys.argv[1:]
    args = [arg for arg in sys.argv[1:] if arg != "--seller-only"]
    root = Path(args[0] if args else r"C:\smartstore uploader")
    if root.exists():
        repair_known_folders(root)
    seller_changed = arrange_seller_copies(root) if root.exists() else False
    if seller_only:
        if seller_changed:
            print("seller edition")
            raise SystemExit(10)
        print("already linked")
        return
    static_changed = apply_static_patches(root)
    version_changed = write_screen_version(root) if root.exists() else False
    if not seller_changed and not static_changed and not version_changed:
        if not iter_static_dirs(root):
            raise SystemExit(f"static files not found: {root / 'app' / 'static'}")
        print("already linked")
        return
    print("inquiry links on")
    raise SystemExit(10)


if __name__ == "__main__":
    main()
