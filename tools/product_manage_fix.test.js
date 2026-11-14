const assert = require("assert");
const {
  supplierFilterRows,
  kpageBoxShippingFee,
  kpageFeeFromProduct,
  isAlreadyRegistered,
  shippingOnlyPatch,
  applyShippingPatch,
  splitReregister,
  REREGISTER_FIELDS,
  changedFieldGroups,
  selectiveReregisterPatch,
  installProductManageFix,
} = require("./product_manage_fix.js");

const wholesalers = [
  { id: "kp", name: "케이페이지", url: "https://kpage.co.kr" },
  { id: "oc", name: "오너클랜", url: "https://www.ownerclan.com" },
];

const products = [
  {
    id: "a",
    name: "완박스 상품",
    wholesale_id: "",
    wholesale_name: "케이페이지",
    source_url: "https://www.kpage.co.kr/goods/1",
    price: 12000,
  },
  {
    id: "b",
    name: "오너 상품",
    wholesale_id: "oc",
    wholesale_name: "오너클랜",
    source_url: "https://ownerclan.com/item/2",
    price: 9000,
  },
  {
    id: "c",
    name: "주소만 있는 케이페이지",
    wholesale_id: "",
    wholesale_name: "",
    source_url: "https://shop.kpage.co.kr/product/3",
    price: 8000,
  },
  {
    id: "d",
    name: "직접 수집",
    wholesale_id: "",
    wholesale_name: "",
    source_url: "https://example.com/item/4",
    price: 5000,
  },
];

const all = supplierFilterRows(products, "all", wholesalers);
assert.deepStrictEqual(all.map((item) => item.id), ["a", "b", "c", "d"]);

const kpage = supplierFilterRows(products, "kp", wholesalers);
assert.deepStrictEqual(kpage.map((item) => item.id), ["a", "c"]);
assert.ok(kpage.length > 0);

const owner = supplierFilterRows(products, "oc", wholesalers);
assert.deepStrictEqual(owner.map((item) => item.id), ["b"]);

const urlOnly = supplierFilterRows(products, "url", wholesalers);
assert.deepStrictEqual(urlOnly.map((item) => item.id), ["d"]);

const stale = supplierFilterRows([
  { id: "e", wholesale_id: "gone", wholesale_name: "케이페이지", source_url: "" },
], "kp", wholesalers);
assert.deepStrictEqual(stale.map((item) => item.id), ["e"]);

const claimed = supplierFilterRows([
  { id: "f", wholesale_id: "oc", wholesale_name: "케이페이지", source_url: "https://kpage.co.kr/x" },
], "kp", wholesalers);
assert.deepStrictEqual(claimed.map((item) => item.id), ["f"]);
assert.deepStrictEqual(supplierFilterRows([
  { id: "f", wholesale_id: "oc", wholesale_name: "케이페이지", source_url: "https://kpage.co.kr/x" },
], "oc", wholesalers).map((item) => item.id), []);

const shopWholesalers = wholesalers.concat([{ id: "murray", name: "머레이", url: "https://murray.co.kr" }]);
const mixed = [
  { id: "m1", wholesale_id: "murray", wholesale_name: "머레이", source_url: "https://murray.co.kr/a" },
  { id: "k1", wholesale_id: "murray", wholesale_name: "케이페이지", source_url: "https://www.kpage.co.kr/b" },
  { id: "k2", wholesale_id: "", wholesale_name: "케이페이지", source_url: "https://murray.co.kr/stolen" },
  { id: "m2", wholesale_id: "", wholesale_name: "", source_url: "https://shop.murray.co.kr/c" },
];
assert.deepStrictEqual(supplierFilterRows(mixed, "murray", shopWholesalers).map((item) => item.id), ["m1", "m2"]);
assert.deepStrictEqual(supplierFilterRows(mixed, "kp", shopWholesalers).map((item) => item.id), ["k1", "k2"]);
assert.deepStrictEqual(supplierFilterRows(mixed, "all", shopWholesalers).map((item) => item.id), ["m1", "k1", "k2", "m2"]);

assert.strictEqual(kpageBoxShippingFee("완박스 배송비 1개 주문시 3,850원"), 3850);
assert.strictEqual(kpageBoxShippingFee("완박스 배송비 3,300원 ~ 27,500원"), 3300);
assert.strictEqual(kpageBoxShippingFee("완박스배송비 3850원"), 3850);
assert.strictEqual(kpageBoxShippingFee("배송비 1개 주문시 3,850원"), null);
assert.strictEqual(kpageBoxShippingFee("완박스 배송비 1개"), null);

const single = {
  name: "단일 배송비",
  shipping_fee: 1,
  detail_html: "<p>완박스 배송비 1개 주문시 3,850원</p>",
};
assert.strictEqual(kpageFeeFromProduct(single), 3850);

const range = {
  id: "range-1",
  name: "범위 배송비",
  price: 22000,
  shipping_fee: 27500,
  summary: "완박스 배송비 3,300원 ~ 27,500원",
};
assert.strictEqual(kpageFeeFromProduct(range), 3300);
assert.strictEqual(kpageFeeFromProduct({ name: "없음", summary: "무료배송" }), null);

