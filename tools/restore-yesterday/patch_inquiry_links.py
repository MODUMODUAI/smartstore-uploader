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
SCRIPT_RE = re.compile(r'(app\.js)(?:\?v=[^"\']*)?')


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


def patch_html(text: str) -> str:
    if "app.js?v=inquiry-links1" in text:
        return text
    updated, count = SCRIPT_RE.subn(r"\1?v=inquiry-links1", text, count=1)
    if count != 1:
        raise SystemExit("app.js script tag not found")
    return updated


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\smartstore uploader")
    static = root / "app" / "static"
    js_path = static / "app.js"
    html_path = static / "index.html"
    if not js_path.is_file() or not html_path.is_file():
        raise SystemExit(f"static files not found: {static}")
    js, js_nl = read_text(js_path)
    html, html_nl = read_text(html_path)
    new_js = patch_js(js)
    new_html = patch_html(html)
    if new_js == js and new_html == html:
        print("already linked")
        return
    for path in (js_path, html_path):
        backup = path.with_name(path.name + ".bak-inquiry-links")
        if not backup.exists():
            backup.write_bytes(path.read_bytes())
    write_text(js_path, new_js, js_nl)
    write_text(html_path, new_html, html_nl)
    print("inquiry links on")
    raise SystemExit(10)


if __name__ == "__main__":
    main()
