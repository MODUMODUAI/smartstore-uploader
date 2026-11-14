const assert = require("assert");
const {
  supplierTotalCountLabel,
  parseSettingsCount,
  catalogCountPath,
  catalogTotal,
  isOwnerclanSupplier,
  settingsProductCount,
  correctSettingsProductCounts,
  paintCollectSupplierCounts,
  installCollectSupplierCounts,
} = require("./collect_supplier_count.js");

assert.strictEqual(supplierTotalCountLabel(0), "0개");
assert.strictEqual(supplierTotalCountLabel(92), "92개");
assert.strictEqual(supplierTotalCountLabel(12345), "12,345개");
assert.strictEqual(supplierTotalCountLabel(null), "");
assert.strictEqual(supplierTotalCountLabel(undefined), "");

assert.strictEqual(parseSettingsCount("92"), 92);
assert.strictEqual(parseSettingsCount("1,234"), 1234);
assert.strictEqual(parseSettingsCount("0"), 0);
assert.strictEqual(parseSettingsCount(" 15개"), 15);
assert.strictEqual(parseSettingsCount(""), null);
assert.strictEqual(parseSettingsCount("   "), null);
assert.strictEqual(parseSettingsCount("없음"), null);

assert.strictEqual(catalogCountPath("panasonic"), "/api/wholesalers/panasonic/catalog");
assert.strictEqual(catalogCountPath("a/b"), "/api/wholesalers/a%2Fb/catalog");
assert.strictEqual(catalogCountPath("panasonic").includes("category"), false);

assert.strictEqual(catalogTotal({ count: 92, items: [1, 2, 3] }), 92);
assert.strictEqual(catalogTotal({ count: 0 }), 0);
assert.strictEqual(catalogTotal({ count: "15" }), 15);
assert.strictEqual(catalogTotal({ count: "1,234" }), 1234);
assert.strictEqual(catalogTotal({ items: [1, 2, 3, 4] }), null);
assert.strictEqual(catalogTotal({ count: -1 }), null);
assert.strictEqual(catalogTotal(null), null);

assert.strictEqual(isOwnerclanSupplier("ownerclan", [], ""), true);
assert.strictEqual(isOwnerclanSupplier("shop", [], "오너클랜"), true);
assert.strictEqual(isOwnerclanSupplier("oc-custom", [{ id: "oc-custom", type: "ownerclan", name: "다른이름" }], ""), true);
assert.strictEqual(isOwnerclanSupplier("panasonic", [{ id: "panasonic", type: "cafe24", name: "PANASONIC" }], "PANASONIC"), false);

function createElement(tag) {
  const node = {
    tagName: String(tag || "").toUpperCase(),
    id: "",
    className: "",
    title: "",
    hidden: false,
    dataset: {},
    children: [],
    parent: null,
    _text: "",
  };
  Object.defineProperty(node, "textContent", {
    get() {
      if (node.children.length) return node.children.map((child) => child.textContent).join("");
      return node._text;
    },
    set(value) {
      node._text = String(value ?? "");
      node.children.forEach((child) => {
        child.parent = null;
      });
      node.children = [];
    },
  });
  Object.defineProperty(node, "innerHTML", {
    get() { return ""; },
    set() {
      node.children.forEach((child) => {
        child.parent = null;
      });
      node.children = [];
      node._text = "";
    },
  });
  node.append = (...kids) => {
    kids.forEach((kid) => node.appendChild(kid));
  };
  node.appendChild = (kid) => {
    if (kid.parent) kid.parent.children = kid.parent.children.filter((child) => child !== kid);
    kid.parent = node;
    node.children.push(kid);
    node._text = "";
    return kid;
  };
  node.remove = () => {
    if (!node.parent) return;
    node.parent.children = node.parent.children.filter((child) => child !== node);
    node.parent = null;
  };
  node.addEventListener = () => {};
  const matches = (el, selector) => {
    if (selector.startsWith(".")) return el.className.split(/\s+/).includes(selector.slice(1));
    return el.tagName === selector.toUpperCase();
  };
  const collect = (root, selectors) => {
    if (!selectors.length) return [root];
    const [head, ...rest] = selectors;
    const found = [];
    const walk = (el) => {
      el.children.forEach((child) => {
        if (matches(child, head)) found.push(child);
        walk(child);
      });
    };
    walk(root);
    if (!rest.length) return found;
    return found.flatMap((el) => collect(el, rest));
  };
  node.querySelectorAll = (sel) => collect(node, String(sel).trim().split(/\s+/));
  node.querySelector = (sel) => node.querySelectorAll(sel)[0] || null;
  return node;
}