const registered = {
  id: "reg-1",
  name: "이미 등록된 상품",
  original_name: "등록 당시 이름",
  price: 15000,
  original_price: 15000,
  origin: "국내",
  shipping_fee: 3000,
  wholesale_shipping_fee: 3850,
  attributes: [{ name: "색상", value: "빨강" }],
  origin_product_no: "9001",
  channel_product_no: "8001",
  market_id: "market-1",
};
assert.strictEqual(isAlreadyRegistered(registered), true);
assert.strictEqual(isAlreadyRegistered({ id: "new", name: "새 상품" }), false);

const patch = shippingOnlyPatch("4,200원");
assert.deepStrictEqual(Object.keys(patch), ["shipping_fee"]);
assert.strictEqual(patch.shipping_fee, 4200);
assert.throws(() => shippingOnlyPatch("배송비 없음"), /배송비/);

const updated = applyShippingPatch(registered, "4,200");
assert.deepStrictEqual(Object.keys(updated.patch), ["shipping_fee"]);
assert.strictEqual(updated.product.shipping_fee, 4200);
assert.strictEqual(updated.product.name, "이미 등록된 상품");
assert.strictEqual(updated.product.price, 15000);
assert.strictEqual(updated.product.origin, "국내");
assert.strictEqual(updated.product.origin_product_no, "9001");
assert.strictEqual(registered.name, "이미 등록된 상품");
assert.strictEqual(registered.shipping_fee, 3000);

const parts = splitReregister([
  registered,
  { id: "new", name: "새 상품", price: 1000, market_id: "market-1" },
]);
assert.deepStrictEqual(parts.registered.map((item) => item.id), ["reg-1"]);
assert.deepStrictEqual(parts.fresh.map((item) => item.id), ["new"]);

assert.deepStrictEqual(REREGISTER_FIELDS.map((group) => group.label).slice(0, 3), ["상품명", "속성", "배송/가격"]);
assert.deepStrictEqual(changedFieldGroups(registered), ["name", "ship_price"]);
const nameOnly = selectiveReregisterPatch(registered, ["name"]);
assert.deepStrictEqual(nameOnly, { name: "이미 등록된 상품" });
const shipOnly = selectiveReregisterPatch(registered, ["ship_price"]);
assert.deepStrictEqual(Object.keys(shipOnly).sort(), ["price", "shipping_fee"]);
assert.ok(!Object.prototype.hasOwnProperty.call(shipOnly, "name"));
assert.ok(!Object.prototype.hasOwnProperty.call(shipOnly, "attributes"));
const nameAndAttributes = selectiveReregisterPatch(registered, ["name", "attributes"]);
assert.deepStrictEqual(Object.keys(nameAndAttributes).sort(), ["attributes", "name"]);
assert.strictEqual(nameAndAttributes.attributes[0].value, "빨강");

const saved = [];
const fresh = { id: "new", name: "새 상품", price: 1000, market_id: "market-1", shipping_fee: 2000 };
let selection = [registered];

globalThis.productFilter = "kp";
globalThis.wholesalers = wholesalers;
globalThis.products = products.map((item) => Object.assign({}, item));
globalThis.scopedProducts = function idOnlyFilter() {
  const filter = globalThis.productFilter;
  if (!filter || filter === "all") return globalThis.products.slice();
  if (filter === "url") return globalThis.products.filter((item) => !item.wholesale_id);
  return globalThis.products.filter((item) => String(item.wholesale_id) === filter);
};
globalThis.currentMarketStatusRows = function idOnlyStatus() {
  return globalThis.scopedProducts();
};
globalThis.wholesaleShipAmount = function readStored(item) {
  const amount = Number(item && item.shipping_fee);
  return Number.isFinite(amount) ? amount : null;
};
globalThis.saveProduct = async function saveProduct(item, body) {
  saved.push(JSON.parse(JSON.stringify(body)));
  const index = globalThis.products.findIndex((row) => row && row.id === item.id);
  if (index >= 0) {
    globalThis.products[index] = Object.assign({}, globalThis.products[index], { name: "서버가 바꾼 이름" }, body);
  }
  return globalThis.products[index] || Object.assign({}, item, body);
};
globalThis.isMasterProduct = () => false;
globalThis.registerCalls = 0;
globalThis.registerSelected = async function originalRegister() {
  const items = globalThis.requireSelected();
  globalThis.registerCalls += 1;
  globalThis.lastRegisterIds = items.map((item) => item.id);
};
globalThis.requireSelected = () => selection.filter((item) => globalThis.selectedIds.has(item.id));
globalThis.selectedIds = new Set(["reg-1"]);
globalThis.toast = () => {};
globalThis.renderProductSheet = () => {};
globalThis.loadProducts = async function loadProducts() {
  return globalThis.products;
};
globalThis.ensureProductFull = async function ensureProductFull(id) {
  return globalThis.products.find((item) => item.id === id) || null;
};
globalThis.localStorage = {
  values: {},
  getItem(key) { return Object.prototype.hasOwnProperty.call(this.values, key) ? this.values[key] : null; },
  setItem(key, value) { this.values[key] = String(value); },
};

