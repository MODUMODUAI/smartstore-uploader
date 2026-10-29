"""Turn inquiry order and product numbers into links. Leaves the rest of the program alone."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
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
SCREEN_VERSION = "2026.10.28.51"
# Longer tokens first is unnecessary: each token is a full version, and a
# shorter prefix such as 2026.10.28.4 must never be added or it rewrites .40.
_OLD_SCREEN_VERSIONS = tuple(f"2026.10.28.{n}" for n in range(10, 51))
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

MASTER_LOGIN2_JS = r"""
/* master-login2 */
(function () {
  function attach(input) {
    if (!input || input.dataset.masterPeek === "1") return;
    input.dataset.masterPeek = "1";
    input.autocomplete = "new-password";
    input.value = "";
    input.inputMode = "numeric";
    const line = document.createElement("span");
    line.className = "seller-password-line";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "seller-peek";
    button.textContent = "보기";
    button.setAttribute("aria-pressed", "false");
    button.addEventListener("click", () => {
      const open = input.type === "password";
      input.type = open ? "text" : "password";
      button.textContent = open ? "가리기" : "보기";
      button.setAttribute("aria-pressed", open ? "true" : "false");
      input.focus();
    });
    input.before(line);
    line.append(input, button);
  }

  function sweep() {
    document.querySelectorAll("#masterLoginPassword").forEach(attach);
  }

  function hook() {
    sweep();
    if (document.body.dataset.masterPeekWatch === "1") return;
    document.body.dataset.masterPeekWatch = "1";
    new MutationObserver(() => sweep()).observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", hook);
  else hook();
  setTimeout(hook, 0);
  setTimeout(sweep, 300);
})();
"""

WHOLESALE_IMPORT_ALL_JS = r"""
/* wholesale-import-all1 */
(function () {
  function attach() {
    if (document.getElementById("wholesaleImportAll")) return;
    const anchor = document.getElementById("wholesaleLogin") || document.getElementById("wholesaleDelete");
    if (!anchor || typeof importWholesaleProducts !== "function") return;
    const button = document.createElement("button");
    button.type = "button";
    button.id = "wholesaleImportAll";
    button.textContent = "전체상품 가져오기";
    button.title = "선택한 공급처의 전체 상품을 상품관리로 가져옵니다.";
    button.addEventListener("click", () => {
      const id = typeof selectedWholesalerId === "function" ? selectedWholesalerId() : "";
      if (!id) {
        toast("공급처를 먼저 선택해 주세요.", true);
        return;
      }
      const supplier = (typeof wholesalers !== "undefined" ? wholesalers : []).find((row) => row.id === id);
      const name = supplier?.name || "선택한 공급처";
      if (supplier?.type !== "ownerclan" && !confirm(`${name}의 전체 상품을 상품관리로 가져올까요?\n이미 있는 상품은 그대로 두고 새 상품만 더합니다. 상품이 많으면 몇 분 걸립니다.`)) return;
      importWholesaleProducts().catch((error) => toast(error.message, true));
    });
    anchor.after(button);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", attach);
  else attach();
  setTimeout(attach, 0);
  setTimeout(attach, 500);
})();
"""

OPEN_LOGIN_JS = r"""
/* open-login1 */
openSupplierProductUrl = async function (url, wholesalerId, emptyMessage) {
  const target = String(url || "").trim();
  if (!looksLikeUrl(target)) {
    toast(emptyMessage || "열 상품 주소가 없습니다.", true);
    return false;
  }
  const id = String(wholesalerId || "").trim();
  if (!id) return openUrl(target, emptyMessage);
  toast("공급처에 로그인한 Chrome에서 상품을 여는 중입니다.");
  try {
    const result = await api(`/api/wholesalers/${encodeURIComponent(id)}/open-product`, {
      method: "POST",
      body: JSON.stringify({ url: target }),
      signal: AbortSignal.timeout(90000),
    });
    toast(result?.message || "로그인 Chrome에서 공급사 상품을 열었습니다.");
    return true;
  } catch (error) {
    toast(`${error.message || "공급사 상품을 열지 못했습니다."} 잠깐 뒤에 다시 눌러 주세요.`, true);
    return false;
  }
};
"""
SERVER_FIX_CHECK_JS = r"""
/* server-fix-check1 */
(function () {
  if (typeof api !== "function") return;
  const original = api;
  let checked = false;
  async function fixStatus() {
    try {
      const response = await fetch(`/static/modumodu-fixes.json?t=${Date.now()}`, { cache: "no-store" });
      return response.ok ? await response.json() : null;
    } catch (error) {
      return null;
    }
  }
  async function warn(fixes) {
    if (checked) return;
    checked = true;
    const status = await fixStatus();
    const missing = [];
    Object.entries(status?.files || {}).forEach(([file, marks]) => {
      Object.entries(marks || {}).forEach(([mark, state]) => {
        if (state !== "ok") missing.push(`${file} ${mark}: ${[].concat(state).join(", ")}`);
      });
    });
    if (missing.length) {
      alert(`공급처 상품명 수정이 프로그램 코드에 들어가지 못했습니다.\n이 창을 캡처해서 보내 주세요.\n\n${missing.join("\n")}`);
      return;
    }
    if (fixes) {
      const off = Object.entries(fixes).filter(([, on]) => !on).map(([name]) => name);
      alert(`공급처 상품명 수정 일부가 실행 중인 프로그램에 없습니다.\n이 창을 캡처해서 보내 주세요.\n\n${off.join(", ")}`);
      return;
    }
    const quit = confirm("프로그램이 아직 예전 코드로 실행 중이라 공급처 상품명이 번호로 나올 수 있습니다.\n\n'확인'을 누르면 프로그램을 종료합니다. 그다음 바탕화면의 모두모두AI 아이콘을 다시 눌러 주세요.");
    if (!quit) return;
    try {
      await original("/api/shutdown", { method: "POST", quiet: true });
      toast("프로그램을 종료했습니다. 바탕화면의 모두모두AI 아이콘을 다시 눌러 주세요.");
    } catch (error) {
      toast(error.message || "종료하지 못했습니다.", true);
    }
  }
  api = async function (path, options) {
    const data = await original(path, options);
    if (/^\/api\/wholesalers\/[^/]+\/(catalog|import)(\?|$)/.test(String(path || "")) && data && typeof data === "object") {
      const fixes = data.server_fixes;
      if (!fixes || !fixes.godo_name || !fixes.godo_site) warn(fixes).catch(() => {});
    }
    return data;
  };
})();
"""
MASTER_LOGIN2_CSS = """
/* master-login2 */
#masterLogin .master-login-card input,
#masterLogin .master-login-card input:focus {
  background: #fff !important;
  color: #111 !important;
  caret-color: #111;
  border: 1px solid #98a2b3 !important;
  font-size: 18px;
  letter-spacing: 0.12em;
}
#masterLogin .master-login-card input:-webkit-autofill {
  -webkit-box-shadow: 0 0 0 40px #fff inset !important;
  -webkit-text-fill-color: #111 !important;
}
#masterLogin .seller-password-line { margin-top: 6px; }
#masterLogin .seller-password-line input { margin-top: 0; }
"""

MASTER_LOGIN3_CSS = """
/* master-login3 */
#masterLogin {
  background: radial-gradient(circle at 50% 30%, rgba(30, 64, 120, 0.55), rgba(8, 12, 20, 0.82));
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
}
#masterLogin .master-login-card {
  position: relative;
  width: min(380px, 100%);
  padding: 34px 30px 26px;
  border: 0;
  border-radius: 22px;
  background: #fff;
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.35);
  font-family: "Pretendard", "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
  text-align: center;
}
#masterLogin .master-login-card::before {
  content: "M";
  display: flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  margin: 0 auto 16px;
  border-radius: 16px;
  background: linear-gradient(135deg, #0b5cab, #3d9eed);
  box-shadow: 0 10px 24px rgba(11, 92, 171, 0.35);
  color: #fff;
  font-size: 24px;
  font-weight: 800;
}
#masterLogin .master-login-card h1 {
  margin: 0 0 6px;
  font-size: 23px;
  font-weight: 800;
  letter-spacing: -0.03em;
}
#masterLogin .master-login-card p {
  margin: 0 0 22px;
  font-size: 13px;
  color: #8a94a6;
}
#masterLogin .master-login-card label {
  text-align: left;
  font-size: 12px;
  font-weight: 700;
  color: #475467;
}
#masterLogin .seller-password-line {
  position: relative;
  display: block;
  margin-top: 8px;
}
#masterLogin .master-login-card input,
#masterLogin .master-login-card input:focus {
  width: 100%;
  height: 50px;
  margin: 0;
  padding: 0 70px 0 16px;
  border: 1.5px solid #d0d5dd !important;
  border-radius: 14px;
  background: #f8fafc !important;
  color: #101828 !important;
  font-size: 20px;
  letter-spacing: 0.18em;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s, background 0.15s;
}
#masterLogin .master-login-card input:focus {
  border-color: #0b5cab !important;
  background: #fff !important;
  box-shadow: 0 0 0 4px rgba(11, 92, 171, 0.14);
}
#masterLogin .seller-peek {
  position: absolute;
  top: 50%;
  right: 8px;
  transform: translateY(-50%);
  height: 34px;
  padding: 0 12px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: #0b5cab;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}
