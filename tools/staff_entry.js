// 직원용은 마스터의 상품을 등록하는 화면만 연다.
// 여러 PC 같이 쓰기를 이미 연결했으면 마스터 비밀번호 창으로 돌아가지 않는다.

function staffEntryPlan(label, syncConfigured, staffPasswordOn) {
  if (label !== "직원용") return "master";
  if (!syncConfigured) return "sync";
  if (staffPasswordOn) return "staff-password";
  return "products";
}

const STAFF_BLOCKED_VIEWS = ["orders", "inquiries", "members", "settings", "collect", "wholesalers"];

if (typeof module !== "undefined" && module.exports) {
  module.exports = { staffEntryPlan, STAFF_BLOCKED_VIEWS };
}

if (typeof document !== "undefined") {
  (function () {
    const hold = document.createElement("style");
    hold.id = "staffEntryHold";
    hold.textContent = "body:not(.edition-known) #masterLogin{visibility:hidden !important}";
    document.head.appendChild(hold);

    let plan = "master";

    function releaseHold() {
      document.body.classList.add("edition-known");
    }

    function errorText(data, fallback) {
      const detail = data && (data.detail || data.error || data.message);
      if (typeof detail === "string" && detail.trim()) return detail.trim();
      return fallback;
    }

    function lockViews() {
      const inner = window.showAppView;
      if (typeof inner !== "function" || inner.staffInstallHook) return;
      const blocked = new Set(STAFF_BLOCKED_VIEWS);
      const wrapped = function (name) {
        if (document.body.classList.contains("staff-install") && blocked.has(String(name))) {
          if (typeof toast === "function") toast("직원용은 상품등록만 할 수 있습니다.", true);
          return inner.call(this, "products");
        }
        return inner.apply(this, arguments);
      };
      Object.assign(wrapped, inner);
      wrapped.staffInstallHook = true;
      wrapped.staffHook = inner.staffHook;
      window.showAppView = wrapped;
    }

    function note() {
      let el = document.getElementById("staffDataNote");
      const host = document.getElementById("viewProducts");
      if (!el && host) {
        el = document.createElement("p");
        el.id = "staffDataNote";
        el.className = "staff-data-note";
        el.hidden = true;
        host.prepend(el);
      }
      return el;
    }

    function showNote(text) {
      const el = note();
      if (!el) return;
      el.hidden = !text;
      el.textContent = text || "";
    }

    function openProducts() {
      document.body.classList.add("staff-install", "staff-mode");
      try {
        sessionStorage.setItem("modumodu-master-gate", "1");
        sessionStorage.setItem("modumodu-staff", "1");
      } catch (_) {}
      document.body.dataset.masterEntered = "1";
      document.body.classList.remove("master-locked");
      const gate = document.getElementById("masterLogin");
      if (gate) gate.hidden = true;
      [...document.body.children].forEach((child) => {
        if (child.id !== "masterLogin" && child.id !== "sellerLogin") child.removeAttribute("inert");
      });
      lockViews();
      if (typeof window.applyStaffMode === "function") window.applyStaffMode();
      if (typeof window.showAppView === "function") window.showAppView("products");
      releaseHold();
    }

    function rewriteGate() {
      const title = document.getElementById("masterLoginTitle");
      if (title && title.lastChild && title.lastChild.nodeType === Node.TEXT_NODE) {
        title.lastChild.textContent = " 직원용";
      }
      const lead = document.querySelector("#masterLogin .master-login-card p");
      const label = document.querySelector("#masterLogin label");
      if (plan === "sync") {
        if (lead) lead.textContent = "마스터 비밀번호가 아닙니다. 여러 PC 같이 쓰기의 마스터 동기화 비밀번호를 넣으면 사장님 상품을 받아 오고, 상품등록 화면만 열립니다.";
        if (label && label.firstChild) label.firstChild.textContent = "마스터 동기화 비밀번호";
      } else if (plan === "staff-password") {
        if (lead) lead.textContent = "직원 비밀번호를 넣으면 상품등록 화면이 열립니다. 마스터 비밀번호로는 관리 화면이 열리지 않습니다.";
        if (label && label.firstChild) label.firstChild.textContent = "직원 비밀번호";
      }
    }

    async function pullProducts() {
      showNote("사장님 PC의 상품을 받아오는 중입니다. 상품이 많으면 몇 분 걸립니다.");
      try {
        if (typeof loadProducts === "function") await loadProducts();
      } catch (_) {}
      if (typeof products !== "undefined" && products.length) {
        showNote("");
      }
      try {
        const res = await fetch("/api/sync/now", { method: "POST" });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || data.ok === false) {
          showNote(errorText(data, "상품을 받아오지 못했습니다. 사장님 PC가 먼저 연결돼 있는지 확인해 주세요."));
          return;
        }
      } catch (_) {
        showNote("상품을 받아오지 못했습니다. 인터넷 연결을 확인해 주세요.");
        return;
      }
      try {
        if (typeof loadProducts === "function") await loadProducts();
      } catch (error) {
        showNote(error && error.message ? error.message : "상품 목록을 열지 못했습니다.");
        return;
      }
      if (typeof products === "undefined" || !products.length) {
        showNote("아직 이 PC에 상품이 없습니다. 사장님 PC에서 여러 PC 같이 쓰기를 먼저 연결해야 상품이 서버에 올라갑니다.");
        return;
      }
      showNote("");
    }

    document.addEventListener(
      "submit",
      async (event) => {
        if (!document.body.classList.contains("staff-install")) return;
        const form = event.target;
        if (!(form instanceof HTMLFormElement) || !form.closest("#masterLogin")) return;
        event.preventDefault();
        event.stopPropagation();
        const input = document.getElementById("masterLoginPassword");
        const error = document.getElementById("masterLoginError");
        const typed = String(input && input.value || "").trim();
        if (typed.length < 4) {
          if (error) error.textContent = "비밀번호는 4자 이상입니다.";
          return;
        }
        try {
          if (plan === "staff-password") {
            const res = await fetch("/api/staff/login", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ password: typed }),
            });
            if (!res.ok) {
              if (error) error.textContent = "직원 비밀번호가 아닙니다. 마스터 비밀번호로는 프로그램관리, 관리자 관리, 회원관리가 열리지 않습니다.";
              return;
            }
          } else {
            const res = await fetch("/api/sync/setup", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ password: typed }),
            });
            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
              if (error) error.textContent = errorText(data, "연결하지 못했습니다. 마스터 동기화 비밀번호를 확인해 주세요.");
              return;
            }
          }
          if (input) input.value = "";
          if (error) error.textContent = "";
          openProducts();
          await pullProducts();
        } catch (_) {
          if (error) error.textContent = "연결하지 못했습니다. 인터넷 연결을 확인해 주세요.";
        }
      },
      true,
    );

    async function boot() {
      let edition = null;
      try {
        const res = await fetch("/api/edition", { cache: "no-store" });
        if (res.ok) edition = await res.json();
      } catch (_) {}
      if (!edition || edition.label !== "직원용") {
        releaseHold();
        return;
      }
      document.body.classList.add("staff-install");
      lockViews();
      let syncConfigured = false;
      try {
        const res = await fetch("/api/sync/status", { cache: "no-store" });
        if (res.ok) {
          const data = await res.json();
          syncConfigured = !!data.configured;
        }
      } catch (_) {}
      let staffPasswordOn = false;
      if (syncConfigured) {
        try {
          const res = await fetch("/api/staff/status", { cache: "no-store" });
          if (res.ok) staffPasswordOn = !!(await res.json()).enabled;
        } catch (_) {}
      }
      plan = staffEntryPlan(edition.label, syncConfigured, staffPasswordOn);
      if (plan === "products") {
        openProducts();
        await pullProducts();
        return;
      }
      rewriteGate();
      releaseHold();
      const gate = document.getElementById("masterLogin");
      if (gate) gate.style.visibility = "";
      setInterval(rewriteGate, 700);
    }

    boot();
  })();
}
