const assert = require("assert");
const {
  supplierTotalCountLabel,
  parseSettingsCount,
  isOwnerclanSupplier,
  settingsProductCount,
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

const settingsRows = [
  { name: "PANASONIC", count: "92" },
  { name: "SONY", count: "15" },
  { name: "빈공급사", count: "0" },
  { name: "미로딩", count: "" },
  { name: "오너클랜", count: "2400" },
  { name: "다른오너", count: "9999" },
];
const grid = buildSettingsGrid(settingsRows);
assert.strictEqual(settingsProductCount(grid, "PANASONIC"), 92);
assert.strictEqual(settingsProductCount(grid, "SONY"), 15);
assert.strictEqual(settingsProductCount(grid, "빈공급사"), 0);
assert.strictEqual(settingsProductCount(grid, "미로딩"), null);
assert.strictEqual(settingsProductCount(grid, "없는공급사"), null);
assert.strictEqual(settingsProductCount(grid, "오너클랜"), 2400);
assert.strictEqual(settingsProductCount(null, "PANASONIC"), null);

const tree = createElement("div");
drawList(tree);
paintCollectSupplierCounts(tree, {
  countOf(id) {
    const item = suppliers.find((row) => row.id === id);
    if (!item || isOwnerclanSupplier(id, suppliers, item.name)) return null;
    return settingsProductCount(grid, item.name);
  },
  skip(id, name) {
    return isOwnerclanSupplier(id, suppliers, name);
  },
});
assert.deepStrictEqual(
  tree.querySelectorAll(".collect-supplier-tag").map((tag) => ({
    text: tag.textContent,
    title: tag.title,
  })),
  [
    { text: "92개", title: "전체상품 92개" },
    { text: "15개", title: "전체상품 15개" },
    { text: "0개", title: "전체상품 0개" },
  ],
);
assert.strictEqual(
  tree.querySelectorAll(".collect-supplier-item").find((button) => button.dataset.id === "ownerclan").querySelector(".collect-supplier-tag"),
  null,
);
assert.strictEqual(
  tree.querySelectorAll(".collect-supplier-item").find((button) => button.dataset.id === "oc-custom").querySelector(".collect-supplier-tag"),
  null,
);
assert.strictEqual(
  tree.querySelectorAll(".collect-supplier-item").find((button) => button.dataset.id === "unloaded").querySelector(".collect-supplier-tag"),
  null,
);

async function main() {
  let liveTree = createElement("div");
  let liveGrid = buildSettingsGrid([]);
  let renderCollectSupplierTree = function () {
    drawList(liveTree);
  };
  let renderWholesalerSheet = function () {
    liveGrid = buildSettingsGrid(settingsRows);
  };
  let styleNode = null;
  let forbiddenReads = 0;
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
    wholesaleProductCount() {
      forbiddenReads += 1;
      return 4;
    },
    cafe24CatalogItems: Array.from({ length: 3 }),
  });

  renderCollectSupplierTree();
  assert.strictEqual(liveTree.querySelectorAll(".collect-supplier-tag").length, 0);

  renderWholesalerSheet();
  assert.deepStrictEqual(
    liveTree.querySelectorAll(".collect-supplier-tag").map((tag) => tag.textContent),
    ["92개", "15개", "0개"],
  );
  assert.strictEqual(forbiddenReads, 0);
  assert.strictEqual(
    liveTree.querySelectorAll(".collect-supplier-item").find((button) => button.dataset.id === "ownerclan").textContent,
    "오너클랜",
  );

  console.log("collect supplier count tests ok");
}

main();