global.document = { createElement };

function buttonFor(item) {
  const button = createElement("button");
  button.className = "collect-supplier-item";
  button.dataset.id = item.id;
  button.textContent = item.name;
  return button;
}

const suppliers = [
  { id: "panasonic", name: "PANASONIC", type: "cafe24" },
  { id: "sony", name: "SONY", type: "cafe24" },
  { id: "empty", name: "빈공급사", type: "cafe24" },
  { id: "unloaded", name: "미로딩", type: "cafe24" },
  { id: "missing", name: "없는공급사", type: "cafe24" },
  { id: "ownerclan", name: "오너클랜", type: "ownerclan" },
  { id: "oc-custom", name: "다른오너", type: "ownerclan" },
];

function drawList(tree) {
  tree.textContent = "";
  suppliers.forEach((item) => tree.append(buttonFor(item)));
}

function headerCell(text) {
  const cell = createElement("th");
  cell.textContent = text;
  return cell;
}

function dataCell(text) {
  const cell = createElement("td");
  cell.textContent = text;
  return cell;
}

function buildSettingsGrid(rows) {
  const grid = createElement("table");
  grid.id = "wholesaleGrid";
  const headRow = createElement("tr");
  ["공급처", "사이트", "유형", "아이디", "상품수", "사용", "메모"].forEach((label) => {
    headRow.append(headerCell(label));
  });
  const thead = createElement("thead");
  thead.append(headRow);
  const tbody = createElement("tbody");
  tbody.id = "wholesaleTable";
  rows.forEach((item) => {
    const row = createElement("tr");
    row.append(
      dataCell(item.name),
      dataCell(item.url || ""),
      dataCell(item.type || ""),
      dataCell(item.login || ""),
      dataCell(item.count),
      dataCell("사용"),
      dataCell(""),
    );
    tbody.append(row);
  });
  grid.append(thead, tbody);
  return grid;
}

function countColumn(grid) {
  return [...grid.querySelectorAll("tbody tr")].map((row) => row.querySelectorAll("td")[4].textContent);
}

const wrongCounts = [
  { name: "PANASONIC", count: "4" },
  { name: "SONY", count: "100" },
  { name: "빈공급사", count: "1" },
  { name: "미로딩", count: "2" },
  { name: "없는공급사", count: "3" },
  { name: "오너클랜", count: "7" },
  { name: "다른오너", count: "8" },
];

correctSettingsProductCounts(buildSettingsGrid(wrongCounts), suppliers, (id) => {
  if (id === "panasonic") return 92;
  if (id === "sony") return 15;
  if (id === "empty") return 0;
  return null;
});
const corrected = buildSettingsGrid(wrongCounts);
correctSettingsProductCounts(corrected, suppliers, (id) => {
  if (id === "panasonic") return 92;
  if (id === "sony") return 15;
  if (id === "empty") return 0;
  return null;
});
assert.deepStrictEqual(countColumn(corrected), ["92", "15", "0", "", "", "", ""]);
assert.strictEqual(settingsProductCount(corrected, "PANASONIC"), 92);
assert.strictEqual(settingsProductCount(corrected, "미로딩"), null);
assert.strictEqual(settingsProductCount(corrected, "오너클랜"), null);

const tree = createElement("div");
drawList(tree);
paintCollectSupplierCounts(tree, {
  countOf(id) {
    const item = suppliers.find((row) => row.id === id);
    if (!item || isOwnerclanSupplier(id, suppliers, item.name)) return null;
    return settingsProductCount(corrected, item.name);
  },
  skip(id, name) {
    return isOwnerclanSupplier(id, suppliers, name);
  },
});
assert.deepStrictEqual(
  tree.querySelectorAll(".collect-supplier-tag").map((tag) => tag.textContent),
  ["92개", "15개", "0개"],
);

