/* collect-supplier-count4 */
// 공급처설정 상품수는 이미 담아 둔 마스터상품 수라 공급사 전체 상품 수와 다릅니다.
// 전체 수는 분류 없이 연 공급사 카탈로그 응답의 count 입니다.
// 그 수를 상품수 칸에 넣은 뒤에만 상품담기 목록에 같은 숫자를 붙입니다.
// 카탈로그 count 가 아직 없으면 칸을 비우고, 숫자를 만들지 않습니다.
// 오너클랜은 상품이 너무 많아 상품담기에 개수를 붙이지 않습니다.

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

function catalogCountPath(id) {
  return `/api/wholesalers/${encodeURIComponent(String(id || ""))}/catalog`;
}

function catalogTotal(data) {
  if (!data || typeof data !== "object" || !Object.prototype.hasOwnProperty.call(data, "count")) return null;
  const count = data.count;
  if (typeof count === "number") {
    if (!Number.isFinite(count) || count < 0) return null;
    return Math.trunc(count);
  }
  return parseSettingsCount(count);
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
  const found = settingsCountCell(grid, supplierName);
  if (!found) return null;
  return parseSettingsCount(found.cell.textContent);
}

function settingsCountCell(grid, supplierName) {
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
    if (!cells[countIndex]) return null;
    return { cell: cells[countIndex] };
  }
  return null;
}

function writeSettingsCount(cell, count) {
  const text = count == null ? "" : String(Math.trunc(count));
  cell.textContent = text;
  if ("title" in cell) cell.title = text;
}

function correctSettingsProductCounts(grid, rows, countOfId) {
  if (!grid || typeof grid.querySelectorAll !== "function") return;
  const headers = [...grid.querySelectorAll("thead th")];
  const nameIndex = headers.findIndex((th) => String(th.textContent || "").trim() === "공급처");
  const countIndex = headers.findIndex((th) => String(th.textContent || "").trim() === "상품수");
  if (nameIndex < 0 || countIndex < 0) return;
  const list = Array.isArray(rows) ? rows : [];
  grid.querySelectorAll("tbody tr").forEach((row) => {
    const cells = row.querySelectorAll("td");
    const cell = cells[countIndex];
    if (!cell) return;
    const name = cells[nameIndex] ? String(cells[nameIndex].textContent || "").trim() : "";
    const record = list.find((item) => item && String(item.name || "").trim() === name);
    if (!record || isOwnerclanSupplier(record.id, list, record.name)) {
      writeSettingsCount(cell, null);
      return;
    }
    const count = typeof countOfId === "function" ? countOfId(record.id) : null;
    writeSettingsCount(cell, count == null ? null : count);
  });
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
  const known = new Map();
  const pending = new Set();
  const failed = new Set();
  const api = Object.assign({
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
    fetchCatalog(supplier) {
      if (typeof globalThis.api !== "function") return Promise.resolve(null);
      const options = { quiet: true };
      if (typeof AbortSignal !== "undefined" && typeof AbortSignal.timeout === "function") {
        options.signal = AbortSignal.timeout(120000);
      }
      return globalThis.api(catalogCountPath(supplier && supplier.id), options);
    },
  }, hooks || {});
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
    if (!record || isOwnerclanSupplier(id, supplierRows(), record.name)) return null;
    const grid = api.settingsGrid ? api.settingsGrid() : null;
    return settingsProductCount(grid, record.name);
  }

  function publish() {
    const grid = api.settingsGrid ? api.settingsGrid() : null;
    correctSettingsProductCounts(grid, supplierRows(), (id) => (known.has(String(id || "")) ? known.get(String(id || "")) : null));
    paintCollectSupplierCounts(api.tree ? api.tree() : null, { countOf, skip: skipSupplier });
  }

  function loadOne(supplier) {
    const id = String(supplier && supplier.id || "");
    if (!id || known.has(id) || pending.has(id) || failed.has(id)) return Promise.resolve();
    if (isOwnerclanSupplier(id, supplierRows(), supplier && supplier.name)) return Promise.resolve();
    if (typeof api.fetchCatalog !== "function") return Promise.resolve();
    pending.add(id);
    return Promise.resolve()
      .then(() => api.fetchCatalog(supplier))
      .then((data) => {
        const count = catalogTotal(data);
        if (count == null) failed.add(id);
        else known.set(id, count);
      })
      .catch(() => {
        failed.add(id);
      })
      .finally(() => {
        pending.delete(id);
        try {
          publish();
        } catch (error) {
          /* 개수 표시가 실패해도 목록은 그대로 둡니다 */
        }
      });
  }

  function loadMissing() {
    supplierRows().forEach((row) => {
      loadOne(row);
    });
  }

  function wrap(getFn, setFn) {
    if (typeof getFn !== "function" || typeof setFn !== "function") return;
    const current = getFn();
    if (typeof current !== "function" || current.collectSupplierCountHook) return;
    const wrapped = function () {
      const result = current.apply(this, arguments);
      try {
        publish();
        loadMissing();
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
  try {
    publish();
    loadMissing();
  } catch (error) {
    /* 처음 그릴 공급사 표가 없어도 다음 그리기에서 다시 합니다 */
  }
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    supplierTotalCountLabel,
    parseSettingsCount,
    catalogCountPath,
    catalogTotal,
    isOwnerclanSupplier,
    settingsProductCount,
    correctSettingsProductCounts,
    paintCollectSupplierCounts,
    installCollectSupplierCounts,
  };
}

if (typeof document !== "undefined") installCollectSupplierCounts();
