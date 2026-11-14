/* collect-supplier-count3 */
// 상품담기 왼쪽 공급사 목록에 전체상품 개수를 붙입니다.
// 개수는 공급처설정 표의 상품수 칸에 이미 나와 있는 숫자입니다.
// 그 칸이 없거나 비어 있으면 숫자를 만들지 않습니다.
// 오너클랜은 상품이 너무 많아 개수를 붙이지 않습니다.

function supplierTotalCountLabel(count) {
  if (typeof count !== "number" || !Number.isFinite(count) || count < 0) return "";
  return `${Math.trunc(count).toLocaleString("ko-KR")}개`;
}

function parseSettingsCount(text) {
  const raw = String(text || "").trim().replace(/개$/, "").replace(/,/g, "");
  if (!/^\d+$/.test(raw)) return null;
  const count = Number(raw);
  if (!Number.isFinite(count) || count < 0) return null;
  return count;
}

function isOwnerclanSupplier(id, rows, name) {
  const key = String(id || "");
  const label = String(name || "").trim();
  if (label === "오너클랜" || key === "ownerclan") return true;
  const list = Array.isArray(rows) ? rows : [];
  const row = list.find((item) => item && String(item.id || "") === key);
  return Boolean(row && row.type === "ownerclan");
}

function settingsProductCount(grid, supplierName) {
  if (!grid || typeof grid.querySelectorAll !== "function") return null;
  const headers = [...grid.querySelectorAll("thead th")];
  const nameIndex = headers.findIndex((th) => String(th.textContent || "").trim() === "공급처");
  const countIndex = headers.findIndex((th) => String(th.textContent || "").trim() === "상품수");
  if (nameIndex < 0 || countIndex < 0) return null;
  const wanted = String(supplierName || "").trim();
  if (!wanted) return null;
  const rows = grid.querySelectorAll("tbody tr");
  for (const row of rows) {
    const cells = row.querySelectorAll("td");
    const name = cells[nameIndex] ? String(cells[nameIndex].textContent || "").trim() : "";
    if (name !== wanted) continue;
    const cell = cells[countIndex];
    return parseSettingsCount(cell ? cell.textContent : "");
  }
  return null;
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
      count = countOf(id);
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
    getRenderSheet() {
      return typeof renderWholesalerSheet === "function" ? renderWholesalerSheet : null;
    },
    setRenderSheet(fn) {
      renderWholesalerSheet = fn;
    },
    tree() {
      return document.getElementById("collectSupplierTree");
    },
    supplierRows: readSupplierRows,
    settingsGrid() {
      return document.getElementById("wholesaleGrid");
    },
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

  function supplierRows() {
    return api.supplierRows ? api.supplierRows() : [];
  }

  function supplierRecord(id) {
    const key = String(id || "");
    return supplierRows().find((item) => item && String(item.id || "") === key) || null;
  }

  function skipSupplier(id, name) {
    const record = supplierRecord(id);
    return isOwnerclanSupplier(id, supplierRows(), record ? record.name : name);
  }

  function countOf(id) {
    const record = supplierRecord(id);
    const name = record ? record.name : "";
    if (isOwnerclanSupplier(id, supplierRows(), name)) return null;
    const grid = api.settingsGrid ? api.settingsGrid() : null;
    return settingsProductCount(grid, name);
  }

  function paintTree() {
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
  wrap(api.getRenderSheet, api.setRenderSheet);
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    supplierTotalCountLabel,
    parseSettingsCount,
    isOwnerclanSupplier,
    settingsProductCount,
    paintCollectSupplierCounts,
    installCollectSupplierCounts,
  };
}

if (typeof document !== "undefined") installCollectSupplierCounts();
