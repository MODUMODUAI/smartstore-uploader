const assert = require("assert");
const {
  supplierTotalCountLabel,
  shopCatalogTotal,
  isOwnerclanSupplier,
  paintCollectSupplierCounts,
  installCollectSupplierCounts,
} = require("./collect_supplier_count.js");

assert.strictEqual(supplierTotalCountLabel(0), "0개");
assert.strictEqual(supplierTotalCountLabel(1), "1개");
assert.strictEqual(supplierTotalCountLabel(92), "92개");
assert.strictEqual(supplierTotalCountLabel(12345), "12,345개");
assert.strictEqual(supplierTotalCountLabel(1.8), "1개");
assert.strictEqual(supplierTotalCountLabel(-1), "");
assert.strictEqual(supplierTotalCountLabel(Number.NaN), "");
assert.strictEqual(supplierTotalCountLabel(null), "");
assert.strictEqual(supplierTotalCountLabel(undefined), "");

assert.strictEqual(shopCatalogTotal(null), null);
assert.strictEqual(shopCatalogTotal({
  searchMode: false,
  selectedCategory: "camera",
  loadedCategory: "",
  loadedFor: "panasonic",
  items: Array.from({ length: 92 }),
}), null);
assert.strictEqual(shopCatalogTotal({
  searchMode: true,
  selectedCategory: "camera",
  loadedCategory: "camera",
  loadedFor: "panasonic",
  items: Array.from({ length: 5 }),
}), null);
assert.deepStrictEqual(shopCatalogTotal({
  searchMode: false,
  selectedCategory: "camera",
  loadedCategory: "camera",
  loadedFor: "panasonic",
  items: Array.from({ length: 92 }),
}), { id: "panasonic", count: 92 });
assert.deepStrictEqual(shopCatalogTotal({
  searchMode: false,
  selectedCategory: "lens",
  loadedCategory: "lens",
  loadedFor: "sony",
  items: [],
}), { id: "sony", count: 0 });

assert.strictEqual(isOwnerclanSupplier("ownerclan", [], ""), true);
assert.strictEqual(isOwnerclanSupplier("shop", [], "오너클랜"), true);
assert.strictEqual(isOwnerclanSupplier("oc-custom", [{ id: "oc-custom", type: "ownerclan", name: "다른이름" }], ""), true);
assert.strictEqual(isOwnerclanSupplier("panasonic", [{ id: "panasonic", type: "cafe24", name: "PANASONIC" }], "PANASONIC"), false);
assert.strictEqual(isOwnerclanSupplier("sony", [], "SONY"), false);

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
      node._text = String(value);
      node.children.forEach((child) => {
        child.parent = null;
      });
      node.children = [];
    },
  });
  node.append = (...kids) => {
    kids.forEach((kid) => {
      if (kid.parent) kid.parent.children = kid.parent.children.filter((child) => child !== kid);
      kid.parent = node;
      node.children.push(kid);
      node._text = "";
    });
  };
  node.remove = () => {
    if (!node.parent) return;
    node.parent.children = node.parent.children.filter((child) => child !== node);
    node.parent = null;
  };
  node.querySelectorAll = (sel) => {
    const out = [];
    const walk = (el) => {
      el.children.forEach((child) => {
        if (child.className.split(/\s+/).includes(sel.slice(1))) out.push(child);
        walk(child);
      });
    };
    if (sel.startsWith(".")) walk(node);
    return out;
  };
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
  { id: "panasonic", name: "PANASONIC" },
  { id: "sony", name: "SONY" },
  { id: "unloaded", name: "미로딩" },
  { id: "ownerclan", name: "오너클랜" },
];

function drawList(tree) {
  tree.textContent = "";
  suppliers.forEach((item) => {
    tree.append(buttonFor(item));
  });
}

const tree = createElement("div");
drawList(tree);
paintCollectSupplierCounts(tree, {
  countOf(id) {
    if (id === "panasonic") return 3;
    return null;
  },
});
assert.deepStrictEqual(
  tree.querySelectorAll(".collect-supplier-tag").map((tag) => tag.textContent),
  ["3개"],
);
paintCollectSupplierCounts(tree, { countOf: () => null });
assert.strictEqual(tree.querySelectorAll(".collect-supplier-tag").length, 0);
assert.deepStrictEqual(
  tree.querySelectorAll(".collect-supplier-item").map((button) => button.textContent),
  ["PANASONIC", "SONY", "미로딩", "오너클랜"],
);

function countOfCatalog(id) {
  const totals = { panasonic: 92, sony: 15 };
  return Object.prototype.hasOwnProperty.call(totals, id) ? totals[id] : null;
}

drawList(tree);
paintCollectSupplierCounts(tree, { countOf: countOfCatalog });
assert.deepStrictEqual(
  tree.querySelectorAll(".collect-supplier-tag").map((tag) => ({
    text: tag.textContent,
    title: tag.title,
  })),
  [
    { text: "92개", title: "전체상품 92개" },
    { text: "15개", title: "전체상품 15개" },
  ],
);
assert.deepStrictEqual(
  tree.querySelectorAll(".collect-supplier-name").map((name) => name.textContent),
  ["PANASONIC", "SONY"],
);

