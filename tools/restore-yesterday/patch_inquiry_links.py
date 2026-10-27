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
SCREEN_VERSION = "2026.10.28.3"
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
    text = bump_asset(text, "styles.css", "inquiry-simple3")
    return bump_asset(text, "app.js", "inquiry-simple3")


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
    return text


def patch_css(text: str) -> str:
    if "/* inquiry-simple3 */" in text:
        return text
    extra = ""
    if "inquiry-send-under-date" not in text:
        extra += ANSWER_CSS
    if "inquiry-answer-place2" not in text:
        extra += ANSWER_CSS2
    if "/* inquiry-simple1 */" not in text:
        extra += SIMPLE_CSS
    if "/* inquiry-simple2 */" not in text:
        extra += SIMPLE_CSS2
    return text.rstrip() + "\n" + extra + SIMPLE3_CSS


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
