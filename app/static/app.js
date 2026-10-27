const $ = (selector) => document.querySelector(selector);

const STATUS = {
  collected: "미등록",
  ai_done: "미등록",
  registered: "등록됨",
  error: "오류",
};

let products = [];
let current = null;
let selectedIds = new Set();
let checkPaint = null;
let checkPaintPending = null;
let checkPaintDidDrag = false;
let saveTimer = 0;
let wholesalers = [];
let currentWholesalerId = "";
let productFilter = "all";
let productStatusFilter = "all";
let productQuery = "";
let productSearchField = "all";
let productSortKey = "";
let productSortDir = "asc";
let markets = [];
let priceSets = [];
let currentMarketId = "";
let marketFormIsNew = false;
let fillingMarketForm = false;
let pendingMarketChannel = "";
let marketFilter = "master";
let sourceExpanded = true;
let masterChannelFilter = "";
const channelExpanded = {};
let orders = [];
let selectedOrderIds = new Set();
let orderFocusId = "";
let orderMarketFilter = "all";
let orderCollectChannel = "smartstore";
let orderCollectStore = "all";
let orderTab = "new";
let ordersCollected = false;
let csMemoOrderId = "";
const invoiceDrafts = new Map();
let orderQuery = "";
let orderDateBasisMemory = "paid";
let csQuery = "";
let orderSortKey = "";
let orderSortDir = "asc";
const ORDER_SORTABLE = {
  "단가": "price",
  "별칭(쇼핑몰계정)": "alias",
  "쇼핑몰": "mall",
};
const ORDER_TAB_TITLES = {
  new: "신규주문",
  wait: "발송대기",
  shipping: "배송중",
  delivered: "배송완료",
  confirmed: "구매확정",
  canceled: "취소주문",
  returned: "반품주문",
  exchanged: "교환주문",
  all: "통합주문관리",
  cs: "CS메모관리",
  excel: "엑셀 양식 설정",
};
let inquiries = [];
let inquiryMarketFilter = "all";
let inquiryChannelFilter = "all";
let inquiryStoreFilter = "all";
let selectedInquiryIds = new Set();
let currentInquiryId = "";
const inquiryTemplateCache = {};
let inquiryUpdatedAt = "";
const inquiryChannelExpanded = {};
const orderChannelExpanded = {};
const COURIERS = [
  ["DIRECT", "직접전달"],
  ["CJGLS", "CJ대한통운"],
  ["HANJIN", "한진택배"],
  ["HYUNDAI", "롯데택배"],
  ["EPOST", "우체국택배"],
  ["KGB", "로젠택배"],
  ["KDEXP", "경동택배"],
  ["DAESIN", "대신택배"],
  ["ILYANG", "일양로지스"],
  ["CHUNIL", "천일택배"],
];

const MARKET_CHANNELS = [
  { id: "master", name: "마스터상품", icon: "M", color: "#6b7280", enabled: true },
  { id: "smartstore", name: "스마트스토어", icon: "N", color: "#03c75a", enabled: true, account: true, needsUrl: true, mallNo: "04" },
  { id: "coupang", name: "쿠팡", icon: "C", color: "#de2910", enabled: true, account: true, mallNo: "05" },
  { id: "auction", name: "옥션", icon: "A", color: "#d2232a", enabled: true, account: true, needsLogin: true, mallNo: "01" },
  { id: "gmarket", name: "G마켓", icon: "G", color: "#00c73c", enabled: true, account: true, needsLogin: true, mallNo: "02" },
  { id: "11st", name: "11번가", icon: "11", color: "#ed1c24", enabled: true, account: true, mallNo: "03" },
  { id: "toss", name: "토스쇼핑", icon: "T", color: "#3182f6", enabled: true, account: true, mallNo: "07" },
  { id: "lotteon", name: "롯데ON", icon: "ON", color: "#f5c518", text: "#111", enabled: true, account: true, mallNo: "08" },
  { id: "kakao", name: "카카오톡스토어", icon: "K", color: "#fee500", text: "#3c1e1e", enabled: true, account: true, mallNo: "06" },
  { id: "ssg", name: "SSG.COM", icon: "S", color: "#f2a900", enabled: true, account: true, mallNo: "09" },
  { id: "temu", name: "테무", icon: "테", color: "#fb7701", enabled: true, account: true, needsLogin: true, mallNo: "10" },
];

function accountChannels() {
  return MARKET_CHANNELS.filter((item) => item.account);
}

function channelById(id) {
  return MARKET_CHANNELS.find((item) => item.id === id) || MARKET_CHANNELS[1];
}

function mallLabel(channel) {
  const item = typeof channel === "string" ? channelById(channel) : channel;
  if (!item) return "";
  return item.mallNo ? `${item.mallNo}.${item.name}` : (item.name || "");
}

function marketChannel(item) {
  return item?.channel || "smartstore";
}

function marketsForChannel(channelId) {
  return markets.filter((item) => marketChannel(item) === channelId);
}

function isChannelExpanded(id) {
  return channelExpanded[id] !== false;
}

function toast(message, isError = false) {
  if (isError) {
    log(message, "err");
    return;
  }
  const el = $("#toast");
  el.textContent = message;
  el.className = "show";
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { el.className = ""; }, 4600);
}

const orderJobs = new Map();
const jobSlots = {
  products: { busy: false, owned: 0, controller: null, label: "" },
  orders: { busy: false, owned: 0, controller: null, label: "" },
  inquiries: { busy: false, owned: 0, controller: null, label: "" },
  wholesalers: { busy: false, owned: 0, controller: null, label: "" },
  ownerclan: { busy: false, owned: 0, controller: null, label: "" },
  settings: { busy: false, owned: 0, controller: null, label: "" },
};
const SCOPE_BUTTONS = {
  products: "#productToolbar button, #collectButton, #productSyncStock, #productRefreshOriginal, #productRefreshMarket, #productStatusFilters button",
  inquiries: "#loadInquiriesButton, #resetInquiriesButton, #inquiryExcelButton, #inquiryAnswerButton",
  wholesalers: "#wholesaleNew, #wholesaleSave, #wholesaleDelete, #wholesaleLogin, #wholesaleGoCollect, #collectCafe24ReloadCats, #collectCafe24Send, #collectCafe24ImportNew",
  ownerclan: "#ownerclanFilterSearch, #ownerclanProductSearch, #ownerclanLowest, #ownerclanSend, #ownerclanPrev, #ownerclanNext, .ownerclan-page-num",
};

function setJobStatus(message, busy) {
  const label = message || (busy ? "작업 중" : "대기");
  document.querySelectorAll("[data-job-status-text]").forEach((text) => {
    text.textContent = label;
  });
  const spinner = $("#jobSpinner");
  if (!spinner) return;
  spinner.hidden = !busy;
  const line = spinner.querySelector("[data-job-spinner-text]");
  if (line) line.textContent = busy ? label : "";
}

function log(message, kind = "") {
  document.querySelectorAll(".job-log").forEach((list) => {
    const item = document.createElement("li");
    if (kind) item.className = kind;
    item.textContent = message;
    list.prepend(item);
    while (list.children.length > 80) list.lastElementChild.remove();
  });
  if ((anyMenuBusy() || orderJobs.size) && message) setJobStatus(message, true);
}

function selectedStoreMarketId() {
  if (currentMarketId) return currentMarketId;
  if (marketFilter && marketFilter !== "master") return marketFilter;
  return "";
}

function withMarketParam(path) {
  const id = selectedStoreMarketId();
  if (!id) return path;
  return `${path}${path.includes("?") ? "&" : "?"}market_id=${encodeURIComponent(id)}`;
}

function scopeForPath(path) {
  const item = String(path || "").split("?")[0];
  if (item.includes("/orders") || item.includes("/excel-forms")) return "orders";
  if (item.includes("/inquiries")) return "inquiries";
  if (item.includes("/ownerclan")) return "ownerclan";
  if (item.includes("/wholesalers") || item.includes("/stock-jobs") || item.includes("/stock-check")) return "wholesalers";
  if (item.includes("/settings") || item.includes("/markets") || item.includes("/chrome")) return "settings";
  return "products";
}

async function api(path, options = {}) {
  const { signal, headers, quiet, status, detached, scope: scopeOption, ...rest } = options;
  const method = String(rest.method || "GET").toUpperCase();
  const silent = Boolean(quiet) || isBackgroundRequest(path, method);
  const scope = scopeOption || scopeForPath(path);
  const slot = jobSlots[scope] || jobSlots.products;
  const manual = !silent && !detached && slot.busy && slot.owned === 0;
  const tracked = !silent && !detached && !manual && method !== "GET";
  if (tracked) {
    slot.owned += 1;
    if (slot.owned === 1) setBusy(true, status || jobStatusText(path, method), scope);
  }
  try {
    const response = await fetch(path, {
      headers: { "Content-Type": "application/json", ...(headers || {}) },
      ...rest,
      signal: signal || (silent || detached ? undefined : slot.controller?.signal),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(typeof data.detail === "string" ? data.detail : "요청에 실패했습니다.");
    }
    return data;
  } catch (error) {
    if (error?.name === "AbortError") throw abortError();
    throw error;
  } finally {
    if (tracked) {
      slot.owned -= 1;
      if (slot.owned === 0) setBusy(false, "", scope);
    }
  }
}

function isBackgroundRequest(path, method) {
  const item = String(path || "").split("?")[0];
  if (method === "GET" && /^\/api\/stock-jobs\/[^/]+$/.test(item)) return true;
  if (method === "GET" && /^\/api\/product-refresh-jobs\/[^/]+$/.test(item)) return true;
  if (method === "GET" && /^\/api\/product-market-jobs\/[^/]+$/.test(item)) return true;
  return item === "/api/alerts";
}

function jobStatusText(path, method) {
  const item = String(path || "").split("?")[0];
  const verb = String(method || "GET").toUpperCase();
  if (item.includes("/ownerclan/products/import")) return "오너클랜 상품을 가져오는 중입니다.";
  if (item.includes("/ownerclan/products")) return "오너클랜 상품을 불러오는 중입니다.";
  if (item.includes("/ownerclan/categories") || item.includes("/ownerclan/category")) return "오너클랜 분류를 불러오는 중입니다.";
  if (item.includes("/ownerclan")) return "오너클랜 설정을 저장하는 중입니다.";
  if (item.includes("/images/remove-text")) return "대표이미지 글씨제거 중 · 홍보 문구를 찾아 지우는 중입니다.";
  if (item.includes("/products/collect")) return "상품 정보를 가져오는 중입니다.";
  if (item.includes("/register")) return "선택한 상품을 등록하는 중입니다.";
  if (item.includes("/orders/import")) return "주문을 불러오는 중입니다.";
  if (item.includes("/orders/confirm")) return "주문을 확인하는 중입니다.";
  if (item.includes("/orders/dispatch")) return "송장을 발송하는 중입니다.";
  if (item.includes("/orders/invoices")) return "송장을 처리하는 중입니다.";
  if (item.includes("/orders/wholesale")) return "공급처 주문을 여는 중입니다.";
  if (item.includes("/orders/cancel")) return "주문을 취소하는 중입니다.";
  if (item.includes("/inquiries/import")) return "문의를 불러오는 중입니다.";
  if (item.includes("/answer")) return "문의 답변을 보내는 중입니다.";
  if (item.includes("/wholesalers/") && item.includes("/import")) return "공급처 상품을 가져오는 중입니다.";
  if (item.includes("/wholesalers/") && item.includes("/login")) return "공급처 로그인 창을 여는 중입니다.";
  if (item.includes("/stock-check") || item.includes("/stock-jobs")) return "품절 상태를 확인하는 중입니다.";
  if (item.includes("/chrome/login")) return "로그인 창을 여는 중입니다.";
  if (item.endsWith("/test")) return "연결을 테스트하는 중입니다.";
  if (item.includes("/delivery-templates/import")) return "배송정보를 가져오는 중입니다.";
  if (item.includes("/notices/import") || item.includes("/notices/apply")) return "상품정보고시를 처리하는 중입니다.";
  if (item.includes("/excel-forms")) return verb === "GET" ? "엑셀 양식을 불러오는 중입니다." : "엑셀 양식을 저장하는 중입니다.";
  if (item.includes("/price-sets") && item.endsWith("/apply")) return "판매가 세트를 적용하는 중입니다.";
  if (verb === "DELETE") return "삭제하는 중입니다.";
  if (item.includes("/products") && verb === "GET") return "상품 목록을 불러오는 중입니다.";
  if (item.includes("/orders") && verb === "GET") return "주문 목록을 불러오는 중입니다.";
  if (item.includes("/inquiries") && verb === "GET") return "문의 목록을 불러오는 중입니다.";
  if (item.includes("/wholesalers") && verb === "GET") return "공급처 목록을 불러오는 중입니다.";
  if (item.includes("/markets") && verb === "GET") return "마켓 목록을 불러오는 중입니다.";
  if (item.includes("/settings") && verb === "GET") return "설정을 불러오는 중입니다.";
  if (verb === "PUT" || verb === "POST") return "저장하는 중입니다.";
  return "작업 중입니다.";
}

function orderJobKey(tab, label) {
  return `${tab}:${label}`;
}

function orderJobsFor(tab) {
  return [...orderJobs.entries()].filter(([key]) => key.startsWith(`${tab}:`)).map(([, job]) => job);
}

function anyMenuBusy() {
  return Object.values(jobSlots).some((slot) => slot.busy) || orderJobs.size > 0;
}

function refreshJobStatus() {
  const labels = [];
  Object.values(jobSlots).forEach((slot) => {
    if (slot.busy && slot.label) labels.push(slot.label);
  });
  orderJobs.forEach((job) => {
    if (job.label) labels.push(job.label);
  });
  if (labels.length) setJobStatus(labels.join(" · "), true);
  else setJobStatus("대기", false);
}

function refreshOrderJobs() {
  document.querySelectorAll("#orderStatusTabs [data-order-tab]").forEach((button) => {
    button.classList.toggle("order-tab-busy", orderJobsFor(button.dataset.orderTab).length > 0);
  });
  const current = orderJobsFor(orderTab);
  const collect = $("#loadOrdersButton");
  if (collect && collect.dataset.lockedByJob !== "orders") {
    collect.disabled = current.some((job) => job.kind === "collect");
  }
  const stop = $("#orderStopJobButton");
  if (stop) {
    stop.hidden = orderTab !== "wait" && !current.length;
    stop.disabled = !current.length;
  }
  refreshJobStatus();
}

async function runOrderTabJob(tab, label, work) {
  const key = orderJobKey(tab, label);
  if (orderJobs.has(key)) {
    toast(`${label}이 이미 진행 중입니다. 다른 작업은 같이 할 수 있습니다.`, true);
    return;
  }
  const controller = new AbortController();
  orderJobs.set(key, { controller, label, kind: label.includes("수집") ? "collect" : "action" });
  refreshOrderJobs();
  log(label);
  try {
    await work(controller.signal);
  } catch (error) {
    if (isAbortError(error)) {
      log("작업을 중단했습니다.");
      toast("작업을 중단했습니다.");
      return;
    }
    throw error;
  } finally {
    if (orderJobs.get(key)?.controller === controller) orderJobs.delete(key);
    refreshOrderJobs();
  }
}

let ordersReload = Promise.resolve();

function reloadOrders() {
  const run = ordersReload.catch(() => {}).then(() => loadOrders({ quiet: true }));
  ordersReload = run;
  return run;
}

function isJobCancelled(scope = "products") {
  return Boolean(jobSlots[scope]?.controller?.signal.aborted);
}

function isAbortError(error) {
  const text = String(error?.message || error || "");
  return error?.name === "AbortError" || /aborted|중단/i.test(text);
}

function abortError() {
  const error = new Error("작업을 중단했습니다.");
  error.name = "AbortError";
  return error;
}

function throwIfCancelled(scope = "products") {
  if (isJobCancelled(scope)) throw abortError();
}

function wait(ms, scope = "products") {
  return new Promise((resolve, reject) => {
    if (isJobCancelled(scope)) {
      reject(abortError());
      return;
    }
    const timer = setTimeout(resolve, ms);
    jobSlots[scope]?.controller?.signal.addEventListener("abort", () => {
      clearTimeout(timer);
      reject(abortError());
    }, { once: true });
  });
}

function lockScopeButtons(scope, busy) {
  const selector = SCOPE_BUTTONS[scope];
  if (!selector) return;
  document.querySelectorAll(selector).forEach((button) => {
    if (button.id === "stopJobButton" || button.classList.contains("stop-job")) return;
    if (busy) {
      if (!button.disabled) button.dataset.lockedByJob = scope;
      button.disabled = true;
    } else if (button.dataset.lockedByJob === scope) {
      button.disabled = false;
      delete button.dataset.lockedByJob;
    }
  });
}

function setBusy(busy, message, scope = "products") {
  const slot = jobSlots[scope] || jobSlots.products;
  slot.busy = Boolean(busy);
  slot.label = busy ? (message || slot.label || "작업 중") : "";
  lockScopeButtons(scope, slot.busy);
  if (scope === "products") {
    const stop = $("#stopJobButton");
    if (stop) stop.disabled = !slot.busy;
  }
  if (busy) {
    if (scope === "products") clearTimeout(saveTimer);
    if (!slot.controller || slot.controller.signal.aborted) slot.controller = new AbortController();
  } else if (slot.owned === 0) {
    slot.controller = null;
  }
  if (message) log(message);
  else refreshJobStatus();
}

function stopCurrentJob() {
  if (refreshJob?.status === "running" && refreshJob.id) {
    api(`/api/product-refresh-jobs/${refreshJob.id}/cancel`, { method: "POST", detached: true }).catch(() => {});
  }
  if (marketJob?.status === "running" && marketJob.id) {
    api(`/api/product-market-jobs/${marketJob.id}/cancel`, { method: "POST", detached: true }).catch(() => {});
  }
  const slot = jobSlots.products;
  if (!slot.controller || slot.controller.signal.aborted) {
    toast("진행 중인 작업이 없습니다.");
    return;
  }
  slot.controller.abort();
  log("작업을 중단합니다.");
  toast("작업을 중단합니다.");
}

function selectedWholesalerId() {
  if (currentWholesalerId) return currentWholesalerId;
  const formId = $("#wholesaleForm")?.elements?.id?.value;
  if (formId) return formId;
  if (productFilter && productFilter !== "all" && productFilter !== "url") return productFilter;
  return $("#orderWholesaler")?.value || "";
}

function productSearchHay(item) {
  if (productSearchField === "name") return String(item.name || "");
  if (productSearchField === "category") return [item.category_name, item.source_category].filter(Boolean).join(" ");
  if (productSearchField === "brand") return String(item.brand || "");
  if (productSearchField === "manufacturer") return String(item.manufacturer || "");
  return [
    item.name,
    item.category_name,
    item.source_category,
    item.brand,
    item.manufacturer,
  ].filter(Boolean).join(" ");
}

function matchesProductQuery(item) {
  const tokens = productQuery.trim().toLowerCase().split(/\s+/).filter(Boolean);
  if (!tokens.length) return true;
  const hay = productSearchHay(item).toLowerCase();
  const compact = hay.replace(/\s+/g, "");
  return tokens.every((token) => hay.includes(token) || compact.includes(token.replace(/\s+/g, "")));
}

function productSearchFieldLabel() {
  return $("#productSearchField")?.selectedOptions?.[0]?.textContent || "전체";
}

function updateProductSearchPlaceholder() {
  const input = $("#productSearch");
  if (!input) return;
  const placeholders = {
    all: "상품명, 카테고리, 브랜드, 제조사",
    name: "상품명",
    category: "카테고리",
    brand: "브랜드",
    manufacturer: "제조사",
  };
  input.placeholder = placeholders[productSearchField] || placeholders.all;
}

function productSortValue(item, key) {
  if (key === "soldout") {
    if (item.wholesale_soldout) return 0;
    if (productWholesalerId(item)) return 1;
    return 2;
  }
  if (key === "created") {
    const stamp = Date.parse(String(item.created_at || ""));
    return Number.isFinite(stamp) ? stamp : 0;
  }
  if (key === "category") return String(item.category_name || item.source_category || "").trim();
  if (key === "name") return String(item.name || "").trim();
  if (key === "price") return Number(item.price || 0);
  if (key === "brand") return String(item.brand || "").trim();
  if (key === "manufacturer") return String(item.manufacturer || "").trim();
  if (key === "origin") return String(item.origin || "").trim();
  return "";
}

function sortVisibleProducts(rows) {
  if (!productSortKey) return rows;
  const dir = productSortDir === "desc" ? -1 : 1;
  return [...rows].sort((a, b) => {
    const av = productSortValue(a, productSortKey);
    const bv = productSortValue(b, productSortKey);
    let cmp = 0;
    if (typeof av === "number" || typeof bv === "number") cmp = Number(av) - Number(bv);
    else cmp = String(av).localeCompare(String(bv), "ko", { numeric: true, sensitivity: "base" });
    if (cmp) return cmp * dir;
    return String(a.id || "").localeCompare(String(b.id || ""));
  });
}

function updateProductSortHeaders() {
  document.querySelectorAll("#productGrid th.sortable").forEach((th) => {
    const active = th.dataset.sort === productSortKey;
    th.classList.toggle("sort-asc", active && productSortDir === "asc");
    th.classList.toggle("sort-desc", active && productSortDir === "desc");
    th.setAttribute("aria-sort", active ? (productSortDir === "desc" ? "descending" : "ascending") : "none");
  });
}

function isOwnerclanProduct(item) {
  const name = String(item?.wholesale_name || "");
  const url = String(item?.source_url || "");
  return name === "오너클랜" || url.includes("ownerclan.com");
}

function productWholesalerId(item) {
  const saved = String(item?.wholesale_id || "");
  if (saved) return saved;
  if (!isOwnerclanProduct(item)) return guessWholesalerIdFromUrl(item?.source_url);
  return wholesalers.find((row) => row.type === "ownerclan")?.id || "ownerclan";
}

function guessWholesalerIdFromUrl(url) {
  const host = (() => {
    try {
      return new URL(String(url || "")).hostname.toLowerCase();
    } catch {
      return "";
    }
  })();
  if (!host) return "";
  if (host.includes("ownerclan.com")) {
    return wholesalers.find((row) => row.type === "ownerclan")?.id || "ownerclan";
  }
  const match = wholesalers.find((row) => {
    try {
      const shop = new URL(String(row.url || "")).hostname.toLowerCase();
      return shop && (host === shop || host.endsWith(`.${shop}`) || shop.endsWith(`.${host}`));
    } catch {
      return false;
    }
  });
  return match?.id || "";
}

function revealFilteredMarketProducts() {
  if (!productFilter || productFilter === "all") return false;
  if (visibleProducts().length) return false;
  const previous = productFilter;
  productFilter = "all";
  if (!visibleProducts().length) {
    productFilter = previous;
    return false;
  }
  const select = $("#productWholesalerFilter");
  if (select) select.value = "all";
  return true;
}

function productStatusBucket(item) {
  const status = String(item?.status || "");
  if (status === "error") return "error";
  if (status === "registered" || item?.origin_product_no || item?.channel_product_no) return "registered";
  return "waiting";
}

function scopedProducts(ignoreStatus = false) {
  let rows = products;
  if (productFilter === "url") rows = rows.filter((item) => !productWholesalerId(item));
  else if (productFilter && productFilter !== "all") rows = rows.filter((item) => productWholesalerId(item) === productFilter);
  if (marketFilter === "master") {
    rows = rows.filter((item) => isMasterProduct(item));
    if (masterChannelFilter) {
      const sent = masterIdsInChannel(masterChannelFilter);
      rows = rows.filter((item) => sent.has(item.id));
    }
  } else if (accountChannels().some((item) => item.id === marketFilter)) {
    const ids = new Set(marketsForChannel(marketFilter).map((item) => item.id));
    rows = rows.filter((item) => item.market_id && ids.has(item.market_id));
  } else if (marketFilter && marketFilter !== "all") {
    rows = rows.filter((item) => item.market_id === marketFilter);
  }
  if (productQuery.trim()) rows = rows.filter(matchesProductQuery);
  if (!ignoreStatus && productStatusFilter && productStatusFilter !== "all") {
    rows = rows.filter((item) => productStatusBucket(item) === productStatusFilter);
  }
  return rows;
}

function visibleProducts() {
  return sortVisibleProducts(scopedProducts(false));
}

function statusCountsOf(rows) {
  const counts = { registered: 0, waiting: 0, error: 0 };
  (rows || []).forEach((item) => {
    counts[productStatusBucket(item)] += 1;
  });
  return counts;
}

function formatStatusCountLabel(counts) {
  return `등록 ${counts.registered} · 대기 ${counts.waiting} · 오류 ${counts.error}`;
}

function productsInMarketScope(filter = marketFilter, channelFilter = masterChannelFilter) {
  let rows = products;
  if (filter === "master") {
    rows = rows.filter((item) => isMasterProduct(item));
    if (channelFilter) {
      const sent = masterIdsInChannel(channelFilter);
      rows = rows.filter((item) => sent.has(item.id));
    }
    return rows;
  }
  if (accountChannels().some((item) => item.id === filter)) {
    const ids = new Set(marketsForChannel(filter).map((item) => item.id));
    return rows.filter((item) => item.market_id && ids.has(item.market_id));
  }
  if (filter && filter !== "all") {
    return rows.filter((item) => item.market_id === filter);
  }
  return rows;
}

function isSourceProductMenu() {
  return marketFilter === "all";
}

function isMasterProductMenu() {
  return marketFilter === "master";
}

function isStoreProductMenu() {
  return !isSourceProductMenu() && !isMasterProductMenu();
}

function refreshProductStatusUi() {
  syncCollectBarVisibility();
  updateProductStatusCounts();
}

function currentMarketStatusRows() {
  let rows = productsInMarketScope(marketFilter, masterChannelFilter);
  if (productFilter === "url") rows = rows.filter((item) => !productWholesalerId(item));
  else if (productFilter && productFilter !== "all") {
    rows = rows.filter((item) => productWholesalerId(item) === productFilter);
  }
  if (productQuery.trim()) rows = rows.filter(matchesProductQuery);
  return rows;
}

function syncCollectBarVisibility() {
  const onMaster = isMasterProductMenu();
  const onStore = isStoreProductMenu();
  const showCollect = onMaster && !document.body.classList.contains("edition-test");
  document.body.classList.toggle("viewing-source-products", isSourceProductMenu());
  document.body.classList.toggle("viewing-master-products", onMaster);
  document.body.classList.toggle("viewing-market-products", onStore);
  document.body.classList.toggle("url-collect-on", showCollect);
  const form = $("#collectForm");
  if (form) {
    form.hidden = !showCollect;
    form.setAttribute("aria-hidden", showCollect ? "false" : "true");
  }
  const statusBox = $("#productStatusFilters");
  if (statusBox) {
    statusBox.hidden = !onStore;
    if (!onStore && productStatusFilter !== "all") productStatusFilter = "all";
  }
}

function updateProductStatusCounts() {
  const box = $("#productStatusFilters");
  const onStore = isStoreProductMenu();
  if (box) box.hidden = !onStore;
  if (!box || !onStore) return;
  const counts = statusCountsOf(currentMarketStatusRows());
  box.querySelectorAll("[data-status-count]").forEach((node) => {
    const key = node.getAttribute("data-status-count");
    node.textContent = String(counts[key] || 0);
  });
  box.querySelectorAll("[data-status-filter]").forEach((button) => {
    button.classList.toggle("active", button.getAttribute("data-status-filter") === productStatusFilter);
  });
  box.title = formatStatusCountLabel(counts);
}

function patchLocalProduct(id, patch) {
  const index = products.findIndex((row) => row.id === id);
  if (index < 0) return;
  products[index] = { ...products[index], ...patch };
  if (current?.id === id) current = products[index];
}

function isMasterProduct(item) {
  return !item?.master_id && !item?.market_id;
}

function masterIdsInChannel(channelId) {
  const ids = new Set(marketsForChannel(channelId).map((item) => item.id));
  return new Set(products
    .filter((item) => item.master_id && item.market_id && ids.has(item.market_id))
    .map((item) => item.master_id));
}

function productsInMarkets(ids) {
  return products.filter((item) => item.market_id && ids.has(item.market_id));
}

function channelProducts(channelId) {
  return productsInMarkets(new Set(marketsForChannel(channelId).map((item) => item.id)));
}

function channelProductCount(channelId) {
  return channelProducts(channelId).length;
}

const PRODUCT_MENUS = {
  source: ["viewCollectedButton", "sendMarketButton", "refreshOriginalButton", "deleteButton", "openNameKeywords"],
  master: ["viewCollectedButton", "sendMarketButton", "refreshOriginalButton", "deleteButton", "openNameKeywords"],
};

function productMenuId() {
  if (marketFilter === "all") return "source";
  if (marketFilter === "master") return "master";
  if (accountChannels().some((item) => item.id === marketFilter)) return marketFilter;
  const market = markets.find((item) => item.id === marketFilter);
  if (market) return marketChannel(market);
  return "default";
}

function applyProductMenu() {
  const allowed = PRODUCT_MENUS[productMenuId()];
  document.querySelectorAll("#productToolbar .tool-group > button").forEach((button) => {
    if (!allowed) {
      const smartstore = productMenuId() === "smartstore";
      if (button.id === "viewCollectedButton" || button.id === "viewRegisteredButton") {
        button.hidden = !smartstore;
        return;
      }
      if (button.id === "refreshOriginalButton") {
        button.hidden = true;
        return;
      }
      if (button.id === "refreshMarketButton") {
        button.hidden = false;
        return;
      }
      button.hidden = smartstore && (button.id === "sendMarketButton" || button.id === "saveButton");
      return;
    }
    button.hidden = !allowed.includes(button.id);
  });
  const sourceView = productMenuId() === "source" || productMenuId() === "master";
  const refresh = $("#productRefreshOriginal");
  if (refresh) refresh.hidden = !sourceView;
  const marketRefresh = $("#productRefreshMarket");
  if (marketRefresh) marketRefresh.hidden = sourceView;
}

function marketFilterLabel() {
  if (marketFilter === "all") return "원본상품";
  if (marketFilter === "master") {
    if (!masterChannelFilter) return "마스터상품";
    return `마스터상품 / ${channelById(masterChannelFilter).name}`;
  }
  const channel = channelById(marketFilter);
  if (accountChannels().some((item) => item.id === marketFilter)) return channel.name;
  const market = markets.find((item) => item.id === marketFilter);
  if (!market) return "마켓";
  const parent = channelById(marketChannel(market)).name;
  const name = market.name || market.slug || market.url || market.id;
  return parent === name ? name : `${parent} / ${name}`;
}

function wholesaleProductCount(wholesalerId) {
  return products.filter((item) => productWholesalerId(item) === wholesalerId && isMasterProduct(item)).length;
}

function dateText(value) {
  return String(value || "").slice(0, 10);
}

function formatOptionValue(value, extra) {
  const amount = Number(extra || 0);
  return amount ? `${value}(${amount > 0 ? "+" : ""}${amount})` : value;
}

function formatOptions(options) {
  return (options || []).map((item) => {
    const extras = item.extras || [];
    const values = (item.values || []).map((value, index) => formatOptionValue(value, extras[index]));
    return `${item.name}: ${values.join(",")}`;
  }).join(" | ");
}

function isCertificationAttribute(name) {
  const text = String(name || "").replace(/\s+/g, "").toLowerCase();
  return ["인증", "kc", "안전확인", "형식승인", "전파인증", "전자파적합", "공급자적합"].some((token) => text.includes(token));
}

function isEnergyEfficiencyAttribute(name) {
  const text = String(name || "").replace(/\s+/g, "").toLowerCase();
  return ["에너지효율", "에너지소비효율", "소비효율등급"].some((token) => text.includes(token));
}

function isAsAttribute(name) {
  const text = String(name || "").replace(/\s+/g, "").toLowerCase();
  if (!text || isEnergyEfficiencyAttribute(name)) return false;
  const compact = text.replace(/\//g, "");
  return ["as", "as기간", "품질보증", "품질보증기간", "보증기간", "보증"].includes(compact)
    || text.includes("a/s")
    || text.includes("보증기간")
    || text.includes("품질보증");
}

const DEFAULT_AS_GUIDE = "무상1년";
const LEGACY_AS_GUIDES = new Set([
  "제조사에 문의하세요",
  "상품 문의는 판매자에게 연락해 주세요.",
  "판매자에게 문의해 주세요.",
]);

function resolveAsGuide(...values) {
  for (const value of values) {
    const text = String(value || "").trim();
    if (text && !LEGACY_AS_GUIDES.has(text)) return text;
  }
  return DEFAULT_AS_GUIDE;
}

function asDefaultOption(attr) {
  const scored = (attr?.values || []).map((option) => {
    const label = String(option.label || option.max || "").replace(/\s+/g, "");
    let score = 0;
    if (label.includes("무상1년") || label === "1년무상") score = 3;
    else if (label.includes("무상") && /(?<!\d)1년/.test(label) && !label.includes("10년") && !label.includes("11년")) score = 2;
    else if (label === "1년" || label === "일년") score = 1;
    return { score, option };
  }).filter((row) => row.score).sort((a, b) => b.score - a.score);
  return scored[0]?.option || null;
}

function formatAttributes(attributes) {
  return (attributes || [])
    .filter((item) => !isCertificationAttribute(item.name) && !isEnergyEfficiencyAttribute(item.name))
    .map((item) => `${item.name}:${item.value}`)
    .join(" | ");
}

function displayAttributes(item) {
  if ((item.attributes || []).length) return formatAttributes(item.attributes);
  const schema = item.attribute_schema || [];
  const naver = item.naver_attributes || [];
  if (!schema.length || !naver.length) return "";
  const bySeq = new Map(schema.map((attr) => [Number(attr.attributeSeq), attr]));
  return naver.map((row) => {
    const attr = bySeq.get(Number(row.attributeSeq)) || {};
    const picked = (attr.values || []).find((value) => Number(value.attributeValueSeq) === Number(row.attributeValueSeq));
    if (isCertificationAttribute(attr.attributeName) || isEnergyEfficiencyAttribute(attr.attributeName)) return "";
    const text = row.attributeRealValue || picked?.label || "";
    return text ? `${attr.attributeName || row.attributeSeq}:${text}` : "";
  }).filter(Boolean).join(" | ");
}

function parseOptionToken(token) {
  const text = String(token || "").trim();
  const match = text.match(/^(.*)\(([+\-]?\d+)\)$/);
  if (match && match[1].trim()) {
    return { name: match[1].trim(), extra: Number(match[2]) };
  }
  return { name: text, extra: 0 };
}

function parseOptions(value) {
  return String(value || "").split("|").map((chunk) => chunk.trim()).filter(Boolean).map((chunk) => {
    const index = chunk.indexOf(":");
    if (index < 1) return null;
    const parsed = chunk.slice(index + 1).split(",").map((part) => parseOptionToken(part)).filter((item) => item.name);
    return {
      name: chunk.slice(0, index).trim(),
      values: parsed.map((item) => item.name),
      extras: parsed.map((item) => item.extra),
    };
  }).filter((item) => item && item.values.length);
}

function parseAttributes(value) {
  return String(value || "").split("|").map((chunk) => chunk.trim()).filter(Boolean).map((chunk) => {
    const index = chunk.indexOf(":");
    if (index < 1) return null;
    return { name: chunk.slice(0, index).trim(), value: chunk.slice(index + 1).trim() };
  }).filter((item) => item && item.value);
}

function parseTags(value) {
  return uniqueTags(String(value || "").split(/[,|#]/));
}

function cleanTag(tag) {
  return String(tag || "").replace(/\s+/g, "").replace(/[^0-9A-Za-z가-힣]/g, "").slice(0, 10);
}

function uniqueTags(tags, limit = 10) {
  const seen = [];
  for (const raw of tags || []) {
    const tag = cleanTag(raw);
    if (tag && !seen.includes(tag)) seen.push(tag);
    if (seen.length >= limit) break;
  }
  return seen;
}

function looksLikeUrl(value) {
  const text = String(value || "").trim();
  return /^(https?:\/\/|www\.)/i.test(text) || /^[a-z0-9.-]+\.[a-z]{2,}\//i.test(text);
}

function collectUrls() {
  const found = [];
  const top = $("#collectUrl").value.trim();
  if (top) found.push(...top.split(/\s+/).filter(Boolean));
  const list = $("#urlList")?.value || "";
  found.push(...list.split(/\r?\n/).map((line) => line.trim()));
  if (current?.source_url) found.push(current.source_url);
  const selectedInput = document.querySelector("#productTable tr.selected [data-field='source_url']");
  if (selectedInput?.value) found.push(selectedInput.value.trim());
  const unique = [];
  found.forEach((item) => {
    const url = item.replace(/^['"]|['"]$/g, "");
    if (url && !url.startsWith("#") && looksLikeUrl(url) && !unique.includes(url)) unique.push(url);
  });
  return unique;
}

function selectedProducts() {
  const found = visibleProducts().filter((item) => selectedIds.has(item.id));
  if (found.length) return found;
  if (current && visibleProducts().some((item) => item.id === current.id)) return [current];
  return [];
}

function requireSelected() {
  const items = selectedProducts();
  if (!items.length) {
    toast("먼저 왼쪽 체크박스나 행을 눌러 상품을 선택해 주세요.", true);
    return [];
  }
  return items;
}

function updateSelectionText() {}

function syncSelectAllBoxes() {
  const ids = visibleProducts().map((item) => item.id);
  const all = ids.length > 0 && ids.every((id) => selectedIds.has(id));
  const some = ids.some((id) => selectedIds.has(id));
  ["#selectAllProducts", "#selectAllOptions"].forEach((selector) => {
    const box = $(selector);
    if (!box) return;
    box.checked = all;
    box.indeterminate = some && !all;
  });
}

function setProductChecked(id, checked) {
  const on = Boolean(checked);
  if (selectedIds.has(id) === on) {
    document.querySelectorAll(`.grid tr[data-id="${id}"]`).forEach((row) => {
      row.classList.toggle("selected", on);
      const box = row.querySelector(".check-cell input");
      if (box) box.checked = on;
    });
    return;
  }
  if (on) {
    selectedIds.add(id);
    current = products.find((item) => item.id === id) || current;
  } else {
    selectedIds.delete(id);
    if (current?.id === id) current = products.find((item) => selectedIds.has(item.id)) || null;
  }
  document.querySelectorAll(`.grid tr[data-id="${id}"]`).forEach((row) => {
    row.classList.toggle("selected", on);
    const box = row.querySelector(".check-cell input");
    if (box) box.checked = on;
  });
  syncSelectAllBoxes();
  updateSelectionText();
  if (current) fillPreview();
}

function startCheckPaint(id, options = {}) {
  const next = Object.prototype.hasOwnProperty.call(options, "checked")
    ? Boolean(options.checked)
    : !selectedIds.has(id);
  checkPaintPending = null;
  checkPaint = { checked: next, startId: id };
  checkPaintDidDrag = true;
  document.body.classList.add("check-painting");
  setProductChecked(id, next);
}

function armCheckPaint(id, event, options = {}) {
  if (event.button !== 0) return false;
  checkPaintPending = {
    id,
    x: event.clientX,
    y: event.clientY,
    checked: Object.prototype.hasOwnProperty.call(options, "checked")
      ? Boolean(options.checked)
      : !selectedIds.has(id),
    additive: Boolean(options.additive),
    fromCheck: Boolean(options.fromCheck),
  };
  return true;
}

function moveCheckPaint(event) {
  if (!checkPaintPending || checkPaint) return;
  const dx = Math.abs(event.clientX - checkPaintPending.x);
  const dy = Math.abs(event.clientY - checkPaintPending.y);
  if (dx < 4 && dy < 4) return;
  startCheckPaint(checkPaintPending.id, { checked: checkPaintPending.checked });
}

function endCheckPaint() {
  const pending = checkPaintPending;
  const dragged = Boolean(checkPaint) || checkPaintDidDrag;
  checkPaintPending = null;
  if (checkPaint) {
    checkPaint = null;
    document.body.classList.remove("check-painting");
  }
  if (dragged) {
    setTimeout(() => {
      checkPaintDidDrag = false;
    }, 0);
    return;
  }
  if (!pending || pending.fromCheck) return;
  selectProduct(pending.id, false, Boolean(pending.additive));
}

function checkCell(item) {
  const cell = document.createElement("td");
  cell.className = "check-cell";
  const input = document.createElement("input");
  input.type = "checkbox";
  input.checked = selectedIds.has(item.id);
  input.title = "이 상품 선택. 끌어서 여러 개 선택";
  const arm = (event) => {
    event.preventDefault();
    event.stopPropagation();
    const checked = !selectedIds.has(item.id);
    armCheckPaint(item.id, event, { checked, fromCheck: true });
    startCheckPaint(item.id, { checked });
  };
  input.addEventListener("mousedown", arm);
  input.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
  });
  cell.addEventListener("mousedown", (event) => {
    if (event.target === input) return;
    arm(event);
  });
  cell.appendChild(input);
  return cell;
}

function bindCellControl(control, field) {
  control.dataset.field = field;
  control.addEventListener("click", (event) => event.stopPropagation());
  control.addEventListener("focus", () => {
    const id = control.closest("tr")?.dataset.id;
    if (!id) return;
    current = products.find((item) => item.id === id) || current;
    fillPreview();
    updateSelectionText();
  });
  control.addEventListener("change", () => {
    const id = control.closest("tr")?.dataset.id;
    queueSave(id ? { id } : current);
  });
}

function discountCell(item, locked = false) {
  if (locked) {
    const price = Number(item.discount_price || 0);
    if (!price) return textCell("");
    const unit = String(item.discount_unit || "WON").toUpperCase() === "PERCENT" ? "%" : "원";
    return textCell(`${price}${unit}`);
  }
  const cell = document.createElement("td");
  cell.className = "discount-cell";
  const input = document.createElement("input");
  input.type = "number";
  input.min = "0";
  input.step = "1";
  input.value = String(item.discount_price || 0);
  bindCellControl(input, "discount_price");
  const select = document.createElement("select");
  [["WON", "원"], ["PERCENT", "%"]].forEach(([itemValue, label]) => {
    const option = document.createElement("option");
    option.value = itemValue;
    option.textContent = label;
    if (String(item.discount_unit || "WON").toUpperCase() === itemValue) option.selected = true;
    select.appendChild(option);
  });
  bindCellControl(select, "discount_unit");
  cell.append(input, select);
  return cell;
}

function selectCell(value, field, options, locked = false) {
  if (locked) {
    const label = options.find(([itemValue]) => String(itemValue) === String(value))?.[1] || value || "";
    return textCell(label);
  }
  const cell = document.createElement("td");
  const select = document.createElement("select");
  options.forEach(([itemValue, label]) => {
    const option = document.createElement("option");
    option.value = itemValue;
    option.textContent = label;
    if (String(itemValue) === String(value)) option.selected = true;
    select.appendChild(option);
  });
  bindCellControl(select, field);
  cell.appendChild(select);
  return cell;
}

function categoryCell(item, locked = false) {
  const label = item.category_name || item.source_category || "";
  if (locked) return textCell(label);
  const cell = document.createElement("td");
  const button = document.createElement("button");
  button.type = "button";
  button.className = "category-pick";
  button.textContent = label || "카테고리 검색";
  button.title = label ? `${label} · 클릭해서 카테고리 검색` : "클릭해서 카테고리 검색";
  button.addEventListener("click", (event) => {
    event.stopPropagation();
    if (checkPaintDidDrag) return;
    current = products.find((row) => row.id === item.id) || item;
    openCategoryMapper([item.id]);
  });
  cell.appendChild(button);
  return cell;
}

function beginCellEdit(input) {
  if (!input) return;
  const view = input.closest("td")?.querySelector(".cell-view");
  if (view) view.hidden = true;
  input.hidden = false;
  input.focus();
  if (input.type === "text" || input.type === "search") input.select();
}

function inputCell(value, field, type = "text", locked = false) {
  if (locked) return textCell(value ?? "");
  const cell = document.createElement("td");
  cell.className = "cell-edit";
  const view = document.createElement("span");
  view.className = "cell-view";
  view.textContent = value ?? "";
  const input = document.createElement("input");
  input.type = type;
  input.value = value ?? "";
  input.hidden = true;
  bindCellControl(input, field);
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      input.blur();
    } else if (event.key === "Escape") {
      input.value = view.dataset.value ?? "";
      input.blur();
    }
  });
  input.addEventListener("blur", () => {
    view.textContent = input.value;
    view.dataset.value = input.value;
    input.hidden = true;
    view.hidden = false;
  });
  view.dataset.value = String(value ?? "");
  cell.addEventListener("dblclick", (event) => {
    if (event.target === input) return;
    event.preventDefault();
    event.stopPropagation();
    beginCellEdit(input);
  });
  cell.append(view, input);
  return cell;
}

function sourceUrlCell(item, locked = false) {
  const url = String(item?.source_url || "");
  const cell = locked ? textCell(url) : inputCell(url, "source_url", "text", false);
  cell.classList.add("source-url-cell");
  if (!looksLikeUrl(url) && locked) return cell;
  const open = document.createElement("button");
  open.type = "button";
  open.className = "source-url-open";
  open.textContent = "열기";
  open.title = "로그인 Chrome에서 공급사 상품 보기";
  open.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    const live =
      cell.querySelector("[data-field='source_url']")?.value ||
      cell.querySelector(".cell-view")?.dataset?.value ||
      url;
    const product = products.find((row) => row.id === item.id) || item;
    openSupplierProductUrl(
      live,
      productWholesalerId(product) || guessWholesalerIdFromUrl(live),
      "수집한 상품 URL이 없습니다."
    );
  });
  cell.appendChild(open);
  return cell;
}

const MASTER_LOCK_MESSAGE = "마스터상품은 원본이라 직접 고칠 수 없습니다. 마켓으로 보낸 상품에서 수정하세요.";

function masterEditBlocked(product = current) {
  if (!isMasterProduct(product)) return false;
  toast(MASTER_LOCK_MESSAGE, true);
  return true;
}

function detailCell(item) {
  if (isMasterProduct(item)) return textCell(item.detail_html || "");
  const cell = inputCell(item.detail_html || "", "detail_html");
  const view = cell.querySelector(".cell-view");
  if (view) view.title = "더블클릭하면 크게 편집합니다";
  cell.addEventListener("dblclick", (event) => {
    event.preventDefault();
    event.stopPropagation();
    current = products.find((row) => row.id === item.id) || current;
    selectedIds.add(item.id);
    openDetailEditor();
  }, true);
  return cell;
}

function dialogEditCell(text, title, onOpen) {
  const cell = document.createElement("td");
  cell.className = "cell-edit cell-dialog-edit";
  cell.title = title;
  const view = document.createElement("span");
  view.className = "cell-view";
  view.textContent = text || "";
  view.title = title;
  cell.appendChild(view);
  cell.addEventListener("dblclick", (event) => {
    event.preventDefault();
    event.stopPropagation();
    onOpen();
  });
  return cell;
}

function tagsCell(item) {
  const text = (item.tags || []).join(",");
  if (isMasterProduct(item)) return textCell(text);
  return dialogEditCell(text, "더블클릭하면 태그 창에서 수정합니다", () => {
    current = products.find((row) => row.id === item.id) || item;
    selectedIds.add(item.id);
    openTagEditor();
  });
}

function attributesCell(item) {
  const text = displayAttributes(item);
  if (isMasterProduct(item)) return textCell(text);
  return dialogEditCell(text, "더블클릭하면 속성 창에서 수정합니다", () => {
    current = products.find((row) => row.id === item.id) || item;
    selectedIds.add(item.id);
    openAttributeEditor().catch((error) => toast(error.message, true));
  });
}

function orderActionButton(label, className, onClick) {
  const cell = document.createElement("td");
  const button = document.createElement("button");
  button.type = "button";
  button.className = className;
  button.textContent = label;
  button.addEventListener("click", onClick);
  cell.appendChild(button);
  return cell;
}

function orderCancelCell(item) {
  return orderActionButton("판매취소하기", "order-cancel-link", () => openOrderCancel(item));
}

function orderProductCell(item) {
  const number = item.channel_product_no || item.product_no || "";
  const href = orderProductUrl(item);
  if (!String(number).trim() && !href) return textCell("");
  if (!href) return textCell(number);
  return linkedNumberCell(number || "상품페이지", href, "스마트스토어 상품 페이지");
}

const ORDER_CANCEL_REASONS = [
  ["SOLD_OUT", "상품 품절"],
  ["DELAYED_DELIVERY", "배송 지연"],
  ["PRODUCT_UNSATISFIED", "서비스 및 상품 불만족"],
  ["INTENT_CHANGED", "구매 의사 취소"],
  ["INCORRECT_INFO", "상품 정보 상이"],
  ["BROKEN", "상품 파손"],
  ["WRONG_ORDER", "다른 상품 잘못 주문"],
  ["COLOR_AND_SIZE", "색상 및 사이즈 변경"],
];
let cancelOrderId = "";

function fillOrderCancelReasons() {
  const select = $("#orderCancelReason");
  if (!select || select.options.length) return;
  ORDER_CANCEL_REASONS.forEach(([value, label]) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.appendChild(option);
  });
}

function openOrderCancel(item) {
  fillOrderCancelReasons();
  cancelOrderId = item.id;
  const summary = $("#orderCancelSummary");
  if (summary) summary.textContent = `${item.product_name || "상품"} / ${item.product_order_id || item.order_id || ""}`;
  const detail = $("#orderCancelDetail");
  if (detail) detail.value = "";
  const dialog = $("#orderCancelDialog");
  if (!dialog) return;
  if (dialog.open) dialog.close();
  dialog.showModal();
}

function orderNumberCell(item) {
  const cell = document.createElement("td");
  const number = item.product_order_id || item.order_id || "";
  if (!number) return cell;
  const button = document.createElement("button");
  button.type = "button";
  button.className = "order-no-link";
  button.textContent = number;
  button.title = "주문 내용 보기";
  button.addEventListener("click", (event) => {
    event.stopPropagation();
    openOrderInfo(item);
  });
  cell.appendChild(button);
  return cell;
}

function findOrderByNumber(number, marketId) {
  const no = String(number || "").trim();
  if (!no) return null;
  const matches = (orders || []).filter((item) => {
    const ids = [item.order_id, item.product_order_id].map((value) => String(value || "").trim());
    return ids.includes(no);
  });
  if (!matches.length) return null;
  if (marketId) {
    const local = matches.find((item) => item.market_id === marketId);
    if (local) return local;
  }
  return matches[0];
}

async function openOrderByNumber(number, marketId) {
  const no = String(number || "").trim();
  if (!no) {
    toast("주문번호가 없습니다.", true);
    return;
  }
  let item = findOrderByNumber(no, marketId);
  if (!item) {
    try {
      setBusy(true, "주문 내용을 찾는 중입니다.");
      await loadOrders({ quiet: true });
      item = findOrderByNumber(no, marketId);
    } catch (error) {
      toast(error.message || "주문을 불러오지 못했습니다.", true);
      return;
    } finally {
      setBusy(false);
    }
  }
  if (!item) {
    toast("수집된 주문에서 이 번호를 찾지 못했습니다. 주문관리에서 먼저 주문을 수집해 주세요.", true);
    return;
  }
  openOrderInfo(item);
}

function inquiryOrderCell(item) {
  const number = item.order_id || item.product_order_id || "";
  if (!String(number).trim()) return textCell("");
  const cell = document.createElement("td");
  const button = document.createElement("button");
  button.type = "button";
  button.className = "order-no-link";
  button.textContent = number;
  button.title = "주문 내용 보기";
  button.addEventListener("click", (event) => {
    event.stopPropagation();
    openOrderByNumber(number, item.market_id).catch((error) => toast(error.message, true));
  });
  cell.appendChild(button);
  return cell;
}

function textCell(value) {
  const cell = document.createElement("td");
  cell.textContent = value ?? "";
  cell.title = String(value ?? "");
  return cell;
}

function marketSlug(market) {
  const slug = String(market?.slug || "").trim();
  if (slug) return slug;
  return storeSlug(market?.url || "");
}

function smartstoreProductUrl(number, market) {
  const no = String(number || "").trim();
  if (!/^\d{6,}$/.test(no)) return "";
  const slug = marketSlug(market);
  if (slug) return `https://smartstore.naver.com/${encodeURIComponent(slug)}/products/${no}`;
  const base = String(market?.url || "").replace(/\/$/, "");
  if (/^https?:\/\/(?:smartstore|brand)\.naver\.com\//i.test(base)) return `${base}/products/${no}`;
  return `https://smartstore.naver.com/main/products/${no}`;
}

function channelProductHref(item) {
  const direct = String(item?.store_product_url || "").trim();
  const no = String(item?.channel_product_no || "").trim();
  const naver = /smartstore\.naver\.com|brand\.naver\.com/i.test(direct);
  if (naver && (!no || direct.includes(no) || /\/products\/\d+/.test(direct))) return direct;
  return smartstoreProductUrl(no, {
    slug: storeSlug(direct || item?.source_url),
    url: direct,
  });
}

function sellerOriginProductUrl(number) {
  const no = String(number || "").trim();
  if (!/^\d{6,}$/.test(no)) return "";
  return `https://sell.smartstore.naver.com/#/products/origin-product/${no}`;
}

function openProductHref(href, emptyMessage) {
  const url = String(href || "").trim();
  if (!url) {
    toast(emptyMessage || "상품 페이지 주소가 없습니다.", true);
    return false;
  }
  const popup = window.open(url, "_blank", "noopener,noreferrer");
  if (popup) {
    try { popup.focus(); } catch (_) {}
    return true;
  }
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.target = "_blank";
  anchor.rel = "noopener noreferrer";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  return true;
}

function linkedNumberCell(number, href, title) {
  const cell = document.createElement("td");
  const no = String(number || "").trim();
  cell.title = title || no;
  if (!no) return cell;
  if (!href) {
    cell.textContent = no;
    return cell;
  }
  const button = document.createElement("button");
  button.type = "button";
  button.className = "order-product-link product-no-link";
  button.textContent = no;
  button.title = title || "상품 페이지 열기";
  button.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    openProductHref(href, "상품 페이지 주소가 없습니다.");
  });
  cell.appendChild(button);
  return cell;
}

function setLinkedText(node, text, href, title) {
  if (!node) return;
  node.replaceChildren();
  const value = String(text || "");
  if (!value) return;
  if (!href) {
    node.textContent = value;
    return;
  }
  const button = document.createElement("button");
  button.type = "button";
  button.className = "order-product-link product-no-link";
  button.textContent = value;
  button.title = title || "상품 페이지 열기";
  button.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    openProductHref(href, "상품 페이지 주소가 없습니다.");
  });
  node.appendChild(button);
}

function productFromRow(row, product) {
  const value = (field) => row.querySelector(`[data-field="${field}"]`)?.value ?? "";
  return {
    name: value("name"),
    model: value("model"),
    category_name: product.category_name || "",
    category_keyword: product.category_keyword || "",
    source_url: value("source_url") || product.source_url,
    stock: Number(value("stock") || 0),
    cost: Number(value("cost") || 0),
    price: Number(value("price") || 0),
    brand: value("brand"),
    manufacturer: value("manufacturer"),
    origin: value("origin"),
    as_phone: value("as_phone"),
    as_guide: value("as_guide"),
    tags: row.querySelector(`[data-field="tags"]`)
      ? parseTags(value("tags"))
      : (product.tags || []),
    options: parseOptions(value("options")),
    option_combinations: product.option_combinations || [],
    attributes: row.querySelector(`[data-field="attributes"]`)
      ? parseAttributes(value("attributes"))
      : (product.attributes || []),
    discount_price: Number(value("discount_price") || 0),
    discount_unit: value("discount_unit") || "WON",
    tax_type: value("tax_type") || "TAX",
    sale_status: value("sale_status") || product.sale_status || "SALE",
    display_status: value("display_status") || product.display_status || "ON",
    display: (value("sale_status") || product.sale_status || "SALE") === "SALE",
    minor_purchasable: value("minor_purchasable") !== "false",
    seller_code: value("seller_code"),
    detail_html: value("detail_html") || product.detail_html || "",
    extra_components: value("extra_components"),
    option_type: value("option_type") || "COMBINATION",
    certification: value("certification"),
    certification_date: value("certification_date"),
    main_ingredient: value("main_ingredient"),
    manufacture_date: value("manufacture_date"),
    expire_date: value("expire_date"),
    unit_price: value("unit_price"),
    memo: value("memo"),
    summary: value("summary"),
    images: product.images || [],
    category_id: product.category_id || "",
  };
}

async function loadProducts() {
  const previous = current?.id;
  products = await fetchProductList();
  selectedIds = new Set([...selectedIds].filter((id) => products.some((item) => item.id === id)));
  if (previous && products.some((item) => item.id === previous)) {
    current = products.find((item) => item.id === previous);
  } else if (!products.some((item) => item.id === current?.id)) {
    current = products[products.length - 1] || null;
  }
  if (current && visibleProducts().some((item) => item.id === current.id)) selectedIds.add(current.id);
  else if (current && !visibleProducts().some((item) => item.id === current.id)) {
    current = visibleProducts().slice(-1)[0] || null;
    if (current) selectedIds.add(current.id);
  }
  renderSheets();
  fillPreview();
  updateSelectionText();
  updateFilterCount();
  renderWholesalerSheet();
  fillMarketTree();
}

function renderSheets() {
  renderProductSheet();
  renderOptionSheet();
  refreshProductStatusUi();
}

function renderProductSheet() {
  const body = $("#productTable");
  if (!body) return;
  body.innerHTML = "";
  visibleProducts().forEach((item, index) => {
    const row = document.createElement("tr");
    if (selectedIds.has(item.id)) row.classList.add("selected");
    if (item.wholesale_soldout) row.classList.add("soldout-row");
    row.dataset.id = item.id;
    const locked = isMasterProduct(item);
    if (locked) row.title = MASTER_LOCK_MESSAGE;
    row.append(
      checkCell(item),
      textCell(index + 1),
      textCell(dateText(item.created_at)),
      textCell(STATUS[item.status] || item.status),
      textCell(item.wholesale_soldout ? "품절" : (productWholesalerId(item) ? "정상" : "")),
      textCell(item.wholesale_name || ""),
      textCell(item.market_name || ""),
      categoryCell(item, locked),
      inputCell(item.seller_code || item.model || "", "seller_code", "text", locked),
      inputCell(item.model || "", "model", "text", locked),
      inputCell(item.name || "", "name", "text", locked),
      inputCell(item.stock || 0, "stock", "number", locked),
      inputCell(item.cost || 0, "cost", "number", locked),
      inputCell(item.price || 0, "price", "number", locked),
      inputCell(item.brand || "", "brand", "text", locked),
      inputCell(item.manufacturer || "", "manufacturer", "text", locked),
      inputCell(item.origin || "", "origin", "text", locked),
      inputCell(locked ? "" : (item.as_phone || ""), "as_phone", "text", locked),
      inputCell(resolveAsGuide(item.as_guide), "as_guide", "text", locked),
      tagsCell(item),
      inputCell(formatOptions(item.options), "options", "text", locked),
      attributesCell(item),
      discountCell(item, locked),
      selectCell(item.tax_type || "TAX", "tax_type", [["TAX", "과세"], ["DUTYFREE", "면세"], ["SMALL", "영세"]], locked),
      selectCell(item.minor_purchasable === false ? "false" : "true", "minor_purchasable", [["true", "가능"], ["false", "불가"]], locked),
      sourceUrlCell(item, locked),
      detailCell(item),
      inputCell(item.extra_components || "", "extra_components", "text", locked),
      selectCell(item.option_type || "COMBINATION", "option_type", [["COMBINATION", "조합형"], ["SIMPLE", "단독형"]], locked),
      inputCell(item.certification || "", "certification", "text", locked),
      inputCell(item.certification_date || "", "certification_date", "text", locked),
      inputCell(item.main_ingredient || "", "main_ingredient", "text", locked),
      inputCell(item.manufacture_date || "", "manufacture_date", "text", locked),
      inputCell(item.expire_date || "", "expire_date", "text", locked),
      inputCell(item.unit_price || "", "unit_price", "text", locked),
      inputCell(item.memo || "", "memo", "text", locked),
      inputCell(item.summary || "", "summary", "text", locked),
      linkedNumberCell(item.origin_product_no || "", sellerOriginProductUrl(item.origin_product_no), "스마트스토어 판매자센터 원상품"),
      linkedNumberCell(item.channel_product_no || "", channelProductHref(item), "스마트스토어 상품 페이지"),
    );
    bindRowSelection(row, item.id);
    body.appendChild(row);
  });
  syncSelectAllBoxes();
}

function renderOptionSheet() {
  const body = $("#optionTable");
  body.innerHTML = "";
  let number = 1;
  visibleProducts().forEach((item) => {
    const options = item.options || [];
    const attributes = item.attributes || [];
    if (!options.length && !attributes.length) {
      body.appendChild(optionRow(number++, item, "상품", "", "상품정보", item.name || "", item));
    }
    options.forEach((group) => {
      body.appendChild(optionRow(number++, item, "옵션", "simpleoption", group.name || "옵션", (group.values || []).map((value, index) => formatOptionValue(value, (group.extras || [])[index])).join(","), item));
    });
    attributes.forEach((attr) => {
      body.appendChild(optionRow(number++, item, "속성", "attributevalue", attr.name || "", attr.value || "", item));
    });
  });
}

function optionRow(number, product, kind, type, name, value, source) {
  const row = document.createElement("tr");
  if (selectedIds.has(product.id)) row.className = "selected";
  row.dataset.id = product.id;
  row.dataset.kind = kind;
  const locked = isMasterProduct(product);
  if (locked) row.title = MASTER_LOCK_MESSAGE;
  [
    checkCell(product),
    textCell(number),
    textCell(product.name || ""),
    textCell(kind),
    textCell(type),
    inputCell(name, "attr_name", "text", locked),
    inputCell(value, "attr_value", "text", locked),
    inputCell(source.brand || "", "brand", "text", locked),
    inputCell(source.manufacturer || "", "manufacturer", "text", locked),
    inputCell(source.origin || "", "origin", "text", locked),
    inputCell(source.certification || "", "certification", "text", locked),
    inputCell(source.certification_date || "", "certification_date", "text", locked),
  ].forEach((cell) => row.appendChild(cell));
  bindRowSelection(row, product.id);
  if (!locked) {
    row.querySelectorAll("input").forEach((input) => {
      input.addEventListener("change", () => saveOptionRow(row, product.id));
    });
  }
  return row;
}

function toggleProduct(id, checked, keepOthers = true) {
  if (!keepOthers) {
    const keep = checked ? new Set([id]) : new Set();
    [...selectedIds].forEach((other) => {
      if (!keep.has(other)) setProductChecked(other, false);
    });
  }
  setProductChecked(id, checked);
}

function bindRowSelection(row, id) {
  row.addEventListener("mousedown", (event) => {
    if (event.button !== 0) return;
    if (event.target.closest(".check-cell")) return;
    if (event.target.closest("input:not([hidden]), select, textarea, a, .source-url-open")) return;
    if (event.target.closest("td.cell-edit") && event.detail >= 2) return;
    armCheckPaint(id, event, {
      checked: true,
      additive: event.ctrlKey || event.metaKey || event.shiftKey,
    });
  });
  row.addEventListener("mouseenter", () => {
    if (checkPaintPending && checkPaintPending.id !== id) {
      startCheckPaint(checkPaintPending.id, { checked: checkPaintPending.checked });
    }
    if (!checkPaint) return;
    setProductChecked(id, checkPaint.checked);
  });
}

const PRODUCT_CACHE_DB = "modumodu-product-cache";
const PRODUCT_CACHE_STORE = "products";
const PRODUCT_FULL_RELOAD_LIMIT = 150;
const productCache = new Map();
let productCacheReady = null;

function openProductCacheDb() {
  return new Promise((resolve) => {
    if (!window.indexedDB) {
      resolve(null);
      return;
    }
    let request;
    try {
      request = indexedDB.open(PRODUCT_CACHE_DB, 1);
    } catch {
      resolve(null);
      return;
    }
    request.onupgradeneeded = () => request.result.createObjectStore(PRODUCT_CACHE_STORE);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => resolve(null);
    request.onblocked = () => resolve(null);
  });
}

async function readProductCache() {
  const db = await openProductCacheDb();
  if (!db) return;
  await new Promise((resolve) => {
    const tx = db.transaction(PRODUCT_CACHE_STORE, "readonly");
    const request = tx.objectStore(PRODUCT_CACHE_STORE).openCursor();
    request.onsuccess = () => {
      const cursor = request.result;
      if (!cursor) return;
      if (cursor.value?.product) productCache.set(cursor.key, cursor.value);
      cursor.continue();
    };
    tx.oncomplete = resolve;
    tx.onerror = resolve;
    tx.onabort = resolve;
  });
  db.close();
}

async function writeProductCache(changedIds, removedIds) {
  if (!changedIds.length && !removedIds.length) return;
  const db = await openProductCacheDb();
  if (!db) return;
  await new Promise((resolve) => {
    const tx = db.transaction(PRODUCT_CACHE_STORE, "readwrite");
    const store = tx.objectStore(PRODUCT_CACHE_STORE);
    changedIds.forEach((id) => {
      const entry = productCache.get(id);
      if (entry) store.put(entry, id);
    });
    removedIds.forEach((id) => store.delete(id));
    tx.oncomplete = resolve;
    tx.onerror = resolve;
    tx.onabort = resolve;
  });
  db.close();
}

async function runLimited(items, limit, worker) {
  let next = 0;
  const lanes = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (next < items.length) {
      const item = items[next++];
      await worker(item);
    }
  });
  await Promise.all(lanes);
}

// /api/products?full=1 re-reads every product file on each call; reuse full copies whose summary row is unchanged.
async function fetchProductList() {
  const summaries = await api("/api/products");
  if (!Array.isArray(summaries)) return api("/api/products?full=1");
  if (!productCacheReady) productCacheReady = readProductCache().catch(() => {});
  await productCacheReady;
  const sigs = new Map(summaries.map((item) => [item.id, JSON.stringify(item)]));
  const stale = summaries.filter((item) => productCache.get(item.id)?.sig !== sigs.get(item.id)).map((item) => item.id);
  const changed = [];
  if (stale.length > PRODUCT_FULL_RELOAD_LIMIT) {
    const full = await api("/api/products?full=1");
    full.forEach((product) => {
      if (!sigs.has(product.id)) return;
      productCache.set(product.id, { sig: sigs.get(product.id), product });
      changed.push(product.id);
    });
  } else {
    await runLimited(stale, 6, async (id) => {
      try {
        const product = await api(`/api/products/${id}`, { quiet: true });
        productCache.set(id, { sig: sigs.get(id), product });
        changed.push(id);
      } catch {
        productCache.delete(id);
      }
    });
  }
  const removed = [...productCache.keys()].filter((id) => !sigs.has(id));
  removed.forEach((id) => productCache.delete(id));
  writeProductCache(changed, removed).catch(() => {});
  return summaries
    .filter((item) => productCache.has(item.id))
    .map((item) => structuredClone(productCache.get(item.id).product));
}

async function refreshCachedProduct(id) {
  const entry = productCache.get(id);
  if (!entry) return;
  let fresh;
  try {
    fresh = await api(`/api/products/${id}`, { quiet: true });
  } catch {
    return;
  }
  if (JSON.stringify(fresh) === JSON.stringify(entry.product)) return;
  productCache.set(id, { sig: entry.sig, product: fresh });
  writeProductCache([id], []).catch(() => {});
  const index = products.findIndex((item) => item.id === id);
  if (index >= 0) products[index] = structuredClone(fresh);
  if (current?.id === id) {
    current = products[index] || structuredClone(fresh);
    fillPreview();
  }
}

async function selectProduct(id, rerender = true, additive = false) {
  current = products.find((item) => item.id === id) || await api(`/api/products/${id}`);
  refreshCachedProduct(id);
  if (!additive) selectedIds.clear();
  selectedIds.add(id);
  if (rerender) renderSheets();
  else {
    document.querySelectorAll(".grid tr[data-id]").forEach((row) => {
      const on = selectedIds.has(row.dataset.id);
      row.classList.toggle("selected", on);
      const box = row.querySelector(".check-cell input");
      if (box) box.checked = on;
    });
    syncSelectAllBoxes();
  }
  fillPreview();
  updateSelectionText();
}

function selectAllProducts(checked) {
  const rows = visibleProducts();
  selectedIds = checked ? new Set(rows.map((item) => item.id)) : new Set();
  if (checked) current = current || rows[rows.length - 1] || null;
  else current = null;
  renderSheets();
  if (current) fillPreview();
  updateSelectionText();
}

const refitDone = new Set();

function gallerySrc(product, image) {
  if (!product || !image) return "";
  if (image.file) return `/media/${product.id}/${image.file}?v=${encodeURIComponent(product.updated_at || image.width || 0)}`;
  if (image.source_url) return `/api/image-proxy?url=${encodeURIComponent(image.source_url)}`;
  return "";
}

function fillPreview() {
  if (!current) {
    $("#previewImage").src = "";
    $("#previewImage").alt = "";
    $("#previewText").textContent = "상품을 선택하면 대표이미지가 여기에 보입니다.";
    $("#imageStrip").innerHTML = "";
    $("#warningBox").hidden = true;
    $("#resultBox").hidden = true;
    return;
  }
  ensureGalleryFit(current);
  const gallery = (current.images || []).find((image) => image.representative) || (current.images || []).find((image) => image.kind === "gallery");
  $("#previewImage").src = gallerySrc(current, gallery);
  $("#previewImage").alt = current.name || "대표이미지";
  $("#previewText").textContent = current.name || "";
  const warnings = (current.warnings || []).filter((text) => !/원가\(공급가\)는 (도매처|공급처) 로그인|(도매처|공급처)에서 품절입니다/.test(String(text || "")));
  $("#warningBox").hidden = warnings.length === 0;
  $("#warningBox").textContent = warnings.join(" ");
  const registered = current.origin_product_no
    ? `원상품번호 ${current.origin_product_no} / 채널상품번호 ${current.channel_product_no || "-"}`
    : "";
  $("#resultBox").hidden = !registered;
  $("#resultBox").textContent = registered;
  const strip = $("#imageStrip");
  strip.innerHTML = "";
  (current.images || []).filter((image) => image.kind === "gallery").forEach((image) => {
    const img = document.createElement("img");
    img.alt = "상품 이미지";
    img.src = gallerySrc(current, image);
    if (image.representative) img.className = "representative";
    img.addEventListener("click", async (event) => {
      event.stopPropagation();
      if (isMasterProduct(current)) return;
      current.images.forEach((item) => { if (item.kind === "gallery") item.representative = false; });
      image.representative = true;
      await saveProduct(current, { images: current.images });
    });
    strip.appendChild(img);
  });
}

function queueSave(product) {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => saveCurrentRow(product?.id, true), 250);
}

async function saveCurrentRow(id, quiet = false) {
  const targetId = id || current?.id;
  if (!targetId) return;
  const row = document.querySelector(`#productTable tr[data-id="${targetId}"]`);
  const product = products.find((item) => item.id === targetId);
  if (!row || !product || isMasterProduct(product)) return;
  const patch = productFromRow(row, product);
  if (!(patch.attributes || []).length) delete patch.attributes;
  await saveProduct(product, patch, quiet);
}

async function saveOptionRow(row, productId) {
  const product = products.find((item) => item.id === productId);
  if (!product || isMasterProduct(product)) return;
  const value = (field) => row.querySelector(`[data-field="${field}"]`)?.value ?? "";
  const patch = {
    brand: value("brand"),
    manufacturer: value("manufacturer"),
    origin: value("origin"),
    certification: value("certification"),
    certification_date: value("certification_date"),
  };
  const kind = row.dataset.kind;
  const name = value("attr_name");
  const raw = value("attr_value");
  if (kind === "옵션") {
    const options = [...(product.options || [])];
    const index = [...row.parentElement.querySelectorAll(`tr[data-id="${productId}"][data-kind="옵션"]`)].indexOf(row);
    if (index >= 0) {
      const parsed = raw.split(",").map((part) => parseOptionToken(part)).filter((item) => item.name);
      options[index] = { name, values: parsed.map((item) => item.name), extras: parsed.map((item) => item.extra) };
    }
    patch.options = options;
  }
  if (kind === "속성") {
    const attributes = [...(product.attributes || [])];
    const index = [...row.parentElement.querySelectorAll(`tr[data-id="${productId}"][data-kind="속성"]`)].indexOf(row);
    if (index >= 0) attributes[index] = { name, value: raw };
    patch.attributes = attributes;
  }
  await saveProduct(product, patch, true);
}

const PRODUCT_UNDO_FIELDS = [
  "name", "price", "cost", "stock", "brand", "manufacturer", "origin", "as_phone", "as_guide",
  "certification", "certification_date", "model", "category_id", "category_name", "category_keyword",
  "source_category", "tags", "attributes", "options", "naver_attributes", "detail_html", "summary",
  "display", "sale_status", "display_status", "discount_price", "discount_unit", "tax_type",
  "minor_purchasable", "seller_code", "extra_components", "option_type", "option_combinations",
  "input_options", "main_ingredient", "manufacture_date", "expire_date", "unit_price", "memo",
  "images", "notice_ids",
];
const productUndo = [];
const productRedo = [];
let productUndoGroup = null;
let undoingProduct = false;
let redoingProduct = false;

function productSnapshot(product) {
  if (!product?.id) return null;
  const fields = {};
  PRODUCT_UNDO_FIELDS.forEach((key) => {
    if (!(key in product) || product[key] === undefined) return;
    fields[key] = structuredClone(product[key]);
  });
  return { id: product.id, fields };
}

function findProductState(id) {
  return products.find((item) => item.id === id) || (current?.id === id ? current : null);
}

function beginProductUndoGroup(label = "") {
  if (productUndoGroup) endProductUndoGroup();
  productUndoGroup = { label: String(label || ""), entries: [] };
}

function endProductUndoGroup() {
  const group = productUndoGroup;
  productUndoGroup = null;
  if (!group?.entries?.length) return;
  productUndo.push({ type: "group", label: group.label, entries: group.entries });
  if (productUndo.length > 30) productUndo.shift();
  productRedo.length = 0;
}

function cancelProductUndoGroup() {
  productUndoGroup = null;
}

function rememberProductUndo(product) {
  if (undoingProduct || redoingProduct || !product?.id) return;
  const snap = productSnapshot(product);
  if (!snap) return;
  if (productUndoGroup) {
    if (!productUndoGroup.entries.some((item) => item.id === snap.id)) {
      productUndoGroup.entries.push(snap);
    }
    return;
  }
  productUndo.push(snap);
  if (productUndo.length > 30) productUndo.shift();
  productRedo.length = 0;
}

function discardLastProductUndo(productId = "") {
  if (productUndoGroup) {
    if (!productId) return;
    productUndoGroup.entries = productUndoGroup.entries.filter((item) => item.id !== productId);
    return;
  }
  if (!productUndo.length) return;
  if (!productId || productUndo[productUndo.length - 1]?.id === productId) productUndo.pop();
}

async function applyProductHistory(entry, { select = true } = {}) {
  const saved = await api(`/api/products/${entry.id}`, {
    method: "PUT",
    body: JSON.stringify(entry.fields),
    quiet: true,
  });
  const index = products.findIndex((item) => item.id === entry.id);
  if (index >= 0) products[index] = saved;
  if (current?.id === entry.id) current = saved;
  if (select) {
    if (visibleProducts().some((item) => item.id === entry.id)) await selectProduct(entry.id, true, true);
    else {
      renderSheets();
      fillPreview();
    }
  }
  return saved;
}

async function undoProductChange() {
  const entry = productUndo.pop();
  if (!entry) {
    toast("되돌릴 수정이 없습니다.", true);
    return;
  }
  undoingProduct = true;
  try {
    if (entry.type === "group") {
      const nowEntries = [];
      for (const item of entry.entries) {
        const now = productSnapshot(findProductState(item.id));
        if (now) nowEntries.push(now);
        await applyProductHistory(item, { select: false });
      }
      productRedo.push({ type: "group", label: entry.label, entries: nowEntries });
      if (productRedo.length > 30) productRedo.shift();
      await loadProducts();
      toast(entry.label ? `${entry.label}을(를) 되돌렸습니다.` : "이전 작업 1개를 되돌렸습니다.");
      return;
    }
    const now = productSnapshot(findProductState(entry.id));
    await applyProductHistory(entry);
    if (now) {
      productRedo.push(now);
      if (productRedo.length > 30) productRedo.shift();
    }
    toast("이전 작업 1개를 되돌렸습니다.");
  } catch (error) {
    productUndo.push(entry);
    throw error;
  } finally {
    undoingProduct = false;
  }
}

async function redoProductChange() {
  const entry = productRedo.pop();
  if (!entry) {
    toast("다시 실행할 수정이 없습니다.", true);
    return;
  }
  redoingProduct = true;
  try {
    if (entry.type === "group") {
      const nowEntries = [];
      for (const item of entry.entries) {
        const now = productSnapshot(findProductState(item.id));
        if (now) nowEntries.push(now);
        await applyProductHistory(item, { select: false });
      }
      productUndo.push({ type: "group", label: entry.label, entries: nowEntries });
      if (productUndo.length > 30) productUndo.shift();
      await loadProducts();
      toast(entry.label ? `${entry.label}을(를) 다시 실행했습니다.` : "되돌린 작업 1개를 다시 실행했습니다.");
      return;
    }
    const now = productSnapshot(findProductState(entry.id));
    await applyProductHistory(entry);
    if (now) {
      productUndo.push(now);
      if (productUndo.length > 30) productUndo.shift();
    }
    toast("되돌린 작업 1개를 다시 실행했습니다.");
  } catch (error) {
    productRedo.push(entry);
    throw error;
  } finally {
    redoingProduct = false;
  }
}

async function saveProduct(product, patch, quiet = false) {
  if (isMasterProduct(product)) throw new Error(MASTER_LOCK_MESSAGE);
  rememberProductUndo(product);
  try {
    current = await api(`/api/products/${product.id}`, { method: "PUT", body: JSON.stringify(patch), quiet });
  } catch (error) {
    discardLastProductUndo(product.id);
    throw error;
  }
  const index = products.findIndex((item) => item.id === product.id);
  if (index >= 0) products[index] = current;
  fillPreview();
  refreshProductStatusUi();
  return current;
}

function applyEdition(edition, version) {
  const testEdition = edition === "test";
  document.body.classList.toggle("edition-test", testEdition);
  document.querySelectorAll(".collect-opts").forEach((node) => {
    node.hidden = testEdition;
  });
  const helpUrl = document.getElementById("helpUrlCollect");
  if (helpUrl) helpUrl.hidden = testEdition;
  syncCollectBarVisibility();
  const text = String(version || "").trim();
  const shown = text && text !== "0" ? text : "";
  const label = $("#appVersion");
  if (label && shown) {
    label.hidden = false;
    label.textContent = `v${shown}`;
    label.title = `버전 ${shown}`;
  }
  const editionLabel = $("#appEdition");
  if (editionLabel) editionLabel.textContent = testEdition ? "배포용" : "마스터";
  document.title = shown
    ? `모두모두AI ${testEdition ? "배포용" : "마스터"} v${shown}`
    : "모두모두AI";
}

async function loadEdition() {
  try {
    const data = await api("/api/edition");
    applyEdition(data.edition, data.version);
  } catch (error) {
    applyEdition("master", "");
  }
}

async function collectNow(urls) {
  if (document.body.classList.contains("edition-test")) {
    throw new Error("배포용에는 상품 URL 수집이 없습니다.");
  }
  if (!isMasterProductMenu()) {
    throw new Error("URL 상품수집은 왼쪽 마스터상품 메뉴에서만 할 수 있습니다.");
  }
  if (!urls.length) throw new Error("수집할 상품 URL을 위 입력칸에 넣어 주세요.");
  setBusy(true, "상품 정보를 가져오는 중입니다. Chrome이 뜨면 닫지 마세요. 로그인 화면이면 로그인한 뒤 기다려 주세요.");
  try {
    const picked = selectedProducts().find((item) => item.wholesale_id);
    const flags = {
      collect_images: $("#optImages")?.checked !== false,
      collect_options: $("#optOptions")?.checked !== false,
      collect_attributes: $("#optAttributes")?.checked !== false,
      wholesale_id: picked?.wholesale_id || (productFilter !== "all" && productFilter !== "url" ? productFilter : ""),
    };
    if (urls.length === 1) {
      current = await api("/api/products/collect", { method: "POST", body: JSON.stringify({ url: urls[0], ...flags }) });
    } else {
      const result = await api("/api/products/collect", { method: "POST", body: JSON.stringify({ urls, ...flags }) });
      current = result.last;
    }
    $("#collectUrl").value = "";
    showMasterProducts();
    await loadProducts();
    if (current) selectProduct(current.id);
    log("상품명, 가격, 카테고리, 속성, 태그, 옵션을 표에 넣었습니다. 칸을 눌러 수정하세요.", "ok");
  } catch (error) {
    if (isAbortError(error)) {
      log("작업을 중단했습니다.");
      toast("작업을 중단했습니다.");
      return;
    }
    log(error.message, "err");
  } finally {
    setBusy(false);
  }
}

function showSheet(name) {
  $("#sheetProducts").hidden = name !== "products";
  $("#sheetOptions").hidden = name !== "options";
  $("#tabProducts").classList.toggle("active", name === "products");
  $("#tabOptions").classList.toggle("active", name === "options");
}

let contextMenuOrder = null;

const CONTEXT_MENUS = {
  source: ["view-collected", "send-market", "refresh-original", "delete"],
};

const TOOLBAR_CONTEXT = [
  ["viewCollectedButton", "view-collected"],
  ["viewRegisteredButton", "view-registered"],
  ["saveButton", "save"],
  ["aiButton", "ai"],
  ["aiNameButton", "ai-name"],
  ["aiTagButton", "ai-tags"],
  ["aiAttrButton", "ai-attributes"],
  ["openOptionButton", "options"],
  ["changeNameButton", "change-name"],
  ["changeCategoryButton", "change-category"],
  ["changeAttributeButton", "change-attributes"],
  ["changeTagButton", "change-tags"],
  ["changeImageButton", "images"],
  ["changeDetailButton", "detail"],
  ["detailIntroButton", "detail-intro"],
  ["undoProductButton", "undo"],
  ["redoProductButton", "redo"],
  ["registerButton", "register"],
  ["stopJobButton", "stop-job"],
  ["refreshOriginalButton", "refresh-original"],
  ["refreshMarketButton", "refresh-market"],
  ["deleteButton", "delete"],
];

function toolbarContextRows() {
  return TOOLBAR_CONTEXT.flatMap(([id, action]) => {
    const button = document.getElementById(id);
    if (!button || button.hidden) return [];
    return [{ action, label: button.textContent.trim() }];
  });
}

function toolbarLabelMap() {
  const map = {};
  TOOLBAR_CONTEXT.forEach(([id, action]) => {
    const button = document.getElementById(id);
    const label = button?.textContent.trim();
    if (label) map[action] = label;
  });
  if (map["change-category"]) map.category = map["change-category"];
  if (map["change-attributes"]) map.attributes = map["change-attributes"];
  if (map["change-tags"]) map.tags = map["change-tags"];
  return map;
}

function applyContextMenu(menu) {
  if (!contextMenuOrder) contextMenuOrder = [...menu.children];
  [...menu.children].forEach((node) => {
    if (node.dataset.action && !node.dataset.defaultLabel) node.dataset.defaultLabel = node.textContent.trim();
  });
  const menuId = productMenuId();
  const toolbarRows = menuId === "smartstore" ? toolbarContextRows() : null;
  const preset = toolbarRows ? toolbarRows.map((row) => row.action) : CONTEXT_MENUS[menuId];
  const labels = toolbarLabelMap();
  menu.classList.toggle("context-menu-source", menuId === "source");
  if (preset) {
    preset.forEach((action) => {
      const node = [...menu.children].find((item) => item.dataset.action === action);
      if (node) menu.appendChild(node);
    });
  } else {
    contextMenuOrder.forEach((node) => menu.appendChild(node));
  }
  [...menu.children].forEach((node) => {
    const action = node.dataset.action || "";
    if (node.dataset.defaultLabel && !labels[action]) node.textContent = node.dataset.defaultLabel;
    if (labels[action] && node.childElementCount === 0) node.textContent = labels[action];
    if (!preset) {
      const sourceView = menuId === "source" || menuId === "master";
      node.hidden = node.dataset.smartstoreOnly === "1" || (node.dataset.sourceOnly === "1" && !sourceView) || (node.dataset.marketOnly === "1" && sourceView);
      return;
    }
    node.hidden = !preset.includes(action);
  });
  const del = menu.querySelector("[data-action='delete']");
  if (del && !labels.delete) del.textContent = "선택삭제";
  if (!preset) {
    const locked = isMasterProduct(current);
    menu.querySelectorAll("[data-master-edit]").forEach((node) => {
      node.hidden = locked;
    });
  }
  stripeContextMenu(menu);
}

function stripeContextMenu(menu) {
  let index = 0;
  [...menu.children].forEach((node) => {
    node.classList.remove("context-menu-alt");
    if (node.hidden || node.tagName === "HR") return;
    if (index % 2 === 1) node.classList.add("context-menu-alt");
    index += 1;
  });
}

function hideContextMenu() {
  $("#contextMenu").hidden = true;
}

function showContextMenu(x, y) {
  const menu = $("#contextMenu");
  menu.hidden = false;
  applyContextMenu(menu);
  const width = menu.offsetWidth;
  const height = menu.offsetHeight;
  const left = Math.min(x, window.innerWidth - width - 8);
  const top = Math.min(y, window.innerHeight - height - 8);
  menu.style.left = `${Math.max(8, left)}px`;
  menu.style.top = `${Math.max(8, top)}px`;
  const panel = menu.querySelector(".context-submenu-panel");
  if (panel) panel.classList.toggle("flip-left", left + width + 180 > window.innerWidth);
}

function shuffleArray(items) {
  const next = [...items];
  for (let index = next.length - 1; index > 0; index -= 1) {
    const swap = Math.floor(Math.random() * (index + 1));
    [next[index], next[swap]] = [next[swap], next[index]];
  }
  return next;
}

function shuffleNameKeywords(name, keepCount) {
  const tokens = String(name || "").trim().split(/\s+/).filter(Boolean);
  const keep = Math.max(0, Math.min(Number(keepCount) || 0, tokens.length));
  const head = tokens.slice(0, keep);
  const tail = tokens.slice(keep);
  if (tail.length <= 1) return tokens.join(" ");
  let shuffled = shuffleArray(tail);
  for (let attempt = 0; attempt < 8 && shuffled.join(" ") === tail.join(" "); attempt += 1) {
    shuffled = shuffleArray(tail);
  }
  return [...head, ...shuffled].join(" ");
}

async function aiRewriteSelected(kind) {
  const jobs = {
    name: { label: "상품명", path: "name/ai" },
    tags: { label: "태그", path: "tags/ai" },
    attributes: { label: "속성", path: "attributes/ai" },
    "detail-intro": { label: "상세페이지추가글", path: "detail-intro/ai" },
  };
  const job = jobs[kind];
  if (!job) return;
  const items = requireSelected();
  if (!items.length) return;
  if (items.every(isMasterProduct)) return masterEditBlocked(items[0]);
  const editable = items.filter((item) => !isMasterProduct(item));
  if (kind === "attributes" && guideCategoryBeforeAi(editable)) return;
  const instruction = $("#fieldInstruction")?.value || "";
  const body = { instruction };
  if (kind === "name") {
    body.mode = await askNameMode();
    if (!body.mode) return;
  }
  setBusy(true, `${job.label} AI 가공 중 (0/${items.length})`);
  let count = 0;
  const errors = [];
  beginProductUndoGroup(`${job.label} AI`);
  try {
    for (let index = 0; index < items.length; index += 1) {
      throwIfCancelled();
      const item = items[index];
      if (isMasterProduct(item)) continue;
      setBusy(true, `${job.label} AI 가공 중 (${index + 1}/${items.length})`);
      try {
        rememberProductUndo(findProductState(item.id) || item);
        await saveCurrentRow(item.id);
        current = await api(`/api/products/${item.id}/${job.path}`, {
          method: "POST",
          body: JSON.stringify(body),
        });
        if (kind === "attributes" && !(current.naver_attributes || []).length && !(current.attributes || []).length) {
          errors.push(`${item.name || "상품"}: 속성값이 비어 있습니다.`);
        } else {
          count += 1;
        }
      } catch (error) {
        if (isAbortError(error)) throw error;
        errors.push(`${item.name || "상품"}: ${error.message}`);
      }
      if (index < items.length - 1) await wait(900);
    }
    await loadProducts();
    if (current) await selectProduct(current.id, true, true);
    if (count) {
      log(`${count}개 ${job.label} AI 가공을 마쳤습니다.`, "ok");
      const done = kind === "attributes"
        ? (items.length === 1 ? "상품 상세페이지를 읽고 속성을 넣었습니다." : `${count}개 상품의 상세페이지를 읽고 속성을 넣었습니다.`)
        : kind === "detail-intro"
          ? (items.length === 1 ? "상세페이지 위에 추가글을 넣었습니다." : `${count}개 상품 상세페이지 위에 추가글을 넣었습니다.`)
          : (items.length === 1 ? `${job.label} AI 가공을 마쳤습니다.` : `${count}개 ${job.label} AI 가공을 마쳤습니다.`);
      toast(done);
    }
    errors.forEach((text) => log(text, "err"));
  } catch (error) {
    if (isAbortError(error)) {
      if (count) log(`${count}개까지 처리한 뒤 작업을 중단했습니다.`);
      toast("작업을 중단했습니다.");
    } else {
      throw error;
    }
  } finally {
    if (count) endProductUndoGroup();
    else cancelProductUndoGroup();
    setBusy(false);
  }
}

function askNameMode() {
  return new Promise((resolve) => {
    const dialog = $("#nameModeDialog");
    const finish = (mode) => {
      dialog.close();
      resolve(mode);
    };
    dialog.querySelectorAll("[data-name-ai-mode]").forEach((button) => {
      button.onclick = () => finish(button.dataset.nameAiMode);
    });
    $("#nameModeCancel").onclick = () => finish("");
    dialog.oncancel = (event) => {
      event.preventDefault();
      finish("");
    };
    dialog.showModal();
  });
}

function aiRewriteSelectedNames() {
  return aiRewriteSelected("name");
}

async function shuffleSelectedNames(keepCount) {
  const items = requireSelected().filter((item) => !isMasterProduct(item));
  if (!items.length) return masterEditBlocked();
  setBusy(true, "선택한 상품명 키워드를 섞는 중입니다.");
  beginProductUndoGroup("상품명 키워드 섞기");
  let count = 0;
  try {
    for (const item of items) {
      const row = document.querySelector(`#productTable tr[data-id="${item.id}"]`);
      const currentName = row?.querySelector('[data-field="name"]')?.value ?? item.name ?? "";
      const next = shuffleNameKeywords(currentName, keepCount);
      if (!next || next === currentName) continue;
      await saveProduct(item, { name: next });
      count += 1;
    }
    await loadProducts();
    if (current) await selectProduct(current.id, true, true);
    toast(count ? `상품명 키워드를 ${count}개 섞었습니다.` : "섞을 키워드가 부족합니다.");
  } catch (error) {
    if (isAbortError(error)) toast("작업을 중단했습니다.");
    else toast(error.message, true);
  } finally {
    if (count) endProductUndoGroup();
    else cancelProductUndoGroup();
    setBusy(false);
  }
}

function focusProductField(field) {
  if (!current || masterEditBlocked()) return;
  showSheet("products");
  const input = document.querySelector(`#productTable tr[data-id="${current.id}"] [data-field="${field}"]`);
  if (input) beginCellEdit(input);
}

function storeSlug(url) {
  const match = String(url || "").match(/smartstore\.naver\.com\/([^/?#]+)\/products/i);
  if (match && !["main", "i", "v1", "v2"].includes(match[1].toLowerCase())) return match[1];
  return "";
}

function openUrl(url, emptyMessage) {
  if (looksLikeUrl(url)) {
    window.open(url, "_blank", "noopener");
    return true;
  }
  toast(emptyMessage, true);
  return false;
}

async function openSupplierProductUrl(url, wholesalerId, emptyMessage) {
  const target = String(url || "").trim();
  if (!looksLikeUrl(target)) {
    toast(emptyMessage || "열 상품 주소가 없습니다.", true);
    return false;
  }
  const id = String(wholesalerId || "").trim();
  if (!id) {
    return openUrl(target, emptyMessage);
  }
  try {
    const result = await api(`/api/wholesalers/${encodeURIComponent(id)}/open-product`, {
      method: "POST",
      body: JSON.stringify({ url: target }),
      signal: AbortSignal.timeout(12000),
    });
    toast(result?.message || "로그인 Chrome에서 공급사 상품을 열었습니다.");
    return true;
  } catch (error) {
    if (openUrl(target, emptyMessage)) {
      toast("프로그램 Chrome이 늦어 브라우저에서 상품을 열었습니다.");
      return true;
    }
    toast(error.message || "공급사 상품을 열지 못했습니다.", true);
    return false;
  }
}

async function openCollectedProduct() {
  const item = current || selectedProducts()[0];
  if (!item) return toast("먼저 상품을 선택해 주세요.", true);
  await openSupplierProductUrl(
    item.source_url,
    productWholesalerId(item),
    "수집한 상품 URL이 없습니다. 먼저 상품수집을 해 주세요."
  );
}

function openRegisteredProduct() {
  const item = current || selectedProducts()[0];
  if (!item) return toast("먼저 상품을 선택해 주세요.", true);
  const channelNo = item.channel_product_no;
  const originNo = item.origin_product_no;
  if (channelNo) {
    const slug = storeSlug(item.source_url);
    const url = slug
      ? `https://smartstore.naver.com/${slug}/products/${channelNo}`
      : `https://smartstore.naver.com/main/products/${channelNo}`;
    window.open(url, "_blank", "noopener");
    return;
  }
  if (originNo) {
    window.open(`https://sell.smartstore.naver.com/#/products/origin-product/${originNo}`, "_blank", "noopener");
    return;
  }
  toast("아직 스마트스토어에 등록되지 않은 상품입니다. 먼저 상품등록을 해 주세요.", true);
}

function optionEnabled() {
  return $("#optionOn").classList.contains("active");
}

function setOptionEnabled(enabled) {
  $("#optionOn").classList.toggle("active", enabled);
  $("#optionOff").classList.toggle("active", !enabled);
  $("#optionSettings").hidden = !enabled;
}

function optionTypeValue() {
  return document.querySelector('input[name="optionType"]:checked')?.value || "COMBINATION";
}

function openOptionEditor() {
  if (!current) return toast("먼저 상품을 선택해 주세요.", true);
  if (masterEditBlocked()) return;
  const groups = [...(current.options || [])];
  const enabled = groups.some((group) => group.name && (group.values || []).length);
  setOptionEnabled(enabled || !groups.length);
  document.querySelector(`input[name="optionType"][value="${current.option_type === "SIMPLE" ? "SIMPLE" : "COMBINATION"}"]`).checked = true;
  $("#optionGroupCount").value = String(Math.max(1, Math.min(3, groups.length || 1)));
  renderOptionNameRows(groups.length ? groups : [{ name: "", values: [""] }]);
  renderOptionCombos(current.option_combinations?.length ? current.option_combinations : buildOptionCombos(groups, current.stock));
  $("#optionDialog").showModal();
}

function renderOptionNameRows(groups) {
  const box = $("#optionEditor");
  const count = Number($("#optionGroupCount").value || 1);
  const rows = groups.slice(0, count);
  while (rows.length < count) rows.push({ name: "", values: [""] });
  box.innerHTML = "";
  rows.forEach((group) => box.appendChild(optionEditorRow(group)));
}

function optionEditorRow(group) {
  const wrap = document.createElement("div");
  wrap.className = "option-edit-row";
  const values = group.values?.length ? group.values : [""];
  wrap.innerHTML = `
    <label>옵션명<input data-opt-name value="${escapeAttr(group.name || "")}" /></label>
    <div>
      <span>옵션값</span>
      <div class="option-value-list"></div>
    </div>
    <button type="button" class="add-option-value">+</button>
  `;
  const list = wrap.querySelector(".option-value-list");
  values.forEach((value) => list.appendChild(optionValueRow(value)));
  wrap.querySelector(".add-option-value").addEventListener("click", () => list.appendChild(optionValueRow("")));
  return wrap;
}

function optionValueRow(value) {
  const row = document.createElement("div");
  row.className = "option-value-row";
  row.innerHTML = `
    <input data-opt-value placeholder="옵션값" value="${escapeAttr(value)}" />
    <button type="button" class="remove-option-value">삭제</button>
  `;
  row.querySelector(".remove-option-value").addEventListener("click", () => {
    if (row.parentElement.querySelectorAll(".option-value-row").length < 2) {
      row.querySelector("[data-opt-value]").value = "";
      return;
    }
    row.remove();
  });
  return row;
}

function escapeAttr(value) {
  return String(value || "").replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
}

function readOptionGroups() {
  return [...$("#optionEditor").querySelectorAll(".option-edit-row")].map((row) => {
    const values = [...row.querySelectorAll("[data-opt-value]")].map((input) => input.value.trim()).filter(Boolean);
    return { name: row.querySelector("[data-opt-name]").value.trim(), values, extras: values.map(() => 0) };
  }).filter((item) => item.name && item.values.length).slice(0, 3);
}

function buildOptionCombos(groups, stock) {
  const qty = Number(stock || current?.stock || 9999);
  if (!groups.length) return [];
  if (optionTypeValue() === "SIMPLE") {
    return groups.flatMap((group) => group.values.map((value) => ({
      group: group.name,
      values: [value],
      price: 0,
      stock: qty,
      status: "SALE",
      code: "",
      usable: true,
    })));
  }
  let rows = [{ values: [], price: 0 }];
  groups.forEach((group) => {
    const next = [];
    group.values.forEach((value, index) => {
      const extra = Number((group.extras || [])[index] || 0);
      rows.forEach((row) => next.push({
        values: [...row.values, value],
        price: row.price + extra,
        stock: qty,
        status: "SALE",
        code: "",
        usable: true,
      }));
    });
    rows = next;
  });
  return rows.slice(0, 200);
}

function renderOptionCombos(rows) {
  const body = $("#optionComboTable");
  body.innerHTML = "";
  rows.forEach((row) => body.appendChild(optionComboRow(row)));
}

function optionComboRow(row) {
  const tr = document.createElement("tr");
  const price = Number(row.price || 0);
  const sign = price < 0 ? "-" : "+";
  tr.innerHTML = `
    <td><input type="checkbox" data-combo-check /></td>
    <td>${escapeAttr((row.values || []).join(" / "))}</td>
    <td>
      <span class="option-price-cell">
        <select data-combo-sign><option value="+">+</option><option value="-">-</option></select>
        <input data-combo-price type="number" step="10" value="${Math.abs(price)}" />
      </span>
    </td>
    <td><input data-combo-stock type="number" value="${Number(row.stock || 9999)}" /></td>
    <td>
      <select data-combo-status>
        <option value="SALE">판매중</option>
        <option value="SUSPENSION">판매중지</option>
      </select>
    </td>
    <td><input data-combo-code value="${escapeAttr(row.code || "")}" /></td>
    <td>
      <select data-combo-usable>
        <option value="true">Y</option>
        <option value="false">N</option>
      </select>
    </td>
    <td><button type="button" class="remove-combo">삭제</button></td>
  `;
  tr.dataset.values = JSON.stringify(row.values || []);
  tr.dataset.group = row.group || "";
  tr.querySelector("[data-combo-sign]").value = sign;
  tr.querySelector("[data-combo-status]").value = row.status === "SUSPENSION" ? "SUSPENSION" : "SALE";
  tr.querySelector("[data-combo-usable]").value = row.usable === false ? "false" : "true";
  tr.querySelector(".remove-combo").addEventListener("click", () => tr.remove());
  return tr;
}

function readOptionCombos() {
  return [...$("#optionComboTable tr")].map((row) => {
    const sign = row.querySelector("[data-combo-sign]").value;
    const amount = Math.abs(Number(row.querySelector("[data-combo-price]").value || 0));
    return {
      group: row.dataset.group || "",
      values: JSON.parse(row.dataset.values || "[]"),
      price: sign === "-" ? -amount : amount,
      stock: Number(row.querySelector("[data-combo-stock]").value || 0),
      status: row.querySelector("[data-combo-status]").value,
      code: row.querySelector("[data-combo-code]").value.trim(),
      usable: row.querySelector("[data-combo-usable]").value !== "false",
    };
  }).filter((item) => item.values.length);
}

function syncExtrasFromCombos(groups, combos) {
  if (groups.length === 1) {
    groups[0].extras = groups[0].values.map((value) => {
      const row = combos.find((item) => item.values[0] === value);
      return Number(row?.price || 0);
    });
  }
  return groups;
}

function selectedComboRows() {
  return [...$("#optionComboTable tr")].filter((row) => row.querySelector("[data-combo-check]")?.checked);
}

function checkSelectedRows() {
  if (!current) return toast("먼저 상품을 선택해 주세요.", true);
  selectedIds.add(current.id);
  toggleProduct(current.id, true, true);
}

function uncheckSelectedRows() {
  const items = selectedProducts();
  if (!items.length) return toast("해제할 상품이 없습니다.", true);
  items.forEach((item) => selectedIds.delete(item.id));
  current = null;
  renderSheets();
  fillPreview();
  updateSelectionText();
}

async function saveSelected() {
  const items = requireSelected();
  if (!items.length) return;
  for (const item of items) await saveCurrentRow(item.id);
  toast(items.length > 1 ? `${items.length}개 상품을 수정 저장했습니다.` : "수정한 값을 저장했습니다.");
}

async function collectSelectedItems() {
  const items = requireSelected();
  if (!items.length) return;
  const urls = items.map((item) => item.source_url).filter((url) => looksLikeUrl(url));
  await collectNow(urls.length ? urls : collectUrls().slice(0, 1));
}

async function registerSelected() {
  const items = requireSelected();
  if (!items.length) return;
  if (items.some((item) => isMasterProduct(item) || !item.market_id)) {
    toast("마스터상품은 등록할 수 없습니다. 먼저 마켓으로 보낸 뒤 그 마켓에서 등록하세요.", true);
    return;
  }
  const marketIds = [...new Set(items.map((item) => item.market_id).filter(Boolean))];
  if (marketIds.length > 1) {
    toast("선택한 상품의 마켓이 서로 다릅니다. 같은 마켓 상품만 등록하세요.", true);
    return;
  }
  const marketId = marketIds[0];
  if (markets.some((item) => item.id === marketFilter) && marketFilter !== marketId) {
    toast("왼쪽에서 고른 마켓과 상품 마켓이 다릅니다. 등록할 마켓을 다시 고르세요.", true);
    return;
  }
  currentMarketId = marketId;
  const template = await currentDeliveryTemplate();
  const addressError = deliveryAddressError(template);
  if (addressError) {
    toast(addressError, true);
    await openDeliveryEditor();
    return;
  }
  const count = items.length;
  const summary = deliverySummary(template);
  const ask = count > 1
    ? `지금 배송/가격 설정(${summary})으로 선택한 ${count}개 상품을 등록할까요?`
    : `지금 배송/가격 설정(${summary})으로 상품등록할까요?`;
  if (!confirm(ask)) return;
  await proceedRegisterSelected({ skipConfirm: true });
}

async function proceedRegisterSelected(options = {}) {
  const items = requireSelected();
  if (!items.length) return;
  if (!options.skipConfirm) {
    const template = await currentDeliveryTemplate();
    const summary = deliverySummary(template);
    if (!confirm(items.length > 1
      ? `지금 배송/가격 설정(${summary})으로 선택한 ${items.length}개 상품을 등록할까요?`
      : `지금 배송/가격 설정(${summary})으로 상품등록할까요?`)) return;
  }
  setBusy(true, `상품 등록 중 (0/${items.length})`);
  let ok = 0;
  let fail = 0;
  try {
    for (let index = 0; index < items.length; index += 1) {
      throwIfCancelled();
      const item = items[index];
      setBusy(true, `상품 등록 중 (${index + 1}/${items.length})`);
      try {
        await saveCurrentRow(item.id);
        current = await api(`/api/products/${item.id}/register`, { method: "POST", body: "{}", quiet: true });
        patchLocalProduct(item.id, {
          ...current,
          status: current.status || "registered",
          origin_product_no: current.origin_product_no,
          channel_product_no: current.channel_product_no,
          last_error: "",
        });
        updateFilterCount();
        renderProductSheet();
        const where = current.store_product_url || current.store_name || current.channel_product_no || "";
        log(`${current.name || item.name || "상품"} 등록을 완료했습니다.${where ? ` ${where}` : ""}`, "ok");
        ok += 1;
      } catch (error) {
        if (isAbortError(error)) throw error;
        fail += 1;
        patchLocalProduct(item.id, { status: "error", last_error: error.message });
        updateFilterCount();
        renderProductSheet();
        log(`${item.name || "상품"} 등록 실패: ${error.message}`, "err");
      }
      if (index < items.length - 1) await wait(2000);
    }
    await loadProducts();
    updateFilterCount();
    if (current) await selectProduct(current.id, true, true);
    updateFilterCount();
    if (fail) toast(`${ok}개 등록, ${fail}개 실패`, true);
    else if (ok) toast(`${ok}개 등록을 마쳤습니다.`);
  } catch (error) {
    if (isAbortError(error)) {
      if (ok || fail) log(`등록 ${ok}개 성공, ${fail}개 실패 뒤 작업을 중단했습니다.`);
      toast("작업을 중단했습니다.");
    } else {
      log(error.message, "err");
    }
  } finally {
    setBusy(false);
  }
}

async function deleteSelected() {
  const items = requireSelected();
  if (!items.length) return;
  if (!confirm(items.length > 1 ? `선택한 ${items.length}개 상품을 삭제할까요?` : "선택한 수집 상품을 삭제할까요?")) return;
  for (const item of items) {
    await api(`/api/products/${item.id}`, { method: "DELETE" });
    selectedIds.delete(item.id);
  }
  current = null;
  await loadProducts();
}

let draftTags = [];

function tagBlockTerms() {
  const terms = [];
  const add = (text, reason) => {
    const token = cleanTag(text);
    if (token.length >= 2 && !terms.some((item) => item.token === token)) {
      terms.push({ token, reason });
    }
  };
  String(current?.category_name || current?.source_category || "").split(/[\s>/]+/).forEach((part) => add(part, "카테고리명"));
  add(current?.brand, "브랜드명");
  add(current?.manufacturer, "판매자명");
  return terms;
}

function classifyDraftTags() {
  const terms = tagBlockTerms();
  const applied = [];
  const excluded = [];
  draftTags.forEach((tag) => {
    const hit = terms.find((item) => item.token === tag || tag.includes(item.token));
    if (hit) excluded.push({ tag, reason: hit.reason });
    else applied.push(tag);
  });
  return { applied, excluded };
}

function showSearchTagCheck() {
  addDraftTag($("#tagInput").value);
  const { applied, excluded } = classifyDraftTags();
  const box = $("#tagSearchResult");
  box.hidden = false;
  const appliedHtml = applied.length
    ? applied.map((tag) => `<button type="button" class="tag-chip tag-chip-on" data-search-tag="${escapeAttr(tag)}">#${tag}</button>`).join("")
    : "<span class='hint'>검색에 적용되는 태그가 없습니다.</span>";
  const excludedHtml = excluded.length
    ? `<p class="hint">제외된 태그</p><div class="tag-search-list">${excluded.map((item) => `<span class="tag-chip tag-chip-off">#${item.tag} (${item.reason})</span>`).join("")}</div>`
    : "";
  box.innerHTML = `<strong>검색에 적용되는 태그</strong><div class="tag-search-list">${appliedHtml}</div>${excludedHtml}<p class="hint">카테고리, 브랜드, 판매자명이 포함된 태그는 검색에 적용되지 않습니다. 적용 태그를 누르면 네이버쇼핑에서 확인할 수 있습니다.</p>`;
}

function openNameEditor() {
  const item = current || selectedProducts()[0];
  if (!item) return toast("먼저 상품을 선택해 주세요.", true);
  if (masterEditBlocked(item)) return;
  current = item;
  $("#nameInput").value = item.name || "";
  $("#nameSuggestKeywords").hidden = true;
  $("#nameDialog").showModal();
  $("#nameInput").focus();
  $("#nameInput").select();
}

function openTagEditor() {
  if (!current) return toast("먼저 상품을 선택해 주세요.", true);
  if (masterEditBlocked()) return;
  draftTags = uniqueTags(current.tags || []);
  $("#tagDirect").checked = true;
  $("#tagInput").value = "";
  $("#tagSearchResult").hidden = true;
  $("#tagSearchResult").innerHTML = "";
  renderTagChips();
  syncTagEditor();
  $("#tagDialog").showModal();
  $("#tagInput").focus();
}

function syncTagEditor() {
  const on = $("#tagDirect").checked;
  $("#tagEditor").hidden = !on;
}

function renderTagChips() {
  const box = $("#tagChips");
  box.innerHTML = "";
  draftTags.forEach((tag, index) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "tag-chip";
    chip.textContent = `#${tag}`;
    const close = document.createElement("span");
    close.textContent = "×";
    chip.append(" ", close);
    chip.addEventListener("click", () => {
      draftTags.splice(index, 1);
      renderTagChips();
    });
    box.appendChild(chip);
  });
  $("#tagCount").textContent = `${draftTags.length}/10`;
}

function addDraftTag(raw) {
  const added = uniqueTags(String(raw || "").split(/[,#\s]+/), 10);
  if (!added.length) return;
  for (const tag of added) {
    if (draftTags.includes(tag)) continue;
    if (draftTags.length >= 10) {
      toast("태그는 최대 10개입니다.", true);
      break;
    }
    draftTags.push(tag);
  }
  $("#tagInput").value = "";
  renderTagChips();
}

let draftImages = [];
let imageDragIndex = -1;
let imageDragMoved = false;

async function ensureGalleryFit(product) {
  if (!product?.id || refitDone.has(product.id)) return product;
  refitDone.add(product.id);
  try {
    const saved = await api(`/api/products/${product.id}/images/refit`, { method: "POST", body: "{}" });
    const index = products.findIndex((item) => item.id === saved.id);
    if (index >= 0) products[index] = saved;
    if (current?.id === saved.id) {
      current = saved;
      fillPreview();
    }
    return saved;
  } catch (error) {
    return product;
  }
}

function galleryImages(product) {
  return [...(product?.images || [])].filter((image) => image.kind === "gallery");
}

function imageSrc(image) {
  if (image.preview) return image.preview;
  if (!current || !image.file) return "";
  const stamp = `${current.updated_at || ""}-${image.width || 0}x${image.height || 0}-${image.text_removed ? 1 : 0}`;
  return `/media/${current.id}/${image.file}?v=${encodeURIComponent(stamp)}`;
}

async function openImageEditor() {
  if (!current) return toast("먼저 상품을 선택해 주세요.", true);
  if (masterEditBlocked()) return;
  try {
    current = await api(`/api/products/${current.id}/images/refit`, { method: "POST", body: "{}" });
    const index = products.findIndex((item) => item.id === current.id);
    if (index >= 0) products[index] = current;
  } catch (error) {
    toast(error.message, true);
  }
  draftImages = galleryImages(current).map((image) => ({ ...image }));
  $("#imageUrl").value = "";
  renderImageEditor();
  fillPreview();
  $("#imageDialog").showModal();
}

function moveDraftImage(from, to) {
  if (from < 0 || from >= draftImages.length || to < 0 || from === to) return;
  const [item] = draftImages.splice(from, 1);
  draftImages.splice(Math.min(to, draftImages.length), 0, item);
  renderImageEditor();
}

function imageSlotAt(x, y) {
  return [...$("#imageThumbs").querySelectorAll(".image-slot")].findIndex((slot) => {
    const box = slot.getBoundingClientRect();
    return x >= box.left && x <= box.right && y >= box.top && y <= box.bottom;
  });
}

function imageRowAt(x, y) {
  return [...$("#imageUrlTable tr")].findIndex((row) => {
    const box = row.getBoundingClientRect();
    return x >= box.left && x <= box.right && y >= box.top && y <= box.bottom;
  });
}

function startImageReorder(event, index, kind) {
  if (event.button !== 0 || event.target.closest("button")) return;
  imageDragMoved = false;
  imageDragIndex = index;
  const startX = event.clientX;
  const startY = event.clientY;
  const onMove = (move) => {
    if (imageDragIndex < 0) return;
    if (!imageDragMoved && Math.hypot(move.clientX - startX, move.clientY - startY) < 5) return;
    if (!imageDragMoved) {
      imageDragMoved = true;
      move.preventDefault();
      document.body.classList.add("image-reordering");
      const ghost = document.createElement("div");
      ghost.id = "imageDragGhost";
      ghost.className = "image-drag-ghost";
      ghost.innerHTML = `<img src="${imageSrc(draftImages[index])}" alt="">`;
      document.body.appendChild(ghost);
    }
    const ghost = $("#imageDragGhost");
    if (ghost) {
      ghost.style.left = `${move.clientX + 10}px`;
      ghost.style.top = `${move.clientY + 10}px`;
    }
    const over = kind === "row" ? imageRowAt(move.clientX, move.clientY) : imageSlotAt(move.clientX, move.clientY);
    const items = kind === "row" ? $("#imageUrlTable").querySelectorAll("tr") : $("#imageThumbs").querySelectorAll(".image-slot");
    items.forEach((item, offset) => {
      item.classList.toggle("drop-target", offset === over);
      item.classList.toggle("dragging", offset === index);
    });
  };
  const onUp = (up) => {
    document.removeEventListener("pointermove", onMove);
    document.removeEventListener("pointerup", onUp);
    document.removeEventListener("pointercancel", onUp);
    $("#imageDragGhost")?.remove();
    document.body.classList.remove("image-reordering");
    const from = imageDragIndex;
    const to = kind === "row" ? imageRowAt(up.clientX, up.clientY) : imageSlotAt(up.clientX, up.clientY);
    imageDragIndex = -1;
    $("#imageThumbs").querySelectorAll(".image-slot").forEach((item) => item.classList.remove("drop-target", "dragging"));
    $("#imageUrlTable").querySelectorAll("tr").forEach((item) => item.classList.remove("drop-target", "dragging"));
    if (imageDragMoved && to >= 0) moveDraftImage(from, to);
  };
  document.addEventListener("pointermove", onMove);
  document.addEventListener("pointerup", onUp);
  document.addEventListener("pointercancel", onUp);
}

function renderImageEditor() {
  const thumbs = $("#imageThumbs");
  thumbs.innerHTML = "";
  const total = Math.max(draftImages.length, 1);
  for (let index = 0; index < total; index += 1) {
    const slot = document.createElement("div");
    slot.className = "image-slot";
    const image = draftImages[index];
    if (image) {
      const img = document.createElement("img");
      img.alt = `이미지 ${index + 1}`;
      img.src = imageSrc(image);
      img.draggable = false;
      if (image.representative) slot.classList.add("representative");
      slot.appendChild(img);
      slot.addEventListener("pointerdown", (event) => startImageReorder(event, index, "slot"));
      slot.addEventListener("click", () => {
        if (imageDragMoved) return;
        draftImages.forEach((item) => { item.representative = false; });
        image.representative = true;
        renderImageEditor();
      });
    }
    thumbs.appendChild(slot);
  }
  const body = $("#imageUrlTable");
  body.innerHTML = "";
  draftImages.forEach((image, index) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${index + 1}</td>
      <td>${escapeAttr(image.source_url || image.file || "")}</td>
      <td><button type="button" class="remove-image">삭제</button></td>
    `;
    row.addEventListener("pointerdown", (event) => startImageReorder(event, index, "row"));
    row.querySelector(".remove-image").addEventListener("click", (event) => {
      event.stopPropagation();
      draftImages.splice(index, 1);
      if (draftImages.length && !draftImages.some((item) => item.representative)) draftImages[0].representative = true;
      renderImageEditor();
    });
    body.appendChild(row);
  });
}

const GALLERY_LIMIT = 10;

function isImageFile(file) {
  return Boolean(file) && (String(file.type || "").startsWith("image/") || /\.(jpe?g|png|webp|gif|bmp|jfif)$/i.test(file.name || ""));
}

async function saveDraftImages() {
  if (!current) return;
  const detail = (current.images || []).filter((image) => image.kind !== "gallery");
  const images = [...draftImages.map((image) => ({ ...image, kind: "gallery", included: true })), ...detail];
  current = await saveProduct(current, { images });
  const index = products.findIndex((item) => item.id === current.id);
  if (index >= 0) products[index] = current;
  draftImages = galleryImages(current).map((image) => ({ ...image }));
}

async function uploadProductImages(files, url) {
  if (!current) return toast("먼저 상품을 선택해 주세요.", true);
  await saveDraftImages();
  const remain = GALLERY_LIMIT - draftImages.length;
  if (remain <= 0) return toast(`이미지는 최대 ${GALLERY_LIMIT}장까지 넣을 수 있습니다.`, true);
  const picked = [...(files || [])].filter(isImageFile).slice(0, remain);
  const urls = String(url || "").split(/[\s,]+/).map((item) => item.trim()).filter(Boolean).slice(0, remain - picked.length);
  if (!picked.length && !urls.length) return toast("이미지 파일이나 URL을 넣어 주세요.", true);
  const form = new FormData();
  picked.forEach((file) => form.append("files", file, file.name || "image.jpg"));
  urls.forEach((item) => form.append("url", item));
  const before = draftImages.length;
  const response = await fetch(`/api/products/${current.id}/images`, { method: "POST", body: form });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "이미지를 추가하지 못했습니다.");
  current = data;
  const index = products.findIndex((item) => item.id === current.id);
  if (index >= 0) products[index] = current;
  draftImages = galleryImages(current).map((image) => ({ ...image }));
  renderImageEditor();
  fillPreview();
  return Math.max(0, draftImages.length - before);
}

function bindImageDrop(el) {
  el.addEventListener("dragover", (event) => {
    if (imageDragIndex >= 0) return;
    if (![...event.dataTransfer.types].includes("Files")) return;
    event.preventDefault();
    el.classList.add("dragover");
  });
  el.addEventListener("dragleave", () => el.classList.remove("dragover"));
  el.addEventListener("drop", async (event) => {
    if (imageDragIndex >= 0) return;
    el.classList.remove("dragover");
    const files = [...(event.dataTransfer?.files || [])].filter(isImageFile);
    if (!files.length) return;
    event.preventDefault();
    if (!current) return toast("먼저 상품을 선택해 주세요.", true);
    try {
      if (!$("#imageDialog").open) await openImageEditor();
      const added = await uploadProductImages(files, "");
      toast(added > 1 ? `${added}장 이미지를 추가했습니다.` : "이미지를 추가했습니다.");
    } catch (error) {
      toast(error.message, true);
    }
  });
}

let detailMode = "editor";

function htmlToText(html) {
  const box = document.createElement("div");
  box.innerHTML = html || "";
  return (box.innerText || box.textContent || "").replace(/\u00a0/g, " ");
}

function textToHtml(text) {
  return String(text || "")
    .split(/\n{2,}/)
    .map((part) => `<p>${part.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/\n/g, "<br>")}</p>`)
    .join("");
}

function isPlaceholderSrc(src) {
  const value = String(src || "").trim();
  if (!value || value === "#" || value === "about:blank") return true;
  if (value.startsWith("data:image") && value.length < 500) return true;
  return /spacer|blank|pixel|placeholder|transparent|1x1/i.test(value);
}

function lazyImageSrc(img) {
  const candidates = [
    img.getAttribute("data-src"),
    img.getAttribute("data-lazy-src"),
    img.getAttribute("data-original"),
    img.getAttribute("data-url"),
    img.getAttribute("data-lazy"),
    img.getAttribute("src"),
  ];
  for (const item of candidates) {
    if (!item || isPlaceholderSrc(item)) continue;
    return item.startsWith("//") ? `https:${item}` : item;
  }
  return "";
}

function prepareDetailHtml(html) {
  const box = document.createElement("div");
  box.innerHTML = html || "";
  box.querySelectorAll("img").forEach((img) => {
    const url = lazyImageSrc(img);
    if (!url) return;
    img.setAttribute("data-origin-src", url);
    img.setAttribute("src", url);
    img.removeAttribute("loading");
    img.removeAttribute("srcset");
  });
  return box.innerHTML;
}

function bindDetailImages(root) {
  if (!root) return;
  root.querySelectorAll("img").forEach((img) => {
    const real = img.getAttribute("data-origin-src") || lazyImageSrc(img);
    if (!real) return;
    img.addEventListener("error", () => {
      // 로컬 /media 파일이 없으면 프록시해도 엑박이므로 빼고, 외부 URL만 프록시한다.
      if (real.startsWith("/media/") || real.startsWith("blob:")) {
        img.remove();
        return;
      }
      if (img.dataset.proxied === "1") {
        img.remove();
        return;
      }
      img.dataset.proxied = "1";
      img.src = `/api/image-proxy?url=${encodeURIComponent(real)}`;
    }, { once: true });
  });
}

function readDetailHtml() {
  if (detailMode === "html") return prepareDetailHtml($("#detailHtml").value);
  if (detailMode === "text") return textToHtml($("#detailText").value);
  const box = document.createElement("div");
  box.innerHTML = $("#detailVisual").innerHTML;
  box.querySelectorAll("img").forEach((img) => {
    const origin = img.getAttribute("data-origin-src");
    if (origin) img.setAttribute("src", origin);
    const src = img.getAttribute("src") || "";
    if (src.includes("/api/image-proxy")) {
      try {
        img.setAttribute("src", new URL(src, location.origin).searchParams.get("url") || origin || src);
      } catch (_error) { /* keep */ }
    }
  });
  return box.innerHTML;
}

function setDetailMode(mode) {
  const html = prepareDetailHtml(readDetailHtml());
  detailMode = mode;
  $("#detailVisual").hidden = mode !== "editor";
  $("#detailHtml").hidden = mode !== "html";
  $("#detailText").hidden = mode !== "text";
  $("#detailToolbar").hidden = mode !== "editor";
  document.querySelectorAll("[data-detail-mode]").forEach((button) => {
    button.classList.toggle("active", button.dataset.detailMode === mode);
  });
  if (mode === "editor") {
    $("#detailVisual").innerHTML = html;
    bindDetailImages($("#detailVisual"));
  }
  if (mode === "html") $("#detailHtml").value = html;
  if (mode === "text") $("#detailText").value = htmlToText(html);
}

function openDetailEditor() {
  if (!current) return toast("먼저 상품을 선택해 주세요.", true);
  if (masterEditBlocked()) return;
  const html = prepareDetailHtml(current.detail_html || "");
  $("#detailVisual").innerHTML = html;
  bindDetailImages($("#detailVisual"));
  $("#detailHtml").value = html;
  $("#detailText").value = htmlToText(html);
  $("#detailImageUrl").value = "";
  setDetailMode("editor");
  $("#detailDialog").showModal();
}

async function fillDetailIntroInEditor() {
  if (!current) return toast("먼저 상품을 선택해 주세요.", true);
  if (masterEditBlocked()) return;
  const button = $("#detailIntroAi");
  const label = button?.textContent || "추가글 AI";
  if (button) {
    button.disabled = true;
    button.textContent = "만드는 중...";
  }
  try {
    await saveProduct(current, { detail_html: readDetailHtml() });
    current = await api(`/api/products/${current.id}/detail-intro/ai`, {
      method: "POST",
      body: JSON.stringify({ instruction: $("#fieldInstruction")?.value || "" }),
    });
    const index = products.findIndex((item) => item.id === current.id);
    if (index >= 0) products[index] = current;
    const html = prepareDetailHtml(current.detail_html || "");
    $("#detailVisual").innerHTML = html;
    bindDetailImages($("#detailVisual"));
    $("#detailHtml").value = html;
    $("#detailText").value = htmlToText(html);
    setDetailMode("editor");
    toast("상세페이지 위에 추가글을 넣었습니다. 확인 후 저장하세요.");
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = label;
    }
  }
}

function insertDetailHtml(html) {
  setDetailMode("editor");
  $("#detailVisual").focus();
  document.execCommand("insertHTML", false, html);
}

async function addDetailImages() {
  if (!current) return toast("먼저 상품을 선택해 주세요.", true);
  const url = $("#detailImageUrl").value.trim();
  const files = [...($("#detailImageFile").files || [])];
  $("#detailImageFile").value = "";
  if (!url && !files.length) {
    $("#detailImageFile").click();
    return;
  }
  try {
    if (url && !files.length && /^https?:\/\//i.test(url)) {
      insertDetailHtml(`<p><img src="${url.replace(/"/g, "&quot;")}" alt=""></p>`);
      $("#detailImageUrl").value = "";
      return;
    }
    const form = new FormData();
    files.filter(isImageFile).forEach((file) => form.append("files", file, file.name || "image.jpg"));
    if (url) form.append("url", url);
    const response = await fetch(`/api/products/${current.id}/detail-images`, { method: "POST", body: form });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "이미지를 넣지 못했습니다.");
    if (data.product) {
      current = data.product;
      const index = products.findIndex((item) => item.id === current.id);
      if (index >= 0) products[index] = current;
    }
    (data.urls || []).forEach((src) => insertDetailHtml(`<p><img src="${src}" alt=""></p>`));
    $("#detailImageUrl").value = "";
    toast("상세 이미지를 넣었습니다.");
  } catch (error) {
    toast(error.message, true);
  }
}

function categoryLeafName(name) {
  const parts = String(name || "").split(/\s*[>/]\s*/).map((part) => part.trim()).filter(Boolean);
  return parts[parts.length - 1] || name || "카테고리";
}

function optionLabel(item) {
  return item.label || item.max || "";
}

function attributeKind(item) {
  const type = String(item.classificationType || item.attributeType || "SINGLE_SELECT").toUpperCase();
  if (type.includes("MULTI")) return "multi";
  if (type.includes("RANGE")) return "combo";
  if (type === "INPUT" || type === "TEXT" || type === "NUMBER") return "input";
  if (attributeNeedsReal(item) && (item.values || []).length) return "combo";
  if (type.includes("SINGLE") || type.includes("SELECT") || (item.values || []).length) return "select";
  return "input";
}

function optionLooksNumeric(option) {
  const label = String(option?.label || option?.max || "").trim();
  if (!label) return false;
  if (/[0-9]/.test(label) && /[~～\-]|W|㎾|kW|㎡|cm|mm|kg|\bL\b|ml|\bV\b/i.test(label)) return true;
  return /^[0-9]+(?:\.[0-9]+)?$/.test(label.replace(/\s+/g, ""));
}

function attributeNeedsReal(item) {
  if (isEnergyEfficiencyAttribute(item?.attributeName)) return false;
  const type = String(item?.classificationType || item?.attributeType || "").toUpperCase();
  if (type.includes("MULTI")) return false;
  if (type.includes("RANGE") || type === "INPUT" || type === "TEXT" || type === "NUMBER") return true;
  const options = item?.values || [];
  if (!options.length) return true;
  if (!options.some(optionLooksNumeric)) return false;
  if (item?.unitUsable) return true;
  return Boolean(item?.inputUsable);
}

function attributeGroupName(item) {
  return item.group || "기본정보";
}

function selectedAttributeValues(seq, saved) {
  return (saved || []).filter((item) => Number(item.attributeSeq) === Number(seq));
}

function bareAttributeText(value) {
  return String(value || "").replace(/[~～]+/g, " ").replace(/\s+/g, "").toLowerCase();
}

function matchAttributeOption(options, token) {
  const needle = bareAttributeText(token);
  if (!needle) return null;
  return options.find((item) => {
    const label = bareAttributeText(item.label);
    const maximum = bareAttributeText(item.max);
    return needle === label || needle === maximum;
  }) || options.find((item) => {
    const label = bareAttributeText(item.label);
    return needle && (needle.includes(label) || label.includes(needle));
  }) || null;
}

function matchCollectedAttributes(schema, collected, existing) {
  const bySeq = new Map();
  (existing || []).forEach((item) => {
    if (!item.attributeSeq) return;
    const list = bySeq.get(Number(item.attributeSeq)) || [];
    list.push(item);
    bySeq.set(Number(item.attributeSeq), list);
  });
  const nameMap = new Map();
  (collected || []).forEach((item) => {
    const name = String(item.name || "").replace(/\s+/g, "").toLowerCase();
    const value = String(item.value || "").trim();
    if (!name || !value) return;
    const list = nameMap.get(name) || [];
    list.push(value);
    nameMap.set(name, list);
  });
  const result = [];
  orderedAttributeSchema(schema).forEach((attr) => {
    const seq = Number(attr.attributeSeq);
    if (!seq || isCertificationAttribute(attr.attributeName) || isEnergyEfficiencyAttribute(attr.attributeName)) return;
    if (bySeq.has(seq)) {
      result.push(...bySeq.get(seq));
      return;
    }
    const key = String(attr.attributeName || "").replace(/\s+/g, "").toLowerCase();
    let values = nameMap.get(key) || [];
    if (!values.length) {
      for (const [other, list] of nameMap.entries()) {
        if (key && (key.includes(other) || other.includes(key))) {
          values = list;
          break;
        }
      }
    }
    if (!values.length) {
      if (isAsAttribute(attr.attributeName)) {
        const option = asDefaultOption(attr);
        if (option?.attributeValueSeq) {
          result.push({ attributeSeq: seq, attributeValueSeq: Number(option.attributeValueSeq) });
        }
      }
      return;
    }
    const kind = attributeKind(attr);
    const options = attr.values || [];
    if (kind === "multi") {
      const seen = new Set();
      values.flatMap((raw) => String(raw).split(/[,/|]/)).forEach((token) => {
        const matched = matchAttributeOption(options, token.trim());
        if (matched?.attributeValueSeq && !seen.has(matched.attributeValueSeq)) {
          seen.add(matched.attributeValueSeq);
          result.push({ attributeSeq: seq, attributeValueSeq: Number(matched.attributeValueSeq) });
        }
      });
      return;
    }
    const entry = { attributeSeq: seq };
    const matched = matchAttributeOption(options, values[0])
      || (/^(가능|있음|지원|해당|포함|사용|y|yes)$/i.test(String(values[0] || "").trim())
        ? matchAttributeOption(options, attr.attributeName)
        : null);
    if (matched?.attributeValueSeq) entry.attributeValueSeq = Number(matched.attributeValueSeq);
    if (attributeNeedsReal(attr)) {
      entry.attributeRealValue = values[0];
    }
    if (options.length && !entry.attributeValueSeq) return;
    if (entry.attributeValueSeq || entry.attributeRealValue) result.push(entry);
  });
  orderedAttributeSchema(schema).forEach((attr) => {
    const seq = Number(attr.attributeSeq);
    if (!seq || !isAsAttribute(attr.attributeName)) return;
    if (result.some((item) => Number(item.attributeSeq) === seq)) return;
    const option = asDefaultOption(attr);
    if (option?.attributeValueSeq) {
      result.push({ attributeSeq: seq, attributeValueSeq: Number(option.attributeValueSeq) });
    }
  });
  return result;
}

function renderFallbackAttributes(rows) {
  const box = $("#attributeFields");
  box.dataset.mode = "fallback";
  box.innerHTML = "";
  const items = rows.length ? rows : [{ name: "", value: "" }];
  items.forEach((item, index) => {
    const row = document.createElement("div");
    row.className = "attribute-row attribute-fallback";
    row.dataset.attrIndex = String(index + 1);
    row.innerHTML = `
      <span>속성</span>
      <div class="attribute-controls">
        <input data-name placeholder="속성명" value="${escapeAttr(item.name || "")}" />
        <input data-value placeholder="속성값" value="${escapeAttr(item.value || "")}" />
      </div>`;
    box.appendChild(row);
  });
}

function appendAttributeSelect(parent, values, pickedSeq) {
  const select = document.createElement("select");
  select.dataset.valueSelect = "1";
  const blank = document.createElement("option");
  blank.value = "";
  blank.textContent = "선택";
  select.appendChild(blank);
  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value.attributeValueSeq;
    option.textContent = optionLabel(value);
    select.appendChild(option);
  });
  if (pickedSeq) select.value = String(pickedSeq);
  parent.appendChild(select);
  return select;
}

function orderedAttributeSchema(schema) {
  return (schema || []).map((item, index) => ({ item, index })).sort((a, b) => {
    const left = Number.isInteger(a.item.order) ? a.item.order : a.index;
    const right = Number.isInteger(b.item.order) ? b.item.order : b.index;
    return left - right;
  }).map((row) => row.item);
}

function attributeErrorFocus(token) {
  const text = String(token || "");
  if (/단위|UnitCode/i.test(text)) return "unit";
  if (/실제값|RealValue/i.test(text)) return "real";
  if (/속성값|ValueSeq/i.test(text)) return "value";
  return "real";
}

function parseAttributeRegisterErrors(text) {
  const raw = String(text || "").replace(/\s+/g, " ").trim();
  if (!raw) return [];
  const found = [];
  const seen = new Set();
  const add = (index, focus, hint) => {
    const number = Number(index);
    if (!Number.isInteger(number) || number < 1) return;
    const key = `${number}:${focus}`;
    if (seen.has(key)) return;
    seen.add(key);
    found.push({ index: number, focus, hint: String(hint || "").trim() });
  };
  const pathRe = /productAttributes\[(\d+)\](?:\.(\w+))?/gi;
  let match;
  while ((match = pathRe.exec(raw))) {
    add(Number(match[1]) + 1, attributeErrorFocus(match[2] || match[0]), match[0]);
  }
  const nthRe = /(\d+)\s*번째\s*속성([^\s.]*)/g;
  while ((match = nthRe.exec(raw))) {
    add(Number(match[1]), attributeErrorFocus(match[0]), match[0]);
  }
  return found;
}

function sentAttributePayloadRows(schema, saved) {
  const ordered = orderedAttributeSchema(schema);
  const bySeq = new Map();
  const extras = [];
  (saved || []).forEach((item) => {
    const seq = Number(item?.attributeSeq);
    if (!seq) return;
    if (!bySeq.has(seq)) extras.push(seq);
    const list = bySeq.get(seq) || [];
    list.push(item);
    bySeq.set(seq, list);
  });
  const inSchema = new Set();
  const seqs = [];
  ordered.forEach((attr) => {
    const seq = Number(attr.attributeSeq);
    if (!seq || isCertificationAttribute(attr.attributeName) || isEnergyEfficiencyAttribute(attr.attributeName) || !bySeq.has(seq)) return;
    inSchema.add(seq);
    seqs.push(seq);
  });
  extras.forEach((seq) => {
    if (!inSchema.has(seq)) seqs.push(seq);
  });
  const schemaBySeq = new Map(ordered.map((attr) => [Number(attr.attributeSeq), attr]));
  const rows = [];
  seqs.forEach((seq) => {
    const attr = schemaBySeq.get(seq) || {};
    if (isCertificationAttribute(attr.attributeName) || isEnergyEfficiencyAttribute(attr.attributeName)) return;
    (bySeq.get(seq) || []).forEach((item) => {
      if (!Number(item.attributeValueSeq)) return;
      rows.push({ seq, attr, item });
    });
  });
  return rows;
}

function ensureAttributeRealInput(row) {
  let input = row.querySelector("[data-real]");
  if (input) return input;
  const cell = row.querySelector("td") || row;
  let stack = row.querySelector(".attribute-stack");
  if (!stack) {
    stack = document.createElement("div");
    stack.className = "attribute-stack";
    cell.appendChild(stack);
  }
  input = document.createElement("input");
  input.dataset.real = "1";
  input.placeholder = "실제값을 입력해주세요";
  stack.appendChild(input);
  return input;
}

function markAttributeErrorRow(row, parsed) {
  row.classList.add("attribute-error-row");
  const nameCell = row.querySelector(".attribute-name, span");
  if (nameCell && !nameCell.querySelector(".attribute-error-mark")) {
    const mark = document.createElement("em");
    mark.className = "attribute-error-mark";
    mark.textContent = "오류";
    nameCell.appendChild(mark);
  }
  let focusEl = null;
  if ((parsed.focus === "real" || parsed.focus === "unit") && row.dataset.needsReal === "1") {
    focusEl = ensureAttributeRealInput(row);
  } else {
    focusEl = row.querySelector("[data-value-select], [data-real], [data-value], [data-name]");
  }
  return focusEl;
}

function focusAttributeRegisterError(product) {
  const box = $("#attributeFields");
  const message = $("#attributeMessage");
  const parsedList = parseAttributeRegisterErrors(product?.last_error);
  if (!box || !parsedList.length) return;
  const visible = [...box.querySelectorAll("tr[data-attr-seq], .attribute-fallback")];
  if (!visible.length) return;
  const sent = sentAttributePayloadRows(product?.attribute_schema || [], product?.naver_attributes || []);
  const names = [];
  let firstFocus = null;
  let firstRow = null;
  parsedList.forEach((parsed) => {
    const realRows = sent.filter((item) => attributeNeedsReal(item.attr));
    let sentRow = sent[parsed.index - 1];
    if ((parsed.focus === "real" || parsed.focus === "unit") && (!sentRow || !attributeNeedsReal(sentRow.attr))) {
      sentRow = realRows[parsed.index - 1]
        || sent.slice(Math.max(parsed.index - 1, 0)).find((item) => attributeNeedsReal(item.attr))
        || realRows[0]
        || sentRow;
    }
    let row = sentRow
      ? visible.find((item) => Number(item.dataset.attrSeq) === Number(sentRow.seq))
      : null;
    if (!row && parsed.focus !== "real" && parsed.focus !== "unit") row = visible[parsed.index - 1] || null;
    if (!row) return;
    if ((parsed.focus === "real" || parsed.focus === "unit") && row.dataset.needsReal !== "1") return;
    const focusEl = markAttributeErrorRow(row, parsed);
    const name = row.dataset.attrName
      || row.querySelector("[data-name]")?.value.trim()
      || sentRow?.attr?.attributeName
      || `${parsed.index}번째 속성`;
    names.push(name);
    if (!firstRow) {
      firstRow = row;
      firstFocus = focusEl;
    }
  });
  if (!firstRow) return;
  const hint = parsedList[0].focus === "unit"
    ? "단위를 확인해 주세요."
    : parsedList[0].focus === "value"
      ? "값을 선택해 주세요."
      : "실제값을 입력해 주세요.";
  if (message && !String(message.textContent || "").trim()) {
    message.textContent = `등록 오류: ${names.join(", ")} — ${hint}`;
  }
  setTimeout(() => {
    firstRow.scrollIntoView({ block: "center", inline: "nearest", behavior: "smooth" });
    if (!firstFocus) return;
    firstFocus.focus();
    if (typeof firstFocus.select === "function") firstFocus.select();
  }, 60);
}

function renderAttributeFields(schema, saved, collected) {
  const box = $("#attributeFields");
  if (!schema.length) {
    renderFallbackAttributes(collected || []);
    return;
  }
  box.dataset.mode = "schema";
  box.innerHTML = "";
  const table = document.createElement("table");
  table.className = "attribute-table";
  let lastGroup = "";
  orderedAttributeSchema(schema).forEach((item) => {
    if (isCertificationAttribute(item.attributeName)) return;
    const group = attributeGroupName(item);
    if (group !== lastGroup) {
      const head = table.insertRow();
      head.className = "attribute-section";
      const cell = document.createElement("th");
      cell.colSpan = 2;
      cell.textContent = group;
      head.appendChild(cell);
      lastGroup = group;
    }
    const kind = attributeKind(item);
    const energyLocked = isEnergyEfficiencyAttribute(item.attributeName);
    let selected = energyLocked ? [] : selectedAttributeValues(item.attributeSeq, saved);
    if (isAsAttribute(item.attributeName) && !selected.find((row) => row.attributeValueSeq)) {
      const option = asDefaultOption(item);
      if (option?.attributeValueSeq) {
        selected = [{ attributeSeq: item.attributeSeq, attributeValueSeq: option.attributeValueSeq }];
      }
    }
    const real = selected.find((row) => row.attributeRealValue)?.attributeRealValue || "";
    const picked = selected.find((row) => row.attributeValueSeq);
    const needsReal = !energyLocked && attributeNeedsReal(item);
    const row = table.insertRow();
    row.dataset.attrSeq = item.attributeSeq;
    row.dataset.attrName = item.attributeName || "";
    row.dataset.attrType = kind;
    row.dataset.needsReal = needsReal ? "1" : "";
    row.dataset.attrIndex = String(table.querySelectorAll("tr[data-attr-seq]").length);
    const nameCell = document.createElement("th");
    nameCell.className = "attribute-name";
    const essential = item.essential ?? item.required;
    nameCell.textContent = `${item.attributeName || "속성"}${essential ? " *" : ""}`;
    const valueCell = document.createElement("td");
    if (kind === "multi") {
      const checks = document.createElement("div");
      checks.className = "attribute-checks";
      const chosen = new Set(selected.map((row) => Number(row.attributeValueSeq)));
      (item.values || []).forEach((value) => {
        const label = document.createElement("label");
        const boxInput = document.createElement("input");
        boxInput.type = "checkbox";
        boxInput.dataset.value = "1";
        boxInput.value = value.attributeValueSeq;
        boxInput.dataset.label = optionLabel(value);
        boxInput.checked = chosen.has(Number(value.attributeValueSeq));
        label.append(boxInput, document.createTextNode(optionLabel(value)));
        checks.appendChild(label);
      });
      valueCell.appendChild(checks);
    } else {
      const stack = document.createElement("div");
      stack.className = "attribute-stack";
      if (kind === "select" || kind === "combo") {
        const select = appendAttributeSelect(stack, item.values || [], energyLocked ? "" : picked?.attributeValueSeq);
        if (energyLocked) {
          select.value = "";
          select.disabled = true;
          select.title = "에너지효율 등급은 선택하지 않습니다.";
        }
      }
      if (needsReal) {
        const realRow = document.createElement("div");
        realRow.className = item.unit ? "attribute-real-row" : "attribute-stack";
        const input = document.createElement("input");
        input.dataset.real = "1";
        input.placeholder = "실제값을 입력해주세요";
        input.value = real;
        realRow.appendChild(input);
        if (item.unit) {
          const unit = document.createElement("span");
          unit.className = "attribute-unit";
          unit.dataset.unit = item.unit;
          unit.textContent = item.unit;
          realRow.appendChild(unit);
        }
        stack.appendChild(realRow);
      }
      valueCell.appendChild(stack);
    }
    row.append(nameCell, valueCell);
  });
  box.appendChild(table);
}

function readAttributeForm() {
  const box = $("#attributeFields");
  if (box.dataset.mode === "fallback") {
    const attributes = [...box.querySelectorAll(".attribute-fallback")].map((row) => ({
      name: row.querySelector("[data-name]")?.value.trim() || "",
      value: row.querySelector("[data-value]")?.value.trim() || "",
    })).filter((item) => item.name && item.value);
    return { fallback: true, attributes, naver_attributes: current?.naver_attributes || [] };
  }
  const naver = [];
  const attributes = [];
  box.querySelectorAll("[data-attr-seq]").forEach((row) => {
    const seq = Number(row.dataset.attrSeq);
    const name = row.dataset.attrName;
    const kind = row.dataset.attrType;
    if (isEnergyEfficiencyAttribute(name)) return;
    if (kind === "multi") {
      const labels = [];
      row.querySelectorAll("[data-value]:checked").forEach((input) => {
        naver.push({ attributeSeq: seq, attributeValueSeq: Number(input.value) });
        labels.push(input.dataset.label);
      });
      if (labels.length) attributes.push({ name, value: labels.join(",") });
      return;
    }
    const real = row.querySelector("[data-real]")?.value.trim() || "";
    const unit = row.querySelector("[data-unit]")?.dataset.unit || row.querySelector("[data-unit]")?.value.trim() || "";
    const select = row.querySelector("[data-value-select]");
    const valueSeq = select?.value ? Number(select.value) : 0;
    const label = select?.selectedOptions?.[0]?.textContent || "";
    const realText = real && unit && !real.endsWith(unit) ? `${real}${unit}` : real;
    const entry = { attributeSeq: seq };
    if (valueSeq) entry.attributeValueSeq = valueSeq;
    if (real) entry.attributeRealValue = real;
    if (!entry.attributeValueSeq && !entry.attributeRealValue && isAsAttribute(name)) {
      const attr = (current?.attribute_schema || []).find((item) => Number(item.attributeSeq) === seq);
      const option = asDefaultOption(attr || {});
      if (option?.attributeValueSeq) {
        entry.attributeValueSeq = Number(option.attributeValueSeq);
        attributes.push({ name, value: option.label || option.max || "무상1년" });
        naver.push(entry);
        return;
      }
    }
    if (entry.attributeValueSeq || entry.attributeRealValue) {
      naver.push(entry);
      attributes.push({ name, value: realText || (label === "선택하세요" ? "" : label) });
    }
  });
  return { fallback: false, naver_attributes: naver, attributes: attributes.filter((item) => item.value) };
}

async function openAttributeEditor() {
  const item = current || selectedProducts()[0];
  if (!item) return toast("먼저 상품을 선택해 주세요.", true);
  if (masterEditBlocked(item)) return;
  current = item;
  const lastError = String(current.last_error || "");
  const leaf = categoryLeafName(current.category_name || current.source_category || "");
  $("#attributeCategory").innerHTML = current.category_id || current.category_name
    ? `<strong>[${leaf}]</strong> 카테고리 맞춤형 검색정보를 입력해보세요.`
    : "카테고리가 없습니다. 카테고리마다 속성이 다릅니다.";
  $("#attributeMessage").textContent = "";
  $("#attributeFields").innerHTML = "<p class='hint'>카테고리 속성을 불러오는 중입니다.</p>";
  $("#attributeDialog").showModal();
  if (!current.category_id) {
    $("#attributeMessage").textContent = "먼저 카테고리매핑을 하면 그 카테고리 속성만 나옵니다.";
    renderFallbackAttributes(current.attributes || []);
    current.last_error = lastError;
    focusAttributeRegisterError(current);
    return;
  }
  try {
    const product = await api(`/api/products/${current.id}/attributes/fetch`, { method: "POST", body: "{}" });
    current = product;
    if (lastError && !current.last_error) current.last_error = lastError;
    const index = products.findIndex((row) => row.id === current.id);
    if (index >= 0) products[index] = current;
    const saved = current.naver_attributes?.length
      ? current.naver_attributes
      : matchCollectedAttributes(current.attribute_schema || [], current.attributes || []);
    renderAttributeFields(current.attribute_schema || [], saved, current.attributes || []);
    if (!(current.attribute_schema || []).length) {
      $("#attributeMessage").textContent = "이 카테고리에 내려온 속성이 없습니다. 수집한 속성을 수정하세요.";
    }
    focusAttributeRegisterError(current);
  } catch (error) {
    $("#attributeMessage").textContent = error.message;
    renderFallbackAttributes(current.attributes || []);
    current.last_error = lastError;
    focusAttributeRegisterError(current);
  }
}

function fillAttributeCollected() {
  if (!current) return;
  const schema = current.attribute_schema || [];
  if (!schema.length) {
    renderFallbackAttributes(current.attributes || []);
    focusAttributeRegisterError(current);
    return;
  }
  renderAttributeFields(schema, matchCollectedAttributes(schema, current.attributes || []), current.attributes || []);
  focusAttributeRegisterError(current);
  toast("수집한 속성값으로 채웠습니다.");
}

async function fillAttributeAi() {
  if (!current) return toast("먼저 상품을 선택해 주세요.", true);
  if (!current.category_id) return toast("먼저 카테고리매핑을 해 주세요.", true);
  try {
    current = await api(`/api/products/${current.id}/attributes/ai`, { method: "POST", body: "{}" });
    const index = products.findIndex((row) => row.id === current.id);
    if (index >= 0) products[index] = current;
    renderAttributeFields(current.attribute_schema || [], current.naver_attributes || [], current.attributes || []);
    focusAttributeRegisterError(current);
    toast("상품 상세페이지를 읽고 속성을 넣었습니다.");
  } catch (error) {
    toast(error.message, true);
  }
}

let categoryTargetIds = [];

function openCategoryMapper(productIds) {
  const requested = Array.isArray(productIds) && productIds.length ? productIds : [...selectedIds];
  const targets = requested
    .map((id) => products.find((item) => item.id === id))
    .filter((item) => item && !isMasterProduct(item));
  if (!targets.length) {
    if (current && isMasterProduct(current)) return masterEditBlocked(current);
    return toast("먼저 상품을 선택해 주세요.", true);
  }
  categoryTargetIds = targets.map((item) => item.id);
  const sample = targets[0];
  const rawCategory = sample.category_name || sample.source_category || "";
  const leaf = rawCategory ? categoryLeafName(rawCategory) : "";
  $("#categoryQuery").value = leaf;
  $("#categoryResults").innerHTML = "";
  $("#categoryMessage").textContent = targets.length > 1
    ? `선택한 ${targets.length}개 상품입니다. 검색해서 카테고리를 고르세요.`
    : "검색해서 카테고리를 고르세요.";
  $("#categoryDialog").showModal();
  $("#categoryQuery").focus();
  $("#categoryQuery").select();
  if (leaf) searchCategoryList();
}

async function searchCategoryList() {
  const query = $("#categoryQuery").value.trim();
  const list = $("#categoryResults");
  list.innerHTML = "";
  if (!query) return;
  try {
    const rows = await api(`/api/categories?q=${encodeURIComponent(query)}`);
    if (!rows.length) {
      $("#categoryMessage").textContent = "맞는 카테고리가 없습니다.";
      return;
    }
    rows.forEach((item) => {
      const row = document.createElement("li");
      row.textContent = item.name;
      row.addEventListener("click", async () => {
        const ids = categoryTargetIds.filter((id) => {
          const product = products.find((entry) => entry.id === id);
          return product && !isMasterProduct(product);
        });
        if (!ids.length) return toast("바꿀 상품이 없습니다.", true);
        const keyword = categoryLeafName(item.name);
        try {
          for (const id of ids) {
            const product = products.find((entry) => entry.id === id);
            await saveProduct(product, {
              category_id: item.id,
              category_name: item.name,
              category_keyword: keyword,
              source_category: item.name,
            });
          }
          await loadProducts();
          if (products.some((entry) => entry.id === ids[0])) selectProduct(ids[0]);
          $("#categoryDialog").close();
          toast(ids.length > 1 ? `${ids.length}개 상품의 카테고리를 바꿨습니다.` : "카테고리를 바꿨습니다.");
        } catch (error) {
          toast(error.message, true);
        }
      });
      list.appendChild(row);
    });
    $("#categoryMessage").textContent = `${rows.length}개 카테고리`;
  } catch (error) {
    $("#categoryMessage").textContent = error.message;
  }
}

function onGridContextMenu(event) {
  const row = event.target.closest(".grid tr[data-id]");
  if (event.target.closest("input, textarea, select, [contenteditable='true']") && !row) {
    hideContextMenu();
    return;
  }
  if (!row) {
    if (!event.target.closest("#contextMenu")) hideContextMenu();
    return;
  }
  event.preventDefault();
  event.stopPropagation();
  const id = row.dataset.id;
  if (!selectedIds.has(id)) selectProduct(id, false);
  else {
    current = products.find((item) => item.id === id) || current;
    fillPreview();
    updateSelectionText();
  }
  showContextMenu(event.clientX, event.clientY);
}

async function runContextAction(action) {
  hideContextMenu();
  const actions = {
    "view-collected": openCollectedProduct,
    "view-registered": openRegisteredProduct,
    category: openCategoryMapper,
    options: openOptionEditor,
    attributes: () => openAttributeEditor().catch((error) => toast(error.message, true)),
    unit: () => focusProductField("unit_price"),
    tags: openTagEditor,
    images: openImageEditor,
    detail: openDetailEditor,
    notices: openNoticeDialog,
    "name-keywords": () => openNameKeywordDialog().catch((error) => toast(error.message, true)),
    discount: openDiscountDialog,
    "ai-name": () => aiRewriteSelected("name").catch((error) => toast(error.message, true)),
    "ai-tags": () => aiRewriteSelected("tags").catch((error) => toast(error.message, true)),
    "ai-attributes": () => aiRewriteSelected("attributes").catch((error) => toast(error.message, true)),
    "detail-intro": () => aiRewriteSelected("detail-intro").catch((error) => toast(error.message, true)),
    "shuffle-0": () => shuffleSelectedNames(0),
    "shuffle-1": () => shuffleSelectedNames(1),
    "shuffle-2": () => shuffleSelectedNames(2),
    "shuffle-3": () => shuffleSelectedNames(3),
    "shuffle-4": () => shuffleSelectedNames(4),
    "shuffle-5": () => shuffleSelectedNames(5),
    check: checkSelectedRows,
    uncheck: uncheckSelectedRows,
    collect: () => collectSelectedItems().catch((error) => toast(error.message, true)),
    save: () => saveSelected().catch((error) => toast(error.message, true)),
    "send-market": () => openSendMarketDialog().catch((error) => toast(error.message, true)),
    "refresh-original": () => refreshOriginalProducts().catch((error) => toast(error.message, true)),
    "refresh-market": () => refreshMarketProducts().catch((error) => toast(error.message, true)),
    register: () => registerSelected().catch((error) => toast(error.message, true)),
    delete: () => deleteSelected().catch((error) => toast(error.message, true)),
    undo: () => undoProductChange().catch((error) => toast(error.message, true)),
    redo: () => redoProductChange().catch((error) => toast(error.message, true)),
    "change-category": openCategoryMapper,
    "change-name": openNameEditor,
    "change-attributes": () => openAttributeEditor().catch((error) => toast(error.message, true)),
    "change-tags": openTagEditor,
    ai: () => aiPolishSelected().catch((error) => toast(error.message, true)),
    delivery: () => openDeliveryEditor().catch((error) => toast(error.message, true)),
    benefit: () => openBenefitEditor().catch((error) => toast(error.message, true)),
    "stop-job": () => stopCurrentJob(),
  };
  await actions[action]?.();
}

async function loadSettingsForm() {
  const settings = await api("/api/settings");
  const form = $("#settingsForm");
  Object.entries(settings).forEach(([key, value]) => {
    const field = form.elements[key];
    if (!field || key.endsWith("_set")) return;
    if (field.type === "checkbox") field.checked = Boolean(value);
    else if (field.type === "password") {
      field.value = "";
      field.placeholder = settings[`${key}_set`] ? "저장되어 있습니다" : (field.dataset.placeholder || field.placeholder);
    }
    else field.value = value ?? "";
  });
  syncAiProviderFields();
}

function syncAiProviderFields() {
  const provider = $("#aiProvider")?.value || "gemini";
  document.querySelectorAll("[data-ai-provider]").forEach((row) => {
    row.hidden = row.dataset.aiProvider !== provider;
  });
}

function settingsPayload() {
  const form = $("#settingsForm");
  const data = {};
  [...form.elements].forEach((field) => {
    if (!field.name) return;
    data[field.name] = field.type === "checkbox" ? field.checked : field.value;
  });
  if ("default_stock" in data) data.default_stock = Number(data.default_stock || 0);
  return data;
}

$("#tabProducts").addEventListener("click", () => showSheet("products"));
$("#tabOptions").addEventListener("click", () => showSheet("options"));
$("#appTabProducts").addEventListener("click", () => showAppView("products"));
$("#appTabOrders").addEventListener("click", () => showAppView("orders"));
$("#appTabInquiries")?.addEventListener("click", () => showAppView("inquiries"));
$("#appTabCollect")?.addEventListener("click", () => showAppView("collect"));
$("#appTabWholesalers").addEventListener("click", () => showAppView("wholesalers"));
$("#appTabSettings").addEventListener("click", () => showAppView("settings"));
const HELP_BY_VIEW = {
  products: "help-products",
  orders: "help-orders",
  inquiries: "help-inquiries",
  collect: "help-collect",
  wholesalers: "help-wholesale",
  ownerclan: "help-collect",
  settings: "help-settings",
  help: "help-overview",
};

let lastAppView = "products";
let activeHelpPanel = "help-overview";

$("#appTabHelp")?.addEventListener("click", () => showAppView("help"));
$("#helpNav")?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-help]");
  if (!button) return;
  showHelpPanel(button.dataset.help);
});

let helpSearchHits = [];

function clearHelpSearchMarks() {
  $("#helpBody")?.querySelectorAll("mark.help-hit").forEach((mark) => {
    mark.replaceWith(document.createTextNode(mark.textContent));
  });
  $("#helpBody")?.normalize();
}

function showHelpPanel(id) {
  const wanted = String(id || "help-overview");
  const panels = [...document.querySelectorAll("#helpBody .help-panel")];
  if (!panels.length) return;
  const exists = panels.some((panel) => panel.dataset.helpPanel === wanted);
  activeHelpPanel = exists ? wanted : "help-overview";
  panels.forEach((panel) => {
    panel.hidden = panel.dataset.helpPanel !== activeHelpPanel;
  });
  $("#helpNav")?.querySelectorAll("button[data-help]").forEach((item) => {
    item.classList.toggle("active", item.dataset.help === activeHelpPanel);
  });
  $("#helpBody")?.scrollTo({ top: 0 });
}

function helpSections() {
  return [...document.querySelectorAll("#helpBody .help-panel")].map((panel) => ({
    id: panel.dataset.helpPanel || panel.id || "",
    title: panel.querySelector("h2")?.textContent.trim() || panel.id || "도움말",
    nodes: [panel],
    panel,
  }));
}

function markHelpText(node, query) {
  const hits = [];
  const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT);
  const texts = [];
  while (walker.nextNode()) texts.push(walker.currentNode);
  const needle = query.toLowerCase();
  texts.forEach((textNode) => {
    const value = textNode.nodeValue || "";
    const lower = value.toLowerCase();
    if (!lower.includes(needle)) return;
    const fragment = document.createDocumentFragment();
    let cursor = 0;
    let index = lower.indexOf(needle);
    while (index >= 0) {
      if (index > cursor) fragment.append(value.slice(cursor, index));
      const mark = document.createElement("mark");
      mark.className = "help-hit";
      mark.textContent = value.slice(index, index + query.length);
      fragment.append(mark);
      hits.push(mark);
      cursor = index + query.length;
      index = lower.indexOf(needle, cursor);
    }
    if (cursor < value.length) fragment.append(value.slice(cursor));
    textNode.parentNode.replaceChild(fragment, textNode);
  });
  return hits;
}

function showHelpHit(index) {
  const mark = helpSearchHits[index];
  if (!mark) return;
  document.querySelectorAll("mark.help-hit.current").forEach((item) => item.classList.remove("current"));
  mark.classList.add("current");
  if (mark.dataset.section) showHelpPanel(mark.dataset.section);
  mark.scrollIntoView({ block: "center" });
  $("#helpSearchResults")?.querySelectorAll("button").forEach((item) => {
    item.classList.toggle("active", Number(item.dataset.hit) === index);
  });
}

function searchHelp(raw) {
  const query = String(raw || "").trim();
  clearHelpSearchMarks();
  helpSearchHits = [];
  const results = $("#helpSearchResults");
  const status = $("#helpSearchStatus");
  results?.replaceChildren();
  const needle = query.toLowerCase();
  helpSections().forEach((section) => {
    const matched = !query || section.panel.textContent.toLowerCase().includes(needle);
    const nav = section.id ? $(`#helpNav button[data-help="${section.id}"]`) : null;
    if (nav) nav.hidden = Boolean(query) && !matched;
    if (!query) return;
    if (!matched) return;
    markHelpText(section.panel, query).forEach((mark) => {
      mark.dataset.section = section.id;
      const index = helpSearchHits.length;
      helpSearchHits.push(mark);
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.hit = String(index);
      const title = document.createElement("strong");
      title.textContent = section.title;
      const snippet = document.createElement("span");
      const text = (mark.parentElement?.textContent || "").replace(/\s+/g, " ").trim();
      snippet.textContent = text.length > 72 ? `${text.slice(0, 72)}…` : text;
      button.append(title, snippet);
      results?.append(button);
    });
  });
  if (!query) {
    $("#helpNav")?.querySelectorAll("button[data-help]").forEach((item) => {
      item.hidden = false;
    });
    showHelpPanel(activeHelpPanel || "help-overview");
    if (status) status.hidden = true;
    if (results) results.hidden = true;
    return;
  }
  if (status) {
    status.hidden = false;
    status.textContent = helpSearchHits.length ? `${helpSearchHits.length}건` : "찾는 내용이 없습니다.";
  }
  if (results) results.hidden = helpSearchHits.length === 0;
  if (helpSearchHits.length) showHelpHit(0);
  else showHelpPanel(activeHelpPanel || "help-overview");
}

$("#helpSearch")?.addEventListener("input", () => searchHelp($("#helpSearch").value));
$("#helpSearch")?.addEventListener("keydown", (event) => {
  if (event.key !== "Enter") return;
  event.preventDefault();
  const buttons = [...($("#helpSearchResults")?.querySelectorAll("button") || [])];
  if (!buttons.length) return;
  const current = buttons.findIndex((button) => button.classList.contains("active"));
  showHelpHit(current >= 0 && current < buttons.length - 1 ? current + 1 : 0);
});
$("#helpSearchResults")?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-hit]");
  if (!button) return;
  showHelpHit(Number(button.dataset.hit));
});
$("#aiProvider")?.addEventListener("change", () => syncAiProviderFields());
$("#settingsTabApi").addEventListener("click", () => showSettingsPane("api"));
$("#settingsTabLicense")?.addEventListener("click", () => showSettingsPane("license"));
$("#settingsTabMarkets").addEventListener("click", () => showSettingsPane("markets"));
$("#licenseActivate")?.addEventListener("click", () => activateLicenseKey());
$("#licenseClear")?.addEventListener("click", () => clearLicenseKey());
$("#licenseRefresh")?.addEventListener("click", () => refreshLicenseStatus());
document.querySelector("#settingsPaneApi")?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-setup-help]");
  if (!button) return;
  openSetupHelp(button.dataset.setupHelp);
});
$("#marketSetupHelp")?.addEventListener("click", () => {
  openSetupHelp($("#marketChannel")?.value || "smartstore");
});
$("#closeSetupHelp")?.addEventListener("click", () => $("#setupHelpDialog")?.close());
$("#setupHelpDialog")?.addEventListener("cancel", (event) => {
  event.preventDefault();
  $("#setupHelpDialog")?.close();
});
$("#setupHelpBody")?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-setup-target]");
  if (!button) return;
  goToSetupTarget(button.dataset.setupTarget);
});
$("#setupHelpForm")?.addEventListener("submit", (event) => event.preventDefault());
$("#deliveryTabShipping")?.addEventListener("click", () => showDeliveryMode("shipping"));
$("#deliveryTabPrice")?.addEventListener("click", () => showDeliveryMode("price"));
$("#addRequiredPriceSet").addEventListener("click", () => openPriceSetDialog("required"));
$("#addMarketPriceSet").addEventListener("click", () => openPriceSetDialog("market"));
$("#priceSetCancel").addEventListener("click", () => $("#priceSetDialog").close());
$("#priceSetDialog").addEventListener("click", (event) => {
  if (event.target === $("#priceSetDialog")) $("#priceSetDialog").close();
});
$("#priceSetForm").addEventListener("submit", (event) => {
  event.preventDefault();
  savePriceSetForm().catch((error) => {
    const message = $("#priceSetMessage");
    if (message) message.textContent = error.message;
    else toast(error.message, true);
  });
});
$("#requiredPriceBody").addEventListener("click", (event) => {
  onPriceSetAction(event, "required").catch((error) => toast(error.message, true));
});
$("#marketPriceBody").addEventListener("click", (event) => {
  onPriceSetAction(event, "market").catch((error) => toast(error.message, true));
});
$("#collectForm").addEventListener("submit", (event) => {
  event.preventDefault();
  collectNow(collectUrls()).catch((error) => toast(error.message, true));
});
function runProductSearch() {
  productQuery = $("#productSearch")?.value || "";
  productSearchField = $("#productSearchField")?.value || "all";
  updateProductSearchPlaceholder();
  refreshVisibleSelection();
}

$("#productGrid")?.tHead?.addEventListener("click", (event) => {
  const th = event.target.closest("th.sortable");
  if (!th || event.target.closest(".col-resizer")) return;
  const key = th.dataset.sort;
  if (!key) return;
  if (productSortKey === key) productSortDir = productSortDir === "asc" ? "desc" : "asc";
  else {
    productSortKey = key;
    productSortDir = key === "price" || key === "created" ? "desc" : "asc";
  }
  updateProductSortHeaders();
  renderSheets();
});
$("#productSearchField")?.addEventListener("change", () => {
  productSearchField = $("#productSearchField").value || "all";
  updateProductSearchPlaceholder();
  if (productQuery.trim()) refreshVisibleSelection();
});
$("#productSearchButton")?.addEventListener("click", () => runProductSearch());
$("#productSearch")?.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    runProductSearch();
    return;
  }
  if (event.key === "Escape") {
    $("#productSearch").value = "";
    productQuery = "";
    refreshVisibleSelection();
  }
});
$("#productWholesalerFilter").addEventListener("change", () => {
  productFilter = $("#productWholesalerFilter").value || "all";
  if (productFilter !== "all" && productFilter !== "url") currentWholesalerId = productFilter;
  refreshVisibleSelection();
});
$("#marketTree").addEventListener("click", (event) => {
  const toggle = event.target.closest("[data-toggle]");
  if (toggle) {
    event.preventDefault();
    event.stopPropagation();
    const name = toggle.dataset.toggle;
    if (name === "source") sourceExpanded = !sourceExpanded;
    else if (name) channelExpanded[name] = !isChannelExpanded(name);
    fillMarketTree();
    return;
  }
  const item = event.target.closest(".market-item");
  if (!item) return;
  if (item.classList.contains("disabled") || item.dataset.kind === "disabled") {
    toast("마켓관리에서 해당 마켓 계정을 먼저 등록하세요.");
    return;
  }
  if (item.dataset.kind === "empty") {
    pendingMarketChannel = item.dataset.channel || "smartstore";
    openMarketDialog();
    return;
  }
  if (item.dataset.kind === "master" || item.dataset.kind === "master-all") {
    marketFilter = "master";
    masterChannelFilter = "";
  } else if (item.dataset.kind === "master-channel") {
    marketFilter = "master";
    masterChannelFilter = item.dataset.channel || "";
  } else {
    masterChannelFilter = "";
    marketFilter = item.dataset.filter || "all";
    if (item.dataset.marketId) currentMarketId = item.dataset.marketId;
    if (accountChannels().some((row) => row.id === marketFilter)) {
      channelExpanded[marketFilter] = true;
      const first = marketsForChannel(marketFilter)[0];
      if (first) currentMarketId = first.id;
    }
  }
  if (item.dataset.kind === "channel" || item.dataset.kind === "store" || item.dataset.kind === "master-channel") {
    if (revealFilteredMarketProducts()) toast("이 마켓 상품이 보이도록 공급처를 전체로 바꿨습니다.");
  }
  if (marketFilter === "all") productStatusFilter = "all";
  fillMarketTree();
  refreshVisibleSelection();
});
$("#marketSidebarSettings").addEventListener("click", () => {
  openMarketDialog();
});
$("#productStatusFilters")?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-status-filter]");
  if (!button) return;
  const next = button.getAttribute("data-status-filter") || "all";
  productStatusFilter = next === productStatusFilter && next !== "all" ? "all" : next;
  refreshVisibleSelection();
});
$("#productRefreshOriginal")?.addEventListener("click", () => {
  refreshOriginalProducts().catch((error) => toast(error.message, true));
});
$("#productRefreshMarket")?.addEventListener("click", () => {
  refreshMarketProducts().catch((error) => toast(error.message, true));
});
function closeStockMenus() {
  document.querySelectorAll(".stock-menu-panel").forEach((panel) => { panel.hidden = true; });
}
document.querySelectorAll(".stock-menu").forEach((menu) => {
  const panel = menu.querySelector(".stock-menu-panel");
  menu.querySelector(".stock-menu-toggle").addEventListener("click", (event) => {
    event.stopPropagation();
    const open = panel.hidden;
    closeStockMenus();
    panel.hidden = !open;
  });
  panel.addEventListener("click", (event) => {
    const button = event.target.closest("[data-stock-mode]");
    if (!button) return;
    closeStockMenus();
    openStockDialog(button.dataset.stockMode).catch((error) => toast(error.message, true));
  });
});
document.addEventListener("click", (event) => {
  if (!event.target.closest(".stock-menu")) closeStockMenus();
});
$("#closeStock").addEventListener("click", () => closeStockDialog());
$("#stockDialog").addEventListener("cancel", (event) => {
  event.preventDefault();
  closeStockDialog();
});
$("#stockStop").addEventListener("click", () => {
  stopStockJob().catch((error) => toast(error.message, true));
});
$("#stockApplySoldout").addEventListener("click", () => {
  applyStockJob("soldout").catch((error) => toast(error.message, true));
});
$("#stockApplyResale").addEventListener("click", () => {
  applyStockJob("resale").catch((error) => toast(error.message, true));
});
$("#wholesaleGoCollect")?.addEventListener("click", () => {
  const id = selectedWholesalerId();
  showAppView("collect");
  if (id) selectCollectSupplier(id).catch((error) => toast(error.message, true));
});
$("#collectOpenWholesalers")?.addEventListener("click", () => showAppView("wholesalers"));
$("#collectEmptyOpenWholesalers")?.addEventListener("click", () => showAppView("wholesalers"));
$("#collectCafe24ImportNew")?.addEventListener("click", () => {
  importNewWholesaleProducts().catch((error) => toast(error.message, true));
});
$("#collectCafe24OpenProducts")?.addEventListener("click", () => {
  openWholesalerProducts();
});
$("#collectCafe24ReloadCats")?.addEventListener("click", () => {
  loadCafe24Categories({ force: true }).catch((error) => toast(error.message, true));
});
$("#collectCafe24SearchBtn")?.addEventListener("click", () => {
  cafe24CatalogPage = 1;
  renderCafe24Catalog();
});
$("#collectCafe24Search")?.addEventListener("keydown", (event) => {
  if (event.key !== "Enter") return;
  event.preventDefault();
  cafe24CatalogPage = 1;
  renderCafe24Catalog();
});
$("#collectCafe24HideSoldout")?.addEventListener("change", () => {
  cafe24CatalogPage = 1;
  saveCafe24Prefs();
  renderCafe24Catalog();
});
$("#collectCafe24OnlyNew")?.addEventListener("change", () => {
  cafe24CatalogPage = 1;
  saveCafe24Prefs();
  renderCafe24Catalog();
});
document.querySelectorAll("[data-cafe24-sort]").forEach((button) => {
  button.addEventListener("click", () => setCafe24CatalogSort(button.dataset.cafe24Sort));
});
$("#collectCafe24SelectAll")?.addEventListener("click", () => {
  const boxes = [...document.querySelectorAll("#collectCafe24List input[type='checkbox']")];
  if (!boxes.length) return;
  const on = boxes.some((box) => !box.checked);
  boxes.forEach((box) => {
    box.checked = on;
  });
  updateCafe24CatalogStatus();
});
$("#collectCafe24Send")?.addEventListener("click", () => {
  sendCafe24Selected().catch((error) => toast(error.message, true));
});
$("#collectCafe24Prev")?.addEventListener("click", () => {
  if (cafe24CatalogPage <= 1) return;
  cafe24CatalogPage -= 1;
  renderCafe24Catalog();
});
$("#collectCafe24Next")?.addEventListener("click", () => {
  const pages = cafe24CatalogPages();
  if (cafe24CatalogPage >= pages) return;
  cafe24CatalogPage += 1;
  renderCafe24Catalog();
});
$("#wholesaleNew").addEventListener("click", () => {
  currentWholesalerId = "";
  fillWholesaleForm({});
  renderWholesalerSheet();
});
$("#wholesaleSave").addEventListener("click", () => {
  saveWholesalerForm().catch((error) => toast(error.message, true));
});
$("#wholesaleForm").addEventListener("submit", (event) => {
  event.preventDefault();
  saveWholesalerForm().catch((error) => toast(error.message, true));
});
$("#wholesaleForm")?.elements?.type?.addEventListener("change", () => {
  const form = $("#wholesaleForm");
  if (form.elements.type.value !== "ownerclan") {
    syncWholesaleTypeFields();
    return;
  }
  const row = wholesalers.find((item) => item.type === "ownerclan");
  if (row) {
    fillWholesaleForm(row);
    renderWholesalerSheet();
  }
});
$("#wholesaleForm")?.elements?.url?.addEventListener("change", () => {
  guessWholesaleTypeFromUrl();
});
$("#wholesaleForm")?.elements?.url?.addEventListener("blur", () => {
  guessWholesaleTypeFromUrl();
});

function guessWholesaleTypeFromUrl() {
  const form = $("#wholesaleForm");
  if (!form || form.elements.type.value === "ownerclan") return;
  const url = String(form.elements.url?.value || "").toLowerCase();
  if (!url) return;
  if (url.includes("ownerclan.com")) return;
  if (url.includes("imweb")) form.elements.type.value = "imweb";
  else if (url.includes("godomall") || url.includes("godo.co.kr") || url.includes("godohosting") || url.includes("/goods/")) {
    form.elements.type.value = "godomall";
  } else if (url.includes("cafe24")) form.elements.type.value = "cafe24";
  syncWholesaleTypeFields();
}
$("#ownerclanSearchType")?.addEventListener("change", () => {
  const input = $("#ownerclanSearchKeyword");
  if (!input) return;
  const type = $("#ownerclanSearchType").value;
  input.placeholder = type === "selfcode" ? "상품코드" : type === "vendercode" ? "공급사코드" : type === "keyword" ? "상품명 또는 키워드" : "검색어";
});
$("#ownerclanSearchKeyword")?.addEventListener("keydown", (event) => {
  if (event.key !== "Enter") return;
  event.preventDefault();
  searchOwnerclanWithFilters().catch((error) => toast(error.message, true));
});
$("#ownerclanProductSearch")?.addEventListener("click", () => {
  searchOwnerclanWithFilters().catch((error) => toast(error.message, true));
});
$("#ownerclanPrev")?.addEventListener("click", () => {
  if (ownerclanPage <= 1) return;
  loadOwnerclanProducts({ ...ownerclanProductQuery, page: ownerclanPage - 1 }).catch((error) => toast(error.message, true));
});
$("#ownerclanNext")?.addEventListener("click", () => {
  if (ownerclanPage >= ownerclanPages) return;
  loadOwnerclanProducts({ ...ownerclanProductQuery, page: ownerclanPage + 1 }).catch((error) => toast(error.message, true));
});
$("#ownerclanOnlyNew")?.addEventListener("change", () => {
  try {
    localStorage.setItem("ownerclan-only-new", $("#ownerclanOnlyNew").checked ? "1" : "0");
  } catch (error) {
    /* ignore */
  }
  renderOwnerclanProducts();
});
$("#ownerclanSelectAll")?.addEventListener("click", () => {
  const boxes = [...document.querySelectorAll("#ownerclanProductList input[type='checkbox']")];
  const check = boxes.some((box) => !box.checked);
  boxes.forEach((box) => {
    box.checked = check;
  });
  updateOwnerclanProductStatus();
});
$("#ownerclanLowest")?.addEventListener("click", () => {
  importLowestOwnerclanProducts().catch((error) => toast(error.message, true));
});
$("#ownerclanSend")?.addEventListener("click", () => {
  sendOwnerclanToProducts().catch((error) => toast(error.message, true));
});
$("#ownerclanExcludedSave")?.addEventListener("click", () => {
  saveOwnerclanExcluded().catch((error) => toast(error.message, true));
});
$("#ownerclanFilterSearch")?.addEventListener("click", () => {
  searchOwnerclanWithFilters().catch((error) => toast(error.message, true));
});
$("#ownerclanFilterSave")?.addEventListener("change", () => {
  const box = $("#ownerclanFilterSave");
  const remember = Boolean(box?.checked);
  saveOwnerclanFilters(remember).catch((error) => {
    if (box) box.checked = !remember;
    toast(error.message, true);
  });
});
document.querySelector(".ownerclan-filters")?.addEventListener("click", (event) => {
  const rank = event.target.closest(".ownerclan-rank");
  if (!rank) return;
  document.querySelectorAll(".ownerclan-rank").forEach((button) => button.classList.toggle("active", button === rank));
  searchOwnerclanWithFilters().catch((error) => toast(error.message, true));
});
$("#wholesaleDelete").addEventListener("click", () => {
  deleteCurrentWholesaler().catch((error) => toast(error.message, true));
});
$("#wholesaleLogin").addEventListener("click", () => {
  loginWholesaler($("#wholesaleForm").elements.id.value).catch((error) => toast(error.message, true));
});
$("#loadOrdersButton")?.addEventListener("click", () => {
  importMarketOrders().catch((error) => toast(error.message, true));
});
$("#orderChannelFilter")?.addEventListener("change", () => {
  orderCollectChannel = $("#orderChannelFilter").value || "smartstore";
  orderCollectStore = "all";
  fillOrderCollectSelects();
});
$("#orderStoreFilter")?.addEventListener("change", () => {
  orderCollectStore = $("#orderStoreFilter").value || "all";
});
document.addEventListener("keydown", (event) => {
  if (event.key !== "F5" || $("#viewOrders")?.hidden) return;
  event.preventDefault();
  importMarketOrders().catch((error) => toast(error.message, true));
});
$("#confirmOrdersButton")?.addEventListener("click", () => {
  confirmSelectedOrders().catch((error) => toast(error.message, true));
});
$("#orderConfirmYes")?.addEventListener("click", () => $("#orderConfirmDialog")?.close("yes"));
$("#orderConfirmNo")?.addEventListener("click", () => $("#orderConfirmDialog")?.close("no"));
$("#orderPeriod")?.addEventListener("change", () => {
  const kind = $("#orderPeriod").value;
  if (kind === "custom") return;
  setOrderPeriod(kind);
});
$("#orderDateFrom")?.addEventListener("change", () => {
  if ($("#orderPeriod")) $("#orderPeriod").value = "custom";
  renderOrders();
});
$("#orderDateTo")?.addEventListener("change", () => {
  if ($("#orderPeriod")) $("#orderPeriod").value = "custom";
  renderOrders();
});
$("#orderDateBasis")?.addEventListener("change", () => {
  if ($("#orderDateBasis").value !== "dispatch") orderDateBasisMemory = $("#orderDateBasis").value || "paid";
  renderOrders();
});
$("#orderSearch")?.addEventListener("keydown", (event) => {
  if (event.key !== "Enter") return;
  orderQuery = $("#orderSearch").value || "";
  renderOrders();
});
$("#orderSearchButton")?.addEventListener("click", () => {
  orderQuery = $("#orderSearch")?.value || "";
  renderOrders();
});
$("#menuConfirmOrders")?.addEventListener("click", () => confirmSelectedOrders().catch((error) => toast(error.message, true)));
$("#menuReplace")?.addEventListener("click", () => openReplaceDialog());
$("#replaceClose")?.addEventListener("click", () => $("#replaceDialog")?.close());
$("#replaceSave")?.addEventListener("click", () => {
  saveReplaceSettings(currentReplaceSettings());
  $("#replaceDialog")?.close();
  renderOrders();
  toast("바꾸기설정을 저장했습니다.");
});
$("#replaceDelete")?.addEventListener("click", () => {
  const rules = readReplaceRules();
  rules.splice(replaceSelected, 1);
  renderReplaceRules(rules.filter((rule) => rule.find || rule.replace));
});
$("#replaceClear")?.addEventListener("click", () => {
  replaceSelected = 0;
  renderReplaceRules([]);
});
$("#replaceInsert")?.addEventListener("click", () => {
  const rules = readReplaceRules();
  rules.splice(replaceSelected + 1, 0, { find: "", replace: "", target: "상품명" });
  replaceSelected += 1;
  renderReplaceRules(rules);
});
$("#replaceUp")?.addEventListener("click", () => {
  const rules = readReplaceRules();
  if (replaceSelected <= 0) return;
  const [row] = rules.splice(replaceSelected, 1);
  replaceSelected -= 1;
  rules.splice(replaceSelected, 0, row);
  renderReplaceRules(rules);
});
$("#replaceDown")?.addEventListener("click", () => {
  const rules = readReplaceRules();
  if (replaceSelected >= rules.length - 1) return;
  const [row] = rules.splice(replaceSelected, 1);
  replaceSelected += 1;
  rules.splice(replaceSelected, 0, row);
  renderReplaceRules(rules);
});
$("#replaceExport")?.addEventListener("click", () => {
  const rules = currentReplaceSettings().rules;
  const lines = ["찾을 내용,바꿀 내용,적용대상", ...rules.map((rule) => [rule.find, rule.replace, rule.target].map(csvEscape).join(","))];
  const blob = new Blob(["\uFEFF" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "바꾸기설정.csv";
  link.click();
  URL.revokeObjectURL(link.href);
});
$("#replaceImport")?.addEventListener("click", () => $("#replaceFile")?.click());
$("#replaceFile")?.addEventListener("change", async (event) => {
  const file = event.target.files?.[0];
  event.target.value = "";
  if (!file) return;
  const text = await file.text();
  const rules = text.split(/\r?\n/).slice(1).map((line) => {
    const cells = [];
    let current = "";
    let quoted = false;
    for (let index = 0; index < line.length; index += 1) {
      const char = line[index];
      if (char === '"' && line[index + 1] === '"') {
        current += '"';
        index += 1;
      } else if (char === '"') quoted = !quoted;
      else if (char === "," && !quoted) {
        cells.push(current);
        current = "";
      } else current += char;
    }
    cells.push(current);
    return { find: cells[0] || "", replace: cells[1] || "", target: cells[2] || "상품명" };
  }).filter((rule) => rule.find);
  const existing = readReplaceRules().filter((rule) => rule.find);
  replaceSelected = 0;
  renderReplaceRules([...existing, ...rules]);
  toast(`${rules.length}개 규칙을 넣었습니다.`);
});
$("#menuExtra")?.addEventListener("click", (event) => {
  event.stopPropagation();
  toggleExtraMenu();
});
$("#orderExtraPanel")?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-extra]");
  if (!button) return;
  runExtraOrderAction(button.dataset.extra);
});
$("#menuColumns")?.addEventListener("click", () => openOrderColumnDialog());
$("#menuStats")?.addEventListener("click", () => openOrderStats());
$("#menuWorkStats")?.addEventListener("click", () => openWorkStats());
$("#menuPrint")?.addEventListener("click", () => printOrderSheet());
$("#menuExcelForm")?.addEventListener("click", () => setOrderTab("excel"));
$("#menuExcel")?.addEventListener("click", () => exportMenuOrders());
$("#menuHold")?.addEventListener("click", () => setOrderHold(true).catch((error) => toast(error.message, true)));
$("#menuRelease")?.addEventListener("click", () => setOrderHold(false).catch((error) => toast(error.message, true)));
$("#menuApplyWork")?.addEventListener("click", () => applyMenuWorkStatus().catch((error) => toast(error.message, true)));
$("#menuResetFilters")?.addEventListener("click", () => resetOrderMenuFilters());
["menuOrderPreset", "menuPlaceFilter", "menuWorkFilter", "menuLinkFilter", "menuRemoteFilter", "menuStoreFilter", "menuClaimFilter"].forEach((id) => {
  $(`#${id}`)?.addEventListener("change", () => renderOrders());
});
$("#orderColumnAll")?.addEventListener("click", () => $("#orderColumnList")?.querySelectorAll("input").forEach((input) => { input.checked = true; }));
$("#orderColumnSave")?.addEventListener("click", () => saveOrderColumnDialog());
$("#orderColumnClose")?.addEventListener("click", () => $("#orderColumnDialog")?.close());
$("#orderExcelAll")?.addEventListener("click", () => $("#orderExcelList")?.querySelectorAll("input").forEach((input) => { input.checked = true; }));
$("#orderExcelSave")?.addEventListener("click", () => saveOrderExcelDialog());
$("#orderExcelClose")?.addEventListener("click", () => $("#orderExcelDialog")?.close());
$("#orderStatsClose")?.addEventListener("click", () => $("#orderStatsDialog")?.close());
$("#orderWorkStatsSave")?.addEventListener("click", () => saveWorkStats());
$("#orderWorkStatsClose")?.addEventListener("click", () => $("#orderWorkStatsDialog")?.close());
document.addEventListener("click", () => {
  if ($("#orderExtraPanel")) $("#orderExtraPanel").hidden = true;
});
document.addEventListener("keydown", (event) => {
  if (event.ctrlKey || event.altKey || event.metaKey) return;
  if ($("#viewOrders")?.hidden || orderTab === "cs" || orderTab === "excel") return;
  if (event.target?.closest?.("input, textarea, select, [contenteditable='true'], #csMemoPanel")) return;
  if (document.querySelector("dialog[open]")) return;
  if ($("#csMemoPanel") && !$("#csMemoPanel").hidden) return;
  const key = event.key.toLowerCase();
  const actions = {
    n: () => confirmSelectedOrders(),
    d: () => setOrderHold(true),
    v: () => setOrderHold(false),
    b: () => resetOrderMenuFilters(),
    k: () => toggleExtraMenu(),
    t: () => openOrderColumnDialog(),
    r: () => openOrderStats(),
    g: () => openWorkStats(),
    p: () => printOrderSheet(),
    m: () => setOrderTab("excel"),
    e: () => exportMenuOrders(),
  };
  if (!actions[key]) return;
  event.preventDefault();
  Promise.resolve(actions[key]()).catch((error) => toast(error.message, true));
});
$("#placeWholesaleButton")?.addEventListener("click", () => {
  placeWholesaleOrders().catch((error) => toast(error.message, true));
});
$("#collectInvoiceButton")?.addEventListener("click", () => {
  collectOrderInvoices().catch((error) => toast(error.message, true));
});
$("#updateInvoiceButton")?.addEventListener("click", () => {
  updateSelectedInvoices().catch((error) => toast(error.message, true));
});
document.addEventListener("keydown", (event) => {
  if (event.key.toLowerCase() !== "s" || event.ctrlKey || event.altKey || event.metaKey) return;
  if ($("#viewOrders")?.hidden || orderTab !== "shipping") return;
  if (event.target?.closest?.("input, textarea, select, [contenteditable='true'], #csMemoPanel")) return;
  if (document.querySelector("dialog[open]")) return;
  if ($("#csMemoPanel") && !$("#csMemoPanel").hidden) return;
  event.preventDefault();
  updateSelectedInvoices().catch((error) => toast(error.message, true));
});
$("#dispatchInvoiceButton")?.addEventListener("click", () => {
  dispatchOrderInvoices().catch((error) => toast(error.message, true));
});
$("#orderStopJobButton")?.addEventListener("click", () => {
  const jobs = orderJobsFor(orderTab).filter((job) => !job.controller.signal.aborted);
  if (!jobs.length) {
    toast("이 탭에서 진행 중인 작업이 없습니다.");
    return;
  }
  jobs.forEach((job) => job.controller.abort());
  log("이 탭 작업을 중단합니다.");
  toast("작업을 중단합니다.");
});
$("#csMemoFilter")?.addEventListener("change", () => renderOrders());
$("#csMallFilter")?.addEventListener("change", () => renderOrders());
$("#csDateBasis")?.addEventListener("change", () => renderOrders());
$("#csPeriod")?.addEventListener("change", () => {
  const kind = $("#csPeriod").value;
  if (kind === "custom") return;
  applyPeriod(kind, "#csDateFrom", "#csDateTo", "#csPeriod");
  renderOrders();
});
$("#csDateFrom")?.addEventListener("change", () => {
  if ($("#csPeriod")) $("#csPeriod").value = "custom";
  renderOrders();
});
$("#csDateTo")?.addEventListener("change", () => {
  if ($("#csPeriod")) $("#csPeriod").value = "custom";
  renderOrders();
});
$("#csSearch")?.addEventListener("keydown", (event) => {
  if (event.key !== "Enter") return;
  event.preventDefault();
  csQuery = $("#csSearch").value || "";
  renderOrders();
});
$("#csSearchButton")?.addEventListener("click", () => {
  csQuery = $("#csSearch")?.value || "";
  renderOrders();
});
$("#csMarkOpenButton")?.addEventListener("click", () => {
  markFocusedCsOpen().catch((error) => toast(error.message, true));
});
$("#csDeleteRowsButton")?.addEventListener("click", () => {
  deleteFocusedCs().catch((error) => toast(error.message, true));
});
$("#csExcelButton")?.addEventListener("click", () => exportCsExcel());
$("#excelFormAdd")?.addEventListener("click", () => openExcelFormEditor(null));
$("#excelFormDelete")?.addEventListener("click", () => deleteSelectedExcelForms().catch((error) => toast(error.message, true)));
$("#excelFormRefresh")?.addEventListener("click", () => loadExcelForms().catch((error) => toast(error.message, true)));
$("#excelFormExport")?.addEventListener("click", () => exportSelectedExcelForms());
$("#excelFormImport")?.addEventListener("click", () => $("#excelFormFile")?.click());
$("#excelFormFile")?.addEventListener("change", () => {
  const file = $("#excelFormFile")?.files?.[0];
  if (!file) return;
  importExcelFormFile(file).catch((error) => toast(error.message, true));
  $("#excelFormFile").value = "";
});
$("#excelFormRestore")?.addEventListener("click", () => {
  api("/api/excel-forms/restore-sample", { method: "POST", body: "{}" })
    .then(() => loadExcelForms())
    .then(() => toast("샘플 양식을 복원했습니다."))
    .catch((error) => toast(error.message, true));
});
$("#excelValueSearch")?.addEventListener("input", () => filterExcelValueOptions());
$("#excelColumnAdd")?.addEventListener("click", () => {
  $("#excelColumnTable")?.appendChild(excelColumnRow({ title: "", code: "(빈칸)", memo: "" }));
  renumberExcelColumns();
});
$("#excelFormSave")?.addEventListener("click", () => saveExcelFormEditor().catch((error) => toast(error.message, true)));
$("#excelFormClose")?.addEventListener("click", () => $("#excelFormDialog")?.close());
$("#excelFormCancel")?.addEventListener("click", () => $("#excelFormDialog")?.close());
$("#excelRowUp")?.addEventListener("click", () => moveExcelRow(-1));
$("#excelRowDown")?.addEventListener("click", () => moveExcelRow(1));
$("#excelFormDialog")?.addEventListener("keydown", (event) => {
  if (event.ctrlKey || event.altKey || event.metaKey) return;
  if (event.target?.closest?.("input, textarea, select")) return;
  const key = event.key.toLowerCase();
  if (key === "s") {
    event.preventDefault();
    saveExcelFormEditor().catch((error) => toast(error.message, true));
  } else if (key === "c") {
    event.preventDefault();
    $("#excelFormDialog")?.close();
  }
});
$("#excelExportRun")?.addEventListener("click", () => runExcelExport().catch((error) => toast(error.message, true)));
$("#excelExportClose")?.addEventListener("click", () => $("#excelExportDialog")?.close());
$("#excelExportCancel")?.addEventListener("click", () => $("#excelExportDialog")?.close());
$("#excelExportHelp")?.addEventListener("click", () => {
  const note = $("#excelExportHelpText");
  if (note) note.hidden = !note.hidden;
});
$("#excelAutoSave")?.addEventListener("change", () => {
  localStorage.setItem("uploader-order-excel-autosave", $("#excelAutoSave").checked ? "1" : "0");
});
$("#excelExportMulti")?.addEventListener("change", () => refreshExcelExportPreview());
$("#excelExportSelect")?.addEventListener("change", () => refreshExcelExportPreview());
$("#excelExportFileName")?.addEventListener("input", () => {
  excelFileNameTouched = true;
});
$("#excelExportPath")?.addEventListener("click", () => chooseExcelSaveDir().catch((error) => toast(error.message, true)));
$("#excelExportOpenForms")?.addEventListener("click", () => {
  $("#excelExportDialog")?.close();
  setOrderTab("excel");
});
document.querySelectorAll("[data-excel-target]").forEach((button) => {
  button.addEventListener("click", () => {
    excelExportTarget = button.dataset.excelTarget || "all";
    refreshExcelExportPreview();
  });
});
$("#excelFormCheckAll")?.addEventListener("click", () => {
  const checked = $("#excelFormCheckAll").checked;
  excelForms.forEach((item) => {
    if (checked) selectedExcelFormIds.add(item.id);
    else selectedExcelFormIds.delete(item.id);
  });
  renderExcelForms();
});
document.addEventListener("keydown", (event) => {
  if (event.ctrlKey || event.altKey || event.metaKey) return;
  if ($("#viewOrders")?.hidden || orderTab !== "excel") return;
  if (event.target?.closest?.("input, textarea, select, [contenteditable='true']")) return;
  if (document.querySelector("dialog[open]")) return;
  const key = event.key.toLowerCase();
  if (key === "a") {
    event.preventDefault();
    openExcelFormEditor(null);
  } else if (key === "d") {
    event.preventDefault();
    deleteSelectedExcelForms().catch((error) => toast(error.message, true));
  } else if (key === "r") {
    event.preventDefault();
    loadExcelForms().catch((error) => toast(error.message, true));
  }
});
document.addEventListener("keydown", (event) => {
  if (event.ctrlKey || event.altKey || event.metaKey) return;
  if ($("#viewOrders")?.hidden || orderTab !== "cs") return;
  if (event.target?.closest?.("input, textarea, select, [contenteditable='true']")) return;
  if (document.querySelector("dialog[open]")) return;
  if ($("#csMemoPanel") && !$("#csMemoPanel").hidden) return;
  const key = event.key.toLowerCase();
  if (key === "s") {
    event.preventDefault();
    csQuery = $("#csSearch")?.value || "";
    renderOrders();
  } else if (key === "n") {
    event.preventDefault();
    markFocusedCsOpen().catch((error) => toast(error.message, true));
  } else if (key === "d") {
    event.preventDefault();
    deleteFocusedCs().catch((error) => toast(error.message, true));
  }
});
$("#csMemoSave")?.addEventListener("click", () => saveCsMemo().catch((error) => toast(error.message, true)));
$("#csMemoClose")?.addEventListener("click", () => closeCsMemo());
$("#csMemoDone")?.addEventListener("click", () => saveCsMemo("처리완료").catch((error) => toast(error.message, true)));
$("#csMemoOpen")?.addEventListener("click", () => saveCsMemo("미처리").catch((error) => toast(error.message, true)));
$("#csMemoReady")?.addEventListener("click", () => saveCsMemo("준비").catch((error) => toast(error.message, true)));
$("#csMemoDelete")?.addEventListener("click", () => {
  if ($("#csMemoText")) $("#csMemoText").value = "";
  saveCsMemo("").catch((error) => toast(error.message, true));
});
$("#csMemoPanel")?.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && event.target?.id === "csMemoText" && !event.shiftKey && !event.ctrlKey && !event.altKey && !event.metaKey) {
    event.preventDefault();
    saveCsMemo().catch((error) => toast(error.message, true));
    return;
  }
  if (event.target?.closest?.("textarea, input")) return;
  const key = event.key.toLowerCase();
  if (key === "s") {
    event.preventDefault();
    saveCsMemo().catch((error) => toast(error.message, true));
  } else if (key === "x" || key === "escape") {
    event.preventDefault();
    closeCsMemo();
  } else if (key === "c") {
    event.preventDefault();
    saveCsMemo("처리완료").catch((error) => toast(error.message, true));
  } else if (key === "n") {
    event.preventDefault();
    saveCsMemo("미처리").catch((error) => toast(error.message, true));
  } else if (key === "d") {
    event.preventDefault();
    if ($("#csMemoText")) $("#csMemoText").value = "";
    saveCsMemo("").catch((error) => toast(error.message, true));
  }
});
$("#orderWholesaler")?.addEventListener("change", () => {
  currentWholesalerId = $("#orderWholesaler").value;
});
$("#orderGrid")?.tHead?.addEventListener("click", (event) => {
  const th = event.target.closest("th.sortable");
  if (!th || event.target.closest(".col-resizer")) return;
  const key = th.dataset.sort;
  if (!key) return;
  if (orderSortKey === key) orderSortDir = orderSortDir === "asc" ? "desc" : "asc";
  else {
    orderSortKey = key;
    orderSortDir = key === "price" ? "desc" : "asc";
  }
  renderOrders();
});
$("#orderGrid")?.addEventListener("click", (event) => {
  if (event.target.id !== "orderCheckAll") return;
  const checked = event.target.checked;
  visibleOrders().forEach((item) => {
    if (checked) selectedOrderIds.add(item.id);
    else selectedOrderIds.delete(item.id);
  });
  renderOrders();
});
$("#orderStatusTabs")?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-order-tab]");
  if (!button) return;
  if (button.dataset.orderTab === "inquiries") {
    showAppView("inquiries");
    return;
  }
  setOrderTab(button.dataset.orderTab);
});
$("#loadInquiriesButton")?.addEventListener("click", () => {
  collectInquiries();
});
$("#resetInquiriesButton")?.addEventListener("click", () => resetInquiryFilters());
$("#inquiryExcelButton")?.addEventListener("click", () => exportInquiryExcel());
$("#inquiryStatusFilter")?.addEventListener("change", () => renderInquiryList());
$("#inquiryDateFrom")?.addEventListener("change", () => {
  if ($("#inquiryPeriod")) $("#inquiryPeriod").value = "custom";
  updateInquiryPeriodButtons();
  renderInquiryList();
});
$("#inquiryDateTo")?.addEventListener("change", () => {
  if ($("#inquiryPeriod")) $("#inquiryPeriod").value = "custom";
  updateInquiryPeriodButtons();
  renderInquiryList();
});
$("#inquiryPeriod")?.addEventListener("change", () => {
  const kind = $("#inquiryPeriod").value;
  if (kind === "custom") {
    updateInquiryPeriodButtons();
    return;
  }
  setInquiryPeriod(kind);
});
$("#inquiryQuickPeriods")?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-inquiry-period]");
  if (!button) return;
  setInquiryPeriod(button.dataset.inquiryPeriod);
});
$("#inquiryChannelFilter")?.addEventListener("change", () => setInquiryChannelFilter($("#inquiryChannelFilter").value));
$("#inquiryResultChannel")?.addEventListener("change", () => setInquiryChannelFilter($("#inquiryResultChannel").value));
$("#inquiryStoreFilter")?.addEventListener("change", () => setInquiryStoreFilter($("#inquiryStoreFilter").value));
$("#inquiryResultStore")?.addEventListener("change", () => setInquiryStoreFilter($("#inquiryResultStore").value));
$("#inquiryDetail")?.addEventListener("click", (event) => {
  const tab = event.target.closest("[data-inquiry-pane]");
  if (!tab) return;
  const name = tab.dataset.inquiryPane;
  document.querySelectorAll("[data-inquiry-pane]").forEach((button) => {
    button.classList.toggle("active", button === tab);
  });
  if ($("#inquiryPaneBasic")) $("#inquiryPaneBasic").hidden = name !== "basic";
  if ($("#inquiryPaneBatch")) $("#inquiryPaneBatch").hidden = name !== "batch";
  updateInquiryBatchCount();
});
$("#inquiryTemplate")?.addEventListener("change", () => applyInquiryTemplate());
$("#inquiryAnswerButton")?.addEventListener("click", () => {
  sendInquiryAnswer().catch((error) => toast(error.message, true));
});
$("#inquiryAnswerView")?.addEventListener("focus", () => {
  const draft = $("#inquiryAnswerDraft");
  if (draft && !draft.readOnly && !draft.disabled) draft.focus();
});
$("#inquiryAnswerView")?.addEventListener("mousedown", (event) => {
  event.preventDefault();
  const draft = $("#inquiryAnswerDraft");
  if (draft && !draft.readOnly && !draft.disabled) draft.focus();
});
["inquiryAnswerDraft", "inquiryAnswerTitle", "inquiryBatchBody", "inquiryBatchTitle"].forEach((id) => {
  $(`#${id}`)?.addEventListener("keydown", (event) => event.stopPropagation());
  $(`#${id}`)?.addEventListener("keypress", (event) => event.stopPropagation());
});
$("#inquiryCheckAll")?.addEventListener("click", (event) => {
  const checked = event.target.checked;
  filteredInquiries().forEach((item) => {
    if (checked) selectedInquiryIds.add(item.id);
    else selectedInquiryIds.delete(item.id);
  });
  renderInquiryList();
});
document.addEventListener("keydown", (event) => {
  if (event.key !== "F5") return;
  if ($("#viewInquiries")?.hidden) return;
  event.preventDefault();
  collectInquiries();
});
$("#orderMarketTree")?.addEventListener("click", (event) => {
  const toggle = event.target.closest("[data-toggle]");
  if (toggle) {
    event.preventDefault();
    event.stopPropagation();
    const name = toggle.dataset.toggle;
    if (name) orderChannelExpanded[name] = !isOrderChannelExpanded(name);
    fillOrderMarketTree();
    return;
  }
  const item = event.target.closest(".market-item");
  if (!item || item.dataset.kind === "empty") return;
  orderMarketFilter = item.dataset.filter || "all";
  if (item.dataset.kind === "store" && item.dataset.marketId) {
    const market = markets.find((row) => row.id === item.dataset.marketId);
    orderCollectChannel = marketChannel(market) || orderCollectChannel;
    orderCollectStore = item.dataset.marketId;
  } else if (item.dataset.kind === "channel") {
    orderCollectChannel = item.dataset.filter || orderCollectChannel;
    orderCollectStore = "all";
  } else if (item.dataset.kind === "all") {
    orderCollectChannel = "all";
    orderCollectStore = "all";
  }
  fillOrderMarketTree();
  renderOrders();
});
$("#saveButton").addEventListener("click", () => {
  saveSelected().catch((error) => toast(error.message, true));
});
$("#aiNameButton").addEventListener("click", () => {
  aiRewriteSelected("name").catch((error) => toast(error.message, true));
});
$("#aiTagButton").addEventListener("click", () => {
  aiRewriteSelected("tags").catch((error) => toast(error.message, true));
});
$("#aiAttrButton").addEventListener("click", () => {
  aiRewriteSelected("attributes").catch((error) => toast(error.message, true));
});
function productsMissingCategory(items) {
  return (items || []).filter((item) => item && !isMasterProduct(item) && !String(item.category_id || "").trim());
}

function guideCategoryBeforeAi(items) {
  const missing = productsMissingCategory(items);
  if (!missing.length) return false;
  const sample = missing[0]?.name || "상품";
  const message = missing.length === 1
    ? `"${sample}"에 카테고리가 없습니다. AI가공 전에 카테고리부터 지정해 주세요.`
    : `카테고리 없는 상품 ${missing.length}개가 있습니다. AI가공 전에 카테고리부터 지정해 주세요.`;
  toast(message, true);
  log(message, "err");
  openCategoryMapper(missing.map((item) => item.id));
  return true;
}

async function aiPolishSelected() {
  const items = requireSelected();
  if (!items.length) return;
  if (items.every(isMasterProduct)) return masterEditBlocked(items[0]);
  const targets = items.filter((item) => !isMasterProduct(item));
  if (!targets.length) return masterEditBlocked(items[0]);
  if (guideCategoryBeforeAi(targets)) return;
  setBusy(true, `AI 가공 중 (0/${targets.length}) · 상품명·태그·속성`);
  let count = 0;
  const errors = [];
  beginProductUndoGroup("AI가공");
  try {
    for (let index = 0; index < targets.length; index += 1) {
      throwIfCancelled();
      const item = targets[index];
      setBusy(true, `AI 가공 중 (${index + 1}/${targets.length}) · 상품명(검색어)·태그·속성`);
      try {
        rememberProductUndo(findProductState(item.id) || item);
        await saveCurrentRow(item.id);
        current = await api(`/api/products/${item.id}/ai`, {
          method: "POST",
          body: JSON.stringify({ instruction: $("#fieldInstruction")?.value || "" }),
        });
        count += 1;
        const warns = (current.warnings || []).filter((text) => /태그|속성|카테고리/.test(String(text || "")));
        warns.slice(-2).forEach((text) => log(`${item.name || "상품"}: ${text}`, "err"));
      } catch (error) {
        if (isAbortError(error)) throw error;
        errors.push(`${item.name || "상품"}: ${error.message}`);
      }
      if (index < targets.length - 1) await wait(900);
    }
    await loadProducts();
    if (current) await selectProduct(current.id, true, true);
    if (count) {
      const done = targets.length === 1
        ? "AI가공으로 상품명(검색어), 태그, 속성을 넣었습니다."
        : `${count}개 상품에 상품명(검색어), 태그, 속성을 넣었습니다.`;
      log(done, "ok");
      toast(done);
    }
    errors.forEach((text) => log(text, "err"));
    if (!count && errors.length) toast(errors[0], true);
  } catch (error) {
    if (isAbortError(error)) {
      if (count) log(`${count}개까지 처리한 뒤 작업을 중단했습니다.`);
      toast("작업을 중단했습니다.");
    } else {
      log(error.message, "err");
      toast(error.message, true);
    }
  } finally {
    if (count) endProductUndoGroup();
    else cancelProductUndoGroup();
    setBusy(false);
  }
}

$("#aiButton").addEventListener("click", () => {
  aiPolishSelected().catch((error) => toast(error.message, true));
});
$("#registerButton").addEventListener("click", () => {
  registerSelected().catch((error) => toast(error.message, true));
});
$("#stopJobButton").addEventListener("click", () => {
  stopCurrentJob();
});
$("#deleteButton").addEventListener("click", () => {
  deleteSelected().catch((error) => toast(error.message, true));
});
$("#changeNameButton")?.addEventListener("click", () => {
  openNameEditor();
});
$("#changeAttributeButton")?.addEventListener("click", () => {
  openAttributeEditor().catch((error) => toast(error.message, true));
});
$("#openOptionButton")?.addEventListener("click", () => {
  openOptionEditor();
});
$("#changeTagButton")?.addEventListener("click", () => {
  openTagEditor();
});
$("#changeImageButton")?.addEventListener("click", () => {
  openImageEditor().catch((error) => toast(error.message, true));
});
$("#changeDetailButton")?.addEventListener("click", () => {
  openDetailEditor();
});
$("#detailIntroButton")?.addEventListener("click", () => {
  aiRewriteSelected("detail-intro").catch((error) => toast(error.message, true));
});
$("#detailIntroAi")?.addEventListener("click", () => {
  fillDetailIntroInEditor().catch((error) => toast(error.message, true));
});
$("#undoProductButton")?.addEventListener("click", () => {
  undoProductChange().catch((error) => toast(error.message, true));
});
$("#redoProductButton")?.addEventListener("click", () => {
  redoProductChange().catch((error) => toast(error.message, true));
});
$("#changeCategoryButton")?.addEventListener("click", () => {
  openCategoryMapper();
});
$("#viewCollectedButton")?.addEventListener("click", () => {
  openCollectedProduct();
});
$("#viewRegisteredButton")?.addEventListener("click", () => {
  openRegisteredProduct();
});
$("#sendMarketButton").addEventListener("click", () => {
  openSendMarketDialog().catch((error) => toast(error.message, true));
});
$("#refreshOriginalButton")?.addEventListener("click", () => {
  refreshOriginalProducts().catch((error) => toast(error.message, true));
});
$("#refreshMarketButton")?.addEventListener("click", () => {
  refreshMarketProducts().catch((error) => toast(error.message, true));
});
$("#openNameKeywords")?.addEventListener("click", () => {
  openNameKeywordDialog().catch((error) => toast(error.message, true));
});
$("#closeSendMarket").addEventListener("click", () => $("#sendMarketDialog").close());
$("#sendMarketForm").addEventListener("submit", (event) => {
  event.preventDefault();
  sendSelectedToMarket($("#sendMarketSelect").value).catch((error) => toast(error.message, true));
});
document.addEventListener("contextmenu", onGridContextMenu, true);
$("#contextMenu").addEventListener("click", (event) => {
  const action = event.target.closest("[data-action]")?.dataset.action;
  if (action) runContextAction(action);
});
document.addEventListener("pointerdown", (event) => {
  if (event.target.closest("#contextMenu")) return;
  if (event.button === 2) return;
  hideContextMenu();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") hideContextMenu();
});
document.querySelectorAll(".grid-wrap").forEach((wrap) => {
  wrap.addEventListener("scroll", hideContextMenu);
});
$("#closeOption").addEventListener("click", () => $("#optionDialog").close());
$("#optionOn").addEventListener("click", () => setOptionEnabled(true));
$("#optionOff").addEventListener("click", () => setOptionEnabled(false));
$("#optionGroupCount").addEventListener("change", () => renderOptionNameRows(readOptionGroups()));
$("#applyOptionList").addEventListener("click", () => {
  const groups = readOptionGroups();
  if (!groups.length) return toast("옵션명과 옵션값을 입력해 주세요.", true);
  renderOptionCombos(buildOptionCombos(groups, current?.stock));
});
$("#selectAllCombos").addEventListener("change", (event) => {
  $("#optionComboTable").querySelectorAll("[data-combo-check]").forEach((box) => { box.checked = event.target.checked; });
});
$("#deleteSelectedCombos").addEventListener("click", () => {
  const rows = selectedComboRows();
  if (!rows.length) return toast("삭제할 옵션을 선택해 주세요.", true);
  rows.forEach((row) => row.remove());
});
$("#applyBulkOptions").addEventListener("click", () => {
  const rows = selectedComboRows();
  if (!rows.length) return toast("수정할 옵션을 선택해 주세요.", true);
  const sign = $("#bulkPriceSign").value;
  const price = $("#bulkPrice").value;
  const stock = $("#bulkStock").value;
  const usable = $("#bulkUsable").value;
  rows.forEach((row) => {
    row.querySelector("[data-combo-sign]").value = sign;
    row.querySelector("[data-combo-price]").value = price;
    row.querySelector("[data-combo-stock]").value = stock;
    row.querySelector("[data-combo-usable]").value = usable;
  });
});
$("#optionForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!current) return;
  try {
    if (!optionEnabled()) {
      await saveProduct(current, { options: [], option_combinations: [], option_type: "SIMPLE" });
    } else {
      const options = syncExtrasFromCombos(readOptionGroups(), readOptionCombos());
      const option_combinations = readOptionCombos();
      if (!options.length || !option_combinations.length) return toast("옵션목록으로 적용한 뒤 저장해 주세요.", true);
      await saveProduct(current, { options, option_combinations, option_type: optionTypeValue() });
    }
    await loadProducts();
    if (current) selectProduct(current.id);
    $("#optionDialog").close();
    toast("옵션을 저장했습니다.");
  } catch (error) {
    toast(error.message, true);
  }
});
$("#closeImage").addEventListener("click", () => $("#imageDialog").close());
$("#removeImageTextButton")?.addEventListener("click", async () => {
  if (!current) return toast("먼저 상품을 선택해 주세요.", true);
  if (masterEditBlocked()) return;
  const button = $("#removeImageTextButton");
  const status = $("#imageTextJobStatus");
  const name = current.name || "상품";
  const label = `대표이미지 글씨제거 중 · ${name}`;
  const previous = button?.textContent || "대표이미지 글씨제거";
  try {
    await saveDraftImages();
    if (button) {
      button.disabled = true;
      button.textContent = "글씨제거 중";
    }
    if (status) {
      status.hidden = false;
      status.textContent = "홍보 문구를 찾아 지우는 중입니다. 작업상태를 확인하세요.";
    }
    current = await api(`/api/products/${current.id}/images/remove-text`, {
      method: "POST",
      body: "{}",
      status: label,
    });
    const index = products.findIndex((item) => item.id === current.id);
    if (index >= 0) products[index] = current;
    draftImages = galleryImages(current).map((image) => ({ ...image }));
    renderImageEditor();
    fillPreview();
    if (status) status.textContent = "대표 이미지 글씨를 지웠습니다.";
    toast("대표 이미지 글씨를 지웠습니다.");
  } catch (error) {
    if (status) {
      status.hidden = false;
      status.textContent = error.message || "글씨를 지우지 못했습니다.";
    }
    toast(error.message, true);
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = previous;
    }
  }
});
$("#addImageButton").addEventListener("click", async () => {
  const url = $("#imageUrl").value.trim();
  if (url) {
    try {
      const added = await uploadProductImages([], url);
      $("#imageUrl").value = "";
      toast(added > 1 ? `${added}장 이미지를 추가했습니다.` : "이미지를 추가했습니다.");
    } catch (error) {
      toast(error.message, true);
    }
    return;
  }
  $("#imageFile").click();
});
$("#imageFile").addEventListener("change", async () => {
  const files = [...($("#imageFile").files || [])];
  $("#imageFile").value = "";
  if (!files.length) return;
  try {
    const added = await uploadProductImages(files, "");
    toast(added > 1 ? `${added}장 이미지를 추가했습니다.` : "이미지를 추가했습니다.");
  } catch (error) {
    toast(error.message, true);
  }
});
$("#imageForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!current) return;
  try {
    const detail = (current.images || []).filter((image) => image.kind !== "gallery");
    const images = [...draftImages.map((image) => ({ ...image, kind: "gallery", included: true })), ...detail];
    if (images.some((image) => image.kind === "gallery") && !images.some((image) => image.kind === "gallery" && image.representative)) {
      const first = images.find((image) => image.kind === "gallery");
      if (first) first.representative = true;
    }
    await saveProduct(current, { images });
    await loadProducts();
    if (current) selectProduct(current.id);
    $("#imageDialog").close();
    toast("이미지를 저장했습니다.");
  } catch (error) {
    toast(error.message, true);
  }
});
bindImageDrop($("#imageDrop"));
bindImageDrop($("#imageStrip"));
$("#closeName")?.addEventListener("click", () => $("#nameDialog")?.close());
document.querySelectorAll("[data-name-mode]").forEach((button) => button.addEventListener("click", async () => {
  if (!current || masterEditBlocked()) return;
  const buttons = document.querySelectorAll("[data-name-mode]");
  const label = button.textContent;
  buttons.forEach((item) => { item.disabled = true; });
  button.textContent = "만드는 중...";
  try {
    const result = await api(`/api/products/${current.id}/name/suggest`, {
      method: "POST",
      body: JSON.stringify({ mode: button.dataset.nameMode, instruction: $("#fieldInstruction")?.value || "" }),
    });
    $("#nameInput").value = result.name || "";
    const box = $("#nameSuggestKeywords");
    const words = result.keywords || [];
    box.hidden = !words.length;
    box.innerHTML = words.length
      ? `<strong>쓰인 월간검색어</strong> ${words.map((row) => `<span>${escapeAttr(row.keyword)} <em>${Number(row.monthly).toLocaleString()}</em></span>`).join("")}`
      : "";
    toast(`${label}으로 상품명을 만들었습니다. 확인 후 저장하세요.`);
  } catch (error) {
    toast(error.message, true);
  } finally {
    button.textContent = label;
    buttons.forEach((item) => { item.disabled = false; });
  }
}));
$("#nameForm")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const name = $("#nameInput")?.value.trim() || "";
  if (!name) return toast("상품명을 입력해 주세요.", true);
  if (!current || masterEditBlocked()) return;
  try {
    await saveProduct(current, { name });
    await loadProducts();
    if (products.some((item) => item.id === current?.id)) selectProduct(current.id);
    $("#nameDialog").close();
    toast("상품명을 바꿨습니다.");
  } catch (error) {
    toast(error.message, true);
  }
});
$("#closeTag").addEventListener("click", () => $("#tagDialog").close());
$("#tagSearchCheck").addEventListener("click", showSearchTagCheck);
$("#tagSearchResult").addEventListener("click", (event) => {
  const tag = event.target.closest("[data-search-tag]")?.dataset.searchTag;
  if (!tag) return;
  window.open(`https://search.shopping.naver.com/search/all?query=${encodeURIComponent(tag)}`, "_blank", "noopener");
});
$("#tagFillAi").addEventListener("click", async () => {
  if (!current) return toast("먼저 상품을 선택해 주세요.", true);
  try {
    current = await api(`/api/products/${current.id}/tags/ai`, {
      method: "POST",
      body: JSON.stringify({ instruction: $("#fieldInstruction")?.value || "" }),
    });
    const index = products.findIndex((item) => item.id === current.id);
    if (index >= 0) products[index] = current;
    draftTags = uniqueTags(current.tags || []);
    renderTagChips();
    toast("AI가 태그를 넣었습니다.");
  } catch (error) {
    toast(error.message, true);
  }
});
$("#tagDirect").addEventListener("change", syncTagEditor);
$("#tagInput").addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === "," || event.key === " ") {
    event.preventDefault();
    addDraftTag($("#tagInput").value);
  }
});
$("#tagInput").addEventListener("blur", () => addDraftTag($("#tagInput").value));
$("#tagForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!current) return;
  addDraftTag($("#tagInput").value);
  try {
    const tags = $("#tagDirect").checked ? uniqueTags(draftTags) : [];
    await saveProduct(current, { tags });
    await loadProducts();
    if (current) selectProduct(current.id);
    $("#tagDialog").close();
    toast("태그를 저장했습니다.");
  } catch (error) {
    toast(error.message, true);
  }
});
$("#closeDetail").addEventListener("click", () => $("#detailDialog").close());
document.querySelectorAll("[data-detail-mode]").forEach((button) => {
  button.addEventListener("click", () => setDetailMode(button.dataset.detailMode));
});
function focusDetailEditor() {
  $("#detailVisual").focus();
}

function applyDetailFontSize(pt) {
  focusDetailEditor();
  document.execCommand("fontSize", false, "7");
  $("#detailVisual").querySelectorAll('font[size="7"]').forEach((node) => {
    const span = document.createElement("span");
    span.style.fontSize = `${pt}pt`;
    span.innerHTML = node.innerHTML;
    node.replaceWith(span);
  });
  $("#detailFontSizeBtn").textContent = `${pt}pt`;
}

function closeDetailFontSizeMenu() {
  $("#detailFontSizeMenu").hidden = true;
}

$("#detailToolbar").addEventListener("click", (event) => {
  const button = event.target.closest("[data-cmd]");
  if (!button) return;
  focusDetailEditor();
  if (button.dataset.cmd === "quote") {
    document.execCommand("formatBlock", false, "blockquote");
    return;
  }
  document.execCommand(button.dataset.cmd, false);
});
$("#detailFontName").addEventListener("change", () => {
  focusDetailEditor();
  document.execCommand("fontName", false, $("#detailFontName").value);
});
$("#detailFontSizeWrap").addEventListener("mousedown", (event) => {
  event.preventDefault();
});
$("#detailFontSizeBtn").addEventListener("click", () => {
  $("#detailFontSizeMenu").hidden = !$("#detailFontSizeMenu").hidden;
});
$("#detailFontSizeMenu").addEventListener("click", (event) => {
  const button = event.target.closest("[data-pt]");
  if (!button) return;
  applyDetailFontSize(button.dataset.pt);
  closeDetailFontSizeMenu();
});
document.addEventListener("click", (event) => {
  if (!$("#detailFontSizeWrap").contains(event.target)) closeDetailFontSizeMenu();
});
$("#detailForeColor").addEventListener("input", () => {
  focusDetailEditor();
  document.execCommand("foreColor", false, $("#detailForeColor").value);
});
$("#detailBackColor").addEventListener("input", () => {
  focusDetailEditor();
  document.execCommand("hiliteColor", false, $("#detailBackColor").value);
});
$("#detailAlign").addEventListener("change", () => {
  focusDetailEditor();
  document.execCommand($("#detailAlign").value, false);
});
$("#detailSpecial").addEventListener("change", () => {
  const mark = $("#detailSpecial").value;
  $("#detailSpecial").value = "";
  if (!mark) return;
  focusDetailEditor();
  document.execCommand("insertText", false, mark);
});
$("#detailLink").addEventListener("click", () => {
  const href = prompt("링크 주소를 입력하세요", "https://");
  if (!href) return;
  focusDetailEditor();
  document.execCommand("createLink", false, href);
});
$("#detailFind").addEventListener("click", () => {
  const query = prompt("찾을 내용을 입력하세요");
  if (!query) return;
  focusDetailEditor();
  if (!window.find(query)) toast("찾는 내용이 없습니다.", true);
});
$("#addDetailImage").addEventListener("click", () => addDetailImages());
$("#detailImageFile").addEventListener("change", () => {
  if ($("#detailImageFile").files?.length) addDetailImages();
});
$("#detailForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!current) return;
  try {
    await saveProduct(current, { detail_html: readDetailHtml() });
    $("#detailDialog").close();
    toast("상세설명을 저장했습니다.");
  } catch (error) {
    toast(error.message, true);
  }
});
$("#closeCategory").addEventListener("click", () => $("#categoryDialog").close());
$("#closeAttribute").addEventListener("click", () => $("#attributeDialog").close());
$("#attributeFillCollected").addEventListener("click", fillAttributeCollected);
$("#attributeFillAi").addEventListener("click", () => {
  fillAttributeAi().catch((error) => toast(error.message, true));
});
$("#attributeForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!current) return;
  try {
    const payload = readAttributeForm();
    await saveProduct(current, {
      attributes: payload.attributes,
      naver_attributes: payload.naver_attributes,
    });
    await loadProducts();
    if (current) selectProduct(current.id);
    $("#attributeDialog").close();
    toast("속성을 저장했습니다.");
  } catch (error) {
    toast(error.message, true);
  }
});
$("#categoryQuery").addEventListener("input", () => {
  clearTimeout(searchCategoryList.timer);
  searchCategoryList.timer = setTimeout(searchCategoryList, 250);
});
$("#categoryForm").addEventListener("submit", (event) => {
  event.preventDefault();
  searchCategoryList();
});
$("#selectAllProducts").addEventListener("click", (event) => {
  selectAllProducts(event.target.checked);
});
$("#selectAllOptions").addEventListener("click", (event) => {
  selectAllProducts(event.target.checked);
});
let storeNotices = { items: [], default_ids: [] };
let draftNameKeywords = [];
let deliveryTemplates = [];
let currentDeliveryId = "";
let deliveryAddresses = [];
let deliveryBundleGroups = [];
const QUICK_REGIONS = ["서울", "경기", "인천", "부산", "대구", "광주", "대전", "울산", "세종", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"];

function uniqueNameKeywords(items) {
  const seen = [];
  for (const raw of items || []) {
    const word = String(raw || "").replace(/\s+/g, " ").trim().slice(0, 30);
    if (word.length >= 2 && !seen.includes(word)) seen.push(word);
    if (seen.length >= 500) break;
  }
  seen.sort((a, b) => a.localeCompare(b, "ko", { numeric: true, sensitivity: "base" }));
  return seen;
}

function keywordFolder(word) {
  const ch = String(word || "").trim().charAt(0);
  const code = ch.charCodeAt(0);
  if (code >= 0xac00 && code <= 0xd7a3) {
    const initials = ["ㄱ", "ㄲ", "ㄴ", "ㄷ", "ㄸ", "ㄹ", "ㅁ", "ㅂ", "ㅃ", "ㅅ", "ㅆ", "ㅇ", "ㅈ", "ㅉ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"];
    return initials[Math.floor((code - 0xac00) / 588)];
  }
  return "기타";
}

function renderNameKeywords(focusWord = "") {
  const box = $("#nameKeywordList");
  if (!box) return;
  box.innerHTML = "";
  if (!draftNameKeywords.length) {
    box.textContent = "";
    return;
  }
  let folder = "";
  let focusChip = null;
  draftNameKeywords.forEach((word, index) => {
    const group = keywordFolder(word);
    if (group !== folder) {
      const head = document.createElement("div");
      head.className = "name-keyword-folder";
      head.textContent = group;
      box.appendChild(head);
      folder = group;
    }
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "tag-chip";
    chip.textContent = word;
    const close = document.createElement("span");
    close.textContent = "×";
    chip.append(" ", close);
    chip.addEventListener("click", () => {
      draftNameKeywords.splice(index, 1);
      renderNameKeywords();
    });
    box.appendChild(chip);
    if (focusWord && word === focusWord) focusChip = chip;
  });
  if (focusChip) focusChip.scrollIntoView({ block: "nearest" });
}

function addNameKeyword(raw) {
  const added = uniqueNameKeywords(String(raw || "").split(/[,#\s]+/).filter(Boolean));
  const fresh = [];
  const duplicated = [];
  for (const word of added) {
    if (draftNameKeywords.includes(word)) duplicated.push(word);
    else {
      draftNameKeywords.push(word);
      fresh.push(word);
    }
  }
  draftNameKeywords = uniqueNameKeywords(draftNameKeywords);
  if ($("#nameKeywordInput")) $("#nameKeywordInput").value = "";
  renderNameKeywords(fresh[0] || "");
  const message = $("#nameKeywordMessage");
  if (message) {
    message.textContent = fresh.length ? "" : (duplicated.length ? "이미 들어 있는 키워드입니다." : "");
  }
}

function commitNameKeywordInput() {
  const input = $("#nameKeywordInput");
  if (!input || !String(input.value || "").trim()) return;
  addNameKeyword(input.value);
  input.focus();
}

async function openNameKeywordDialog() {
  const dialog = $("#nameKeywordDialog");
  if (!dialog) throw new Error("등록금지키워드 창을 찾지 못했습니다.");
  if ($("#nameKeywordInput")) $("#nameKeywordInput").value = "";
  if ($("#nameKeywordMessage")) $("#nameKeywordMessage").textContent = "";
  renderNameKeywords();
  if (!dialog.open) dialog.showModal();
  $("#nameKeywordInput")?.focus();
  try {
    const data = await api("/api/name-keywords");
    draftNameKeywords = uniqueNameKeywords(data.keywords || []);
    renderNameKeywords();
  } catch (error) {
    if ($("#nameKeywordMessage")) $("#nameKeywordMessage").textContent = error.message;
  }
}

async function saveNameKeywords() {
  addNameKeyword($("#nameKeywordInput")?.value || "");
  const saved = await api("/api/name-keywords", {
    method: "PUT",
    body: JSON.stringify({ keywords: draftNameKeywords }),
  });
  draftNameKeywords = uniqueNameKeywords(saved.keywords || []);
  renderNameKeywords();
  $("#nameKeywordMessage").textContent = "";
  toast("등록금지키워드를 저장했습니다.");
}

function noticeThumb(url) {
  const src = String(url || "");
  if (src.startsWith("/media/")) return src;
  return `/api/image-proxy?url=${encodeURIComponent(src)}`;
}

function selectedNoticeIds() {
  return [...$("#noticeList").querySelectorAll("[data-notice-id]:checked")].map((box) => box.value);
}

function renderNoticeList() {
  const box = $("#noticeList");
  box.innerHTML = "";
  const items = storeNotices.items || [];
  const checked = new Set();
  const selected = selectedProducts();
  if (selected.length === 1 && Array.isArray(selected[0].notice_ids)) {
    selected[0].notice_ids.forEach((id) => checked.add(String(id)));
  } else {
    (storeNotices.default_ids || []).forEach((id) => checked.add(String(id)));
  }
  if (!items.length) {
    box.innerHTML = "<p class='hint'>가져온 공지사항이 없습니다. 스마트스토어에서 가져오기를 누르세요.</p>";
    return;
  }
  items.forEach((item) => {
    const label = document.createElement("label");
    label.className = "notice-item";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.dataset.noticeId = item.id;
    input.value = item.id;
    input.checked = checked.has(String(item.id));
    const img = document.createElement("img");
    const src = (item.image_urls || [])[0] || "";
    img.alt = item.name || "공지사항";
    if (src) img.src = noticeThumb(src);
    else img.hidden = true;
    const text = document.createElement("span");
    text.textContent = item.name || "공지사항";
    label.append(input, img, text);
    box.appendChild(label);
  });
}

async function loadStoreNotices() {
  storeNotices = await api("/api/notices");
  renderNoticeList();
  return storeNotices;
}

async function openNoticeDialog() {
  if (current && masterEditBlocked()) return;
  await loadStoreNotices();
  $("#noticeMessage").textContent = selectedProducts().length
    ? `선택한 ${selectedProducts().length}개 상품 상세 상단에 넣을 공지를 고르세요.`
    : "공지를 가져온 뒤 상품을 선택하고 상단에 넣으세요.";
  $("#noticeDialog").showModal();
}

async function importStoreNotices() {
  $("#noticeMessage").textContent = "판매자센터 공지사항관리에서 가져오는 중입니다. Chrome에서 로그인되어 있어야 합니다.";
  try {
    storeNotices = await api("/api/notices/import", { method: "POST" });
  } catch (error) {
    await loadStoreNotices();
    $("#noticeMessage").textContent = error.message;
    throw error;
  }
  renderNoticeList();
  const count = (storeNotices.items || []).length;
  $("#noticeMessage").textContent = count ? `공지사항 ${count}개를 가져왔습니다. 상품 상세 상단에만 들어갑니다.` : "가져온 공지사항이 없습니다.";
  log(`스마트스토어 공지사항 ${count}개를 가져왔습니다.`, "ok");
  toast(count ? `공지사항 ${count}개를 가져왔습니다.` : "가져온 공지사항이 없습니다.");
}

async function applySelectedNotices() {
  const items = requireSelected().filter((item) => !isMasterProduct(item));
  if (!items.length) return masterEditBlocked();
  const noticeIds = selectedNoticeIds();
  const result = await api("/api/notices/apply", {
    method: "POST",
    body: JSON.stringify({ product_ids: items.map((item) => item.id), notice_ids: noticeIds }),
  });
  await loadProducts();
  $("#noticeMessage").textContent = `${result.count}개 상품 상세 상단에 공지 ${noticeIds.length}개를 넣었습니다.`;
  log(`${result.count}개 상품 상단에 공지를 넣었습니다.`, "ok");
  toast(`${result.count}개 상품 상단에 공지를 넣었습니다.`);
}

function noticeTextHtml() {
  const editor = $("#noticeText");
  if (!editor) return "";
  const text = (editor.innerText || editor.textContent || "").replace(/\u00a0/g, " ").trim();
  if (!text) return "";
  return (editor.innerHTML || "").trim();
}

function noticeExec(command, value) {
  const editor = $("#noticeText");
  if (!editor) return;
  editor.focus();
  document.execCommand(command, false, value);
}

function openNoticeCreateDialog() {
  $("#noticeTitle").value = "";
  $("#noticeImageUrl").value = "";
  $("#noticeImageFile").value = "";
  $("#noticeCategory").value = "일반";
  $("#noticeText").innerHTML = "";
  $("#noticeCreateMessage").textContent = "제목과 이미지 또는 텍스트를 넣고 저장하세요.";
  $("#noticeCreateDialog").showModal();
}

async function saveCreatedNotice() {
  const name = ($("#noticeTitle").value || "").trim();
  if (!name) {
    $("#noticeCreateMessage").textContent = "제목을 입력해 주세요.";
    return toast("제목을 입력해 주세요.", true);
  }
  const files = [...($("#noticeImageFile").files || [])].filter(isImageFile);
  const urls = String($("#noticeImageUrl").value || "").split(/[\s,]+/).map((item) => item.trim()).filter(Boolean);
  const html = noticeTextHtml();
  if (!files.length && !urls.length && !html) {
    $("#noticeCreateMessage").textContent = "공지 이미지나 내용을 넣어 주세요.";
    return toast("공지 이미지나 내용을 넣어 주세요.", true);
  }
  $("#noticeCreateMessage").textContent = "공지를 저장하는 중입니다.";
  const form = new FormData();
  form.append("name", name);
  form.append("category", $("#noticeCategory").value || "일반");
  if (html) form.append("html", html);
  files.forEach((file) => form.append("files", file, file.name || "image.jpg"));
  urls.forEach((item) => form.append("url", item));
  const response = await fetch("/api/notices", { method: "POST", body: form });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "공지를 저장하지 못했습니다.");
  storeNotices = data;
  renderNoticeList();
  $("#noticeCreateDialog").close();
  $("#noticeMessage").textContent = `공지 '${name}'을 만들었습니다. 상품을 선택하고 상단에 넣으세요.`;
  log(`공지 ${name}을 만들었습니다.`, "ok");
  toast("공지를 만들었습니다.");
}

async function saveNoticeDefaults() {
  storeNotices = await api("/api/notices/defaults", {
    method: "POST",
    body: JSON.stringify({ notice_ids: selectedNoticeIds() }),
  });
  renderNoticeList();
  $("#noticeMessage").textContent = "앞으로 새로 가져오는 상품에 이 공지가 상단 기본값으로 들어갑니다.";
  toast("새 상품 기본 공지를 저장했습니다.");
}

function fillMarketChannelSelect(selected) {
  const select = $("#marketChannel");
  if (!select) return;
  const currentValue = selected || select.value || "smartstore";
  select.innerHTML = "";
  accountChannels().forEach((item) => {
    const option = document.createElement("option");
    option.value = item.id;
    option.textContent = item.name;
    select.appendChild(option);
  });
  if ([...select.options].some((item) => item.value === currentValue)) select.value = currentValue;
  else select.value = "smartstore";
}

function marketApiConfig(channelId) {
  const configs = {
    smartstore: {
      url: true,
      apiKey: "애플리케이션 ID",
      apiSecret: "애플리케이션 시크릿",
      accountId: true,
    },
    coupang: {
      apiKey: "아이디키 (Access Key)",
      apiSecret: "시크릿키 (Secret Key)",
      vendor: "업체코드 (vendorId)",
    },
    auction: {
      esm: true,
    },
    gmarket: {
      esm: true,
    },
    "11st": {
      apiKey: "아이디키 (OPEN API KEY)",
    },
    toss: {
      apiKey: "Access Key",
      apiSecret: "Secret Key",
    },
    lotteon: {
      apiKey: "인증키",
      apiSecret: "시크릿키",
      vendor: "거래처번호 (trNo)",
    },
    kakao: {
      apiKey: "Admin/API Key",
      apiSecret: "판매자 Key",
    },
    ssg: {
      apiKey: "인증키",
      apiSecret: "시크릿키",
    },
    temu: {},
  };
  return configs[channelId] || configs.smartstore;
}

function syncMarketFormFields() {
  const channel = channelById($("#marketChannel")?.value || "smartstore");
  const config = marketApiConfig(channel.id);
  const setHidden = (id, hidden) => { const el = $(id); if (el) el.hidden = hidden; };
  setHidden("#marketUrlRow", !config.url);
  setHidden("#marketEsmRow", !config.esm);
  setHidden("#marketApiKeyRow", !config.apiKey);
  setHidden("#marketApiSecretRow", !config.apiSecret);
  setHidden("#marketVendorRow", !config.vendor);
  setHidden("#marketApiAccountRow", !config.accountId);
  if ($("#marketApiKeyLabel")) $("#marketApiKeyLabel").textContent = config.apiKey || "아이디키";
  if ($("#marketApiSecretLabel")) $("#marketApiSecretLabel").textContent = config.apiSecret || "시크릿키";
  if ($("#marketVendorLabel")) $("#marketVendorLabel").textContent = config.vendor || "업체코드";
  const vendorInput = $("#marketForm")?.elements?.vendor_code;
  if (vendorInput) vendorInput.placeholder = "";
  if ($("#marketApiHint")) {
    $("#marketApiHint").textContent = "";
    $("#marketApiHint").hidden = true;
  }
  const urlInput = $("#marketForm")?.elements?.url;
  if (urlInput) urlInput.placeholder = "";
}

function fillMarketTable() {
  const body = $("#marketTableBody");
  if (!body) return;
  body.innerHTML = "";
  markets.forEach((item) => {
    const row = document.createElement("tr");
    if (!marketFormIsNew && item.id === currentMarketId) row.classList.add("active");
    row.append(
      textCell(item.channel_name || channelById(marketChannel(item)).name),
      textCell(item.name || ""),
      textCell(item.login_id || ""),
      textCell(item.login_password_set ? "********" : ""),
      textCell(item.api_key_set || item.api_key || item.naver_client_id ? "********" : ""),
      textCell(item.api_secret_set || item.naver_client_secret_set ? "********" : ""),
      textCell(item.vendor_code || ""),
      textCell(item.esm_id || ""),
    );
    row.addEventListener("click", () => {
      currentMarketId = item.id;
      fillMarketForm(item);
      fillMarketTable();
    });
    body.appendChild(row);
  });
}

function fillMarketForm(item) {
  const form = $("#marketForm");
  const row = item || {};
  fillingMarketForm = true;
  fillMarketChannelSelect(row.channel || pendingMarketChannel || $("#marketChannel")?.value || "smartstore");
  form.elements.id.value = row.id || "";
  form.elements.name.value = row.name || "";
  form.elements.url.value = row.url || "";
  form.elements.login_id.value = row.login_id || "";
  form.elements.login_password.value = row.login_password_set ? "********" : "";
  form.elements.login_password.placeholder = "";
  if (form.elements.esm_id) form.elements.esm_id.value = row.esm_id || "";
  if (form.elements.api_key) form.elements.api_key.value = (row.api_key_set || row.api_key || row.naver_client_id) ? "********" : "";
  if (form.elements.api_secret) {
    form.elements.api_secret.value = (row.api_secret_set || row.naver_client_secret_set) ? "********" : "";
    form.elements.api_secret.placeholder = "";
  }
  if (form.elements.vendor_code) form.elements.vendor_code.value = row.vendor_code || "";
  if (form.elements.naver_account_id) form.elements.naver_account_id.value = row.naver_account_id || "";
  form.elements.is_default.checked = Boolean(row.is_default);
  currentMarketId = row.id || "";
  marketFormIsNew = !row.id;
  pendingMarketChannel = "";
  syncMarketFormFields();
  fillMarketTable();
  fillingMarketForm = false;
}

async function loadMarkets() {
  markets = await api("/api/markets");
  if (!marketFormIsNew && !currentMarketId) {
    const chosen = markets.find((item) => item.is_default) || markets[0];
    if (chosen) currentMarketId = chosen.id;
  }
  fillMarketFilter();
  fillSendMarketSelect();
  fillMarketTable();
  fillInquiryMallSelects();
  if (setupChannel) {
    fillMarketForm({ channel: setupChannel });
  } else if (!marketFormIsNew) {
    const currentItem = markets.find((item) => item.id === currentMarketId);
    if (currentItem) fillMarketForm(currentItem);
  }
  return markets;
}

async function openMarketDialog() {
  showAppView("settings");
  showSettingsPane("markets");
}

async function saveMarketForm() {
  const form = $("#marketForm");
  const wasNew = !form.elements.id.value;
  const payload = {
    id: form.elements.id.value || undefined,
    channel: form.elements.channel.value || "smartstore",
    name: form.elements.name.value,
    url: form.elements.url.value,
    login_id: form.elements.login_id.value,
    login_password: form.elements.login_password.value,
    esm_id: form.elements.esm_id?.value || "",
    api_key: form.elements.api_key?.value || "",
    api_secret: form.elements.api_secret?.value || "",
    vendor_code: form.elements.vendor_code?.value || "",
    naver_client_id: form.elements.api_key?.value || "",
    naver_client_secret: form.elements.api_secret?.value || "",
    naver_account_id: form.elements.naver_account_id?.value || "",
    is_default: form.elements.is_default.checked,
  };
  const channel = channelById(payload.channel);
  if (!payload.name) throw new Error("스토어명을 넣어 주세요.");
  if (channel.needsUrl && !payload.url) throw new Error("스토어 주소를 넣어 주세요.");
  const saved = payload.id
    ? await api(`/api/markets/${payload.id}`, { method: "PUT", body: JSON.stringify(payload) })
    : await api("/api/markets", { method: "POST", body: JSON.stringify(payload) });
  currentMarketId = saved.id;
  marketFormIsNew = wasNew;
  await loadMarkets();
  if (wasNew) {
    fillMarketForm({});
    $("#marketMessage").textContent = "";
    toast(`${saved.name}을 추가했습니다.`);
  } else {
    fillMarketForm(saved);
    $("#marketMessage").textContent = "";
    toast("마켓을 저장했습니다.");
  }
}

async function testMarketConnection() {
  const form = $("#marketForm");
  if (!form?.elements?.id?.value) {
    await saveMarketForm();
  }
  const id = $("#marketForm")?.elements?.id?.value || currentMarketId;
  if (!id) throw new Error("마켓을 먼저 저장해 주세요.");
  setBusy(true, "마켓 연동을 테스트하는 중입니다.", "settings");
  try {
    const result = await api(`/api/markets/${id}/test`, { method: "POST", body: "{}" });
    $("#marketMessage").textContent = result.message || "연동 테스트를 마쳤습니다.";
    log(result.message || "연동 테스트를 마쳤습니다.", "ok");
  } catch (error) {
    $("#marketMessage").textContent = error.message;
    log(error.message, "err");
    throw error;
  } finally {
    setBusy(false, "", "settings");
  }
}

async function deleteCurrentMarket() {
  if (!currentMarketId) return toast("삭제할 마켓을 선택해 주세요.", true);
  markets = await api(`/api/markets/${currentMarketId}`, { method: "DELETE" });
  currentMarketId = (markets.find((item) => item.is_default) || markets[0] || {}).id || "";
  fillMarketFilter();
  fillMarketTable();
  fillMarketForm(markets.find((item) => item.id === currentMarketId) || {});
  $("#marketMessage").textContent = "마켓을 삭제했습니다.";
}

function fillSendMarketSelect() {
  const select = $("#sendMarketSelect");
  if (!select) return;
  const currentValue = select.value || currentMarketId;
  select.innerHTML = "";
  let hasAccount = false;
  accountChannels().forEach((channel) => {
    const rows = marketsForChannel(channel.id);
    const group = document.createElement("optgroup");
    group.label = channel.name;
    if (!rows.length) {
      const option = document.createElement("option");
      option.value = "";
      option.disabled = true;
      option.textContent = "등록된 계정이 없습니다";
      group.appendChild(option);
    } else {
      hasAccount = true;
      rows.forEach((item) => {
        const option = document.createElement("option");
        option.value = item.id;
        option.textContent = item.name || item.slug || item.url || item.login_id || item.id;
        group.appendChild(option);
      });
    }
    select.appendChild(group);
  });
  if (!hasAccount) {
    select.innerHTML = "";
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "설정에서 마켓을 먼저 등록하세요";
    select.appendChild(option);
    return;
  }
  if (currentValue && [...select.options].some((item) => item.value === currentValue && !item.disabled)) select.value = currentValue;
}

async function openSendMarketDialog() {
  const items = requireSelected();
  if (!items.length) return;
  if (!markets.length) {
    toast("설정에서 마켓을 먼저 등록하세요.", true);
    openMarketDialog();
    return;
  }
  fillSendMarketSelect();
  $("#sendMarketMessage").textContent = `선택한 ${items.length}개 상품을 마켓으로 복사합니다.`;
  $("#sendMarketDialog").showModal();
}

async function sendSelectedToMarket(marketId) {
  const items = requireSelected();
  if (!items.length) return;
  const targetId = marketId || $("#sendMarketSelect")?.value || currentMarketId;
  if (!targetId) throw new Error("보낼 마켓을 선택해 주세요.");
  const result = await api("/api/markets/apply", {
    method: "POST",
    body: JSON.stringify({ product_ids: items.map((item) => item.id), market_id: targetId }),
  });
  currentMarketId = result.market?.id || targetId;
  marketFilter = currentMarketId;
  sourceExpanded = true;
  channelExpanded[marketChannel(result.market || {})] = true;
  await loadProducts();
  const opened = revealFilteredMarketProducts();
  fillMarketTree();
  refreshVisibleSelection();
  fillSendMarketSelect();
  const market = result.market || {};
  const channel = market.channel_name || channelById(marketChannel(market)).name;
  const store = market.name || channel;
  const name = store === channel ? channel : `${channel} ${store}`;
  const skipped = result.skipped ? `, 이미 있는 ${result.skipped}개는 건너뛰었습니다` : "";
  const categorized = Number(result.categorized || 0);
  const categoryNote = categorized
    ? ` 카테고리 ${categorized}개를 자동으로 넣었습니다.`
    : "";
  const openedNote = opened ? " 공급처는 전체로 맞춰 두었습니다." : "";
  const message = `${result.count}개 상품을 ${name}으로 보냈습니다${skipped}.${categoryNote} 이 마켓에서 가공하고 등록하세요.${openedNote}`;
  const note = $("#sendMarketMessage");
  if (note) note.textContent = message;
  $("#sendMarketDialog")?.close();
  toast(message);
}

function deliveryAddressError(template) {
  const shipping = String(template?.shipping_address_id || "").trim();
  const returning = String(template?.return_address_id || "").trim();
  if (shipping && returning) return "";
  if (!shipping && !returning) return "상품등록 전에 배송/가격에서 출고지와 반품지를 먼저 선택해 주세요.";
  if (!shipping) return "상품등록 전에 배송/가격에서 출고지를 먼저 선택해 주세요.";
  return "상품등록 전에 배송/가격에서 반품지를 먼저 선택해 주세요.";
}

function deliveryFeeTypeLabel(value) {
  return {
    FREE: "무료배송",
    CHARGE: "유료배송",
    CONDITIONAL_FREE: "조건부무료",
    UNIT_QUANTITY_PAID: "수량별",
  }[String(value || "")] || String(value || "");
}

function deliverySummary(template) {
  if (!template) return "저장된 배송/가격 설정이 없습니다.";
  const title = String(template.name || "기본 배송템플릿").trim() || "기본 배송템플릿";
  const fee = deliveryFeeTypeLabel(template.delivery_fee_type);
  const extra = [];
  if (Number(template.area2_extra_fee || 0) || Number(template.area3_extra_fee || 0) || template.area_type) {
    extra.push("제주·도서산간 추가");
  }
  if (template.bundle_usable && template.bundle_group_id) extra.push("묶음배송");
  return extra.length ? `${title} · ${fee} · ${extra.join(" · ")}` : `${title} · ${fee}`;
}

async function currentDeliveryTemplate() {
  if (!deliveryTemplates.length) {
    deliveryTemplates = await api("/api/delivery-templates");
  }
  return deliveryTemplates.find((item) => item.is_default) || deliveryTemplates[0] || null;
}

async function saveCurrentDeliveryTemplate() {
  const payload = deliveryPayload();
  if (!payload.name) {
    toast("제목을 입력해 주세요.", true);
    return null;
  }
  const addressError = deliveryAddressError(payload);
  if (addressError) {
    $("#deliveryMessage").textContent = addressError;
    $("#deliveryShippingAddress")?.focus();
    return null;
  }
  const saved = payload.id
    ? await api(`/api/delivery-templates/${payload.id}`, { method: "PUT", body: JSON.stringify(payload) })
    : await api("/api/delivery-templates", { method: "POST", body: JSON.stringify(payload) });
  deliveryTemplates = await api("/api/delivery-templates");
  fillDeliveryForm(deliveryTemplates.find((item) => item.id === saved.id) || saved);
  await loadDeliveryCatalog({
    shipping: saved.shipping_address_id || "",
    returning: saved.return_address_id || "",
    visit: saved.visit_address_id || "",
    bundle: saved.bundle_group_id || "",
  }).catch(() => {});
  return saved;
}

function fillAddressSelect(select, addresses, selected) {
  if (!select) return;
  const currentValue = selected == null || selected === "" ? "" : String(selected);
  select.innerHTML = "";
  const blank = document.createElement("option");
  blank.value = "";
  blank.textContent = "선택하세요";
  select.appendChild(blank);
  (addresses || []).forEach((item) => {
    const option = document.createElement("option");
    option.value = String(item.id);
    const kind = item.type_label || item.type;
    option.textContent = kind ? `${item.name} (${kind})` : (item.name || ("주소 " + item.id));
    select.appendChild(option);
  });
  if (currentValue && [...select.options].some((option) => option.value === currentValue)) {
    select.value = currentValue;
  } else {
    select.value = "";
  }
}

function fillBundleAddressSelect(selected) {
  const select = $("#deliveryBundleAddress");
  if (!select) return;
  const currentValue = selected == null || selected === "" ? "" : String(selected);
  select.innerHTML = "";
  const blank = document.createElement("option");
  blank.value = "";
  blank.textContent = deliveryBundleGroups.length ? "선택없음" : "묶음그룹 없음";
  select.appendChild(blank);
  (deliveryBundleGroups || []).forEach((item) => {
    const option = document.createElement("option");
    option.value = String(item.id);
    const ship = item.shipping_address_id ? `출고 ${item.shipping_address_id}` : "";
    const ret = item.return_address_id && String(item.return_address_id) !== String(item.shipping_address_id)
      ? `반품 ${item.return_address_id}`
      : "";
    option.textContent = [item.name || ("묶음배송 " + item.id), item.id ? `코드 ${item.id}` : "", ship, ret].filter(Boolean).join(" · ");
    select.appendChild(option);
  });
  if (currentValue && [...select.options].some((option) => option.value === currentValue)) {
    select.value = currentValue;
  } else {
    select.value = "";
  }
  $("#deliveryBundleGroup").value = select.value;
}

function applyBundleGroup(groupId) {
  $("#deliveryBundleGroup").value = groupId || "";
  if (!groupId) {
    syncDeliveryFields();
    return;
  }
  const group = (deliveryBundleGroups || []).find((item) => String(item.id) === String(groupId));
  if (!group) {
    syncDeliveryFields();
    return;
  }
  $("#deliveryBundleUsable").value = "true";
  if (group.shipping_address_id) {
    $("#deliveryShippingAddress").value = String(group.shipping_address_id);
  }
  if (group.return_address_id) {
    $("#deliveryReturnAddress").value = String(group.return_address_id);
  } else if (group.shipping_address_id) {
    $("#deliveryReturnAddress").value = String(group.shipping_address_id);
  }
  syncDeliveryFields();
}

function syncBundleGroupFromAddresses() {
  if ($("#deliveryBundleUsable").value !== "true") return;
  const ship = $("#deliveryShippingAddress").value;
  const ret = $("#deliveryReturnAddress").value;
  if (!ship) return;
  const match = (deliveryBundleGroups || []).find((item) =>
    String(item.shipping_address_id || "") === String(ship)
    && (!item.return_address_id || String(item.return_address_id) === String(ret) || String(item.return_address_id) === String(ship))
  ) || (deliveryBundleGroups || []).find((item) => String(item.shipping_address_id || "") === String(ship));
  if (match) {
    $("#deliveryBundleAddress").value = String(match.id);
    $("#deliveryBundleGroup").value = String(match.id);
    syncDeliveryFields();
  }
}

function syncDeliveryFields() {
  const bundleOn = $("#deliveryBundleUsable").value === "true";
  $("#deliveryBundleAddress").disabled = !bundleOn;
  if (!bundleOn) {
    $("#deliveryBundleAddress").value = "";
    $("#deliveryBundleGroup").value = "";
  }
  const hasBundleCode = bundleOn && !!String($("#deliveryBundleGroup").value || $("#deliveryBundleAddress").value || "").trim();
  const areaType = $("#deliveryAreaType");
  const area2 = document.querySelector('#deliveryForm [name="area2_extra_fee"]');
  const area3 = document.querySelector('#deliveryForm [name="area3_extra_fee"]');
  const hint = $("#deliveryAreaFeeHint");
  if (areaType) areaType.disabled = hasBundleCode;
  if (area2) area2.disabled = hasBundleCode;
  if (area3) area3.disabled = hasBundleCode;
  if (hint) hint.hidden = !hasBundleCode;
}

function renderDeliveryList() {
  const body = $("#deliveryTemplateBody");
  body.innerHTML = "";
  deliveryTemplates.forEach((item, index) => {
    const row = document.createElement("tr");
    row.dataset.id = item.id;
    if (item.id === currentDeliveryId) row.className = "active";
    const code = document.createElement("td");
    code.textContent = item.code || index + 1;
    const title = document.createElement("td");
    title.textContent = item.name || "";
    row.append(code, title);
    row.addEventListener("click", () => fillDeliveryForm(item));
    body.appendChild(row);
  });
}

function fillDeliveryForm(item) {
  currentDeliveryId = item?.id || "";
  const form = $("#deliveryForm");
  const source = item || {};
  [...form.elements].forEach((field) => {
    if (!field.name) return;
    const value = source[field.name];
    if (field.name === "bundle_usable" || field.name === "minor_purchasable") {
      field.value = value === true || value === "true" ? "true" : "false";
      return;
    }
    if (field.type === "checkbox") field.checked = Boolean(value);
    else if (field.name === "as_guide") field.value = resolveAsGuide(value);
    else field.value = value ?? (field.type === "number" ? 0 : "");
  });
  fillBundleAddressSelect(source.bundle_group_id || "");
  if ((source.bundle_usable === true || source.bundle_usable === "true") && (source.bundle_group_id || $("#deliveryBundleAddress").value)) {
    applyBundleGroup(source.bundle_group_id || $("#deliveryBundleAddress").value);
  }
  syncDeliveryFields();
  renderDeliveryList();
}

function blankDelivery() {
  const form = $("#deliveryForm");
  return {
    id: "",
    code: "",
    name: "",
    is_default: !deliveryTemplates.length,
    delivery_type: "DELIVERY",
    delivery_attribute_type: "NORMAL",
    delivery_company: "CJGLS",
    delivery_fee_type: "FREE",
    delivery_fee_pay_type: "COLLECT_OR_PREPAID",
    base_fee: 0,
    free_conditional_amount: 0,
    repeat_quantity: 0,
    bundle_usable: "false",
    bundle_group_id: "",
    quick_service: "",
    area_type: "AREA_2",
    area2_extra_fee: 0,
    area3_extra_fee: 0,
    return_fee: form.elements.return_fee?.value || 0,
    exchange_fee: form.elements.exchange_fee?.value || 0,
    shipping_address_id: $("#deliveryShippingAddress").value,
    return_address_id: $("#deliveryReturnAddress").value,
    visit_address_id: "",
    tax_type: "TAX",
    minor_purchasable: "true",
    as_guide: resolveAsGuide(form.elements.as_guide?.value),
    as_phone: form.elements.as_phone?.value || "",
    sale_type: "NEW",
    top_notice_urls: "",
    bottom_notice_urls: "",
  };
}

function deliveryPayload() {
  const form = $("#deliveryForm");
  const data = {};
  [...form.elements].forEach((field) => {
    if (!field.name) return;
    data[field.name] = field.type === "checkbox" ? field.checked : field.value;
  });
  ["code", "base_fee", "free_conditional_amount", "repeat_quantity", "area2_extra_fee", "area3_extra_fee", "return_fee", "exchange_fee"].forEach((key) => {
    data[key] = Number(data[key] || 0);
  });
  data.bundle_usable = data.bundle_usable === "true";
  data.minor_purchasable = data.minor_purchasable !== "false";
  data.is_default = true;
  return data;
}

function renderQuickRegions() {
  const selected = new Set(($("#deliveryQuickService").value || "").split(",").map((item) => item.trim()).filter(Boolean));
  const box = $("#quickRegionList");
  box.innerHTML = "";
  QUICK_REGIONS.forEach((name) => {
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = name;
    input.checked = selected.has(name);
    label.append(input, document.createTextNode(name));
    box.appendChild(label);
  });
}

async function loadDeliveryCatalog(selected = {}, applyImported = false) {
  const errors = [];
  try {
    deliveryAddresses = await api(withMarketParam("/api/addresses"));
  } catch (error) {
    deliveryAddresses = [];
    errors.push(error.message);
  }
  try {
    deliveryBundleGroups = await api(withMarketParam("/api/bundle-groups"));
  } catch (error) {
    deliveryBundleGroups = Array.isArray(deliveryBundleGroups) ? deliveryBundleGroups : [];
    errors.push(error.message);
  }
  const picked = { ...selected };
  if (applyImported) {
    const group = deliveryBundleGroups[0];
    if (group?.id) {
      picked.bundle = group.id;
      $("#deliveryBundleUsable").value = "true";
    }
    picked.shipping = "";
    picked.returning = "";
    picked.visit = "";
  }
  fillAddressSelect($("#deliveryShippingAddress"), deliveryAddresses, picked.shipping ?? $("#deliveryShippingAddress").value);
  fillAddressSelect($("#deliveryReturnAddress"), deliveryAddresses, picked.returning ?? $("#deliveryReturnAddress").value);
  fillAddressSelect($("#deliveryVisitAddress"), deliveryAddresses, picked.visit ?? $("#deliveryVisitAddress").value);
  fillBundleAddressSelect(picked.bundle ?? $("#deliveryBundleGroup").value);
  if ($("#deliveryBundleUsable").value === "true" && (picked.bundle || $("#deliveryBundleAddress").value)) {
    applyBundleGroup(picked.bundle || $("#deliveryBundleAddress").value);
  }
  syncDeliveryFields();
  if (!deliveryAddresses.length && !deliveryBundleGroups.length && errors.length) {
    throw new Error(errors.join(" / "));
  }
  return { addresses: deliveryAddresses, groups: deliveryBundleGroups, errors, applied: picked };
}

function showDeliveryMode(name) {
  const price = name === "price";
  if ($("#deliveryPane")) $("#deliveryPane").hidden = price;
  if ($("#priceSetPane")) $("#priceSetPane").hidden = !price;
  $("#deliveryTabShipping")?.classList.toggle("active", !price);
  $("#deliveryTabPrice")?.classList.toggle("active", price);
  if (!price) return;
  const ready = markets.length ? Promise.resolve(markets) : loadMarkets();
  ready.then(() => loadPriceSets()).catch((error) => toast(error.message, true));
}

async function openDeliveryEditor(options = {}) {
  const forRegister = Boolean(options.forRegister);
  deliveryTemplates = await api("/api/delivery-templates");
  const chosen = deliveryTemplates.find((item) => item.is_default) || deliveryTemplates[0] || null;
  fillDeliveryForm(chosen);
  $("#quickRegionPop").hidden = true;
  const registerBtn = $("#deliveryRegisterButton");
  if (registerBtn) registerBtn.hidden = !forRegister;
  $("#deliveryMessage").textContent = forRegister
    ? "상품등록 전에 출고지와 반품지를 선택한 뒤 '이 주소로 등록'을 누르세요."
    : "";
  showDeliveryMode("shipping");
  $("#deliveryDialog").showModal();
  if (forRegister) $("#deliveryShippingAddress")?.focus();
  try {
    await loadDeliveryCatalog({
      shipping: chosen?.shipping_address_id || "",
      returning: chosen?.return_address_id || "",
      visit: chosen?.visit_address_id || "",
      bundle: chosen?.bundle_group_id || "",
    });
  } catch (error) {
    $("#deliveryMessage").textContent = forRegister
      ? `${$("#deliveryMessage").textContent} ${error.message}`
      : error.message;
  }
}

$("#settingsForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await api("/api/settings", { method: "PUT", body: JSON.stringify(settingsPayload()) });
    $("#settingsMessage").textContent = "저장했습니다.";
  } catch (error) {
    $("#settingsMessage").textContent = error.message;
  }
});
async function testSettingConnection(target, messageId) {
  const box = $(messageId);
  if (box) box.textContent = "연결 확인 중...";
  try {
    await api("/api/settings", { method: "PUT", body: JSON.stringify(settingsPayload()) });
    const result = await api(`/api/settings/test?target=${encodeURIComponent(target)}`, { method: "POST", body: "{}" });
    const text = target === "searchad" ? result.searchad : (result.ai || result.gemini || "");
    if (box) box.textContent = text || "연결 결과를 받지 못했습니다.";
  } catch (error) {
    if (box) box.textContent = error.message;
  }
}
$("#testAiConnection")?.addEventListener("click", () => {
  testSettingConnection("ai", "#aiTestMessage");
});
$("#testSearchadConnection")?.addEventListener("click", () => {
  testSettingConnection("searchad", "#searchadTestMessage");
});
function fillBenefitForm(row) {
  const form = $("#benefitForm");
  if (!form) return;
  const source = row || {};
  [...form.elements].forEach((field) => {
    if (!field.name) return;
    const value = source[field.name];
    if (field.type === "checkbox") {
      field.checked = Boolean(value);
      return;
    }
    if (field.type === "hidden" && field.name.endsWith("_enabled")) {
      field.value = value === true || value === "true" ? "true" : "false";
      return;
    }
    if (field.tagName === "SELECT" && field.name.endsWith("_enabled")) {
      field.value = value === true || value === "true" ? "true" : "false";
      return;
    }
    field.value = value ?? (field.type === "number" ? 0 : "");
  });
  syncBenefitFields();
}

function benefitPayload() {
  const form = $("#benefitForm");
  const data = {};
  [...form.elements].forEach((field) => {
    if (!field.name) return;
    if (field.type === "checkbox") data[field.name] = field.checked;
    else if (field.type === "hidden" && field.name.endsWith("_enabled")) data[field.name] = field.value === "true";
    else if (field.tagName === "SELECT" && field.name.endsWith("_enabled")) data[field.name] = field.value === "true";
    else data[field.name] = field.value;
  });
  return data;
}

function syncBenefitToggle(name, on) {
  document.querySelectorAll(`[data-toggle="${name}"] button`).forEach((button) => {
    button.classList.toggle("active", button.dataset.value === (on ? "true" : "false"));
  });
}

function syncBenefitFields() {
  const form = $("#benefitForm");
  if (!form) return;
  const reviewOn = Boolean(form.elements.review_point_enabled?.checked);
  const periodOn = Boolean(form.elements.review_point_period_only?.checked);
  const multiOn = String(form.elements.multi_discount_enabled?.value || "") === "true";
  const multiPeriodOn = Boolean(form.elements.multi_discount_period_only?.checked);
  const basis = form.elements.multi_discount_basis?.value || "AMOUNT";
  if ($("#benefitReviewFields")) $("#benefitReviewFields").hidden = !reviewOn;
  if ($("#benefitReviewPeriodRow")) $("#benefitReviewPeriodRow").hidden = !reviewOn || !periodOn;
  if ($("#benefitMultiFields")) $("#benefitMultiFields").hidden = !multiOn;
  if ($("#benefitMultiPeriodRow")) $("#benefitMultiPeriodRow").hidden = !multiOn || !multiPeriodOn;
  if ($("#benefitMultiOrderUnit")) $("#benefitMultiOrderUnit").textContent = basis === "QUANTITY" ? "개" : "원";
  syncBenefitToggle("multi_discount_enabled", multiOn);
}

async function openBenefitEditor() {
  const row = await api("/api/benefit");
  fillBenefitForm(row);
  $("#benefitMessage").textContent = "";
  $("#benefitDialog").showModal();
}

function syncDiscountFields() {
  const discountOn = $("#discountEnabled")?.value === "true";
  document.querySelectorAll('#discountForm [data-toggle="discount_enabled"] button').forEach((button) => {
    button.classList.toggle("active", button.dataset.value === (discountOn ? "true" : "false"));
  });
  if ($("#saleDiscountFields")) $("#saleDiscountFields").hidden = !discountOn;
}

function fillDiscountForm(item) {
  const amount = Number(item?.discount_price || 0);
  if ($("#discountEnabled")) $("#discountEnabled").value = amount > 0 ? "true" : "false";
  if ($("#discountPriceValue")) $("#discountPriceValue").value = String(amount || 0);
  if ($("#discountUnitValue")) {
    $("#discountUnitValue").value = String(item?.discount_unit || "WON").toUpperCase() === "PERCENT" ? "PERCENT" : "WON";
  }
  syncDiscountFields();
}

function openDiscountDialog() {
  const items = requireSelected();
  if (!items.length) return;
  if (items.every(isMasterProduct)) return masterEditBlocked(items[0]);
  fillDiscountForm(items[0]);
  if ($("#discountMessage")) $("#discountMessage").textContent = `선택한 ${items.length}개 상품에 적용합니다.`;
  $("#discountDialog")?.showModal();
}

$("#openDiscount")?.addEventListener("click", () => openDiscountDialog());
$("#closeDiscount")?.addEventListener("click", () => $("#discountDialog")?.close());
$("#discountForm")?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-toggle] button");
  if (!button) return;
  if (button.parentElement?.dataset.toggle !== "discount_enabled") return;
  if ($("#discountEnabled")) $("#discountEnabled").value = button.dataset.value;
  syncDiscountFields();
});
$("#discountForm")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const items = requireSelected();
  if (!items.length) return;
  const discountOn = $("#discountEnabled")?.value === "true";
  const discount_price = discountOn ? Number($("#discountPriceValue")?.value || 0) : 0;
  const discount_unit = $("#discountUnitValue")?.value || "WON";
  try {
    setBusy(true, "즉시할인을 적용하는 중입니다.");
    const editable = items.filter((item) => !isMasterProduct(item));
    if (!editable.length) throw new Error(MASTER_LOCK_MESSAGE);
    for (const item of editable) {
      await saveProduct(item, { discount_price, discount_unit });
    }
    await loadProducts();
    $("#discountDialog")?.close();
    log(`선택한 ${items.length}개 상품에 즉시할인을 적용했습니다.`, "ok");
  } catch (error) {
    if ($("#discountMessage")) $("#discountMessage").textContent = error.message;
    log(error.message, "err");
  } finally {
    setBusy(false);
  }
});

$("#openDelivery").addEventListener("click", () => {
  openDeliveryEditor().catch((error) => toast(error.message, true));
});
$("#openBenefit")?.addEventListener("click", () => {
  openBenefitEditor().catch((error) => toast(error.message, true));
});
$("#closeBenefit")?.addEventListener("click", () => $("#benefitDialog")?.close());
$("#benefitForm")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const saved = await api("/api/benefit", { method: "PUT", body: JSON.stringify(benefitPayload()) });
    fillBenefitForm(saved);
    $("#benefitMessage").textContent = "구매/리뷰 혜택 조건을 저장했습니다. 상품등록에 이 설정이 사용됩니다.";
    toast("구매/리뷰 혜택 조건을 저장했습니다.");
  } catch (error) {
    $("#benefitMessage").textContent = error.message;
  }
});
$("#benefitForm")?.addEventListener("change", syncBenefitFields);
$("#benefitForm")?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-toggle] button");
  if (!button) return;
  const name = button.parentElement?.dataset.toggle;
  const field = name ? $("#benefitForm")?.elements?.[name] : null;
  if (!field) return;
  field.value = button.dataset.value;
  syncBenefitFields();
});
$("#openNotices").addEventListener("click", () => {
  openNoticeDialog().catch((error) => toast(error.message, true));
});
$("#closeNameKeywords")?.addEventListener("click", () => $("#nameKeywordDialog")?.close());
$("#addNameKeyword")?.addEventListener("click", () => addNameKeyword($("#nameKeywordInput")?.value || ""));
let nameKeywordEnterCommit = false;
$("#nameKeywordInput")?.addEventListener("keydown", (event) => {
  if (event.key !== "Enter") return;
  if (event.isComposing || event.keyCode === 229) {
    nameKeywordEnterCommit = true;
    return;
  }
  event.preventDefault();
  commitNameKeywordInput();
});
$("#nameKeywordInput")?.addEventListener("compositionend", () => {
  if (!nameKeywordEnterCommit) return;
  nameKeywordEnterCommit = false;
  commitNameKeywordInput();
});
$("#nameKeywordForm")?.addEventListener("submit", (event) => {
  event.preventDefault();
  saveNameKeywords().catch((error) => toast(error.message, true));
});
$("#closeNotice").addEventListener("click", () => $("#noticeDialog").close());
$("#importNotices").addEventListener("click", () => {
  importStoreNotices().catch((error) => toast(error.message, true));
});
$("#openNoticeCreate").addEventListener("click", () => openNoticeCreateDialog());
$("#closeNoticeCreate").addEventListener("click", () => $("#noticeCreateDialog").close());
$("#saveNoticeCreate").addEventListener("click", () => {
  saveCreatedNotice().catch((error) => {
    $("#noticeCreateMessage").textContent = error.message;
    toast(error.message, true);
  });
});
$("#noticeCreateForm").addEventListener("submit", (event) => {
  event.preventDefault();
  saveCreatedNotice().catch((error) => {
    $("#noticeCreateMessage").textContent = error.message;
    toast(error.message, true);
  });
});
$("#noticeTextToolbar").addEventListener("click", (event) => {
  const button = event.target.closest("[data-notice-cmd]");
  if (!button) return;
  noticeExec(button.dataset.noticeCmd);
});
$("#noticeFontName").addEventListener("change", () => noticeExec("fontName", $("#noticeFontName").value));
$("#noticeFontSize").addEventListener("change", () => noticeExec("fontSize", $("#noticeFontSize").value));
$("#noticeForeColor").addEventListener("input", () => noticeExec("foreColor", $("#noticeForeColor").value));
$("#noticeLink").addEventListener("click", () => {
  const href = prompt("링크 주소");
  if (href) noticeExec("createLink", href);
});
$("#applyNoticesSelected").addEventListener("click", () => {
  applySelectedNotices().catch((error) => toast(error.message, true));
});
$("#applyNoticeDefaults").addEventListener("click", () => {
  saveNoticeDefaults().catch((error) => toast(error.message, true));
});
$("#addMarket").addEventListener("click", () => {
  fillMarketForm({ channel: $("#marketChannel")?.value || "smartstore" });
  $("#marketMessage").textContent = "";
});
$("#marketChannel").addEventListener("change", () => {
  if (fillingMarketForm) return;
  fillMarketForm({ channel: $("#marketChannel").value || "smartstore" });
  $("#marketMessage").textContent = "";
});
$("#testMarketButton")?.addEventListener("click", () => {
  testMarketConnection().catch((error) => toast(error.message, true));
});
$("#deleteMarket").addEventListener("click", () => {
  deleteCurrentMarket().catch((error) => toast(error.message, true));
});
$("#marketForm").addEventListener("submit", (event) => {
  event.preventDefault();
  saveMarketForm().catch((error) => toast(error.message, true));
});
$("#closeDelivery").addEventListener("click", () => {
  const registerBtn = $("#deliveryRegisterButton");
  if (registerBtn) registerBtn.hidden = true;
  $("#deliveryDialog").close();
});
$("#addDeliveryTemplate").addEventListener("click", () => {
  fillDeliveryForm(blankDelivery());
  $("#deliveryMessage").textContent = "새 템플릿입니다. 저장하면 목록에 추가됩니다.";
});
$("#deliveryBundleUsable").addEventListener("change", syncDeliveryFields);
$("#deliveryBundleAddress").addEventListener("change", () => {
  const chosen = $("#deliveryBundleAddress").value;
  if (chosen) {
    applyBundleGroup(chosen);
  } else {
    $("#deliveryBundleGroup").value = "";
    $("#deliveryBundleUsable").value = "false";
  }
  syncDeliveryFields();
});
$("#deliveryShippingAddress").addEventListener("change", syncBundleGroupFromAddresses);
$("#deliveryReturnAddress").addEventListener("change", syncBundleGroupFromAddresses);
async function importMarketDelivery() {
  setBusy(true, "스마트스토어 배송정보관리·템플릿관리를 가져오는 중입니다.");
  try {
    const result = await api(withMarketParam("/api/delivery-templates/import"), { method: "POST", body: "{}" });
    deliveryTemplates = result.templates || [];
    if (Array.isArray(result.addresses)) deliveryAddresses = result.addresses;
    if (Array.isArray(result.bundle_groups) && result.bundle_groups.length) {
      deliveryBundleGroups = result.bundle_groups;
    }
    const chosen = deliveryTemplates.find((item) => item.is_default) || deliveryTemplates[0] || null;
    fillDeliveryForm(chosen);
    await loadDeliveryCatalog({
      shipping: chosen?.shipping_address_id || "",
      returning: chosen?.return_address_id || "",
      visit: chosen?.visit_address_id || "",
      bundle: chosen?.bundle_group_id || "",
    }).catch(() => {});
    const message = result.message || `배송템플릿 ${deliveryTemplates.length}개를 가져왔습니다.`;
    const needLogin = /프로그램이 연 Chrome|판매자센터 로그인|템플릿은 아직/.test(message);
    $("#deliveryMessage").textContent = message;
    log(message, needLogin ? "err" : "ok");
    toast(needLogin ? "프로그램 Chrome에서 판매자센터 로그인 후 다시 가져오세요." : message, needLogin);
    return result;
  } finally {
    setBusy(false);
  }
}

$("#loadDeliveryCatalog").addEventListener("click", () => {
  importMarketDelivery().catch((error) => {
    $("#deliveryMessage").textContent = error.message;
    log(error.message, "err");
  });
});
$("#openQuickRegions").addEventListener("click", () => {
  renderQuickRegions();
  $("#quickRegionPop").hidden = !$("#quickRegionPop").hidden;
});
$("#closeQuickRegions").addEventListener("click", () => {
  $("#quickRegionPop").hidden = true;
});
$("#applyQuickRegions").addEventListener("click", () => {
  const picked = [...$("#quickRegionList").querySelectorAll("input:checked")].map((item) => item.value);
  $("#deliveryQuickService").value = picked.join(",");
  $("#quickRegionPop").hidden = true;
});
$("#deleteDeliveryTemplate").addEventListener("click", async () => {
  if (!currentDeliveryId) return toast("저장된 템플릿만 삭제할 수 있습니다.", true);
  try {
    deliveryTemplates = await api(`/api/delivery-templates/${currentDeliveryId}`, { method: "DELETE" });
    fillDeliveryForm(deliveryTemplates.find((item) => item.is_default) || deliveryTemplates[0]);
    $("#deliveryMessage").textContent = "템플릿을 삭제했습니다.";
  } catch (error) {
    $("#deliveryMessage").textContent = error.message;
  }
});
$("#deliveryRegisterButton")?.addEventListener("click", async () => {
  try {
    if (!(await saveCurrentDeliveryTemplate())) return;
    const registerBtn = $("#deliveryRegisterButton");
    if (registerBtn) registerBtn.hidden = true;
    $("#deliveryDialog").close();
    await proceedRegisterSelected();
  } catch (error) {
    $("#deliveryMessage").textContent = error.message;
  }
});
$("#deliveryForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    if (!(await saveCurrentDeliveryTemplate())) return;
    $("#deliveryMessage").textContent = "배송정보를 저장했습니다. 상품등록에 이 설정이 사용됩니다.";
  } catch (error) {
    $("#deliveryMessage").textContent = error.message;
  }
});

function columnStorageKey(table) {
  return `uploader-col-widths:${table.id}`;
}

function applyColumnWidths(table) {
  const saved = JSON.parse(localStorage.getItem(columnStorageKey(table)) || "{}");
  const cols = [...table.querySelectorAll("col")];
  cols.forEach((col) => {
    const key = col.dataset.col;
    if (saved[key]) col.style.width = `${saved[key]}px`;
  });
  table.style.width = `${cols.reduce((sum, col) => sum + (parseFloat(col.style.width) || 80), 0)}px`;
}

function saveColumnWidths(table) {
  const saved = {};
  table.querySelectorAll("col").forEach((col) => {
    saved[col.dataset.col] = Math.round(parseFloat(col.style.width) || col.getBoundingClientRect().width);
  });
  localStorage.setItem(columnStorageKey(table), JSON.stringify(saved));
}

function enablePaneResize(pane, { edge = "right", min = 160, max = 720, storageKey, basis = true } = {}) {
  if (!pane || pane.dataset.paneResize) return;
  pane.dataset.paneResize = "1";
  const saved = Number(localStorage.getItem(storageKey) || 0);
  const apply = (width) => {
    pane.style.width = `${width}px`;
    if (basis) pane.style.flexBasis = `${width}px`;
  };
  if (saved >= min && saved <= max) apply(saved);
  const handle = document.createElement("div");
  handle.className = "pane-resizer";
  handle.title = "좌우로 끌어 간격을 조절합니다";
  pane.appendChild(handle);
  handle.addEventListener("mousedown", (event) => {
    event.preventDefault();
    event.stopPropagation();
    const startX = event.pageX;
    const startWidth = pane.getBoundingClientRect().width;
    document.body.classList.add("col-resizing");
    const move = (moveEvent) => {
      const delta = moveEvent.pageX - startX;
      const width = Math.max(min, Math.min(max, Math.round(edge === "left" ? startWidth - delta : startWidth + delta)));
      apply(width);
    };
    const up = () => {
      document.removeEventListener("mousemove", move);
      document.removeEventListener("mouseup", up);
      document.body.classList.remove("col-resizing");
      localStorage.setItem(storageKey, String(Math.round(pane.getBoundingClientRect().width)));
    };
    document.addEventListener("mousemove", move);
    document.addEventListener("mouseup", up);
  });
}

function enableJobStatusResize() {
  const key = "job-status-height";
  const min = 72;
  const max = 480;
  const saved = Number(localStorage.getItem(key) || 0);
  const apply = (height) => {
    const next = Math.max(min, Math.min(max, Math.round(height)));
    document.documentElement.style.setProperty("--job-status-height", `${next}px`);
    return next;
  };
  if (saved >= min && saved <= max) apply(saved);
  document.querySelectorAll(".bottom, #globalStatusLog").forEach((pane) => {
    if (pane.dataset.rowResize) return;
    pane.dataset.rowResize = "1";
    const handle = document.createElement("div");
    handle.className = "pane-resizer row-resizer";
    handle.title = "위아래로 끌어 작업상태 높이를 조절합니다";
    pane.prepend(handle);
    handle.addEventListener("mousedown", (event) => {
      event.preventDefault();
      event.stopPropagation();
      const startY = event.pageY;
      const startHeight = pane.getBoundingClientRect().height;
      document.body.classList.add("row-resizing");
      const move = (moveEvent) => apply(startHeight + (startY - moveEvent.pageY));
      const up = () => {
        document.removeEventListener("mousemove", move);
        document.removeEventListener("mouseup", up);
        document.body.classList.remove("row-resizing");
        localStorage.setItem(key, String(Math.round(pane.getBoundingClientRect().height)));
      };
      document.addEventListener("mousemove", move);
      document.addEventListener("mouseup", up);
    });
  });
}

function enableDetailLabelResize() {
  const panel = $("#orderDetail");
  if (!panel || panel.dataset.labelResize) return;
  panel.dataset.labelResize = "1";
  const saved = Number(localStorage.getItem("order-detail-label") || 0);
  const apply = (width) => {
    const next = Math.max(90, Math.min(360, Math.round(width)));
    panel.style.setProperty("--detail-label", `${next}px`);
    return next;
  };
  if (saved) apply(saved);
  const handle = document.createElement("div");
  handle.className = "pane-resizer detail-label-resizer";
  handle.title = "좌우로 끌어 항목 이름 칸을 조절합니다";
  panel.appendChild(handle);
  handle.addEventListener("mousedown", (event) => {
    event.preventDefault();
    event.stopPropagation();
    const startX = event.pageX;
    const startWidth = parseFloat(getComputedStyle(panel).getPropertyValue("--detail-label")) || 160;
    document.body.classList.add("col-resizing");
    let width = startWidth;
    const move = (moveEvent) => {
      width = apply(startWidth + moveEvent.pageX - startX);
    };
    const up = () => {
      document.removeEventListener("mousemove", move);
      document.removeEventListener("mouseup", up);
      document.body.classList.remove("col-resizing");
      localStorage.setItem("order-detail-label", String(width));
    };
    document.addEventListener("mousemove", move);
    document.addEventListener("mouseup", up);
  });
}

function enableColumnResize(table) {
  applyColumnWidths(table);
  [...table.tHead.rows[0].cells].forEach((th, index) => {
    if (th.querySelector(".col-resizer")) return;
    th.style.position = "sticky";
    const handle = document.createElement("span");
    handle.className = "col-resizer";
    handle.title = "좌우로 끌어 열 너비를 조절합니다";
    th.appendChild(handle);
    handle.addEventListener("mousedown", (event) => {
      event.preventDefault();
      event.stopPropagation();
      const col = table.querySelectorAll("col")[index];
      const startX = event.pageX;
      const startWidth = col.getBoundingClientRect().width;
      table.classList.add("resizing");
      document.body.classList.add("col-resizing");
      const move = (moveEvent) => {
        const width = Math.max(36, Math.round(startWidth + moveEvent.pageX - startX));
        col.style.width = `${width}px`;
        col.style.minWidth = `${width}px`;
        const total = [...table.querySelectorAll("col")].reduce((sum, item) => sum + (parseFloat(item.style.width) || 80), 0);
        table.style.width = `${total}px`;
        table.style.minWidth = `${total}px`;
      };
      const up = () => {
        document.removeEventListener("mousemove", move);
        document.removeEventListener("mouseup", up);
        table.classList.remove("resizing");
        document.body.classList.remove("col-resizing");
        saveColumnWidths(table);
      };
      document.addEventListener("mousemove", move);
      document.addEventListener("mouseup", up);
    });
    handle.addEventListener("dblclick", (event) => {
      event.preventDefault();
      event.stopPropagation();
      const col = table.querySelectorAll("col")[index];
      const cells = [th, ...table.tBodies[0].querySelectorAll(`td:nth-child(${index + 1})`)];
      let width = 64;
      cells.forEach((cell) => {
        const text = cell.querySelector("input")?.value || cell.textContent || "";
        width = Math.max(width, Math.min(480, 16 + text.length * 8));
      });
      col.style.width = `${width}px`;
      col.style.minWidth = `${width}px`;
      const total = [...table.querySelectorAll("col")].reduce((sum, item) => sum + (parseFloat(item.style.width) || 80), 0);
      table.style.width = `${total}px`;
      table.style.minWidth = `${total}px`;
      saveColumnWidths(table);
    });
  });
}

async function copyText(text) {
  const value = String(text || "").trim();
  if (!value) throw new Error("복사할 내용이 없습니다.");
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }
  const area = document.createElement("textarea");
  area.value = value;
  area.setAttribute("readonly", "");
  area.style.position = "fixed";
  area.style.left = "-9999px";
  document.body.appendChild(area);
  area.select();
  const ok = document.execCommand("copy");
  area.remove();
  if (!ok) throw new Error("클립보드에 복사하지 못했습니다.");
}

async function shareOrCopyLink(link, title = "모두모두AI 공유 주소") {
  const url = String(link || "").trim();
  if (!url) return;
  if (navigator.share) {
    try {
      await navigator.share({ title, text: "같은 와이파이에서 이 주소로 열어 주세요.", url });
      return;
    } catch (error) {
      if (error?.name === "AbortError") return;
    }
  }
  await copyText(url);
  toast("링크를 복사했습니다. 카톡·문자에 붙여 넣으세요.");
}

function renderShareLinkRows(container, links) {
  if (!container) return;
  container.replaceChildren();
  if (!links.length) {
    container.textContent = "다른 컴퓨터용 주소를 찾지 못했습니다. 이 컴퓨터가 공유기에 연결되어 있는지 확인해 주세요.";
    return;
  }
  links.forEach((link) => {
    const row = document.createElement("div");
    row.className = "share-link-row";
    const anchor = document.createElement("a");
    anchor.href = link;
    anchor.textContent = link;
    anchor.className = "share-link-url";
    const copyBtn = document.createElement("button");
    copyBtn.type = "button";
    copyBtn.textContent = "복사";
    copyBtn.addEventListener("click", async () => {
      try {
        await copyText(link);
        toast("링크를 복사했습니다.");
      } catch (error) {
        toast(error.message || "복사에 실패했습니다.", true);
      }
    });
    const shareBtn = document.createElement("button");
    shareBtn.type = "button";
    shareBtn.textContent = "공유";
    shareBtn.addEventListener("click", async () => {
      try {
        await shareOrCopyLink(link);
      } catch (error) {
        toast(error.message || "공유에 실패했습니다.", true);
      }
    });
    row.append(anchor, copyBtn, shareBtn);
    container.append(row);
  });
}

let cachedShareLinks = [];

async function fetchShareLinks() {
  const data = await api("/api/share-link");
  cachedShareLinks = data.links || [];
  return cachedShareLinks;
}

async function loadShareLinks() {
  const box = $("#helpShare");
  if (!box) return;
  try {
    const links = await fetchShareLinks();
    box.replaceChildren();
    const head = document.createElement("p");
    head.className = "share-link-head";
    head.textContent = "다른 컴퓨터·휴대폰에 이 링크를 보내면 같은 와이파이에서 화면을 볼 수 있습니다.";
    box.append(head);
    const list = document.createElement("div");
    list.className = "share-link-list";
    box.append(list);
    renderShareLinkRows(list, links);
  } catch (error) {
    box.textContent = "";
  }
}

function showAppView(name) {
  if (name === "ownerclan") name = "collect";
  if (name !== "help") lastAppView = name;
  $("#viewProducts").hidden = name !== "products";
  $("#viewWholesalers").hidden = name !== "wholesalers";
  if ($("#viewCollect")) $("#viewCollect").hidden = name !== "collect";
  $("#viewOrders").hidden = name !== "orders";
  if ($("#viewInquiries")) $("#viewInquiries").hidden = name !== "inquiries";
  $("#viewSettings").hidden = name !== "settings";
  if ($("#viewHelp")) $("#viewHelp").hidden = name !== "help";
  if ($("#globalStatusLog")) $("#globalStatusLog").hidden = name === "products";
  $("#appTabProducts").classList.toggle("active", name === "products");
  $("#appTabOrders").classList.toggle("active", name === "orders");
  $("#appTabInquiries")?.classList.toggle("active", name === "inquiries");
  $("#appTabCollect")?.classList.toggle("active", name === "collect");
  $("#appTabWholesalers").classList.toggle("active", name === "wholesalers");
  $("#appTabSettings").classList.toggle("active", name === "settings");
  $("#appTabHelp")?.classList.toggle("active", name === "help");
  if (name === "help") {
    showHelpPanel(HELP_BY_VIEW[lastAppView] || "help-overview");
    loadShareLinks();
  }
  if (name === "wholesalers") loadWholesalers().catch((error) => toast(error.message, true));
  if (name === "collect") {
    loadWholesalers()
      .then(() => openCollectView())
      .catch((error) => toast(error.message, true));
  }
  if (name === "orders") {
    arrivalOrderCount = 0;
    paintArrivalBadges();
    const productLoad = products.length ? Promise.resolve() : loadProducts().catch(() => {});
    Promise.all([loadWholesalers(), loadInquiries(), productLoad]).then(() => {
      fillOrderMarketTree();
      if (!ordersCollected) {
        setOrderTab(orderTab);
        return;
      }
      return loadOrders().then(() => setOrderTab(orderTab));
    }).catch((error) => toast(error.message, true));
  }
  if (name === "inquiries") {
    arrivalInquiryCount = 0;
    paintArrivalBadges();
    if (!$("#inquiryDateFrom")?.value) setInquiryPeriod("month");
    Promise.all([loadMarkets(), loadInquiries()]).then(() => {
      fillInquiryMallSelects();
      renderInquiryList();
    }).catch((error) => toast(error.message, true));
  }
  if (name === "settings") {
    loadSettingsView().catch((error) => toast(error.message, true));
  }
}

let setupFocus = null;
let setupChannel = "";

const SETUP_HELPS = {
  smartstore: {
    title: "스마트스토어 설정",
    intro: "네이버 커머스 API 애플리케이션 키와 판매자 UID를 넣으면 스토어 연결과 상품등록에 씁니다.",
    links: [
      ["네이버 커머스 API 센터", "https://apicenter.commerce.naver.com/ko/basic/join"],
      ["커머스 API 문서", "https://apicenter.commerce.naver.com/docs/commerce-api/current"],
      ["스마트스토어 센터", "https://sell.smartstore.naver.com"],
    ],
    steps: [
      "커머스 API 센터에서 애플리케이션을 등록하고 애플리케이션 ID와 시크릿을 발급합니다.",
      "솔루션 앱이면 마켓관리의 애플리케이션 ID, 시크릿과 판매자 UID(account_id)를 넣습니다.",
      "판매자 앱이면 스토어마다 그 스토어의 애플리케이션 ID와 시크릿을 마켓관리에 넣습니다.",
      "스토어 주소는 https://smartstore.naver.com/스토어아이디 형식으로 마켓관리에 넣습니다.",
      "저장한 뒤 마켓관리의 연동 테스트를 누릅니다.",
    ],
    fields: [
      ["마켓관리 스토어 주소", "market:smartstore:url"],
      ["마켓관리 판매자 account_id", "market:smartstore:naver_account_id"],
      ["마켓관리 애플리케이션 ID", "market:smartstore:api_key"],
      ["마켓관리 애플리케이션 시크릿", "market:smartstore:api_secret"],
    ],
  },
  coupang: {
    title: "쿠팡 설정",
    intro: "쿠팡 Open API의 Access Key, Secret Key, 업체코드(vendorId)를 마켓관리에 넣습니다. 지금 보신 ‘시작하기’ 화면에서 키를 받습니다.",
    links: [
      ["OpenAPI Key 발급받기 (시작하기)", "https://developers.coupangcorp.com/hc/ko/categories/360002110872"],
      ["쿠팡 Wing", "https://wing.coupang.com"],
      ["쿠팡 개발자 문서 홈", "https://developers.coupangcorp.com/hc/ko"],
    ],
    steps: [
      "개발자 문서 왼쪽 ‘시작하기’에서 ‘OpenAPI Key 발급받기’ 카드를 엽니다.",
      "쿠팡 Wing에 로그인한 뒤 Access Key, Secret Key, Vendor ID(업체코드)를 발급·확인합니다.",
      "마켓관리에서 마켓을 쿠팡으로 고르고, 아이디키=Access Key, 시크릿키=Secret Key, 업체코드=Vendor ID를 넣습니다.",
      "저장한 뒤 연동 테스트를 누릅니다. IP 허용 목록이 있으면 이 PC/서버 IP도 Wing에 등록합니다.",
    ],
    fields: [
      ["마켓관리 아이디키 (= Access Key)", "market:coupang:api_key"],
      ["마켓관리 시크릿키 (= Secret Key)", "market:coupang:api_secret"],
      ["마켓관리 업체코드 (= Vendor ID)", "market:coupang:vendor_code"],
    ],
  },
  "11st": {
    title: "11번가 설정",
    intro: "11번가 셀러오피스에서 발급한 OPEN API KEY 32자를 넣습니다.",
    links: [
      ["11번가 Open API", "https://openapi.11st.co.kr"],
      ["11번가 셀러오피스", "https://soffice.11st.co.kr"],
    ],
    steps: [
      "셀러오피스에 로그인한 뒤 셀러정보에서 Open API 키를 확인합니다.",
      "32자 OPEN API KEY를 마켓관리의 아이디키에 넣습니다.",
      "저장한 뒤 마켓관리에서 연동 테스트를 누릅니다.",
    ],
    fields: [
      ["마켓관리 아이디키", "market:11st:api_key"],
    ],
  },
  auction: {
    title: "옥션 설정",
    intro: "옥션은 API 키가 없습니다. ESM+ 판매자 아이디로 로그인합니다. G마켓과 같은 ESM 계정을 씁니다.",
    links: [
      ["ESM+", "https://www.esmplus.com"],
    ],
    steps: [
      "ESM+에 쓰는 판매자 아이디와 비밀번호를 확인합니다.",
      "마켓관리에서 마켓을 옥션으로 고르고 스토어명, 아이디, 패스워드를 넣습니다.",
      "ESM ID가 따로 있으면 ESM ID란에 넣습니다.",
      "저장한 뒤 연동 테스트를 누릅니다.",
    ],
    fields: [
      ["마켓관리 아이디", "market:auction:login_id"],
      ["마켓관리 패스워드", "market:auction:login_password"],
      ["마켓관리 ESM ID", "market:auction:esm_id"],
    ],
  },
  gmarket: {
    title: "G마켓 설정",
    intro: "G마켓은 API 키가 없습니다. ESM+ 판매자 아이디로 로그인합니다. 옥션과 같은 ESM 계정을 씁니다.",
    links: [
      ["ESM+", "https://www.esmplus.com"],
    ],
    steps: [
      "ESM+에 쓰는 판매자 아이디와 비밀번호를 확인합니다.",
      "마켓관리에서 마켓을 G마켓으로 고르고 스토어명, 아이디, 패스워드를 넣습니다.",
      "ESM ID가 따로 있으면 ESM ID란에 넣습니다.",
      "저장한 뒤 연동 테스트를 누릅니다.",
    ],
    fields: [
      ["마켓관리 아이디", "market:gmarket:login_id"],
      ["마켓관리 패스워드", "market:gmarket:login_password"],
      ["마켓관리 ESM ID", "market:gmarket:esm_id"],
    ],
  },
  toss: {
    title: "토스쇼핑 설정",
    intro: "토스쇼핑 판매자 센터에서 발급한 Access Key와 Secret Key를 마켓관리에 넣습니다.",
    links: [
      ["토스쇼핑 판매자 센터", "https://shopping-seller.toss.im"],
    ],
    steps: [
      "토스쇼핑 판매자 센터에서 API 키를 발급합니다.",
      "마켓관리에서 마켓을 토스쇼핑으로 고르고 Access Key와 Secret Key를 넣습니다.",
      "저장한 뒤 연동 테스트를 누릅니다.",
    ],
    fields: [
      ["Access Key", "market:toss:api_key"],
      ["Secret Key", "market:toss:api_secret"],
    ],
  },
  lotteon: {
    title: "롯데ON 설정",
    intro: "롯데ON Open API의 인증키, 시크릿키, 거래처번호(trNo)를 마켓관리에 넣습니다.",
    links: [
      ["롯데ON 스토어 센터", "https://store.lotteon.com"],
      ["롯데ON Open API", "https://api.lotteon.com"],
    ],
    steps: [
      "롯데ON 판매자 센터에서 Open API 인증키와 거래처번호를 확인합니다.",
      "마켓관리에서 마켓을 롯데ON으로 고르고 인증키, 시크릿키, 거래처번호를 넣습니다.",
      "저장한 뒤 연동 테스트를 누릅니다.",
    ],
    fields: [
      ["인증키", "market:lotteon:api_key"],
      ["시크릿키", "market:lotteon:api_secret"],
      ["거래처번호", "market:lotteon:vendor_code"],
    ],
  },
  kakao: {
    title: "카카오톡스토어 설정",
    intro: "카카오쇼핑 판매자 센터의 Admin/API Key와 판매자 Key를 마켓관리에 넣습니다. 연동대행사 승인이 필요할 수 있습니다.",
    links: [
      ["카카오쇼핑 판매자 센터", "https://shopping-seller.kakao.com"],
      ["카카오 디벨로퍼스", "https://developers.kakao.com"],
    ],
    steps: [
      "카카오 디벨로퍼스에서 앱을 만들고 Admin 키를 확인합니다.",
      "카카오쇼핑 판매자 센터에서 판매자 Key를 확인합니다.",
      "마켓관리에서 마켓을 카카오톡스토어로 고르고 두 키를 넣습니다.",
      "저장한 뒤 연동 테스트를 누릅니다.",
    ],
    fields: [
      ["Admin/API Key", "market:kakao:api_key"],
      ["판매자 Key", "market:kakao:api_secret"],
    ],
  },
  ssg: {
    title: "SSG.COM 설정",
    intro: "SSG 파트너오피스에서 발급한 인증키와 시크릿키를 마켓관리에 넣습니다.",
    links: [
      ["SSG 파트너오피스", "https://po.ssg.com"],
    ],
    steps: [
      "SSG 파트너오피스에서 API 인증키를 확인합니다.",
      "마켓관리에서 마켓을 SSG.COM으로 고르고 인증키와 시크릿키를 넣습니다.",
      "저장한 뒤 연동 테스트를 누릅니다.",
    ],
    fields: [
      ["인증키", "market:ssg:api_key"],
      ["시크릿키", "market:ssg:api_secret"],
    ],
  },
  temu: {
    title: "테무 설정",
    intro: "테무는 판매자 아이디로 계정을 저장합니다.",
    links: [
      ["테무 셀러 센터", "https://seller.temu.com"],
    ],
    steps: [
      "테무 셀러 센터의 판매자 아이디를 확인합니다.",
      "마켓관리에서 마켓을 테무로 고르고 스토어명과 아이디를 넣습니다.",
      "저장한 뒤 연동 테스트를 누릅니다.",
    ],
    fields: [
      ["마켓관리 아이디", "market:temu:login_id"],
      ["마켓관리 패스워드", "market:temu:login_password"],
    ],
  },
  gemini: {
    title: "AI 설정",
    intro: "상품명, 태그, 속성 AI 가공에 쓸 서비스를 Gemini, ChatGPT, Claude 중에서 고릅니다. 고른 서비스의 키만 사용합니다.",
    links: [
      ["Gemini API 키 발급", "https://aistudio.google.com/apikey"],
      ["ChatGPT API 키 발급", "https://platform.openai.com/api-keys"],
      ["Claude API 키 발급", "https://console.anthropic.com/settings/keys"],
    ],
    steps: [
      "사용할 AI에서 Gemini, ChatGPT, Claude 중 하나를 고릅니다.",
      "그 서비스에서 API 키를 만들어 해당 칸에 넣습니다.",
      "모델은 기본값이 들어 있습니다. 다른 모델을 쓰려면 모델명만 바꿉니다.",
      "API 저장 후 연결 테스트를 누릅니다.",
    ],
    fields: [
      ["사용할 AI", "api:ai_provider"],
      ["Gemini API 키", "api:gemini_api_key"],
      ["Gemini 모델", "api:gemini_model"],
      ["ChatGPT API 키", "api:openai_api_key"],
      ["ChatGPT 모델", "api:openai_model"],
      ["Claude API 키", "api:anthropic_api_key"],
      ["Claude 모델", "api:anthropic_model"],
    ],
  },
  searchad: {
    title: "네이버 검색광고 API",
    intro: "상품명을 만들 때 네이버 월간 검색수와 경쟁강도를 가져오는 키입니다. 검색광고 계정이 있으면 무료로 발급됩니다.",
    links: [
      ["검색광고 API 관리", "https://manage.searchad.naver.com/customers/api"],
    ],
    steps: [
      "네이버 검색광고(searchad.naver.com)에 로그인합니다.",
      "도구 → API 사용 관리에서 API 라이선스를 발급합니다.",
      "CUSTOMER_ID, 액세스라이선스, 비밀키를 각 칸에 넣습니다.",
      "API 저장 후 연결 테스트를 누릅니다.",
    ],
    fields: [
      ["CUSTOMER_ID", "api:searchad_customer_id"],
      ["액세스라이선스", "api:searchad_access_license"],
      ["비밀키", "api:searchad_secret_key"],
    ],
  },
};

function renderSetupHelp(id) {
  const help = SETUP_HELPS[id];
  if (!help) return false;
  $("#setupHelpTitle").textContent = help.title;
  const body = $("#setupHelpBody");
  body.innerHTML = "";
  const intro = document.createElement("p");
  intro.textContent = help.intro;
  body.append(intro);

  const linkTitle = document.createElement("h4");
  linkTitle.textContent = "발급 화면";
  const linkList = document.createElement("ul");
  linkList.className = "setup-help-links";
  help.links.forEach(([label, href]) => {
    const item = document.createElement("li");
    const anchor = document.createElement("a");
    anchor.href = href;
    anchor.target = "_blank";
    anchor.rel = "noopener noreferrer";
    anchor.textContent = label;
    item.append(anchor);
    linkList.append(item);
  });

  const stepTitle = document.createElement("h4");
  stepTitle.textContent = "설정 순서";
  const steps = document.createElement("ol");
  help.steps.forEach((text) => {
    const item = document.createElement("li");
    item.textContent = text;
    steps.append(item);
  });

  const fieldTitle = document.createElement("h4");
  fieldTitle.textContent = "이 프로그램에서 넣을 곳";
  const fields = document.createElement("ul");
  fields.className = "setup-field-list";
  help.fields.forEach(([label, target]) => {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.setupTarget = target;
    button.textContent = label;
    item.append(button);
    fields.append(item);
  });
  body.append(linkTitle, linkList, stepTitle, steps, fieldTitle, fields);
  return true;
}

function openSetupHelp(id) {
  if (!renderSetupHelp(id)) {
    toast("이 마켓의 설정 도움말이 없습니다.", true);
    return;
  }
  $("#setupHelpDialog").showModal();
}

function focusSetupField() {
  if (!setupFocus) return;
  const { kind, field } = setupFocus;
  setupFocus = null;
  const form = kind === "market" ? $("#marketForm") : $("#settingsForm");
  if (kind === "api" && $("#aiProvider")) {
    if (field.startsWith("openai_")) $("#aiProvider").value = "openai";
    else if (field.startsWith("anthropic_")) $("#aiProvider").value = "claude";
    else if (field.startsWith("gemini_")) $("#aiProvider").value = "gemini";
    syncAiProviderFields();
  }
  const input = form?.elements?.[field];
  const card = input?.closest(".settings-card") || input?.closest(".delivery-row");
  card?.scrollIntoView({ block: "center" });
  input?.focus();
  card?.classList.add("setup-flash");
  setTimeout(() => card?.classList.remove("setup-flash"), 1600);
  setupChannel = "";
}

function goToSetupTarget(spec) {
  const parts = String(spec || "").split(":");
  const kind = parts[0] === "market" ? "market" : "api";
  const channel = kind === "market" ? parts[1] : "";
  const field = kind === "market" ? parts[2] : parts[1];
  if (!field) return;
  $("#setupHelpDialog")?.close();
  setupFocus = { kind, field };
  setupChannel = kind === "market" ? (channel || "smartstore") : "";
  showAppView("settings");
  if (setupChannel) pendingMarketChannel = setupChannel;
  showSettingsPane(kind === "market" ? "markets" : "api");
}

function showSettingsPane(name) {
  if (name === "accounts") name = "markets";
  $("#settingsForm").hidden = name !== "api";
  $("#settingsPaneApi").hidden = name !== "api";
  const licensePane = $("#settingsPaneLicense");
  if (licensePane) licensePane.hidden = name !== "license";
  $("#marketForm").hidden = name !== "markets";
  $("#settingsTabApi").classList.toggle("active", name === "api");
  $("#settingsTabLicense")?.classList.toggle("active", name === "license");
  $("#settingsTabMarkets").classList.toggle("active", name === "markets");
  if (name === "license") {
    refreshLicenseStatus().catch((error) => toast(error.message, true));
    return;
  }
  if (name === "markets") {
    marketFormIsNew = false;
    loadMarkets().then(() => {
      if (pendingMarketChannel || setupChannel) {
        fillMarketForm({ channel: pendingMarketChannel || setupChannel });
      } else {
        const chosen =
          markets.find((item) => item.id === currentMarketId)
          || markets.find((item) => item.is_default)
          || markets[0];
        if (chosen) fillMarketForm(chosen);
        else {
          fillMarketChannelSelect("smartstore");
          syncMarketFormFields();
          fillMarketTable();
        }
      }
      if ($("#marketMessage")) {
        $("#marketMessage").textContent = markets.length
          ? `등록된 마켓 ${markets.length.toLocaleString("ko-KR")}개 · 위 목록에서 고르세요.`
          : "등록된 마켓이 없습니다. 아래에서 새 마켓을 저장하세요.";
      }
      focusSetupField();
    }).catch((error) => toast(error.message, true));
    return;
  }
  focusSetupField();
}

async function refreshLicenseStatus() {
  const box = $("#licenseStatusText");
  const list = $("#licenseDeviceList");
  if (!box) return null;
  const data = await api("/api/license");
  const used = data.devices_used ?? 0;
  const max = data.max_devices ?? 5;
  const parts = [
    data.active ? "등록됨 · 이용 중" : data.expired ? "기간 만료" : data.has_key ? "이 PC에 키가 묶여 있지 않음" : "이용 키 없음",
    `PC ${used}/${max}대`,
  ];
  if (data.expires_at) parts.push(`만료 ${data.expires_at}`);
  if (data.plan) parts.push(data.plan);
  if (data.current_device_name) parts.push(`이 PC: ${data.current_device_name}`);
  box.textContent = parts.join(" · ");
  if (list) {
    list.innerHTML = "";
    (data.devices || []).forEach((device) => {
      const li = document.createElement("li");
      li.textContent = `${device.name || device.id || "PC"}${device.current ? " (이 PC)" : ""}`;
      list.appendChild(li);
    });
  }
  return data;
}

async function activateLicenseKey() {
  const input = $("#licenseKeyInput");
  const key = String(input?.value || "").trim();
  if (!key) {
    toast("이용 키를 입력해 주세요.", true);
    return;
  }
  try {
    const data = await api("/api/license/activate", { method: "POST", body: JSON.stringify({ key }) });
    const max = data?.max_devices ?? 5;
    toast(`이용 키가 등록되었습니다. PC ${max}대까지 사용할 수 있습니다.`);
    if (input) input.value = "";
    await refreshLicenseStatus();
  } catch (error) {
    toast(error.message || "키 등록에 실패했습니다.", true);
  }
}

async function clearLicenseKey() {
  if (!window.confirm("이 PC에서 이용 키 등록을 해제할까요?")) return;
  try {
    await api("/api/license/clear", { method: "POST", body: "{}" });
    toast("이 PC에서 이용 키를 해제했습니다.");
    await refreshLicenseStatus();
  } catch (error) {
    toast(error.message || "해제에 실패했습니다.", true);
  }
}

async function loadSettingsView() {
  await Promise.all([loadSettingsForm(), loadMarkets(), loadWholesalers()]);
}

async function loginSmartstore(marketId) {
  const result = await api("/api/chrome/login", {
    method: "POST",
    body: JSON.stringify({ market_id: marketId || "" }),
  });
  toast(result.message || "판매자 로그인을 열었습니다.");
  return result;
}

function fillWholesalerSelects() {
  const orderSelect = $("#orderWholesaler");
  if (orderSelect) {
    const currentValue = currentWholesalerId || orderSelect.value;
    orderSelect.innerHTML = "";
    wholesalers
      .filter((item) => item.enabled !== false && item.type !== "ownerclan")
      .slice()
      .sort((a, b) => String(a.name || a.url || "").localeCompare(String(b.name || b.url || ""), "ko"))
      .forEach((item) => {
      const option = document.createElement("option");
      option.value = item.id;
      option.textContent = item.name || item.url || item.id;
      orderSelect.appendChild(option);
    });
    if (currentValue && [...orderSelect.options].some((item) => item.value === currentValue)) {
      orderSelect.value = currentValue;
    }
  }
  fillProductFilter();
}

function marketIcon(channel) {
  const icon = document.createElement("span");
  icon.className = "market-icon";
  icon.style.background = channel.color || "#666";
  icon.style.color = channel.text || "#fff";
  icon.textContent = channel.icon || "";
  return icon;
}

function sourceIcon() {
  const icon = document.createElement("span");
  icon.className = "market-icon";
  icon.innerHTML = `<svg viewBox="0 0 16 16" aria-hidden="true"><rect width="16" height="16" rx="3" fill="#20b038"/><path d="M4.2 6.2h7.6l-.7 5.2H4.9L4.2 6.2zm1.1-1.7c0-.9.7-1.6 1.6-1.6h2.2c.9 0 1.6.7 1.6 1.6v.4H5.3v-.4z" fill="#fff"/></svg>`;
  return icon;
}

function marketCaret(expanded, toggle) {
  const caret = document.createElement("span");
  caret.className = "market-caret";
  caret.dataset.toggle = toggle;
  caret.textContent = expanded ? "▼" : "▶";
  return caret;
}

function marketSpacer() {
  const spacer = document.createElement("span");
  spacer.className = "market-caret";
  return spacer;
}

function marketButton({ depth, label, filter, marketId, kind, active, disabled, caret, icon, channel, count }) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `market-item depth-${depth}`;
  button.dataset.filter = filter || "";
  button.dataset.kind = kind || "";
  if (marketId) button.dataset.marketId = marketId;
  if (channel) button.dataset.channel = channel;
  if (active) button.classList.add("active");
  if (disabled) button.classList.add("disabled");
  const name = document.createElement("span");
  name.className = "market-item-label";
  name.textContent = label;
  button.append(caret || marketSpacer(), icon, name);
  if (count != null) {
    const badge = document.createElement("span");
    badge.className = "market-count";
    badge.textContent = `(${Number(count).toLocaleString("ko-KR")})`;
    button.append(badge);
  }
  button.title = count != null ? `${label}(${Number(count).toLocaleString("ko-KR")})` : label;
  return button;
}

function placeMasterFlyout(host) {
  const panel = host.querySelector(".market-flyout-panel");
  if (!panel) return;
  const rect = host.getBoundingClientRect();
  panel.style.left = `${Math.round(rect.right - 6)}px`;
  const previous = panel.style.display;
  panel.style.display = "block";
  const height = panel.offsetHeight;
  const top = Math.max(8, Math.min(rect.top, window.innerHeight - height - 8));
  panel.style.top = `${Math.round(top)}px`;
  panel.style.display = previous;
}

function masterFlyout(channel, masterCount) {
  const host = document.createElement("div");
  host.className = "market-flyout";
  const button = marketButton({
    depth: 1,
    label: channel.name,
    filter: "master",
    kind: "master",
    active: marketFilter === "master",
    icon: marketIcon(channel),
    count: masterCount,
  });
  const arrow = document.createElement("span");
  arrow.className = "market-caret";
  arrow.textContent = "▶";
  button.append(arrow);
  const panel = document.createElement("div");
  panel.className = "market-flyout-panel";
  panel.append(marketButton({
    depth: 0,
    label: "전체",
    filter: "master",
    kind: "master-all",
    active: marketFilter === "master" && !masterChannelFilter,
    icon: marketIcon({ icon: "전", color: "#6b7280" }),
    count: masterCount,
  }));
  accountChannels().forEach((market) => {
    panel.append(marketButton({
      depth: 0,
      label: market.name,
      filter: "master",
      kind: "master-channel",
      channel: market.id,
      active: marketFilter === "master" && masterChannelFilter === market.id,
      icon: marketIcon(market),
      count: masterIdsInChannel(market.id).size,
    }));
  });
  host.append(button, panel);
  host.addEventListener("mouseenter", () => placeMasterFlyout(host));
  host.addEventListener("focusin", () => placeMasterFlyout(host));
  return host;
}

function fillMarketTree() {
  const tree = $("#marketTree");
  if (!tree) return;
  const channelIds = accountChannels().map((item) => item.id);
  if (
    marketFilter !== "all"
    && marketFilter !== "master"
    && !channelIds.includes(marketFilter)
    && !markets.some((item) => item.id === marketFilter)
  ) {
    marketFilter = "master";
  }
  if (masterChannelFilter && !accountChannels().some((item) => item.id === masterChannelFilter)) {
    masterChannelFilter = "";
  }
  const masterCount = products.filter(isMasterProduct).length;
  tree.innerHTML = "";
  tree.append(marketButton({
    depth: 0,
    label: "원본상품",
    filter: "all",
    kind: "source",
    active: marketFilter === "all",
    caret: marketCaret(sourceExpanded, "source"),
    icon: sourceIcon(),
    count: products.length,
  }));
  if (!sourceExpanded) {
    refreshProductStatusUi();
    return;
  }
  MARKET_CHANNELS.forEach((channel) => {
    if (channel.id === "master") {
      tree.append(masterFlyout(channel, masterCount));
      return;
    }
    const rows = marketsForChannel(channel.id);
    const expanded = isChannelExpanded(channel.id);
    tree.append(marketButton({
      depth: 1,
      label: channel.name,
      filter: channel.id,
      kind: "channel",
      channel: channel.id,
      active: marketFilter === channel.id,
      caret: marketCaret(expanded, channel.id),
      icon: marketIcon(channel),
      count: channelProductCount(channel.id),
    }));
    if (!expanded) return;
    if (!rows.length) {
      tree.append(marketButton({
        depth: 2,
        label: "마켓을 등록하세요",
        kind: "empty",
        channel: channel.id,
        icon: marketIcon({ icon: "+", color: "#555" }),
      }));
      return;
    }
    rows.forEach((item) => {
      const name = item.name || item.slug || item.url || item.login_id || item.id;
      tree.append(marketButton({
        depth: 2,
        label: name,
        filter: item.id,
        marketId: item.id,
        kind: "store",
        channel: channel.id,
        active: marketFilter === item.id,
        icon: marketIcon(channel),
        count: products.filter((product) => product.market_id === item.id).length,
      }));
    });
  });
  fillOrderMarketTree();
  applyProductMenu();
  refreshProductStatusUi();
}

function fillMarketFilter() {
  fillMarketTree();
}

function showMasterProducts() {
  marketFilter = "master";
  masterChannelFilter = "";
  sourceExpanded = true;
  fillMarketTree();
}

function fillProductFilter() {
  fillMarketFilter();
  const select = $("#productWholesalerFilter");
  if (!select) return;
  const currentValue = productFilter || "all";
  select.innerHTML = "";
  const supplierOptions = wholesalers
    .map((item) => [item.id, item.name || item.url || item.id])
    .sort((a, b) => String(a[1]).localeCompare(String(b[1]), "ko"));
  [["all", "전체"], ["url", "URL수집"]].concat(supplierOptions).forEach(([value, label]) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    option.selected = value === currentValue;
    select.appendChild(option);
  });
  if (![...select.options].some((item) => item.value === currentValue)) select.value = "all";
  productFilter = select.value || "all";
  updateFilterCount();
}

function refreshVisibleSelection() {
  selectedIds = new Set([...selectedIds].filter((id) => visibleProducts().some((item) => item.id === id)));
  if (current && !visibleProducts().some((item) => item.id === current.id)) {
    current = visibleProducts().slice(-1)[0] || null;
    if (current) selectedIds.add(current.id);
  }
  renderSheets();
  fillPreview();
  updateSelectionText();
  updateFilterCount();
}

function updateFilterCount() {
  refreshProductStatusUi();
  const el = $("#productFilterCount");
  if (!el) return;
  const shown = visibleProducts().length;
  const all = products.length;
  const parts = [];
  if (marketFilter !== "all") parts.push(marketFilterLabel());
  if (productFilter !== "all") parts.push($("#productWholesalerFilter")?.selectedOptions?.[0]?.textContent || "공급처");
  if (productStatusFilter === "registered") parts.push("등록");
  else if (productStatusFilter === "waiting") parts.push("대기");
  else if (productStatusFilter === "error") parts.push("오류");
  if (productQuery.trim()) {
    const field = productSearchField === "all" ? "검색" : `${productSearchFieldLabel()} 검색`;
    parts.push(`${field} ${productQuery.trim()}`);
  }
  el.textContent = parts.length ? `${parts.join(" / ")} ${shown}개 / 전체 ${all}개` : `전체 ${all}개`;
}

function openWholesalerProducts() {
  const id = selectedWholesalerId();
  if (!id) {
    toast("공급처를 먼저 선택해 주세요.", true);
    return;
  }
  productFilter = id;
  currentWholesalerId = id;
  showMasterProducts();
  fillProductFilter();
  showAppView("products");
  renderSheets();
  fillPreview();
  updateSelectionText();
  updateFilterCount();
  const item = wholesalers.find((row) => row.id === id);
  log(`${item?.name || "공급처"} 상품 ${wholesaleProductCount(id)}개를 상품관리에서 보여 줍니다.`);
}

let ownerclanGroups = [];
let ownerclanSelected = new Set();
let ownerclanParent = "";
let ownerclanDetail = null;
let ownerclanViewCode = "";
let ownerclanProducts = [];
let ownerclanPage = 1;
let ownerclanPages = 1;
const ownerclanCache = new Map();
const ownerclanNames = new Map();

function ownerclanCountText(count) {
  const value = Number(count || 0);
  return value ? value.toLocaleString("ko-KR") : "";
}

function rememberOwnerclan(detail) {
  (detail?.title || []).forEach((item) => ownerclanNames.set(String(item.code), item.name));
  (detail?.children || []).forEach((item) => ownerclanNames.set(String(item.code), item.name));
}

function updateOwnerclanSelected() {
  const line = $("#ownerclanSelected");
  if (!line) return;
  const names = [...ownerclanSelected].map((code) => ownerclanNames.get(code)).filter(Boolean);
  const shown = names.slice(0, 8).join(", ");
  const more = names.length > 8 ? ` 외 ${names.length - 8}개` : "";
  line.textContent = ownerclanSelected.size
    ? `선택한 하위 카테고리 ${ownerclanSelected.size}개: ${shown}${more}`
    : "선택한 하위 카테고리가 없습니다.";
}

function renderOwnerclanCategories() {
  const box = $("#ownerclanCategoryList");
  if (!box) return;
  const parentScroll = box.querySelector(".ownerclan-parents-scroll")?.scrollTop || 0;
  const detailScroll = box.querySelector(".ownerclan-detail")?.scrollTop || 0;
  box.textContent = "";
  if (!ownerclanGroups.length) {
    box.className = "ownerclan-empty";
    box.textContent = "대분류를 누르면 하위 분류가 나옵니다.";
    updateOwnerclanSelected();
    return;
  }
  box.className = "ownerclan-menu";
  if (!ownerclanGroups.some((group) => group.code === ownerclanParent)) {
    ownerclanParent = ownerclanGroups[0].code;
  }
  const parents = document.createElement("div");
  parents.className = "ownerclan-parents";
  const parentsScroll = document.createElement("div");
  parentsScroll.className = "ownerclan-parents-scroll";
  const detailBox = document.createElement("div");
  detailBox.className = "ownerclan-detail";
  ownerclanGroups.forEach((group) => {
    const button = document.createElement("button");
    button.type = "button";
    const active = group.code === ownerclanParent;
    button.className = `ownerclan-parent${active ? " active" : ""}`;
    const name = document.createElement("span");
    name.textContent = group.name;
    button.append(name);
    if (active) {
      const mark = document.createElement("span");
      mark.textContent = ">";
      button.append(mark);
    }
    button.addEventListener("click", () => {
      openOwnerclanCategory(group.code).catch((error) => toast(error.message, true));
    });
    parentsScroll.append(button);
  });
  parents.append(parentsScroll);
  const title = ownerclanDetail?.title || [];
  const children = ownerclanDetail?.children || [];
  if (!ownerclanDetail) {
    detailBox.textContent = "분류를 불러오는 중입니다.";
  } else {
    const crumb = document.createElement("div");
    crumb.className = "ownerclan-crumb";
    title.forEach((item, index) => {
      if (index) {
        const sep = document.createElement("span");
        sep.className = "ownerclan-sep";
        sep.textContent = ">";
        crumb.append(sep);
      }
      const crumbButton = document.createElement("button");
      crumbButton.type = "button";
      crumbButton.className = "ownerclan-crumb-item";
      crumbButton.textContent = item.name;
      crumbButton.addEventListener("click", () => {
        openOwnerclanCategory(item.code).catch((error) => toast(error.message, true));
      });
      crumb.append(crumbButton);
    });
    const grid = document.createElement("div");
    grid.className = "ownerclan-grid";
    children.forEach((child) => {
      const button = document.createElement("button");
      button.type = "button";
      const picked = ownerclanSelected.has(String(child.code));
      const viewing = ownerclanViewCode === String(child.code);
      button.className = `ownerclan-child${picked ? " picked" : ""}${viewing ? " viewing" : ""}`;
      const label = document.createElement("span");
      label.textContent = child.name;
      button.append(label);
      const count = ownerclanCountText(child.count);
      if (count) {
        const countNode = document.createElement("span");
        countNode.className = "count";
        countNode.textContent = `(${count})`;
        button.append(countNode);
      }
      button.addEventListener("click", () => {
        openOwnerclanCategory(child.code).catch((error) => toast(error.message, true));
      });
      grid.append(button);
    });
    detailBox.append(crumb, grid);
  }
  box.append(parents, detailBox);
  parentsScroll.scrollTop = parentScroll;
  detailBox.scrollTop = detailScroll;
  updateOwnerclanSelected();
}

async function openOwnerclanCategory(code) {
  const key = String(code || "");
  let detail = ownerclanCache.get(key);
  if (!detail) {
    detail = await api(`/api/ownerclan/category/${encodeURIComponent(key)}`);
    ownerclanCache.set(key, detail);
  }
  rememberOwnerclan(detail);
  if (!(detail.children || []).length) {
    const name = detail.title?.at?.(-1)?.name || ownerclanNames.get(key) || key;
    ownerclanViewCode = key;
    renderOwnerclanCategories();
    if ($("#ownerclanSearchKeyword")) $("#ownerclanSearchKeyword").value = "";
    await loadOwnerclanProducts({ category: key, title: name });
    return;
  }
  ownerclanDetail = detail;
  const top = String(detail.title?.[0]?.code || key);
  if (ownerclanGroups.some((group) => group.code === top)) ownerclanParent = top;
  renderOwnerclanCategories();
}

async function reloadOwnerclanCategories() {
  const data = await api("/api/ownerclan/categories");
  ownerclanGroups = data.groups || [];
  ownerclanCache.clear();
  ownerclanDetail = null;
  const code = ownerclanParent || ownerclanGroups[0]?.code || "";
  renderOwnerclanCategories();
  if (code) await openOwnerclanCategory(code);
}

async function loadOwnerclan() {
  const data = await api("/api/ownerclan");
  if ($("#ownerclanExcluded")) $("#ownerclanExcluded").value = (data.excluded_suppliers || []).join(", ");
  if (data.search_filters?.remember) applyOwnerclanFilters(data.search_filters);
  if ($("#ownerclanFilterSave")) $("#ownerclanFilterSave").checked = Boolean(data.search_filters?.remember);
  renderOwnerclanPager();
  ownerclanSelected = new Set(data.categories || []);
  renderOwnerclanCategories();
  if (!ownerclanGroups.length) await reloadOwnerclanCategories();
  else if (!ownerclanDetail && ownerclanGroups[0]) await openOwnerclanCategory(ownerclanParent || ownerclanGroups[0].code);
}

async function saveOwnerclanExcluded() {
  const codes = ($("#ownerclanExcluded")?.value || "").split(/[\s,]+/).map((item) => item.trim()).filter(Boolean);
  const saved = await api("/api/ownerclan", { method: "PUT", body: JSON.stringify({ excluded_suppliers: codes }) });
  if ($("#ownerclanExcluded")) $("#ownerclanExcluded").value = (saved.excluded_suppliers || []).join(", ");
  toast(`제외 공급사코드 ${(saved.excluded_suppliers || []).length}개를 저장했습니다.`);
}

let ownerclanProductTitle = "";
let ownerclanExcludedCount = 0;
let ownerclanProductQuery = {};
let ownerclanLoadToken = 0;

function ownerclanChecked(name, fallback = "0") {
  return document.querySelector(`input[name="${name}"]:checked`)?.value || fallback;
}

function collectOwnerclanFilters() {
  return {
    tax_type: ownerclanChecked("ocTax"),
    origin: ownerclanChecked("ocOrigin"),
    deli_type: ownerclanChecked("ocDeli"),
    sale_type: ownerclanChecked("ocSale"),
    return_available: ownerclanChecked("ocReturn"),
    return_type: ownerclanChecked("ocReturnType"),
    min_price: ($("#ownerclanMinPrice")?.value || "").replace(/\D/g, ""),
    max_price: ($("#ownerclanMaxPrice")?.value || "").replace(/\D/g, ""),
    research_mode: $("#ownerclanResearchMode")?.value || "and",
    research: $("#ownerclanResearch")?.value.trim() || "",
    rank_type: document.querySelector(".ownerclan-rank.active")?.dataset.rank || "lowPrice",
  };
}

function applyOwnerclanFilters(filters) {
  const data = filters || {};
  const setRadio = (name, value) => {
    const box = document.querySelector(`input[name="${name}"][value="${value || "0"}"]`);
    if (box) box.checked = true;
  };
  setRadio("ocTax", data.tax_type);
  setRadio("ocOrigin", data.origin || "1");
  setRadio("ocDeli", data.deli_type);
  setRadio("ocSale", data.sale_type);
  setRadio("ocReturn", data.return_available);
  setRadio("ocReturnType", data.return_type);
  if ($("#ownerclanMinPrice")) $("#ownerclanMinPrice").value = data.min_price || "";
  if ($("#ownerclanMaxPrice")) $("#ownerclanMaxPrice").value = data.max_price || "";
  if ($("#ownerclanResearchMode")) $("#ownerclanResearchMode").value = data.research_mode || "and";
  if ($("#ownerclanResearch")) $("#ownerclanResearch").value = data.research || "";
  const rank = data.rank_type || "lowPrice";
  document.querySelectorAll(".ownerclan-rank").forEach((button) => button.classList.toggle("active", button.dataset.rank === rank));
}

function searchOwnerclanWithFilters() {
  const query = { ...ownerclanProductQuery, page: 1 };
  query.search_type = $("#ownerclanSearchType")?.value || "all";
  query.keyword = $("#ownerclanSearchKeyword")?.value.trim() || "";
  query.product_code = "";
  query.supplier_code = "";
  if (query.keyword) {
    query.category = "";
  } else {
    query.search_type = "";
    if (!query.category && ownerclanViewCode) query.category = ownerclanViewCode;
  }
  if (!query.category && !query.keyword) {
    return Promise.reject(new Error("검색어를 입력하거나 소분류를 눌러 주세요."));
  }
  const run = loadOwnerclanProducts(query);
  if (!$("#ownerclanFilterSave")?.checked) return run;
  return run.then((value) => saveOwnerclanFilters(true, true).then(() => value));
}

async function saveOwnerclanFilters(remember, quiet = false) {
  const filters = remember ? { ...collectOwnerclanFilters(), remember: true } : { remember: false };
  const saved = await api("/api/ownerclan", { method: "PUT", body: JSON.stringify({ search_filters: filters }) });
  if ($("#ownerclanFilterSave")) $("#ownerclanFilterSave").checked = Boolean(saved.search_filters?.remember);
  if (!quiet) toast(remember ? "검색조건을 저장했습니다." : "검색조건 저장을 해제했습니다.");
  return saved;
}

function updateOwnerclanProductStatus() {
  const line = $("#ownerclanProductStatus");
  if (!line) return;
  if (!ownerclanProducts.length) {
    line.textContent = ownerclanExcludedCount ? `제외 ${ownerclanExcludedCount}개` : "";
    return;
  }
  const collected = ownerclanCollectedCodes();
  const total = ownerclanProducts.length;
  const fresh = ownerclanProducts.filter((item) => !collected.has(String(item.code || "").trim())).length;
  const checked = document.querySelectorAll("#ownerclanProductList input:checked").length;
  const head = ownerclanProductTitle ? `${ownerclanProductTitle} ` : "";
  const extra = ownerclanExcludedCount ? ` · 제외 ${ownerclanExcludedCount}개` : "";
  line.textContent = `${head}${ownerclanPage}페이지 · 안담은 ${fresh.toLocaleString("ko-KR")}개 / 전체 ${total.toLocaleString("ko-KR")}개 · 선택 ${checked}개${extra}`;
}

function renderOwnerclanPager() {
  const box = $("#ownerclanPageNumbers");
  const prev = $("#ownerclanPrev");
  const next = $("#ownerclanNext");
  const total = Math.max(1, Number(ownerclanPages) || 1);
  const current = Math.min(Math.max(1, Number(ownerclanPage) || 1), total);
  if (prev) prev.disabled = current <= 1;
  if (next) next.disabled = current >= total;
  if (!box) return;
  box.textContent = "";
  const size = 10;
  const start = Math.floor((current - 1) / size) * size + 1;
  const end = Math.min(total, start + size - 1);
  const addPage = (label, page) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "ownerclan-page-num";
    button.textContent = label;
    if (label !== ".." && page === current) {
      button.classList.add("active");
      button.disabled = true;
    }
    button.addEventListener("click", () => {
      if (page === ownerclanPage) return;
      loadOwnerclanProducts({ ...ownerclanProductQuery, page }).catch((error) => toast(error.message, true));
    });
    box.append(button);
  };
  if (start > 1) addPage("..", start - 1);
  for (let page = start; page <= end; page += 1) addPage(String(page), page);
  if (end < total) addPage("..", end + 1);
}

function allowOwnerclanTextSelect(node, input) {
  let startX = 0;
  let startY = 0;
  let startChecked = false;
  node.addEventListener("mousedown", (event) => {
    if (event.button !== 0 || event.detail !== 1) return;
    startX = event.clientX;
    startY = event.clientY;
    startChecked = input.checked;
  });
  node.addEventListener("click", (event) => {
    const moved = Math.abs(event.clientX - startX) > 3 || Math.abs(event.clientY - startY) > 3;
    const selected = window.getSelection()?.toString();
    if (event.detail === 1 && !moved && !selected) return;
    event.preventDefault();
    event.stopPropagation();
    if (input.checked !== startChecked) {
      input.checked = startChecked;
      input.dispatchEvent(new Event("change"));
    }
  });
}

function ownerclanShippingText(item) {
  const type = String(item?.shipping_type || "").toUpperCase();
  const fee = Number(item?.shipping || 0);
  if (type === "F" || (type !== "C" && fee <= 0)) return "무료";
  const amount = `${fee.toLocaleString("ko-KR")}원`;
  if (type === "C") return fee ? `착불 ${amount}` : "착불";
  return `배송 ${amount}`;
}

function renderOwnerclanProducts() {
  const box = $("#ownerclanProductList");
  if (!box) return;
  box.textContent = "";
  if (!ownerclanProducts.length) {
    const empty = document.createElement("p");
    empty.className = "ownerclan-product-empty";
    empty.textContent = ownerclanExcludedCount
      ? "제외 공급사 상품은 검색 결과에서 뺐습니다."
      : "소분류를 누르거나 상품코드, 공급사코드를 검색하면 상품이 나옵니다.";
    box.append(empty);
    updateOwnerclanProductStatus();
    return;
  }
  const collected = ownerclanCollectedCodes();
  const onlyNew = $("#ownerclanOnlyNew")?.checked === true;
  const visible = onlyNew
    ? ownerclanProducts.filter((item) => !collected.has(String(item.code || "").trim()))
    : ownerclanProducts;
  if (!visible.length) {
    const empty = document.createElement("p");
    empty.className = "ownerclan-product-empty";
    empty.textContent = ownerclanProducts.length && onlyNew
      ? "이 페이지 상품은 모두 이미 담았습니다. ‘안담은 상품만 보기’를 끄면 전체가 보입니다."
      : ownerclanExcludedCount
        ? "제외 공급사 상품은 검색 결과에서 뺐습니다."
        : "소분류를 누르거나 상품코드, 공급사코드를 검색하면 상품이 나옵니다.";
    box.append(empty);
    updateOwnerclanProductStatus();
    renderOwnerclanPager();
    return;
  }
  visible.forEach((item) => {
    const label = document.createElement("label");
    label.className = "ownerclan-product";
    const already = collected.has(String(item.code || "").trim());
    if (already) label.classList.add("is-collected");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = item.code;
    input.dataset.collected = already ? "1" : "0";
    input.checked = !already;
    input.addEventListener("change", updateOwnerclanProductStatus);
    const img = document.createElement("img");
    img.alt = "";
    if (item.image) img.src = item.image;
    const productUrl = String(item.url || "").trim() || (item.code ? `https://www.ownerclan.com/V2/product/view.php?selfcode=${encodeURIComponent(item.code)}` : "");
    const picture = productUrl ? document.createElement("a") : img;
    if (productUrl) {
      picture.href = productUrl;
      picture.rel = "noopener noreferrer";
      picture.title = "오너클랜 상품 보기 (로그인 Chrome)";
      picture.append(img);
      picture.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        const ownerId =
          selectedCollectSupplierId ||
          selectedWholesalerId() ||
          wholesalers.find((row) => row.type === "ownerclan")?.id ||
          "ownerclan";
        openSupplierProductUrl(productUrl, ownerId, "오너클랜 상품 주소가 없습니다.");
      });
    }
    const name = document.createElement("span");
    name.className = "name";
    name.textContent = item.name;
    allowOwnerclanTextSelect(name, input);
    const meta = document.createElement("span");
    meta.className = "meta";
    meta.textContent = `${item.code}${item.supplier ? ` · ${item.supplier}` : ""}`;
    const priceLine = document.createElement("span");
    priceLine.className = "price-line";
    const price = document.createElement("span");
    price.className = "sale";
    price.textContent = `${Number(item.price || 0).toLocaleString("ko-KR")}원`;
    const shipping = document.createElement("span");
    shipping.className = "shipping";
    shipping.textContent = ownerclanShippingText(item);
    priceLine.append(price, shipping);
    allowOwnerclanTextSelect(meta, input);
    allowOwnerclanTextSelect(priceLine, input);
    label.append(input, picture, name, meta, priceLine);
    box.append(label);
  });
  updateOwnerclanProductStatus();
  renderOwnerclanPager();
}

async function loadOwnerclanProducts({ category = "", product_code = "", supplier_code = "", keyword = "", search_type = "", title = "", page = 1 } = {}) {
  const pageNo = Math.max(1, Number(page) || 1);
  const params = new URLSearchParams();
  if (keyword) {
    params.set("keyword", keyword);
    params.set("search_type", search_type || "all");
  } else if (product_code) params.set("product_code", product_code);
  else if (supplier_code) params.set("supplier_code", supplier_code);
  else if (category) params.set("category", category);
  if (![...params.keys()].length) throw new Error("검색어를 입력하거나 소분류를 눌러 주세요.");
  const token = ++ownerclanLoadToken;
  params.set("page", String(pageNo));
  ownerclanProductQuery = { category, product_code, supplier_code, keyword, search_type, title };
  Object.entries(collectOwnerclanFilters()).forEach(([key, value]) => params.set(key, value));
  const line = $("#ownerclanProductStatus");
  if (line) line.textContent = `${pageNo}페이지 상품을 불러오는 중입니다.`;
  if ($("#ownerclanPrev")) $("#ownerclanPrev").disabled = true;
  if ($("#ownerclanNext")) $("#ownerclanNext").disabled = true;
  document.querySelectorAll(".ownerclan-page-num").forEach((button) => {
    button.disabled = true;
  });
  setBusy(true, `${pageNo}페이지 오너클랜 상품을 불러오는 중입니다.`, "ownerclan");
  try {
    const data = await api(`/api/ownerclan/products?${params.toString()}`);
    if (token !== ownerclanLoadToken) return;
    ownerclanProducts = (data.products || []).slice(0, 60);
    ownerclanExcludedCount = Number(data.excluded_count || 0);
    ownerclanPage = Number(data.page || pageNo);
    ownerclanPages = Math.max(ownerclanPage, Number(data.pages || 1));
    const total = $("#ownerclanProductTotal");
    if (total) total.textContent = Number(data.total || 0) ? `총 ${Number(data.total).toLocaleString("ko-KR")}개` : "";
    ownerclanProductTitle = title || (product_code ? "상품코드" : supplier_code ? "공급사코드" : "");
    if (category) ownerclanViewCode = String(category);
    renderOwnerclanCategories();
    renderOwnerclanProducts();
    const list = $("#ownerclanProductList");
    if (list) list.scrollTop = 0;
    log(`${ownerclanPage}페이지 상품 ${ownerclanProducts.length}개를 불러왔습니다.`, "ok");
  } catch (error) {
    if (token !== ownerclanLoadToken) return;
    renderOwnerclanPager();
    if (isAbortError(error)) return;
    throw error;
  } finally {
    if (token === ownerclanLoadToken) setBusy(false, "", "ownerclan");
  }
}

async function sendOwnerclanToProducts() {
  const codes = new Set([...document.querySelectorAll("#ownerclanProductList input:checked")].map((box) => box.value));
  const items = ownerclanProducts.filter((item) => codes.has(item.code));
  if (!items.length) throw new Error("상품관리로 보낼 상품을 선택해 주세요.");
  setBusy(true, `선택한 상품 ${items.length}개를 상품관리로 보내는 중입니다.`, "ownerclan");
  try {
    const result = await api("/api/ownerclan/products/import", { method: "POST", body: JSON.stringify({ items }) });
    const ownerId = wholesalers.find((row) => row.type === "ownerclan")?.id || "ownerclan";
    productFilter = ownerId;
    showMasterProducts();
    await loadProducts();
    fillProductFilter();
    updateFilterCount();
    renderOwnerclanProducts();
    updateOwnerclanProductStatus();
    const kept = result.kept ? `, 이미 있는 상품 ${result.kept}개` : "";
    log(`오너클랜 상품 ${result.added}개를 상품관리로 보냈습니다${kept}.`, "ok");
    toast(`상품관리로 ${result.added}개를 보냈습니다${kept}. 목록을 갱신했습니다.`);
  } catch (error) {
    if (isAbortError(error)) {
      log("작업을 중단했습니다.");
      return;
    }
    throw error;
  } finally {
    setBusy(false, "", "ownerclan");
  }
}

function ownerclanSecondCategoryCode() {
  if (ownerclanProductQuery.keyword) return "";
  const code = String(ownerclanProductQuery.category || "");
  const title = ownerclanCache.get(code)?.title || [];
  if (title.length >= 2 && title[1]?.code) return String(title[1].code);
  return "";
}

async function importLowestOwnerclanProducts() {
  const codes = new Set([...document.querySelectorAll("#ownerclanProductList input:checked")].map((box) => box.value));
  const items = ownerclanProducts.filter((item) => codes.has(item.code));
  if (!items.length) throw new Error("최저가를 찾을 상품을 선택해 주세요.");
  if (items.length > 60) throw new Error("최저가 가져오기는 한 번에 60개까지 선택할 수 있습니다.");
  setBusy(true, `선택한 상품 ${items.length}개의 최저가를 2차 카테고리에서 찾는 중입니다.`, "ownerclan");
  try {
    const result = await api("/api/ownerclan/products/lowest", {
      method: "POST",
      body: JSON.stringify({ items, context: ownerclanProducts, category_code: ownerclanSecondCategoryCode() }),
    });
    const chosen = new Map((result.items || []).map((item) => [item.from_code, item]));
    ownerclanProducts = ownerclanProducts.map((item) => {
      const next = chosen.get(item.code);
      return next ? { ...item, ...next } : item;
    });
    await loadProducts();
    fillProductFilter();
    updateFilterCount();
    renderOwnerclanProducts();
    updateOwnerclanProductStatus();
    const swapped = result.cheaper ? ` 같은 상품 중 더 싼 것 ${result.cheaper}개로 바꿨습니다.` : " 고른 상품이 이미 가장 싼 가격입니다.";
    const kept = result.kept ? ` 이미 있는 상품 ${result.kept}개.` : "";
    log(`오너클랜 최저가 상품 ${result.added}개를 가져왔습니다.${swapped}${kept}`, "ok");
    toast(`최저가 상품 ${result.added}개를 가져왔습니다.${swapped}${kept}`);
  } catch (error) {
    if (isAbortError(error)) {
      log("작업을 중단했습니다.");
      return;
    }
    throw error;
  } finally {
    setBusy(false, "", "ownerclan");
  }
}

let selectedCollectSupplierId = "";

function collectSupplierList() {
  const rows = [...wholesalers];
  rows.sort((a, b) => {
    const aOwner = a.type === "ownerclan" ? 0 : 1;
    const bOwner = b.type === "ownerclan" ? 0 : 1;
    if (aOwner !== bOwner) return aOwner - bOwner;
    return String(a.name || "").localeCompare(String(b.name || ""), "ko");
  });
  return rows;
}

function renderCollectSupplierTree() {
  const tree = $("#collectSupplierTree");
  if (!tree) return;
  tree.replaceChildren();
  const rows = collectSupplierList();
  if (!rows.length) {
    const empty = document.createElement("div");
    empty.className = "collect-supplier-empty";
    empty.textContent = "등록된 공급사가 없습니다. 공급처에서 로그인 정보를 넣으세요.";
    tree.append(empty);
    return;
  }
  rows.forEach((item) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "collect-supplier-item";
    if (item.id === selectedCollectSupplierId) button.classList.add("active");
    if (item.enabled === false) button.classList.add("is-disabled");
    button.dataset.id = item.id;
    button.textContent = item.name || item.type_label || item.type || "공급사";
    button.addEventListener("click", () => {
      selectCollectSupplier(item.id).catch((error) => toast(error.message, true));
    });
    tree.append(button);
  });
}

async function openCollectView() {
  renderCollectSupplierTree();
  const rows = collectSupplierList().filter((item) => item.enabled !== false);
  const preferred =
    rows.find((item) => item.id === selectedCollectSupplierId)
    || rows.find((item) => item.type === "ownerclan")
    || rows[0]
    || collectSupplierList()[0];
  if (preferred) {
    await selectCollectSupplier(preferred.id);
  } else {
    showCollectPane("");
  }
}

function showCollectPane(kind) {
  const empty = $("#collectPaneEmpty");
  const shop = $("#collectPaneCafe24");
  const ownerclan = $("#collectPaneOwnerclan");
  if (empty) empty.hidden = kind !== "";
  // cafe24·고도몰·아임웹·기타는 같은 상품담기(shop) 화면
  if (shop) shop.hidden = kind !== "shop" && kind !== "cafe24";
  if (ownerclan) ownerclan.hidden = kind !== "ownerclan";
}

let cafe24CatalogItems = [];
let cafe24CatalogLoadedFor = "";
let cafe24CatalogLoadedCategory = "";
let cafe24CatalogPath = "";
let cafe24Categories = [];
let cafe24CategoryGroups = [];
let cafe24CategoriesLoadedFor = "";
let cafe24SelectedCategory = "";
let cafe24ParentCategory = "";
let cafe24CatalogPage = 1;
let cafe24CatalogSort = "lowPrice";
let cafe24CatalogLoggedIn = false;
const CAFE24_PAGE_SIZE = 60;
const CAFE24_PREFS_KEY = "collect-cafe24-prefs";

function cafe24ItemPrice(item) {
  const value = Number(item?.price || item?.sale_price || item?.cost || 0);
  return Number.isFinite(value) ? value : 0;
}

function loadCafe24Prefs() {
  let data = {};
  try {
    data = JSON.parse(localStorage.getItem(CAFE24_PREFS_KEY) || "{}") || {};
  } catch (error) {
    data = {};
  }
  cafe24CatalogSort = data.sort === "highPrice" ? "highPrice" : "lowPrice";
  document.querySelectorAll("[data-cafe24-sort]").forEach((button) => {
    button.classList.toggle("active", button.dataset.cafe24Sort === cafe24CatalogSort);
  });
  if ($("#collectCafe24HideSoldout") && typeof data.hideSoldout === "boolean") {
    $("#collectCafe24HideSoldout").checked = data.hideSoldout;
  }
  if ($("#collectCafe24OnlyNew")) {
    $("#collectCafe24OnlyNew").checked = Number(data.v || 0) >= 2 && (data.onlyNew ?? data.checkNew) === true;
  }
}

function saveCafe24Prefs() {
  try {
    localStorage.setItem(CAFE24_PREFS_KEY, JSON.stringify({
      v: 2,
      sort: cafe24CatalogSort,
      hideSoldout: $("#collectCafe24HideSoldout")?.checked !== false,
      onlyNew: $("#collectCafe24OnlyNew")?.checked === true,
    }));
  } catch (error) {
    /* ignore quota */
  }
}

function normalizeCollectUrl(url) {
  return String(url || "").trim().replace(/\/+$/, "").toLowerCase().split("?")[0];
}

function cafe24CollectedKeys(wholesalerId) {
  const nos = new Set();
  const urls = new Set();
  const id = String(wholesalerId || "");
  products.forEach((item) => {
    if (!isMasterProduct(item)) return;
    if (id && productWholesalerId(item) !== id) return;
    const no = String(item.wholesale_product_no || "").trim();
    if (no) nos.add(no);
    const url = normalizeCollectUrl(item.source_url);
    if (url) urls.add(url);
  });
  return { nos, urls };
}

function isCafe24AlreadyCollected(item, keys) {
  const no = String(item?.product_no || "").trim();
  if (no && keys.nos.has(no)) return true;
  const url = normalizeCollectUrl(item?.url);
  return Boolean(url && keys.urls.has(url));
}

function ownerclanCollectedCodes() {
  const codes = new Set();
  products.forEach((item) => {
    if (!isMasterProduct(item)) return;
    if (!isOwnerclanProduct(item)) return;
    const code = String(item.wholesale_product_no || item.model || "").trim();
    if (code) codes.add(code);
  });
  return codes;
}

loadCafe24Prefs();
try {
  if ($("#ownerclanOnlyNew")) {
    const migrated = localStorage.getItem("ownerclan-only-new-v2") === "1";
    if (!migrated) {
      $("#ownerclanOnlyNew").checked = false;
      localStorage.setItem("ownerclan-only-new-v2", "1");
      localStorage.setItem("ownerclan-only-new", "0");
    } else {
      const saved = localStorage.getItem("ownerclan-only-new") ?? localStorage.getItem("ownerclan-check-new");
      $("#ownerclanOnlyNew").checked = saved === "1";
    }
  }
} catch (error) {
  /* ignore */
}

function filteredCafe24Catalog() {
  const q = String($("#collectCafe24Search")?.value || "").trim().toLowerCase();
  const hideSold = $("#collectCafe24HideSoldout")?.checked !== false;
  const onlyNew = $("#collectCafe24OnlyNew")?.checked === true;
  const collected = onlyNew
    ? cafe24CollectedKeys(selectedCollectSupplierId || selectedWholesalerId())
    : null;
  const rows = cafe24CatalogItems.filter((item) => {
    if (hideSold && item.soldout) return false;
    if (collected && isCafe24AlreadyCollected(item, collected)) return false;
    if (!q) return true;
    const hay = `${item.name || ""} ${item.product_no || ""} ${item.source_category || ""}`.toLowerCase();
    return hay.includes(q);
  });
  const high = cafe24CatalogSort === "highPrice";
  return rows.slice().sort((a, b) => {
    const pa = cafe24ItemPrice(a);
    const pb = cafe24ItemPrice(b);
    const aMissing = pa <= 0;
    const bMissing = pb <= 0;
    if (aMissing !== bMissing) return aMissing ? 1 : -1;
    if (pa !== pb) return high ? pb - pa : pa - pb;
    return String(a.name || "").localeCompare(String(b.name || ""), "ko");
  });
}

function setCafe24CatalogSort(sort) {
  cafe24CatalogSort = sort === "highPrice" ? "highPrice" : "lowPrice";
  document.querySelectorAll("[data-cafe24-sort]").forEach((button) => {
    button.classList.toggle("active", button.dataset.cafe24Sort === cafe24CatalogSort);
  });
  cafe24CatalogPage = 1;
  saveCafe24Prefs();
  renderCafe24Catalog();
}

function cafe24CatalogPages() {
  return Math.max(1, Math.ceil(filteredCafe24Catalog().length / CAFE24_PAGE_SIZE) || 1);
}

function updateCafe24CatalogStatus() {
  const line = $("#collectCafe24Status");
  if (!line) return;
  const checked = document.querySelectorAll("#collectCafe24List input:checked").length;
  const filtered = filteredCafe24Catalog().length;
  const total = cafe24CatalogItems.length;
  const collected = cafe24CollectedKeys(selectedCollectSupplierId || selectedWholesalerId());
  const fresh = cafe24CatalogItems.filter((item) => !isCafe24AlreadyCollected(item, collected)).length;
  const parts = [];
  if (cafe24SelectedCategory && cafe24CatalogLoadedCategory === cafe24SelectedCategory) {
    parts.push(`안담은 ${fresh.toLocaleString("ko-KR")}개 / 전체 ${total.toLocaleString("ko-KR")}개`);
  } else if (cafe24SelectedCategory) {
    parts.push("분류 상품을 불러오세요");
  } else {
    parts.push("대분류·소분류를 고르세요");
  }
  if (filtered !== fresh && filtered !== total) {
    parts.push(`표시 ${filtered.toLocaleString("ko-KR")}개`);
  }
  parts.push(`선택 ${checked}개`);
  parts.push(`상품관리 ${wholesaleProductCount(selectedCollectSupplierId).toLocaleString("ko-KR")}개`);
  const priced = cafe24CatalogItems.filter((item) => cafe24ItemPrice(item) > 0).length;
  if (cafe24CatalogItems.length && priced === 0 && !cafe24CatalogLoggedIn) {
    parts.push("가격 비공개 · 공급처 로그인 후 다시 불러오기");
  } else if (cafe24CatalogItems.length && priced < cafe24CatalogItems.length) {
    parts.push(`가격 ${priced.toLocaleString("ko-KR")}개`);
  }
  line.textContent = parts.join(" · ");
  const path = $("#collectCafe24Path");
  if (path) path.textContent = cafe24CatalogPath || "";
}

function renderCafe24Pager() {
  const box = $("#collectCafe24PageNumbers");
  const pages = cafe24CatalogPages();
  cafe24CatalogPage = Math.min(Math.max(1, cafe24CatalogPage), pages);
  if ($("#collectCafe24Prev")) $("#collectCafe24Prev").disabled = cafe24CatalogPage <= 1;
  if ($("#collectCafe24Next")) $("#collectCafe24Next").disabled = cafe24CatalogPage >= pages;
  if (!box) return;
  box.replaceChildren();
  const start = Math.max(1, cafe24CatalogPage - 4);
  const end = Math.min(pages, start + 9);
  for (let page = start; page <= end; page += 1) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "ownerclan-page-num";
    if (page === cafe24CatalogPage) button.classList.add("active");
    button.textContent = String(page);
    button.addEventListener("click", () => {
      cafe24CatalogPage = page;
      renderCafe24Catalog();
    });
    box.append(button);
  }
  const total = $("#collectCafe24Total");
  if (total) total.textContent = pages > 1 ? `${cafe24CatalogPage}/${pages}페이지` : "";
}

function renderCafe24Catalog() {
  const box = $("#collectCafe24List");
  if (!box) return;
  const rows = filteredCafe24Catalog();
  const pages = cafe24CatalogPages();
  cafe24CatalogPage = Math.min(Math.max(1, cafe24CatalogPage), pages);
  const start = (cafe24CatalogPage - 1) * CAFE24_PAGE_SIZE;
  const pageRows = rows.slice(start, start + CAFE24_PAGE_SIZE);
  box.replaceChildren();
  if (!cafe24SelectedCategory) {
    const empty = document.createElement("p");
    empty.className = "ownerclan-product-empty";
    empty.textContent = "위쪽 대분류를 고른 뒤 소분류를 누르면 상품이 나옵니다.";
    box.append(empty);
    updateCafe24CatalogStatus();
    renderCafe24Pager();
    return;
  }
  if (cafe24CatalogLoadedCategory !== cafe24SelectedCategory) {
    const empty = document.createElement("p");
    empty.className = "ownerclan-product-empty";
    empty.textContent = "이 분류 상품을 불러오는 중이거나, 다시 불러오기를 눌러 주세요.";
    box.append(empty);
    updateCafe24CatalogStatus();
    renderCafe24Pager();
    return;
  }
  if (!pageRows.length) {
    const empty = document.createElement("p");
    empty.className = "ownerclan-product-empty";
    const onlyNew = $("#collectCafe24OnlyNew")?.checked === true;
    empty.textContent = rows.length
      ? "이 페이지에 상품이 없습니다."
      : cafe24CatalogItems.length && onlyNew
        ? "이 분류 상품은 모두 이미 담았습니다. ‘안담은 상품만 보기’를 끄면 전체가 보입니다."
        : "이 분류에 상품이 없거나 검색 결과가 없습니다.";
    box.append(empty);
    updateCafe24CatalogStatus();
    renderCafe24Pager();
    return;
  }
  const collected = cafe24CollectedKeys(selectedCollectSupplierId || selectedWholesalerId());
  pageRows.forEach((item) => {
    const label = document.createElement("label");
    label.className = "ownerclan-product";
    if (item.soldout) label.classList.add("is-soldout");
    const already = isCafe24AlreadyCollected(item, collected);
    if (already) label.classList.add("is-collected");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = item.url || "";
    input.dataset.productNo = item.product_no || "";
    input.dataset.collected = already ? "1" : "0";
    input.checked = !already;
    input.addEventListener("change", updateCafe24CatalogStatus);
    const img = document.createElement("img");
    img.alt = "";
    if (item.image) img.src = item.image;
    const productUrl = String(item.url || "").trim();
    const picture = productUrl ? document.createElement("a") : img;
    if (productUrl) {
      picture.href = productUrl;
      picture.rel = "noopener noreferrer";
      picture.title = "공급사 상품 보기 (로그인 Chrome)";
      picture.append(img);
      picture.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        const supplierId = selectedCollectSupplierId || selectedWholesalerId();
        openSupplierProductUrl(productUrl, supplierId, "공급사 상품 주소가 없습니다.");
      });
    }
    const name = document.createElement("span");
    name.className = "name";
    name.textContent = item.name || item.product_no || "상품";
    const meta = document.createElement("span");
    meta.className = "meta";
    meta.textContent = [item.product_no, item.source_category, item.soldout ? "품절" : ""]
      .filter(Boolean)
      .join(" · ");
    const priceLine = document.createElement("span");
    priceLine.className = "price-line";
    const price = document.createElement("span");
    price.className = "sale";
    const amount = cafe24ItemPrice(item);
    price.textContent = amount > 0 ? `${amount.toLocaleString("ko-KR")}원` : "가격 비공개";
    priceLine.append(price);
    label.append(input, picture, name, meta, priceLine);
    box.append(label);
  });
  updateCafe24CatalogStatus();
  renderCafe24Pager();
}

function cafe24ActiveGroup() {
  return cafe24CategoryGroups.find((group) => String(group.id) === String(cafe24ParentCategory))
    || cafe24CategoryGroups[0]
    || null;
}

function renderCafe24Categories() {
  const box = $("#collectCafe24CategoryList");
  if (!box) return;
  const parentScroll = box.querySelector(".ownerclan-parents-scroll")?.scrollTop || 0;
  const detailScroll = box.querySelector(".ownerclan-detail")?.scrollTop || 0;
  box.replaceChildren();
  if (!cafe24CategoryGroups.length) {
    box.className = "ownerclan-empty";
    box.textContent = cafe24CategoriesLoadedFor
      ? "분류를 찾지 못했습니다. 분류 새로고침을 눌러 보세요."
      : "대분류를 불러오는 중입니다.";
    return;
  }
  box.className = "ownerclan-menu";
  if (!cafe24CategoryGroups.some((group) => String(group.id) === String(cafe24ParentCategory))) {
    cafe24ParentCategory = String(cafe24CategoryGroups[0]?.id ?? "");
  }
  const parents = document.createElement("div");
  parents.className = "ownerclan-parents";
  const parentsScroll = document.createElement("div");
  parentsScroll.className = "ownerclan-parents-scroll";
  const detailBox = document.createElement("div");
  detailBox.className = "ownerclan-detail";
  cafe24CategoryGroups.forEach((group) => {
    const button = document.createElement("button");
    button.type = "button";
    const active = String(group.id) === String(cafe24ParentCategory);
    button.className = `ownerclan-parent${active ? " active" : ""}`;
    const name = document.createElement("span");
    name.textContent = group.name || String(group.id || "분류");
    button.append(name);
    if (active) {
      const mark = document.createElement("span");
      mark.textContent = ">";
      button.append(mark);
    }
    button.addEventListener("click", () => {
      openCafe24Group(group.id).catch((error) => toast(error.message, true));
    });
    parentsScroll.append(button);
  });
  parents.append(parentsScroll);
  const group = cafe24ActiveGroup();
  const children = group?.children || [];
  const groupId = String(group?.id ?? "");
  const canLoadGroup = Boolean(groupId) && !["0", "all", "etc"].includes(groupId);
  if (!group) {
    detailBox.textContent = "대분류를 골라 주세요.";
  } else if (!children.length) {
    const hint = document.createElement("div");
    hint.className = "ownerclan-crumb";
    hint.textContent = canLoadGroup
      ? "하위 분류가 없습니다. 이 대분류 상품을 불러옵니다."
      : "소분류를 불러오지 못했습니다. 분류 새로고침을 눌러 보세요.";
    const grid = document.createElement("div");
    grid.className = "ownerclan-grid";
    if (canLoadGroup) {
      const button = document.createElement("button");
      button.type = "button";
      const viewing = String(cafe24SelectedCategory) === groupId;
      button.className = `ownerclan-child${viewing ? " viewing" : ""}`;
      button.append(Object.assign(document.createElement("span"), { textContent: `${group.name || "상품"} 보기` }));
      button.addEventListener("click", () => {
        selectCafe24Category(group.id).catch((error) => toast(error.message, true));
      });
      grid.append(button);
    }
    detailBox.append(hint, grid);
  } else {
    const crumb = document.createElement("div");
    crumb.className = "ownerclan-crumb";
    crumb.textContent = group.name || "분류";
    const grid = document.createElement("div");
    grid.className = "ownerclan-grid";
    if (canLoadGroup) {
      const allBtn = document.createElement("button");
      allBtn.type = "button";
      const allViewing = String(cafe24SelectedCategory) === groupId;
      allBtn.className = `ownerclan-child${allViewing ? " viewing" : ""}`;
      allBtn.append(Object.assign(document.createElement("span"), { textContent: "대분류 전체" }));
      allBtn.addEventListener("click", () => {
        selectCafe24Category(group.id).catch((error) => toast(error.message, true));
      });
      grid.append(allBtn);
    }
    children.forEach((child) => {
      const button = document.createElement("button");
      button.type = "button";
      const viewing = String(cafe24SelectedCategory) === String(child.id);
      button.className = `ownerclan-child${viewing ? " viewing" : ""}`;
      button.append(Object.assign(document.createElement("span"), { textContent: child.name || String(child.id) }));
      button.addEventListener("click", () => {
        selectCafe24Category(child.id).catch((error) => toast(error.message, true));
      });
      grid.append(button);
    });
    detailBox.append(crumb, grid);
  }
  box.append(parents, detailBox);
  parentsScroll.scrollTop = parentScroll;
  detailBox.scrollTop = detailScroll;
}

async function openCafe24Group(groupId) {
  cafe24ParentCategory = String(groupId ?? "");
  renderCafe24Categories();
  const group = cafe24ActiveGroup();
  const children = group?.children || [];
  const gid = String(group?.id ?? "");
  if (gid && !["0", "all", "etc"].includes(gid)) {
    await selectCafe24Category(group.id);
    if (cafe24CatalogItems.length || !children.length) return;
  }
  if (children.length) await selectCafe24Category(children[0].id);
}

async function loadCafe24Categories({ force = false } = {}) {
  const id = selectedCollectSupplierId || selectedWholesalerId();
  if (!id) throw new Error("공급사를 먼저 선택해 주세요.");
  if (!force && cafe24CategoriesLoadedFor === id && cafe24CategoryGroups.length) {
    renderCafe24Categories();
    if (!cafe24CatalogItems.length) await openCafe24Group(cafe24ParentCategory);
    else renderCafe24Catalog();
    return;
  }
  setBusy(true, "공급사 분류를 불러오는 중입니다.", "wholesalers");
  try {
    const data = await api(`/api/wholesalers/${id}/categories`);
    cafe24CategoryGroups = data.groups || [];
    cafe24Categories = data.categories || [];
    cafe24CategoriesLoadedFor = id;
    if (!cafe24CategoryGroups.length && cafe24Categories.length) {
      cafe24CategoryGroups = [{ id: 0, name: "전체 분류", children: cafe24Categories }];
    }
    const stillValid = cafe24Categories.some((row) => String(row.id) === String(cafe24SelectedCategory))
      || cafe24CategoryGroups.some((group) => String(group.id) === String(cafe24SelectedCategory));
    if (!stillValid) {
      cafe24SelectedCategory = "";
      cafe24CatalogItems = [];
      cafe24CatalogLoadedCategory = "";
      cafe24CatalogPath = "";
    }
    if (!cafe24CategoryGroups.some((group) => String(group.id) === String(cafe24ParentCategory))) {
      const preferred = cafe24CategoryGroups.find((group) => (group.children || []).length)
        || cafe24CategoryGroups[0];
      cafe24ParentCategory = String(preferred?.id ?? "");
    }
    const childCount = cafe24CategoryGroups.reduce((sum, group) => sum + (group.children?.length || 0), 0);
    toast(`대분류 ${cafe24CategoryGroups.length.toLocaleString("ko-KR")}개 · 소분류 ${childCount.toLocaleString("ko-KR")}개`);
    await openCafe24Group(cafe24ParentCategory);
  } finally {
    setBusy(false, "", "wholesalers");
  }
}

async function selectCafe24Category(categoryId) {
  const cate = String(categoryId ?? "").trim();
  if (!cate || ["0", "all", "etc"].includes(cate)) return;
  cafe24SelectedCategory = cate;
  const parent = cafe24CategoryGroups.find((group) =>
    String(group.id) === cate || (group.children || []).some((child) => String(child.id) === cate)
  );
  if (parent) cafe24ParentCategory = String(parent.id ?? "");
  renderCafe24Categories();
  await loadCafe24Catalog({ force: true });
}

async function loadCafe24Catalog({ force = false } = {}) {
  const id = selectedCollectSupplierId || selectedWholesalerId();
  if (!id) throw new Error("공급사를 먼저 선택해 주세요.");
  const cate = String(cafe24SelectedCategory || "").trim();
  if (!cate || ["0", "all", "etc"].includes(cate)) {
    renderCafe24Catalog();
    throw new Error("대분류·소분류를 먼저 골라 주세요.");
  }
  if (
    !force
    && cafe24CatalogLoadedFor === id
    && String(cafe24CatalogLoadedCategory) === cate
    && cafe24CatalogItems.length
  ) {
    renderCafe24Catalog();
    return;
  }
  setBusy(true, "이 분류 상품을 불러오는 중입니다.", "wholesalers");
  const status = $("#collectCafe24Status");
  if (status) status.textContent = "이 분류 상품을 불러오는 중입니다…";
  try {
    const data = await api(`/api/wholesalers/${id}/catalog?category=${encodeURIComponent(cate)}`, {
      signal: AbortSignal.timeout(20000),
    });
    cafe24CatalogItems = data.items || [];
    cafe24CatalogLoadedFor = id;
    cafe24CatalogLoadedCategory = cate;
    cafe24CatalogPath = data.path || "";
    cafe24CatalogLoggedIn = Boolean(data.logged_in);
    cafe24CatalogPage = 1;
    renderCafe24Catalog();
    const priced = Number(data.priced_count || cafe24CatalogItems.filter((item) => cafe24ItemPrice(item) > 0).length);
    if (!cafe24CatalogItems.length && data.message) {
      toast(data.message, true);
    } else if (cafe24CatalogItems.length && priced === 0 && !cafe24CatalogLoggedIn) {
      toast(`이 분류 ${cafe24CatalogItems.length.toLocaleString("ko-KR")}개 · 가격은 공급처 로그인 후 다시 불러오세요.`);
    } else {
      toast(`이 분류 상품 ${cafe24CatalogItems.length.toLocaleString("ko-KR")}개를 불러왔습니다.`);
    }
  } catch (error) {
    if (error?.name === "TimeoutError" || isAbortError(error)) {
      const line = $("#collectCafe24Status");
      if (line) line.textContent = "상품을 제때 가져오지 못했습니다. 분류를 다시 눌러 주세요.";
      throw new Error("공급처 상품을 제때 가져오지 못했습니다. 분류를 다시 눌러 주세요.");
    }
    throw error;
  } finally {
    setBusy(false, "", "wholesalers");
  }
}

async function sendCafe24Selected() {
  const id = selectedCollectSupplierId || selectedWholesalerId();
  if (!id) throw new Error("공급사를 먼저 선택해 주세요.");
  const urls = [...document.querySelectorAll("#collectCafe24List input:checked")]
    .map((box) => String(box.value || "").trim())
    .filter(Boolean);
  if (!urls.length) throw new Error("보낼 상품을 선택해 주세요.");
  if (urls.length > 60) throw new Error("한 번에 60개까지 보낼 수 있습니다. 페이지에서 골라 주세요.");
  setBusy(true, `선택한 상품 ${urls.length}개를 상품관리로 담는 중입니다.`, "wholesalers");
  try {
    const result = await api(`/api/wholesalers/${id}/collect`, {
      method: "POST",
      body: JSON.stringify({ urls, collect_images: true, collect_options: true, collect_attributes: true }),
      scope: "wholesalers",
    });
    productFilter = id;
    currentWholesalerId = id;
    current = result.last || current;
    showMasterProducts();
    await loadProducts();
    fillProductFilter();
    updateFilterCount();
    if (cafe24CatalogPage > cafe24CatalogPages()) cafe24CatalogPage = cafe24CatalogPages();
    renderCafe24Catalog();
    toast(`상품관리에 ${result.count || urls.length}개를 담았습니다. 목록을 갱신했습니다.`);
  } finally {
    setBusy(false, "", "wholesalers");
  }
}

async function selectCollectSupplier(id) {
  const item = wholesalers.find((row) => row.id === id);
  if (!item) {
    selectedCollectSupplierId = "";
    showCollectPane("");
    renderCollectSupplierTree();
    return;
  }
  selectedCollectSupplierId = item.id;
  currentWholesalerId = item.id;
  renderCollectSupplierTree();
  if (item.type === "ownerclan") {
    showCollectPane("ownerclan");
    await loadOwnerclan();
    return;
  }
  showCollectPane("shop");
  const title = $("#collectCafe24Title");
  const typeLabel = item.type_label || item.type || "공급사";
  if (title) title.textContent = `${item.name || "공급사"} · ${typeLabel}`;
  if (cafe24CategoriesLoadedFor !== item.id) {
    cafe24Categories = [];
    cafe24CategoryGroups = [];
    cafe24CategoriesLoadedFor = "";
    cafe24SelectedCategory = "";
    cafe24ParentCategory = "";
    cafe24CatalogItems = [];
    cafe24CatalogLoadedFor = "";
    cafe24CatalogLoadedCategory = "";
    cafe24CatalogPath = "";
    cafe24CatalogLoggedIn = false;
  }
  if (item.enabled === false) {
    cafe24CatalogItems = [];
    cafe24CatalogLoadedFor = "";
    cafe24CatalogLoadedCategory = "";
    cafe24CatalogLoggedIn = false;
    renderCafe24Categories();
    renderCafe24Catalog();
    const status = $("#collectCafe24Status");
    if (status) status.textContent = "사용 중지된 공급사입니다. 공급처에서 사용을 켜 주세요.";
    return;
  }
  await loadCafe24Categories();
}

async function loadWholesalers() {
  wholesalers = await api("/api/wholesalers");
  fillWholesalerSelects();
  renderWholesalerSheet();
  if ($("#viewCollect") && !$("#viewCollect").hidden) renderCollectSupplierTree();
  if (!currentWholesalerId && wholesalers[0]) {
    fillWholesaleForm(wholesalers[0]);
  } else {
    const currentItem = wholesalers.find((item) => item.id === currentWholesalerId);
    if (currentItem) fillWholesaleForm(currentItem);
  }
  return wholesalers;
}

function renderWholesalerSheet() {
  const body = $("#wholesaleTable");
  if (!body) return;
  body.innerHTML = "";
  wholesalers.forEach((item) => {
    const row = document.createElement("tr");
    if (item.id === currentWholesalerId) row.className = "selected";
    row.append(
      textCell(item.name || ""),
      textCell(item.url || ""),
      textCell(item.type_label || item.type || ""),
      textCell(item.login_id || ""),
      textCell(String(wholesaleProductCount(item.id))),
      textCell(item.enabled === false ? "중지" : "사용"),
      textCell(item.memo || ""),
    );
    row.addEventListener("click", () => {
      currentWholesalerId = item.id;
      fillWholesaleForm(item);
      fillWholesalerSelects();
      renderWholesalerSheet();
    });
    body.appendChild(row);
  });
}

function syncWholesaleTypeFields() {
  const form = $("#wholesaleForm");
  if (!form) return;
  const ownerclan = form.elements.type.value === "ownerclan";
  form.elements.name.readOnly = ownerclan;
  form.elements.url.readOnly = ownerclan;
  form.elements.type.disabled = ownerclan;
}

function fillWholesaleForm(item) {
  const form = $("#wholesaleForm");
  if (!form) return;
  const data = item || {};
  currentWholesalerId = data.id || "";
  form.elements.id.value = data.id || "";
  form.elements.name.value = data.name || "";
  form.elements.url.value = data.url || "";
  form.elements.type.disabled = false;
  const type = data.type || "cafe24";
  const typeSelect = form.elements.type;
  if (typeSelect && ![...typeSelect.options].some((opt) => opt.value === type)) {
    const option = document.createElement("option");
    option.value = type;
    option.textContent = data.type_label || type;
    typeSelect.append(option);
  }
  form.elements.type.value = type;
  form.elements.login_id.value = data.login_id || "";
  form.elements.login_password.value = "";
  form.elements.login_password.placeholder = data.login_password_set ? "저장되어 있습니다" : "로그인 비밀번호";
  form.elements.enabled.checked = data.enabled !== false;
  form.elements.memo.value = data.memo || "";
  syncWholesaleTypeFields();
}

function wholesalePayload() {
  const form = $("#wholesaleForm");
  const payload = {
    id: form.elements.id.value || undefined,
    name: form.elements.name.value,
    url: form.elements.url.value,
    type: form.elements.type.value,
    login_id: form.elements.login_id.value,
    enabled: form.elements.enabled.checked,
    memo: form.elements.memo.value,
  };
  const password = form.elements.login_password.value;
  if (password) payload.login_password = password;
  return payload;
}

async function saveWholesalerForm() {
  const payload = wholesalePayload();
  if (payload.type === "ownerclan") {
    if (!payload.login_id && !payload.login_password) {
      throw new Error("오너클랜 로그인 아이디 또는 비밀번호를 입력해 주세요.");
    }
  } else if (!payload.name || !payload.url) {
    throw new Error("공급처 이름과 사이트 URL을 입력해 주세요.");
  }
  const saved = payload.id
    ? await api(`/api/wholesalers/${payload.id}`, { method: "PUT", body: JSON.stringify(payload) })
    : await api("/api/wholesalers", { method: "POST", body: JSON.stringify(payload) });
  currentWholesalerId = saved.id;
  await loadWholesalers();
  fillWholesaleForm(saved);
  log(`${saved.name} 공급처를 저장했습니다.`, "ok");
  toast("공급처를 저장했습니다.");
}

async function deleteCurrentWholesaler() {
  const id = $("#wholesaleForm").elements.id.value;
  if (!id) throw new Error("삭제할 공급처를 먼저 선택해 주세요.");
  if (id === "ownerclan") throw new Error("오너클랜 로그인은 목록에서 지우지 않습니다. 아이디를 비우고 저장하세요.");
  const item = wholesalers.find((row) => row.id === id);
  if (!confirm(`${item?.name || "이 공급처"}를 삭제할까요?`)) return;
  await api(`/api/wholesalers/${id}`, { method: "DELETE" });
  currentWholesalerId = "";
  fillWholesaleForm({});
  await loadWholesalers();
  log("공급처를 삭제했습니다.", "ok");
}

async function loginWholesaler(id) {
  const wholesalerId = id || selectedWholesalerId();
  if (!wholesalerId) throw new Error("공급처를 먼저 선택해 주세요.");
  const result = await api(`/api/wholesalers/${wholesalerId}/login`, { method: "POST" });
  toast(result.message || "공급처 로그인 창을 열었습니다.");
  log(result.message || "공급처 로그인 창을 열었습니다.", "ok");
}

let refreshJob = null;
let refreshTimer = 0;

function originalRefreshTargets() {
  const usable = (items) => items.filter((item) => isMasterProduct(item) && looksLikeUrl(item.source_url));
  if (selectedIds.size) return usable(selectedProducts());
  return usable(visibleProducts());
}

async function refreshOriginalProducts() {
  if (selectedIds.size && !originalRefreshTargets().length) {
    toast("선택한 상품은 원본상품이 아닙니다. 원본상품이나 마스터상품에서 고르세요.", true);
    return;
  }
  const targets = originalRefreshTargets();
  if (!targets.length) {
    toast("공급처 주소가 있는 원본상품이 없습니다.", true);
    return;
  }
  const fields = await askOriginalRefresh(targets.length);
  if (!fields.length) return;
  setBusy(true, "원본상품 정보를 업데이트하는 중입니다.");
  try {
    refreshJob = await api("/api/products/refresh-original", {
      method: "POST",
      body: JSON.stringify({ ids: targets.map((item) => item.id), fields }),
    });
  } catch (error) {
    setBusy(false);
    throw error;
  }
  log("원본상품 정보 업데이트를 시작했습니다.");
  pollRefreshJob();
}

function askOriginalRefresh(count) {
  const dialog = $("#originalRefreshDialog");
  const all = $("#originalRefreshAll");
  const price = $("#originalRefreshPrice");
  const images = $("#originalRefreshImages");
  const options = $("#originalRefreshOptions");
  const note = $("#originalRefreshNote");
  if (!dialog || !all || !price || !images || !options) return Promise.resolve(["all"]);
  if (note) note.textContent = `원본상품 ${count}개를 어떤 항목으로 업데이트할까요?`;
  const boxes = [price, images, options];
  const sync = () => {
    boxes.forEach((box) => {
      if (all.checked) box.checked = true;
      box.disabled = all.checked;
    });
  };
  all.checked = true;
  sync();
  all.onchange = sync;
  return new Promise((resolve) => {
    const finish = (fields) => {
      dialog.close();
      resolve(fields);
    };
    $("#originalRefreshOk").onclick = () => {
      if (all.checked) {
        finish(["all"]);
        return;
      }
      const fields = [];
      if (price.checked) fields.push("price");
      if (images.checked) fields.push("images");
      if (options.checked) fields.push("options");
      if (!fields.length) {
        toast("업데이트할 항목을 선택해 주세요.", true);
        return;
      }
      finish(fields);
    };
    $("#originalRefreshCancel").onclick = () => finish([]);
    dialog.oncancel = (event) => {
      event.preventDefault();
      finish([]);
    };
    dialog.showModal();
  });
}

function pollRefreshJob() {
  clearTimeout(refreshTimer);
  if (!refreshJob || refreshJob.status !== "running") return;
  refreshTimer = setTimeout(async () => {
    if (!refreshJob) return;
    try {
      refreshJob = await api(`/api/product-refresh-jobs/${refreshJob.id}`);
      const done = Number(refreshJob.done || 0);
      const total = Number(refreshJob.total || 0);
      setJobStatus(total ? `원본상품 정보 업데이트 ${done}/${total}` : (refreshJob.phase || "원본상품 정보를 업데이트하는 중입니다."), refreshJob.status === "running");
      if (refreshJob.status === "running") {
        pollRefreshJob();
        return;
      }
      await loadProducts();
      const updated = Number(refreshJob.updated || 0);
      const failed = Number(refreshJob.failed || 0);
      const stopped = refreshJob.status === "cancelled";
      const message = stopped
        ? `정보 업데이트를 멈췄습니다. ${updated}개 반영, 실패 ${failed}개.`
        : `원본상품 ${updated}개의 정보를 업데이트했습니다. 실패 ${failed}개.`;
      log(message, refreshJob.status === "error" ? "err" : "ok");
      toast(refreshJob.message || message, refreshJob.status === "error");
      setBusy(false);
    } catch (error) {
      log(error.message, "err");
      setBusy(false);
    }
  }, 700);
}

let marketJob = null;
let marketTimer = 0;
let marketPushAsked = false;
let marketPushFields = [];

function marketRefreshTargets() {
  const usable = (items) => items.filter((item) => !isMasterProduct(item) && item.market_id);
  if (selectedIds.size) return usable(selectedProducts());
  return usable(visibleProducts());
}

async function refreshMarketProducts() {
  if (selectedIds.size && !marketRefreshTargets().length) {
    toast("선택한 상품은 마켓 상품이 아니거나 공급처 주소가 없습니다.", true);
    return;
  }
  const targets = marketRefreshTargets();
  if (!targets.length) {
    toast("공급처 주소가 있는 마켓 상품이 없습니다.", true);
    return;
  }
  const waiting = targets.filter((item) => !item.origin_product_no && !item.channel_product_no);
  const registered = targets.filter((item) => item.origin_product_no || item.channel_product_no);
  const ids = [];
  marketPushFields = [];
  if (waiting.length) {
    const label = waiting.length > 1 ? `대기 상품 ${waiting.length}개` : "이 대기 상품";
    if (confirm(`${label}을 업데이트할까요?`)) ids.push(...waiting.map((item) => item.id));
  }
  if (registered.length) {
    const fields = await askMarketApply(registered.length);
    if (fields.length) {
      marketPushFields = fields;
      ids.push(...registered.map((item) => item.id));
    }
  }
  if (!ids.length) return;
  marketPushAsked = false;
  setBusy(true, "마켓 상품 판매정보를 업데이트하는 중입니다.");
  try {
    marketJob = await api("/api/products/refresh-market", {
      method: "POST",
      body: JSON.stringify({ ids }),
    });
  } catch (error) {
    setBusy(false);
    throw error;
  }
  log("마켓 상품 판매정보 업데이트를 시작했습니다.");
  pollMarketJob();
}

function askMarketApply(count) {
  const dialog = $("#marketApplyDialog");
  const price = $("#marketApplyPrice");
  const option = $("#marketApplyOption");
  const note = $("#marketApplyNote");
  if (!dialog || !price || !option) return Promise.resolve([]);
  if (note) note.textContent = `등록 상품 ${count}개에 업데이트 적용할까요?`;
  price.checked = true;
  option.checked = true;
  return new Promise((resolve) => {
    const finish = (fields) => {
      dialog.close();
      resolve(fields);
    };
    $("#marketApplyOk").onclick = () => {
      const fields = [];
      if (price.checked) fields.push("price");
      if (option.checked) fields.push("option");
      if (!fields.length) {
        toast("가격 또는 옵션을 선택해 주세요.", true);
        return;
      }
      finish(fields);
    };
    $("#marketApplyCancel").onclick = () => finish([]);
    dialog.oncancel = (event) => {
      event.preventDefault();
      finish([]);
    };
    dialog.showModal();
  });
}

function pollMarketJob() {
  clearTimeout(marketTimer);
  if (!marketJob || marketJob.status !== "running") return;
  marketTimer = setTimeout(async () => {
    if (!marketJob) return;
    try {
      marketJob = await api(`/api/product-market-jobs/${marketJob.id}`);
      const done = Number(marketJob.done || 0);
      const total = Number(marketJob.total || 0);
      const pushing = marketJob.push_status === "running";
      const label = pushing ? "스마트스토어 반영" : "판매정보 업데이트";
      setJobStatus(total ? `${label} ${done}/${total}` : (marketJob.phase || label), marketJob.status === "running");
      if (marketJob.status === "running") {
        pollMarketJob();
        return;
      }
      await loadProducts();
      if (!pushing && !marketPushAsked && marketJob.status === "done" && Number(marketJob.registered || 0) > 0) {
        marketPushAsked = true;
        const updated = Number(marketJob.updated || 0);
        const failed = Number(marketJob.failed || 0);
        log(`판매정보 ${updated}개를 갱신했습니다. 실패 ${failed}개.`, "ok");
        toast(`판매정보 ${updated}개를 갱신했습니다. 실패 ${failed}개.`);
        setBusy(false);
        const fields = marketPushFields.slice();
        if (fields.length) {
          setBusy(true, "등록 상품을 스마트스토어에 반영하는 중입니다.");
          marketJob = await api(`/api/product-market-jobs/${marketJob.id}/push`, {
            method: "POST",
            body: JSON.stringify({ fields }),
          });
          pollMarketJob();
        }
        return;
      }
      const stopped = marketJob.status === "cancelled" || marketJob.push_status === "cancelled";
      const message = marketJob.push_status
        ? (stopped
          ? `스마트스토어 반영을 멈췄습니다. ${marketJob.push_updated || 0}개 반영, 실패 ${marketJob.push_failed || 0}개.`
          : `스마트스토어 등록 상품 ${marketJob.push_updated || 0}개를 반영했습니다. 실패 ${marketJob.push_failed || 0}개.`)
        : (stopped
          ? `판매정보 업데이트를 멈췄습니다. ${marketJob.updated || 0}개 반영, 실패 ${marketJob.failed || 0}개.`
          : `마켓 상품 ${marketJob.updated || 0}개의 판매정보를 업데이트했습니다. 실패 ${marketJob.failed || 0}개.`);
      log(message, marketJob.status === "error" ? "err" : "ok");
      toast(marketJob.message || message, marketJob.status === "error");
      setBusy(false);
    } catch (error) {
      log(error.message, "err");
      setBusy(false);
    }
  }, 700);
}

async function importNewWholesaleProducts() {
  const onCollect = $("#viewCollect") && !$("#viewCollect").hidden;
  const picked = $("#productWholesalerFilter")?.value || "";
  const id = onCollect
    ? (selectedCollectSupplierId || selectedWholesalerId())
    : ((picked && picked !== "all" && picked !== "url") ? picked : selectedWholesalerId());
  if (!id) throw new Error("공급처를 먼저 선택해 주세요.");
  if (wholesalers.find((item) => item.id === id)?.type === "ownerclan") {
    showAppView("collect");
    selectCollectSupplier(id).catch(() => {});
    toast("오너클랜 상품은 상품담기에서 골라 가져옵니다.");
    return;
  }
  setBusy(true, "공급처 새 상품을 가져오는 중입니다.");
  try {
    const result = await api(`/api/wholesalers/${id}/import?new_only=true`, { method: "POST", scope: "products" });
    productFilter = id;
    currentWholesalerId = id;
    current = result.last || current;
    showMasterProducts();
    await loadProducts();
    fillProductFilter();
    updateFilterCount();
    if (onCollect && selectedCollectSupplierId === id) {
      if (cafe24CatalogPage > cafe24CatalogPages()) cafe24CatalogPage = cafe24CatalogPages();
      renderCafe24Catalog();
    } else if (current?.id) {
      selectProduct(current.id);
    }
    const name = result.wholesaler?.name || "공급처";
    if (result.added) {
      log(`${name} 새 상품 ${result.added}개를 가져왔습니다. 카테고리 ${result.categorized || 0}개, 상세 ${result.detailed || 0}개.`, "ok");
    } else {
      log(`${name}에 새 상품이 없습니다.`, "ok");
    }
  } catch (error) {
    if (isAbortError(error)) {
      log("작업을 중단했습니다.");
      return;
    }
    throw error;
  } finally {
    setBusy(false);
  }
}

async function importWholesaleProducts() {
  const id = selectedWholesalerId();
  if (!id) throw new Error("공급처를 먼저 선택해 주세요.");
  if (wholesalers.find((item) => item.id === id)?.type === "ownerclan") {
    showAppView("collect");
    selectCollectSupplier(id).catch(() => {});
    toast("오너클랜 상품은 상품담기에서 골라 가져옵니다.");
    return;
  }
  setBusy(true, "공급처 상품을 상품관리 목록으로 가져오는 중입니다.", "wholesalers");
  try {
    const result = await api(`/api/wholesalers/${id}/import`, { method: "POST", scope: "wholesalers" });
    productFilter = id;
    currentWholesalerId = id;
    current = result.last || null;
    showMasterProducts();
    await loadProducts();
    fillProductFilter();
    showAppView("products");
    if (current?.id) selectProduct(current.id);
    const name = result.wholesaler?.name || "공급처";
    const categorized = result.categorized || 0;
    const detailed = result.detailed || 0;
    log(`${name} 상품 ${result.count}개를 상품관리에 넣었습니다. 새로 ${result.added}개, 기존 ${result.kept}개, 카테고리 ${categorized}개, 상세설명 ${detailed}개.`, "ok");
    toast(`${name} 상품을 상품관리에서 공급처별로 볼 수 있습니다.`);
  } catch (error) {
    if (isAbortError(error)) {
      log("작업을 중단했습니다.");
      toast("작업을 중단했습니다.");
      return;
    }
    throw error;
  } finally {
    setBusy(false, "", "wholesalers");
  }
}

let stockJob = null;
let stockTimer = 0;
let stockMode = "soldout";

function stockModeLabel() {
  return stockMode === "resale" ? "재판매" : "품절";
}

async function openStockDialog(mode = "soldout") {
  const id = (productFilter && productFilter !== "all" && productFilter !== "url")
    ? productFilter
    : selectedWholesalerId();
  if (!id) throw new Error("공급처를 먼저 선택하거나, 상품관리에서 공급처 필터를 고르세요.");
  if (wholesalers.find((row) => row.id === id)?.type === "ownerclan") {
    throw new Error("오너클랜 상품은 상품담기에서 확인합니다.");
  }
  const supplier = wholesalers.find((row) => row.id === id);
  stockJob = null;
  stockMode = mode === "resale" ? "resale" : "soldout";
  $("#stockTitle").textContent = stockModeLabel();
  $("#stockRowSoldout").hidden = stockMode !== "soldout";
  $("#stockRowResale").hidden = stockMode !== "resale";
  $("#stockSupplier").textContent = stockMode === "resale"
    ? `${supplier?.name || "공급처"} 품절상품 중 공급처에서 다시 판매하는 상품을 확인합니다.`
    : `${supplier?.name || "공급처"} 상품의 품절 여부를 공급처에서 확인합니다.`;
  $("#stockMessage").textContent = "";
  renderStockJob({ status: "running", phase: "작업을 시작하는 중입니다.", done: 0, total: 0, checked: 0, products: 0, soldout_total: 0, soldout_count: 0, resale_count: 0, applied: {} });
  $("#stockDialog").showModal();
  setBusy(true, `${stockModeLabel()} 상태를 확인하는 중입니다.`);
  try {
    stockJob = await api(`/api/wholesalers/${id}/stock-check`, { method: "POST", scope: "products" });
  } catch (error) {
    setBusy(false);
    renderStockJob({ status: "error", phase: "시작하지 못했습니다.", done: 0, total: 0, checked: 0, products: 0, soldout_total: 0, soldout_count: 0, resale_count: 0, applied: {} });
    $("#stockMessage").textContent = error.message;
    throw error;
  }
  log(`${stockModeLabel()} 확인을 시작했습니다.`);
  renderStockJob(stockJob);
  pollStockJob();
}

function renderStockJob(job) {
  const running = job.status === "running";
  const total = Number(job.total || 0);
  const done = Number(job.done || 0);
  const progress = $("#stockProgress");
  if (running && !total) progress.removeAttribute("value");
  else progress.value = total ? Math.round((done / total) * 100) : 100;
  $("#stockPhase").textContent = job.phase || "";
  $("#stockStep").textContent = total ? `${done.toLocaleString("ko-KR")} / ${total.toLocaleString("ko-KR")}` : "";
  $("#stockChecked").textContent = job.products ? `상품 ${job.products}개 중 ${job.checked}개 확인` : "";
  const applied = job.applied || {};
  $("#stockSoldoutText").textContent = applied.soldout != null
    ? `품절상품 ${job.soldout_total}개 / ${applied.soldout}개를 품절로 바꿨습니다`
    : `품절상품 ${job.soldout_total}개 (새로 품절 ${job.soldout_count}개) 품절상태로 바꿀까요?`;
  $("#stockResaleText").textContent = applied.resale != null
    ? `${applied.resale}개를 재판매로 바꿨습니다`
    : `재판매 가능 ${job.resale_count}개 재판매로 바꿀까요?`;
  $("#stockApplySoldout").disabled = running || !job.soldout_count || applied.soldout != null;
  $("#stockApplyResale").disabled = running || !job.resale_count || applied.resale != null;
  $("#stockStop").disabled = !running || !stockJob;
  if (job.message) $("#stockMessage").textContent = job.message;
}

function pollStockJob() {
  clearTimeout(stockTimer);
  if (!stockJob || stockJob.status !== "running") return;
  stockTimer = setTimeout(async () => {
    if (!stockJob) return;
    try {
      stockJob = await api(`/api/stock-jobs/${stockJob.id}`);
      renderStockJob(stockJob);
      if (stockJob.status === "running") pollStockJob();
      else {
        const summary = stockMode === "resale"
          ? `재판매 가능 ${stockJob.resale_count}개`
          : `품절 ${stockJob.soldout_total}개, 새로 품절 ${stockJob.soldout_count}개`;
        log(`${stockModeLabel()} 확인 ${stockJob.status === "cancelled" ? "중지" : "완료"}. ${summary}.`, "ok");
        setBusy(false);
      }
    } catch (error) {
      $("#stockMessage").textContent = error.message;
      setBusy(false);
    }
  }, 700);
}

async function stopStockJob() {
  if (!stockJob) return;
  stockJob = await api(`/api/stock-jobs/${stockJob.id}/cancel`, { method: "POST" });
  renderStockJob(stockJob);
  $("#stockStop").disabled = true;
  setBusy(false);
}

async function applyStockJob(kind) {
  if (!stockJob) return;
  stockJob = await api(`/api/stock-jobs/${stockJob.id}/apply`, { method: "POST", body: JSON.stringify({ kind }) });
  renderStockJob(stockJob);
  await loadProducts();
  const count = stockJob.applied?.[kind] || 0;
  const message = kind === "soldout" ? `${count}개 상품을 품절로 바꿨습니다.` : `${count}개 상품을 재판매로 바꿨습니다.`;
  $("#stockMessage").textContent = message;
  log(message, "ok");
}

function closeStockDialog() {
  clearTimeout(stockTimer);
  if (stockJob?.status === "running") {
    api(`/api/stock-jobs/${stockJob.id}/cancel`, { method: "POST" }).catch(() => {});
    log(`${stockModeLabel()} 확인을 중지했습니다.`);
  }
  stockJob = null;
  $("#stockDialog").close();
  setBusy(false);
}

function isOrderChannelExpanded(id) {
  return orderChannelExpanded[id] !== false;
}

function orderCollectStores() {
  if (orderCollectChannel === "all") {
    return accountChannels().flatMap((channel) => marketsForChannel(channel.id));
  }
  return marketsForChannel(orderCollectChannel);
}

function fillOrderCollectSelects() {
  fillCsMallSelect();
  fillMenuStoreFilter();
  fillWorkStatusSelects();
  const channels = accountChannels();
  if (orderCollectChannel !== "all" && !channels.some((item) => item.id === orderCollectChannel)) {
    orderCollectChannel = "all";
  }
  const stores = orderCollectStores();
  if (orderCollectStore !== "all" && !stores.some((item) => item.id === orderCollectStore)) {
    orderCollectStore = "all";
  }
  fillSelectOptions(
    $("#orderChannelFilter"),
    [["all", "전체마켓"]].concat(channels.map((item) => [item.id, mallLabel(item) || item.name || item.id])),
    orderCollectChannel,
  );
  fillSelectOptions(
    $("#orderStoreFilter"),
    [["all", "(전체)"]].concat(stores.map((item) => {
      const name = item.name || item.slug || item.login_id || item.id;
      if (orderCollectChannel !== "all") return [item.id, name];
      const prefix = mallLabel(marketChannel(item));
      return [item.id, prefix ? `${prefix} ${name}` : name];
    })),
    orderCollectStore,
  );
}

function fillOrderMarketTree() {
  fillOrderCollectSelects();
  const tree = $("#orderMarketTree");
  if (!tree) return;
  const channelIds = accountChannels().map((item) => item.id);
  if (
    orderMarketFilter !== "all"
    && !channelIds.includes(orderMarketFilter)
    && !markets.some((item) => item.id === orderMarketFilter)
  ) {
    orderMarketFilter = "all";
  }
  tree.innerHTML = "";
  tree.append(marketButton({
    depth: 0,
    label: "전체",
    filter: "all",
    kind: "all",
    active: orderMarketFilter === "all",
    icon: marketIcon({ icon: "전", color: "#6b7280" }),
  }));
  accountChannels().forEach((channel) => {
    const rows = marketsForChannel(channel.id);
    const expanded = isOrderChannelExpanded(channel.id);
    tree.append(marketButton({
      depth: 1,
      label: channel.name,
      filter: channel.id,
      kind: "channel",
      channel: channel.id,
      active: orderMarketFilter === channel.id,
      caret: marketCaret(expanded, channel.id),
      icon: marketIcon(channel),
    }));
    if (!expanded) return;
    if (!rows.length) {
      tree.append(marketButton({
        depth: 2,
        label: "마켓을 등록하세요",
        kind: "empty",
        channel: channel.id,
        icon: marketIcon({ icon: "+", color: "#555" }),
      }));
      return;
    }
    rows.forEach((item) => {
      const name = item.name || item.slug || item.url || item.login_id || item.id;
      tree.append(marketButton({
        depth: 2,
        label: name,
        filter: item.id,
        marketId: item.id,
        kind: "store",
        channel: channel.id,
        active: orderMarketFilter === item.id,
        icon: marketIcon(channel),
      }));
    });
  });
}

function inquiryAccountMarkets() {
  if (inquiryChannelFilter && inquiryChannelFilter !== "all") return marketsForChannel(inquiryChannelFilter);
  return markets.filter((item) => accountChannels().some((channel) => channel.id === marketChannel(item)));
}

function inquiryStoreOption(item) {
  return [item.id, item.login_id || item.slug || item.name || item.id];
}

function fillSelectOptions(select, options, selected) {
  if (!select) return;
  select.innerHTML = "";
  options.forEach(([value, label]) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.appendChild(option);
  });
  select.value = options.some((item) => item[0] === selected) ? selected : (options[0]?.[0] || "");
}

function fillInquiryMallSelects() {
  const stores = inquiryAccountMarkets();
  if (inquiryStoreFilter !== "all" && !stores.some((item) => item.id === inquiryStoreFilter)) {
    inquiryStoreFilter = "all";
  }
  inquiryMarketFilter = inquiryStoreFilter !== "all" ? inquiryStoreFilter : inquiryChannelFilter;
  const channelOptions = [["all", "(쇼핑몰선택)"]].concat(
    accountChannels().map((item) => [item.id, mallLabel(item)]),
  );
  const storeTop = [["all", "(쇼핑몰ID선택)"]].concat(stores.map(inquiryStoreOption));
  const storeResult = [["all", "(전체)"]].concat(stores.map(inquiryStoreOption));
  fillSelectOptions($("#inquiryChannelFilter"), channelOptions, inquiryChannelFilter);
  fillSelectOptions($("#inquiryResultChannel"), channelOptions, inquiryChannelFilter);
  fillSelectOptions($("#inquiryStoreFilter"), storeTop, inquiryStoreFilter);
  fillSelectOptions($("#inquiryResultStore"), storeResult, inquiryStoreFilter);
}

function setInquiryChannelFilter(value) {
  inquiryChannelFilter = value || "all";
  inquiryStoreFilter = "all";
  fillInquiryMallSelects();
  renderInquiryList();
}

function setInquiryStoreFilter(value) {
  inquiryStoreFilter = value || "all";
  fillInquiryMallSelects();
  renderInquiryList();
}

function fillInquiryMarketTree() {
  fillInquiryMallSelects();
}

function orderTargetMarkets() {
  if (orderCollectStore !== "all") {
    const one = markets.find((item) => item.id === orderCollectStore);
    return one ? [one] : [];
  }
  if (orderCollectChannel === "all") return orderCollectStores();
  return marketsForChannel(orderCollectChannel || "smartstore");
}

function smartstoreTargets(rows) {
  return (rows || []).filter((item) => (item.channel || "smartstore") === "smartstore");
}

function inquiryTargetMarkets() {
  if (inquiryStoreFilter && inquiryStoreFilter !== "all") {
    const one = markets.find((item) => item.id === inquiryStoreFilter);
    return one ? [one] : [];
  }
  if (inquiryChannelFilter && inquiryChannelFilter !== "all") {
    return marketsForChannel(inquiryChannelFilter);
  }
  return marketsForChannel("smartstore");
}

function marketOf(id) {
  return markets.find((item) => item.id === id) || null;
}

function orderMarketName(item) {
  return marketOf(item.market_id)?.name || item.market_name || "";
}

function orderBucket(item) {
  const status = String(item.status || "").trim().toUpperCase();
  const place = String(item.place_status || "").trim().toUpperCase();
  if (status === "CANCELED" || status === "CANCELED_BY_NOPAYMENT" || status.includes("CANCEL")) return "canceled";
  if (status === "RETURNED" || status.includes("RETURN")) return "returned";
  if (status === "EXCHANGED" || status.includes("EXCHANGE")) return "exchanged";
  if (status === "PURCHASE_DECIDED") return "confirmed";
  if (status === "DELIVERED") return "delivered";
  if (status === "DELIVERING") return "shipping";
  if (status === "PAYED" && (place === "OK" || item.wholesale_order_no || item.dispatched)) return "wait";
  if (status === "PAYMENT_WAITING") return "";
  if (status === "PAYED") return "new";
  if (String(item.tracking_number || "").trim() && !item.dispatched) return "wait";
  if (String(item.tracking_number || "").trim()) return "shipping";
  return "new";
}

function visibleOrders() {
  if (!ordersCollected) return [];
  let rows = orders;
  if (orderMarketFilter !== "all") {
    if (accountChannels().some((item) => item.id === orderMarketFilter)) {
      const ids = new Set(marketsForChannel(orderMarketFilter).map((item) => item.id));
      rows = rows.filter((item) => ids.has(item.market_id) || item.channel === orderMarketFilter);
    } else {
      rows = rows.filter((item) => item.market_id === orderMarketFilter);
    }
  }
  rows = rows.filter((item) => orderBucket(item));
  if (orderTab === "cs") return sortVisibleOrders(csVisibleOrders(rows));
  if (orderTab !== "all") {
    rows = rows.filter((item) => orderBucket(item) === orderTab);
  }
  const from = inquiryDateValue($("#orderDateFrom")?.value);
  const to = inquiryDateValue($("#orderDateTo")?.value);
  if (from || to) {
    const basis = $("#orderDateBasis")?.value || "paid";
    rows = rows.filter((item) => {
      const day = basis === "dispatch"
        ? inquiryDateValue(item.send_date)
        : inquiryDateValue(basis === "order" ? item.order_date : (item.payment_date || item.order_date));
      if (!day) return basis !== "dispatch";
      if (from && day < from) return false;
      if (to && day > to) return false;
      return true;
    });
  }
  const query = String(orderQuery || "").trim().toLowerCase();
  if (query) {
    rows = rows.filter((item) => {
      const blob = [item.order_id, item.product_order_id, item.product_name, item.option, item.receiver_name, item.buyer_name]
        .map((value) => String(value || "").toLowerCase())
        .join(" ");
      return blob.includes(query);
    });
  }
  return sortVisibleOrders(applyOrderMenuFilters(rows));
}

function orderSortValue(item, key) {
  if (key === "price") {
    const unit = Number(item.unit_price);
    if (Number.isFinite(unit) && String(item.unit_price ?? "") !== "") return unit;
    const qty = Number(item.quantity) || 1;
    return qty ? orderGrossAmount(item) / qty : 0;
  }
  if (key === "alias") return orderMarketName(item);
  if (key === "mall") return mallLabel(item.channel || marketOf(item.market_id)?.channel || "smartstore");
  return "";
}

function sortVisibleOrders(rows) {
  if (!orderSortKey) return rows;
  const dir = orderSortDir === "desc" ? -1 : 1;
  return [...rows].sort((a, b) => {
    const av = orderSortValue(a, orderSortKey);
    const bv = orderSortValue(b, orderSortKey);
    let cmp = 0;
    if (typeof av === "number" || typeof bv === "number") cmp = Number(av) - Number(bv);
    else cmp = String(av).localeCompare(String(bv), "ko", { numeric: true, sensitivity: "base" });
    if (cmp) return cmp * dir;
    return String(a.id || "").localeCompare(String(b.id || ""));
  });
}

function updateOrderSortHeaders() {
  document.querySelectorAll("#orderGrid th.sortable").forEach((th) => {
    const active = th.dataset.sort === orderSortKey;
    th.classList.toggle("sort-asc", active && orderSortDir === "asc");
    th.classList.toggle("sort-desc", active && orderSortDir === "desc");
    th.setAttribute("aria-sort", active ? (orderSortDir === "desc" ? "descending" : "ascending") : "none");
  });
}

const DEFAULT_WORK_STATUSES = ["미지정", "진행중", "완료", "보류"];
const DEFAULT_EXCEL_COLUMNS = ["No.", "주문상태", "쇼핑몰", "별칭(쇼핑몰계정)", "주문번호", "구매자", "수령자", "상품명", "선택사항", "수량", "단가", "택배사", "송장번호", "보류여부", "작업상태"];

function loadNameList(key) {
  try {
    const saved = JSON.parse(localStorage.getItem(key) || "[]");
    return Array.isArray(saved) ? saved.map((item) => String(item || "")).filter(Boolean) : [];
  } catch (error) {
    return [];
  }
}

function orderWorkStatuses() {
  const saved = loadNameList("uploader-order-work-statuses");
  return saved.length ? saved : DEFAULT_WORK_STATUSES.slice();
}

function displayedOrderColumns() {
  const columns = orderGridColumns();
  if (orderTab === "cs") return columns;
  const hidden = new Set(loadNameList("uploader-order-hidden-cols"));
  if (orderTab === "wait") ["택배사", "송장번호", "배송추적", "판매취소하기"].forEach((title) => hidden.delete(title));
  const visible = columns.filter((title) => !hidden.has(title));
  return visible.length ? visible : columns;
}

function orderExcelColumns() {
  const known = new Set(ORDER_SHEET_COLUMNS);
  const saved = [];
  const seen = new Set();
  loadNameList("uploader-order-excel-cols").forEach((name) => {
    const title = name === "도매처" || name === "주문순번" ? "공급처" : name;
    if (!known.has(title) || seen.has(title)) return;
    seen.add(title);
    saved.push(title);
  });
  return saved.length ? saved : DEFAULT_EXCEL_COLUMNS.filter((name) => known.has(name));
}

function orderRemoteKind(item) {
  const address = `${item?.address1 || ""} ${item?.address2 || ""}`;
  return /제주|울릉|독도/.test(address) ? "remote" : "normal";
}

function applyOrderMenuFilters(rows) {
  const preset = $("#menuOrderPreset")?.value || "all";
  if (preset === "hold") rows = rows.filter((item) => item.on_hold);
  else if (preset === "no-invoice") rows = rows.filter((item) => !String(item.tracking_number || "").trim());
  else if (preset === "unconfirmed") rows = rows.filter((item) => orderBucket(item) === "new" && String(item.place_status || "").toUpperCase() !== "OK");
  const place = $("#menuPlaceFilter")?.value || "all";
  if (place === "ok") rows = rows.filter((item) => String(item.place_status || "").toUpperCase() === "OK" || item.wholesale_order_no);
  else if (place === "none") rows = rows.filter((item) => String(item.place_status || "").toUpperCase() !== "OK" && !item.wholesale_order_no);
  const work = $("#menuWorkFilter")?.value || "all";
  if (work !== "all") rows = rows.filter((item) => (item.work_status || "미지정") === work);
  const link = $("#menuLinkFilter")?.value || "all";
  if (link === "linked") rows = rows.filter((item) => item.wholesale_id || item.wholesale_name);
  else if (link === "none") rows = rows.filter((item) => !item.wholesale_id && !item.wholesale_name);
  const remote = $("#menuRemoteFilter")?.value || "all";
  if (remote !== "all") rows = rows.filter((item) => orderRemoteKind(item) === remote);
  const store = $("#menuStoreFilter")?.value || "all";
  if (store !== "all") rows = rows.filter((item) => item.market_id === store);
  const claim = $("#menuClaimFilter")?.value || "all";
  const claimed = (item) => Boolean(item.claim_reason) || ["canceled", "returned", "exchanged"].includes(orderBucket(item));
  if (claim === "claim") rows = rows.filter(claimed);
  else if (claim === "none") rows = rows.filter((item) => !claimed(item));
  return rows;
}

function fillWorkStatusSelects() {
  const statuses = orderWorkStatuses();
  const work = $("#menuWorkStatus");
  const filter = $("#menuWorkFilter");
  if (work) {
    const current = work.value;
    work.replaceChildren();
    const blank = document.createElement("option");
    blank.value = "";
    blank.textContent = "선택";
    work.appendChild(blank);
    statuses.forEach((name) => {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = name;
      work.appendChild(option);
    });
    if ([...work.options].some((option) => option.value === current)) work.value = current;
  }
  if (filter) {
    const current = filter.value || "all";
    filter.replaceChildren();
    const all = document.createElement("option");
    all.value = "all";
    all.textContent = "(전체)";
    filter.appendChild(all);
    statuses.forEach((name) => {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = name;
      filter.appendChild(option);
    });
    if ([...filter.options].some((option) => option.value === current)) filter.value = current;
  }
}

function fillMenuStoreFilter() {
  const select = $("#menuStoreFilter");
  if (!select) return;
  fillSelectOptions(
    select,
    [["all", "(전체)"]].concat(markets.map((item) => [item.id, item.name || item.slug || item.login_id || item.id])),
    select.value || "all",
  );
}

function menuTargetOrders() {
  const selected = selectedOrders();
  if (selected.length) return selected;
  const focused = orders.find((item) => item.id === orderFocusId);
  if (focused && visibleOrders().some((item) => item.id === focused.id)) return [focused];
  toast("먼저 주문을 선택해 주세요.", true);
  return [];
}

async function setOrderHold(held) {
  const items = menuTargetOrders();
  if (!items.length) return;
  for (const item of items) await saveOrderPatch(item.id, { on_hold: held });
  renderOrders();
  toast(held ? `${items.length}건을 보류했습니다.` : `${items.length}건 보류를 해제했습니다.`);
}

async function applyMenuWorkStatus() {
  const status = $("#menuWorkStatus")?.value || "";
  if (!status) {
    toast("작업상태를 선택해 주세요.", true);
    return;
  }
  const items = menuTargetOrders();
  if (!items.length) return;
  for (const item of items) await saveOrderPatch(item.id, { work_status: status });
  renderOrders();
  toast(`${items.length}건을 ${status}(으)로 지정했습니다.`);
}

function resetOrderMenuFilters() {
  ["menuOrderPreset", "menuPlaceFilter", "menuWorkFilter", "menuLinkFilter", "menuRemoteFilter", "menuStoreFilter", "menuClaimFilter"].forEach((id) => {
    if ($(`#${id}`)) $(`#${id}`).value = id === "menuWorkFilter" || id === "menuStoreFilter" ? "all" : "all";
  });
  if ($("#orderSearch")) $("#orderSearch").value = "";
  orderQuery = "";
  renderOrders();
}

function orderStatsText(rows) {
  const count = (bucket) => rows.filter((item) => orderBucket(item) === bucket).length;
  const works = new Map();
  rows.forEach((item) => {
    const name = item.work_status || "미지정";
    works.set(name, (works.get(name) || 0) + 1);
  });
  const paid = rows.reduce((sum, item) => sum + orderPaidAmount(item), 0);
  return [
    `보이는 주문 ${rows.length}건`,
    `신규 ${count("new")} / 발송대기 ${count("wait")} / 배송중 ${count("shipping")}`,
    `배송완료 ${count("delivered")} / 구매확정 ${count("confirmed")}`,
    `취소 ${count("canceled")} / 반품 ${count("returned")} / 교환 ${count("exchanged")}`,
    `보류 ${rows.filter((item) => item.on_hold).length}건`,
    `결제 ${Math.round(paid).toLocaleString("ko-KR")}원`,
    ...[...works].map(([name, amount]) => `작업상태 ${name} ${amount}건`),
  ].join("\n");
}

function fillCheckList(container, names, checked) {
  if (!container) return;
  container.replaceChildren();
  names.forEach((title) => {
    const label = document.createElement("label");
    label.className = "check";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = title;
    input.checked = checked(title);
    label.append(input, document.createTextNode(` ${title}`));
    container.appendChild(label);
  });
}

function openOrderColumnDialog() {
  const hidden = new Set(loadNameList("uploader-order-hidden-cols"));
  fillCheckList($("#orderColumnList"), orderGridColumns(), (title) => !hidden.has(title));
  $("#orderColumnDialog")?.showModal();
}

function saveOrderColumnDialog() {
  const inputs = [...($("#orderColumnList")?.querySelectorAll("input") || [])];
  const hidden = inputs.filter((input) => !input.checked).map((input) => input.value);
  if (hidden.length >= inputs.length) {
    toast("표시할 항목을 하나 이상 남겨 주세요.", true);
    return;
  }
  localStorage.setItem("uploader-order-hidden-cols", JSON.stringify(hidden));
  $("#orderColumnDialog")?.close();
  const table = $("#orderGrid");
  if (table) table.dataset.sheet = "";
  renderOrders();
}

function openOrderExcelDialog() {
  const picked = new Set(orderExcelColumns());
  fillCheckList($("#orderExcelList"), ORDER_SHEET_COLUMNS, (title) => picked.has(title));
  $("#orderExcelDialog")?.showModal();
}

function saveOrderExcelDialog() {
  const names = [...($("#orderExcelList")?.querySelectorAll("input") || [])].filter((input) => input.checked).map((input) => input.value);
  if (!names.length) {
    toast("엑셀에 넣을 항목을 하나 이상 선택해 주세요.", true);
    return;
  }
  localStorage.setItem("uploader-order-excel-cols", JSON.stringify(names));
  $("#orderExcelDialog")?.close();
  toast("엑셀 양식을 저장했습니다.");
}

function exportPlainOrders() {
  const picked = selectedOrders();
  const rows = picked.length ? picked : visibleOrders();
  if (!rows.length) {
    toast("내보낼 주문이 없습니다.", true);
    return;
  }
  const headers = orderExcelColumns();
  const lines = [headers.join(",")];
  rows.forEach((item, index) => {
    const fields = new Map(orderDetailRows(item, index + 1).map((parts) => [parts[0], parts[1]]));
    lines.push(headers.map((label) => csvEscape(fields.get(label) ?? "")).join(","));
  });
  const blob = new Blob(["\uFEFF" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `주문_${formatLocalDate(new Date())}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
  toast(`${rows.length}건을 엑셀 파일로 만들었습니다.`);
}

let excelForms = [];
let selectedExcelFormIds = new Set();
let editingExcelFormId = "";
let excelEditRow = null;
let excelExportTarget = "all";
let excelExportIds = new Set();
let excelFileNameTouched = false;
let excelSaveDirHandle = null;
let excelSaveDirLabel = localStorage.getItem("uploader-order-excel-dir") || "";
const EXCEL_VALUE_CODES = [
  "(빈칸)",
  "(엑셀수식)",
  "(오늘날짜)",
  "(총[송장상품수량]개)[배송메모]",
  "(컬럼메모에 입력한 값)",
  "[CS메모]",
  "[개인통관고유부호 인증번호]",
  "[개인통관고유부호]",
  "[결제번호(ESM)]",
  "[결제수단]",
  "[결제일시]",
  "[결제일자(yyyyMMdd)]",
  "[결제일자(yyyy-MM-dd)]",
  "[공급금액]",
  "[구매번호(위메프)]",
  "[구매자]",
  "[구매자전달사항(도매꾹)]",
  "[구매자전화(숫자)]",
  "[구매자전화]",
  "[구매자휴대전화(숫자)]",
  "[구매자휴대전화]",
  "[구매확정일시(스마트스토어)]",
  "[노출상품명]",
  "[노출옵션명(쿠팡)]",
  "[단가(옵션추가금액포함)]",
  "[단가]",
  "[도서산간]",
  "[등록상품명]",
  "[등록옵션명(쿠팡)]",
  "[마지막 유입경로(스마트스토어)]",
  "[마켓수수료금액]",
  "[메모(쇼핑몰계정)]",
  "[발송마감일]",
  "[발송예정일]",
  "[발송일시]",
  "[발송일자(yyyyMMdd)]",
  "[발송일자(yyyy-MM-dd)]",
  "[배송구분]",
  "[배송메모]",
  "[배송방법]",
  "[배송번호]",
  "[배송비]",
  "[배송속성(스마트스토어)]",
  "[배송완료일시]",
  "[별칭(쇼핑몰계정)]",
  "[별칭(쇼핑몰계정)]:[상품명][구분자1][선택사항][구분자2][수량][구분자3][구분자4][추가구성]",
  "[보류여부]",
  "[사은품 정보(고도몰5)]",
  "[상품URL]",
  "[상품명]",
  "[상품명][구분자1][선택사항][구분자2][수량][구분자3][구분자4][추가구성]",
  "[상품명][구분자1][선택사항][구분자4][추가구성]",
  "[상품번호]",
  "[상품주문번호(스마트스토어)]",
  "[샵마인주문상태]",
  "[선택사항]",
  "[선택사항] [추가구성]",
  "[선택사항][구분자2][수량][구분자3][구분자4][추가구성]",
  "[설치예약일]",
  "[송장번호]",
  "[송장번호입력일시(로컬)]",
  "[송장상품수량]",
  "[송장실결제금액(배송비포함)]",
  "[송장실결제금액]",
  "[송장입력]",
  "[송장총주문금액]",
  "[쇼핑몰]",
  "[쇼핑몰]([쇼핑몰ID])",
  "[쇼핑몰]([쇼핑몰ID])/[정산예상금액]([배송비])/[선택사항][추가구성]",
  "[쇼핑몰]([상품명][구분자1][선택사항][구분자2][수량][구분자3][구분자4][추가구성])",
  "[쇼핑몰ID]",
  "[쇼핑몰계정고유번호]",
  "[수량]",
  "[수령자]",
  "[수령자전화번호(숫자)]",
  "[수령자전화번호]",
  "[수령자휴대전화(숫자)]",
  "[수령자휴대전화]",
  "[수수료율]",
  "[실결제금액(배송비포함)]",
  "[실결제금액]",
  "[실수수료율]",
  "[옵션추가금액]",
  "[우편번호]",
  "[위메프배송번호]",
  "[인터파크 공급계약번호]",
  "[작업상태]",
  "[정산예상금액]",
  "[정산예정금액(배송비포함)]",
  "[정산추가정보]",
  "[주문고유코드]",
  "[주문메모(오늘의집)]",
  "[주문번호(스마트스토어)]",
  "[주문번호]",
  "[주문상태]",
  "[주문섹션번호(아임웹)]",
  "[공급처]",
  "[주문일(약식)]",
  "[주문일시]",
  "[주문일자(yyyyMMdd)]",
  "[주문일자(yyyy-MM-dd)]",
  "[주문자ID]",
  "[주소]",
  "[총주문금액]",
  "[최근 엑셀생성 일시(로컬)]",
  "[최초 엑셀생성 일시(로컬)]",
  "[추가구성]",
  "[추가구성수량]",
  "[추가메모1]",
  "[추가메모10]",
  "[추가메모2]",
  "[추가메모3]",
  "[추가메모4]",
  "[추가메모5]",
  "[추가메모6]",
  "[추가메모7]",
  "[추가메모8]",
  "[추가메모9]",
  "[쿠팡모델번호]",
  "[쿠팡옵션ID]",
  "[클레임사유]",
  "[클레임완료일시]",
  "[클레임접수일시]",
  "[택배사]",
  "[통관부호일치여부]",
  "[판매자내부코드1]",
  "[판매자내부코드2]",
  "[판매자상품코드]",
  "[판매자옵션코드]",
  "[할인금액]",
];

function excelSettlementWithFee(item) {
  const paid = orderPaidAmount(item);
  const commission = Number(item.commission) || 0;
  const settlement = item.settlement_amount === undefined || item.settlement_amount === null || item.settlement_amount === ""
    ? paid - commission
    : Number(item.settlement_amount);
  const fee = item.shipping_fee_type === "착불" ? 0 : Number(item.delivery_fee) || 0;
  return orderMoney(settlement + fee);
}

function excelFields(item, index) {
  const map = new Map(orderDetailRows(item, index + 1).map((parts) => [parts[0], parts[1] == null ? "" : String(parts[1])]));
  const digits = (value) => String(value || "").replace(/\D/g, "");
  const market = marketOf(item.market_id);
  const compact = (value) => orderDay(value).replace(/-/g, "");
  map.set("주문고유코드", item.product_order_id || item.order_id || "");
  map.set("주문번호", item.order_id || item.product_order_id || "");
  map.set("공급처", item.wholesale_name || "");
  map.set("주문순번", item.wholesale_name || "");
  map.set("도매처", item.wholesale_name || "");
  map.set("주문번호(스마트스토어)", item.order_id || "");
  map.set("상품주문번호(스마트스토어)", item.product_order_id || "");
  const phones = orderListPhones(item);
  map.set("수령자전화번호", phones.receiver);
  map.set("수령자휴대전화", phones.receiver);
  map.set("구매자전화", phones.buyer);
  map.set("구매자휴대전화", phones.buyer);
  map.set("구매자휴대전화(숫자)", digits(phones.buyer));
  map.set("구매자전화(숫자)", digits(phones.buyer));
  map.set("결제일시(yyyy-MM-dd)", orderDay(item.payment_date || item.order_date));
  map.set("결제일자(yyyy-MM-dd)", orderDay(item.payment_date));
  map.set("결제일자(yyyyMMdd)", compact(item.payment_date));
  map.set("주문일자(yyyy-MM-dd)", orderDay(item.order_date));
  map.set("주문일자(yyyyMMdd)", compact(item.order_date));
  map.set("발송일자(yyyy-MM-dd)", orderDay(item.send_date));
  map.set("발송일자(yyyyMMdd)", compact(item.send_date));
  map.set("단가(옵션추가금액포함)", map.get("단가(옵션추가금액 포함)") || "");
  map.set("실결제금액(배송비포함)", map.get("실결제금액(배송비 포함)") || "");
  map.set("쇼핑몰ID", item.mall_id || market?.login_id || "");
  map.set("최근 엑셀생성 일시(로컬)", map.get("최근 엑셀생성 일시") || "");
  map.set("최초 엑셀생성 일시(로컬)", map.get("최초 엑셀생성 일시") || "");
  map.set("송장번호입력일시(로컬)", map.get("송장번호입력일시") || "");
  map.set("구매확정일시(스마트스토어)", map.get("구매확정일시") || "");
  map.set("마지막 유입경로(스마트스토어)", map.get("마지막 유입경로") || "");
  map.set("사은품 정보(고도몰5)", map.get("사은품 정보") || "");
  map.set("구매자전달사항(도매꾹)", map.get("구매자전달사항") || "");
  map.set("샵마인주문상태", map.get("스마트주문상태") || map.get("주문상태") || "");
  map.set("정산예정금액(배송비포함)", excelSettlementWithFee(item));
  map.set("정산예상금액(배송비포함)", excelSettlementWithFee(item));
  return map;
}

function resolveExcelCode(code, memo, separators, fields) {
  if (!code || code === "(빈칸)") return "";
  if (code === "(컬럼메모에 입력한 값)" || code === "(엑셀수식)") return memo || "";
  if (code === "(오늘날짜)") return formatLocalDate(new Date());
  return String(code).replace(/\[([^\]]+)\]/g, (_, name) => {
    const separator = /^구분자(\d+)$/.exec(name);
    if (separator) {
      const value = (separators || [])[Number(separator[1]) - 1];
      return value == null ? "" : String(value);
    }
    return fields.get(name) || "";
  });
}

function downloadText(filename, text, type) {
  downloadBlob(filename, new Blob([text], { type }));
}

function downloadBlob(filename, blob) {
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

function xmlEscape(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&apos;" }[ch]));
}

function crc32(bytes) {
  let crc = 0xffffffff;
  for (let i = 0; i < bytes.length; i += 1) {
    crc ^= bytes[i];
    for (let bit = 0; bit < 8; bit += 1) crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1));
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function zipStore(files) {
  const encoder = new TextEncoder();
  const u16 = (value) => [value & 255, (value >> 8) & 255];
  const u32 = (value) => [value & 255, (value >> 8) & 255, (value >> 16) & 255, (value >> 24) & 255];
  const parts = [];
  const central = [];
  let offset = 0;
  files.forEach((file) => {
    const name = encoder.encode(file.name);
    const data = typeof file.data === "string" ? encoder.encode(file.data) : file.data;
    const crc = crc32(data);
    const local = Uint8Array.from([
      0x50, 0x4b, 0x03, 0x04, 20, 0, 0, 0, 0, 0, 0, 0, 0, 0,
      ...u32(crc), ...u32(data.length), ...u32(data.length), ...u16(name.length), 0, 0,
    ]);
    parts.push(local, name, data);
    central.push(Uint8Array.from([
      0x50, 0x4b, 0x01, 0x02, 20, 0, 20, 0, 0, 0, 0, 0, 0, 0, 0, 0,
      ...u32(crc), ...u32(data.length), ...u32(data.length), ...u16(name.length),
      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, ...u32(offset),
    ]), name);
    offset += local.length + name.length + data.length;
  });
  const centralStart = offset;
  let centralSize = 0;
  central.forEach((part) => { centralSize += part.length; });
  const end = Uint8Array.from([
    0x50, 0x4b, 0x05, 0x06, 0, 0, 0, 0,
    ...u16(files.length), ...u16(files.length), ...u32(centralSize), ...u32(centralStart), 0, 0,
  ]);
  const out = new Uint8Array(offset + centralSize + end.length);
  let cursor = 0;
  const write = (chunk) => { out.set(chunk, cursor); cursor += chunk.length; };
  parts.forEach(write);
  central.forEach(write);
  write(end);
  return out;
}

function excelColumnName(index) {
  let n = index + 1;
  let name = "";
  while (n > 0) {
    const rem = (n - 1) % 26;
    name = String.fromCharCode(65 + rem) + name;
    n = Math.floor((n - 1) / 26);
  }
  return name;
}

function sheetXmlText(value) {
  return String(value ?? "")
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, "")
    .replace(/[&<>]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[ch]));
}

function ordersToXlsx(form, rows) {
  const columns = form.columns || [];
  const lines = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'];
  const header = columns.map((column, index) => {
    const ref = `${excelColumnName(index)}1`;
    return `<c r="${ref}" s="1" t="inlineStr"><is><t xml:space="preserve">${sheetXmlText(column.title || "")}</t></is></c>`;
  }).join("");
  lines.push(`<row r="1">${header}</row>`);
  rows.forEach((item, rowIndex) => {
    const fields = excelFields(item, rowIndex);
    const cells = columns.map((column, index) => {
      const ref = `${excelColumnName(index)}${rowIndex + 2}`;
      const formula = column.code === "(엑셀수식)" ? String(column.memo || "").trim() : "";
      if (formula.startsWith("=")) return `<c r="${ref}"><f>${sheetXmlText(formula.slice(1))}</f></c>`;
      const value = resolveExcelCode(column.code, column.memo, form.separators || [], fields);
      return `<c r="${ref}" t="inlineStr"><is><t xml:space="preserve">${sheetXmlText(value)}</t></is></c>`;
    }).join("");
    lines.push(`<row r="${rowIndex + 2}">${cells}</row>`);
  });
  lines.push("</sheetData></worksheet>");
  const sheet = String(form.name || "주문").replace(/[\\/*?:[\]]/g, " ").slice(0, 31) || "주문";
  const files = [
    { name: "[Content_Types].xml", data: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>` },
    { name: "_rels/.rels", data: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>` },
    { name: "xl/workbook.xml", data: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="${sheetXmlText(sheet)}" sheetId="1" r:id="rId1"/></sheets>
</workbook>` },
    { name: "xl/_rels/workbook.xml.rels", data: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>` },
    { name: "xl/styles.xml", data: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="1"><font><sz val="11"/><name val="맑은 고딕"/></font></fonts>
<fills count="3">
<fill><patternFill patternType="none"/></fill>
<fill><patternFill patternType="gray125"/></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFFFFF00"/><bgColor indexed="64"/></patternFill></fill>
</fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="2">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="0" fillId="2" borderId="0" xfId="0" applyFill="1"/>
</cellXfs>
</styleSheet>` },
    { name: "xl/worksheets/sheet1.xml", data: lines.join("") },
  ];
  return zipStore(files);
}

function ordersToXls(form, rows) {
  return ordersToXlsx(form, rows);
}

function usableExcelForms() {
  const active = excelForms.filter((item) => item.in_use);
  return active.length ? active : excelForms.slice();
}

function preferredExcelForm(forms) {
  const market = markets.find((item) => item.id === orderCollectStore);
  const storeName = market?.name || "";
  if (storeName) {
    const hit = forms.find((form) => form.name && (storeName.includes(form.name) || form.name.includes(storeName)));
    if (hit) return hit;
  }
  return forms[0] || null;
}

function chosenExcelForms() {
  const forms = usableExcelForms();
  if ($("#excelExportMulti")?.checked) {
    return forms.filter((item) => excelExportIds.has(item.id));
  }
  return forms.filter((item) => item.id === $("#excelExportSelect")?.value).slice(0, 1);
}

function excelExportRows() {
  return excelExportTarget === "selected" ? selectedOrders() : visibleOrders();
}

function excelFileBase(form) {
  const tab = ORDER_TAB_TITLES[orderTab] || "주문";
  if (chosenExcelForms().length === 1 && excelFileNameTouched) {
    return ($("#excelExportFileName")?.value || `${tab}-${form?.name || "양식"}`).trim();
  }
  return `${tab}-${form?.name || "양식"}`;
}

function safeExcelName(name) {
  return String(name || "주문").replace(/[\\/:*?"<>|]/g, "_").replace(/\s+/g, " ").trim() || "주문";
}

function refreshExcelExportPreview() {
  const forms = usableExcelForms();
  const rows = excelExportRows();
  const multi = Boolean($("#excelExportMulti")?.checked);
  document.querySelectorAll("[data-excel-target]").forEach((button) => {
    button.classList.toggle("active", button.dataset.excelTarget === excelExportTarget);
  });
  if ($("#excelTargetAllCount")) $("#excelTargetAllCount").textContent = `${visibleOrders().length}건`;
  if ($("#excelTargetSelectedCount")) $("#excelTargetSelectedCount").textContent = `${selectedOrders().length}건`;
  if ($("#excelExportSelect")) $("#excelExportSelect").hidden = multi;
  const checks = $("#excelExportChecks");
  if (checks) {
    checks.hidden = !multi;
    if (multi && checks.childElementCount !== forms.length) {
      checks.replaceChildren();
      forms.forEach((item) => {
        const label = document.createElement("label");
        const input = document.createElement("input");
        input.type = "checkbox";
        input.value = item.id;
        input.checked = excelExportIds.has(item.id);
        input.addEventListener("change", () => {
          if (input.checked) excelExportIds.add(item.id);
          else excelExportIds.delete(item.id);
          excelFileNameTouched = false;
          refreshExcelExportPreview();
        });
        label.append(input, document.createTextNode(item.name || ""));
        checks.appendChild(label);
      });
    }
  }
  const picked = chosenExcelForms();
  const names = picked.map((item) => item.name).filter(Boolean);
  if ($("#excelFormPicked")) {
    $("#excelFormPicked").textContent = names.length ? `${names.join(", ")} 선택됨` : "양식을 선택하세요";
  }
  if ($("#excelPreviewTarget")) $("#excelPreviewTarget").textContent = excelExportTarget === "selected" ? "선택한 주문만" : "검색 결과 전체";
  if ($("#excelPreviewCount")) $("#excelPreviewCount").textContent = `${rows.length}건`;
  if ($("#excelPreviewForm")) $("#excelPreviewForm").textContent = names.join(", ") || "-";
  const fileInput = $("#excelExportFileName");
  if (fileInput) {
    fileInput.disabled = multi && picked.length > 1;
    if (!excelFileNameTouched) fileInput.value = excelFileBase(picked[0]);
  }
  const folder = excelSaveDirHandle?.name || excelSaveDirLabel;
  const formFolder = picked[0]?.name || "";
  if ($("#excelExportPath")) {
    $("#excelExportPath").textContent = folder ? `${folder}\\${formFolder}` : "다운로드 폴더";
  }
}

async function chooseExcelSaveDir() {
  if (!window.showDirectoryPicker) {
    toast("이 브라우저는 폴더 선택을 지원하지 않습니다. 파일은 다운로드 폴더에 저장됩니다.", true);
    return;
  }
  try {
    excelSaveDirHandle = await window.showDirectoryPicker({ mode: "readwrite" });
    excelSaveDirLabel = excelSaveDirHandle.name || "";
    localStorage.setItem("uploader-order-excel-dir", excelSaveDirLabel);
    refreshExcelExportPreview();
  } catch (error) {
    if (error?.name !== "AbortError") throw error;
  }
}

async function openExcelExportDialog() {
  if (!excelForms.length) {
    try {
      excelForms = await api("/api/excel-forms");
    } catch (error) {
      excelForms = [];
    }
  }
  const forms = usableExcelForms();
  const preferred = preferredExcelForm(forms);
  excelExportTarget = selectedOrders().length ? "selected" : "all";
  excelFileNameTouched = false;
  excelExportIds = new Set(preferred ? [preferred.id] : []);
  const select = $("#excelExportSelect");
  if (select) {
    select.replaceChildren();
    forms.forEach((item) => {
      const option = document.createElement("option");
      option.value = item.id;
      option.textContent = item.name;
      select.appendChild(option);
    });
    if (preferred) select.value = preferred.id;
  }
  if ($("#excelExportMulti")) $("#excelExportMulti").checked = false;
  if ($("#excelExportChecks")) $("#excelExportChecks").replaceChildren();
  if ($("#excelAutoSave")) $("#excelAutoSave").checked = localStorage.getItem("uploader-order-excel-autosave") === "1";
  if ($("#excelExportHelpText")) $("#excelExportHelpText").hidden = true;
  refreshExcelExportPreview();
  $("#excelExportDialog")?.showModal();
}

async function writeExcelFile(filename, blob) {
  const auto = $("#excelAutoSave")?.checked;
  if (auto && !excelSaveDirHandle) await chooseExcelSaveDir();
  if (auto && excelSaveDirHandle) {
    const handle = await excelSaveDirHandle.getFileHandle(filename, { create: true });
    const writable = await handle.createWritable();
    await writable.write(blob);
    await writable.close();
    return "folder";
  }
  downloadBlob(filename, blob);
  return "download";
}

async function runExcelExport() {
  const forms = chosenExcelForms();
  const rows = excelExportRows();
  if (!forms.length) {
    toast("사용할 엑셀 양식을 선택해 주세요.", true);
    return;
  }
  if (!rows.length) {
    toast("내보낼 주문이 없습니다.", true);
    return;
  }
  let where = "download";
  for (const form of forms) {
    const blob = new Blob([ordersToXlsx(form, rows)], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
    where = await writeExcelFile(`${safeExcelName(excelFileBase(form))}.xlsx`, blob);
  }
  $("#excelExportDialog")?.close();
  const place = where === "folder" ? "고른 폴더에" : "다운로드 폴더에";
  toast(`${forms.map((item) => item.name).join(", ")} 양식으로 ${rows.length}건을 ${place} 저장했습니다.`);
}

async function exportMenuOrders() {
  await openExcelExportDialog();
}

function renderExcelForms() {
  const body = $("#excelFormTable");
  if (!body) return;
  body.replaceChildren();
  if (!excelForms.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 10;
    cell.textContent = "등록된 엑셀 양식이 없습니다.";
    row.appendChild(cell);
    body.appendChild(row);
    return;
  }
  excelForms.forEach((item, index) => {
    const row = document.createElement("tr");
    const check = document.createElement("td");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = selectedExcelFormIds.has(item.id);
    input.addEventListener("click", (event) => {
      event.stopPropagation();
      if (input.checked) selectedExcelFormIds.add(item.id);
      else selectedExcelFormIds.delete(item.id);
    });
    check.appendChild(input);
    const edit = document.createElement("button");
    edit.type = "button";
    edit.className = "excel-edit";
    edit.textContent = "수정";
    edit.addEventListener("click", () => openExcelFormEditor(item));
    const copy = document.createElement("button");
    copy.type = "button";
    copy.className = "excel-copy";
    copy.textContent = "복사";
    copy.addEventListener("click", () => copyExcelForm(item.id).catch((error) => toast(error.message, true)));
    const use = document.createElement("button");
    use.type = "button";
    use.className = item.in_use ? "excel-use" : "excel-use off";
    use.textContent = item.in_use ? "사용" : "미사용";
    use.addEventListener("click", () => toggleExcelFormUse(item).catch((error) => toast(error.message, true)));
    row.append(
      check,
      textCell(index + 1),
      textCell(item.name || ""),
      buttonCell(edit),
      buttonCell(copy),
      buttonCell(use),
      textCell(item.author || ""),
      textCell(String(item.created_at || "").slice(0, 19)),
      textCell(item.updated_by || ""),
      textCell(String(item.updated_at || "").slice(0, 19)),
    );
    body.appendChild(row);
  });
  if ($("#excelFormCheckAll")) {
    $("#excelFormCheckAll").checked = excelForms.length > 0 && excelForms.every((item) => selectedExcelFormIds.has(item.id));
  }
}

function buttonCell(button) {
  const cell = document.createElement("td");
  cell.appendChild(button);
  return cell;
}

async function loadExcelForms() {
  excelForms = await api("/api/excel-forms");
  selectedExcelFormIds = new Set([...selectedExcelFormIds].filter((id) => excelForms.some((item) => item.id === id)));
  renderExcelForms();
  return excelForms;
}

function blankExcelColumns() {
  return Array.from({ length: 36 }, () => ({
    title: "",
    code: "(빈칸)",
    memo: "",
  }));
}

function renderExcelSeparators(values) {
  const box = $("#excelSeparators");
  if (!box) return;
  const source = values?.length ? values : ["/", "☞", "", "EA"];
  box.replaceChildren();
  for (let index = 0; index < 9; index += 1) {
    const label = document.createElement("label");
    label.append(document.createTextNode(`구분자${index + 1}`));
    const input = document.createElement("input");
    input.value = source[index] || "";
    input.dataset.separator = String(index);
    label.appendChild(input);
    box.appendChild(label);
  }
}

function readExcelSeparators() {
  return [...document.querySelectorAll("#excelSeparators input")].map((input) => input.value);
}

function excelValueSelect(current) {
  const select = document.createElement("select");
  select.dataset.field = "code";
  const codes = EXCEL_VALUE_CODES.slice();
  if (current && !codes.includes(current)) codes.unshift(current);
  codes.forEach((code) => {
    const option = document.createElement("option");
    option.value = code;
    option.textContent = code;
    select.appendChild(option);
  });
  select.value = current && codes.includes(current) ? current : "(빈칸)";
  return select;
}

function filterExcelValueOptions() {
  const query = ($("#excelValueSearch")?.value || "").trim();
  document.querySelectorAll("#excelColumnTable select[data-field='code']").forEach((select) => {
    [...select.options].forEach((option) => {
      option.hidden = Boolean(query) && option.value !== select.value && !option.value.includes(query);
    });
  });
}

function renderExcelColumnEditor(columns) {
  const body = $("#excelColumnTable");
  if (!body) return;
  body.replaceChildren();
  (columns.length ? columns : blankExcelColumns()).forEach((column) => body.appendChild(excelColumnRow(column)));
  renumberExcelColumns();
  filterExcelValueOptions();
}

function excelColumnRow(column) {
  const row = document.createElement("tr");
  const letter = document.createElement("td");
  letter.textContent = column.index || "";
  const title = document.createElement("input");
  title.value = column.title || "";
  title.dataset.field = "title";
  title.placeholder = "컬럼 제목을 입력하세요";
  const code = excelValueSelect(column.code || "(빈칸)");
  const memo = document.createElement("input");
  memo.value = column.memo || "";
  memo.dataset.field = "memo";
  memo.placeholder = "메모 입력";
  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "excel-remove";
  remove.textContent = "삭제";
  remove.addEventListener("click", (event) => {
    event.stopPropagation();
    if (excelEditRow === row) excelEditRow = row.nextElementSibling || row.previousElementSibling;
    row.remove();
    renumberExcelColumns();
    if (excelEditRow) markExcelRow(excelEditRow);
  });
  const insert = document.createElement("button");
  insert.type = "button";
  insert.className = "excel-insert";
  insert.textContent = "삽입";
  insert.addEventListener("click", (event) => {
    event.stopPropagation();
    insertExcelColumn(row);
  });
  const actions = document.createElement("td");
  actions.className = "excel-row-actions";
  actions.append(remove, insert);
  row.addEventListener("click", () => markExcelRow(row));
  row.append(letter, excelInputCell(title), excelInputCell(code), excelInputCell(memo), actions);
  return row;
}

function markExcelRow(row) {
  excelEditRow = row;
  document.querySelectorAll("#excelColumnTable tr").forEach((item) => item.classList.toggle("excel-row-current", item === row));
}

function insertExcelColumn(afterRow) {
  const row = excelColumnRow({ title: "", code: "(빈칸)", memo: "" });
  if (afterRow?.parentNode) afterRow.parentNode.insertBefore(row, afterRow.nextSibling);
  else $("#excelColumnTable")?.appendChild(row);
  renumberExcelColumns();
  markExcelRow(row);
  filterExcelValueOptions();
}

function moveExcelRow(direction) {
  const row = excelEditRow;
  if (!row?.parentNode) return;
  const sibling = direction < 0 ? row.previousElementSibling : row.nextElementSibling;
  if (!sibling) return;
  if (direction < 0) row.parentNode.insertBefore(row, sibling);
  else row.parentNode.insertBefore(sibling, row);
  renumberExcelColumns();
}

function excelInputCell(input) {
  const cell = document.createElement("td");
  cell.appendChild(input);
  return cell;
}

function renumberExcelColumns() {
  [...($("#excelColumnTable")?.rows || [])].forEach((row, index) => {
    let number = index + 1;
    let letters = "";
    while (number) {
      number -= 1;
      letters = String.fromCharCode(65 + (number % 26)) + letters;
      number = Math.floor(number / 26);
    }
    row.cells[0].textContent = letters;
  });
}

function readExcelColumnEditor() {
  return [...($("#excelColumnTable")?.rows || [])].map((row, index) => ({
    index: row.cells[0].textContent || "",
    title: row.querySelector("[data-field='title']")?.value || "",
    code: row.querySelector("[data-field='code']")?.value || "(빈칸)",
    memo: row.querySelector("[data-field='memo']")?.value || "",
  })).filter((column, index, list) => column.title || column.code !== "(빈칸)" || column.memo || index < list.length);
}

function openExcelFormEditor(item) {
  editingExcelFormId = item?.id || "";
  if ($("#excelFormDialogTitle")) $("#excelFormDialogTitle").textContent = item ? "엑셀 양식 수정" : "엑셀 양식 추가";
  if ($("#excelFormName")) $("#excelFormName").value = item?.name || "";
  if ($("#excelFormUse")) $("#excelFormUse").value = item && item.in_use === false ? "0" : "1";
  if ($("#excelValueSearch")) $("#excelValueSearch").value = "";
  excelEditRow = null;
  renderExcelSeparators(item?.separators);
  renderExcelColumnEditor(item?.columns?.length ? item.columns : blankExcelColumns());
  $("#excelFormDialog")?.showModal();
}

async function saveExcelFormEditor() {
  const name = ($("#excelFormName")?.value || "").trim();
  if (!name) {
    toast("양식 이름을 입력해 주세요.", true);
    $("#excelFormName")?.focus();
    return;
  }
  const payload = {
    name,
    in_use: $("#excelFormUse")?.value !== "0",
    columns: readExcelColumnEditor(),
    separators: readExcelSeparators(),
  };
  const saved = editingExcelFormId
    ? await api(`/api/excel-forms/${editingExcelFormId}`, { method: "PUT", body: JSON.stringify(payload) })
    : await api("/api/excel-forms", { method: "POST", body: JSON.stringify(payload) });
  $("#excelFormDialog")?.close();
  await loadExcelForms();
  toast(`${saved.name} 양식을 저장했습니다.`);
}

async function copyExcelForm(id) {
  await api(`/api/excel-forms/${id}/copy`, { method: "POST", body: "{}" });
  await loadExcelForms();
  toast("양식을 복사했습니다.");
}

async function toggleExcelFormUse(item) {
  await api(`/api/excel-forms/${item.id}`, { method: "PUT", body: JSON.stringify({ in_use: !item.in_use }) });
  await loadExcelForms();
}

async function deleteSelectedExcelForms() {
  const ids = [...selectedExcelFormIds];
  if (!ids.length) {
    toast("삭제할 양식을 선택해 주세요.", true);
    return;
  }
  await api("/api/excel-forms/delete", { method: "POST", body: JSON.stringify({ ids }) });
  selectedExcelFormIds.clear();
  await loadExcelForms();
  toast("선택한 양식을 삭제했습니다.");
}

function exportSelectedExcelForms() {
  const picked = excelForms.filter((item) => selectedExcelFormIds.has(item.id));
  const rows = picked.length ? picked : excelForms;
  if (!rows.length) {
    toast("내보낼 양식이 없습니다.", true);
    return;
  }
  const documents = rows.map((form) => ({
    ExcelFormName: form.name,
    Config: JSON.stringify({
      Seperators: form.separators || [],
      Columns: (form.columns || []).map((column) => ({
        ExcelAlphabetColumnIndex: column.index,
        ColumnTitle: column.title,
        ColumnValueCode: column.code,
        ColumnMemo: column.memo || null,
      })),
    }),
  }));
  downloadText(`엑셀양식_${formatLocalDate(new Date())}.json`, JSON.stringify(documents, null, 2), "application/json");
  toast(`${rows.length}개 양식을 내보냈습니다.`);
}

async function importExcelFormFile(file) {
  const payload = JSON.parse(await file.text());
  await api("/api/excel-forms/import", { method: "POST", body: JSON.stringify(payload) });
  await loadExcelForms();
  toast("양식을 불러왔습니다.");
}

function printOrderSheet() {
  const picked = selectedOrders();
  const rows = picked.length ? picked : visibleOrders();
  if (!rows.length) {
    toast("인쇄할 주문이 없습니다.", true);
    return;
  }
  const popup = window.open("", "orderPrint");
  if (!popup) {
    toast("인쇄 창을 열지 못했습니다.", true);
    return;
  }
  const labels = ["주문번호", "구매자", "수령자", "상품명", "선택사항", "수량", "주소", "구매자전화", "배송메모", "택배사", "송장번호"];
  const body = rows.map((item, index) => {
    const fields = new Map(orderDetailRows(item, index + 1).map((parts) => [parts[0], parts[1]]));
    const lines = labels.map((label) => `<tr><th>${escapeAttr(label)}</th><td>${escapeAttr(fields.get(label) || "")}</td></tr>`).join("");
    return `<section><h2>${index + 1}. ${escapeAttr(item.product_name || "주문")}</h2><table>${lines}</table></section>`;
  }).join("");
  popup.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>주문서</title><style>body{font-family:sans-serif}table{width:100%;border-collapse:collapse;margin-bottom:24px}th,td{border:1px solid #ccc;padding:6px;text-align:left}th{width:140px;background:#f6f6f6}</style></head><body><h1>주문서 ${rows.length}건</h1>${body}</body></html>`);
  popup.document.close();
  popup.focus();
  popup.print();
}

function openOrderStats() {
  if ($("#orderStatsBody")) $("#orderStatsBody").textContent = orderStatsText(visibleOrders());
  $("#orderStatsDialog")?.showModal();
}

function openWorkStats() {
  if ($("#orderWorkStatusText")) $("#orderWorkStatusText").value = orderWorkStatuses().join("\n");
  if ($("#orderWorkStatsBody")) $("#orderWorkStatsBody").textContent = orderStatsText(visibleOrders());
  $("#orderWorkStatsDialog")?.showModal();
}

function saveWorkStats() {
  const names = String($("#orderWorkStatusText")?.value || "").split(/\n+/).map((item) => item.trim()).filter(Boolean);
  if (!names.length) {
    toast("작업상태를 하나 이상 적어 주세요.", true);
    return;
  }
  localStorage.setItem("uploader-order-work-statuses", JSON.stringify(names));
  fillWorkStatusSelects();
  $("#orderWorkStatsDialog")?.close();
  renderOrders();
  toast("작업상태를 저장했습니다.");
}

function toggleExtraMenu() {
  const panel = $("#orderExtraPanel");
  if (panel) panel.hidden = !panel.hidden;
}

function runExtraOrderAction(name) {
  if ($("#orderExtraPanel")) $("#orderExtraPanel").hidden = true;
  if (name === "wholesale") {
    placeWholesaleOrders().catch((error) => toast(error.message, true));
    return;
  }
  if (name === "dispatch") {
    dispatchOrderInvoices().catch((error) => toast(error.message, true));
    return;
  }
  if (name === "invoice") {
    updateSelectedInvoices().catch((error) => toast(error.message, true));
    return;
  }
  if (name === "cancel") {
    const items = menuTargetOrders();
    if (items.length !== 1) {
      if (items.length) toast("판매취소는 한 건씩 할 수 있습니다.", true);
      return;
    }
    openOrderCancel(items[0]);
    return;
  }
  if (name === "cs" || name === "detail") {
    const items = menuTargetOrders();
    if (!items[0]) return;
    if (name === "cs") openCsMemo(items[0]);
    else focusOrder(items[0]);
  }
}

function selectedOrders() {
  const visible = new Set(visibleOrders().map((item) => item.id));
  return orders.filter((item) => selectedOrderIds.has(item.id) && visible.has(item.id));
}

function requireSelectedOrders() {
  const items = selectedOrders();
  if (!items.length) toast("먼저 주문을 선택해 주세요.", true);
  return items;
}

function formatOrderDate(value) {
  const text = String(value || "").replace("T", " ");
  return text.slice(0, 19);
}

function orderCheckCell(item) {
  const cell = document.createElement("td");
  cell.className = "check-cell";
  const input = document.createElement("input");
  input.type = "checkbox";
  input.checked = selectedOrderIds.has(item.id);
  input.addEventListener("click", (event) => {
    event.stopPropagation();
    if (input.checked) selectedOrderIds.add(item.id);
    else selectedOrderIds.delete(item.id);
    const visible = visibleOrders();
    const all = visible.length && visible.every((row) => selectedOrderIds.has(row.id));
    if ($("#orderCheckAll")) $("#orderCheckAll").checked = all;
    renderOrderSummary();
  });
  cell.appendChild(input);
  return cell;
}

function orderCourierCell(item) {
  const cell = document.createElement("td");
  const select = document.createElement("select");
  const current = courierCode(item.delivery_company);
  [["", "선택"]].concat(COURIERS).forEach(([value, label]) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    if (value === current) option.selected = true;
    select.appendChild(option);
  });
  select.addEventListener("change", () => {
    item.delivery_company = select.value;
    saveOrderPatch(item.id, { delivery_company: select.value }).catch((error) => toast(error.message, true));
  });
  cell.appendChild(select);
  return cell;
}

function invoiceDraft(item) {
  return invoiceDrafts.get(item.id) || { company: "", tracking: "" };
}

function mallCourierLabel(item) {
  const name = String(item.delivery_company_name || "").trim();
  if (item.delivery_company && name) return name;
  const method = String(item.delivery_method || "").trim();
  if (method && method !== "택배,등기,소포") return method;
  return item.tracking_number ? name : "직접전달";
}

function orderInvoiceEditCourierCell(item) {
  const cell = document.createElement("td");
  const select = document.createElement("select");
  const draft = invoiceDraft(item);
  [["", "선택"]].concat(COURIERS).forEach(([value, label]) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    if (value === draft.company) option.selected = true;
    select.appendChild(option);
  });
  select.addEventListener("change", () => {
    const current = invoiceDraft(item);
    invoiceDrafts.set(item.id, { company: select.value, tracking: current.tracking });
  });
  cell.appendChild(select);
  return cell;
}

function orderInvoiceEditTrackingCell(item) {
  const cell = document.createElement("td");
  const input = document.createElement("input");
  input.type = "text";
  input.value = invoiceDraft(item).tracking;
  const paint = () => input.classList.toggle("order-invoice-draft", Boolean(input.value.trim()));
  paint();
  input.addEventListener("input", () => {
    const current = invoiceDraft(item);
    invoiceDrafts.set(item.id, { company: current.company, tracking: input.value.trim() });
    paint();
  });
  cell.appendChild(input);
  return cell;
}

function orderMallCourierCell(item) {
  const cell = document.createElement("td");
  cell.textContent = mallCourierLabel(item);
  cell.classList.add(item.delivery_company ? "order-invoice-ok" : "order-invoice-empty");
  return cell;
}

function orderMallTrackingCell(item) {
  const cell = document.createElement("td");
  const text = item.tracking_number || "";
  cell.textContent = text;
  cell.classList.add(text ? "order-invoice-ok" : "order-invoice-empty");
  return cell;
}

function orderTrackingCell(item) {
  const cell = document.createElement("td");
  if (orderTab === "wait") cell.classList.add("order-invoice-cell");
  const input = document.createElement("input");
  input.type = "text";
  input.value = item.tracking_number || "";
  const paint = () => input.classList.toggle("order-invoice-filled", Boolean(input.value.trim()));
  paint();
  input.addEventListener("input", () => {
    item.tracking_number = input.value.trim();
    paint();
  });
  input.addEventListener("change", () => {
    saveOrderPatch(item.id, { tracking_number: input.value.trim() }, true).catch((error) => toast(error.message, true));
  });
  cell.appendChild(input);
  return cell;
}

function orderTraceCell(item) {
  return orderActionButton("배송추적", "order-trace-link", () => {
    const url = trackingUrl(item.delivery_company, item.tracking_number);
    if (!url) {
      toast("송장번호가 없습니다.", true);
      return;
    }
    window.open(url, "_blank", "noopener");
  });
}

async function saveOrderPatch(id, patch, quiet = false) {
  const saved = await api(`/api/orders/${id}`, { method: "PUT", body: JSON.stringify(patch), quiet });
  const index = orders.findIndex((item) => item.id === id);
  if (index >= 0) orders[index] = saved;
  else orders.push(saved);
  return saved;
}

function orderHasCs(item) {
  return Boolean(String(item?.cs_memo || "").trim() || String(item?.cs_status || "").trim());
}

function fillCsMallSelect() {
  const select = $("#csMallFilter");
  if (!select) return;
  fillSelectOptions(
    select,
    [["all", "(전체)"]].concat(accountChannels().map((item) => [item.id, mallLabel(item)])),
    select.value || "all",
  );
}

function csVisibleOrders(rows) {
  rows = rows.filter((item) => orderHasCs(item));
  const status = $("#csMemoFilter")?.value || "all";
  if (status !== "all") rows = rows.filter((item) => (item.cs_status || "미처리") === status);
  const mall = $("#csMallFilter")?.value || "all";
  if (mall !== "all") {
    rows = rows.filter((item) => (item.channel || marketOf(item.market_id)?.channel || "smartstore") === mall);
  }
  const basis = $("#csDateBasis")?.value || "order";
  const from = inquiryDateValue($("#csDateFrom")?.value);
  const to = inquiryDateValue($("#csDateTo")?.value);
  if (from || to) {
    rows = rows.filter((item) => {
      const day = inquiryDateValue(basis === "paid" ? item.payment_date || item.order_date : item.order_date);
      if (from && day && day < from) return false;
      if (to && day && day > to) return false;
      return true;
    });
  }
  const query = String(csQuery || "").trim().toLowerCase();
  if (query) {
    rows = rows.filter((item) => {
      const market = marketOf(item.market_id);
      const blob = [
        item.order_id, item.product_order_id, item.product_name, item.option, item.cs_memo,
        item.receiver_name, item.buyer_name, item.buyer_id, item.mall_id, market?.login_id,
      ].map((value) => String(value || "").toLowerCase()).join(" ");
      return blob.includes(query);
    });
  }
  rows.sort((left, right) => String(right.order_date || "").localeCompare(String(left.order_date || "")));
  return rows;
}

function csFocusedOrder() {
  const item = orders.find((row) => row.id === orderFocusId && orderHasCs(row));
  if (!item) {
    toast("목록에서 CS메모를 선택해 주세요.", true);
    return null;
  }
  return item;
}

async function markFocusedCsOpen() {
  const item = csFocusedOrder();
  if (!item) return;
  await saveOrderPatch(item.id, { cs_status: "미처리" });
  renderOrders();
  toast("미처리로 바꿨습니다.");
}

async function deleteFocusedCs() {
  const item = csFocusedOrder();
  if (!item) return;
  await saveOrderPatch(item.id, { cs_memo: "", cs_status: "" });
  if (csMemoOrderId === item.id) closeCsMemo();
  renderOrders();
  toast("CS메모를 삭제했습니다.");
}

function exportCsExcel() {
  const rows = visibleOrders();
  if (!rows.length) {
    toast("내보낼 CS메모가 없습니다.", true);
    return;
  }
  const headers = CS_SHEET_COLUMNS;
  const lines = [headers.join(",")];
  rows.forEach((item, index) => {
    const market = marketOf(item.market_id);
    const values = {
      "No.": index + 1,
      "CS상태": item.cs_status || "미처리",
      "쇼핑몰": mallLabel(item.channel || market?.channel || "smartstore"),
      "쇼핑몰ID": market?.login_id || item.mall_id || "",
      "주문일(역순)": shortOrderDay(item.order_date),
      "주문번호": item.order_id || item.product_order_id || "",
      "주문자": item.buyer_name || "",
      "메모": item.cs_memo || "",
      "url": orderProductUrl(item),
      "구매자ID": item.buyer_id || "",
      "구매자": item.buyer_name || "",
      "수령자": item.receiver_name || "",
      "상품명": item.product_name || "",
      "판매자상품코드": item.option || item.seller_product_code || "",
    };
    lines.push(headers.map((label) => csvEscape(values[label] ?? "")).join(","));
  });
  const blob = new Blob(["\uFEFF" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `CS메모_${formatLocalDate(new Date())}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
  toast(`${rows.length}건을 엑셀 파일로 만들었습니다.`);
}

function csMemoItem() {
  return orders.find((item) => item.id === csMemoOrderId) || null;
}

function fillCsMemoPanel(item) {
  const panel = $("#csMemoPanel");
  if (!panel || !item) return;
  const title = `${item.buyer_name || item.receiver_name || "주문"}/04.스마트스토어/${item.product_order_id || item.order_id || ""}`;
  if ($("#csMemoTitle")) $("#csMemoTitle").textContent = title;
  if ($("#csMemoText")) $("#csMemoText").value = item.cs_memo || "";
  const status = $("#csMemoStatus");
  if (status) {
    if (!orderHasCs(item)) status.textContent = "CS메모 없음.";
    else status.textContent = item.cs_status ? `${item.cs_status} · ${item.cs_memo ? "메모 있음" : "메모 없음"}` : "메모 있음";
  }
  panel.hidden = false;
}

function openCsMemo(item) {
  if (!item) return;
  if (!orders.some((row) => row.id === item.id)) orders.push(item);
  csMemoOrderId = item.id;
  focusOrder(item);
  fillCsMemoPanel(orders.find((row) => row.id === item.id) || item);
  $("#csMemoText")?.focus();
}

function closeCsMemo() {
  csMemoOrderId = "";
  if ($("#csMemoPanel")) $("#csMemoPanel").hidden = true;
}

async function saveCsMemo(status) {
  const item = csMemoItem();
  if (!item) return;
  const patch = { cs_memo: $("#csMemoText")?.value || "" };
  if (status !== undefined) patch.cs_status = status;
  else if (!item.cs_status && patch.cs_memo.trim()) patch.cs_status = "미처리";
  const saved = await saveOrderPatch(item.id, patch);
  fillCsMemoPanel(saved);
  renderOrders();
  if (status === "") toast("CS메모를 삭제했습니다.");
  else if (patch.cs_status) toast(`CS메모를 ${patch.cs_status}로 저장했습니다.`);
  else toast("CS메모를 저장했습니다.");
}

function orderMemoCell(item) {
  const cell = document.createElement("td");
  const input = document.createElement("input");
  input.type = "text";
  input.value = item.cs_memo || "";
  input.addEventListener("change", () => {
    saveOrderPatch(item.id, { cs_memo: input.value.trim() }, true).catch((error) => toast(error.message, true));
  });
  cell.appendChild(input);
  return cell;
}

function setOrderPeriod(kind) {
  applyPeriod(kind, "#orderDateFrom", "#orderDateTo", "#orderPeriod");
  renderOrders();
}

function applyTabDateBasis(tab) {
  const select = $("#orderDateBasis");
  if (!select) return;
  const dispatchTab = tab === "shipping" || tab === "delivered";
  if (dispatchTab) {
    if (select.value !== "dispatch") orderDateBasisMemory = select.value || "paid";
    select.value = "dispatch";
    return;
  }
  if (select.value === "dispatch") select.value = orderDateBasisMemory === "dispatch" ? "paid" : (orderDateBasisMemory || "paid");
}

function setOrderTab(name) {
  orderTab = name === "inquiries" || name === "urgent" ? "new" : (name || "new");
  applyTabDateBasis(orderTab);
  document.querySelectorAll("#orderStatusTabs [data-order-tab]").forEach((button) => {
    button.classList.toggle("active", button.dataset.orderTab === orderTab);
  });
  const wait = orderTab === "wait";
  const cs = orderTab === "cs";
  const excel = orderTab === "excel";
  if ($("#orderFilterBar")) $("#orderFilterBar").hidden = cs || excel;
  if ($("#csWorkBar")) $("#csWorkBar").hidden = !cs;
  if ($("#orderSummary")) $("#orderSummary").hidden = cs || excel;
  if ($("#excelFormPage")) $("#excelFormPage").hidden = !excel;
  if ($("#confirmOrdersButton")) $("#confirmOrdersButton").hidden = orderTab !== "new";
  $("#menuConfirmOrders")?.classList.toggle("order-accent", orderTab === "new");
  $("#menuExcel")?.classList.toggle("order-accent", orderTab === "new");
  if ($("#menuReplace")) $("#menuReplace").hidden = orderTab !== "new" && orderTab !== "wait";
  if ($("#placeWholesaleButton")) $("#placeWholesaleButton").hidden = !wait;
  if ($("#orderStopJobButton")) $("#orderStopJobButton").hidden = !wait && !orderJobsFor(orderTab).length;
  refreshOrderJobs();
  if ($("#orderWholesalerLabel")) $("#orderWholesalerLabel").hidden = !wait;
  if ($("#collectInvoiceButton")) $("#collectInvoiceButton").hidden = !wait;
  if ($("#dispatchInvoiceButton")) $("#dispatchInvoiceButton").hidden = orderTab !== "wait";
  if ($("#updateInvoiceButton")) $("#updateInvoiceButton").hidden = orderTab !== "shipping";
  if ($("#orderGridWrap")) $("#orderGridWrap").hidden = excel;
  const orderBody = document.querySelector("#viewOrders .order-body");
  if (orderBody) orderBody.hidden = excel;
  if ($("#orderActionBar")) $("#orderActionBar").hidden = excel;
  if (excel) {
    if ($("#orderDetail")) $("#orderDetail").hidden = true;
    if ($("#orderDetailResizer")) $("#orderDetailResizer").hidden = true;
    loadExcelForms().catch((error) => toast(error.message, true));
    return;
  }
  if (!$("#orderDateFrom")?.value) setOrderPeriod($("#orderPeriod")?.value || "2weeks");
  if (cs) {
    if (!$("#csDateFrom")?.value && $("#orderDateFrom")?.value) $("#csDateFrom").value = $("#orderDateFrom").value;
    if (!$("#csDateTo")?.value && $("#orderDateTo")?.value) $("#csDateTo").value = $("#orderDateTo").value;
    fillCsMallSelect();
    if ($("#orderDetail")) $("#orderDetail").hidden = true;
    if ($("#orderDetailResizer")) $("#orderDetailResizer").hidden = true;
  }
  renderOrders();
}

function askOrderConfirm(count) {
  const dialog = $("#orderConfirmDialog");
  const message = $("#orderConfirmMessage");
  if (!dialog || !message) return Promise.resolve(false);
  message.textContent = `[결제완료일]로부터 -영업일 이내에 발송불가한 경우,\n[지연예고] 처리를 하실것을 권합니다.\n(재고 확인 후 [주문확인] 하실것을 권합니다.)\n\n선택한 ${count}개의 주문을 [주문확인] 하시겠습니까?`;
  return new Promise((resolve) => {
    const finish = (ok) => {
      dialog.removeEventListener("close", onClose);
      dialog.removeEventListener("keydown", onKey);
      resolve(ok);
    };
    const onClose = () => finish(dialog.returnValue === "yes");
    const onKey = (event) => {
      const key = event.key.toLowerCase();
      if (key === "y") {
        event.preventDefault();
        dialog.close("yes");
      } else if (key === "n" || key === "escape") {
        event.preventDefault();
        dialog.close("no");
      }
    };
    dialog.addEventListener("close", onClose);
    dialog.addEventListener("keydown", onKey);
    if (dialog.open) dialog.close("no");
    dialog.showModal();
    $("#orderConfirmYes")?.focus();
  });
}

async function confirmSelectedOrders() {
  const tab = orderTab;
  const items = requireSelectedOrders();
  if (!items.length) return;
  if (!(await askOrderConfirm(items.length))) return;
  await runOrderTabJob(tab, "주문확인", async (signal) => {
    const result = await api("/api/orders/confirm", {
      method: "POST",
      detached: true,
      signal,
      body: JSON.stringify({ ids: items.map((item) => item.id) }),
    });
    await reloadOrders();
    const extra = (result.errors || []).filter(Boolean).join(" / ");
    toast(`${result.count || 0}건을 스마트스토어에서 주문확인했습니다.${extra ? ` ${extra}` : ""}`, Boolean(extra));
  });
}

function inquiriesForMarket(filter) {
  if (filter === "all") return inquiries;
  if (accountChannels().some((item) => item.id === filter)) {
    const ids = new Set(marketsForChannel(filter).map((item) => item.id));
    return inquiries.filter((item) => ids.has(item.market_id) || item.channel === filter);
  }
  return inquiries.filter((item) => item.market_id === filter);
}

function visibleInquiries() {
  if (inquiryStoreFilter && inquiryStoreFilter !== "all") {
    return inquiries.filter((item) => item.market_id === inquiryStoreFilter);
  }
  return inquiriesForMarket(inquiryChannelFilter);
}

function inquiryMarketOf(item) {
  return markets.find((row) => row.id === item.market_id) || null;
}

function inquiryMallId(item) {
  const market = inquiryMarketOf(item);
  return item.mall_id || market?.login_id || market?.slug || "";
}

function inquiryStoreName(item) {
  const market = inquiryMarketOf(item);
  return item.store_name || market?.name || item.market_name || "";
}

function inquiryAlias(item) {
  const market = inquiryMarketOf(item);
  return item.alias || market?.name || item.market_name || "";
}

function inquiryMemo(item) {
  const market = inquiryMarketOf(item);
  return item.memo || market?.memo || "";
}

function inquiryLinkCell(text, url) {
  const cell = document.createElement("td");
  const label = String(text || "").trim();
  if (url) {
    const link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.rel = "noopener";
    link.textContent = label || "열기";
    cell.appendChild(link);
  } else {
    cell.textContent = label;
  }
  cell.title = label;
  return cell;
}

function inquiryCheckCell(item) {
  const cell = document.createElement("td");
  cell.className = "check-cell";
  const input = document.createElement("input");
  input.type = "checkbox";
  input.checked = selectedInquiryIds.has(item.id);
  input.addEventListener("click", (event) => {
    event.stopPropagation();
    if (input.checked) selectedInquiryIds.add(item.id);
    else selectedInquiryIds.delete(item.id);
    updateInquirySelectionCount();
  });
  cell.appendChild(input);
  return cell;
}

function renderInquiryRows(body, rows, cols) {
  if (!body) return;
  body.innerHTML = "";
  if (!rows.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = cols;
    cell.textContent = "문의가 없습니다.";
    row.appendChild(cell);
    body.appendChild(row);
    return;
  }
  rows.forEach((item, index) => {
    const market = inquiryMarketOf(item);
    const row = document.createElement("tr");
    row.dataset.id = item.id;
    if (selectedInquiryIds.has(item.id)) row.classList.add("selected");
    if (item.id === currentInquiryId) row.classList.add("inquiry-current");
    row.addEventListener("click", (event) => {
      if (event.target.closest("input, a, button, select")) return;
      currentInquiryId = item.id;
      selectedInquiryIds.add(item.id);
      document.querySelectorAll("#inquiryTable tr[data-id]").forEach((line) => {
        const on = line.dataset.id === item.id;
        line.classList.toggle("inquiry-current", on);
        line.classList.toggle("selected", selectedInquiryIds.has(line.dataset.id));
        const box = line.querySelector("input[type='checkbox']");
        if (box) box.checked = selectedInquiryIds.has(line.dataset.id);
      });
      fillInquiryDetail(item);
      updateInquirySelectionCount();
    });
    row.append(
      inquiryCheckCell(item),
      textCell(index + 1),
      textCell(mallLabel(item.channel || market?.channel || "smartstore")),
      inquiryLinkCell(inquiryMallId(item), market?.url || ""),
      textCell(inquiryStoreName(item)),
      textCell(inquiryAlias(item)),
      textCell(inquiryMemo(item)),
      inquiryOrderCell(item),
      linkedNumberCell(item.product_no || "", smartstoreProductUrl(item.product_no, market), "스마트스토어 상품 페이지"),
      textCell(item.product_name || ""),
      textCell(formatOrderDate(item.created_at)),
      textCell(item.writer || ""),
      textCell(item.title || ""),
      textCell(item.status || "미답변"),
    );
    body.appendChild(row);
  });
}

function inquiryDateValue(value) {
  return String(value || "").slice(0, 10);
}

function shiftInquiryDate(base, days) {
  const date = new Date(base.getFullYear(), base.getMonth(), base.getDate() + days);
  return formatLocalDate(date);
}

const PERIOD_OPTIONS = [
  ["custom", "기간지정"],
  ["today", "오늘"],
  ["yesterday", "어제"],
  ["3days", "3일"],
  ["week", "일주일"],
  ["2weeks", "2주일"],
  ["month", "한달"],
  ["thisWeek", "이번 주"],
  ["prevWeek1", "1주 전주"],
  ["prevWeek2", "2주 전주"],
  ["prevWeek3", "3주 전주"],
  ["prevWeek4", "4주 전주"],
  ["prevWeek5", "5주 전주"],
  ["prevWeek6", "6주 전주"],
  ["prevWeek7", "7주 전주"],
  ["prevWeek8", "8주 전주"],
  ["prevWeek9", "9주 전주"],
  ["prevWeek10", "10주 전주"],
  ["3months", "세달"],
  ["halfYear", "반년"],
  ["year", "일년"],
  ["thisMonth", "이달"],
  ["lastMonth", "전달"],
  ["monthBeforeLast", "전전달"],
  ["thisYear", "올해"],
  ["lastYear", "작년"],
  ["yearBeforeLast", "재작년"],
];

function formatLocalDate(date) {
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

function startOfWeek(date) {
  const day = date.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() + diff);
}

function periodRange(kind) {
  const today = new Date();
  const from = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const to = new Date(from);
  if (kind === "today") return [from, to];
  if (kind === "yesterday") {
    from.setDate(from.getDate() - 1);
    return [from, from];
  }
  if (kind === "3days") { from.setDate(from.getDate() - 2); return [from, to]; }
  if (kind === "week") { from.setDate(from.getDate() - 6); return [from, to]; }
  if (kind === "2weeks") { from.setDate(from.getDate() - 13); return [from, to]; }
  if (kind === "month") { from.setMonth(from.getMonth() - 1); return [from, to]; }
  if (kind === "thisWeek") return [startOfWeek(from), to];
  if (String(kind).startsWith("prevWeek")) {
    const weeks = Number(String(kind).replace("prevWeek", "")) || 1;
    const start = startOfWeek(from);
    start.setDate(start.getDate() - 7 * weeks);
    const end = new Date(start.getFullYear(), start.getMonth(), start.getDate() + 6);
    return [start, end];
  }
  if (kind === "3months") { from.setMonth(from.getMonth() - 3); return [from, to]; }
  if (kind === "halfYear") { from.setMonth(from.getMonth() - 6); return [from, to]; }
  if (kind === "year") { from.setFullYear(from.getFullYear() - 1); return [from, to]; }
  if (kind === "thisMonth") return [new Date(from.getFullYear(), from.getMonth(), 1), to];
  if (kind === "lastMonth") {
    return [
      new Date(from.getFullYear(), from.getMonth() - 1, 1),
      new Date(from.getFullYear(), from.getMonth(), 0),
    ];
  }
  if (kind === "monthBeforeLast") {
    return [
      new Date(from.getFullYear(), from.getMonth() - 2, 1),
      new Date(from.getFullYear(), from.getMonth() - 1, 0),
    ];
  }
  if (kind === "thisYear") return [new Date(from.getFullYear(), 0, 1), to];
  if (kind === "lastYear") {
    return [new Date(from.getFullYear() - 1, 0, 1), new Date(from.getFullYear() - 1, 11, 31)];
  }
  if (kind === "yearBeforeLast") {
    return [new Date(from.getFullYear() - 2, 0, 1), new Date(from.getFullYear() - 2, 11, 31)];
  }
  return [from, to];
}

function fillPeriodSelect(select, selected) {
  if (!select) return;
  const current = selected || select.value || "2weeks";
  select.innerHTML = "";
  PERIOD_OPTIONS.forEach(([value, label]) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.appendChild(option);
  });
  select.value = PERIOD_OPTIONS.some((item) => item[0] === current) ? current : "2weeks";
}

fillPeriodSelect($("#orderPeriod"), "2weeks");
fillPeriodSelect($("#inquiryPeriod"), "month");
fillPeriodSelect($("#csPeriod"), "month");

function applyPeriod(kind, fromId, toId, selectId) {
  if (!kind || kind === "custom") {
    if ($(selectId)) $(selectId).value = "custom";
    return;
  }
  const [from, to] = periodRange(kind);
  if ($(fromId)) $(fromId).value = formatLocalDate(from);
  if ($(toId)) $(toId).value = formatLocalDate(to);
  if ($(selectId)) $(selectId).value = kind;
}

function updateInquiryPeriodButtons() {
  const kind = $("#inquiryPeriod")?.value;
  document.querySelectorAll("[data-inquiry-period]").forEach((button) => {
    button.classList.toggle("active", button.dataset.inquiryPeriod === kind);
  });
}

function setInquiryPeriod(kind) {
  applyPeriod(kind, "#inquiryDateFrom", "#inquiryDateTo", "#inquiryPeriod");
  updateInquiryPeriodButtons();
  renderInquiryList();
}

function resetInquiryFilters() {
  inquiryChannelFilter = "all";
  inquiryStoreFilter = "all";
  selectedInquiryIds.clear();
  if ($("#inquiryStatusFilter")) $("#inquiryStatusFilter").value = "unanswered";
  fillInquiryMallSelects();
  setInquiryPeriod("month");
}

function filteredInquiries() {
  const from = inquiryDateValue($("#inquiryDateFrom")?.value);
  const to = inquiryDateValue($("#inquiryDateTo")?.value);
  const status = $("#inquiryStatusFilter")?.value || "unanswered";
  return visibleInquiries().filter((item) => {
    const day = inquiryDateValue(item.created_at);
    if (from && day && day < from) return false;
    if (to && day && day > to) return false;
    const answered = String(item.status || "").includes("완료") || String(item.answer || "").trim();
    if (status === "unanswered") return !answered;
    if (status === "answered") return answered;
    return true;
  });
}

function inquiryWriterText(item) {
  const name = String(item?.writer || "").trim();
  const note = String(item?.writer_note || "").trim();
  if (name && note) return `${name}(${note})`;
  return name || note;
}

function inquiryTitleText(item) {
  const title = String(item?.title || "").trim();
  if (title && title !== String(item?.content || "").trim()) return title;
  if (item?.product_name && item?.kind !== "customer") return `[상품Q&A]${item.product_name}`;
  return title;
}

function fillInquiryDetail(item) {
  const panel = $("#inquiryDetail");
  if (!panel || !item) return;
  const same = panel.dataset.id === item.id;
  panel.hidden = false;
  panel.dataset.id = item.id;
  const market = inquiryMarketOf(item);
  if ($("#inquiryMall")) $("#inquiryMall").textContent = mallLabel(item.channel || market?.channel || "smartstore");
  if ($("#inquiryMallId")) $("#inquiryMallId").textContent = inquiryMallId(item);
  if ($("#inquiryState")) $("#inquiryState").textContent = item.status || "미답변";
  if ($("#inquiryWhen")) $("#inquiryWhen").textContent = formatOrderDate(item.created_at);
  if ($("#inquiryWriter")) $("#inquiryWriter").textContent = inquiryWriterText(item);
  const productHref = smartstoreProductUrl(item.product_no, market);
  setLinkedText($("#inquiryProductNo"), item.product_no || "", productHref, "스마트스토어 상품 페이지");
  setLinkedText($("#inquiryProductName"), item.product_name || "", productHref, "스마트스토어 상품 페이지");
  if ($("#inquiryTitle")) $("#inquiryTitle").textContent = inquiryTitleText(item);
  if ($("#inquiryContent")) {
    $("#inquiryContent").value = item.content || "";
    $("#inquiryContent").readOnly = true;
  }
  const answered = String(item.answer || "").trim();
  const oldWrap = $("#inquiryOldWrap");
  if (oldWrap) oldWrap.hidden = !answered;
  $("#inquiryPaneBasic")?.classList.toggle("inquiry-no-old", !answered);
  if ($("#inquiryAnswerView")) {
    $("#inquiryAnswerView").value = answered;
    $("#inquiryAnswerView").readOnly = true;
  }
  if ($("#inquiryAnswerAt")) {
    $("#inquiryAnswerAt").value = item.answer_at ? formatOrderDate(item.answer_at) : "";
    $("#inquiryAnswerAt").readOnly = true;
  }
  const draft = $("#inquiryAnswerDraft");
  const title = $("#inquiryAnswerTitle");
  if (draft) {
    draft.readOnly = false;
    draft.disabled = false;
    draft.removeAttribute("readonly");
    draft.removeAttribute("disabled");
  }
  if (title) {
    title.readOnly = false;
    title.disabled = false;
  }
  if (!same) {
    if (title) title.value = "";
    if (draft) draft.value = "";
  }
  updateInquiryBatchCount();
  loadInquiryTemplates(item.market_id).catch(() => {});
  const batch = $("#inquiryPaneBatch") && !$("#inquiryPaneBatch").hidden;
  const focusTarget = batch ? $("#inquiryBatchBody") : draft;
  if (focusTarget) {
    requestAnimationFrame(() => {
      try {
        focusTarget.focus({ preventScroll: true });
      } catch (_) {
        focusTarget.focus();
      }
    });
  }
}

function updateInquiryBatchCount() {
  const count = filteredInquiries().filter((item) => selectedInquiryIds.has(item.id)).length;
  if ($("#inquiryBatchCount")) $("#inquiryBatchCount").textContent = String(count);
}

async function loadInquiryTemplates(marketId) {
  const select = $("#inquiryTemplate");
  if (!select || !marketId) return;
  if (!inquiryTemplateCache[marketId]) {
    try {
      inquiryTemplateCache[marketId] = await api(`/api/inquiries/templates?market_id=${encodeURIComponent(marketId)}`);
    } catch (error) {
      inquiryTemplateCache[marketId] = [];
    }
  }
  const current = select.value;
  select.innerHTML = "";
  const blank = document.createElement("option");
  blank.value = "";
  blank.textContent = "사용 방법 및 안내 사항";
  select.appendChild(blank);
  (inquiryTemplateCache[marketId] || []).forEach((item, index) => {
    const option = document.createElement("option");
    option.value = String(index + 1);
    option.textContent = item.title || "답변 템플릿";
    option.dataset.title = item.title || "";
    option.dataset.content = item.content || "";
    select.appendChild(option);
  });
  if ([...select.options].some((item) => item.value === current)) select.value = current;
}

function applyInquiryTemplate() {
  const option = $("#inquiryTemplate")?.selectedOptions?.[0];
  if (!option || !option.value) return;
  const batch = $("#inquiryPaneBatch") && !$("#inquiryPaneBatch").hidden;
  const title = batch ? $("#inquiryBatchTitle") : $("#inquiryAnswerTitle");
  const body = batch ? $("#inquiryBatchBody") : $("#inquiryAnswerDraft");
  if (title && !title.value) title.value = option.dataset.title || "";
  if (body) body.value = option.dataset.content || body.value;
}

async function sendInquiryAnswer() {
  const batch = $("#inquiryPaneBatch") && !$("#inquiryPaneBatch").hidden;
  const targets = batch
    ? filteredInquiries().filter((item) => selectedInquiryIds.has(item.id))
    : inquiries.filter((item) => item.id === currentInquiryId);
  const title = (batch ? $("#inquiryBatchTitle") : $("#inquiryAnswerTitle"))?.value || "";
  const answer = (batch ? $("#inquiryBatchBody") : $("#inquiryAnswerDraft"))?.value || "";
  if (!targets.length) throw new Error("답변할 문의를 선택해 주세요.");
  if (!answer.trim()) throw new Error("새 답변 내용을 입력해 주세요.");
  setBusy(true, "스마트스토어에 답변을 보내는 중입니다.", "inquiries");
  try {
    let count = 0;
    for (const item of targets) {
      throwIfCancelled("inquiries");
      const saved = await api(`/api/inquiries/${item.id}/answer`, {
        method: "POST",
        body: JSON.stringify({ answer, title }),
      });
      const index = inquiries.findIndex((row) => row.id === item.id);
      if (index >= 0) inquiries[index] = saved;
      count += 1;
    }
    const current = inquiries.find((row) => row.id === currentInquiryId);
    if (current) {
      const panel = $("#inquiryDetail");
      if (panel) panel.dataset.id = "";
      fillInquiryDetail(current);
    }
    renderInquiryList();
    toast(`${count}건 답변을 보냈습니다.`);
    log(`문의 답변 ${count}건을 보냈습니다.`, "ok");
  } finally {
    setBusy(false, "", "inquiries");
  }
}

function updateInquirySelectionCount() {
  const visible = new Set(filteredInquiries().map((item) => item.id));
  const selected = [...selectedInquiryIds].filter((id) => visible.has(id)).length;
  if ($("#inquirySelectedCount")) $("#inquirySelectedCount").textContent = `${selected}건`;
  const rows = filteredInquiries();
  if ($("#inquiryCheckAll")) $("#inquiryCheckAll").checked = Boolean(rows.length && rows.every((item) => selectedInquiryIds.has(item.id)));
}

function formatInquiryUpdated(date) {
  const pad = (value) => String(value).padStart(2, "0");
  return `${date.getFullYear()}.${pad(date.getMonth() + 1)}.${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function renderInquiryList() {
  selectedInquiryIds = new Set([...selectedInquiryIds].filter((id) => inquiries.some((item) => item.id === id)));
  const rows = filteredInquiries();
  if ($("#inquiryFilterCount")) $("#inquiryFilterCount").textContent = `${rows.length}건`;
  if ($("#inquiryUpdatedAt")) {
    $("#inquiryUpdatedAt").textContent = inquiryUpdatedAt ? `최근 업데이트 ${inquiryUpdatedAt}` : "최근 업데이트 -";
  }
  renderInquiryRows($("#inquiryTable"), rows, 14);
  if (currentInquiryId && !rows.some((item) => item.id === currentInquiryId)) {
    currentInquiryId = "";
    if ($("#inquiryDetail")) $("#inquiryDetail").hidden = true;
  }
  updateInquirySelectionCount();
  updateInquiryPeriodButtons();
}

function collectInquiries() {
  importMarketInquiries().catch((error) => toast(error.message, true));
}

async function importMarketInquiries() {
  const targets = smartstoreTargets(inquiryTargetMarkets());
  if (!targets.length) throw new Error("스마트스토어 마켓을 고르세요. 설정 > 마켓관리에서 스토어를 등록하세요.");
  setBusy(true, "스마트스토어 문의를 불러오는 중입니다.", "inquiries");
  try {
    let total = 0;
    const errors = [];
    for (const market of targets) {
      throwIfCancelled("inquiries");
      try {
        const result = await api("/api/inquiries/import", {
          method: "POST",
          body: JSON.stringify({
            market_id: market.id,
            started: $("#inquiryDateFrom")?.value || "",
            ended: $("#inquiryDateTo")?.value || "",
          }),
        });
        total += Number(result.count || 0);
        log(`${market.name || "마켓"} 문의 ${result.count || 0}건을 불러왔습니다.`, "ok");
        (result.errors || []).forEach((message) => log(`${market.name || "마켓"} 문의 일부: ${message}`, "err"));
      } catch (error) {
        if (isAbortError(error)) throw error;
        errors.push(`${market.name || "마켓"}: ${error.message}`);
        log(`${market.name || "마켓"} 문의를 가져오지 못했습니다. ${error.message}`, "err");
      }
    }
    inquiryUpdatedAt = formatInquiryUpdated(new Date());
    await loadInquiries();
    log(`문의 ${total}건을 불러왔습니다.`, total ? "ok" : "");
    if (errors.length) toast(errors[0], true);
    else toast(`문의 ${total}건을 불러왔습니다.`);
  } catch (error) {
    if (isAbortError(error)) {
      log("작업을 중단했습니다.");
      toast("작업을 중단했습니다.");
      return;
    }
    throw error;
  } finally {
    setBusy(false, "", "inquiries");
  }
}

function csvEscape(value) {
  const text = String(value ?? "");
  if (/[",\n]/.test(text)) return `"${text.replace(/"/g, '""')}"`;
  return text;
}

function exportInquiryExcel() {
  const rows = filteredInquiries();
  if (!rows.length) {
    toast("내보낼 문의가 없습니다.", true);
    return;
  }
  const headers = ["No.", "쇼핑몰", "쇼핑몰ID", "스토어명", "별칭(쇼핑몰계정)", "메모(쇼핑몰계정)", "주문번호", "상품번호", "상품명", "문의일", "작성자", "제목", "상태"];
  const lines = [headers.join(",")];
  rows.forEach((item, index) => {
    const market = inquiryMarketOf(item);
    lines.push([
      index + 1,
      mallLabel(item.channel || market?.channel || "smartstore"),
      inquiryMallId(item),
      inquiryStoreName(item),
      inquiryAlias(item),
      inquiryMemo(item),
      item.order_id || "",
      item.product_no || "",
      item.product_name || "",
      formatOrderDate(item.created_at),
      item.writer || "",
      item.title || "",
      item.status || "미답변",
    ].map(csvEscape).join(","));
  });
  const blob = new Blob(["\uFEFF" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `문의관리_${formatLocalDate(new Date())}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
  toast(`${rows.length}건을 엑셀 파일로 만들었습니다.`);
}

async function loadInquiries() {
  inquiries = await api("/api/inquiries");
  fillInquiryMallSelects();
  renderInquiryList();
  return inquiries;
}

const CS_SHEET_COLUMNS = [
  "No.", "CS상태", "쇼핑몰", "쇼핑몰ID", "주문일(역순)", "주문번호", "주문자", "메모", "url",
  "구매자ID", "구매자", "수령자", "상품명", "판매자상품코드",
];

const ORDER_SHEET_COLUMNS = [
  "No.", "주문상태", "CS", "쇼핑몰", "별칭(쇼핑몰계정)", "주문일(약식)", "구매자", "수령자",
  "주문번호", "공급처", "판매취소하기", "상품번호", "상품명", "선택사항",
  "수량", "단가", "추가구성", "수령자전화번호", "구매자전화",
  "우편번호", "주소", "배송메모", "CS메모", "배송구분", "총주문금액", "옵션추가금액", "마켓수수료금액",
  "수수료율", "실수수료율", "공급금액", "배송비", "할인금액", "정산예상금액", "정산내역",
  "원가합계", "정산예정", "마진", "마진율",
  "주문일시", "결제일시", "클레임접수일시", "발송예정일", "배송번호", "주문자ID", "상품URL",
  "판매자상품코드", "판매자옵션코드", "쇼핑몰계정고유번호", "스토어명", "개인통관고유부호",
  "스마트주문상태", "송장입력", "보류여부", "도서산간", "정산추가정보", "발송일시", "결제수단",
  "배송방법", "실결제금액", "송장번호입력일시", "송장상품수량", "추가구성수량", "톡톡하기",
  "주문일자(yyyyMMdd)", "송장실결제금액", "송장총주문금액", "작업상태", "메모(쇼핑몰계정)",
  "택배사", "송장번호", "발송",
];

function orderGridColumns() {
  if (orderTab === "cs") return CS_SHEET_COLUMNS;
  if (orderTab === "shipping") return ["택배사(수정용)", "송장번호(수정용)", "택배사(쇼핑몰)", "송장번호(쇼핑몰)", ...ORDER_SHEET_COLUMNS];
  if (orderTab !== "wait") return ORDER_SHEET_COLUMNS;
  const columns = ORDER_SHEET_COLUMNS.filter((title) => !["택배사", "송장번호", "판매취소하기"].includes(title));
  const at = columns.indexOf("공급처");
  columns.splice(at + 1, 0, "택배사", "송장번호", "배송추적", "판매취소하기");
  return columns;
}

function ensureOrderGrid() {
  const table = $("#orderGrid");
  const hiddenKey = orderTab === "cs" ? "" : loadNameList("uploader-order-hidden-cols").join("|");
  const mode = `${orderTab === "cs" ? "cs" : orderTab === "shipping" ? "shipping" : orderTab === "wait" ? "wait" : "base"}:phone2:${hiddenKey}`;
  if (!table || table.dataset.sheet === mode) return;
  const titles = orderTab === "cs" ? displayedOrderColumns() : ["", ...displayedOrderColumns()];
  const widths = {
    "": "36px",
    "No.": "46px",
    "CS상태": "72px",
    "주문상태": "118px",
    "CS": "52px",
    "쇼핑몰": "108px",
    "주문일(역순)": "96px",
    "주문자": "84px",
    "메모": "180px",
    "url": "180px",
    "구매자ID": "120px",
    "판매자상품코드": "180px",
    "별칭(쇼핑몰계정)": "150px",
    "쇼핑몰ID": "120px",
    "주문일(약식)": "88px",
    "구매자": "84px",
    "수령자": "84px",
    "수령자전화번호": "132px",
    "구매자전화": "132px",
    "구매자휴대전화": "132px",
    "원가합계": "96px",
    "정산예정": "96px",
    "마진": "96px",
    "마진율": "84px",
    "주문번호": "150px",
    "공급처": "120px",
    "판매취소하기": "96px",
    "배송추적": "84px",
    "상품번호": "120px",
    "상품명": "240px",
    "선택사항": "160px",
    "수량": "56px",
    "단가": "96px",
    "택배사(수정용)": "120px",
    "송장번호(수정용)": "148px",
    "택배사(쇼핑몰)": "120px",
    "송장번호(쇼핑몰)": "148px",
    "주소": "420px",
    "배송메모": "280px",
    "정산추가정보": "260px",
    "상품URL": "220px",
    "배송번호": "150px",
  };
  const colgroup = document.createElement("colgroup");
  const headRow = document.createElement("tr");
  titles.forEach((title, index) => {
    const col = document.createElement("col");
    col.dataset.col = title ? `ord-${title}` : "check";
    col.style.width = widths[title] || "120px";
    colgroup.appendChild(col);
    const th = document.createElement("th");
    if (!title) {
      const input = document.createElement("input");
      input.id = "orderCheckAll";
      input.type = "checkbox";
      th.appendChild(input);
    } else {
      th.textContent = title;
      const sortKey = ORDER_SORTABLE[title];
      if (sortKey) {
        th.classList.add("sortable");
        th.dataset.sort = sortKey;
        th.title = `${title}순 정렬`;
      }
    }
    if (title === "수량") th.classList.add("align-center");
    if (title === "단가") th.classList.add("align-end");
    headRow.appendChild(th);
  });
  table.querySelector("colgroup")?.replaceWith(colgroup);
  table.tHead.replaceChildren(headRow);
  table.dataset.sheet = mode;
  enableColumnResize(table);
}

function orderSheetCell(item, label, value, emphasis, link, href) {
  if (orderTab === "cs" && label === "주문번호") {
    return orderActionButton(item.order_id || item.product_order_id || "", "order-no-link", () => openCsMemo(item));
  }
  if (orderTab === "cs" && label === "CS상태") {
    const cell = document.createElement("td");
    const status = item.cs_status || "미처리";
    cell.textContent = status;
    cell.className = status === "처리완료" ? "cs-status-done" : status === "준비" ? "cs-status-ready" : "cs-status-open";
    return cell;
  }
  if (orderTab === "cs" && label === "쇼핑몰") {
    const cell = textCell(mallLabel(item.channel || marketOf(item.market_id)?.channel || "smartstore"));
    return cell;
  }
  if (orderTab === "cs" && label === "쇼핑몰ID") {
    const market = marketOf(item.market_id);
    const id = market?.login_id || item.mall_id || "";
    const cell = textCell(id);
    if (id) cell.classList.add("cs-link");
    return cell;
  }
  if (orderTab === "cs" && label === "주문일(역순)") return textCell(shortOrderDay(item.order_date));
  if (orderTab === "cs" && label === "주문자") return textCell(item.buyer_name || "");
  if (orderTab === "cs" && label === "메모") return textCell(item.cs_memo || "");
  if (orderTab === "cs" && label === "url") {
    const href = orderProductUrl(item);
    const cell = document.createElement("td");
    if (href) {
      const anchor = document.createElement("a");
      anchor.href = href;
      anchor.target = "_blank";
      anchor.rel = "noreferrer";
      anchor.className = "cs-link";
      anchor.textContent = href;
      cell.appendChild(anchor);
    }
    return cell;
  }
  if (orderTab === "cs" && label === "구매자ID") return textCell(item.buyer_id || "");
  if (orderTab === "cs" && label === "판매자상품코드") return textCell(item.option || item.seller_product_code || "");
  if (label === "주문번호" || label === "상품주문번호(스마트스토어)") return orderNumberCell(item);
  if (label === "판매취소하기") return orderCancelCell(item);
  if (label === "배송추적") return orderTraceCell(item);
  if (label === "상품번호") return orderProductCell(item);
  if (label === "택배사(수정용)") return orderInvoiceEditCourierCell(item);
  if (label === "송장번호(수정용)") return orderInvoiceEditTrackingCell(item);
  if (label === "택배사(쇼핑몰)") return orderMallCourierCell(item);
  if (label === "송장번호(쇼핑몰)") return orderMallTrackingCell(item);
  if (label === "택배사") return orderCourierCell(item);
  if (label === "송장번호") return orderTrackingCell(item);
  if (label === "CS메모") return orderMemoCell(item);
  if (label === "CS") {
    const cell = orderActionButton("CS", orderHasCs(item) ? "order-no-link order-cs-active" : "order-no-link", () => openCsMemo(item));
    return cell;
  }
  const cell = document.createElement("td");
  const text = value === undefined || value === null ? "" : String(value);
  if (emphasis) cell.classList.add("emphasis");
  if (label === "수량") cell.classList.add("align-center");
  if (["단가", "원가합계", "정산예정", "마진", "마진율"].includes(label)) cell.classList.add("align-end");
  if (label === "배송구분" && text === "착불") cell.classList.add("order-cod");
  if (label === "주문상태" && orderBucket(item) === "new") cell.classList.add("order-status-new");
  const target = href || (link ? text : "");
  if (link && text && target) {
    const anchor = document.createElement("a");
    anchor.href = target;
    anchor.target = "_blank";
    anchor.rel = "noreferrer";
    anchor.textContent = text;
    cell.appendChild(anchor);
  } else cell.textContent = text;
  return cell;
}

function focusOrder(item) {
  selectedOrderIds.clear();
  selectedOrderIds.add(item.id);
  orderFocusId = item.id;
  renderOrders();
}

function isInstallFee(item) {
  const name = String(item.product_name || "").trim();
  const option = String(item.option || "").trim();
  return name === "설치비" || option.startsWith("설치비");
}

function placeInstallDeliveryFees(items) {
  const groups = new Map();
  items.forEach((item) => {
    const key = String(item.package_number || "").trim();
    if (!key) return;
    const group = groups.get(key) || [];
    group.push(item);
    groups.set(key, group);
  });
  groups.forEach((group) => {
    if (group.length < 2) return;
    const positive = group.map((item) => Number(item.delivery_fee) || 0).filter((fee) => fee > 0);
    if (!positive.length) return;
    const install = group.find(isInstallFee);
    const repeated = positive.length > 1 && positive.every((fee) => fee === positive[0]);
    if (!install && !repeated) return;
    const fee = Math.max(...positive);
    const keeper = install || group[0];
    group.forEach((item) => {
      item.delivery_fee = item === keeper ? fee : 0;
    });
  });
}

function renderOrders() {
  replacePhoneCache = null;
  const body = $("#orderTable");
  if (!body) return;
  placeInstallDeliveryFees(orders);
  ensureOrderGrid();
  updateOrderSortHeaders();
  const rows = visibleOrders();
  body.innerHTML = "";
  if ($("#orderFilterCount")) $("#orderFilterCount").textContent = ordersCollected ? `${rows.length}건` : "";
  const all = rows.length && rows.every((item) => selectedOrderIds.has(item.id));
  if ($("#orderCheckAll")) $("#orderCheckAll").checked = Boolean(all);
  if (!rows.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = (orderTab === "cs" ? 0 : 1) + displayedOrderColumns().length;
    cell.textContent = ordersCollected ? (orderTab === "cs" ? "조회된 CS메모가 없습니다." : "주문이 없습니다.") : "수집하기를 누르면 주문을 불러옵니다.";
    row.appendChild(cell);
    body.appendChild(row);
    renderOrderDetail();
    renderOrderSummary();
    return;
  }
  const orderCounts = new Map();
  const orderToneKey = (item) => String(item.order_id || item.package_number || "").trim();
  rows.forEach((item) => {
    const key = orderToneKey(item);
    if (!key) return;
    orderCounts.set(key, (orderCounts.get(key) || 0) + 1);
  });
  const toneByOrder = new Map();
  rows.forEach((item) => {
    const key = orderToneKey(item);
    if (!key || orderCounts.get(key) < 2 || toneByOrder.has(key)) return;
    toneByOrder.set(key, toneByOrder.size % 6);
  });
  rows.forEach((item, index) => {
    const fields = new Map(orderDetailRows(item, index + 1).map((parts) => [parts[0], parts]));
    const row = document.createElement("tr");
    const toneKey = orderToneKey(item);
    if (orderTab !== "cs" && toneByOrder.has(toneKey)) row.classList.add(`order-tone-${toneByOrder.get(toneKey)}`);
    if (selectedOrderIds.has(item.id)) row.classList.add("selected");
    if (item.id === orderFocusId) row.classList.add("order-current");
    if (item.on_hold) row.classList.add("order-hold");
    if (orderTab !== "cs") row.append(orderCheckCell(item));
    displayedOrderColumns().forEach((label) => {
      if (label === "공급처") {
        row.append(textCell(item.wholesale_name || item.wholesale_status || ""));
        return;
      }
      if (label === "발송") {
        row.append(textCell(item.dispatched ? "발송" : ""));
        return;
      }
      const parts = fields.get(label) || [label, ""];
      row.append(orderSheetCell(item, ...parts));
    });
    row.addEventListener("click", (event) => {
      if (event.target.closest("input, select, button, a")) return;
      if (orderTab === "cs") {
        openCsMemo(item);
        return;
      }
      focusOrder(item);
    });
    body.appendChild(row);
  });
  renderOrderDetail();
  renderOrderSummary();
}

function renderOrderSummary() {
  const bar = $("#orderSummary");
  if (!bar) return;
  if (!ordersCollected) {
    bar.textContent = "";
    return;
  }
  const checked = selectedOrders();
  const items = checked.length ? checked : visibleOrders();
  const quantity = items.reduce((sum, item) => sum + (Number(item.quantity) || 0), 0);
  const paid = items.reduce((sum, item) => sum + orderPaidAmount(item), 0);
  const fee = items.reduce((sum, item) => sum + (Number(item.commission) || 0), 0);
  const discount = items.reduce((sum, item) => sum + (Number(item.discount_amount) || 0), 0);
  const settlement = items.reduce((sum, item) => {
    if (item.settlement_amount === undefined || item.settlement_amount === null || item.settlement_amount === "") {
      return sum + orderPaidAmount(item) - (Number(item.commission) || 0);
    }
    return sum + (Number(item.settlement_amount) || 0);
  }, 0);
  const shipping = items.reduce((sum, item) => sum + (item.shipping_fee_type === "착불" ? 0 : (Number(item.delivery_fee) || 0)), 0);
  const sheets = new Set(items.map((item) => String(item.package_number || item.id))).size;
  const money = (value) => `${Math.round(value).toLocaleString("ko-KR")}원`;
  const parts = [
    `(${checked.length ? "체크됨" : "전체"})총 ${items.length}건`,
    `송장:${sheets}장`,
    `상품:${quantity}개`,
    `결제:${money(paid)}`,
    `수수료:${money(fee)}`,
  ];
  if (discount) parts.push(`할인:${money(discount)}`);
  parts.push(`정산:${money(settlement)}`, `정산+배송:${money(settlement + shipping)}`);
  bar.textContent = parts.join(" | ");
}

function orderMoney(value) {
  if (value === undefined || value === null || value === "") return "";
  const number = Number(value);
  if (!Number.isFinite(number)) return "";
  return number.toLocaleString("ko-KR");
}

function orderGrossAmount(item) {
  const unit = Number(item.unit_price);
  const option = Number(item.option_price) || 0;
  const qty = Number(item.quantity) || 1;
  if (Number.isFinite(unit) && unit > 0) return unit * qty + option;
  return (Number(item.amount) || 0) + (Number(item.discount_amount) || 0);
}

function orderPaidAmount(item) {
  const paid = Number(item.amount);
  if (Number.isFinite(paid)) return paid;
  return orderGrossAmount(item);
}

function orderPhoneDigits(value) {
  return String(value || "").replace(/\D/g, "");
}

function joinUniquePhones(...values) {
  const seen = new Set();
  const parts = [];
  values.forEach((value) => {
    const text = String(value || "").trim();
    const digits = orderPhoneDigits(text);
    if (!text || !digits || seen.has(digits)) return;
    seen.add(digits);
    parts.push(text);
  });
  return parts.join(" / ");
}

function orderListPhones(item) {
  const phoneRaw = String(item?.receiver_tel || "").trim();
  const mobileRaw = String(item?.receiver_tel2 || "").trim();
  const buyerRaw = String(item?.buyer_tel || "").trim();
  const receiverDigits = new Set([phoneRaw, mobileRaw].map(orderPhoneDigits).filter(Boolean));
  const buyerDigits = orderPhoneDigits(buyerRaw);
  const same = !buyerDigits || !receiverDigits.size || receiverDigits.has(buyerDigits);
  if (same) {
    return { receiver: "", buyer: joinUniquePhones(buyerRaw, phoneRaw, mobileRaw) };
  }
  return { receiver: joinUniquePhones(phoneRaw, mobileRaw), buyer: joinUniquePhones(buyerRaw) };
}

function orderUnitCost(item) {
  const maps = orderCostMaps();
  const channel = String(item?.channel_product_no || "").trim();
  const origin = String(item?.origin_product_no || "").trim();
  const seller = String(item?.seller_product_code || "").trim();
  const productId = String(item?.product_id || "").trim();
  const cost = maps.byChannel.get(channel) || maps.byOrigin.get(origin) || maps.bySeller.get(seller) || maps.bySeller.get(productId) || 0;
  return cost > 0 ? cost : 0;
}

function orderCostMaps() {
  if (orderCostCache && orderCostCache.stamp === products) return orderCostCache;
  const byChannel = new Map();
  const byOrigin = new Map();
  const bySeller = new Map();
  const put = (map, key, cost) => {
    const text = String(key || "").trim();
    if (text && cost > 0 && !map.has(text)) map.set(text, cost);
  };
  products.forEach((product) => {
    let cost = Number(product.cost) || 0;
    if (!(cost > 0) && product.master_id) {
      const master = products.find((item) => item.id === product.master_id);
      cost = Number(master?.cost) || 0;
    }
    if (!(cost > 0)) return;
    put(byChannel, product.channel_product_no, cost);
    const url = String(product.store_product_url || "");
    const found = url.match(/\/products\/(\d+)/);
    if (found) put(byChannel, found[1], cost);
    put(byOrigin, product.origin_product_no, cost);
    put(bySeller, product.seller_code, cost);
    put(bySeller, product.model, cost);
    put(bySeller, product.id, cost);
  });
  orderCostCache = { stamp: products, byChannel, byOrigin, bySeller };
  return orderCostCache;
}

let orderCostCache = null;

function orderMarginRate(part, total) {
  const left = Number(part);
  const right = Number(total);
  if (!Number.isFinite(left) || !right) return "";
  return `${(left / right * 100).toFixed(2)}%`;
}

function orderPercent(part, total) {
  const left = Number(part);
  const right = Number(total);
  if (!left || !right) return "";
  return `${(left / right * 100).toFixed(2)}%`;
}

function orderTalkUrl(item) {
  const market = marketOf(item.market_id);
  const slug = String(market?.slug || "").trim();
  if (!slug) return "";
  return `https://talk.naver.com/ct/${encodeURIComponent(slug)}`;
}

function orderProductUrl(item) {
  if (item.product_url) return item.product_url;
  const market = marketOf(item.market_id);
  const number = String(item.channel_product_no || item.product_no || "").trim();
  return smartstoreProductUrl(number, market);
}

function orderStatusCell(item) {
  const cell = document.createElement("td");
  cell.textContent = orderStatusText(item);
  if (orderBucket(item) === "new") cell.className = "order-status-new";
  return cell;
}

function orderStatusText(item) {
  const bucket = orderBucket(item);
  if (bucket === "new") return "발송대기(신규주문)";
  if (bucket === "wait") return "발송대기";
  return item.status_label || item.status || "";
}

function courierCode(code) {
  const key = String(code || "").toUpperCase();
  if (key === "LOGEN") return "KGB";
  if (key === "LOTTE") return "HYUNDAI";
  return key;
}

function isDirectDelivery(item) {
  const company = String(item?.delivery_company || "").trim().toUpperCase();
  const method = String(item?.delivery_method || "").trim();
  return company === "DIRECT" || method === "직접전달";
}

function trackingUrl(company, number) {
  const code = String(company || "").toUpperCase();
  const no = String(number || "").trim();
  if (!no) return "";
  const encoded = encodeURIComponent(no);
  if (code === "CJGLS") return `https://trace.cjlogistics.com/next/tracking.html?wblNo=${encoded}`;
  if (code === "HANJIN") return `https://www.hanjin.com/kor/CMS/DeliveryMgr/WaybillResult.do?mCode=MN038&schLang=KR&wblnumText2=${encoded}`;
  if (code === "KGB" || code === "LOGEN") return `https://www.ilogen.com/web/personal/trace/${encoded}`;
  if (code === "EPOST") return `https://service.epost.go.kr/trace.RetrieveDomRigiTraceList.comm?sid1=${encoded}`;
  if (code === "HYUNDAI" || code === "LOTTE") return `https://www.lotteglogis.com/home/reservation/tracking/linkView?InvNo=${encoded}`;
  return `https://search.naver.com/search.naver?query=${encodeURIComponent(`${no} 배송조회`)}`;
}

function shortOrderDay(value) {
  const day = formatOrderDate(value).slice(0, 10);
  const parts = day.split("-");
  if (parts.length < 3 || !parts[0]) return "";
  return `${parts[0].slice(2)}.${parts[1]}.${parts[2]}`;
}

function orderDay(value) {
  return formatOrderDate(value).slice(0, 10);
}

function feeRateText(item) {
  return orderPercent(item.commission, orderGrossAmount(item));
}

function smartOrderStatus(item) {
  const names = {
    new: "신규주문",
    wait: "발송대기",
    shipping: "배송중",
    delivered: "배송완료",
    confirmed: "구매확정",
    canceled: "취소",
    returned: "반품",
    exchanged: "교환",
  };
  return names[orderBucket(item)] || item.status_label || "";
}

const REPLACE_TARGETS = ["상품명", "선택사항", "추가구성", "배송구분", "판매자상품코드"];
let replacePhoneCache = null;
let replaceSelected = 0;

function loadReplaceSettings() {
  const fallback = {
    enabled: true,
    stripMoney: false,
    stripQty: false,
    stripName: false,
    useSellerCode: false,
    sameContact: false,
    rules: [],
  };
  try {
    const saved = JSON.parse(localStorage.getItem("uploader-order-replace") || "null");
    if (!saved || typeof saved !== "object") return fallback;
    const rules = Array.isArray(saved.rules) ? saved.rules.map((rule) => ({
      find: String(rule?.find || ""),
      replace: String(rule?.replace || ""),
      target: REPLACE_TARGETS.includes(rule?.target) ? rule.target : "상품명",
    })).filter((rule) => rule.find) : [];
    return { ...fallback, ...saved, rules };
  } catch (error) {
    return fallback;
  }
}

function saveReplaceSettings(settings) {
  localStorage.setItem("uploader-order-replace", JSON.stringify(settings));
  replacePhoneCache = null;
}

function replaceActive() {
  if (orderTab !== "new" && orderTab !== "wait") return false;
  return loadReplaceSettings().enabled;
}

function replaceContactKey(item) {
  return `${item?.receiver_name || ""}\n${item?.address1 || ""}\n${item?.address2 || ""}`.replace(/\s+/g, "");
}

function replacePhoneMap() {
  if (replacePhoneCache) return replacePhoneCache;
  const map = new Map();
  replacePhoneCache = map;
  const settings = loadReplaceSettings();
  if (!settings.enabled || !settings.sameContact) return map;
  orders.forEach((item) => {
    if (orderBucket(item) !== orderTab) return;
    const key = replaceContactKey(item);
    if (!key) return;
    if (!map.has(key)) map.set(key, { receiver_tel: "", receiver_tel2: "", buyer_tel: "" });
    const slot = map.get(key);
    if (!slot.receiver_tel && item.receiver_tel) slot.receiver_tel = item.receiver_tel;
    if (!slot.receiver_tel2 && item.receiver_tel2) slot.receiver_tel2 = item.receiver_tel2;
    if (!slot.buyer_tel && item.buyer_tel) slot.buyer_tel = item.buyer_tel;
  });
  return map;
}

function replaceMoneyText(value) {
  return String(value || "")
    .replace(/\(\s*[+-]?\s*[\d,]+\s*원\s*\)/g, "")
    .replace(/[+-]\s*[\d,]+\s*원/g, "")
    .replace(/\s{2,}/g, " ")
    .trim();
}

function replaceQtyText(value) {
  return String(value || "")
    .replace(/\(\s*\d+\s*개\s*\)/g, "")
    .replace(/\s*[/／]\s*\d+\s*개/g, "")
    .replace(/\s*[xX×*]\s*\d+\s*$/g, "")
    .replace(/\s+\d+\s*개\s*$/g, "")
    .replace(/\s{2,}/g, " ")
    .trim();
}

function presentOrder(item) {
  if (!item || !replaceActive()) return item;
  const settings = loadReplaceSettings();
  const copy = { ...item };
  if (settings.stripMoney) {
    copy.option = replaceMoneyText(copy.option);
    copy.extra_option = replaceMoneyText(copy.extra_option);
  }
  if (settings.stripQty) copy.option = replaceQtyText(copy.option);
  if (settings.stripName && String(copy.option || "").trim()) copy.product_name = "";
  if (settings.useSellerCode && String(copy.seller_product_code || "").trim()) {
    copy.product_name = String(copy.seller_product_code).trim();
  }
  let shipping = String(copy.shipping_fee_type || copy.shipping_policy || "");
  settings.rules.forEach((rule) => {
    const next = String(rule.replace || "");
    const apply = (value) => String(value || "").split(rule.find).join(next);
    if (rule.target === "상품명") copy.product_name = apply(copy.product_name);
    else if (rule.target === "선택사항") copy.option = apply(copy.option);
    else if (rule.target === "추가구성") copy.extra_option = apply(copy.extra_option);
    else if (rule.target === "판매자상품코드") copy.seller_product_code = apply(copy.seller_product_code);
    else if (rule.target === "배송구분") shipping = apply(shipping);
  });
  copy.shipping_fee_type = shipping;
  copy.shipping_policy = "";
  if (settings.sameContact) {
    const phones = replacePhoneMap().get(replaceContactKey(item));
    if (phones?.receiver_tel) copy.receiver_tel = phones.receiver_tel;
    if (phones?.receiver_tel2) copy.receiver_tel2 = phones.receiver_tel2;
    if (phones?.buyer_tel) copy.buyer_tel = phones.buyer_tel;
  }
  return copy;
}

function replaceTargetSelect(value) {
  const select = document.createElement("select");
  select.dataset.target = "1";
  REPLACE_TARGETS.forEach((name) => {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    select.appendChild(option);
  });
  select.value = REPLACE_TARGETS.includes(value) ? value : "상품명";
  return select;
}

function renderReplaceRules(rules) {
  const body = $("#replaceRuleTable tbody");
  if (!body) return;
  const rows = (rules || []).map((rule) => ({ ...rule }));
  rows.push({ find: "", replace: "", target: "상품명" });
  body.replaceChildren();
  rows.forEach((rule, index) => {
    const row = document.createElement("tr");
    if (index === replaceSelected) row.classList.add("selected");
    row.addEventListener("click", () => {
      replaceSelected = index;
      body.querySelectorAll("tr").forEach((line, lineIndex) => line.classList.toggle("selected", lineIndex === index));
    });
    const no = document.createElement("td");
    no.textContent = rule.find || rule.replace ? String(index + 1) : "";
    const findCell = document.createElement("td");
    const find = document.createElement("input");
    find.dataset.find = "1";
    find.value = rule.find || "";
    findCell.appendChild(find);
    const replaceCell = document.createElement("td");
    const replace = document.createElement("input");
    replace.dataset.replace = "1";
    replace.value = rule.replace || "";
    replaceCell.appendChild(replace);
    const targetCell = document.createElement("td");
    targetCell.appendChild(replaceTargetSelect(rule.target));
    row.append(no, findCell, replaceCell, targetCell);
    body.appendChild(row);
  });
  if (replaceSelected >= rows.length) replaceSelected = Math.max(0, rows.length - 1);
}

function readReplaceRules() {
  const rules = [...document.querySelectorAll("#replaceRuleTable tbody tr")].map((row) => ({
    find: row.querySelector("[data-find]")?.value || "",
    replace: row.querySelector("[data-replace]")?.value || "",
    target: row.querySelector("[data-target]")?.value || "상품명",
  }));
  const last = rules[rules.length - 1];
  if (last && !last.find && !last.replace) rules.pop();
  return rules;
}

function openReplaceDialog() {
  const settings = loadReplaceSettings();
  if ($("#replaceStripMoney")) $("#replaceStripMoney").checked = settings.stripMoney;
  if ($("#replaceStripQty")) $("#replaceStripQty").checked = settings.stripQty;
  if ($("#replaceStripName")) $("#replaceStripName").checked = settings.stripName;
  if ($("#replaceUseSellerCode")) $("#replaceUseSellerCode").checked = settings.useSellerCode;
  if ($("#replaceSameContact")) $("#replaceSameContact").checked = settings.sameContact;
  const use = document.querySelector(`input[name="replaceUse"][value="${settings.enabled ? "on" : "off"}"]`);
  if (use) use.checked = true;
  replaceSelected = 0;
  renderReplaceRules(settings.rules);
  $("#replaceDialog")?.showModal();
}

function currentReplaceSettings() {
  return {
    enabled: document.querySelector('input[name="replaceUse"]:checked')?.value !== "off",
    stripMoney: Boolean($("#replaceStripMoney")?.checked),
    stripQty: Boolean($("#replaceStripQty")?.checked),
    stripName: Boolean($("#replaceStripName")?.checked),
    useSellerCode: Boolean($("#replaceUseSellerCode")?.checked),
    sameContact: Boolean($("#replaceSameContact")?.checked),
    rules: readReplaceRules().filter((rule) => rule.find),
  };
}

function orderDetailRows(item, index) {
  item = presentOrder(item);
  const market = marketOf(item.market_id);
  const address = [item.address1, item.address2].filter(Boolean).join(" ");
  const gross = orderGrossAmount(item);
  const paid = orderPaidAmount(item);
  const commission = Number(item.commission) || 0;
  const unit = item.unit_price === undefined || item.unit_price === null || item.unit_price === ""
    ? (Number(item.quantity) === 1 ? orderMoney(gross) : "")
    : orderMoney(item.unit_price);
  const unitWithOption = orderMoney((Number(item.unit_price) || 0) + (Number(item.option_price) || 0)) || unit;
  const trace = trackingUrl(item.delivery_company, item.tracking_number);
  const rate = orderPercent(commission, gross);
  const paidRate = orderPercent(commission, paid);
  const supply = gross - commission;
  const settlement = item.settlement_amount === undefined || item.settlement_amount === null || item.settlement_amount === ""
    ? paid - commission
    : Number(item.settlement_amount);
  const qty = Number(item.quantity) || 1;
  const orderCost = orderUnitCost(item) * qty;
  const phones = orderListPhones(item);
  const phone = phones.receiver;
  const buyerPhone = phones.buyer;
  const digits = (value) => String(value || "").replace(/\D/g, "");
  const payFee = Number(item.payment_commission) || 0;
  const shopFee = Number(item.shopping_commission) || 0;
  const settlementNote = (payFee || shopFee || Number(item.commission))
    ? `결제수수료:${payFee}/ 매출연동수수료:${shopFee}/ 숨은수수료:0`
    : "";
  const productUrl = orderProductUrl(item);
  return [
    ["No.", index],
    ["주문상태", orderStatusText(item)],
    ["쇼핑몰", "04.스마트스토어"],
    ["별칭(쇼핑몰계정)", orderMarketName(item)],
    ["쇼핑몰ID", item.mall_id || market?.login_id || ""],
    ["주문일(약식)", shortOrderDay(item.order_date)],
    ["구매자", item.buyer_name || "", true],
    ["수령자", item.receiver_name || "", true],
    ["주문고유코드", ""],
    ["주문번호", item.product_order_id || item.order_id || ""],
    ["공급처", item.wholesale_name || ""],
    ["판매취소하기", "판매취소하기"],
    ["클레임사유", item.claim_reason || ""],
    ["택배사", item.delivery_company_name || item.delivery_company || "기타택배"],
    ["재배송 택배사", item.redelivery_company_name || ""],
    ["송장번호", item.tracking_number || ""],
    ["재배송 송장번호", item.redelivery_tracking || ""],
    ["배송추적", "배송추적", false, Boolean(trace), trace],
    ["상품번호", item.channel_product_no || ""],
    ["상품명", item.product_name || ""],
    ["선택사항", item.option || ""],
    ["수량", item.quantity || 1, true],
    ["단가", unit],
    ["추가구성", item.extra_option || ""],
    ["수령자전화번호", phone],
    ["구매자전화", buyerPhone],
    ["우편번호", item.zipcode || ""],
    ["주소", address],
    ["배송메모", item.shipping_memo || ""],
    ["CS메모", item.cs_memo || ""],
    ["배송구분", item.shipping_fee_type || item.shipping_policy || ""],
    ["총주문금액", orderMoney(gross)],
    ["옵션추가금액", orderMoney(item.option_price)],
    ["마켓수수료금액", orderMoney(commission)],
    ["수수료율", rate],
    ["실수수료율", paidRate],
    ["공급금액", orderMoney(supply)],
    ["배송비", orderMoney(item.shipping_fee_type === "착불" ? 0 : item.delivery_fee)],
    ["할인금액", orderMoney(item.discount_amount)],
    ["정산예상금액", orderMoney(settlement)],
    ["정산내역", "정산내역"],
    ["원가합계", orderCost ? orderMoney(orderCost) : ""],
    ["정산예정", orderMoney(settlement)],
    ["마진", orderCost ? orderMoney(settlement - orderCost) : ""],
    ["마진율", orderCost ? orderMarginRate(settlement - orderCost, settlement) : ""],
    ["주문일시", formatOrderDate(item.order_date)],
    ["결제일시", formatOrderDate(item.payment_date)],
    ["클레임접수일시", formatOrderDate(item.claim_requested)],
    ["발송예정일", formatOrderDate(item.shipping_due)],
    ["인터파크 공급계약가", ""],
    ["배송번호", item.package_number || ""],
    ["주문자ID", item.buyer_id || ""],
    ["상품URL", productUrl, false, Boolean(productUrl), productUrl],
    ["판매자상품코드", item.seller_product_code || ""],
    ["판매자옵션코드", item.option_code || ""],
    ["쇼핑몰계정고유번호", item.merchant_channel_id || market?.channel_no || ""],
    ["네이버 아이디 로그인", ""],
    ["스토어명", orderMarketName(item)],
    ["개인통관고유부호", item.customs_code || ""],
    ["개인통관고유부호2", ""],
    ["스마트주문상태", smartOrderStatus(item)],
    ["송장입력", item.tracking_number ? "송장입력" : "송장미입력"],
    ["보류여부", item.on_hold ? "보류" : "보류아님"],
    ["도서산간", orderRemoteKind(item) === "remote" ? "제주도서산간" : "보통지역"],
    ["정산추가정보", settlementNote],
    ["발송일시", formatOrderDate(item.send_date)],
    ["결제수단", item.payment_means || ""],
    ["배송방법", item.delivery_method || ""],
    ["실결제금액", orderMoney(paid)],
    ["최초 엑셀생성 일시", ""],
    ["최근 엑셀생성 일시", ""],
    ["송장번호입력일시", formatOrderDate(item.invoice_entered_at)],
    ["송장상품수량", item.quantity || 1],
    ["추가구성수량", 0],
    ["톡톡하기", "톡톡하기", false, Boolean(orderTalkUrl(item)), orderTalkUrl(item)],
    ["송장실결제금액", orderMoney(paid)],
    ["송장총주문금액", orderMoney(gross)],
    ["작업상태", item.work_status || "미지정"],
    ["메모(쇼핑몰계정)", market?.memo || ""],
    ["통관부호일치여부", item.customs_code ? "조회중" : ""],
    ["결제번호(ESM)", ""],
    ["주문번호(스마트스토어)", item.order_id || ""],
    ["상품주문번호(스마트스토어)", item.product_order_id || ""],
    ["배송속성(스마트스토어)", item.delivery_attribute || ""],
    ["단가(옵션추가금액 포함)", unitWithOption],
    ["정산예상금액(배송비 제외)", orderMoney(settlement)],
    ["실결제금액(배송비 포함)", orderMoney(paid + (item.shipping_fee_type === "착불" ? 0 : Number(item.delivery_fee) || 0))],
    ["주문일자(yyyyMMdd)", orderDay(item.order_date).replace(/-/g, "")],
    ["구매확정일시", formatOrderDate(item.decided_date)],
    ["발송마감일", formatOrderDate(item.shipping_due)],
    ["쿠팡옵션ID", ""],
    ["쿠팡모델번호", ""],
    ["url", ""],
    ["추가메모2", ""],
    ["추가메모3", ""],
    ["추가메모4", ""],
    ["추가메모5", ""],
    ["발송일자", orderDay(item.send_date).replace(/-/g, "")],
    ["발송일자", orderDay(item.send_date)],
    ["결제일자", orderDay(item.payment_date).replace(/-/g, "")],
    ["결제일자", orderDay(item.payment_date)],
    ["구매자전화(숫자)", digits(buyerPhone)],
    ["구매자휴대전화(숫자)", digits(buyerPhone)],
    ["수령자전화번호(숫자)", digits(phone)],
    ["수령자휴대전화(숫자)", digits(phone)],
    ["위메프배송번호", ""],
    ["판매자내부코드1", ""],
    ["판매자내부코드2", ""],
    ["주문메모(오늘의집)", ""],
    ["구매채널(멸치쇼핑)", ""],
    ["노출상품명", item.product_name || ""],
    ["등록상품명", item.product_name || ""],
    ["노출옵션명(쿠팡)", ""],
    ["등록옵션명(쿠팡)", ""],
    ["송장실결제금액(배송비포함)", orderMoney(paid)],
    ["구매번호(위메프)", ""],
    ["설치예약일", ""],
    ["클레임완료일시", formatOrderDate(item.claim_completed)],
    ["배송완료일시", formatOrderDate(item.delivered_date)],
    ["마지막 유입경로", item.inflow_path || ""],
    ["사은품 정보", item.free_gift || ""],
    ["구매자전달사항", item.shipping_memo || ""],
    ["주문색상번호", ""],
    ["구매확정요청(스마트스토어)", "구매확정요청(스마트스토어)"],
    ["구매확정 요청일", formatOrderDate(item.decided_date)],
  ];
}

function closeOrderDetail() {
  orderFocusId = "";
  const panel = $("#orderDetail");
  const splitter = $("#orderDetailResizer");
  if (panel) panel.hidden = true;
  if (splitter) splitter.hidden = true;
  document.querySelectorAll("#orderTable tr.order-current").forEach((row) => row.classList.remove("order-current"));
}

function renderOrderDetail() {
  const panel = $("#orderDetail");
  const body = $("#orderDetailBody");
  if (!panel || !body) return;
  const item = orders.find((row) => row.id === orderFocusId);
  const splitter = $("#orderDetailResizer");
  if (orderTab === "cs") {
    panel.hidden = true;
    if (splitter) splitter.hidden = true;
    return;
  }
  if (!item) {
    panel.hidden = true;
    if (splitter) splitter.hidden = true;
    body.replaceChildren();
    return;
  }
  panel.hidden = false;
  if (splitter) splitter.hidden = false;
  const table = document.createElement("table");
  table.className = "order-detail-table";
  const index = visibleOrders().findIndex((row) => row.id === item.id);
  orderDetailRows(item, index >= 0 ? index + 1 : 1).forEach(([label, value, emphasis, link, href]) => {
    const row = document.createElement("tr");
    const head = document.createElement("th");
    head.textContent = label;
    const cell = document.createElement("td");
    if (emphasis) cell.className = "emphasis";
    const text = value === undefined || value === null ? "" : String(value);
    if (label === "배송구분" && text === "착불") cell.classList.add("order-cod");
    if ((label === "주문번호" || label === "상품주문번호(스마트스토어)") && text) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "order-no-link";
      button.textContent = text;
      button.addEventListener("click", () => openOrderInfo(item));
      cell.appendChild(button);
      row.append(head, cell);
      table.appendChild(row);
      return;
    }
    if (label === "판매취소하기") {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "order-cancel-link";
      button.textContent = "판매취소하기";
      button.addEventListener("click", () => openOrderCancel(item));
      cell.appendChild(button);
      row.append(head, cell);
      table.appendChild(row);
      return;
    }
    if (label === "상품번호" && text) {
      const href = orderProductUrl(item);
      if (href) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "order-product-link product-no-link";
        button.textContent = text;
        button.title = "스마트스토어 상품 페이지";
        button.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          openProductHref(href, "상품 페이지 주소가 없습니다.");
        });
        cell.appendChild(button);
      } else {
        cell.textContent = text;
      }
      row.append(head, cell);
      table.appendChild(row);
      return;
    }
    const target = href || (link ? text : "");
    if (link && text && target) {
      const anchor = document.createElement("a");
      anchor.href = target;
      anchor.target = "_blank";
      anchor.rel = "noreferrer";
      anchor.textContent = text;
      cell.appendChild(anchor);
    } else {
      cell.textContent = text;
    }
    row.append(head, cell);
    table.appendChild(row);
  });
  body.replaceChildren(table);
}

function popupDate(value) {
  const match = String(value || "").match(/(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?/);
  if (!match) return "";
  return `${match[1]}.${match[2]}.${match[3]} ${match[4]}:${match[5]}:${match[6] || "00"}`;
}

function wonText(value) {
  if (value === undefined || value === null || value === "") return "";
  const number = Number(value);
  if (!Number.isFinite(number)) return "";
  return `${number.toLocaleString("ko-KR")}원`;
}

function orderInfoTable(rows) {
  const table = document.createElement("table");
  table.className = "order-info-table";
  rows.forEach((cells) => {
    const tr = document.createElement("tr");
    cells.forEach(([label, value, span]) => {
      const th = document.createElement("th");
      th.textContent = label;
      const td = document.createElement("td");
      td.textContent = value === undefined || value === null ? "" : String(value);
      if (span) td.colSpan = span;
      tr.append(th, td);
    });
    table.appendChild(tr);
  });
  return table;
}

function orderHistoryTable(rows) {
  const table = document.createElement("table");
  table.className = "order-info-table order-info-history";
  rows.forEach(([label, when]) => {
    if (!when) return;
    const tr = document.createElement("tr");
    const th = document.createElement("th");
    th.textContent = label;
    const gap = document.createElement("td");
    const td = document.createElement("td");
    td.textContent = when;
    tr.append(th, gap, td);
    table.appendChild(tr);
  });
  return table;
}

function openOrderInfo(item) {
  const dialog = $("#orderInfoDialog");
  const body = $("#orderInfoBody");
  const account = $("#orderInfoAccount");
  if (!dialog || !body || !item) return;
  const market = marketOf(item.market_id);
  const login = item.mall_id || market?.login_id || "";
  if (account) account.textContent = `04.스마트스토어 : ${login}`;
  const address = [item.address1, item.address2].filter(Boolean).join(" ");
  const amount = wonText(item.amount);
  const firstAmount = wonText(item.initial_amount ?? item.amount);
  const quantity = item.quantity || 1;
  const shipped = Boolean(item.tracking_number || item.send_date);
  const box = document.createElement("div");
  const number = document.createElement("div");
  number.className = "order-info-no";
  number.textContent = `상품주문번호: ${item.product_order_id || item.order_id || ""}`;
  const detailTitle = document.createElement("h4");
  detailTitle.textContent = "주문 상세정보";
  const shipTitle = document.createElement("h4");
  shipTitle.textContent = "배송 정보";
  const placeTitle = document.createElement("h4");
  placeTitle.textContent = "배송지 정보";
  const historyTitle = document.createElement("h4");
  historyTitle.textContent = "주문 처리 이력";
  box.append(
    detailTitle,
    number,
    orderInfoTable([
      [["상품명", item.product_name || "", 3]],
      [["상품주문상태", item.status_label || item.status || ""], ["클레임", item.claim_reason || ""]],
      [["수량클레임여부", item.claim_reason ? "Y" : "N"], ["구매확정연장상태", ""]],
      [["구매자명", item.buyer_name || ""], ["구매자 ID", item.buyer_id || ""]],
      [["옵션", item.option || "", 3]],
      [["주문수량", quantity], ["최초주문수량", item.initial_quantity || quantity]],
      [["최종 상품금액 (최초 상품금액)", `${amount} (${firstAmount || amount})`], ["상품별 할인액", wonText(item.discount_amount || 0)]],
    ]),
    shipTitle,
    orderInfoTable([
      [["발송지연사유", ""], ["당일발송여부", String(item.delivery_attribute || "").includes("당일") ? "Y" : "N"]],
      [["발송기한", popupDate(item.shipping_due)], ["예약구매여부", String(item.delivery_attribute || "").includes("희망") ? "Y" : "N"]],
      [["발송처리일", popupDate(item.send_date)], ["발주확인일", popupDate(item.place_order_date)]],
      [["최초 집화처리일시", popupDate(item.pickup_date)], ["최종 집화처리일시", popupDate(item.pickup_date)]],
      [["배송방법", item.delivery_method || ""], ["배송완료일", popupDate(item.delivered_date)]],
      [["출하일시", popupDate(item.send_date) || popupDate(item.shipping_due)], ["배송속성", item.delivery_attribute || ""]],
      [["택배사", shipped ? (item.delivery_company_name || "") : ""], ["배송상세상태", item.delivery_status || ""]],
      [["구매확정일", popupDate(item.decided_date)], ["송장번호", item.tracking_number || ""]],
      [["오류송장등록사유", ""], ["오류송장 등록일", ""]],
      [["개인통관고유부호", item.customs_code || "", 3]],
    ]),
    placeTitle,
    orderInfoTable([
      [["수취인명", item.receiver_name || "", 3]],
      [["연락처1", item.receiver_tel || ""], ["연락처2", item.receiver_tel2 || ""]],
      [["배송지", address, 3]],
      [["배송메모", item.shipping_memo || "", 3]],
    ]),
    historyTitle,
    orderHistoryTable([
      ["주문", popupDate(item.order_date)],
      ["결제완료", popupDate(item.payment_date)],
    ]),
  );
  body.replaceChildren(box);
  if (dialog.open) dialog.close();
  dialog.showModal();
}

$("#closeOrderInfo")?.addEventListener("click", () => $("#orderInfoDialog")?.close());
$("#closeOrderInfoX")?.addEventListener("click", () => $("#orderInfoDialog")?.close());
$("#closeOrderCancel")?.addEventListener("click", () => $("#orderCancelDialog")?.close());
$("#closeOrderCancelX")?.addEventListener("click", () => $("#orderCancelDialog")?.close());
$("#orderCancelForm")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!cancelOrderId) return;
  const button = $("#orderCancelSubmit");
  if (button) button.disabled = true;
  try {
    await api(`/api/orders/${cancelOrderId}/cancel`, {
      method: "POST",
      body: JSON.stringify({
        reason: $("#orderCancelReason")?.value || "",
        detail: $("#orderCancelDetail")?.value || "",
      }),
    });
    $("#orderCancelDialog")?.close();
    await loadOrders();
    toast("판매취소했습니다.");
  } catch (error) {
    toast(error.message, true);
  } finally {
    if (button) button.disabled = false;
  }
});

async function loadOrders(options = {}) {
  orders = await api("/api/orders", options);
  selectedOrderIds = new Set([...selectedOrderIds].filter((id) => orders.some((item) => item.id === id)));
  fillOrderMarketTree();
  renderOrders();
  return orders;
}

const ORDER_TAB_LABELS = {
  new: "신규주문",
  wait: "발송대기",
  shipping: "배송중",
  delivered: "배송완료",
  confirmed: "구매확정",
  canceled: "취소주문",
  returned: "반품주문",
  exchanged: "교환주문",
  all: "통합주문",
};

async function importMarketOrders() {
  const targets = smartstoreTargets(orderTargetMarkets());
  if (!targets.length) throw new Error("스마트스토어 마켓을 고르세요. 설정 > 마켓관리에서 스토어를 등록하세요.");
  const tab = ORDER_TAB_LABELS[orderTab] ? orderTab : "all";
  const label = `${ORDER_TAB_LABELS[tab] || "주문"} 수집`;
  const started = $("#orderDateFrom")?.value || "";
  const ended = $("#orderDateTo")?.value || "";
  const basis = $("#orderDateBasis")?.value || "paid";
  const rangeType = basis === "order" ? "ORDERED_DATETIME" : basis === "dispatch" ? "DISPATCHED_DATETIME" : "PAYED_DATETIME";
  await runOrderTabJob(tab, label, async (signal) => {
    let total = 0;
    let movedTotal = 0;
    let collected = false;
    const errors = [];
    for (const market of targets) {
      if (signal.aborted) throw abortError();
      try {
        const result = await api("/api/orders/import", {
          method: "POST",
          detached: true,
          signal,
          body: JSON.stringify({
            market_id: market.id,
            started,
            ended,
            tab: tab === "all" ? "" : tab,
            range_type: rangeType,
          }),
        });
        const fresh = Number(result.count || 0);
        const changed = Number(result.changed ?? result.count ?? 0);
        const moved = Number(result.moved || 0);
        total += fresh;
        movedTotal += moved;
        collected = true;
        const extra = moved
          ? ` 발송대기 ${moved}건은 발송대기로 반영했습니다.`
          : (tab === "all" && changed > fresh ? ` 그 외 상태 변경 ${changed - fresh}건은 배송완료, 구매확정, 취소입니다.` : "");
        log(`${market.name || "마켓"} ${ORDER_TAB_LABELS[tab] || "주문"} ${fresh}건을 불러왔습니다.${extra}`, "ok");
      } catch (error) {
        if (isAbortError(error)) throw error;
        errors.push(`${market.name || "마켓"}: ${error.message}`);
        log(`${market.name || "마켓"} 주문을 가져오지 못했습니다. ${error.message}`, "err");
      }
    }
    if (collected) {
      ordersCollected = true;
      await reloadOrders();
    }
    const movedText = movedTotal ? ` 발송대기 ${movedTotal}건은 발송대기로 반영했습니다.` : "";
    log(`${ORDER_TAB_LABELS[tab] || "주문"} ${total}건을 불러왔습니다.${movedText}`, total || movedTotal ? "ok" : "");
    if (errors.length) toast(errors[0], true);
    else toast(`${ORDER_TAB_LABELS[tab] || "주문"} ${total}건을 불러왔습니다.${movedText}`);
  });
}

async function placeWholesaleOrders() {
  const items = requireSelectedOrders();
  if (!items.length) return;
  if (!confirm(`선택한 ${items.length}건을 공급처에서 주문할까요? Chrome에서 주문서가 열리며, 결제는 직접 하세요.`)) return;
  const tab = orderTab;
  await runOrderTabJob(tab, "공급처 주문", async (signal) => {
    const result = await api("/api/orders/wholesale", {
      method: "POST",
      detached: true,
      signal,
      body: JSON.stringify({
        ids: items.map((item) => item.id),
        wholesaler_id: $("#orderWholesaler")?.value || "",
      }),
    });
    await reloadOrders();
    const extra = (result.errors || []).join(" / ");
    log(`공급처 주문 ${result.count || 0}건을 열었습니다.${extra ? ` ${extra}` : ""}`, extra ? "err" : "ok");
    toast("Chrome에서 수령인 정보를 확인하고 결제하세요.");
  });
}

async function collectOrderInvoices() {
  const tab = orderTab;
  const items = selectedOrders();
  await runOrderTabJob(tab, "송장수집", async (signal) => {
    const result = await api("/api/orders/invoices", {
      method: "POST",
      detached: true,
      signal,
      body: JSON.stringify({
        ids: items.map((item) => item.id),
        wholesaler_id: $("#orderWholesaler")?.value || "",
      }),
    });
    await reloadOrders();
    log(`송장 ${result.count || 0}건을 가져왔습니다.`, "ok");
  });
}

async function dispatchOrderInvoices() {
  const items = requireSelectedOrders();
  if (!items.length) return;
  if (items.some((item) => !isDirectDelivery(item) && !String(item.tracking_number || "").trim())) {
    throw new Error("선택한 주문에 송장번호가 없습니다. 택배사를 직접전달로 두거나 송장번호를 입력하세요.");
  }
  const directCount = items.filter((item) => isDirectDelivery(item)).length;
  const message = directCount === items.length
    ? `선택한 ${items.length}건을 송장번호 없이 직접전달로 보낼까요?`
    : directCount
      ? `선택한 ${items.length}건을 보낼까요? 직접전달 ${directCount}건은 송장번호 없이 보냅니다.`
      : `선택한 ${items.length}건의 송장을 스마트스토어로 보낼까요?`;
  if (!confirm(message)) return;
  const tab = orderTab;
  await runOrderTabJob(tab, "송장보내기", async (signal) => {
    await Promise.all(items.map((item) => {
      const patch = { tracking_number: String(item.tracking_number || "").trim() };
      if (item.delivery_company) patch.delivery_company = item.delivery_company;
      return saveOrderPatch(item.id, patch, true);
    }));
    if (signal.aborted) throw abortError();
    const result = await api("/api/orders/dispatch", {
      method: "POST",
      detached: true,
      signal,
      body: JSON.stringify({ ids: items.map((item) => item.id) }),
    });
    await reloadOrders();
    const extra = (result.errors || []).join(" / ");
    log(`송장보내기 ${result.count || 0}건.${extra ? ` ${extra}` : ""}`, extra ? "err" : "ok");
  });
}

async function updateSelectedInvoices() {
  const items = requireSelectedOrders();
  if (!items.length) return;
  const payload = [];
  items.forEach((item) => {
    const draft = invoiceDraft(item);
    const tracking = String(draft.tracking || "").replace(/\s+/g, "");
    const company = draft.company || item.delivery_company || "";
    if (!tracking || !company) return;
    payload.push({ id: item.id, delivery_company: company, tracking_number: tracking });
  });
  if (!payload.length) {
    toast("수정할 택배사와 송장번호를 입력해 주세요.", true);
    return;
  }
  const tab = orderTab;
  const skipped = items.length - payload.length;
  await runOrderTabJob(tab, "송장번호수정", async (signal) => {
    const result = await api("/api/orders/invoices/update", {
      method: "POST",
      detached: true,
      signal,
      body: JSON.stringify({ items: payload }),
    });
    (result.orders || []).forEach((saved) => invoiceDrafts.delete(saved.id));
    await reloadOrders();
    const extra = (result.errors || []).filter(Boolean).join(" / ");
    const note = skipped ? ` 송장번호가 없는 ${skipped}건은 건너뛰었습니다.` : "";
    toast(`${result.count || 0}건의 송장번호를 수정했습니다.${note}${extra ? ` ${extra}` : ""}`, Boolean(extra));
  });
}

function textBytes(text) {
  let size = 0;
  for (const char of String(text || "")) size += char.codePointAt(0) <= 0x7f ? 1 : 2;
  return size;
}

function priceNumber(value) {
  const text = String(value ?? "").trim().replace(/,/g, "");
  if (!text) return 0;
  const number = Number(text);
  if (!Number.isFinite(number) || number < 0) throw new Error("0 이상의 숫자만 입력하세요.");
  return number;
}

function formatPriceAmount(value, unit) {
  const number = Number(value || 0);
  const shown = Number.isInteger(number) ? number.toLocaleString("ko-KR") : String(number);
  return unit === "WON" ? `${shown}원` : `${shown}%`;
}

function priceSummaryText(item) {
  const parts = [
    `마진 ${formatPriceAmount(item.margin, "PERCENT")}`,
    `할인 ${formatPriceAmount(item.discount_value, item.discount_unit)}`,
    `포인트 ${formatPriceAmount(item.point_value, item.point_unit)}`,
    `추가 ${formatPriceAmount(item.extra_amount, "WON")}`,
  ];
  if (item.promo) parts.push(`홍보문구 ${item.promo}`);
  return parts.join(" / ");
}

function priceTextButton(action, label, pressed = false) {
  const button = document.createElement("button");
  button.type = "button";
  button.dataset.action = action;
  button.textContent = label;
  if (pressed) button.className = "is-on";
  return button;
}

function priceActions(item) {
  const wrap = document.createElement("div");
  wrap.className = "price-actions";
  wrap.appendChild(priceTextButton("apply", "간편전송"));
  if (item.kind === "market") wrap.appendChild(priceTextButton("shipping", "무료배송", Boolean(item.free_shipping)));
  wrap.append(priceTextButton("edit", "수정"), priceTextButton("delete", "삭제"));
  return wrap;
}

function priceMarketText(item) {
  const market = markets.find((row) => row.id === item.market_id);
  if (!market) return "삭제된 계정";
  const channel = market.channel_name || channelById(marketChannel(market)).name;
  const store = market.name || market.login_id || "이름 없음";
  return `${channel} ${store}`.trim();
}

function renderPriceSets() {
  const requiredBody = $("#requiredPriceBody");
  const marketBody = $("#marketPriceBody");
  if (!requiredBody || !marketBody) return;
  requiredBody.innerHTML = "";
  marketBody.innerHTML = "";
  const required = priceSets.filter((item) => item.kind !== "market");
  const marketRows = priceSets.filter((item) => item.kind === "market");
  const fillEmpty = (body, columns, text) => {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = columns;
    cell.className = "price-empty";
    cell.textContent = text;
    row.appendChild(cell);
    body.appendChild(row);
  };
  if (!required.length) fillEmpty(requiredBody, 3, "등록된 필수 가격세트가 없습니다.");
  required.forEach((item) => {
    const row = document.createElement("tr");
    row.dataset.id = item.id;
    const name = document.createElement("td");
    name.textContent = item.name || "";
    const summary = document.createElement("td");
    summary.textContent = priceSummaryText(item);
    const manage = document.createElement("td");
    manage.className = "col-manage";
    manage.appendChild(priceActions(item));
    row.append(name, summary, manage);
    requiredBody.appendChild(row);
  });
  if (!marketRows.length) fillEmpty(marketBody, 4, "등록된 마켓별 가격세트가 없습니다.");
  marketRows.forEach((item) => {
    const row = document.createElement("tr");
    row.dataset.id = item.id;
    const account = document.createElement("td");
    account.textContent = priceMarketText(item);
    const name = document.createElement("td");
    name.textContent = item.name || "";
    const summary = document.createElement("td");
    summary.textContent = priceSummaryText(item);
    const manage = document.createElement("td");
    manage.className = "col-manage";
    manage.appendChild(priceActions(item));
    row.append(account, name, summary, manage);
    marketBody.appendChild(row);
  });
}

async function loadPriceSets() {
  priceSets = await api("/api/price-sets");
  renderPriceSets();
  return priceSets;
}

function fillPriceMarketSelect(selected) {
  const select = $("#priceSetForm").elements.market_id;
  select.innerHTML = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "마켓 계정을 선택하세요";
  select.appendChild(placeholder);
  markets.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.id;
    const channel = item.channel_name || channelById(marketChannel(item)).name;
    option.textContent = `${channel} ${item.name || ""}`.trim();
    select.appendChild(option);
  });
  select.value = selected && [...select.options].some((item) => item.value === selected) ? selected : "";
}

function openPriceSetDialog(kind, item) {
  const form = $("#priceSetForm");
  const editing = Boolean(item?.id);
  form.elements.id.value = item?.id || "";
  form.elements.kind.value = kind;
  form.elements.name.value = item?.name || "";
  form.elements.margin.value = item ? (item.margin ?? "") : "";
  form.elements.discount_value.value = item ? (item.discount_value ?? "") : "";
  form.elements.discount_unit.value = item?.discount_unit || "PERCENT";
  form.elements.point_value.value = item ? (item.point_value ?? "") : "";
  form.elements.point_unit.value = item?.point_unit || "PERCENT";
  form.elements.extra_amount.value = item ? (item.extra_amount ?? "") : "";
  form.elements.promo.value = item?.promo || "";
  $("#priceSetMarketRow").hidden = kind !== "market";
  $("#priceSetPromoRow").hidden = kind !== "required";
  if (kind === "market") fillPriceMarketSelect(item?.market_id || "");
  $("#priceSetDialogTitle").textContent = kind === "market"
    ? (editing ? "마켓별 가격세트 수정" : "마켓별 가격세트 추가")
    : (editing ? "필수 가격세트 수정" : "필수 가격세트 추가");
  $("#priceSetSubmit").textContent = editing ? "저장하기" : "추가하기";
  $("#priceSetMessage").textContent = "";
  $("#priceSetDialog").showModal();
  form.elements[kind === "market" ? "market_id" : "name"].focus();
}

async function savePriceSetForm() {
  const form = $("#priceSetForm");
  const kind = form.elements.kind.value === "market" ? "market" : "required";
  const name = form.elements.name.value.trim();
  if (!name) throw new Error("이름을 입력하세요.");
  if (kind === "market" && !form.elements.market_id.value) throw new Error("마켓 계정을 선택하세요.");
  const margin = priceNumber(form.elements.margin.value);
  const discount = priceNumber(form.elements.discount_value.value);
  const point = priceNumber(form.elements.point_value.value);
  const extra = priceNumber(form.elements.extra_amount.value);
  if (margin > 300) throw new Error("마진은 0에서 300%까지 넣을 수 있습니다.");
  if (form.elements.discount_unit.value === "PERCENT" && discount >= 100) throw new Error("할인율은 100% 미만이어야 합니다.");
  if (form.elements.point_unit.value === "PERCENT" && point >= 100) throw new Error("포인트율은 100% 미만이어야 합니다.");
  const promo = kind === "required" ? form.elements.promo.value.trim() : "";
  if (textBytes(promo) > 80) throw new Error("홍보문구는 80byte까지 입력할 수 있습니다.");
  const payload = {
    id: form.elements.id.value || undefined,
    kind,
    name,
    margin,
    discount_value: discount,
    discount_unit: form.elements.discount_unit.value,
    point_value: point,
    point_unit: form.elements.point_unit.value,
    extra_amount: Math.round(extra),
    promo,
  };
  if (kind === "market") payload.market_id = form.elements.market_id.value;
  const saved = payload.id
    ? await api(`/api/price-sets/${payload.id}`, { method: "PUT", body: JSON.stringify(payload) })
    : await api("/api/price-sets", { method: "POST", body: JSON.stringify(payload) });
  $("#priceSetDialog").close();
  await loadPriceSets();
  toast(payload.id ? `${saved.name} 가격세트를 수정했습니다.` : `${saved.name} 가격세트를 추가했습니다.`);
}

async function onPriceSetAction(event, kind) {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  const row = button.closest("tr");
  const item = priceSets.find((entry) => entry.id === row?.dataset.id && (kind === "market" ? entry.kind === "market" : entry.kind !== "market"));
  if (!item) return;
  const action = button.dataset.action;
  if (action === "edit") {
    openPriceSetDialog(item.kind === "market" ? "market" : "required", item);
    return;
  }
  if (action === "delete") {
    if (!confirm(`"${item.name}" 가격세트를 삭제할까요?`)) return;
    await api(`/api/price-sets/${item.id}`, { method: "DELETE" });
    await loadPriceSets();
    toast("가격세트를 삭제했습니다.");
    return;
  }
  if (action === "shipping") {
    const saved = await api(`/api/price-sets/${item.id}/free-shipping`, { method: "POST", body: "{}" });
    await loadPriceSets();
    toast(saved.free_shipping ? "무료 배송을 사용합니다." : "무료 배송을 해제했습니다.");
    return;
  }
  if (action === "apply") {
    if (!confirm(`"${item.name}" 가격세트로 판매가, 할인, 포인트를 다시 계산할까요?`)) return;
    const result = await api(`/api/price-sets/${item.id}/apply`, { method: "POST", body: "{}" });
    await loadProducts();
    const skipped = Number(result.skipped || 0);
    if (!result.count) toast("적용할 상품이 없습니다. 원가가 있는 상품만 계산됩니다.");
    else toast(`${result.count}개 상품에 가격을 적용했습니다.${skipped ? ` ${skipped}개는 원가가 없어 건너뛰었습니다.` : ""}`);
  }
}

document.querySelectorAll(".market-sidebar").forEach((pane) => {
  enablePaneResize(pane, { edge: "right", min: 160, max: 480, storageKey: "market-sidebar-width" });
});
enableJobStatusResize();
enableDetailLabelResize();
const detailPanel = $("#orderDetail");
const savedDetailWidth = Number(localStorage.getItem("order-detail-width") || 0);
if (detailPanel && savedDetailWidth >= 280 && savedDetailWidth <= 760) {
  detailPanel.style.width = `${savedDetailWidth}px`;
  detailPanel.style.flexBasis = `${savedDetailWidth}px`;
}
$("#orderDetailClose")?.addEventListener("click", () => closeOrderDetail());
const orderDetailSplitter = $("#orderDetailResizer");
orderDetailSplitter?.addEventListener("mousedown", (event) => {
  event.preventDefault();
  const panel = $("#orderDetail");
  if (!panel) return;
  const startX = event.pageX;
  const startWidth = panel.getBoundingClientRect().width;
  document.body.classList.add("col-resizing");
  const move = (moveEvent) => {
    const width = Math.max(280, Math.min(760, Math.round(startWidth - (moveEvent.pageX - startX))));
    panel.style.width = `${width}px`;
    panel.style.flexBasis = `${width}px`;
  };
  const up = () => {
    document.removeEventListener("mousemove", move);
    document.removeEventListener("mouseup", up);
    document.body.classList.remove("col-resizing");
    localStorage.setItem("order-detail-width", String(Math.round(panel.getBoundingClientRect().width)));
  };
  document.addEventListener("mousemove", move);
  document.addEventListener("mouseup", up);
});
enableColumnResize($("#productGrid"));
enableColumnResize($("#optionGrid"));
enableColumnResize($("#wholesaleGrid"));
enableColumnResize($("#orderGrid"));
enableColumnResize($("#inquiryGrid"));
updateProductSortHeaders();
let arrivalWatching = false;
let arrivalOrderCount = 0;
let arrivalInquiryCount = 0;
let arrivalOpenKind = "new";
const ALERT_SEEN_KEY = "modumodu-alert-seen";
const ALERT_ORDER = ["new", "canceled", "returned", "exchanged", "inquiry"];
const ALERT_LABELS = { new: "신규주문", canceled: "취소", returned: "반품", exchanged: "교환", inquiry: "상품문의" };

function readAlertSeen() {
  try {
    const data = JSON.parse(localStorage.getItem(ALERT_SEEN_KEY) || "[]");
    return new Set(Array.isArray(data) ? data.map((item) => String(item)) : []);
  } catch {
    return new Set();
  }
}

function writeAlertSeen(seen) {
  localStorage.setItem(ALERT_SEEN_KEY, JSON.stringify([...seen].slice(-2000)));
}

function paintArrivalBadges() {
  const orderBadge = $("#orderAlertBadge");
  const inquiryBadge = $("#inquiryAlertBadge");
  if (orderBadge) {
    orderBadge.hidden = arrivalOrderCount <= 0;
    orderBadge.textContent = arrivalOrderCount > 99 ? "99+" : String(arrivalOrderCount);
  }
  if (inquiryBadge) {
    inquiryBadge.hidden = arrivalInquiryCount <= 0;
    inquiryBadge.textContent = arrivalInquiryCount > 99 ? "99+" : String(arrivalInquiryCount);
  }
}

function arrivalSummary(items) {
  const counts = {};
  items.forEach((item) => {
    counts[item.kind] = (counts[item.kind] || 0) + 1;
  });
  return ALERT_ORDER.filter((kind) => counts[kind]).map((kind) => `${ALERT_LABELS[kind]} ${counts[kind]}건`).join(", ");
}

function playArrivalSound() {
  const AudioCtx = window.AudioContext || window.webkitAudioContext;
  if (!AudioCtx) return;
  const context = new AudioCtx();
  const oscillator = context.createOscillator();
  const gain = context.createGain();
  oscillator.type = "sine";
  oscillator.frequency.value = 880;
  gain.gain.value = 0.04;
  oscillator.connect(gain);
  gain.connect(context.destination);
  oscillator.start();
  gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.18);
  oscillator.stop(context.currentTime + 0.2);
  oscillator.onended = () => context.close();
}

function showArrivalNotice(items) {
  const text = `${arrivalSummary(items)}이 왔습니다.`;
  const box = $("#arrivalNotice");
  const line = $("#arrivalNoticeText");
  if (line) line.textContent = text;
  if (box) box.hidden = false;
  arrivalOpenKind = ALERT_ORDER.find((kind) => items.some((item) => item.kind === kind)) || "new";
  arrivalOrderCount += items.filter((item) => item.kind !== "inquiry").length;
  arrivalInquiryCount += items.filter((item) => item.kind === "inquiry").length;
  paintArrivalBadges();
  log(text, "ok");
  playArrivalSound();
  if ("Notification" in window && Notification.permission === "granted") {
    new Notification("모두모두AI", { body: text });
  } else if ("Notification" in window && Notification.permission === "default") {
    Notification.requestPermission().catch(() => {});
  }
}

function openArrivalNotice() {
  const box = $("#arrivalNotice");
  if (box) box.hidden = true;
  if (arrivalOpenKind === "inquiry") {
    arrivalInquiryCount = 0;
    paintArrivalBadges();
    showAppView("inquiries");
    return;
  }
  arrivalOrderCount = 0;
  paintArrivalBadges();
  showAppView("orders");
  setOrderTab(arrivalOpenKind);
}

async function watchIncomingAlerts() {
  if (arrivalWatching) return;
  arrivalWatching = true;
  try {
    const data = await api("/api/alerts", { quiet: true });
    const items = Array.isArray(data.items) ? data.items : [];
    const seen = readAlertSeen();
    const fresh = items.filter((item) => item.key && !seen.has(item.key));
    items.forEach((item) => {
      if (item.key) seen.add(item.key);
    });
    writeAlertSeen(seen);
    if (fresh.length) showArrivalNotice(fresh);
  } catch {
    // 알림 확인이 실패해도 화면 작업은 그대로 둡니다.
  } finally {
    arrivalWatching = false;
  }
}

$("#arrivalNoticeOpen")?.addEventListener("click", () => openArrivalNotice());
$("#arrivalNoticeClose")?.addEventListener("click", () => {
  const box = $("#arrivalNotice");
  if (box) box.hidden = true;
});

function applyAppTheme(theme, save) {
  const next = theme === "dark" ? "dark" : "light";
  if (next === "dark") document.documentElement.dataset.theme = "dark";
  else delete document.documentElement.dataset.theme;
  if (save) localStorage.setItem("uploader-theme", next);
  document.querySelectorAll('input[name="appTheme"]').forEach((input) => {
    input.checked = input.value === next;
  });
}

applyAppTheme(localStorage.getItem("uploader-theme") === "dark" ? "dark" : "light", false);
document.addEventListener("change", (event) => {
  if (event.target?.name !== "appTheme") return;
  applyAppTheme(event.target.value, true);
  toast(event.target.value === "dark" ? "어두운 배경으로 바꿨습니다." : "밝은 배경으로 바꿨습니다.");
});

$("#appQuit")?.addEventListener("click", async () => {
  if (!window.confirm("프로그램을 종료할까요?")) return;
  toast("프로그램을 종료합니다.");
  try {
    await api("/api/shutdown", { method: "POST", quiet: true });
  } catch (error) {
    toast(error.message || "종료하지 못했습니다.", true);
  }
});

loadEdition().catch(() => applyEdition("master"));
(async () => {
  try {
    await Promise.all([
      loadMarkets(),
      loadWholesalers(),
      loadProducts(),
    ]);
    if (productFilter !== "all" && !visibleProducts().length && products.length) {
      productFilter = "all";
      fillProductFilter();
      refreshVisibleSelection();
    }
    if (!visibleProducts().length && products.length) {
      marketFilter = "master";
      masterChannelFilter = "";
      fillMarketTree();
      refreshVisibleSelection();
    }
    const shown = visibleProducts().length;
    if (products.length || markets.length) {
      toast(`상품 ${products.length.toLocaleString("ko-KR")}개 · 마켓 ${markets.length.toLocaleString("ko-KR")}개${shown !== products.length ? ` · 지금 보기 ${shown.toLocaleString("ko-KR")}개` : ""}`);
    } else {
      toast("상품·마켓 데이터가 비어 있습니다. data 폴더를 확인해 주세요.", true);
    }
  } catch (error) {
    toast(error.message || "상품·마켓을 불러오지 못했습니다.", true);
  }
})();
window.addEventListener("mousemove", moveCheckPaint);
window.addEventListener("mouseup", endCheckPaint);
window.addEventListener("blur", endCheckPaint);
setTimeout(watchIncomingAlerts, 8000);
setInterval(watchIncomingAlerts, 90000);

function dialogDragHandle(dialog) {
  return (
    dialog.querySelector(":scope > form > header")
    || dialog.querySelector(":scope > header")
    || dialog.querySelector(":scope > form > h2, :scope > form > h3")
    || dialog.querySelector(":scope > h2, :scope > h3")
  );
}

function resetDialogPosition(dialog) {
  dialog.classList.remove("dialog-moved");
  dialog.style.left = "";
  dialog.style.top = "";
  dialog.style.margin = "";
  dialog.style.position = "";
  dialog.style.width = "";
}

function setupDraggableDialogs() {
  document.querySelectorAll("dialog").forEach((dialog) => {
    const handle = dialogDragHandle(dialog);
    if (!handle || handle.dataset.dragReady === "1") return;
    handle.dataset.dragReady = "1";
    handle.classList.add("dialog-drag-handle");
    let dragging = false;
    let startX = 0;
    let startY = 0;
    let originLeft = 0;
    let originTop = 0;
    handle.addEventListener("pointerdown", (event) => {
      if (event.button !== 0) return;
      if (event.target.closest("button, a, input, select, textarea, label")) return;
      const rect = dialog.getBoundingClientRect();
      dialog.classList.add("dialog-moved");
      dialog.style.margin = "0";
      dialog.style.position = "fixed";
      dialog.style.left = `${rect.left}px`;
      dialog.style.top = `${rect.top}px`;
      dialog.style.width = `${rect.width}px`;
      startX = event.clientX;
      startY = event.clientY;
      originLeft = rect.left;
      originTop = rect.top;
      dragging = true;
      try {
        handle.setPointerCapture(event.pointerId);
      } catch {
        // ignore
      }
      event.preventDefault();
    });
    handle.addEventListener("pointermove", (event) => {
      if (!dragging) return;
      const maxX = Math.max(0, window.innerWidth - dialog.offsetWidth);
      const maxY = Math.max(0, window.innerHeight - 48);
      const left = Math.min(Math.max(0, originLeft + (event.clientX - startX)), maxX);
      const top = Math.min(Math.max(0, originTop + (event.clientY - startY)), maxY);
      dialog.style.left = `${left}px`;
      dialog.style.top = `${top}px`;
    });
    const stop = () => {
      dragging = false;
    };
    handle.addEventListener("pointerup", stop);
    handle.addEventListener("pointercancel", stop);
    dialog.addEventListener("close", () => resetDialogPosition(dialog));
  });
}

setupDraggableDialogs();