#masterLogin .seller-peek:hover { background: #eef4fb; }
#masterLogin #masterLoginError {
  min-height: 0;
  margin: 8px 2px 0;
  text-align: left;
  font-size: 12.5px;
}
#masterLogin #masterLoginError:empty { display: none; }
#masterLogin .master-login-card button[type="submit"] {
  height: 50px;
  margin-top: 18px;
  border: 0;
  border-radius: 14px;
  background: linear-gradient(135deg, #0b5cab, #2f8de4);
  box-shadow: 0 10px 22px rgba(11, 92, 171, 0.3);
  font-size: 16px;
  cursor: pointer;
  transition: transform 0.1s, box-shadow 0.15s, filter 0.15s;
}
#masterLogin .master-login-card button[type="submit"]:hover { filter: brightness(1.06); box-shadow: 0 14px 28px rgba(11, 92, 171, 0.38); }
#masterLogin .master-login-card button[type="submit"]:active { transform: translateY(1px); }
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
    stock_help = (
        "품절/재판매: 품절상품 조회하기 또는 재판매상품 조회하기로 마스터상품과 각 마켓 상품을 본 뒤, "
        "모두 선택한 상태에서 품절진행 또는 재판매진행을 누릅니다. "
        "진행하면 마스터상품과 각 마켓 상품에 함께 적용됩니다."
    )
    text = text.replace(
        "품절/재판매: 고른 상품의 공급처 재고를 확인한 뒤, 품절로 바꾸기 또는 재판매로 바꾸기를 누릅니다.",
        stock_help,
    )
    text = text.replace(
        "품절/재판매: 품절상품 조회하기 또는 재판매상품 조회하기로 목록을 본 뒤, 모두 선택한 상태에서 품절진행 또는 재판매진행을 누릅니다.",
        stock_help,
    )
    old_forbid = "등록금지키워드: 상품명에서 빼야 하는 말을 등록합니다."
    new_forbid = "등록금지키워드: 상품명과 상품태그에서 빼야 하는 말을 등록합니다."
    if old_forbid in text and new_forbid not in text:
        text = text.replace(old_forbid, new_forbid, 1)
    name_help = "경쟁강도 낮음 단어는 뺍니다. Claude 키가 있으면 상품명은 Claude로 만들고, 없으면 설정에서 고른 AI를 씁니다."
    name_help_new = name_help + " 누르면 옆에 그 상품의 상세페이지가 함께 열립니다."
    if name_help in text and "옆에 그 상품의 상세페이지" not in text:
        text = text.replace(name_help, name_help_new, 1)
    name_field_help = "상품명: 공급처 상품명 그대로입니다. 상품명바꾸기와 상품명AI로 바꾼 뒤에는 그 이름이 저장됩니다."
    if name_field_help in text and "100자까지" not in text:
        text = text.replace(
            name_field_help,
            name_field_help + " 스마트스토어 상품명은 100자까지이고, 칸 오른쪽에 글자수가 보입니다.",
            1,
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


SETUP_ZIP_BUILT = False


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
    global SETUP_ZIP_BUILT
    SETUP_ZIP_BUILT = True
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
            if patch_murray_sources(seller):
                changed = True
            if write_frozen_fixes(seller):
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


def _replace_old_versions(text: str) -> str:
    for old in _OLD_SCREEN_VERSIONS:
        if old != SCREEN_VERSION:
            text = text.replace(old, SCREEN_VERSION)
    return text


def _screen_build_script() -> str:
    # seller-edition1 keeps a MutationObserver on #appVersion and writes its
    # own constant until 11s. Cloning the node drops that observer. The late
    # timers cover a cached app.js?v=open-login1 that still says an older
    # version after this HTML has been loaded.
    return (
        "<script>\n"
        "/* screen-build1 */\n"
        "(function () {\n"
        f'  const version = "{SCREEN_VERSION}";\n'
        "  function show() {\n"
        '    const label = document.getElementById("appVersion");\n'
        "    if (label && label.dataset.screenBuild !== version) {\n"
        "      const fresh = label.cloneNode(true);\n"
        "      fresh.dataset.screenBuild = version;\n"
        "      fresh.hidden = false;\n"
        "      label.replaceWith(fresh);\n"
        "      new MutationObserver(function () {\n"
        '        if (fresh.textContent !== "v" + version) fresh.textContent = "v" + version;\n'
        "      }).observe(fresh, { childList: true, characterData: true, subtree: true });\n"
        "    }\n"
        '    const current = document.getElementById("appVersion");\n'
        "    if (current) {\n"
        "      current.hidden = false;\n"
        '      if (current.textContent !== "v" + version) current.textContent = "v" + version;\n'
        '      current.title = "버전 " + version;\n'
        "    }\n"
        '    const seller = document.body && (document.body.classList.contains("edition-seller") || document.body.classList.contains("edition-test") || String(location.port || "") === "8788");\n'
        '    const title = "모두모두AI " + (seller ? "셀러용" : "마스터") + " v" + version;\n'
        "    if (document.title !== title) document.title = title;\n"
        "  }\n"
        "  show();\n"
        "  setTimeout(show, 0);\n"
        "  setTimeout(show, 12000);\n"
        "  setTimeout(show, 16000);\n"
        "  setTimeout(show, 20000);\n"
        "})();\n"
        "</script>\n"
    )


def _ensure_screen_build(text: str) -> str:
    script = _screen_build_script()
    pattern = re.compile(r"<script>\s*/\* screen-build1 \*/.*?</script>\s*", re.S)
    if pattern.search(text):
        return pattern.sub(script, text, count=1)
    if "</body>" in text:
        return text.replace("</body>", script + "</body>", 1)
    return text + script


def _set_version_label(text: str) -> str:
    pattern = re.compile(r'(id="appVersion"[^>]*>)v[\d.]+')
    return pattern.sub(rf"\1v{SCREEN_VERSION}", text, count=1)


def patch_html(text: str) -> str:
    text = patch_store_label(text)
    text = patch_help(text)
    text = bump_asset(text, "styles.css", SCREEN_VERSION)
    text = bump_asset(text, "app.js", SCREEN_VERSION)
    text = _set_version_label(text)
    text = _ensure_screen_build(text)
    return _replace_old_versions(text)


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


STOCK_MARKET_JS = r"""
/* stock-market1 */
function stockPlaceLabel(item) {
  if (!item || !item.market_id) return "마스터";
  let name = "";
  if (typeof marketOf === "function") {
    const market = marketOf(item.market_id);
    name = (market && (market.name || market.slug)) || "";
  }
  return String(name || item.market_name || "마켓");
}

function stockRows() {
  const id = String(stockSupplierId || "");
  const seen = new Set();
  const take = (item) => {
    const key = String(item?.id || "");
    if (!key || seen.has(key)) return null;
    seen.add(key);
    return item;
  };
  const masters = [];
  products.forEach((item) => {
    if (!id || item.market_id || productWholesalerId(item) !== id) return;
    const row = take(item);
    if (row) masters.push(row);
  });
  const masterIds = new Set(masters.map((item) => String(item.id)));
  const copies = [];
  products.forEach((item) => {
    if (!item || !item.market_id) return;
    const linked = masterIds.has(String(item.master_id || "")) || productWholesalerId(item) === id;
    if (!linked) return;
    const row = take(item);
    if (row) copies.push(row);
  });
  const byName = (a, b) => String(a.name || "").localeCompare(String(b.name || ""), "ko");
  const soldRank = (item) => (item.wholesale_soldout ? 0 : 1);
  masters.sort((a, b) => soldRank(a) - soldRank(b) || byName(a, b));
  const grouped = new Map();
  copies.forEach((item) => {
    const key = String(item.master_id || "");
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(item);
  });
  const rows = [];
  masters.forEach((master) => {
    rows.push(master);
    const kids = grouped.get(String(master.id)) || [];
    kids.sort((a, b) => stockPlaceLabel(a).localeCompare(stockPlaceLabel(b), "ko") || byName(a, b));
    kids.forEach((kid) => rows.push(kid));
    grouped.delete(String(master.id));
  });
  const orphans = [];
  grouped.forEach((kids) => orphans.push(...kids));
  orphans.sort((a, b) => soldRank(a) - soldRank(b) || stockPlaceLabel(a).localeCompare(stockPlaceLabel(b), "ko") || byName(a, b));
  orphans.forEach((item) => rows.push(item));
  return rows;
}

function stockSummaryText() {
  const rows = stockListedRows();
  const masters = rows.filter((item) => !item.market_id).length;
  const markets = rows.length - masters;
  const kind = stockMode === "resale" ? "resale" : "soldout";
  const applied = stockJob?.applied || {};
  const noun = stockMode === "resale" ? "재판매상품 조회하기" : "품절상품 조회하기";
  const place = markets
    ? `마스터상품 ${masters}개, 마켓 상품 ${markets}개`
    : `마스터상품 ${masters}개`;
  if (!stockJob) {
    return `아래는 이 공급처의 ${place}입니다. ${noun}를 누른 뒤, 모두 선택한 상태에서 ${stockProceedLabel()}을 누르세요. 진행하면 마스터상품과 각 마켓 상품에 함께 적용됩니다.`;
  }
  if (stockJob.status === "running") return "공급처 상품을 확인하는 중입니다. 마스터상품과 각 마켓 상품을 미리 볼 수 있습니다.";
  if (stockJob.status === "cancelled") return "조회를 중지했습니다.";
  if (stockJob.status === "error") return stockJob.message || "조회하지 못했습니다.";
  if (applied[kind] != null) {
    return kind === "resale"
      ? `마스터상품과 각 마켓 상품에 재판매를 적용했습니다. ${applied.resale}개 상품의 품절 표시를 바꿨습니다.`
      : `마스터상품과 각 마켓 상품에 품절을 적용했습니다. ${applied.soldout}개 상품의 품절 표시를 바꿨습니다.`;
  }
  const count = stockResultCount();
  if (!count) {
    return kind === "resale" ? "재판매로 바꿀 상품이 없습니다." : "품절로 바꿀 상품이 없습니다.";
  }
  const action = kind === "resale"
    ? `공급처에서 다시 판매하는 상품 ${count}개를 마스터상품과 각 마켓 상품에 재판매로 적용합니다.`
    : `공급처에서 품절로 확인된 상품 ${count}개를 마스터상품과 각 마켓 상품에 품절로 적용합니다.`;
  if (!stockSelectionComplete()) {
    return "지금은 조회된 상품 중 일부만 따로 바꿀 수 없습니다. 마스터상품과 각 마켓 상품을 모두 선택한 뒤 진행해 주세요.";
  }
  return `${place}입니다. ${action}`;
}

function renderStockList(force) {
  ensureStockList();
  adoptStockRows();
  const listed = stockListedRows();
  const stamp = [
    stockMode,
    stockSupplierId,
    stockListQuery,
    stockJob?.id || "",
    stockJob?.status || "",
    stockJob?.soldout_count || 0,
    stockJob?.resale_count || 0,
    listed.map((item) => `${item.id}:${item.market_id || ""}:${item.wholesale_soldout ? 1 : 0}:${item.sale_status || ""}`).join(","),
  ].join("|");
  const list = $("#stockList");
  if (list && (force || stamp !== stockListStamp)) {
    stockListStamp = stamp;
    const query = stockListQuery.trim().toLowerCase();
    const rows = listed.filter((item) => {
      if (!query) return true;
      const hay = `${item.name || ""} ${item.wholesale_product_no || ""} ${item.seller_code || ""} ${stockPlaceLabel(item)}`.toLowerCase();
      return hay.includes(query);
    });
    if (!rows.length) {
      const empty = stockListQuery.trim() ? "찾는 상품이 없습니다." : "이 공급처의 마스터상품이 없습니다.";
      list.innerHTML = `<p class="stock-list-empty">${stockEscape(empty)}</p>`;
    } else {
      list.innerHTML = rows.map((item) => {
        const id = String(item.id);
        const checked = stockPicked.has(id) ? " checked" : "";
        const sold = item.wholesale_soldout ? " is-soldout" : "";
        const role = item.market_id ? " is-market" : " is-master";
        const no = String(item.wholesale_product_no || "").trim();
        const price = Number(item.price || 0).toLocaleString("ko-KR");
        const state = item.wholesale_soldout ? "품절" : "정상";
        const meta = [no, `${price}원`, state].filter(Boolean).join(" · ");
        const place = stockEscape(stockPlaceLabel(item));
        return `<label class="stock-list-row${sold}${role}"><input type="checkbox" data-stock-id="${stockEscape(id)}"${checked} /><span class="stock-list-name"><span class="stock-list-place">${place}</span>${stockEscape(item.name || "이름 없는 상품")}</span><span class="stock-list-meta">${stockEscape(meta)}</span></label>`;
      }).join("");
    }
  }
  syncStockSelection();
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
    ? `${supplier?.name || "공급처"}의 마스터상품과 각 마켓 상품을 조회한 뒤, 재판매진행으로 다시 판매합니다.`
    : `${supplier?.name || "공급처"}의 마스터상품과 각 마켓 상품을 조회한 뒤, 품절진행으로 품절 처리합니다.`;
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

function stockSalePatch(kind, item, fallbackStock) {
  if (kind === "soldout") {
    const patch = {};
    if (String(item.sale_status || "").toUpperCase() !== "SUSPENSION") patch.sale_status = "SUSPENSION";
    if (item.display !== false) patch.display = false;
    if (String(item.display_status || "").toUpperCase() !== "SUSPENSION") patch.display_status = "SUSPENSION";
    if (Number(item.stock || 0) !== 0) patch.stock = 0;
    return patch;
  }
  const patch = {};
  if (String(item.sale_status || "").toUpperCase() !== "SALE") patch.sale_status = "SALE";
  if (item.display === false) patch.display = true;
  if (String(item.display_status || "").toUpperCase() !== "ON") patch.display_status = "ON";
  if (Number(item.stock || 0) === 0) patch.stock = fallbackStock;
  return patch;
}

async function applyStockJob(kind) {
  if (!stockJob) return;
  const expected = kind === "resale" ? "resale" : "soldout";
  if (stockMode !== expected) return;
  if (!stockProceedReady()) {
    renderStockList(false);
    toast("지금은 조회된 상품 중 일부만 따로 바꿀 수 없습니다. 마스터상품과 각 마켓 상품을 모두 선택한 뒤 진행해 주세요.", true);
    return;
  }
  const before = new Map(products.map((item) => [String(item.id), !!item.wholesale_soldout]));
  stockJob = await api(`/api/stock-jobs/${stockJob.id}/apply`, { method: "POST", body: JSON.stringify({ kind }) });
  await loadProducts();
  const target = kind === "soldout";
  const flipped = new Set();
  products.forEach((item) => {
    const id = String(item.id || "");
    if (!before.has(id) || !!item.wholesale_soldout === before.get(id)) return;
    flipped.add(id);
  });
  const flippedMasterIds = new Set();
  products.forEach((item) => {
    if (!flipped.has(String(item.id))) return;
    if (!item.market_id) flippedMasterIds.add(String(item.id));
    else if (item.master_id) flippedMasterIds.add(String(item.master_id));
  });
  const copies = products.filter((item) => {
    if (!item.market_id || (typeof isMasterProduct === "function" && isMasterProduct(item))) return false;
    return flipped.has(String(item.id)) || flippedMasterIds.has(String(item.master_id || ""));
  });
  let fallbackStock = 999;
  if (kind === "resale" && copies.some((item) => Number(item.stock || 0) === 0)) {
    try {
      const settings = await api("/api/settings", { quiet: true });
      const parsed = Number(settings?.default_stock || 0);
      if (parsed > 0) fallbackStock = parsed;
    } catch (error) {
      fallbackStock = 999;
    }
  }
  let failed = 0;
  if (copies.length) setBusy(true, "마스터상품과 각 마켓 상품에 적용하는 중입니다.");
  try {
    for (const item of copies) {
      const patch = stockSalePatch(kind, item, fallbackStock);
      if (!Object.keys(patch).length) continue;
      try {
        const saved = await api(`/api/products/${item.id}`, { method: "PUT", body: JSON.stringify(patch), quiet: true });
        const index = products.findIndex((row) => row.id === item.id);
        if (index >= 0 && saved && saved.id) products[index] = saved;
      } catch (error) {
        failed += 1;
      }
    }
  } finally {
    if (copies.length) setBusy(false);
  }
  const masterCount = products.filter((item) => !item.market_id && flipped.has(String(item.id)) && !!item.wholesale_soldout === target).length;
  const flagged = copies.filter((item) => {
    const saved = products.find((row) => row.id === item.id) || item;
    return !!saved.wholesale_soldout === target;
  }).length;
  const missed = copies.length - flagged;
  const verb = kind === "soldout" ? "품절" : "재판매";
  const parts = [];
  if (masterCount) parts.push(`마스터상품 ${masterCount}개`);
  if (flagged) parts.push(`마켓 상품 ${flagged}개`);
  let message = parts.length
    ? `${parts.join("와 ")}를 ${verb}로 바꿨습니다.`
    : (kind === "soldout" ? `${stockJob.applied?.[kind] || 0}개 상품을 품절로 바꿨습니다.` : `${stockJob.applied?.[kind] || 0}개 상품을 재판매로 바꿨습니다.`);
  if (missed) {
    message += kind === "soldout"
      ? ` 마켓 상품 ${missed}개는 판매상태만 판매중지로 바꿨습니다.`
      : ` 마켓 상품 ${missed}개는 판매상태만 판매중으로 바꿨습니다.`;
  }
  if (failed) message += ` 마켓 상품 ${failed}개는 바꾸지 못했습니다.`;
  stockListStamp = "";
  renderStockJob(stockJob);
  $("#stockMessage").textContent = message;
  log(message, "ok");
  toast(message);
}
"""


STOCK_MARKET_CSS = """
/* stock-market1 */
.stock-list-row.is-market { padding-left: 28px; background: #fafafa; }
.stock-list-place {
  display: inline-block;
  margin-right: 6px;
  padding: 0 6px;
  border-radius: 999px;
  background: #e7eef8;
  color: #245;
  font-size: 11px;
  line-height: 18px;
  vertical-align: 1px;
}
.stock-list-row.is-market .stock-list-place { background: #f3e7d3; color: #643; }
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
    if "/* stock-market1 */" not in text:
        text = text.rstrip() + "\n" + STOCK_MARKET_JS
    if "/* collect-url2 */" not in text:
        text = text.rstrip() + "\n" + COLLECT_URL2_JS
    if "/* master-login2 */" not in text:
        text = text.rstrip() + "\n" + MASTER_LOGIN2_JS
    if "/* wholesale-import-all1 */" not in text:
        text = text.rstrip() + "\n" + WHOLESALE_IMPORT_ALL_JS
    if "/* server-fix-check1 */" not in text:
        text = text.rstrip() + "\n" + SERVER_FIX_CHECK_JS
    if "/* open-login1 */" not in text:
        text = text.rstrip() + "\n" + OPEN_LOGIN_JS
    if "/* godo-image2 */" not in text:
        text = text.rstrip() + "\n" + GODO_IMAGE2_JS
    if "/* godo-image3 */" not in text:
        text = text.rstrip() + "\n" + GODO_IMAGE3_JS
    if "/* godo-image4 */" not in text:
        text = text.rstrip() + "\n" + GODO_IMAGE4_JS
    if "/* naver-tag1 */" not in text:
        text = text.rstrip() + "\n" + NAVER_TAG_JS
    if "/* name-keyword-tags1 */" not in text:
        text = text.rstrip() + "\n" + NAME_FORBID_JS
    if "/* name-count1 */" not in text:
        text = text.rstrip() + "\n" + NAME_COUNT_JS
    if "/* name-layout1 */" not in text:
        text = text.rstrip() + "\n" + NAME_LAYOUT_JS
    if "/* dialog-resize1 */" not in text:
        text = text.rstrip() + "\n" + DIALOG_RESIZE_JS
    text = text.replace("배포용", "셀러용")
    return _replace_old_versions(text)


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
    if "/* stock-market1 */" not in text:
        extra += STOCK_MARKET_CSS
    if "/* master-login2 */" not in text:
        extra += MASTER_LOGIN2_CSS
    if "/* master-login3 */" not in text:
        extra += MASTER_LOGIN3_CSS
    if extra:
        text = text.rstrip() + "\n" + extra
    if "/* naver-tag1 */" not in text:
        text = text.rstrip() + "\n" + NAVER_TAG_CSS
    if "/* name-keyword-tags1 */" not in text:
        text = text.rstrip() + "\n" + NAME_FORBID_CSS
    if "/* name-count1 */" not in text:
        text = text.rstrip() + "\n" + NAME_COUNT_CSS
    if "/* name-layout1 */" not in text:
        text = text.rstrip() + "\n" + NAME_LAYOUT_CSS
    if "/* dialog-resize1 */" not in text:
        text = text.rstrip() + "\n" + DIALOG_RESIZE_CSS
    return text


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


def _newer_file(path: Path, other: Path) -> bool:
    a, b = path.stat(), other.stat()
    if int(a.st_mtime) != int(b.st_mtime):
        return a.st_mtime > b.st_mtime
    return a.st_size > b.st_size


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
                if dest.read_bytes() == path.read_bytes() or not _newer_file(path, dest):
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


MURRAY_MARKER = "# murray-price1"
MURRAY_PARSE_PY = r'''
# murray-price1
import re as _murray_re
import threading as _murray_threading

_murray_local = _murray_threading.local()


def _murray_won(text):
    match = _murray_re.search(r"(\d{1,3}(?:,\d{3})+|\d+)\s*원", text or "")
    if not match:
        return 0
    try:
        return int(match.group(1).replace(",", ""))
    except ValueError:
        return 0


def _murray_ship_amount(text):
    head = (text or "").split("지역별", 1)[0]
    if _murray_re.search(r"\d", head):
        return _murray_won(head)
    if "무료" in head:
        return 0
    return None


def _murray_compact(text):
    return _murray_re.sub(r"\s+", "", text or "")


def _murray_following(el):
    sibling = el.next_sibling
    steps = 0
    while sibling is not None and steps < 6:
        steps += 1
        getter = getattr(sibling, "get_text", None)
        if getter is not None:
            return getter(" ", strip=True)
        text = str(sibling).strip()
        if text:
            return text
        sibling = sibling.next_sibling
    return ""


def murray_price_fields(html):
    raw = html or ""
    compact = _murray_compact(raw)
    if "판매지도가" not in compact and "딜러공급가" not in compact:
        return 0, 0, None
    guide = 0
    dealer = 0
    ship = None

    def take(label, value):
        nonlocal guide, dealer, ship
        key = _murray_compact(label)
        blob = f"{label or ''} {value or ''}"
        if "판매지도가" in key:
            amount = _murray_won(value) or _murray_won(blob)
            if amount:
                guide = amount
            return
        if "딜러공급가" in key:
            amount = _murray_won(value) or _murray_won(blob)
            if amount:
                dealer = amount
            return
        if "지역별" in key:
            return
        if key == "배송비" or (key.startswith("배송비") and len(key) <= 12 and "원" not in key):
            amount = _murray_ship_amount(value or blob)
            if amount is None:
                amount = _murray_ship_amount(blob)
            if amount is not None:
                ship = amount

    try:
        from bs4 import BeautifulSoup
        try:
            soup = BeautifulSoup(raw, "lxml")
        except Exception:
            soup = BeautifulSoup(raw, "html.parser")
        for row in soup.select("tr"):
            cells = row.find_all(["th", "td"], recursive=False) or row.find_all(["th", "td"])
            if len(cells) >= 2:
                take(cells[0].get_text(" ", strip=True), cells[1].get_text(" ", strip=True))
        for block in soup.select("dl"):
            term = block.find("dt")
            desc = block.find("dd")
            if term is not None and desc is not None:
                take(term.get_text(" ", strip=True), desc.get_text(" ", strip=True))
        for el in soup.find_all(["strong", "span", "th", "dt", "em", "b", "p", "div", "li"]):
            label = el.get_text(" ", strip=True)
            if not label or len(label) > 24:
                continue
            key = _murray_compact(label)
            known = key in {"판매지도가", "딜러공급가", "배송비"} or (
                key.startswith("배송비") and len(key) <= 12 and "지역" not in key and "원" not in key
            )
            if not known:
                continue
            value = _murray_following(el)
            if not _murray_won(value) and "무료" not in value and el.parent is not None:
                parent_text = el.parent.get_text(" ", strip=True)
                if parent_text.startswith(label):
                    value = parent_text[len(label):].strip()
            take(label, value)
    except Exception:
        pass
    plain = _murray_re.sub(r"<[^>]+>", " ", raw)
    plain = _murray_re.sub(r"\s+", " ", plain)
    if not guide:
        match = _murray_re.search(r"판매\s*지도가\s*[:：]?\s*([\d,]+)\s*원", plain)
        if match:
            guide = int(match.group(1).replace(",", ""))
    if not dealer:
        match = _murray_re.search(r"딜러\s*공급가\s*[:：]?\s*([\d,]+)\s*원", plain)
        if match:
            dealer = int(match.group(1).replace(",", ""))
    if ship is None and (guide or dealer):
        match = _murray_re.search(r"(?<![가-힣])배송비\s*[:：]?\s*([\d,]+)\s*원", plain)
        if match:
            ship = int(match.group(1).replace(",", ""))
        elif _murray_re.search(r"(?<![가-힣])배송비\s*[:：]?\s*무료", plain):
            ship = 0
    if not guide and not dealer:
        return 0, 0, None
    return guide, dealer, ship
'''
MURRAY_SCRAPER_PY = MURRAY_PARSE_PY + r'''

_extract_product_before_murray = extract_product


def extract_product(html, page_url=""):
    _murray_local.info = None
    _murray_local.url = str(page_url or "")
    data = _extract_product_before_murray(html, page_url)
    guide, dealer, ship = murray_price_fields(html if isinstance(html, str) else "")
    info = {}
    if isinstance(data, dict):
        if guide:
            data["price"] = int(guide)
            data["original_price"] = int(guide)
            data["_murray_guide"] = int(guide)
            info["guide"] = int(guide)
        if dealer:
            data["cost"] = int(dealer)
            data["_murray_dealer"] = int(dealer)
            info["dealer"] = int(dealer)
        if ship is not None and (guide or dealer):
            data["shipping_fee"] = int(ship)
            data["_murray_ship"] = int(ship)
            info["ship"] = int(ship)
    if info:
        _murray_local.info = info
    return data
'''
MURRAY_SERVICE_PY = r'''
# murray-price1
import re as _murray_re

try:
    from app import scraper as _murray_scraper
except Exception:
    _murray_scraper = None


def _murray_same_page(left, right):
    a = str(left or "").strip()
    b = str(right or "").strip()
    if not a or not b:
        return False
    if a.rstrip("/") == b.rstrip("/"):
        return True
    pattern = r"(?:goodsNo|goods_no|product_no|productno)=(\d+)"
    ma = _murray_re.search(pattern, a, _murray_re.I)
    mb = _murray_re.search(pattern, b, _murray_re.I)
    if ma and mb:
        return ma.group(1) == mb.group(1)
    return a.split("?", 1)[0].rstrip("/") == b.split("?", 1)[0].rstrip("/")


def _murray_apply_fields(item, info):
    if not isinstance(item, dict) or not isinstance(info, dict):
        return False
    changed = False
    guide = int(info.get("guide") or 0)
    dealer = int(info.get("dealer") or 0)
    if guide and int(item.get("price") or 0) != guide:
        item["price"] = guide
        changed = True
    if guide and int(item.get("original_price") or 0) != guide:
        item["original_price"] = guide
        changed = True
    if dealer and int(item.get("cost") or 0) != dealer:
        item["cost"] = dealer
        changed = True
    if "ship" in info:
        ship = int(info.get("ship") or 0)
        current = item.get("shipping_fee")
        if current in (None, "") or int(current or 0) != ship:
            item["shipping_fee"] = ship
            changed = True
    return changed


def _murray_info_from_extract(extracted):
    if not isinstance(extracted, dict):
        return None
    if not extracted.get("_murray_guide") and not extracted.get("_murray_dealer"):
        return None
    info = {}
    if extracted.get("_murray_guide"):
        info["guide"] = int(extracted.get("_murray_guide") or 0)
    if extracted.get("_murray_dealer"):
        info["dealer"] = int(extracted.get("_murray_dealer") or 0)
    if "_murray_ship" in extracted:
        info["ship"] = int(extracted.get("_murray_ship") or 0)
    return info or None


_apply_wholesale_extract_before_murray = _apply_wholesale_extract


def _apply_wholesale_extract(*args, **kwargs):
    changed = _apply_wholesale_extract_before_murray(*args, **kwargs)
    extracted = args[1] if len(args) > 1 else kwargs.get("extracted")
    item = args[0] if args else kwargs.get("item")
    info = _murray_info_from_extract(extracted)
    if info and _murray_apply_fields(item, info):
        changed = True
    return changed


_collect_product_before_murray = collect_product


def collect_product(*args, **kwargs):
    product = _collect_product_before_murray(*args, **kwargs)
    scraper = _murray_scraper
    local = getattr(scraper, "_murray_local", None) if scraper is not None else None
    info = getattr(local, "info", None) if local is not None else None
    seen = getattr(local, "url", "") if local is not None else ""
    if not isinstance(product, dict) or not isinstance(info, dict):
        return product
    source = product.get("source_url") or (args[0] if args else "")
    if seen and source and not _murray_same_page(seen, source):
        return product
    if _murray_apply_fields(product, info):
        save_product(product)
    return product
'''


GODO_MARKER = "# godo-login1"
GODO_SCRAPER_PY = r'''
# godo-login1
import re as _godo_re

_GODO_IMAGE_RE = _godo_re.compile(r"/goods/(\d+)/image/(detail|magnify|main|list|add\d*)/", _godo_re.I)


def _godo_goods_no(page_url):
    match = _godo_re.search(r"goodsNo=(\d+)", str(page_url or ""), _godo_re.I)
    return match.group(1) if match else ""


def godo_gallery_urls(html, page_url=""):
    number = _godo_goods_no(page_url)
    if not number:
        return []
    found = []
    rank = {"magnify": 0, "detail": 1, "main": 2, "list": 3}
    for match in _godo_re.finditer(r"(?:https?:)?//[^\s\"'<>()]+?\.(?:jpe?g|png|gif|webp)", html or "", _godo_re.I):
        url = match.group(0)
        if url.startswith("//"):
            url = "https:" + url
        image = _GODO_IMAGE_RE.search(url)
        if not image or image.group(1) != number:
            continue
        if url not in [item[1] for item in found]:
            found.append((rank.get(image.group(2).lower(), 4), url))
    found.sort(key=lambda item: item[0])
    return [url for _, url in found][:10]


_extract_product_before_godo = extract_product


def extract_product(html, page_url=""):
    data = _extract_product_before_godo(html, page_url)
    if not isinstance(data, dict) or not _godo_goods_no(page_url):
        return data
    urls = godo_gallery_urls(html if isinstance(html, str) else "", page_url)
    if not urls:
        return data
    current = [url for url in (data.get("gallery_images") or []) if _GODO_IMAGE_RE.search(str(url or ""))]
    if current:
        return data
    data["gallery_images"] = urls
    data["images"] = urls + list(data.get("detail_images") or [])
    warnings = data.get("warnings")
    if isinstance(warnings, list):
        data["warnings"] = [text for text in warnings if "이미지를 찾지 못했습니다" not in str(text)]
    return data
'''
GODO_SERVICE_PY = r'''
# godo-login1
import threading as _godo_threading
from urllib.parse import urlparse as _godo_urlparse

_godo_jars = {}
_godo_jar_lock = _godo_threading.Lock()
_GODO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9",
}
GODO_LOGIN_MESSAGE = (
    "공급처 회원 로그인이 필요합니다. 공급처관리에서 이 공급처의 아이디와 비밀번호를 저장한 뒤 다시 가져오세요."
)


def _godo_host(url):
    host = (_godo_urlparse(str(url or "")).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _godo_is_goods_url(url):
    text = str(url or "").lower()
    return "/goods/goods_view" in text and "goodsno=" in text


def _godo_is_login(html, final_url):
    if "/member/login" in str(final_url or "").lower():
        return True
    text = html or ""
    return 'id="formLogin"' in text and 'name="loginPwd"' in text and "goodsNo" not in str(final_url or "")


def _godo_supplier(url, supplier=None):
    item = supplier if isinstance(supplier, dict) else None
    if item is None or not item.get("login_password"):
        wanted = item.get("id") if item else ""
        if not wanted:
            try:
                wanted = _match_wholesaler_id(url)
            except Exception:
                wanted = ""
        if wanted:
            try:
                item = get_wholesaler(wanted, include_secret=True) or item
            except Exception:
                pass
    if not isinstance(item, dict):
        return None
    kind = str(item.get("type") or "").lower()
    if kind and kind != "godomall":
        return None
    if _godo_host(item.get("url")) and _godo_host(item.get("url")) != _godo_host(url):
        return None
    if not str(item.get("login_id") or "").strip() or not str(item.get("login_password") or ""):
        return None
    return item


def _godo_base(url):
    parsed = _godo_urlparse(str(url or ""))
    return f"{parsed.scheme or 'http'}://{parsed.netloc}"


def _godo_login(client, url, supplier):
    base = _godo_base(url)
    client.get(base + "/member/login.php")
    response = client.post(
        base + "/member/login_ps.php",
        data={
            "mode": "login",
            "returnUrl": "",
            "loginId": str(supplier.get("login_id") or "").strip(),
            "loginPwd": str(supplier.get("login_password") or ""),
        },
        headers={"Referer": base + "/member/login.php"},
    )
    text = response.text or ""
    if "alert(" in text and ("찾을 수 없" in text or "일치하지" in text or "승인" in text or "잘못" in text):
        return False
    return True


def _godo_fetch(url, supplier):
    key = (_godo_host(url), str(supplier.get("login_id") or "").strip())
    for attempt in range(2):
        with _godo_jar_lock:
            saved = list(_godo_jars.get(key) or [])
        jar = httpx.Cookies()
        for name, value, domain, path in saved:
            jar.set(name, value, domain=domain, path=path)
        client = httpx.Client(headers=_GODO_HEADERS, follow_redirects=True, timeout=25.0, cookies=jar)
        try:
            if not saved or attempt:
                if not _godo_login(client, url, supplier):
                    return None
            response = client.get(url)
            html = response.text or ""
            final_url = str(response.url)
            if response.status_code < 400 and not _godo_is_login(html, final_url):
                with _godo_jar_lock:
                    _godo_jars[key] = [(c.name, c.value, c.domain, c.path) for c in client.cookies.jar]
                return client, html, final_url
        except httpx.HTTPError:
            client.close()
            return None
        client.close()
        with _godo_jar_lock:
            _godo_jars.pop(key, None)
    return None


_load_page_before_godo = _load_page


def _load_page(url):
    if _godo_is_goods_url(url):
        supplier = _godo_supplier(url)
        if supplier is not None:
            fetched = _godo_fetch(url, supplier)
            if fetched is not None:
                client, html, final_url = fetched
                session = PageSession()
                session._http = client
                session.html = html
                session.final_url = final_url
                session.via = "http"
                session.extracted = None
                return session
    session = _load_page_before_godo(url)
    if _godo_is_goods_url(url) and session is not None and _godo_is_login(getattr(session, "html", ""), getattr(session, "final_url", "")):
        try:
            session.close()
        except Exception:
            pass
        _bad(GODO_LOGIN_MESSAGE)
    return session


_read_supplier_product_before_godo = _read_supplier_product


def _read_supplier_product(url, cookies=None, supplier=None, *args, **kwargs):
    if _godo_is_goods_url(url):
        found = _godo_supplier(url, supplier)
        if found is not None:
            fetched = _godo_fetch(url, found)
            if fetched is not None:
                client, html, final_url = fetched
                client.close()
                return extract_product(html, final_url)
            raise RuntimeError(GODO_LOGIN_MESSAGE)
    return _read_supplier_product_before_godo(url, cookies, supplier, *args, **kwargs)


_gallery_ready_before_godo = _gallery_ready


def _gallery_ready(item, *args, **kwargs):
    if isinstance(item, dict) and _godo_is_goods_url(item.get("source_url")) and not int(item.get("cost") or 0):
        return False
    return _gallery_ready_before_godo(item, *args, **kwargs)
'''


GODO_NAME_MARKER = "# godo-name1"
GODO_NAME_SCRAPER_PY = r'''
# godo-name1
def _godo_text(node):
    return " ".join(node.get_text(" ", strip=True).split()) if node is not None else ""


def godo_goods_name(html, page_url=""):
    number = _godo_goods_no(page_url)
    if not number:
        return ""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html or "", "lxml")
    except Exception:
        return ""
    for selector in (
        ".goods-view .goods-header h2", ".goods-view .goods-header h3", ".goods-view .info h2",
        ".goods-view .info h3", ".item_detail_tit h3", ".item_detail_tit h2", ".goods_name", "#goodsNm",
    ):
        text = _godo_text(soup.select_one(selector))
        if 2 <= len(text) <= 200 and not text.isdigit():
            return text
    for img in soup.find_all("img"):
        src = str(img.get("src") or img.get("data-src") or "")
        image = _GODO_IMAGE_RE.search(src)
        if not image or image.group(1) != number:
            continue
        text = " ".join(str(img.get("alt") or img.get("title") or "").split())
        if 2 <= len(text) <= 200 and not text.isdigit():
            return text
    return ""


_extract_product_before_godo_name = extract_product


def extract_product(html, page_url=""):
    data = _extract_product_before_godo_name(html, page_url)
    if not isinstance(data, dict) or not _godo_goods_no(page_url):
        return data
    name = godo_goods_name(html if isinstance(html, str) else "", page_url)
    if name:
        data["name"] = name
        data["original_name"] = name
        warnings = data.get("warnings")
        if isinstance(warnings, list):
            data["warnings"] = [text for text in warnings if "상품명을 찾지 못했습니다" not in str(text)]
    return data
'''
GODO_NAME_CATALOG_PY = r'''
# godo-name1
def _godo_bad_name(name, number):
    text = str(name or "").strip()
    return not text or text.isdigit() or text == str(number or "") or text.startswith("공급처 상품") or text == "품절"


def _godo_list_names(shop_url, category):
    base = _base(shop_url)
    cate = str(category or "").strip()
    if cate in {"", "all", "etc"}:
        cate = ""
    names = {}
    try:
        with httpx.Client(headers=PAGE_HEADERS, follow_redirects=True, timeout=30.0) as client:
            for page in range(1, 31):
                params = {"page": page}
                if cate:
                    params["cateCd"] = cate
                response = client.get(f"{base}/goods/goods_list.php", params=params)
                if response.status_code >= 400:
                    break
                soup = BeautifulSoup(response.text, "lxml")
                added = 0
                for link in soup.select("a[href*='goodsNo'], a[href*='goods_view']"):
                    number = _godo_goods_from_href(str(link.get("href") or ""))
                    if not number or number in names:
                        continue
                    name = ""
                    img = link.find("img")
                    if img is not None:
                        name = " ".join(str(img.get("alt") or img.get("title") or "").split())
                    if _godo_bad_name(name, number):
                        box = link.find_parent("li") or link.parent
                        node = box.select_one(".name, .item_name, .goods_name, .prdName") if box is not None else None
                        name = " ".join(node.get_text(" ", strip=True).split()) if node is not None else ""
                    if not _godo_bad_name(name, number):
                        names[number] = name
                        added += 1
                if not added:
                    break
    except httpx.HTTPError:
        return names
    return names


_godomall_products_before_name = _godomall_products


def _godomall_products(shop_url, category=None, *args, **kwargs):
    data = _godomall_products_before_name(shop_url, category, *args, **kwargs)
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return data
    bad = [item for item in items if isinstance(item, dict) and _godo_bad_name(item.get("name"), item.get("product_no"))]
    if not bad:
        return data
    names = _godo_list_names(shop_url, category)
    for item in bad:
        name = names.get(str(item.get("product_no") or ""))
        if name:
            item["name"] = name
    return data
'''
GODO_NAME_SERVICE_PY = r'''
# godo-name1
_collect_product_before_godo_name = collect_product


def collect_product(*args, **kwargs):
    product = _collect_product_before_godo_name(*args, **kwargs)
    if not isinstance(product, dict) or not _godo_is_goods_url(product.get("source_url")):
        return product
    if str(product.get("wholesale_product_no") or "").strip():
        return product
    match = _murray_re.search(r"goodsNo=(\d+)", str(product.get("source_url") or ""), _murray_re.I)
    if match:
        product["wholesale_product_no"] = match.group(1)
        save_product(product)
    return product
'''
GODO_NAME2_MARKER = "# godo-name2"
GODO_NAME2_CATALOG_PY = r'''
# godo-name2
# Godomall answers goods_list.php without cateCd with "잘못된 접근입니다", so
# the whole-shop import found no list names. Walk the shop's own categories.
_godo_known_names = {}
_godo_bad_name_before_name2 = _godo_bad_name


def _godo_bad_name(name, number):
    return _godo_bad_name_before_name2(name, number) or str(name or "").strip() == "이름 없는 상품"


def _godo_cate_links(shop_url):
    base = _base(shop_url)
    found = []
    try:
        with httpx.Client(headers=PAGE_HEADERS, follow_redirects=True, timeout=30.0) as client:
            response = client.get(base + "/")
        soup = BeautifulSoup(response.text, "lxml")
        for link in soup.select("a[href*='cateCd']"):
            code = _godo_cate_from_href(str(link.get("href") or ""))
            label = " ".join(link.get_text(" ", strip=True).split())
            if code and code not in [item[0] for item in found]:
                found.append((code, label))
    except Exception:
        return []
    return found


def _godo_all_cates(shop_url):
    found = _godo_cate_links(shop_url)
    whole = [code for code, label in found if "전체" in label]
    top = [code for code, label in found if len(code) <= 3 and code not in whole]
    rest = [code for code, label in found if code not in whole and code not in top]
    return whole + top + rest


def _godo_whole_shop(shop_url, data, *args, **kwargs):
    found = _godo_cate_links(shop_url)
    whole = [code for code, label in found if "전체" in label]
    top = [code for code, label in found if len(code) <= 3 and code not in whole]
    seen = {}
    for group in (whole[:1], top[:60]):
        for cate in group:
            part = _godomall_products_before_name(shop_url, cate, *args, **kwargs)
            for item in (part.get("items") if isinstance(part, dict) else None) or []:
                if isinstance(item, dict):
                    seen.setdefault(str(item.get("product_no") or item.get("url") or ""), item)
        if seen:
            break
    if not seen:
        return data
    merged = dict(data) if isinstance(data, dict) else {}
    merged["items"] = list(seen.values())
    merged["count"] = len(merged["items"])
    return merged


def _godo_names_for(shop_url, category, wanted):
    names = _godo_list_names(shop_url, category)
    need = set(wanted) - set(names)
    if need:
        for cate in _godo_all_cates(shop_url)[:60]:
            if cate == str(category or "").strip():
                continue
            more = _godo_list_names(shop_url, cate)
            for number, name in more.items():
                names.setdefault(number, name)
            need -= set(more)
            if not need:
                break
    return names


def _godomall_products(shop_url, category=None, *args, **kwargs):
    data = _godomall_products_before_name(shop_url, category, *args, **kwargs)
    items = data.get("items") if isinstance(data, dict) else None
    if not items and str(category or "").strip() in {"", "all"}:
        data = _godo_whole_shop(shop_url, data, *args, **kwargs)
        items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return data
    bad = [item for item in items if isinstance(item, dict) and _godo_bad_name(item.get("name"), item.get("product_no"))]
    if not bad:
        return data
    names = _godo_names_for(shop_url, category, {str(item.get("product_no") or "") for item in bad})
    _godo_known_names.update(names)
    for item in bad:
        name = names.get(str(item.get("product_no") or ""))
        if name:
            item["name"] = name
    return data
'''
GODO_NAME2_SERVICE_PY = r'''
# godo-name2
_import_wholesale_catalog_before_name2 = import_wholesale_catalog


def _godo_repair_saved_names(wholesaler_id):
    import app.shop_catalog as _godo_catalog

    known = getattr(_godo_catalog, "_godo_known_names", None) or {}
    bad_name = getattr(_godo_catalog, "_godo_bad_name", None)
    if not known or bad_name is None:
        return 0
    fixed = []
    for product in list_full_products():
        if str(product.get("wholesale_id") or "") != str(wholesaler_id or ""):
            continue
        number = str(product.get("wholesale_product_no") or "").strip()
        name = known.get(number)
        if not name or not bad_name(product.get("name"), number):
            continue
        product["name"] = name
        if bad_name(product.get("original_name"), number):
            product["original_name"] = name
        fixed.append(product)
    if fixed:
        save_products_batch(fixed)
    return len(fixed)


def import_wholesale_catalog(wholesaler_id, *args, **kwargs):
    result = _import_wholesale_catalog_before_name2(wholesaler_id, *args, **kwargs)
    try:
        renamed = _godo_repair_saved_names(wholesaler_id)
        if renamed and isinstance(result, dict):
            result["renamed"] = renamed
    except Exception:
        pass
    return result
'''
COLLECT_URL2_JS = r"""
/* collect-url2 */
function collectIdentity(url) {
  const raw = String(url || "").trim();
  if (!raw) return { key: "", no: "" };
  let parsed = null;
  try { parsed = new URL(raw, location.href); } catch (error) { parsed = null; }
  const idNames = ["product_no", "productno", "goods_no", "goodsno", "it_id", "product_id", "prdno", "item_id", "branduid", "idx"];
  if (!parsed) {
    const plain = raw.replace(/\/+$/, "").toLowerCase().split("?")[0];
    return { key: plain, no: "" };
  }
  let found = "";
  let foundName = "";
  idNames.forEach((name) => {
    if (found) return;
    for (const [key, value] of parsed.searchParams.entries()) {
      if (String(key).toLowerCase() !== name) continue;
      if (value && String(value).trim()) {
        found = String(value).trim();
        foundName = name;
        return;
      }
    }
  });
  const path = parsed.pathname.replace(/\/+$/, "");
  const pretty = path.match(/\/product\/[^/]+\/(\d+)(?:\/|$)/i);
  const no = found || (pretty ? pretty[1] : "");
  const host = parsed.host.replace(/^www\./i, "");
  const key = found
    ? `${host}${path}?${foundName}=${found}`.toLowerCase()
    : `${host}${path}`.toLowerCase();
  return { key, no };
}
function cafe24CollectedKeys(wholesalerId) {
  const nos = new Set();
  const urls = new Set();
  const id = String(wholesalerId || "");
  products.forEach((item) => {
    if (!isMasterProduct(item)) return;
    const owner = String(productWholesalerId(item) || "");
    if (id && owner && owner !== id) return;
    const ident = collectIdentity(item.source_url);
    const no = String(item.wholesale_product_no || "").trim();
    if (owner) {
      if (no) nos.add(no);
      if (ident.no) nos.add(ident.no);
    }
    if (ident.key) urls.add(ident.key);
  });
  return { nos, urls };
}
"""


def _append_marked_source(path: Path, snippet: str, required, marker: str = MURRAY_MARKER) -> bool:
    if not path.is_file():
        return False
    text, newline = read_text(path)
    if marker in text:
        return False
    needed = (required,) if isinstance(required, str) else tuple(required)
    if any(name not in text for name in needed):
        return False
    updated = text.rstrip() + "\n\n" + snippet.strip() + "\n"
    try:
        compile(updated, str(path), "exec")
    except SyntaxError:
        return False
    write_text(path, updated, newline)
    return True


def patch_murray_sources(root: Path) -> bool:
    changed = False
    scraper = root / "app" / "scraper.py"
    service = root / "app" / "service.py"
    if _append_marked_source(scraper, MURRAY_SCRAPER_PY, "def extract_product"):
        changed = True
    if _append_marked_source(service, MURRAY_SERVICE_PY, "def _apply_wholesale_extract"):
        changed = True
    if _append_marked_source(scraper, GODO_SCRAPER_PY, "def extract_product", GODO_MARKER):
        changed = True
    godo_needed = (
        "def _read_supplier_product",
        "def _load_page",
        "def _gallery_ready",
        "def _match_wholesaler_id",
        "PageSession",
    )
    if _append_marked_source(service, GODO_SERVICE_PY, godo_needed, GODO_MARKER):
        changed = True
    if _append_marked_source(scraper, GODO_NAME_SCRAPER_PY, ("def extract_product", GODO_MARKER), GODO_NAME_MARKER):
        changed = True
    catalog_needed = ("def _godomall_products", "def _godo_goods_from_href", "def _base", "PAGE_HEADERS", "BeautifulSoup", "httpx")
    if _append_marked_source(root / "app" / "shop_catalog.py", GODO_NAME_CATALOG_PY, catalog_needed, GODO_NAME_MARKER):
        changed = True
    if _append_marked_source(service, GODO_NAME_SERVICE_PY, ("def collect_product", GODO_MARKER, MURRAY_MARKER), GODO_NAME_MARKER):
        changed = True
    if _append_marked_source(root / "app" / "shop_catalog.py", GODO_NAME2_CATALOG_PY, GODO_NAME2_CATALOG_NEEDED, GODO_NAME2_MARKER):
        changed = True
    if _append_marked_source(service, GODO_NAME2_SERVICE_PY, GODO_NAME2_SERVICE_NEEDED, GODO_NAME2_MARKER):
        changed = True
    if _append_marked_source(root / "app" / "shop_catalog.py", GODO_SITE1_CATALOG_PY, GODO_SITE1_CATALOG_NEEDED, GODO_SITE1_MARKER):
        changed = True
    if _append_marked_source(service, GODO_SITE2_SERVICE_PY, GODO_SITE2_SERVICE_NEEDED, GODO_SITE2_MARKER):
        changed = True
    if _append_marked_source(service, GODO_OPEN1_SERVICE_PY, GODO_OPEN1_SERVICE_NEEDED, GODO_OPEN1_MARKER):
        changed = True
    if _append_marked_source(service, GODO_LOGIN2_SERVICE_PY, GODO_LOGIN2_SERVICE_NEEDED, GODO_LOGIN2_MARKER):
        changed = True
    if _append_marked_source(root / "app" / "shop_catalog.py", GODO_IMAGE1_CATALOG_PY, GODO_IMAGE1_CATALOG_NEEDED, GODO_IMAGE1_MARKER):
        changed = True
    if _append_marked_source(scraper, GODO_IMAGE1_SCRAPER_PY, GODO_IMAGE1_SCRAPER_NEEDED, GODO_IMAGE1_MARKER):
        changed = True
    if _append_marked_source(scraper, GODO_IMAGE2_SCRAPER_PY, GODO_IMAGE2_SCRAPER_NEEDED, GODO_IMAGE2_MARKER):
        changed = True
    if _append_marked_source(service, GODO_IMAGE2_SERVICE_PY, GODO_IMAGE2_SERVICE_NEEDED, GODO_IMAGE2_MARKER):
        changed = True
    if _append_marked_source(root / "app" / "shop_catalog.py", GODO_IMAGE2_CATALOG_PY, GODO_IMAGE2_CATALOG_NEEDED, GODO_IMAGE2_MARKER):
        changed = True
    if _append_marked_source(scraper, GODO_IMAGE3_SCRAPER_PY, GODO_IMAGE3_SCRAPER_NEEDED, GODO_IMAGE3_MARKER):
        changed = True
    if _append_marked_source(root / "app" / "shop_catalog.py", GODO_IMAGE3_CATALOG_PY, GODO_IMAGE3_CATALOG_NEEDED, GODO_IMAGE3_MARKER):
        changed = True
    if _append_marked_source(scraper, GODO_IMAGE4_SCRAPER_PY, GODO_IMAGE4_SCRAPER_NEEDED, GODO_IMAGE4_MARKER):
        changed = True
    if _append_marked_source(root / "app" / "shop_catalog.py", GODO_IMAGE4_CATALOG_PY, GODO_IMAGE4_CATALOG_NEEDED, GODO_IMAGE4_MARKER):
        changed = True
    if _append_marked_source(service, NAVER_TAG_SERVICE_PY, NAVER_TAG_SERVICE_NEEDED, NAVER_TAG_MARKER):
        changed = True
    if _append_marked_source(root / "app" / "chrome_app.py", TEXT_DECODE1_CHROME_PY, TEXT_DECODE1_CHROME_NEEDED, TEXT_DECODE1_MARKER):
        changed = True
    try:
        write_fix_status(root)
    except OSError:
        pass
    return changed


GODO_SITE1_MARKER = "# godo-site1"
GODO_SITE1_CATALOG_PY = r'''
# godo-site1
# detect_shop_type returns "" for Godomall home pages such as murray.co.kr, so
# suppliers were saved as another type and only the home page links (named by
# goods number) were read. Godomall sites are recognised by their goods links,
# and https://www. hosts whose certificate does not match fall back to http.
_godo_site_cache = {}
_detect_shop_type_before_site = detect_shop_type
_list_all_products_before_site = list_all_products
_list_category_before_site = list_category
_discover_groups_before_site = discover_groups


def _godo_site_base(shop_url):
    raw = str(shop_url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else "http://" + raw)
    host = (parsed.netloc or "").strip().lower()
    if not host:
        return ""
    if host in _godo_site_cache:
        return _godo_site_cache[host]
    bare = host[4:] if host.startswith("www.") else host
    scheme = parsed.scheme or "http"
    tries = []
    for base in (f"{scheme}://{host}", f"http://{host}", f"http://{bare}", f"http://www.{bare}", f"https://{bare}"):
        if base not in tries:
            tries.append(base)
    found = ""
    for base in tries:
        try:
            html = _get(base + "/", timeout=15.0)
        except Exception:
            continue
        if "goods_view.php?goodsNo=" in html or "goods_list.php?cateCd=" in html:
            found = base
        break
    _godo_site_cache[host] = found
    return found


def _godo_site_kind(shop_url, shop_type):
    kind = str(shop_type or "").strip().lower()
    if kind in {"cafe24", "imweb"}:
        return kind, shop_url
    base = _godo_site_base(shop_url)
    if base:
        return "godomall", base
    return shop_type, shop_url


def detect_shop_type(shop_url):
    kind = _detect_shop_type_before_site(shop_url)
    if kind:
        return kind
    return "godomall" if _godo_site_base(shop_url) else kind


def list_all_products(shop_url, shop_type, *args, **kwargs):
    kind, url = _godo_site_kind(shop_url, shop_type)
    if kind == "godomall":
        items = _godomall_all(url)
        if items:
            return items
    return _list_all_products_before_site(shop_url, shop_type, *args, **kwargs)


def list_category(shop_url, shop_type, *args, **kwargs):
    kind, url = _godo_site_kind(shop_url, shop_type)
    return _list_category_before_site(url, kind, *args, **kwargs)


def discover_groups(shop_url, shop_type, *args, **kwargs):
    kind, url = _godo_site_kind(shop_url, shop_type)
    return _discover_groups_before_site(url, kind, *args, **kwargs)
'''
GODO_SITE1_CATALOG_NEEDED = (
    "def detect_shop_type",
    "def list_all_products",
    "def list_category",
    "def discover_groups",
    "def _godomall_all",
    "def _get",
    "urlparse",
    GODO_NAME2_MARKER,
)
GODO_SITE2_MARKER = "# godo-site2"
GODO_SITE2_SERVICE_PY = r"""
# godo-site2
# The screen reads server_fixes to tell an old server process (needs a restart)
# from a source the fixes could not be added to.
_list_wholesale_catalog_before_site2 = list_wholesale_catalog
_import_wholesale_catalog_before_site2 = import_wholesale_catalog


def _godo_server_fixes():
    import app.shop_catalog as _godo_catalog

    return {
        "godo_name": hasattr(_godo_catalog, "_godo_names_for"),
        "godo_site": hasattr(_godo_catalog, "_godo_site_base"),
    }


def list_wholesale_catalog(wholesaler_id, *args, **kwargs):
    result = _list_wholesale_catalog_before_site2(wholesaler_id, *args, **kwargs)
    if isinstance(result, dict):
        result["server_fixes"] = _godo_server_fixes()
    return result


def import_wholesale_catalog(wholesaler_id, *args, **kwargs):
    result = _import_wholesale_catalog_before_site2(wholesaler_id, *args, **kwargs)
    if isinstance(result, dict):
        result["server_fixes"] = _godo_server_fixes()
    return result
"""
GODO_LOGIN2_MARKER = "# godo-login2"
GODO_LOGIN2_SERVICE_PY = r"""
# godo-login2
# godo-login1 saved the session with dict(client.cookies), which drops cookie
# domains. Murray sets analytics_* again for .murray.co.kr, so the next fetch
# held two cookies with one name and httpx raised CookieConflict.
_godo_jars = {}


def _godo_fetch(url, supplier):
    key = (_godo_host(url), str(supplier.get("login_id") or "").strip())
    for attempt in range(2):
        with _godo_jar_lock:
            saved = list(_godo_jars.get(key) or [])
        jar = httpx.Cookies()
        for name, value, domain, path in saved:
            jar.set(name, value, domain=domain, path=path)
        client = httpx.Client(headers=_GODO_HEADERS, follow_redirects=True, timeout=25.0, cookies=jar)
        try:
            if not saved or attempt:
                if not _godo_login(client, url, supplier):
                    return None
            response = client.get(url)
            html = response.text or ""
            final_url = str(response.url)
            if response.status_code < 400 and not _godo_is_login(html, final_url):
                with _godo_jar_lock:
                    _godo_jars[key] = [(c.name, c.value, c.domain, c.path) for c in client.cookies.jar]
                return client, html, final_url
        except httpx.HTTPError:
            client.close()
            return None
        client.close()
        with _godo_jar_lock:
            _godo_jars.pop(key, None)
    return None
"""
GODO_LOGIN2_SERVICE_NEEDED = ("def _godo_fetch", "_godo_jar_lock", "_godo_login", GODO_MARKER)
GODO_IMAGE1_MARKER = "# godo-image1"
GODO_IMAGE1_SCRAPER_PY = r"""
# godo-image1
# Murray pages put long description images ahead of the goods photos, so the
# first gallery image (the representative) was a detail strip. Keep only this
# goods number's own photos, falling back to the list page's main image.
_extract_product_before_godo_image = extract_product


def _godo_own_image(url, number):
    match = _GODO_IMAGE_RE.search(str(url or ""))
    return bool(match and match.group(1) == number)


def _godo_list_image(page_url, number):
    try:
        import app.shop_catalog as _godo_catalog

        return _godo_catalog._godo_image_for(page_url, number)
    except Exception:
        return ""


def extract_product(html, page_url=""):
    data = _extract_product_before_godo_image(html, page_url)
    number = _godo_goods_no(page_url)
    if not isinstance(data, dict) or not number:
        return data
    gallery = [str(url) for url in (data.get("gallery_images") or []) if url]
    own = [url for url in gallery if _godo_own_image(url, number)]
    if not own:
        own = godo_gallery_urls(html if isinstance(html, str) else "", page_url)
    if not own:
        main = _godo_list_image(page_url, number)
        own = [main] if main else []
    if not own:
        return data
    detail = [str(url) for url in (data.get("detail_images") or []) if url and str(url) not in own]
    for url in gallery:
        if url not in own and url not in detail and not _GODO_IMAGE_RE.search(url):
            detail.append(url)
    data["gallery_images"] = own
    data["detail_images"] = detail
    data["images"] = own + detail
    warnings = data.get("warnings")
    if isinstance(warnings, list):
        data["warnings"] = [text for text in warnings if "이미지를 찾지 못했습니다" not in str(text)]
    return data
"""
GODO_IMAGE1_SCRAPER_NEEDED = ("def extract_product", "def godo_gallery_urls", "_GODO_IMAGE_RE", GODO_MARKER)
GODO_IMAGE1_CATALOG_PY = r"""
# godo-image1
import threading as _godo_threading

_godo_known_images = {}
_godo_image_sites = set()
_godo_image_lock = _godo_threading.Lock()
_godomall_products_before_image = _godomall_products


def _godomall_products(shop_url, category=None, *args, **kwargs):
    data = _godomall_products_before_image(shop_url, category, *args, **kwargs)
    for item in (data.get("items") if isinstance(data, dict) else None) or []:
        if isinstance(item, dict) and item.get("product_no") and item.get("image"):
            _godo_known_images[str(item.get("product_no"))] = str(item.get("image"))
    return data


def _godo_image_for(page_url, number):
    number = str(number or "")
    if number in _godo_known_images:
        return _godo_known_images[number]
    finder = globals().get("_godo_site_base")
    base = (finder(page_url) if finder else "") or _base(page_url)
    with _godo_image_lock:
        if base in _godo_image_sites:
            return _godo_known_images.get(number, "")
        _godo_image_sites.add(base)
        try:
            _godomall_all(base)
        except Exception:
            pass
    return _godo_known_images.get(number, "")
"""
GODO_IMAGE1_CATALOG_NEEDED = ("def _godomall_products", "def _godomall_all", "def _base", GODO_SITE1_MARKER)
GODO_IMAGE2_MARKER = "# godo-image2"
GODO_IMAGE2_JS = r"""
/* godo-image2 */
function godoGoodsNumber(url) {
  const match = String(url || "").match(/goodsNo=(\d+)/i);
  return match ? match[1] : "";
}
function godoPhotoRank(url, number) {
  const path = String(url || "").split("#")[0].split("?")[0];
  const match = path.match(/\/goods\/(\d+)\/image\/(main|list|magnify|detail|add\d*)\//i);
  if (!match || String(match[1]) !== String(number) || /\/thumb\//i.test(path)) return null;
  const kind = match[2].toLowerCase();
  if (kind === "main") return 0;
  if (kind === "list") return 1;
  if (kind === "magnify") return 2;
  if (kind === "detail") return 3;
  return 4;
}
function godoIsStrip(image) {
  const width = Number(image?.width || 0);
  const height = Number(image?.height || 0);
  return width >= 100 && height >= width * 2;
}
function godoApplyRepresentative(product) {
  const images = product?.images;
  const number = godoGoodsNumber(product?.source_url);
  if (!number || !Array.isArray(images) || !images.length) return false;
  const photos = images.filter((image) => godoPhotoRank(image?.source_url, number) !== null);
  photos.sort((a, b) => godoPhotoRank(a.source_url, number) - godoPhotoRank(b.source_url, number));
  let best = photos[0] || null;
  if (!best) {
    const squares = images.filter((image) => image && !godoIsStrip(image) && Number(image.width || 0) >= 150 && Number(image.height || 0) >= 150);
    const current = images.find((image) => image?.representative);
    if (!squares.length || (current && !godoIsStrip(current))) return false;
    best = squares[0];
  }
  let changed = false;
  images.forEach((image) => {
    if (!image || typeof image !== "object") return;
    const rank = godoPhotoRank(image.source_url, number);
    const wantRep = image === best;
    let wantKind = image.kind;
    if (rank !== null || wantRep) wantKind = "gallery";
    else if (image.source_url || godoIsStrip(image)) wantKind = "detail";
    if (!!image.representative !== wantRep) {
      image.representative = wantRep;
      changed = true;
    }
    if (wantKind && image.kind !== wantKind) {
      image.kind = wantKind;
      changed = true;
    }
  });
  return changed;
}
if (typeof fillPreview === "function" && !fillPreview._godoImage2) {
  const fillPreviewBeforeGodo = fillPreview;
  const wrapped = function () {
    const product = typeof current !== "undefined" ? current : null;
    if (product && godoApplyRepresentative(product) && !wrapped._saving) {
      const master = typeof isMasterProduct === "function" && isMasterProduct(product);
      if (!master && typeof saveProduct === "function") {
        wrapped._saving = true;
        Promise.resolve(saveProduct(product, { images: product.images }, true)).catch(() => {}).finally(() => {
          wrapped._saving = false;
        });
      }
    }
    return fillPreviewBeforeGodo();
  };
  wrapped._godoImage2 = true;
  fillPreview = wrapped;
}
"""
GODO_IMAGE2_SCRAPER_PY = r'''
# godo-image2
# The representative image is this goods number's own photo (main, then list,
# magnify, detail). Long description images, including ones stored ahead of the
# photos, stay detail images. Thumb files are not the representative.
_GODO_PHOTO_RE = _godo_re.compile(r"/goods/(\d+)/image/(main|list|magnify|detail|add\d*)/", _godo_re.I)
_GODO_PHOTO_RANK = {"main": 0, "list": 1, "magnify": 2, "detail": 3}
_extract_product_before_godo_image2 = extract_product


def _godo_clean_url(url):
    text = str(url or "").strip().rstrip("\\")
    if text.startswith("//"):
        text = "https:" + text
    if "\\" in text:
        text = text.split("\\", 1)[0]
    return text


def _godo_image_url(item):
    if isinstance(item, str):
        return _godo_clean_url(item)
    if isinstance(item, dict):
        return _godo_clean_url(item.get("source_url") or item.get("url") or "")
    return ""


def _godo_photo_rank(url, number):
    path = _godo_clean_url(url).split("#", 1)[0].split("?", 1)[0]
    match = _GODO_PHOTO_RE.search(path)
    if not match or match.group(1) != str(number or "") or "/thumb/" in path.lower():
        return None
    kind = match.group(2).lower()
    if kind.startswith("add"):
        return 4
    return _GODO_PHOTO_RANK.get(kind, 5)


def _godo_is_strip(image):
    if not isinstance(image, dict):
        return False
    try:
        width = int(image.get("width") or 0)
        height = int(image.get("height") or 0)
    except (TypeError, ValueError):
        return False
    return width >= 100 and height >= width * 2


def _godo_skip_url(url):
    text = _godo_clean_url(url).lower()
    return any(part in text for part in (
        "/data/skin/", "/img/btn/", "/img/banner/", "/img/etc/",
        "pinterest.com", "facebook.com", "twitter.com", "googletagmanager",
    ))


def _godo_cached_photo(number):
    try:
        import app.shop_catalog as _godo_catalog

        known = getattr(_godo_catalog, "_godo_known_images", {}) or {}
        url = str(known.get(str(number)) or "")
    except Exception:
        return ""
    if _godo_photo_rank(url, number) is None:
        return ""
    return _godo_clean_url(url)


def _godo_ordered_photos(html, number, extra):
    found = []
    seen = set()

    def add(url):
        url = _godo_clean_url(url)
        rank = _godo_photo_rank(url, number)
        if rank is None or url in seen:
            return
        seen.add(url)
        found.append((rank, url))

    for match in _godo_re.finditer(r"(?:https?:)?//[^\s\"'<>\\]+", html or "", _godo_re.I):
        add(match.group(0))
    for match in _godo_re.finditer(r"(?:src|data-src|data-original)\s*=\s*[\"']([^\"']+)", html or "", _godo_re.I):
        add(match.group(1))
    for url in extra or []:
        add(url)
    add(_godo_cached_photo(number))
    found.sort(key=lambda item: item[0])
    return [url for _, url in found]


def godo_fix_saved_images(product):
    if not isinstance(product, dict):
        return False
    number = _godo_goods_no(product.get("source_url"))
    images = product.get("images")
    if not number or not isinstance(images, list) or not images:
        return False
    photos = []
    for image in images:
        if not isinstance(image, dict):
            continue
        rank = _godo_photo_rank(_godo_image_url(image), number)
        if rank is not None:
            photos.append((rank, image))
    photos.sort(key=lambda item: item[0])
    best = photos[0][1] if photos else None
    if best is None:
        squares = []
        for image in images:
            if not isinstance(image, dict) or _godo_is_strip(image):
                continue
            try:
                width = int(image.get("width") or 0)
                height = int(image.get("height") or 0)
            except (TypeError, ValueError):
                continue
            if width >= 150 and height >= 150:
                squares.append(image)
        current = next((image for image in images if isinstance(image, dict) and image.get("representative")), None)
        if not squares or (current is not None and not _godo_is_strip(current)):
            return False
        best = squares[0]
    changed = False
    for image in images:
        if not isinstance(image, dict):
            continue
        url = _godo_image_url(image)
        rank = _godo_photo_rank(url, number)
        want_rep = image is best
        if rank is not None or want_rep:
            want_kind = "gallery"
        elif url or _godo_is_strip(image):
            want_kind = "detail"
        else:
            want_kind = image.get("kind")
        if bool(image.get("representative")) != want_rep:
            image["representative"] = want_rep
            changed = True
        if want_kind and image.get("kind") != want_kind:
            image["kind"] = want_kind
            changed = True
    return changed


def extract_product(html, page_url=""):
    data = _extract_product_before_godo_image2(html, page_url)
    number = _godo_goods_no(page_url)
    if not isinstance(data, dict) or not number:
        return data
    html_text = html if isinstance(html, str) else ""
    buckets = []
    for key in ("detail_images", "gallery_images", "images"):
        buckets.extend(data.get(key) or [])
    extra = [_godo_image_url(item) for item in buckets]
    photos = _godo_ordered_photos(html_text, number, extra)
    if not photos:
        return data
    photo_set = set(photos)
    description = []
    for item in buckets:
        url = _godo_image_url(item)
        if not url or url in photo_set or url in description or _godo_skip_url(url):
            continue
        if _godo_photo_rank(url, number) is not None:
            continue
        path = url.split("?", 1)[0].lower()
        if "/thumb/" in path and "/goods/" in path and "/image/" in path:
            continue
        description.append(url)
    data["gallery_images"] = photos
    data["detail_images"] = description
    images = data.get("images") or []
    has_photo = any(
        isinstance(item, dict) and _godo_photo_rank(_godo_image_url(item), number) is not None
        for item in images
    )
    if images and isinstance(images[0], dict) and has_photo:
        holder = {"source_url": page_url, "images": [dict(item) if isinstance(item, dict) else item for item in images]}
        godo_fix_saved_images(holder)
        data["images"] = holder["images"]
    else:
        data["images"] = photos + description
    warnings = data.get("warnings")
    if isinstance(warnings, list):
        data["warnings"] = [text for text in warnings if "이미지를 찾지 못했습니다" not in str(text)]
    return data
'''
GODO_IMAGE2_SCRAPER_NEEDED = ("def extract_product", "def _godo_goods_no", "_godo_re", GODO_IMAGE1_MARKER)
GODO_IMAGE2_SERVICE_PY = r'''
# godo-image2
# Saved Godomall products can still have the long description image marked as
# the representative. Point that flag at the goods photo, once at startup and
# again whenever a product is collected.
import threading as _godo_image_threading
import time as _godo_image_time

_collect_product_before_godo_image2 = collect_product


def _godo_repair_saved_images():
    import app.scraper as _godo_scraper

    fixer = getattr(_godo_scraper, "godo_fix_saved_images", None)
    if fixer is None:
        return False
    fixed = []
    for product in list_full_products():
        try:
            if fixer(product):
                fixed.append(product)
        except Exception:
            continue
    if fixed:
        save_products_batch(fixed)
    return True


def _godo_repair_images_later():
    def run():
        for _ in range(20):
            try:
                if _godo_repair_saved_images():
                    return
            except Exception:
                pass
            _godo_image_time.sleep(0.5)
    _godo_image_threading.Thread(target=run, name="godo-image2", daemon=True).start()


def collect_product(*args, **kwargs):
    product = _collect_product_before_godo_image2(*args, **kwargs)
    try:
        import app.scraper as _godo_scraper

        fixer = getattr(_godo_scraper, "godo_fix_saved_images", None)
        if fixer and fixer(product):
            save_product(product)
    except Exception:
        pass
    return product


_godo_repair_images_later()
'''
GODO_IMAGE2_SERVICE_NEEDED = ("def collect_product", "def save_product", "list_full_products", "save_products_batch", GODO_NAME2_MARKER)
GODO_IMAGE2_CATALOG_PY = r'''
# godo-image2
# Remember only this goods number's own photo. A description image must not
# become the list image later used as the representative.
import re as _godo_image_re

_GODO_LIST_PHOTO_RE = _godo_image_re.compile(r"/goods/(\d+)/image/(main|list|magnify|detail|add\d*)/", _godo_image_re.I)
_godomall_products_before_image2 = _godomall_products


def _godo_list_photo(url, number):
    path = str(url or "").split("#", 1)[0].split("?", 1)[0]
    match = _GODO_LIST_PHOTO_RE.search(path)
    if not match or match.group(1) != str(number or "") or "/thumb/" in path.lower():
        return False
    return True


def _godomall_products(shop_url, category=None, *args, **kwargs):
    data = _godomall_products_before_image2(shop_url, category, *args, **kwargs)
    for item in (data.get("items") if isinstance(data, dict) else None) or []:
        if not isinstance(item, dict):
            continue
        number = str(item.get("product_no") or "")
        image = str(item.get("image") or "")
        if number and _godo_list_photo(image, number):
            _godo_known_images[number] = image
        elif number and image:
            _godo_known_images.pop(number, None)
    return data
'''
GODO_IMAGE2_CATALOG_NEEDED = ("def _godomall_products", "_godo_known_images", GODO_IMAGE1_MARKER)
GODO_IMAGE3_MARKER = "# godo-image3"
GODO_IMAGE3_JS = r"""
/* godo-image3 */
function godoListRank(url, number) {
  const path = String(url || "").split("#")[0].split("?")[0];
  const match = path.match(/\/goods\/(\d+)\/image\/(main|list|magnify)\//i);
  if (!match || String(match[1]) !== String(number) || /\/thumb\//i.test(path)) return null;
  const kind = match[2].toLowerCase();
  if (kind === "main") return 0;
  if (kind === "list") return 1;
  return 2;
}
function godoIsTall(image) {
  const width = Number(image?.width || 0);
  const height = Number(image?.height || 0);
  return width >= 100 && height >= 700 && height >= width * 1.45;
}
function godoIsDescription(url) {
  const text = String(url || "").toLowerCase();
  return text.indexOf("esmplus.com") >= 0 || text.indexOf("/data/editor/") >= 0;
}
function godoApplyRepresentative(product) {
  const images = product?.images;
  const number = godoGoodsNumber(product?.source_url);
  if (!number || !Array.isArray(images) || !images.length) return false;
  const photos = images.filter((image) => godoListRank(image?.source_url, number) !== null);
  photos.sort((a, b) => godoListRank(a.source_url, number) - godoListRank(b.source_url, number));
  let best = photos[0] || null;
  if (!best) {
    const squares = images.filter((image) => image && !godoIsTall(image) && !godoIsDescription(image.source_url) && Number(image.width || 0) >= 150 && Number(image.height || 0) >= 150);
    squares.sort((a, b) => Math.abs(Number(a.width) / Number(a.height) - 1) - Math.abs(Number(b.width) / Number(b.height) - 1));
    const current = images.find((image) => image?.representative) || images[0];
    const currentBad = current && (godoIsTall(current) || godoIsDescription(current.source_url) || /\/image\/detail\//i.test(String(current.source_url || "")));
    if (!squares.length || !currentBad) return false;
    best = squares[0];
  }
  let changed = false;
  const index = images.indexOf(best);
  if (index > 0) {
    images.splice(index, 1);
    images.unshift(best);
    changed = true;
  }
  images.forEach((image) => {
    if (!image || typeof image !== "object") return;
    const rank = godoListRank(image.source_url, number);
    const wantRep = image === best;
    let wantKind = image.kind;
    if (rank !== null || wantRep) wantKind = "gallery";
    else if (image.source_url || godoIsTall(image) || godoIsDescription(image.source_url)) wantKind = "detail";
    if (!!image.representative !== wantRep) {
      image.representative = wantRep;
      changed = true;
    }
    if (wantKind && image.kind !== wantKind) {
      image.kind = wantKind;
      changed = true;
    }
  });
  return changed;
}
"""
GODO_IMAGE3_SCRAPER_PY = r'''
# godo-image3
# The list image is the goods main photo, then the list photo, then magnify.
# Detail-slot files and long description images stay detail images. A saved
# list can still show the description when it is only moderately tall, so move
# the real list photo to the front.
_GODO3_LIST_RANK = {"main": 0, "list": 1, "magnify": 2}
_extract_product_before_godo_image3 = extract_product
_godo_fix_saved_images_before3 = godo_fix_saved_images


def _godo3_list_rank(url, number):
    rank = _godo_photo_rank(url, number)
    if rank is None or rank > 2:
        return None
    return rank


def _godo3_description(url):
    text = _godo_clean_url(url).lower()
    return "esmplus.com" in text or "/data/editor/" in text


def _godo3_tall(image):
    if not isinstance(image, dict):
        return False
    try:
        width = int(image.get("width") or 0)
        height = int(image.get("height") or 0)
    except (TypeError, ValueError):
        return False
    return width >= 100 and height >= 700 and height >= width * 1.45


def _godo3_split(html, number, extra):
    listed = []
    detail = []
    seen = set()

    def add(url):
        url = _godo_clean_url(url)
        if not url or url in seen or _godo_skip_url(url):
            return
        path = url.split("?", 1)[0].lower()
        if "/thumb/" in path and "/goods/" in path and "/image/" in path:
            return
        seen.add(url)
        rank = _godo3_list_rank(url, number)
        if rank is not None:
            listed.append((rank, url))
        else:
            detail.append(url)

    for match in _godo_re.finditer(r"(?:https?:)?//[^\s\"'<>\\]+", html or "", _godo_re.I):
        add(match.group(0))
    for match in _godo_re.finditer(r"(?:src|data-src|data-original)\s*=\s*[\"']([^\"']+)", html or "", _godo_re.I):
        add(match.group(1))
    for url in extra or []:
        add(url)
    listed.sort(key=lambda item: item[0])
    list_urls = []
    for _, url in listed:
        if url not in list_urls:
            list_urls.append(url)
    return list_urls, detail


def _godo3_cached_list(number, page_url):
    try:
        import app.shop_catalog as _godo_catalog
    except Exception:
        return ""
    url = ""
    getter = getattr(_godo_catalog, "_godo3_list_image", None)
    if getter:
        try:
            url = getter(page_url, number) or ""
        except Exception:
            url = ""
    if _godo3_list_rank(url, number) is None:
        known = getattr(_godo_catalog, "_godo_known_images", {}) or {}
        url = str(known.get(str(number)) or "")
    if _godo3_list_rank(url, number) is None:
        return ""
    return _godo_clean_url(url)


def _godo3_pull_list_photo(product, images, number):
    if any(
        isinstance(image, dict) and _godo3_list_rank(_godo_image_url(image), number) == 0
        for image in images
    ):
        return
    current = next((image for image in images if isinstance(image, dict) and image.get("representative")), None)
    current_url = _godo_image_url(current) if current is not None else ""
    if _godo3_list_rank(current_url, number) is not None:
        return
    cached = _godo3_cached_list(number, product.get("source_url") or "")
    if not cached:
        return
    for image in images:
        if isinstance(image, dict) and _godo_image_url(image) == cached:
            return
    images.insert(0, {
        "source_url": cached,
        "kind": "gallery",
        "representative": False,
        "included": True,
    })


def _godo3_same_images(before, images):
    return before is not None and images == before


def godo_fix_saved_images(product):
    before = None
    if isinstance(product, dict) and isinstance(product.get("images"), list):
        before = [dict(image) if isinstance(image, dict) else image for image in product["images"]]
    changed = bool(_godo_fix_saved_images_before3(product))
    if not isinstance(product, dict):
        return changed
    number = _godo_goods_no(product.get("source_url"))
    images = product.get("images")
    if not number or not isinstance(images, list) or not images:
        return False if _godo3_same_images(before, product.get("images")) else changed
    _godo3_pull_list_photo(product, images, number)
    ranked = []
    for image in images:
        if not isinstance(image, dict):
            continue
        rank = _godo3_list_rank(_godo_image_url(image), number)
        if rank is not None:
            ranked.append((rank, image))
    ranked.sort(key=lambda item: item[0])
    best = ranked[0][1] if ranked else None
    if best is None:
        squares = []
        for image in images:
            if not isinstance(image, dict) or _godo3_tall(image) or _godo3_description(_godo_image_url(image)):
                continue
            try:
                width = int(image.get("width") or 0)
                height = int(image.get("height") or 0)
            except (TypeError, ValueError):
                continue
            if width >= 150 and height >= 150:
                squares.append((abs((width / height) - 1), image))
        squares.sort(key=lambda item: item[0])
        current = next((image for image in images if isinstance(image, dict) and image.get("representative")), None)
        current_url = _godo_image_url(current) if current is not None else ""
        current_bad = current is not None and (
            _godo3_tall(current) or _godo3_description(current_url) or _godo_photo_rank(current_url, number) == 3
        )
        if squares and current_bad:
            best = squares[0][1]
    if best is None:
        return False if _godo3_same_images(before, product.get("images")) else changed
    if images[0] is not best:
        images.remove(best)
        images.insert(0, best)
        changed = True
    for image in images:
        if not isinstance(image, dict):
            continue
        url = _godo_image_url(image)
        rank = _godo3_list_rank(url, number)
        want_rep = image is best
        if rank is not None or want_rep:
            want_kind = "gallery"
        elif url or _godo3_tall(image) or _godo3_description(url):
            want_kind = "detail"
        else:
            want_kind = image.get("kind")
        if bool(image.get("representative")) != want_rep:
            image["representative"] = want_rep
            changed = True
        if want_kind and image.get("kind") != want_kind:
            image["kind"] = want_kind
            changed = True
    if _godo3_same_images(before, product.get("images")):
        return False
    return changed


def extract_product(html, page_url=""):
    data = _extract_product_before_godo_image3(html, page_url)
    number = _godo_goods_no(page_url)
    if not isinstance(data, dict) or not number:
        return data
    html_text = html if isinstance(html, str) else ""
    extra = []
    for key in ("detail_images", "gallery_images", "images"):
        for item in data.get(key) or []:
            extra.append(_godo_image_url(item))
    list_urls, detail_urls = _godo3_split(html_text, number, extra)
    if not any(_godo3_list_rank(url, number) == 0 for url in list_urls):
        cached = _godo3_cached_list(number, page_url)
        if cached and cached not in list_urls:
            list_urls.insert(0, cached)
    if not list_urls:
        fallback = [url for url in detail_urls if _godo_photo_rank(url, number) is not None]
        if fallback:
            list_urls = [fallback[0]]
            detail_urls = [url for url in detail_urls if url != fallback[0]]
    if not list_urls:
        return data
    detail_urls = [url for url in detail_urls if url not in list_urls]
    data["gallery_images"] = list_urls
    data["detail_images"] = detail_urls
    images = data.get("images") or []
    if images and isinstance(images[0], dict):
        by_url = {}
        rest = []
        for image in images:
            url = _godo_image_url(image) if isinstance(image, dict) else ""
            if isinstance(image, dict) and url and url not in by_url:
                by_url[url] = image
            else:
                rest.append(image)
        ordered = []
        for url in list_urls + detail_urls:
            image = by_url.pop(url, None)
            if image is None:
                image = {"source_url": url, "kind": "gallery" if url in list_urls else "detail", "representative": False}
            ordered.append(image)
        ordered.extend(by_url.values())
        ordered.extend(item for item in rest if item not in ordered)
        data["images"] = ordered
        godo_fix_saved_images({"source_url": page_url, "images": data["images"]})
    else:
        data["images"] = list_urls + detail_urls
    warnings = data.get("warnings")
    if isinstance(warnings, list):
        data["warnings"] = [text for text in warnings if "이미지를 찾지 못했습니다" not in str(text)]
    return data
'''
GODO_IMAGE3_SCRAPER_NEEDED = ("def extract_product", "def godo_fix_saved_images", "def _godo_photo_rank", GODO_IMAGE2_MARKER)
GODO_IMAGE3_CATALOG_PY = r'''
# godo-image3
# Some list rows keep the detail page or the detail-slot file as item.image.
# The list page's own main/list photo is the list image.
import re as _godo3_re

_GODO3_ABS = _godo3_re.compile(
    r"(?:https?:)?//[^\"'\s<>\\]+/goods/(\d+)/image/(main|list|magnify)/[^\"'\s<>\\]+",
    _godo3_re.I,
)
_GODO3_RANK = {"main": 0, "list": 1, "magnify": 2}
_godo3_main_cache = {}
_godomall_products_before_image3 = _godomall_products


def _godo3_rank(url, number):
    path = str(url or "").split("#", 1)[0].split("?", 1)[0]
    match = _GODO3_ABS.search(path if "://" in path or path.startswith("//") else "//" + path)
    if match is None:
        match = _godo3_re.search(r"/goods/(\d+)/image/(main|list|magnify)/", path, _godo3_re.I)
        if match is None or match.group(1) != str(number or "") or "/thumb/" in path.lower():
            return None
        return _GODO3_RANK.get(match.group(2).lower())
    if match.group(1) != str(number or "") or "/thumb/" in path.lower():
        return None
    return _GODO3_RANK.get(match.group(2).lower())


def _godo3_description(url):
    text = str(url or "").lower()
    return "esmplus.com" in text or "/data/editor/" in text


def _godo3_mains_from_html(html, base=""):
    found = {}

    def consider(url, number, kind):
        url = str(url or "").strip()
        if not url or "/thumb/" in url.lower():
            return
        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("/") and base:
            url = str(base).rstrip("/") + url
        elif not url.startswith("http"):
            return
        rank = _GODO3_RANK.get(str(kind or "").lower(), 9)
        prev = found.get(number)
        if prev is None or rank < prev[0]:
            found[number] = (rank, url)

    for match in _GODO3_ABS.finditer(html or ""):
        consider(match.group(0), match.group(1), match.group(2))
    for match in _godo3_re.finditer(
        r"[\"']([^\"']*?/goods/(\d+)/image/(main|list|magnify)/[^\"']+)",
        html or "",
        _godo3_re.I,
    ):
        consider(match.group(1), match.group(2), match.group(3))
    return {number: url for number, (_, url) in found.items()}


def _godo3_fetch_mains(shop_url, category):
    key = (str(shop_url or ""), str(category or ""))
    if key in _godo3_main_cache:
        return _godo3_main_cache[key]
    base = _base(shop_url)
    cate = str(category or "").strip()
    if cate in {"", "all", "etc"}:
        cate = ""
    found = {}
    try:
        with httpx.Client(headers=PAGE_HEADERS, follow_redirects=True, timeout=30.0) as client:
            for page in range(1, 9):
                params = {"page": page}
                if cate:
                    params["cateCd"] = cate
                response = client.get(f"{base}/goods/goods_list.php", params=params)
                if response.status_code >= 400:
                    break
                html = response.text or ""
                before = len(found)
                found.update(_godo3_mains_from_html(html, base))
                if "goodsNo=" not in html or len(found) == before:
                    break
    except Exception:
        found = found or {}
    _godo3_main_cache[key] = found
    return found


def _godo3_mains_for(shop_url, category, items):
    wanted = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        number = str(item.get("product_no") or "")
        if number and _godo3_rank(item.get("image"), number) != 0:
            wanted.add(number)
    if not wanted:
        return {}
    cates = []
    chosen = str(category or "").strip()
    if chosen and chosen not in {"all", "etc"}:
        cates = [chosen]
    getter = globals().get("_godo_all_cates")
    if getter and (not cates or len(wanted) > 0):
        try:
            more = list(getter(shop_url) or [])
        except Exception:
            more = []
        for cate in more:
            if cate not in cates:
                cates.append(cate)
            if len(cates) >= 12:
                break
    if not cates:
        cates = [chosen]
    found = {}
    for cate in cates:
        if not wanted:
            break
        for number, url in _godo3_fetch_mains(shop_url, cate).items():
            found.setdefault(number, url)
            wanted.discard(number)
    return found


def _godo3_apply_items(items, mains):
    for item in items or []:
        if not isinstance(item, dict):
            continue
        number = str(item.get("product_no") or "")
        if not number:
            continue
        image = str(item.get("image") or "")
        better = str((mains or {}).get(number) or "")
        rank = _godo3_rank(image, number)
        better_rank = _godo3_rank(better, number)
        if better and better_rank is not None and (rank is None or better_rank < rank):
            item["image"] = better
            image = better
            rank = better_rank
        if rank is not None:
            _godo_known_images[number] = image
        elif _godo3_description(image):
            _godo_known_images.pop(number, None)
            item["image"] = ""


def _godo3_list_image(page_url, number):
    number = str(number or "")
    known = str(_godo_known_images.get(number) or "")
    if _godo3_rank(known, number) == 0:
        return known
    found = _godo3_mains_for(page_url, "", [{"product_no": number, "image": known}])
    url = str(found.get(number) or "")
    if _godo3_rank(url, number) is None:
        url = known if _godo3_rank(known, number) is not None else ""
    if url:
        _godo_known_images[number] = url
    return url


def _godomall_products(shop_url, category=None, *args, **kwargs):
    data = _godomall_products_before_image3(shop_url, category, *args, **kwargs)
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        return data
    mains = {}
    if any(isinstance(item, dict) and _godo3_rank(item.get("image"), item.get("product_no")) != 0 for item in items):
        try:
            mains = _godo3_mains_for(shop_url, category, items)
        except Exception:
            mains = {}
    _godo3_apply_items(items, mains)
    return data
'''
GODO_IMAGE3_CATALOG_NEEDED = ("def _godomall_products", "_godo_known_images", "def _base", "httpx", GODO_IMAGE2_MARKER)
GODO_IMAGE4_MARKER = "# godo-image4"
GODO_IMAGE4_JS = r"""
/* godo-image4 */
function godoListRank(url, number) {
  const path = String(url || "").split("#")[0].split("?")[0];
  const match = path.match(/\/goods\/(\d+)\/image\/(main|list)\//i);
  if (!match || String(match[1]) !== String(number) || /\/thumb\//i.test(path)) return null;
  return match[2].toLowerCase() === "main" ? 0 : 1;
}
function godoApplyRepresentative(product) {
  const images = product?.images;
  const number = godoGoodsNumber(product?.source_url);
  if (!number || !Array.isArray(images) || !images.length) return false;
  const photos = images.filter((image) => image && godoListRank(image.source_url, number) !== null);
  photos.sort((a, b) => godoListRank(a.source_url, number) - godoListRank(b.source_url, number));
  const best = photos[0] || null;
  if (!best) return false;
  let changed = false;
  const index = images.indexOf(best);
  if (index > 0) {
    images.splice(index, 1);
    images.unshift(best);
    changed = true;
  }
  images.forEach((image) => {
    if (!image || typeof image !== "object") return;
    const rank = godoListRank(image.source_url, number);
    const detailPage = /\/image\/(?:detail|magnify|add\d*)\//i.test(String(image.source_url || "")) || godoIsDescription(image.source_url);
    const wantRep = image === best;
    let wantKind = image.kind;
    if (rank !== null) wantKind = "gallery";
    else if (image.source_url || godoIsTall(image) || detailPage) wantKind = "detail";
    if (!!image.representative !== wantRep) {
      image.representative = wantRep;
      changed = true;
    }
    if (wantKind && image.kind !== wantKind) {
      image.kind = wantKind;
      changed = true;
    }
  });
  return changed;
}
"""
GODO_IMAGE4_SCRAPER_PY = r'''
# godo-image4
# The list image is only the list page's /image/main/ photo, then /image/list/.
# Magnify, the detail slot, add images, and the long description are detail
# images. A saved representative that is already the detail-page zoom still
# needs the list-page main pulled in front of it.
_extract_product_before_godo_image4 = extract_product
_godo_fix_saved_images_before4 = godo_fix_saved_images


def _godo4_list_rank(url, number):
    rank = _godo_photo_rank(url, number)
    if rank is None or rank > 1:
        return None
    return rank


def _godo4_title(html):
    text = html if isinstance(html, str) else ""
    for pattern in (
        r"<meta[^>]+property=[\"']og:title[\"'][^>]+content=[\"']([^\"']+)",
        r"<meta[^>]+content=[\"']([^\"']+)[\"'][^>]+property=[\"']og:title[\"']",
        r"<title>([^<]+)</title>",
    ):
        match = _godo_re.search(pattern, text, _godo_re.I)
        if match:
            return match.group(1).strip()
    return ""


def _godo4_lookup(page_url, number, name):
    try:
        import app.shop_catalog as _godo_catalog
    except Exception:
        return ""
    getter = getattr(_godo_catalog, "_godo4_list_image", None)
    if not getter:
        return ""
    try:
        url = getter(page_url, number, name) or ""
    except TypeError:
        try:
            url = getter(page_url, number) or ""
        except Exception:
            return ""
    except Exception:
        return ""
    url = _godo_clean_url(url)
    if not url.startswith("http") or _godo4_list_rank(url, number) is None:
        return ""
    return url


def _godo4_same(before, images):
    return before is not None and images == before


def godo_fix_saved_images(product):
    before = None
    if isinstance(product, dict) and isinstance(product.get("images"), list):
        before = [dict(image) if isinstance(image, dict) else image for image in product["images"]]
    changed = bool(_godo_fix_saved_images_before4(product))
    if not isinstance(product, dict):
        return changed
    number = _godo_goods_no(product.get("source_url"))
    images = product.get("images")
    if not number or not isinstance(images, list) or not images:
        return False if _godo4_same(before, product.get("images")) else changed
    has_main = any(
        isinstance(image, dict) and _godo4_list_rank(_godo_image_url(image), number) == 0
        for image in images
    )
    if not has_main:
        cached = _godo4_lookup(product.get("source_url") or "", number, product.get("name") or "")
        if cached and not any(isinstance(image, dict) and _godo_image_url(image) == cached for image in images):
            images.insert(0, {
                "source_url": cached,
                "kind": "gallery",
                "representative": False,
                "included": True,
            })
            changed = True
    ranked = []
    for image in images:
        if not isinstance(image, dict):
            continue
        rank = _godo4_list_rank(_godo_image_url(image), number)
        if rank is not None:
            ranked.append((rank, image))
    ranked.sort(key=lambda item: item[0])
    best = ranked[0][1] if ranked else None
    if best is None:
        for image in images:
            if isinstance(image, dict) and _godo_photo_rank(_godo_image_url(image), number) == 2:
                best = image
                break
    if best is None:
        for image in images:
            if not isinstance(image, dict):
                continue
            if image.get("representative"):
                image["representative"] = False
                changed = True
            if _godo_image_url(image) and image.get("kind") != "detail":
                image["kind"] = "detail"
                changed = True
        if _godo4_same(before, product.get("images")):
            return False
        return changed
    if images[0] is not best:
        images.remove(best)
        images.insert(0, best)
        changed = True
    for image in images:
        if not isinstance(image, dict):
            continue
        url = _godo_image_url(image)
        rank = _godo4_list_rank(url, number)
        want_rep = image is best
        if rank is not None or want_rep:
            want_kind = "gallery"
        elif url:
            want_kind = "detail"
        else:
            want_kind = image.get("kind")
        if bool(image.get("representative")) != want_rep:
            image["representative"] = want_rep
            changed = True
        if want_kind and image.get("kind") != want_kind:
            image["kind"] = want_kind
            changed = True
    if _godo4_same(before, product.get("images")):
        return False
    return changed


def extract_product(html, page_url=""):
    data = _extract_product_before_godo_image4(html, page_url)
    number = _godo_goods_no(page_url)
    if not isinstance(data, dict) or not number:
        return data
    html_text = html if isinstance(html, str) else ""
    name = str(data.get("name") or "").strip() or _godo4_title(html_text)
    urls = []

    def add(url):
        url = _godo_clean_url(url)
        if url and url not in urls and not _godo_skip_url(url):
            urls.append(url)

    for key in ("gallery_images", "detail_images", "images"):
        for item in data.get(key) or []:
            add(_godo_image_url(item))
    for match in _godo_re.finditer(r"(?:https?:)?//[^\s\"'<>\\]+", html_text, _godo_re.I):
        add(match.group(0))
    gallery = [url for url in urls if _godo4_list_rank(url, number) is not None]
    if not any(_godo4_list_rank(url, number) == 0 for url in gallery):
        found = _godo4_lookup(page_url, number, name)
        if found:
            gallery = [found] + [url for url in gallery if url != found]
    gallery.sort(key=lambda url: _godo4_list_rank(url, number) or 0)
    if not gallery:
        magnify = [url for url in urls if _godo_photo_rank(url, number) == 2]
        if magnify:
            gallery = [magnify[0]]
    detail = []
    for url in urls:
        if url in gallery:
            continue
        rank = _godo_photo_rank(url, number)
        low = url.lower()
        if rank is not None or "esmplus.com" in low or "/data/editor/" in low:
            detail.append(url)
    data["gallery_images"] = gallery
    data["detail_images"] = detail
    images = data.get("images") or []
    by_url = {}
    rest = []
    if images and isinstance(images[0], dict):
        for image in images:
            url = _godo_image_url(image) if isinstance(image, dict) else ""
            if isinstance(image, dict) and url and url not in by_url:
                by_url[url] = image
            else:
                rest.append(image)
    ordered = []
    gallery_set = set(gallery)
    for url in gallery + detail:
        image = by_url.pop(url, None)
        if image is None:
            image = {
                "source_url": url,
                "kind": "gallery" if url in gallery_set else "detail",
                "representative": False,
                "included": True,
            }
        ordered.append(image)
    ordered.extend(by_url.values())
    ordered.extend(item for item in rest if item not in ordered)
    if ordered:
        data["images"] = ordered
        godo_fix_saved_images({"source_url": page_url, "name": name, "images": data["images"]})
    return data
'''
GODO_IMAGE4_SCRAPER_NEEDED = ("def extract_product", "def godo_fix_saved_images", "def _godo_photo_rank", "def _godo_goods_no", GODO_IMAGE3_MARKER)
GODO_IMAGE4_CATALOG_PY = r'''
# godo-image4
# A list image is the list page's /image/main/ or /image/list/ file. Magnify and
# the detail slot are the detail page, so they are replaced when the list page
# has a main photo. Follow goods_list.php page= links (page index, not pageNum)
# and keep an unfinished crawl out of the cache. A missed goods number is
# looked up by name on goods_search.php, using the absolute CDN url.
import re as _godo4_re
from urllib.parse import urlparse as _godo4_urlparse

_GODO4_ABS = _godo4_re.compile(
    r"(?:https?:)?//[^\"'\s<>\\]+/goods/(\d+)/image/(main|list)/[^\"'\s<>\\]+",
    _godo4_re.I,
)
_GODO4_RANK = {"main": 0, "list": 1}
_godo4_main_cache = {}
_godomall_products_before_image4 = _godomall_products


def _godo4_host(url):
    host = _godo4_urlparse(str(url or "")).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _godo4_keep(url, base=""):
    text = str(url or "").strip()
    if text.startswith("//"):
        text = "https:" + text
    if not text.startswith("http") or "/thumb/" in text.lower():
        return ""
    if base and _godo4_host(text) == _godo4_host(base):
        path = _godo4_urlparse(text).path.lower()
        if "/goods/" in path and "/image/" in path:
            return ""
    return text


def _godo4_rank(url, number):
    path = str(url or "").split("#", 1)[0].split("?", 1)[0]
    match = _godo4_re.search(r"/goods/(\d+)/image/(main|list)/", path, _godo4_re.I)
    if match is None or match.group(1) != str(number or "") or "/thumb/" in path.lower():
        return None
    return _GODO4_RANK.get(match.group(2).lower())


def _godo4_mains_from_html(html, base=""):
    found = {}

    def consider(url, number, kind):
        url = _godo4_keep(url, base)
        if not url:
            return
        rank = _GODO4_RANK.get(str(kind or "").lower())
        if rank is None:
            return
        prev = found.get(number)
        if prev is None or rank < prev[0] or (rank == prev[0] and url.startswith("https") and not str(prev[1]).startswith("https")):
            found[number] = (rank, url)

    for match in _GODO4_ABS.finditer(html or ""):
        consider(match.group(0), match.group(1), match.group(2))
    for match in _godo4_re.finditer(
        r"[\"']([^\"']*?/goods/(\d+)/image/(main|list)/[^\"']+)",
        html or "",
        _godo4_re.I,
    ):
        consider(match.group(1), match.group(2), match.group(3))
    return {number: url for number, (_, url) in found.items()}


def _godo4_linked_pages(html):
    text = (html or "").replace("&amp;", "&").replace("&#38;", "&")
    pages = set()
    for match in _godo4_re.finditer(r"goods_list\.php\?[^\"'\s>]*", text, _godo4_re.I):
        found = _godo4_re.search(r"(?:^|[?&])page=(\d+)", match.group(0), _godo4_re.I)
        if not found:
            continue
        try:
            page = int(found.group(1))
        except ValueError:
            continue
        if 1 <= page <= 20:
            pages.add(page)
    return pages


def _godo4_fetch_mains(shop_url, category):
    key = (str(shop_url or ""), str(category or ""))
    if key in _godo4_main_cache:
        return _godo4_main_cache[key]
    base = _base(shop_url)
    cate = str(category or "").strip()
    if cate in {"", "all", "etc"}:
        cate = ""
    found = {}
    seen = set()
    pending = [1]
    complete = True
    try:
        with httpx.Client(headers=PAGE_HEADERS, follow_redirects=True, timeout=30.0) as client:
            while pending and len(seen) < 20:
                page = pending.pop(0)
                if page in seen or page < 1 or page > 20:
                    continue
                seen.add(page)
                params = {"page": page}
                if cate:
                    params["cateCd"] = cate
                response = client.get(f"{base}/goods/goods_list.php", params=params)
                if getattr(response, "status_code", 200) >= 400:
                    complete = False
                    break
                html = response.text or ""
                added = _godo4_mains_from_html(html, base)
                if "잘못된 접근" in html and not added:
                    complete = False
                    break
                found.update(added)
                for linked in sorted(_godo4_linked_pages(html)):
                    if linked not in seen and linked not in pending:
                        pending.append(linked)
            if pending:
                complete = False
    except Exception:
        complete = False
    if complete:
        _godo4_main_cache[key] = found
    return found


def _godo4_mains_for(shop_url, category, items):
    wanted = set()
    for item in items or []:
        if not isinstance(item, dict):
            continue
        number = str(item.get("product_no") or "")
        if number and _godo4_rank(item.get("image"), number) is None:
            wanted.add(number)
    if not wanted:
        return {}
    cates = []
    getter = globals().get("_godo_all_cates")
    if getter:
        try:
            more = list(getter(shop_url) or [])
        except Exception:
            more = []
        for cate in more:
            if cate not in cates:
                cates.append(cate)
            if len(cates) >= 12:
                break
    chosen = str(category or "").strip()
    if chosen and chosen not in {"all", "etc"} and chosen not in cates:
        cates.append(chosen)
    if not cates:
        cates = [chosen]
    found = {}
    pending = set(wanted)
    for cate in cates:
        if not pending:
            break
        for number, url in _godo4_fetch_mains(shop_url, cate).items():
            if number not in wanted:
                continue
            prev = found.get(number)
            if prev is None or (_godo4_rank(url, number) or 9) < (_godo4_rank(prev, number) or 9):
                found[number] = url
            if _godo4_rank(found.get(number), number) == 0:
                pending.discard(number)
    return found


def _godo4_search_main(shop_url, number, name):
    name = str(name or "").strip()
    number = str(number or "")
    if not name or not number:
        return ""
    base = _base(shop_url)
    try:
        with httpx.Client(headers=PAGE_HEADERS, follow_redirects=True, timeout=30.0) as client:
            response = client.get(f"{base}/goods/goods_search.php", params={"keyword": name})
            if getattr(response, "status_code", 200) >= 400:
                return ""
            found = _godo4_mains_from_html(response.text or "", base)
    except Exception:
        return ""
    return str(found.get(number) or "")


def _godo4_apply_items(items, mains):
    for item in items or []:
        if not isinstance(item, dict):
            continue
        number = str(item.get("product_no") or "")
        if not number:
            continue
        image = str(item.get("image") or "")
        better = str((mains or {}).get(number) or "")
        rank = _godo4_rank(image, number)
        better_rank = _godo4_rank(better, number)
        if better and better_rank is not None and (rank is None or better_rank < rank):
            item["image"] = better
            image = better
            rank = better_rank
        if rank is not None:
            _godo_known_images[number] = image


def _godo4_list_image(page_url, number, name=""):
    number = str(number or "")
    known = str(_godo_known_images.get(number) or "")
    if _godo4_rank(known, number) == 0 and _godo4_keep(known, _base(page_url)):
        return known
    found = _godo4_mains_for(page_url, "", [{"product_no": number, "image": "", "name": name}])
    url = str(found.get(number) or "")
    if _godo4_rank(url, number) is None:
        url = _godo4_search_main(page_url, number, name)
    if _godo4_rank(url, number) is None:
        url = known if _godo4_rank(known, number) is not None and _godo4_keep(known, _base(page_url)) else ""
    if url:
        _godo_known_images[number] = url
    return url


def _godomall_products(shop_url, category=None, *args, **kwargs):
    data = _godomall_products_before_image4(shop_url, category, *args, **kwargs)
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        return data
    mains = {}
    if any(isinstance(item, dict) and _godo4_rank(item.get("image"), item.get("product_no")) is None for item in items):
        try:
            mains = _godo4_mains_for(shop_url, category, items)
        except Exception:
            mains = {}
    _godo4_apply_items(items, mains)
    for item in items:
        if not isinstance(item, dict):
            continue
        number = str(item.get("product_no") or "")
        if not number or _godo4_rank(item.get("image"), number) is not None:
            continue
        found = _godo4_search_main(shop_url, number, item.get("name") or "")
        if _godo4_rank(found, number) is not None:
            item["image"] = found
            _godo_known_images[number] = found
    return data
'''
GODO_IMAGE4_CATALOG_NEEDED = ("def _godomall_products", "_godo_known_images", "def _base", "httpx", GODO_IMAGE3_MARKER)
TEXT_DECODE1_MARKER = "# subprocess-text1"
TEXT_DECODE1_CHROME_PY = r"""
# subprocess-text1
# kill_profile_chrome reads PowerShell output with text=True, which decodes as
# cp949 on Korean Windows. Chrome command lines can hold UTF-8 bytes, and the
# reader threads then print UnicodeDecodeError tracebacks to the console.
import subprocess as _text_subprocess

if not getattr(_text_subprocess.Popen, "_modumodu_text_errors", False):
    _text_popen_init = _text_subprocess.Popen.__init__

    def _text_popen_init_replace(self, *args, **kwargs):
        if kwargs.get("errors") is None and (kwargs.get("text") or kwargs.get("universal_newlines") or kwargs.get("encoding")):
            kwargs["errors"] = "replace"
        _text_popen_init(self, *args, **kwargs)

    _text_subprocess.Popen.__init__ = _text_popen_init_replace
    _text_subprocess.Popen._modumodu_text_errors = True
"""
TEXT_DECODE1_CHROME_NEEDED = ("def kill_profile_chrome", "subprocess")
GODO_OPEN1_MARKER = "# godo-open1"
GODO_OPEN1_SERVICE_PY = r"""
# godo-open1
# open_wholesale_product only opened the URL, so Godomall shops such as Murray
# showed their login page. Godomall forms use loginId/loginPwd, which the
# cafe24 login filler does not know, so log in here with the saved account.
_open_wholesale_product_before_godo = open_wholesale_product
_GODO_LOGIN_ID = ("#loginId", "input[name='loginId']", "#member_id", "input[name='member_id']", "input[name='userid']")
_GODO_LOGIN_PW = ("#loginPwd", "input[name='loginPwd']", "#member_passwd", "input[name='member_passwd']", "input[type='password']")
_GODO_LOGIN_SUBMIT = ("#formLogin button[type='submit']", "#formLogin input[type='submit']", "button.l-login", "a[onclick*='MemberAction.login']")


def _godo_first(page, selectors):
    for selector in selectors:
        try:
            found = page.query_selector(selector)
        except Exception:
            found = None
        if found is not None:
            return found
    return None


def _godo_open_base(supplier, url):
    import app.shop_catalog as _godo_catalog

    finder = getattr(_godo_catalog, "_godo_site_base", None)
    kind = str(supplier.get("type") or "").strip().lower()
    if kind in {"cafe24", "imweb", "ownerclan"}:
        return ""
    for source in (supplier.get("url"), url):
        base = finder(source) if finder else ""
        if base:
            return base
    if kind == "godomall":
        return _godo_catalog._base(str(supplier.get("url") or url))
    return ""


def _godo_on_login(page):
    try:
        return "/member/login" in (page.url or "")
    except Exception:
        return False


def _godo_open_logged_in(url, base, login_id, password):
    from playwright.sync_api import sync_playwright
    from app.chrome_app import connect_cdp, existing_context

    playwright = sync_playwright().start()
    try:
        browser = connect_cdp(playwright)
        context = existing_context(browser)
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=25000)
        if _godo_on_login(page) or page.query_selector("a[href*='logout']") is None:
            if not _godo_on_login(page):
                page.goto(base + "/member/login.php", wait_until="domcontentloaded", timeout=25000)
            user_box = _godo_first(page, _GODO_LOGIN_ID) if _godo_on_login(page) else None
            pass_box = _godo_first(page, _GODO_LOGIN_PW) if user_box is not None else None
            if pass_box is not None:
                user_box.fill(login_id)
                pass_box.fill(password)
                pass_box.press("Enter")
                left = "() => !location.pathname.includes('/member/login')"
                try:
                    page.wait_for_function(left, timeout=6000)
                except Exception:
                    button = _godo_first(page, _GODO_LOGIN_SUBMIT)
                    if button is not None and _godo_on_login(page):
                        try:
                            button.click(force=True, timeout=5000)
                            page.wait_for_function(left, timeout=10000)
                        except Exception:
                            pass
                page.goto(url, wait_until="domcontentloaded", timeout=25000)
        try:
            page.bring_to_front()
        except Exception:
            pass
        if _godo_on_login(page):
            return False
        return True if page.query_selector("a[href*='logout']") is not None else None
    finally:
        playwright.stop()


def open_wholesale_product(wholesaler_id, url, *args, **kwargs):
    supplier = get_wholesaler(wholesaler_id, include_secret=True) or {}
    target = str(url or "").strip()
    base = _godo_open_base(supplier, target) if supplier and target.startswith("http") else ""
    if not base:
        return _open_wholesale_product_before_godo(wholesaler_id, url, *args, **kwargs)
    name = str(supplier.get("name") or "공급처")
    login_id = str(supplier.get("login_id") or "").strip()
    password = str(supplier.get("login_password") or "")
    if not login_id or not password:
        result = _open_wholesale_product_before_godo(wholesaler_id, url, *args, **kwargs)
        if isinstance(result, dict):
            result["message"] = f"{name} 아이디와 비밀번호가 저장돼 있지 않아 로그인 없이 열었습니다. 공급처관리에서 저장해 주세요."
        return result
    try:
        logged_in = _godo_open_logged_in(target, base, login_id, password)
    except Exception:
        return _open_wholesale_product_before_godo(wholesaler_id, url, *args, **kwargs)
    if logged_in:
        return {"ok": True, "message": f"{name}에 로그인한 Chrome에서 상품을 열었습니다."}
    if logged_in is None:
        return {"ok": True, "message": f"{name} 상품을 열었지만 로그인이 됐는지 확인하지 못했습니다. 공급처관리에서 아이디와 비밀번호를 확인해 주세요."}
    return {"ok": True, "message": f"{name} 로그인에 실패했습니다. 공급처관리에서 아이디와 비밀번호를 확인해 주세요."}
"""
GODO_OPEN1_SERVICE_NEEDED = ("def open_wholesale_product", "def get_wholesaler", GODO_NAME2_MARKER)
GODO_SITE2_SERVICE_NEEDED = ("def list_wholesale_catalog", "def import_wholesale_catalog", GODO_NAME2_MARKER)
FIX_STATUS_FILE = "modumodu-fixes.json"


def write_fix_status(root: Path) -> bool:
    catalog = root / "app" / "shop_catalog.py"
    service = root / "app" / "service.py"
    static = root / "app" / "static"
    if not catalog.is_file() or not service.is_file() or not (root / "app" / "scraper.py").is_file() or not static.is_dir():
        return False
    catalog_needed = ("def _godomall_products", "def _godo_goods_from_href", "def _base", "PAGE_HEADERS", "BeautifulSoup", "httpx")
    checks = {
        "shop_catalog.py": (
            (catalog, GODO_NAME_MARKER, catalog_needed),
            (catalog, GODO_NAME2_MARKER, GODO_NAME2_CATALOG_NEEDED),
            (catalog, GODO_SITE1_MARKER, GODO_SITE1_CATALOG_NEEDED),
            (catalog, GODO_IMAGE1_MARKER, GODO_IMAGE1_CATALOG_NEEDED),
            (catalog, GODO_IMAGE2_MARKER, GODO_IMAGE2_CATALOG_NEEDED),
            (catalog, GODO_IMAGE3_MARKER, GODO_IMAGE3_CATALOG_NEEDED),
            (catalog, GODO_IMAGE4_MARKER, GODO_IMAGE4_CATALOG_NEEDED),
        ),
        "scraper.py": (
            (root / "app" / "scraper.py", GODO_IMAGE1_MARKER, GODO_IMAGE1_SCRAPER_NEEDED),
            (root / "app" / "scraper.py", GODO_IMAGE2_MARKER, GODO_IMAGE2_SCRAPER_NEEDED),
            (root / "app" / "scraper.py", GODO_IMAGE3_MARKER, GODO_IMAGE3_SCRAPER_NEEDED),
            (root / "app" / "scraper.py", GODO_IMAGE4_MARKER, GODO_IMAGE4_SCRAPER_NEEDED),
        ),
        "service.py": (
            (service, GODO_NAME2_MARKER, GODO_NAME2_SERVICE_NEEDED),
            (service, GODO_SITE2_MARKER, GODO_SITE2_SERVICE_NEEDED),
            (service, GODO_OPEN1_MARKER, GODO_OPEN1_SERVICE_NEEDED),
            (service, GODO_LOGIN2_MARKER, GODO_LOGIN2_SERVICE_NEEDED),
            (service, GODO_IMAGE2_MARKER, GODO_IMAGE2_SERVICE_NEEDED),
            (service, NAVER_TAG_MARKER, NAVER_TAG_SERVICE_NEEDED),
        ),
    }
    files = {}
    for label, rows in checks.items():
        for path, marker, needed in rows:
            text = read_text(path)[0]
            state = "ok" if marker in text else [name for name in needed if name not in text] or ["not added"]
            files.setdefault(label, {})[marker.lstrip("# ")] = state
    payload = json.dumps({"version": SCREEN_VERSION, "files": files}, ensure_ascii=False, indent=1) + "\n"
    target = static / FIX_STATUS_FILE
    if target.is_file() and target.read_text(encoding="utf-8") == payload:
        return False
    target.write_text(payload, encoding="utf-8")
    return True


GODO_NAME2_CATALOG_NEEDED = ("def _godomall_products", "def _godo_cate_from_href", GODO_NAME_MARKER)
GODO_NAME2_SERVICE_NEEDED = ("def import_wholesale_catalog", "list_full_products", "save_products_batch")
NAVER_TAG_MARKER = "# naver-tag1"
NAVER_TAG_JS = r"""
/* naver-tag1 */
let naverTagLoad = 0;

function naverTagQuery() {
  const named = typeof categoryLeafName === "function"
    ? categoryLeafName(current?.category_name || current?.source_category || "")
    : "";
  if (named && named !== "카테고리") return named;
  return String(current?.category_keyword || "").trim();
}

function ensureNaverTagPanel() {
  const form = document.getElementById("tagForm");
  if (!form || document.getElementById("naverSearchTags")) return;
  const actions = form.querySelector(".dialog-actions");
  const layout = document.createElement("div");
  layout.className = "tag-layout";
  const main = document.createElement("div");
  main.className = "tag-main";
  const header = form.querySelector("header");
  [...form.children].forEach((child) => {
    if (child === header || child === actions) return;
    main.appendChild(child);
  });
  const aside = document.createElement("aside");
  aside.className = "naver-search-tags";
  aside.innerHTML = "<h3>검색 태그</h3><p id=\"naverSearchTagCount\" class=\"hint\"></p><p id=\"naverSearchTagPage\" class=\"hint\">1–3페이지</p><div id=\"naverSearchTags\" class=\"naver-search-tag-list\"></div>";
  layout.append(main, aside);
  if (actions) form.insertBefore(layout, actions);
  else form.appendChild(layout);
}

function ensureNaverTagButton() {
  if (document.getElementById("tagFillDictionary")) return;
  const ai = document.getElementById("tagFillAi");
  if (!ai || !ai.parentElement) return;
  const button = document.createElement("button");
  button.type = "button";
  button.id = "tagFillDictionary";
  button.textContent = "태그넣기";
  button.addEventListener("click", () => {
    fillTagsFromDictionary().catch((error) => toast(error.message, true));
  });
  ai.parentElement.insertBefore(button, ai);
}

function renderNaverSearchTags(tags) {
  const box = document.getElementById("naverSearchTags");
  if (!box) return;
  box.innerHTML = "";
  (tags || []).forEach((tag) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = tag;
    button.addEventListener("click", () => addDraftTag(tag));
    box.appendChild(button);
  });
}

async function loadNaverSearchTags() {
  ensureNaverTagPanel();
  const token = ++naverTagLoad;
  const query = naverTagQuery();
  const count = document.getElementById("naverSearchTagCount");
  const page = document.getElementById("naverSearchTagPage");
  if (page) page.textContent = "1–3페이지";
  if (!query) {
    if (count) count.textContent = "카테고리의 마지막 분류가 없습니다.";
    renderNaverSearchTags([]);
    return;
  }
  if (count) count.textContent = query + " 검색 태그를 가져오는 중입니다.";
  renderNaverSearchTags([]);
  try {
    const data = await api("/api/tags/naver-search?q=" + encodeURIComponent(query), { method: "GET", quiet: true });
    if (token !== naverTagLoad) return;
    const tags = Array.isArray(data.tags) ? data.tags : [];
    if (count) count.textContent = query + " 검색 태그 " + tags.length + "개";
    renderNaverSearchTags(tags);
  } catch (error) {
    if (token !== naverTagLoad) return;
    if (count) count.textContent = error.message || "검색 태그를 가져오지 못했습니다.";
  }
}

async function fillTagsFromDictionary() {
  if (!current) return toast("먼저 상품을 선택해 주세요.", true);
  if (typeof masterEditBlocked === "function" && masterEditBlocked()) return;
  const query = naverTagQuery();
  if (!query) return toast("카테고리의 마지막 분류를 지정해 주세요.", true);
  const button = document.getElementById("tagFillDictionary");
  const previous = button ? button.textContent : "";
  if (button) {
    button.disabled = true;
    button.textContent = "가져오는 중";
  }
  try {
    const data = await api("/api/tags/naver-dictionary?q=" + encodeURIComponent(query), { method: "GET", quiet: true });
    const tags = (Array.isArray(data.tags) ? data.tags : []).map((item) => {
      if (typeof item === "string") return item.trim();
      return String(item?.text || "").trim();
    }).filter(Boolean);
    if (!tags.length) return toast("네이버 태그사전에 태그가 없습니다.", true);
    const seen = [];
    tags.forEach((tag) => {
      if (!seen.includes(tag)) seen.push(tag);
    });
    draftTags = seen.slice(0, 10);
    renderTagChips();
    toast("네이버 태그사전을 넣었습니다.");
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = previous || "태그넣기";
    }
  }
}

function bootNaverTags() {
  ensureNaverTagPanel();
  ensureNaverTagButton();
  if (typeof openTagEditor === "function" && !openTagEditor._naverTag1) {
    const openTagEditorBefore = openTagEditor;
    const wrapped = function () {
      ensureNaverTagPanel();
      ensureNaverTagButton();
      const result = openTagEditorBefore.apply(this, arguments);
      loadNaverSearchTags();
      return result;
    };
    wrapped._naverTag1 = true;
    openTagEditor = wrapped;
  }
}
if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bootNaverTags);
else bootNaverTags();
"""
NAVER_TAG_CSS = r"""
/* naver-tag1 */
#tagDialog { width: min(980px, calc(100vw - 24px)); }
.tag-layout { display: flex; gap: 16px; align-items: stretch; }
.tag-main { flex: 1 1 auto; min-width: 0; }
.naver-search-tags {
  flex: 0 0 280px;
  width: 280px;
  border: 1px solid var(--line);
  background: var(--surface);
  padding: 10px;
  display: flex;
  flex-direction: column;
  min-height: 280px;
  max-height: min(560px, calc(100vh - 160px));
}
.naver-search-tags h3 { margin: 0 0 4px; font-size: 14px; }
.naver-search-tags .hint { margin: 0 0 4px; }
.naver-search-tag-list {
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 6px;
}
.naver-search-tag-list button {
  display: block;
  width: 100%;
  text-align: left;
  background: var(--field);
  border: 1px solid var(--field-border);
  padding: 6px 8px;
}
@media (max-width: 800px) {
  .tag-layout { flex-direction: column; }
  .naver-search-tags { width: auto; flex-basis: auto; }
}
"""
NAME_FORBID_JS = r"""
/* name-keyword-tags1 */
let nameForbidCache = [];

/* forbid-pure-start */
function stripForbiddenText(value, words) {
  let text = String(value || "");
  const source = Array.isArray(words) ? words : (typeof nameForbidWords === "function" ? nameForbidWords() : []);
  const list = source
    .map((word) => String(word || "").replace(/\s+/g, " ").trim())
    .filter((word) => word.length >= 2);
  list.sort((a, b) => b.length - a.length);
  list.forEach((word) => {
    if (text.indexOf(word) >= 0) text = text.split(word).join(" ");
  });
  return text.replace(/\s+/g, " ").trim();
}
function stripForbiddenTags(tags, words) {
  const out = [];
  const list = Array.isArray(tags) ? tags : [];
  for (let index = 0; index < list.length; index += 1) {
    const stripped = stripForbiddenText(list[index], words);
    const tag = typeof cleanTag === "function"
      ? cleanTag(stripped)
      : String(stripped || "").replace(/\s+/g, "").replace(/[^0-9A-Za-z가-힣]/g, "").slice(0, 10);
    if (tag && out.indexOf(tag) < 0) out.push(tag);
    if (out.length >= 10) break;
  }
  return out;
}
/* forbid-pure-end */

function nameForbidWords() {
  return nameForbidCache.slice();
}
function scrubProductRecord(product) {
  if (!product || typeof product !== "object" || !product.id) return product;
  const words = nameForbidWords();
  if (!words.length) return product;
  if (typeof product.name === "string") product.name = stripForbiddenText(product.name, words);
  if (Array.isArray(product.tags)) product.tags = stripForbiddenTags(product.tags, words);
  return product;
}
function scrubForbidPayload(data) {
  if (Array.isArray(data)) {
    data.forEach(scrubProductRecord);
    return data;
  }
  if (data && typeof data === "object") {
    scrubProductRecord(data);
    if (Array.isArray(data.items)) data.items.forEach(scrubProductRecord);
    if (data.product) scrubProductRecord(data.product);
  }
  return data;
}
function rememberForbidWords(data) {
  const raw = data && Array.isArray(data.keywords) ? data.keywords : [];
  nameForbidCache = typeof uniqueNameKeywords === "function" ? uniqueNameKeywords(raw) : raw.slice();
  return nameForbidCache;
}
function applyForbidToLoadedProducts() {
  try {
    if (typeof products !== "undefined" && Array.isArray(products)) products.forEach(scrubProductRecord);
    if (typeof current !== "undefined" && current) scrubProductRecord(current);
    if (typeof renderSheets === "function" && document.getElementById("productTable")) renderSheets();
    if (typeof fillPreview === "function") fillPreview();
  } catch (error) {}
}
if (typeof api === "function" && !api.nameForbidWrapped) {
  const apiBeforeForbid = api;
  api = async function (path, options) {
    const data = await apiBeforeForbid(path, options);
    const url = String(path || "");
    if (url.indexOf("/api/name-keywords") >= 0) {
      rememberForbidWords(data);
      applyForbidToLoadedProducts();
      return data;
    }
    if (url.indexOf("/name/suggest") >= 0 && data && typeof data === "object") {
      const words = nameForbidWords();
      if (typeof data.name === "string") data.name = stripForbiddenText(data.name, words);
      if (Array.isArray(data.keywords)) {
        data.keywords = data.keywords.filter((row) => {
          const word = String((row && row.keyword) || "");
          return word && stripForbiddenText(word, words) === word;
        });
      }
      return data;
    }
    return scrubForbidPayload(data);
  };
  api.nameForbidWrapped = true;
}
if (typeof saveProduct === "function" && !saveProduct.nameForbidWrapped) {
  const saveProductBeforeForbid = saveProduct;
  saveProduct = async function (product, patch, quiet) {
    const next = patch && typeof patch === "object" ? Object.assign({}, patch) : patch;
    const words = nameForbidWords();
    if (next && words.length) {
      if (typeof next.name === "string") next.name = stripForbiddenText(next.name, words);
      if (Array.isArray(next.tags)) next.tags = stripForbiddenTags(next.tags, words);
    }
    return saveProductBeforeForbid(product, next, quiet);
  };
  saveProduct.nameForbidWrapped = true;
}
if (typeof renderTagChips === "function" && !renderTagChips.nameForbidWrapped) {
  const renderTagChipsBeforeForbid = renderTagChips;
  renderTagChips = function () {
    if (typeof draftTags !== "undefined" && Array.isArray(draftTags) && nameForbidWords().length) {
      draftTags = stripForbiddenTags(draftTags, nameForbidWords());
    }
    return renderTagChipsBeforeForbid.apply(this, arguments);
  };
  renderTagChips.nameForbidWrapped = true;
}
if (typeof openNameEditor === "function" && !openNameEditor.nameDetailWrapped) {
  const openNameEditorBeforeDetail = openNameEditor;
  openNameEditor = function () {
    const result = openNameEditorBeforeDetail.apply(this, arguments);
    const dialog = document.getElementById("nameDialog");
    if (!dialog || !dialog.open) return result;
    const form = document.getElementById("nameForm");
    let layout = document.getElementById("nameDetailLayout");
    if (!layout && form && form.parentNode) {
      layout = document.createElement("div");
      layout.id = "nameDetailLayout";
      layout.className = "name-detail-layout";
      form.parentNode.insertBefore(layout, form);
      layout.appendChild(form);
      const pane = document.createElement("aside");
      pane.id = "nameDetailPane";
      pane.className = "name-detail-pane";
      pane.innerHTML = '<h3>상세페이지</h3><div id="nameDetailView" class="detail-visual name-detail-view"></div>';
      layout.appendChild(pane);
      dialog.classList.add("name-with-detail");
    }
    const view = document.getElementById("nameDetailView");
    if (view && typeof current !== "undefined" && current) {
      const html = typeof prepareDetailHtml === "function" ? prepareDetailHtml(current.detail_html || "") : (current.detail_html || "");
      view.innerHTML = html || '<p class="hint">상세페이지가 없습니다.</p>';
      if (typeof bindDetailImages === "function") bindDetailImages(view);
    }
    return result;
  };
  openNameEditor.nameDetailWrapped = true;
}
if (typeof api === "function") {
  api("/api/name-keywords", { method: "GET", quiet: true }).catch(() => {});
}
"""
NAME_FORBID_CSS = r"""
/* name-keyword-tags1 */
#nameDialog.name-with-detail {
  width: min(1180px, calc(100vw - 24px));
  max-height: calc(100vh - 24px);
}
#nameDialog.name-with-detail .name-detail-layout {
  display: flex;
  align-items: stretch;
  max-height: calc(100vh - 48px);
}
#nameDialog.name-with-detail #nameForm {
  flex: 0 0 400px;
  width: 400px;
  max-width: 46vw;
  overflow: auto;
}
#nameDialog.name-with-detail .name-detail-pane {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  flex-direction: column;
  border-left: 1px solid var(--line, #d6dbe3);
  background: var(--page, #fff);
}
#nameDialog.name-with-detail .name-detail-pane h3 {
  margin: 0;
  padding: 14px 16px 8px;
  font-size: 16px;
}
#nameDialog.name-with-detail .name-detail-view {
  flex: 1 1 auto;
  margin: 0 12px 12px;
  min-height: 240px;
  max-height: calc(100vh - 120px);
}
@media (max-width: 860px) {
  #nameDialog.name-with-detail .name-detail-layout { flex-direction: column; }
  #nameDialog.name-with-detail #nameForm { width: auto; max-width: none; flex-basis: auto; }
  #nameDialog.name-with-detail .name-detail-pane { border-left: 0; border-top: 1px solid var(--line, #d6dbe3); }
  #nameDialog.name-with-detail .name-detail-view { max-height: 42vh; }
}
"""
NAME_COUNT_JS = r"""
/* name-count1 */
function nameCharCount(value) {
  return Array.from(String(value || "")).length;
}
function paintNameCount(node, value) {
  if (!node) return;
  const count = nameCharCount(value);
  node.textContent = count + "/100";
  node.classList.toggle("over", count > 100);
}
function mountNameCharCount() {
  const input = document.getElementById("nameInput");
  if (!input || document.getElementById("nameCharCount")) return;
  const count = document.createElement("span");
  count.id = "nameCharCount";
  count.className = "name-char-count";
  const parent = input.parentNode;
  if (parent) parent.classList.add("name-count-field");
  input.insertAdjacentElement("afterend", count);
  const refresh = () => paintNameCount(count, input.value);
  input.addEventListener("input", refresh);
  refresh();
  window.refreshNameCharCount = refresh;
}
function attachNameCellCount(cell) {
  if (!cell || cell.querySelector(".name-char-count")) return;
  cell.classList.add("name-count-cell");
  const count = document.createElement("span");
  count.className = "name-char-count";
  const read = () => {
    const input = cell.querySelector("input");
    if (input && !input.hidden) return input.value;
    const view = cell.querySelector(".cell-view");
    return view ? view.textContent : "";
  };
  const refresh = () => paintNameCount(count, read());
  cell.appendChild(count);
  const input = cell.querySelector("input");
  if (input) {
    input.addEventListener("input", refresh);
    input.addEventListener("blur", refresh);
  }
  refresh();
}
function closeMenuDialog(id) {
  const dialog = document.getElementById(id);
  if (dialog && dialog.open) dialog.close();
}
function menuSaveClosesDialog(path, options) {
  const method = String((options && options.method) || "GET").toUpperCase();
  const url = String(path || "").split("?")[0];
  if (method === "PUT" && url.indexOf("/api/benefit") >= 0) return "benefitDialog";
  if (method === "PUT" && url.indexOf("/api/name-keywords") >= 0) return "nameKeywordDialog";
  if (method === "POST" && /\/api\/delivery-templates$/.test(url)) return "deliveryDialog";
  if (method === "PUT" && /\/api\/delivery-templates\/(?!import$)[^/]+$/.test(url)) return "deliveryDialog";
  return "";
}
if (typeof inputCell === "function" && !inputCell.nameCountWrapped) {
  const inputCellBeforeCount = inputCell;
  inputCell = function (value, field, type, locked) {
    const cell = inputCellBeforeCount.apply(this, arguments);
    if (field === "name" && !locked && cell) attachNameCellCount(cell);
    return cell;
  };
  inputCell.nameCountWrapped = true;
}
if (typeof openNameEditor === "function" && !openNameEditor.nameCountWrapped) {
  const openNameEditorBeforeCount = openNameEditor;
  openNameEditor = function () {
    const result = openNameEditorBeforeCount.apply(this, arguments);
    if (typeof window.refreshNameCharCount === "function") window.refreshNameCharCount();
    return result;
  };
  openNameEditor.nameCountWrapped = true;
}
if (typeof api === "function" && !api.menuSaveCloseWrapped) {
  const apiBeforeMenuSave = api;
  api = async function (path, options) {
    const data = await apiBeforeMenuSave.apply(this, arguments);
    const dialogId = menuSaveClosesDialog(path, options);
    if (dialogId) closeMenuDialog(dialogId);
    if (String(path || "").indexOf("/name/suggest") >= 0 && typeof window.refreshNameCharCount === "function") {
      setTimeout(window.refreshNameCharCount, 0);
    }
    return data;
  };
  api.menuSaveCloseWrapped = true;
}
mountNameCharCount();
"""
NAME_COUNT_CSS = r"""
/* name-count1 */
.name-char-count {
  color: #1f9d55;
  font-size: 13px;
  font-weight: 700;
  line-height: 1;
  pointer-events: none;
}
.name-char-count.over { color: #e11d48; }
html[data-theme="dark"] .name-char-count { color: #3ddc84; }
html[data-theme="dark"] .name-char-count.over { color: #fb7185; }
.name-count-field { position: relative; }
.name-count-field .name-char-count {
  position: absolute;
  right: 10px;
  bottom: 8px;
}
#nameInput { padding-right: 72px; padding-bottom: 22px; }
td.name-count-cell { position: relative; }
td.name-count-cell .name-char-count {
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
}
td.name-count-cell .cell-view,
td.name-count-cell input {
  padding-right: 58px;
  box-sizing: border-box;
}
"""
NAME_LAYOUT_JS = r"""
/* name-layout1 */
function widenNameEditorColumn() {
  const form = document.getElementById("nameForm");
  const input = document.getElementById("nameInput");
  const dialog = document.getElementById("nameDialog");
  if (!form || !input || !dialog) return;
  let node = input.parentElement;
  let column = null;
  while (node && node !== form && node !== dialog) {
    const parent = node.parentElement;
    if (!parent) break;
    const style = window.getComputedStyle(parent);
    const display = style.display || "";
    const direction = style.flexDirection || "row";
    const row = (display === "flex" || display === "inline-flex") && direction.indexOf("column") !== 0;
    const grid = display === "grid" || display === "inline-grid";
    if (row || grid) {
      const siblings = Array.prototype.filter.call(parent.children, (el) => el !== node);
      if (siblings.length) {
        column = node;
        break;
      }
    }
    node = parent;
  }
  form.classList.toggle("name-has-keywords", !!column);
  if (!column) return;
  column.style.setProperty("flex", "1 0 360px", "important");
  column.style.setProperty("min-width", "360px", "important");
  column.style.setProperty("max-width", "520px", "important");
  column.style.setProperty("width", "auto", "important");
}
if (typeof openNameEditor === "function" && !openNameEditor.nameLayoutWrapped) {
  const openNameEditorBeforeLayout = openNameEditor;
  openNameEditor = function () {
    const result = openNameEditorBeforeLayout.apply(this, arguments);
    widenNameEditorColumn();
    setTimeout(widenNameEditorColumn, 0);
    return result;
  };
  openNameEditor.nameLayoutWrapped = true;
}
"""
NAME_LAYOUT_CSS = r"""
/* name-layout1 */
#nameDialog.name-with-detail {
  width: min(1480px, calc(100vw - 24px));
}
#nameDialog.name-with-detail #nameForm {
  flex: 1 0 420px;
  width: auto;
  min-width: 360px;
  max-width: 520px;
  overflow: auto;
}
#nameDialog.name-with-detail #nameForm.name-has-keywords,
#nameDialog.name-with-detail #nameForm:has(aside) {
  flex: 1 1 auto;
  width: auto;
  min-width: min(760px, 100%);
  max-width: none;
}
#nameDialog.name-with-detail .name-detail-pane {
  flex: 1 1 420px;
  min-width: 260px;
}
#nameDialog.name-with-detail #nameForm *:has(#nameInput):not(:has(aside)) {
  flex-grow: 1 !important;
  flex-shrink: 0 !important;
  flex-basis: 360px !important;
  min-width: 360px !important;
  max-width: 520px;
  width: auto !important;
  box-sizing: border-box;
}
#nameDialog.name-with-detail #nameInput {
  box-sizing: border-box;
  width: 100%;
  min-height: 96px;
  writing-mode: horizontal-tb;
  word-break: keep-all;
  padding-right: 76px;
  padding-bottom: 28px;
}
#nameDialog.name-with-detail .name-suggest-actions button {
  white-space: nowrap;
  flex: 0 0 auto;
}
#nameDialog.name-with-detail .name-suggest-actions .hint {
  white-space: normal;
  word-break: keep-all;
  line-height: 1.45;
}
@media (max-width: 980px) {
  #nameDialog.name-with-detail .name-detail-layout { flex-direction: column; }
  #nameDialog.name-with-detail #nameForm,
  #nameDialog.name-with-detail #nameForm.name-has-keywords {
    min-width: 0;
    max-width: none;
    width: auto;
    flex-basis: auto;
  }
  #nameDialog.name-with-detail .name-detail-pane {
    min-width: 0;
    border-left: 0;
    border-top: 1px solid var(--line, #d6dbe3);
  }
}
"""
DIALOG_RESIZE_JS = r"""
/* dialog-resize1 */
/* resize-pure-start */
function dialogResizeBox(edge, startLeft, startWidth, dx, viewWidth, minWidth) {
  const margin = 8;
  const startRight = startLeft + startWidth;
  let left = startLeft;
  let right = startRight;
  if (edge === "right") right = startRight + dx;
  else left = startLeft + dx;
  if (right - left < minWidth) {
    if (edge === "left") left = right - minWidth;
    else right = left + minWidth;
  }
  if (left < margin) {
    left = margin;
    if (right - left < minWidth) right = left + minWidth;
  }
  if (right > viewWidth - margin) {
    right = viewWidth - margin;
    if (right - left < minWidth) left = Math.max(margin, right - minWidth);
  }
  return { left: Math.round(left), width: Math.round(right - left) };
}
/* resize-pure-end */
function pinDialogBox(dialog) {
  const rect = dialog.getBoundingClientRect();
  dialog.classList.add("dialog-moved");
  dialog.style.margin = "0";
  dialog.style.position = "fixed";
  dialog.style.left = rect.left + "px";
  dialog.style.top = rect.top + "px";
  dialog.style.width = rect.width + "px";
  dialog.style.maxWidth = "none";
  return rect;
}
function relaxNameColumnWidth() {
  const input = document.getElementById("nameInput");
  const form = document.getElementById("nameForm");
  if (!input || !form) return;
  let node = input.parentElement;
  while (node && node !== form) {
    node.style.setProperty("max-width", "none", "important");
    node = node.parentElement;
  }
}
function trackDialogResize(event, onMove) {
  event.preventDefault();
  event.stopPropagation();
  document.body.classList.add("col-resizing");
  const move = (ev) => onMove(ev);
  const stop = () => {
    document.removeEventListener("pointermove", move);
    document.removeEventListener("pointerup", stop);
    document.removeEventListener("pointercancel", stop);
    document.body.classList.remove("col-resizing");
  };
  document.addEventListener("pointermove", move);
  document.addEventListener("pointerup", stop);
  document.addEventListener("pointercancel", stop);
}
function mountDialogEdgeResize(dialog) {
  if (!dialog || dialog.dataset.edgeResize === "1") return;
  dialog.dataset.edgeResize = "1";
  ["left", "right"].forEach((edge) => {
    const handle = document.createElement("div");
    handle.className = "dialog-resize-handle dialog-resize-" + edge;
    handle.title = "좌우로 끌어 창 너비를 조절합니다";
    dialog.appendChild(handle);
    handle.addEventListener("pointerdown", (event) => {
      if (event.button !== 0) return;
      const rect = pinDialogBox(dialog);
      const startX = event.clientX;
      trackDialogResize(event, (ev) => {
        const box = dialogResizeBox(edge, rect.left, rect.width, ev.clientX - startX, window.innerWidth, 360);
        dialog.style.left = box.left + "px";
        dialog.style.width = box.width + "px";
        dialog.style.maxWidth = "none";
      });
    });
  });
  dialog.addEventListener("close", () => {
    dialog.style.maxWidth = "";
    dialog.style.minWidth = "";
  });
}
function mountDialogEdgeResizeAll() {
  document.querySelectorAll("dialog").forEach(mountDialogEdgeResize);
}
function setPaneWidth(pane, width) {
  pane.style.setProperty("flex", "0 0 " + width + "px", "important");
  pane.style.setProperty("width", width + "px", "important");
  pane.style.setProperty("max-width", "none", "important");
  pane.style.setProperty("min-width", "0px", "important");
}
function mountSplitter(parent, pane, minPane, minRest) {
  if (!parent || !pane || pane.dataset.splitterReady === "1") return;
  pane.dataset.splitterReady = "1";
  const handle = document.createElement("div");
  handle.className = "dialog-pane-resizer";
  handle.title = "좌우로 끌어 너비를 조절합니다";
  parent.insertBefore(handle, pane);
  handle.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    const previous = pane.previousElementSibling === handle ? handle.previousElementSibling : pane.previousElementSibling;
    const target = previous && previous !== handle ? previous : pane;
    const startWidth = target.getBoundingClientRect().width;
    const startX = event.clientX;
    trackDialogResize(event, (ev) => {
      const parentWidth = parent.getBoundingClientRect().width || window.innerWidth;
      const next = Math.round(startWidth + (ev.clientX - startX));
      const width = Math.max(minPane, Math.min(parentWidth - minRest, next));
      setPaneWidth(target, width);
      relaxNameColumnWidth();
    });
  });
}
function mountNameSplitters() {
  const layout = document.getElementById("nameDetailLayout");
  const form = document.getElementById("nameForm");
  const detail = document.getElementById("nameDetailPane");
  if (layout && detail) mountSplitter(layout, detail, 360, 240);
  const input = document.getElementById("nameInput");
  if (!form || !input) return;
  let node = input.parentElement;
  while (node && node !== form) {
    const parent = node.parentElement;
    if (!parent) break;
    const style = window.getComputedStyle(parent);
    const row = (style.display === "flex" || style.display === "inline-flex") && String(style.flexDirection || "row").indexOf("column") !== 0;
    if (row && node.nextElementSibling) {
      mountSplitter(parent, node.nextElementSibling, 320, 220);
      break;
    }
    node = parent;
  }
}
if (typeof openNameEditor === "function" && !openNameEditor.dialogResizeWrapped) {
  const openNameEditorBeforeResize = openNameEditor;
  openNameEditor = function () {
    const result = openNameEditorBeforeResize.apply(this, arguments);
    relaxNameColumnWidth();
    mountNameSplitters();
    setTimeout(() => {
      relaxNameColumnWidth();
      mountNameSplitters();
    }, 0);
    return result;
  };
  openNameEditor.dialogResizeWrapped = true;
}
mountDialogEdgeResizeAll();
try {
  if (typeof HTMLDialogElement === "function" && HTMLDialogElement.prototype.showModal && !HTMLDialogElement.prototype.showModal.dialogResizeWrapped) {
    const showModalBeforeResize = HTMLDialogElement.prototype.showModal;
    HTMLDialogElement.prototype.showModal = function () {
      mountDialogEdgeResize(this);
      return showModalBeforeResize.apply(this, arguments);
    };
    HTMLDialogElement.prototype.showModal.dialogResizeWrapped = true;
  }
} catch (error) {}
"""
DIALOG_RESIZE_CSS = r"""
/* dialog-resize1 */
.dialog-resize-handle,
.dialog-pane-resizer {
  cursor: col-resize;
  touch-action: none;
  z-index: 30;
}
.dialog-resize-handle {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 8px;
}
.dialog-resize-left { left: 0; }
.dialog-resize-right { right: 0; }
.dialog-pane-resizer {
  position: relative;
  flex: 0 0 8px;
  width: 8px;
  align-self: stretch;
  margin: 0;
  background: transparent;
}
.dialog-resize-handle:hover,
.dialog-pane-resizer:hover,
body.col-resizing .dialog-resize-handle,
body.col-resizing .dialog-pane-resizer { background: #0078d7; }
#nameDialog.name-with-detail #nameForm,
#nameDialog.name-with-detail #nameForm.name-has-keywords,
#nameDialog.name-with-detail #nameForm *:has(#nameInput):not(:has(aside)) {
  max-width: none;
}
@media (max-width: 980px) {
  #nameDialog .dialog-pane-resizer { display: none; }
}
"""
NAVER_TAG_SERVICE_PY = r'''
# naver-tag1
# Tag fill uses Naver's tag dictionary as returned. The search-tag list is the
# seller tags on Naver shopping results for the leaf category, pages 1 to 3.
import base64 as _naver_tag_base64
import json as _naver_tag_json
import re as _naver_tag_re
import time as _naver_tag_time

try:
    from starlette.requests import Request as _NaverRequest
except Exception:
    _NaverRequest = object

_NAVER_AUTO_TAGS = {"오늘출발", "오늘발송", "오늘도착", "무료교환", "무료반품", "무료배송"}
_naver_token_cache = {"token": "", "until": 0.0}


def _naver_tag_token(value):
    text = str(value or "").strip()
    if text.startswith("#"):
        text = text[1:].strip()
    text = text.replace("\u200b", "")
    if not text or text in _NAVER_AUTO_TAGS or len(text) > 30:
        return ""
    return text


def _naver_split_tags(blob):
    found = []
    for part in _naver_tag_re.split(r"[,|/·]+", str(blob or "")):
        token = _naver_tag_token(part)
        if token:
            found.append(token)
    return found


def _naver_tags_from_product(product):
    found = []
    if not isinstance(product, dict):
        return found
    for key in ("manuTag", "manualTag", "sellerTag", "searchTag"):
        if product.get(key):
            found.extend(_naver_split_tags(product.get(key)))
    for key in ("sellerTags", "tags", "tagList", "manuTags"):
        value = product.get(key)
        if isinstance(value, str):
            found.extend(_naver_split_tags(value))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    token = _naver_tag_token(item)
                elif isinstance(item, dict):
                    token = _naver_tag_token(item.get("text") or item.get("tag") or item.get("name") or "")
                else:
                    token = ""
                if token:
                    found.append(token)
    return found


def _naver_walk_products(node, out, seen):
    if isinstance(node, dict):
        marker = id(node)
        if marker in seen:
            return
        seen.add(marker)
        if any(key in node for key in ("manuTag", "sellerTags", "productTitle", "productName", "mallProductId")):
            out.extend(_naver_tags_from_product(node))
        for value in node.values():
            if isinstance(value, (dict, list)):
                _naver_walk_products(value, out, seen)
    elif isinstance(node, list):
        for item in node:
            _naver_walk_products(item, out, seen)


def _naver_unique_tags(tags):
    ordered = []
    for tag in tags:
        if tag and tag not in ordered:
            ordered.append(tag)
        if len(ordered) >= 300:
            break
    return ordered


def _tags_from_text(text):
    raw = str(text or "")
    tags = []
    stripped = raw.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            data = _naver_tag_json.loads(raw)
        except Exception:
            data = None
        if data is not None:
            _naver_walk_products(data, tags, set())
    if not tags:
        for match in _naver_tag_re.finditer(r'"manuTag"\s*:\s*"((?:\\.|[^"\\])*)"', raw):
            try:
                blob = _naver_tag_json.loads('"' + match.group(1) + '"')
            except Exception:
                blob = match.group(1)
            tags.extend(_naver_split_tags(blob))
    return _naver_unique_tags(tags)


def _collect_search_tags(pages):
    ordered = []
    for text in pages or []:
        for tag in _tags_from_text(text):
            if tag not in ordered:
                ordered.append(tag)
            if len(ordered) >= 300:
                return ordered
    return ordered


def _naver_http_get(url, params, headers):
    try:
        import httpx
    except Exception:
        httpx = None
    if httpx is not None:
        with httpx.Client(headers=headers, follow_redirects=True, timeout=20.0) as client:
            response = client.get(url, params=params)
            return response.status_code, response.text or ""
    import urllib.parse
    import urllib.request
    full = url + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(full, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.status, response.read().decode("utf-8", "replace")


def _naver_http_post_form(url, form):
    try:
        import httpx
    except Exception:
        httpx = None
    if httpx is not None:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            response = client.post(url, data=form)
            return response.status_code, response.text or ""
    import urllib.parse
    import urllib.request
    data = urllib.parse.urlencode(form).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.status, response.read().decode("utf-8", "replace")


def _naver_search_product_tags(query):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        "Referer": "https://search.shopping.naver.com/search/all?query=" + str(query),
    }
    pages = []
    failures = 0
    for page in (1, 2, 3):
        params = {
            "sort": "rel",
            "pagingIndex": str(page),
            "pagingSize": "40",
            "viewType": "list",
            "productSet": "total",
            "query": query,
            "origQuery": query,
            "adQuery": query,
        }
        try:
            status, text = _naver_http_get("https://search.shopping.naver.com/api/search/all", params, headers)
        except Exception:
            status, text = 0, ""
        if status >= 400 or not _tags_from_text(text):
            try:
                status, text = _naver_http_get(
                    "https://search.shopping.naver.com/search/all",
                    {"query": query, "pagingIndex": str(page), "pagingSize": "40"},
                    headers,
                )
            except Exception:
                status, text = 0, ""
        if status >= 400 or not text:
            failures += 1
            continue
        pages.append(text)
    tags = _collect_search_tags(pages)
    if not tags and failures:
        raise RuntimeError("네이버 쇼핑 검색에서 태그를 가져오지 못했습니다.")
    return tags


def _dictionary_rows(payload):
    rows = payload
    if isinstance(payload, dict):
        rows = []
        for key in ("tags", "recommendTags", "contents", "data", "items"):
            if isinstance(payload.get(key), list):
                rows = payload[key]
                break
    out = []
    seen = set()
    if not isinstance(rows, list):
        return out
    for item in rows:
        if isinstance(item, str):
            text = item.strip()
            code = None
        elif isinstance(item, dict):
            text = str(item.get("text") or item.get("tagName") or item.get("name") or "").strip()
            code = item.get("code")
            if code is None:
                code = item.get("id")
        else:
            continue
        if not text or text in seen:
            continue
        seen.add(text)
        out.append({"text": text, "code": code})
    return out


def _dictionary_from_app(keyword):
    import sys
    names = ("recommend_tags", "get_recommend_tags", "search_recommend_tags", "naver_recommend_tags")
    for module in list(sys.modules.values()):
        if module is None:
            continue
        for name in names:
            fn = getattr(module, name, None)
            if not callable(fn):
                continue
            try:
                return fn(keyword)
            except TypeError:
                continue
            except Exception:
                return None
    return None


def _existing_commerce_token():
    import sys
    names = ("commerce_token", "naver_commerce_token", "get_commerce_token", "smartstore_token")
    for module in list(sys.modules.values()):
        if module is None:
            continue
        for name in names:
            fn = getattr(module, name, None)
            if not callable(fn):
                continue
            try:
                token = fn()
            except Exception:
                continue
            if isinstance(token, str) and len(token) > 20:
                return token
            if isinstance(token, dict):
                value = token.get("access_token") or token.get("token")
                if isinstance(value, str) and len(value) > 20:
                    return value
    return ""


def _commerce_credentials():
    import sys
    chosen = None
    for module in list(sys.modules.values()):
        if module is None:
            continue
        for name in ("list_markets", "load_markets", "get_markets", "read_markets"):
            fn = getattr(module, name, None)
            if not callable(fn):
                continue
            try:
                data = fn()
            except Exception:
                continue
            rows = data if isinstance(data, list) else []
            if isinstance(data, dict):
                items = data.get("items") or data.get("markets") or []
                rows = items if isinstance(items, list) else []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                channel = str(row.get("channel") or row.get("channel_id") or "smartstore").lower()
                if channel and "smart" not in channel and "naver" not in channel:
                    continue
                client_id = str(row.get("naver_client_id") or row.get("api_key") or row.get("client_id") or "").strip()
                secret = str(row.get("naver_client_secret") or row.get("api_secret") or row.get("client_secret") or "").strip()
                account = str(row.get("naver_account_id") or row.get("account_id") or "").strip()
                if not client_id or not secret or "*" in secret:
                    continue
                chosen = (client_id, secret, account)
                if row.get("is_default"):
                    return chosen
    return chosen


def _commerce_access_token():
    now = _naver_tag_time.time()
    if _naver_token_cache["token"] and _naver_token_cache["until"] > now:
        return _naver_token_cache["token"]
    existing = _existing_commerce_token()
    if existing:
        _naver_token_cache["token"] = existing
        _naver_token_cache["until"] = now + 60
        return existing
    creds = _commerce_credentials()
    if not creds:
        return ""
    client_id, secret, account = creds
    try:
        import bcrypt
    except Exception:
        return ""
    timestamp = str(int(_naver_tag_time.time() * 1000))
    try:
        hashed = bcrypt.hashpw((client_id + "_" + timestamp).encode("utf-8"), secret.encode("utf-8"))
    except Exception:
        return ""
    sign = _naver_tag_base64.b64encode(hashed).decode("utf-8")
    form = {
        "client_id": client_id,
        "timestamp": timestamp,
        "client_secret_sign": sign,
        "grant_type": "client_credentials",
        "type": "SELF",
    }
    if account:
        form["account_id"] = account
    try:
        status, text = _naver_http_post_form("https://api.commerce.naver.com/external/v1/oauth2/token", form)
    except Exception:
        return ""
    if status >= 400:
        return ""
    try:
        payload = _naver_tag_json.loads(text)
    except Exception:
        return ""
    token = str(payload.get("access_token") or "")
    if not token:
        return ""
    try:
        expires = int(payload.get("expires_in") or 3600)
    except (TypeError, ValueError):
        expires = 3600
    _naver_token_cache["token"] = token
    _naver_token_cache["until"] = now + max(60, expires - 60)
    return token


def _naver_dictionary(keyword):
    found = _dictionary_from_app(keyword)
    if found is not None:
        tags = _dictionary_rows(found)
        if tags:
            return tags
    token = _commerce_access_token()
    if not token:
        raise RuntimeError("네이버 태그사전을 가져오려면 스마트스토어 연동이 필요합니다.")
    headers = {"Authorization": "Bearer " + token, "Accept": "application/json"}
    status, text = _naver_http_get(
        "https://api.commerce.naver.com/external/v2/tags/recommend-tags",
        {"keyword": keyword},
        headers,
    )
    if status == 404:
        status, text = _naver_http_get(
            "https://api.commerce.naver.com/external/v1/tags/recommend-tags",
            {"keyword": keyword},
            headers,
        )
    if status >= 400:
        raise RuntimeError("네이버 태그사전 조회에 실패했습니다.")
    try:
        payload = _naver_tag_json.loads(text)
    except Exception as exc:
        raise RuntimeError("네이버 태그사전 응답을 읽지 못했습니다.") from exc
    return _dictionary_rows(payload)


def _naver_json(payload, status=200):
    from starlette.responses import JSONResponse
    return JSONResponse(payload, status_code=status)


async def _naver_search_route(request: _NaverRequest):
    query = str(request.query_params.get("q") or "").strip()
    if not query:
        return _naver_json({"detail": "카테고리가 없습니다."}, 400)
    try:
        tags = _naver_search_product_tags(query)
    except Exception as exc:
        return _naver_json({"detail": str(exc)}, 502)
    return _naver_json({"query": query, "pages": [1, 2, 3], "tags": tags})


async def _naver_dictionary_route(request: _NaverRequest):
    query = str(request.query_params.get("q") or "").strip()
    if not query:
        return _naver_json({"detail": "카테고리가 없습니다."}, 400)
    try:
        tags = _naver_dictionary(query)
    except Exception as exc:
        return _naver_json({"detail": str(exc)}, 502)
    return _naver_json({"query": query, "tags": tags})


def _find_api_app():
    import sys
    best = None
    best_score = 0
    for module in list(sys.modules.values()):
        if module is None:
            continue
        for name in ("app", "api", "application"):
            candidate = getattr(module, name, None)
            routes = getattr(candidate, "routes", None)
            if not routes:
                continue
            score = 0
            for route in routes:
                path = str(getattr(route, "path", "") or getattr(route, "rule", "") or "")
                if "/api/products" in path:
                    score += 5
                elif "/api/" in path:
                    score += 1
            if score > best_score:
                best = candidate
                best_score = score
    return best


def _add_naver_tag_routes(app):
    paths = {"/api/tags/naver-search": _naver_search_route, "/api/tags/naver-dictionary": _naver_dictionary_route}
    existing = set()
    for route in getattr(app, "routes", []):
        existing.add(str(getattr(route, "path", "") or getattr(route, "rule", "") or ""))
    for path, handler in paths.items():
        if path in existing:
            continue
        if hasattr(app, "add_api_route"):
            app.add_api_route(path, handler, methods=["GET"])
        else:
            from starlette.routing import Route
            app.router.routes.append(Route(path, handler, methods=["GET"]))


def _naver_tag_install():
    if globals().get("_naver_tag_installed"):
        return
    globals()["_naver_tag_installed"] = True

    def attach():
        app = _find_api_app()
        if app is None:
            return False
        _add_naver_tag_routes(app)
        return True

    try:
        if attach():
            return
    except Exception:
        pass
    import threading

    def run():
        for _ in range(40):
            try:
                if attach():
                    return
            except Exception:
                return
            _naver_tag_time.sleep(0.5)
    threading.Thread(target=run, name="naver-tag1", daemon=True).start()


if not globals().get("_NAVER_TAG_NO_INSTALL"):
    _naver_tag_install()
'''
NAVER_TAG_SERVICE_NEEDED = ("def collect_product",)


def frozen_fix_plan() -> dict:
    godo_needed = (
        "def _read_supplier_product",
        "def _load_page",
        "def _gallery_ready",
        "def _match_wholesaler_id",
        "PageSession",
    )
    catalog_needed = ("def _godomall_products", "def _godo_goods_from_href", "def _base", "PAGE_HEADERS", "BeautifulSoup", "httpx")
    return {
        "app.scraper": [
            (MURRAY_MARKER, ("def extract_product",), MURRAY_SCRAPER_PY),
            (GODO_MARKER, ("def extract_product",), GODO_SCRAPER_PY),
            (GODO_NAME_MARKER, ("def extract_product", GODO_MARKER), GODO_NAME_SCRAPER_PY),
            (GODO_IMAGE1_MARKER, GODO_IMAGE1_SCRAPER_NEEDED, GODO_IMAGE1_SCRAPER_PY),
            (GODO_IMAGE2_MARKER, GODO_IMAGE2_SCRAPER_NEEDED, GODO_IMAGE2_SCRAPER_PY),
            (GODO_IMAGE3_MARKER, GODO_IMAGE3_SCRAPER_NEEDED, GODO_IMAGE3_SCRAPER_PY),
            (GODO_IMAGE4_MARKER, GODO_IMAGE4_SCRAPER_NEEDED, GODO_IMAGE4_SCRAPER_PY),
        ],
        "app.service": [
            (MURRAY_MARKER, ("def _apply_wholesale_extract",), MURRAY_SERVICE_PY),
            (GODO_MARKER, godo_needed, GODO_SERVICE_PY),
            (GODO_NAME_MARKER, ("def collect_product", GODO_MARKER, MURRAY_MARKER), GODO_NAME_SERVICE_PY),
            (GODO_NAME2_MARKER, GODO_NAME2_SERVICE_NEEDED, GODO_NAME2_SERVICE_PY),
            (GODO_SITE2_MARKER, GODO_SITE2_SERVICE_NEEDED, GODO_SITE2_SERVICE_PY),
            (GODO_OPEN1_MARKER, GODO_OPEN1_SERVICE_NEEDED, GODO_OPEN1_SERVICE_PY),
            (GODO_LOGIN2_MARKER, GODO_LOGIN2_SERVICE_NEEDED, GODO_LOGIN2_SERVICE_PY),
            (GODO_IMAGE2_MARKER, GODO_IMAGE2_SERVICE_NEEDED, GODO_IMAGE2_SERVICE_PY),
            (NAVER_TAG_MARKER, NAVER_TAG_SERVICE_NEEDED, NAVER_TAG_SERVICE_PY),
        ],
        "app.chrome_app": [
            (TEXT_DECODE1_MARKER, TEXT_DECODE1_CHROME_NEEDED, TEXT_DECODE1_CHROME_PY),
        ],
        "app.shop_catalog": [
            (GODO_NAME_MARKER, catalog_needed, GODO_NAME_CATALOG_PY),
            (GODO_NAME2_MARKER, GODO_NAME2_CATALOG_NEEDED, GODO_NAME2_CATALOG_PY),
            (GODO_SITE1_MARKER, GODO_SITE1_CATALOG_NEEDED, GODO_SITE1_CATALOG_PY),
            (GODO_IMAGE1_MARKER, GODO_IMAGE1_CATALOG_NEEDED, GODO_IMAGE1_CATALOG_PY),
            (GODO_IMAGE2_MARKER, GODO_IMAGE2_CATALOG_NEEDED, GODO_IMAGE2_CATALOG_PY),
            (GODO_IMAGE3_MARKER, GODO_IMAGE3_CATALOG_NEEDED, GODO_IMAGE3_CATALOG_PY),
            (GODO_IMAGE4_MARKER, GODO_IMAGE4_CATALOG_NEEDED, GODO_IMAGE4_CATALOG_PY),
        ],
    }


FROZEN_FIXES_TEMPLATE = r'''# The seller program is a frozen PyInstaller build, so its app modules cannot
# be edited. pwd.py loads this file early and it applies the same source fixes
# as the master right after each app module runs.
import sys

FIXES = __FIXES__


def _ready(module, required):
    done = module.__dict__.get("_modumodu_fixes", set())
    for name in required:
        if name.startswith("# "):
            if name not in done:
                return False
        elif (name[4:] if name.startswith("def ") else name) not in module.__dict__:
            return False
    return True


def apply(module):
    done = module.__dict__.setdefault("_modumodu_fixes", set())
    for marker, required, snippet in FIXES.get(module.__name__, ()):
        if marker in done or not _ready(module, required):
            continue
        try:
            code = compile(snippet, "<" + module.__name__ + " " + marker + ">", "exec", flags=0x1000000, dont_inherit=True)
            exec(code, module.__dict__)
        except Exception as exc:
            print("modumodu fix failed", module.__name__, marker, exc, file=sys.stderr)
            continue
        done.add(marker)


class _Loader:
    def __init__(self, loader):
        self._loader = loader

    def __getattr__(self, name):
        return getattr(self._loader, name)

    def create_module(self, spec):
        return self._loader.create_module(spec)

    def exec_module(self, module):
        self._loader.exec_module(module)
        apply(module)


class _Finder:
    def find_spec(self, name, path=None, target=None):
        if name not in FIXES:
            return None
        for finder in list(sys.meta_path):
            if isinstance(finder, _Finder):
                continue
            find = getattr(finder, "find_spec", None)
            if find is None:
                continue
            spec = find(name, path, target)
            if spec is None:
                continue
            if spec.loader is not None and hasattr(spec.loader, "exec_module"):
                spec.loader = _Loader(spec.loader)
            return spec
        return None

    def invalidate_caches(self):
        pass


def install():
    if getattr(sys, "_modumodu_fixes_installed", False):
        return
    sys._modumodu_fixes_installed = True
    for name in FIXES:
        module = sys.modules.get(name)
        spec = getattr(module, "__spec__", None)
        if module is not None and not getattr(spec, "_initializing", False):
            apply(module)
    sys.meta_path.insert(0, _Finder())
'''

FROZEN_PWD_PY = r'''# Windows has no pwd module. The frozen seller program imports it while
# starting (shutil does), which is the first chance to load modumodu_fixes.
import sys

if getattr(sys, "frozen", False) and not getattr(sys, "_modumodu_fixes_installed", False):
    try:
        import modumodu_fixes

        modumodu_fixes.install()
    except Exception:
        pass

raise ModuleNotFoundError("No module named 'pwd'", name="pwd")
'''


def frozen_fixes_source() -> str:
    plan = frozen_fix_plan()
    lines = ["{"]
    for module, items in plan.items():
        lines.append("    " + repr(module) + ": [")
        for marker, required, snippet in items:
            lines.append("        (" + repr(marker) + ", " + repr(tuple(required)) + ", " + repr(snippet.strip() + "\n") + "),")
        lines.append("    ],")
    lines.append("}")
    return FROZEN_FIXES_TEMPLATE.replace("__FIXES__", "\n".join(lines))


def _frozen_program(folder: Path) -> bool:
    exe = folder / "MODUMODU.exe"
    return (folder / "_internal").is_dir() and exe.is_file() and exe.stat().st_size > 8000000


def write_frozen_fixes(folder: Path) -> bool:
    if not _frozen_program(folder):
        return False
    changed = False
    internal = folder / "_internal"
    for name, text in (("modumodu_fixes.py", frozen_fixes_source()), ("pwd.py", FROZEN_PWD_PY)):
        path = internal / name
        payload = text.encode("utf-8")
        if path.is_file() and path.read_bytes() == payload:
            continue
        path.write_bytes(payload)
        changed = True
    return changed


MASTER_SCRIPT_NAME = "어제오후9시.vbs"


def refresh_master_script(folder: Path) -> bool:
    """Windows tar can unpack the Korean script name garbled, and the old
    repair kept the bigger file, so a same-size new script was thrown away.
    The ASCII-named copy always arrives intact."""
    source = folder / "open-yesterday.vbs"
    target = folder / MASTER_SCRIPT_NAME
    if not source.is_file() or "셀러용" in folder.name:
        return False
    data = source.read_bytes()
    if target.is_file() and target.read_bytes() == data:
        return False
    try:
        if target.exists():
            target.chmod(0o666)
        target.write_bytes(data)
    except OSError:
        return False
    return True


RUNNING_STAMP = "master-running-version.txt"


def _windows_processes() -> list[tuple[int, int, str]]:
    script = (
        "[Console]::OutputEncoding=[Text.Encoding]::UTF8; "
        "Get-CimInstance Win32_Process | ForEach-Object { '{0}`t{1}`t{2}' -f $_.ProcessId, $_.ParentProcessId, $_.CommandLine }"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            timeout=60,
            creationflags=0x08000000,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    rows = []
    for line in result.stdout.decode("utf-8", "replace").splitlines():
        parts = line.split("\t", 2)
        if len(parts) == 3 and parts[0].strip().isdigit() and parts[1].strip().isdigit():
            rows.append((int(parts[0]), int(parts[1]), parts[2]))
    return rows


def _norm_cmd(text: str) -> str:
    return text.replace("/", "\\").lower()


def _started_by_idle_update(rows) -> bool:
    by_pid = {pid: (ppid, cmd) for pid, ppid, cmd in rows}
    pid = os.getpid()
    for _ in range(5):
        entry = by_pid.get(pid)
        if entry is None:
            return False
        parent = by_pid.get(entry[0])
        if parent is None:
            return False
        if "idle-update.vbs" in parent[1].lower():
            return True
        pid = entry[0]
    return False


def restart_stale_master(root: Path) -> bool:
    """launcher.py only reopens the browser when the server is already up, so
    a server started before an update keeps running the old Python code."""
    if os.name != "nt":
        return False
    data = root / "data"
    stamp = data / RUNNING_STAMP
    current = stamp.read_text(encoding="utf-8").strip() if stamp.is_file() else ""
    if current == SCREEN_VERSION:
        return False
    rows = _windows_processes()
    if not rows:
        return False
    launcher = _norm_cmd(str(root / "launcher.py"))
    running = [pid for pid, _ppid, cmd in rows if launcher in _norm_cmd(cmd) and pid != os.getpid()]
    stopped = False
    if running and current != SCREEN_VERSION:
        if _started_by_idle_update(rows):
            return False
        for pid in running:
            try:
                os.kill(pid, signal.SIGTERM)
                stopped = True
            except OSError:
                pass
        if stopped:
            time.sleep(2)
    try:
        data.mkdir(parents=True, exist_ok=True)
        stamp.write_text(SCREEN_VERSION + "\n", encoding="utf-8")
    except OSError:
        pass
    return stopped


def _step(root: Path, name: str, func, *args) -> bool:
    """One failing step (a locked seller file, say) must not stop the master
    from getting the rest of the update."""
    try:
        return bool(func(*args))
    except (Exception, SystemExit) as exc:
        import traceback

        print(f"{name} failed: {exc}")
        try:
            log = root / "data" / "patch-errors.log"
            log.parent.mkdir(parents=True, exist_ok=True)
            with log.open("a", encoding="utf-8") as handle:
                handle.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {SCREEN_VERSION} {name}\n")
                handle.write(traceback.format_exc() + "\n")
        except OSError:
            pass
        return False


def main() -> None:
    seller_only = "--seller-only" in sys.argv[1:]
    args = [arg for arg in sys.argv[1:] if arg != "--seller-only"]
    root = Path(args[0] if args else r"C:\smartstore uploader")
    if root.exists():
        _step(root, "repair names", repair_known_folders, root)
    _step(root, "master script", refresh_master_script, Path(__file__).resolve().parent)
    if seller_only:
        if root.exists() and _step(root, "seller copies", arrange_seller_copies, root):
            print("seller edition")
            raise SystemExit(11 if SETUP_ZIP_BUILT else 0)
        print("already linked")
        return
    static_changed = _step(root, "static", apply_static_patches, root)
    version_changed = root.exists() and _step(root, "version", write_screen_version, root)
    murray_changed = root.exists() and _step(root, "sources", patch_murray_sources, root)
    seller_changed = root.exists() and _step(root, "seller copies", arrange_seller_copies, root)
    if root.exists():
        _step(root, "restart", restart_stale_master, root)
    if not seller_changed and not static_changed and not version_changed and not murray_changed:
        if not iter_static_dirs(root):
            raise SystemExit(f"static files not found: {root / 'app' / 'static'}")
        print("already linked")
        return
    print("inquiry links on")
    # Exit 10 made older 어제오후9시.vbs copies show the seller setup notice on
    # every master start; 11 is only for a rebuilt seller setup zip.
    raise SystemExit(11 if SETUP_ZIP_BUILT else 0)


if __name__ == "__main__":
    main()
