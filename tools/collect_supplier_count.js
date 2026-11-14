/* collect-supplier-count2 */
// 상품담기 왼쪽 공급사 목록에 전체상품 개수를 붙입니다.
// 개수는 상품 목록이 ‘전체 N개’로 보여주는 그 카탈로그 수입니다.
// 분류 상품을 불러온 뒤의 cafe24CatalogItems 길이입니다.
// 그 공급사 목록을 아직 불러오기 전이면 숫자를 그리지 않습니다.
// 이미 불러온 마스터상품 수(wholesaleProductCount)는 쓰지 않습니다.
// 오너클랜은 상품이 너무 많아 개수를 붙이지 않습니다.

function supplierTotalCountLabel(count) {
  if (typeof count !== "number" || !Number.isFinite(count) || count < 0) return "";
  return `${Math.trunc(count).toLocaleString("ko-KR")}개`;
}

function shopCatalogTotal(state) {
  if (!state || state.searchMode) return null;
  if (!state.selectedCategory || state.loadedCategory !== state.selectedCategory) return null;
  const id = String(state.loadedFor || "");
  if (!id || !Array.isArray(state.items)) return null;
  return { id, count: state.items.length };
}

function isOwnerclanSupplier(id, rows, name) {
  const key = String(id || "");
  const label = String(name || "").trim();
  if (label === "오너클랜" || key === "ownerclan") return true;
  const list = Array.isArray(rows) ? rows : [];
  const row = list.find((item) => item && String(item.id || "") === key);
  return Boolean(row && row.type === "ownerclan");
}

function paintCollectSupplierCounts(tree, options) {
  if (!tree) return;
  const countOf = options && options.countOf;
  const skip = options && options.skip;
  tree.querySelectorAll(".collect-supplier-item").forEach((button) => {
    const existing = button.querySelector(".collect-supplier-tag");
    const id = button.dataset.id || "";
    const nameNode = button.querySelector(".collect-supplier-name");
    const visibleName = nameNode ? nameNode.textContent : button.textContent;
    if (typeof skip === "function") {
      let hidden = false;
      try {
        hidden = Boolean(skip(id, visibleName));
      } catch (error) {
        hidden = false;
      }
      if (hidden) {
        if (existing) existing.remove();
        return;
      }
    }
    if (typeof countOf !== "function") {
      if (existing) existing.remove();
      return;
    }
    let count = null;
    try {
      count = countOf(button.dataset.id || "");
    } catch (error) {
      count = null;
    }
    const text = supplierTotalCountLabel(count);
    if (!text) {
      if (existing) existing.remove();
      return;
    }
    let name = button.querySelector(".collect-supplier-name");
    if (!name) {
      const label = button.textContent;
      button.textContent = "";
      name = document.createElement("span");
      name.className = "collect-supplier-name";
      name.textContent = label;
      button.append(name);
    }
    const tag = existing || document.createElement("span");
    tag.className = "collect-supplier-tag";
    tag.textContent = text;
    tag.title = `전체상품 ${text}`;
    if (!existing) button.append(tag);
  });
}

function readShopCatalog() {
  return {
    searchMode: typeof cafe24SearchMode !== "undefined" && Boolean(cafe24SearchMode),
    selectedCategory: typeof cafe24SelectedCategory !== "undefined" ? cafe24SelectedCategory : "",
    loadedCategory: typeof cafe24CatalogLoadedCategory !== "undefined" ? cafe24CatalogLoadedCategory : "",
    loadedFor: typeof cafe24CatalogLoadedFor !== "undefined" ? cafe24CatalogLoadedFor : "",
    items: typeof cafe24CatalogItems !== "undefined" ? cafe24CatalogItems : null,
  };
}

function readSupplierRows() {
  return typeof wholesalers !== "undefined" && Array.isArray(wholesalers) ? wholesalers : [];
}

function installCollectSupplierCounts(hooks) {
  const api = hooks || {
    document,
    getRender() {
      return typeof renderCollectSupplierTree === "function" ? renderCollectSupplierTree : null;
    },
    setRender(fn) {
      renderCollectSupplierTree = fn;
    },
    getRenderCatalog() {
      return typeof renderCafe24Catalog === "function" ? renderCafe24Catalog : null;
    },
    setRenderCatalog(fn) {
      renderCafe24Catalog = fn;
    },
    tree() {
      return document.getElementById("collectSupplierTree");
    },
    shopCatalog: readShopCatalog,
    supplierRows: readSupplierRows,
  };
  if (api.getRender && api.getRender() && api.getRender().collectSupplierCountHook) return;

  const doc = api.document;
  if (doc && doc.head && !doc.getElementById("collectSupplierCountStyle")) {
    const style = doc.createElement("style");
    style.id = "collectSupplierCountStyle";
    style.textContent = [
      ".collect-supplier-item .collect-supplier-name {",
      "  flex: 1 1 auto;",
      "  min-width: 0;",
      "  overflow: hidden;",
      "  text-overflow: ellipsis;",
      "  white-space: nowrap;",
      "}",
    ].join("\n");
    doc.head.appendChild(style);
  }

  const counts = new Map();

  function supplierRows() {
    return api.supplierRows ? api.supplierRows() : [];
  }

  function skipSupplier(id, name) {
    return isOwnerclanSupplier(id, supplierRows(), name);
  }

  function rememberVisibleTotals() {
    const shop = shopCatalogTotal(api.shopCatalog ? api.shopCatalog() : null);
    if (shop && !isOwnerclanSupplier(shop.id, supplierRows(), "")) counts.set(shop.id, shop.count);
  }

  function countOf(id) {
    const key = String(id || "");
    if (isOwnerclanSupplier(key, supplierRows(), "")) return null;
    if (!counts.has(key)) return null;
    return counts.get(key);
  }

  function paintTree() {
    rememberVisibleTotals();
    paintCollectSupplierCounts(api.tree(), { countOf, skip: skipSupplier });
  }

  function wrap(getFn, setFn) {
    if (typeof getFn !== "function" || typeof setFn !== "function") return;
    const current = getFn();
    if (typeof current !== "function" || current.collectSupplierCountHook) return;
    const wrapped = function () {
      const result = current.apply(this, arguments);
      try {
        paintTree();
      } catch (error) {
        /* 개수 표시가 실패해도 목록은 그대로 둡니다 */
      }
      return result;
    };
    wrapped.collectSupplierCountHook = true;
    Object.assign(wrapped, current);
    setFn(wrapped);
  }

  wrap(api.getRender, api.setRender);
  wrap(api.getRenderCatalog, api.setRenderCatalog);
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    supplierTotalCountLabel,
    shopCatalogTotal,
    isOwnerclanSupplier,
    paintCollectSupplierCounts,
    installCollectSupplierCounts,
  };
}

if (typeof document !== "undefined") installCollectSupplierCounts();