async function main() {
  let liveTree = createElement("div");
  let liveGrid = buildSettingsGrid([]);
  let renderCollectSupplierTree = function () {
    drawList(liveTree);
  };
  let renderWholesalerSheet = function () {
    liveGrid = buildSettingsGrid(wrongCounts);
  };
  let styleNode = null;
  let releaseFetch;
  const gate = new Promise((resolve) => {
    releaseFetch = resolve;
  });
  const fetched = [];
  const doc = {
    head: { appendChild(node) { styleNode = node; } },
    getElementById(id) {
      if (id === "collectSupplierTree") return liveTree;
      if (id === "wholesaleGrid") return liveGrid;
      if (id === "collectSupplierCountStyle") return styleNode;
      return null;
    },
    createElement,
  };

  installCollectSupplierCounts({
    document: doc,
    getRender: () => renderCollectSupplierTree,
    setRender: (fn) => { renderCollectSupplierTree = fn; },
    getRenderSheet: () => renderWholesalerSheet,
    setRenderSheet: (fn) => { renderWholesalerSheet = fn; },
    tree: () => liveTree,
    supplierRows: () => suppliers,
    settingsGrid: () => liveGrid,
    fetchCatalog(supplier) {
      fetched.push(catalogCountPath(supplier.id));
      return gate.then(() => {
        if (supplier.id === "panasonic") return { count: 92, items: [1, 2, 3] };
        if (supplier.id === "sony") return { count: 15 };
        if (supplier.id === "empty") return { count: 0 };
        if (supplier.id === "unloaded") return { items: [1, 2, 3, 4] };
        throw new Error("catalog failed");
      });
    },
  });

  renderCollectSupplierTree();
  assert.strictEqual(liveTree.querySelectorAll(".collect-supplier-tag").length, 0);

  renderWholesalerSheet();
  assert.deepStrictEqual(countColumn(liveGrid), ["", "", "", "", "", "", ""]);
  assert.strictEqual(liveTree.querySelectorAll(".collect-supplier-tag").length, 0);
  assert.deepStrictEqual(fetched.filter((path) => path.includes("ownerclan") || path.includes("oc-custom")), []);
  assert.ok(fetched.every((path) => path.startsWith("/api/wholesalers/") && path.endsWith("/catalog") && !path.includes("category")));

  releaseFetch();
  await new Promise((resolve) => setImmediate(resolve));

  assert.deepStrictEqual(countColumn(liveGrid), ["92", "15", "0", "", "", "", ""]);
  assert.deepStrictEqual(
    liveTree.querySelectorAll(".collect-supplier-tag").map((tag) => tag.textContent),
    ["92개", "15개", "0개"],
  );
  assert.strictEqual(
    liveTree.querySelectorAll(".collect-supplier-item").find((button) => button.dataset.id === "ownerclan").textContent,
    "오너클랜",
  );
  assert.strictEqual(settingsProductCount(liveGrid, "PANASONIC"), 92);
  assert.strictEqual(settingsProductCount(liveGrid, "미로딩"), null);

  const calls = [];
  global.api = (path, options) => {
    calls.push({ path, quiet: options && options.quiet });
    return Promise.resolve({ count: 3 });
  };
  let soloGrid = buildSettingsGrid([{ name: "SOLO", count: "9" }]);
  let soloTree = createElement("div");
  const solo = [{ id: "solo", name: "SOLO", type: "cafe24" }];
  let renderSoloSheet = function () {
    soloGrid = buildSettingsGrid([{ name: "SOLO", count: "9" }]);
  };
  let renderSoloTree = function () {
    soloTree.textContent = "";
    soloTree.append(buttonFor(solo[0]));
  };
  installCollectSupplierCounts({
    document: {
      head: { appendChild() {} },
      getElementById(id) {
        if (id === "collectSupplierTree") return soloTree;
        if (id === "wholesaleGrid") return soloGrid;
        return null;
      },
      createElement,
    },
    getRender: () => renderSoloTree,
    setRender: (fn) => { renderSoloTree = fn; },
    getRenderSheet: () => renderSoloSheet,
    setRenderSheet: (fn) => { renderSoloSheet = fn; },
    tree: () => soloTree,
    supplierRows: () => solo,
    settingsGrid: () => soloGrid,
  });
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepStrictEqual(calls.map((call) => call.path), ["/api/wholesalers/solo/catalog"]);
  assert.strictEqual(calls[0].quiet, true);
  assert.strictEqual(settingsProductCount(soloGrid, "SOLO"), 3);
  renderSoloTree();
  renderSoloSheet();
  assert.deepStrictEqual(countColumn(soloGrid), ["3"]);
  assert.strictEqual(soloTree.querySelector(".collect-supplier-tag").textContent, "3개");

  console.log("collect supplier count tests ok");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