drawList(tree);
paintCollectSupplierCounts(tree, {
  countOf(id) {
    if (id === "ownerclan") return 2400;
    if (id === "panasonic") return 92;
    if (id === "sony") return 15;
    return null;
  },
  skip(id, name) {
    return isOwnerclanSupplier(id, [{ id: "ownerclan", type: "ownerclan", name: "오너클랜" }], name);
  },
});
assert.deepStrictEqual(
  tree.querySelectorAll(".collect-supplier-tag").map((tag) => tag.textContent),
  ["92개", "15개"],
);
assert.strictEqual(
  tree.querySelectorAll(".collect-supplier-item").find((button) => button.dataset.id === "ownerclan").querySelector(".collect-supplier-tag"),
  null,
);

async function main() {
  const view = createElement("section");
  view.id = "viewCollect";
  view.hidden = false;
  let liveTree = createElement("div");
  let renderCollectSupplierTree = function () {
    drawList(liveTree);
  };
  let catalog = {
    searchMode: false,
    selectedCategory: "",
    loadedCategory: "",
    loadedFor: "",
    items: [],
  };
  let renderCafe24Catalog = function () {};
  let styleNode = null;
  const supplierRows = [
    { id: "panasonic", name: "PANASONIC", type: "cafe24" },
    { id: "sony", name: "SONY", type: "cafe24" },
    { id: "unloaded", name: "미로딩", type: "cafe24" },
    { id: "ownerclan", name: "오너클랜", type: "ownerclan" },
  ];
  let masterCountReads = 0;
  const doc = {
    head: { appendChild(node) { styleNode = node; } },
    getElementById(id) {
      if (id === "collectSupplierTree") return liveTree;
      if (id === "viewCollect") return view;
      if (id === "collectSupplierCountStyle") return styleNode;
      return null;
    },
    createElement,
  };

  installCollectSupplierCounts({
    document: doc,
    getRender: () => renderCollectSupplierTree,
    setRender: (fn) => { renderCollectSupplierTree = fn; },
    getRenderCatalog: () => renderCafe24Catalog,
    setRenderCatalog: (fn) => { renderCafe24Catalog = fn; },
    tree: () => liveTree,
    shopCatalog: () => catalog,
    supplierRows: () => supplierRows,
    countMasterProducts() {
      masterCountReads += 1;
      return 4;
    },
  });

  renderCollectSupplierTree();
  assert.strictEqual(liveTree.querySelectorAll(".collect-supplier-tag").length, 0);
  assert.strictEqual(masterCountReads, 0);

  catalog = {
    searchMode: false,
    selectedCategory: "camera",
    loadedCategory: "camera",
    loadedFor: "panasonic",
    items: Array.from({ length: 92 }),
  };
  renderCafe24Catalog();
  assert.deepStrictEqual(
    liveTree.querySelectorAll(".collect-supplier-tag").map((tag) => tag.textContent),
    ["92개"],
  );
  assert.notStrictEqual(
    liveTree.querySelector(".collect-supplier-tag").textContent,
    "4개",
  );

  catalog = {
    searchMode: false,
    selectedCategory: "body",
    loadedCategory: "body",
    loadedFor: "sony",
    items: Array.from({ length: 15 }),
  };
  renderCafe24Catalog();
  assert.deepStrictEqual(
    liveTree.querySelectorAll(".collect-supplier-tag").map((tag) => tag.textContent),
    ["92개", "15개"],
  );

  catalog = {
    searchMode: true,
    selectedCategory: "camera",
    loadedCategory: "__search__",
    loadedFor: "panasonic",
    items: Array.from({ length: 2 }),
  };
  renderCafe24Catalog();
  assert.deepStrictEqual(
    liveTree.querySelectorAll(".collect-supplier-tag").map((tag) => tag.textContent),
    ["92개", "15개"],
  );

  catalog = {
    searchMode: false,
    selectedCategory: "lens",
    loadedCategory: "",
    loadedFor: "",
    items: [],
  };
  renderCollectSupplierTree();
  assert.deepStrictEqual(
    liveTree.querySelectorAll(".collect-supplier-tag").map((tag) => tag.textContent),
    ["92개", "15개"],
  );

  catalog = {
    searchMode: false,
    selectedCategory: "lens",
    loadedCategory: "lens",
    loadedFor: "sony",
    items: [],
  };
  renderCafe24Catalog();
  assert.deepStrictEqual(
    liveTree.querySelectorAll(".collect-supplier-tag").map((tag) => tag.textContent),
    ["92개", "0개"],
  );

  catalog = {
    searchMode: false,
    selectedCategory: "all",
    loadedCategory: "all",
    loadedFor: "ownerclan",
    items: Array.from({ length: 2400 }),
  };
  renderCafe24Catalog();
  assert.deepStrictEqual(
    liveTree.querySelectorAll(".collect-supplier-tag").map((tag) => tag.textContent),
    ["92개", "0개"],
  );
  assert.strictEqual(
    liveTree.querySelectorAll(".collect-supplier-item").find((button) => button.dataset.id === "ownerclan").querySelector(".collect-supplier-tag"),
    null,
  );
  assert.strictEqual(
    liveTree.querySelectorAll(".collect-supplier-item").find((button) => button.dataset.id === "unloaded").querySelector(".collect-supplier-tag"),
    null,
  );
  assert.strictEqual(masterCountReads, 0);

  console.log("collect supplier count tests ok");
}

main();
