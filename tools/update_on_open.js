/* update-on-open1 */
// 아이콘으로 프로그램을 켜면 새 버전이 있을 때 바로 받습니다. 업데이트 버튼을 눌러도 확인 창 없이 진행합니다.
(function () {
  if (window.__updateOnOpen) return;
  window.__updateOnOpen = true;
  let running = false;

  async function run() {
    if (running) return;
    running = true;
    try {
      const status = await fetch("/api/update/status?refresh=1", { cache: "no-store" });
      if (!status.ok) return;
      const data = await status.json();
      if (!data || !data.newer || (data.applying && data.applying.running)) return;
      const button = document.getElementById("appUpdate");
      if (button) {
        button.hidden = false;
        button.disabled = true;
        button.textContent = "받는 중…";
      }
      if (typeof toast === "function") toast("새 버전을 받아 다시 켭니다.");
      const res = await fetch("/api/update/apply", { method: "POST" });
      const body = await res.json();
      if (!body.started) {
        if (button) {
          button.disabled = false;
          const remote = data.status && data.status.remote_version;
          button.textContent = remote ? ("v" + remote) : "업데이트";
        }
        if (typeof toast === "function") toast(body.message || "업데이트를 시작하지 못했습니다.", true);
        return;
      }
      const oldVersion = data.local_version;
      for (let i = 0; i < 120; i++) {
        await new Promise((resolve) => setTimeout(resolve, 3000));
        try {
          const edition = await fetch("/api/edition", { cache: "no-store" });
          if (edition.ok) {
            const info = await edition.json();
            if (info.version && info.version !== oldVersion) {
              location.reload();
              return;
            }
          }
        } catch (_) {
          /* 프로그램을 다시 켜는 중 */
        }
      }
    } catch (_) {
      /* 확인이 안 되면 지금 버전으로 계속 씁니다 */
    } finally {
      running = false;
    }
  }

  setTimeout(() => { run(); }, 1200);

  document.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof Element) || !target.closest("#appUpdate")) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    run();
  }, true);
})();
