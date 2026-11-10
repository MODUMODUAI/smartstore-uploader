/* seller-alpha-label1 */
// 셀러용 알파: 로그인 창과 프로그램 이름에 셀러용 알파라고 보여 줍니다.
(function () {
  if (window.__sellerAlphaLabel) return;
  window.__sellerAlphaLabel = true;
  let alpha = false;
  const name = "셀러용 알파";

  function paint() {
    if (!alpha) return;
    document.body.classList.add("edition-alpha");
    const badge = document.getElementById("appEdition");
    if (badge && badge.textContent !== name) badge.textContent = name;
    if (document.title.indexOf("알파") < 0) {
      document.title = document.title.indexOf("테스트용") >= 0
        ? document.title.replace("테스트용", name)
        : ("모두모두AI " + name);
    }
    const loginTitle = document.getElementById("sellerLoginTitle");
    if (loginTitle) {
      const last = loginTitle.lastChild;
      if (last && last.nodeType === 3 && last.nodeValue.indexOf("알파") < 0) last.nodeValue = " " + name;
    }
  }

  fetch("/api/edition", { cache: "no-store" })
    .then((response) => (response.ok ? response.json() : {}))
    .then((data) => {
      alpha = Boolean(data && (data.alpha || /알파/.test(String((data && data.label) || ""))));
      if (!alpha) return;
      paint();
      [300, 800, 1600, 3200].forEach((delay) => setTimeout(paint, delay));
    })
    .catch(() => {});
})();
