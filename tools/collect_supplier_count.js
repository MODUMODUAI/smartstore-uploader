/* collect-supplier-count1 */
// 상품담기 왼쪽 공급사 목록에 전체상품 개수를 붙입니다.
// 개수는 공급처 표의 상품수와 같습니다. wholesaleProductCount 가 세는,
// 이미 불러온 마스터상품 수입니다. 상품 목록이 아직 바뀌기 전이면 숫자를 그리지 않습니다.

function supplierTotalCountLabel(count, loaded) {
  if (!loaded) return "";
  if (typeof count !== "number" || !Number.isFinite(count) || count < 0) return "";
  return `${Math.trunc(count).toLocaleString("ko-KR")}개`;
}

function paintCollectSupplierCounts(tree, options) {
  if (!tree) return;
  const loaded = Boolean(options && options.loaded);
  const countOf = options && options.countOf;
  tree.querySelectorAll(".collect-supplier-item").forEach((button) => {
    const existing = button.querySelector(".collect-supplier-tag");
    if (!loaded || typeof countOf !== "function") {
      if (existing) existing.remove();
      return;
    }
    let count = null;
    try {
      count = countOf(button.dataset.id || "");
    } catch (error) {
      count = null;
    }
    const text = supplierTotalCountLabel(count, true);
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

function installCollectSupplierCounts(hooks) {
  const api = hooks || {
    document,
    readProducts() {
      return products;
    },
    countOf(id) {
      return typeof wholesaleProductCount === "function" ? wholesaleProductCount(id) : null;
    },
    getRender() {
      return typeof renderCollectSupplierTree === "function" ? renderCollectSupplierTree : null;
    },
    setRender(fn) {
      renderCollectSupplierTree = fn;
    },
    getRenderSheets() {
      return typeof renderSheets === "function" ? renderSheets : null;
    },
    setRenderSheets(fn) {
      renderSheets = fn;
    },
    getLoadProducts() {
      return typeof loadProducts === "function" ? loadProducts : null;
    },
    setLoadProducts(fn) {
      loadProducts = fn;
    },
    viewOpen() {
      const view = document.getElementById("viewCollect");
      return Boolean(view && !view.hidden);
    },
    tree() {
      return document.getElementById("collectSupplierTree");
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

  let beforeLoad = null;
  try {
    beforeLoad = api.readProducts();
  } catch (error) {
    beforeLoad = null;
  }
  let ready = Array.isArray(beforeLoad) && beforeLoad.length > 0;

  function loadedNow() {
    if (ready) return true;
    let current = null;
    try {
      current = api.readProducts();
    } catch (error) {
      return false;
    }
    if (current !== beforeLoad) ready = true;
    return ready;
  }

  function paintTree() {
    paintCollectSupplierCounts(api.tree(), {
      loaded: loadedNow(),
      countOf: api.countOf,
    });
  }

  function refreshOpenList() {
    if (!api.viewOpen()) return;
    const render = api.getRender();
    if (typeof render === "function") render();
  }

  const render = api.getRender();
  if (typeof render === "function") {
    const wrapped = function () {
      const result = render.apply(this, arguments);
      try {
        paintTree();
      } catch (error) {
        /* 개수 표시가 실패해도 공급사 목록은 그대로 둡니다 */
      }
      return result;
    };
    wrapped.collectSupplierCountHook = true;
    Object.assign(wrapped, render);
    api.setRender(wrapped);
  }

  // 지역 이름을 renderSheets/loadProducts 로 두면, 기본 훅이 그 이름을 찾을 때
  // 전역 함수 대신 초기화 중인 지역 변수를 봐서 감싸기가 실패합니다.
  const currentSheets = api.getRenderSheets();
  if (typeof currentSheets === "function" && !currentSheets.collectSupplierCountHook) {
    const wrappedSheets = function () {
      const result = currentSheets.apply(this, arguments);
      const wasReady = ready;
      if (!wasReady && loadedNow()) {
        try {
          refreshOpenList();
        } catch (error) {
          /* 목록을 다시 그리지 못해도 상품 목록 갱신은 막지 않습니다 */
        }
      }
      return result;
    };
    wrappedSheets.collectSupplierCountHook = true;
    Object.assign(wrappedSheets, currentSheets);
    api.setRenderSheets(wrappedSheets);
  }

  const currentLoad = api.getLoadProducts();
  if (typeof currentLoad === "function" && !currentLoad.collectSupplierCountHook) {
    const wrappedLoad = async function () {
      const result = await currentLoad.apply(this, arguments);
      ready = true;
      try {
        refreshOpenList();
      } catch (error) {
        /* 개수는 다음에 목록을 그릴 때 붙습니다 */
      }
      return result;
    };
    wrappedLoad.collectSupplierCountHook = true;
    Object.assign(wrappedLoad, currentLoad);
    api.setLoadProducts(wrappedLoad);
  }
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { supplierTotalCountLabel, paintCollectSupplierCounts, installCollectSupplierCounts };
}

if (typeof document !== "undefined") installCollectSupplierCounts();
