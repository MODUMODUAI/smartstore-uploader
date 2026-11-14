const assert = require("assert");
const {
  supplierTotalCountLabel,
  paintCollectSupplierCounts,
  installCollectSupplierCounts,
} = require("./collect_supplier_count.js");

assert.strictEqual(supplierTotalCountLabel(0, false), "");
assert.strictEqual(supplierTotalCountLabel(1, false), "");
assert.strictEqual(supplierTotalCountLabel(12345, false), "");
assert.strictEqual(supplierTotalCountLabel(0, true), "0개");
assert.strictEqual(supplierTotalCountLabel(1, true), "1개");
assert.strictEqual(supplierTotalCountLabel(12345, true), "12,345개");
assert.strictEqual(supplierTotalCountLabel(1.8, true), "1개");
assert.strictEqual(supplierTotalCountLabel(-1, true), "");
assert.strictEqual(supplierTotalCountLabel(Number.NaN, true), "");
assert.strictEqual(supplierTotalCountLabel(null, true), "");
assert.strictEqual(supplierTotalCountLabel(undefined, true), "");

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
  { id: "empty", name: "빈공급사" },
  { id: "one", name: "한개상점" },
  { id: "many", name: "많은도매" },
];

function drawList(tree) {
  tree.textContent = "";
  suppliers.forEach((item) => {
    const button = buttonFor(item);
    tree.append(button);
  });
}

const tree = createElement("div");
drawList(tree);
paintCollectSupplierCounts(tree, { loaded: false, countOf: () => 0 });
assert.deepStrictEqual(
  tree.querySelectorAll(".collect-supplier-item").map((button) => button.textContent),
  ["빈공급사", "한개상점", "많은도매"],
);
assert.strictEqual(tree.querySelectorAll(".collect-supplier-tag").length, 0);

function countMasterProducts(list, id) {
  return list.filter((item) => item.wholesale_id === id && !item.master_id && !item.market_id).length;
}

const loadedProducts = [
  { wholesale_id: "empty", master_id: "master", market_id: "store" },
  { wholesale_id: "one" },
  ...Array.from({ length: 12345 }, () => ({ wholesale_id: "many" })),
];
drawList(tree);
paintCollectSupplierCounts(tree, {
  loaded: true,
  countOf: (id) => countMasterProducts(loadedProducts, id),
});
const tags = tree.querySelectorAll(".collect-supplier-tag").map((tag) => ({
  text: tag.textContent,
  title: tag.title,
}));
assert.deepStrictEqual(tags, [
  { text: "0개", title: "전체상품 0개" },
  { text: "1개", title: "전체상품 1개" },
  { text: "12,345개", title: "전체상품 12,345개" },
]);
assert.deepStrictEqual(
  tree.querySelectorAll(".collect-supplier-name").map((name) => name.textContent),
  ["빈공급사", "한개상점", "많은도매"],
);
assert.strictEqual(tree.querySelectorAll(".collect-supplier-item").length, suppliers.length);

async function main() {
  let products = [];
  const initialProducts = products;
  const view = createElement("section");
  view.id = "viewCollect";
  view.hidden = false;
  let liveTree = createElement("div");
  let renderCollectSupplierTree = function () {
    drawList(liveTree);
  };
  let renderSheets = function () {};
  let loadProducts = async function () {
    renderSheets();
  };
  let styleNode = null;
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
    readProducts: () => products,
    countOf: (id) => countMasterProducts(products, id),
    getRender: () => renderCollectSupplierTree,
    setRender: (fn) => { renderCollectSupplierTree = fn; },
    getRenderSheets: () => renderSheets,
    setRenderSheets: (fn) => { renderSheets = fn; },
    getLoadProducts: () => loadProducts,
    setLoadProducts: (fn) => { loadProducts = fn; },
    viewOpen: () => view.hidden === false,
    tree: () => liveTree,
  });

  renderCollectSupplierTree();
  assert.strictEqual(liveTree.querySelectorAll(".collect-supplier-tag").length, 0);
  assert.deepStrictEqual(
    liveTree.querySelectorAll(".collect-supplier-item").map((button) => button.dataset.id),
    ["empty", "one", "many"],
  );

  products = loadedProducts.slice();
  assert.notStrictEqual(products, initialProducts);
  renderSheets();
  assert.deepStrictEqual(
    liveTree.querySelectorAll(".collect-supplier-tag").map((tag) => tag.textContent),
    ["0개", "1개", "12,345개"],
  );

  products = [
    { wholesale_id: "empty" },
    { wholesale_id: "one" },
    { wholesale_id: "one" },
    { wholesale_id: "many" },
  ];
  await loadProducts();
  assert.deepStrictEqual(
    liveTree.querySelectorAll(".collect-supplier-tag").map((tag) => tag.textContent),
    ["1개", "2개", "1개"],
  );

  view.hidden = true;
  products = loadedProducts.slice();
  renderSheets();
  assert.deepStrictEqual(
    liveTree.querySelectorAll(".collect-supplier-tag").map((tag) => tag.textContent),
    ["1개", "2개", "1개"],
  );
  view.hidden = false;
  renderCollectSupplierTree();
  assert.deepStrictEqual(
    liveTree.querySelectorAll(".collect-supplier-tag").map((tag) => tag.textContent),
    ["0개", "1개", "12,345개"],
  );

  console.log("collect supplier count tests ok");
}

main();