function walkAll(node, visit) {
  (node.children || []).forEach((child) => {
    visit(child);
    walkAll(child, visit);
  });
}

function makeNode(tag) {
  const node = {
    tagName: String(tag || "").toUpperCase(),
    id: "",
    className: "",
    type: "",
    value: "",
    checked: false,
    textContent: "",
    children: [],
    attrs: {},
    appendChild(child) {
      this.children.push(child);
      return child;
    },
    setAttribute(name, value) {
      this.attrs[name] = value;
    },
    querySelector(selector) {
      let found = null;
      walkAll(this, (child) => {
        if (found) return;
        if (selector === "form" && child.tagName === "FORM") found = child;
        if (selector.charAt(0) === "#" && child.id === selector.slice(1)) found = child;
        if (selector === "[data-cancel]" && child.attrs["data-cancel"]) found = child;
      });
      return found;
    },
    querySelectorAll(selector) {
      const found = [];
      walkAll(this, (child) => {
        if (selector === "input" && child.tagName === "INPUT") found.push(child);
      });
      return found;
    },
    close() {},
    showModal() {},
  };
  if (tag === "dialog") {
    node.showModal = function showNameOnly() {
      node.querySelectorAll("input").forEach((box) => {
        box.checked = box.value === "name";
      });
      node.querySelector("form").onsubmit({ preventDefault() {} });
    };
  }
  return node;
}

globalThis.document = {
  getElementById() { return null; },
  createElement(tag) { return makeNode(tag); },
  body: { appendChild() {} },
};

installProductManageFix();

assert.deepStrictEqual(globalThis.scopedProducts().map((item) => item.id), ["a", "c"]);
assert.ok(globalThis.scopedProducts().length > 0);
globalThis.productFilter = "all";
assert.deepStrictEqual(globalThis.scopedProducts().map((item) => item.id), ["a", "b", "c", "d"]);
globalThis.productFilter = "oc";
assert.deepStrictEqual(globalThis.currentMarketStatusRows().map((item) => item.id), ["b"]);
globalThis.productFilter = "url";
assert.deepStrictEqual(
  globalThis.scopedProducts().map((item) => item.id),
  globalThis.products.filter((item) => !item.wholesale_id).map((item) => item.id),
);

assert.strictEqual(globalThis.wholesaleShipAmount(single), 3850);
assert.strictEqual(globalThis.wholesaleShipAmount(range), 3300);
const manual = Object.assign({}, range, { _shipManual: true, shipping_fee: 4100 });
assert.strictEqual(globalThis.wholesaleShipAmount(manual), 4100);

(async () => {
  const imported = Object.assign({}, range);
  globalThis.products = [imported];
  await globalThis.loadProducts();
  assert.strictEqual(globalThis.products[0].shipping_fee, 3300);
  assert.strictEqual(globalThis.products[0].name, "범위 배송비");
  assert.strictEqual(globalThis.products[0].price, 22000);
  assert.deepStrictEqual(saved, [{ shipping_fee: 3300 }]);

  saved.length = 0;
  selection = [Object.assign({}, registered)];
  globalThis.products = selection.slice();
  globalThis.selectedIds = new Set(["reg-1"]);
  await globalThis.registerSelected();
  assert.strictEqual(globalThis.registerCalls, 0);
  assert.deepStrictEqual(saved, [{ name: "이미 등록된 상품" }]);
  assert.strictEqual(globalThis.products[0].name, "이미 등록된 상품");
  assert.strictEqual(globalThis.products[0].price, 15000);
  assert.strictEqual(globalThis.products[0].origin, "국내");
  assert.strictEqual(globalThis.products[0].origin_product_no, "9001");
  assert.strictEqual(globalThis.products[0].shipping_fee, 3000);
  assert.strictEqual(globalThis.products[0].attributes[0].value, "빨강");

  saved.length = 0;
  selection = [fresh];
  globalThis.products = [fresh];
  globalThis.selectedIds = new Set(["new"]);
  await globalThis.registerSelected();
  assert.strictEqual(globalThis.registerCalls, 1);
  assert.deepStrictEqual(globalThis.lastRegisterIds, ["new"]);
  assert.deepStrictEqual(saved, []);

  saved.length = 0;
  const registeredAgain = Object.assign({}, registered);
  const freshAgain = Object.assign({}, fresh);
  selection = [registeredAgain, freshAgain];
  globalThis.products = selection.slice();
  globalThis.selectedIds = new Set(["reg-1", "new"]);
  await globalThis.registerSelected();
  assert.deepStrictEqual(saved, [{ name: "이미 등록된 상품" }]);
  assert.strictEqual(registeredAgain.name, "이미 등록된 상품");
  assert.strictEqual(registeredAgain.shipping_fee, 3000);
  assert.strictEqual(registeredAgain.price, 15000);
  assert.deepStrictEqual(globalThis.lastRegisterIds, ["new"]);
  assert.strictEqual(globalThis.registerCalls, 2);

  console.log("product_manage_fix.test.js ok");
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
