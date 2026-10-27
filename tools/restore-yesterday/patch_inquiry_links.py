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
ANSWER_MARKER = "/* inquiry-answer-place */"
ANSWER_JS = r"""
/* inquiry-answer-place */
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
  function placeButton() {
    const button = document.getElementById("inquiryAnswerButton");
    const date = document.getElementById("inquiryAnswerAt");
    if (!button || !date) return;
    const anchor = date.closest("label") || date;
    if (button.previousElementSibling !== anchor) anchor.insertAdjacentElement("afterend", button);
    button.classList.add("inquiry-send-under-date");
    button.style.display = "block";
    button.style.width = "fit-content";
    button.style.maxWidth = "100%";
    button.style.margin = "8px auto 0";
    button.style.alignSelf = "center";
  }
  function openTyping() {
    fieldIds.forEach((id) => arm(document.getElementById(id)));
    const view = document.getElementById("inquiryAnswerView");
    const draft = document.getElementById("inquiryAnswerDraft");
    if (view && draft && view.dataset.inquiryRedirect !== "1") {
      view.dataset.inquiryRedirect = "1";
      const jump = (event) => {
        unlock(draft);
        if (event && event.type === "mousedown") event.preventDefault();
        draft.focus();
      };
      view.addEventListener("mousedown", jump);
      view.addEventListener("focus", jump);
    }
    placeButton();
  }
  function hookFill() {
    if (typeof fillInquiryDetail !== "function" || fillInquiryDetail.inquiryAnswerHook) return;
    const inner = fillInquiryDetail;
    function wrapped(item) {
      const result = inner.apply(this, arguments);
      openTyping();
      requestAnimationFrame(openTyping);
      return result;
    }
    wrapped.inquiryAnswerHook = true;
    fillInquiryDetail = wrapped;
  }
  function start() {
    openTyping();
    hookFill();
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


def patch_html(text: str) -> str:
    text = bump_asset(text, "styles.css", "inquiry-answer1")
    return bump_asset(text, "app.js", "inquiry-answer1")


def patch_answer(text: str) -> str:
    if ANSWER_MARKER in text:
        return text
    return text.rstrip() + "\n" + ANSWER_JS


def patch_css(text: str) -> str:
    if "inquiry-send-under-date" in text:
        return text
    return text.rstrip() + "\n" + ANSWER_CSS


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
    if new_js == js and new_html == html and new_css == css:
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
