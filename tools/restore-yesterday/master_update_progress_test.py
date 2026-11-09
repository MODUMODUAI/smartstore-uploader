"""Progress for the master (original) product update follows done/total."""

import subprocess
import unittest
from pathlib import Path

import patch_inquiry_links as patch


def _pure():
    start = patch.MASTER_UPDATE_PROGRESS_JS.index("/* master-update-pure-start */")
    end = patch.MASTER_UPDATE_PROGRESS_JS.index("/* master-update-pure-end */")
    return patch.MASTER_UPDATE_PROGRESS_JS[start:end]


class MasterUpdateProgressTest(unittest.TestCase):
    def test_counts_move_the_bar_and_edges_stay_honest(self):
        script = _pure() + r"""
function same(state, hidden, percent, tone, label) {
  if (Boolean(state.hidden) !== hidden) throw new Error("hidden " + tone + " " + JSON.stringify(state));
  if (state.percent !== percent) throw new Error("percent " + tone + " " + state.percent);
  if (state.tone !== tone) throw new Error("tone " + tone + " " + state.tone);
  if (label != null && state.label !== label) throw new Error("label " + tone + " " + state.label);
}
same(masterUpdateState(null), true, 0, "idle", "");
same(masterUpdateState({ status: "idle" }), true, 0, "idle", "");
const empty = masterUpdateState({ status: "done", done: 0, total: 0, updated: 0, failed: 0 });
same(empty, false, 0, "empty", "업데이트할 원본상품이 없습니다.");
if (empty.indeterminate) throw new Error("empty should not spin");
const one = masterUpdateState({ status: "running", done: 0, total: 1 });
same(one, false, 0, "running", "원본상품 정보 업데이트 0/1");
if (one.indeterminate) throw new Error("one item is determinate");
same(masterUpdateState({ status: "running", done: 1, total: 1 }), false, 100, "running", "원본상품 정보 업데이트 1/1");
const many = [0, 1, 3, 8].map((done) => masterUpdateState({ status: "running", done: done, total: 8 }));
if (many.map((state) => state.percent).join(",") !== "0,13,38,100") throw new Error(many.map((state) => state.percent).join(","));
many.forEach((state) => {
  if (state.tone !== "running" || state.hidden || state.indeterminate) throw new Error("many");
});
const unknown = masterUpdateState({ status: "running", done: 0, total: 0 });
if (!unknown.indeterminate || unknown.percent !== 0) throw new Error("unknown total");
if (unknown.label !== "원본상품 정보를 업데이트하는 중입니다.") throw new Error(unknown.label);
const failed = masterUpdateState({ status: "error", done: 2, total: 8, message: "공급처 응답이 없습니다." });
same(failed, false, 25, "error", "공급처 응답이 없습니다.");
const stopped = masterUpdateState({ status: "cancelled", done: 2, total: 8, updated: 2, failed: 0 });
same(stopped, false, 25, "stopped", "정보 업데이트를 멈췄습니다. 2개 반영, 실패 0개.");
const finished = masterUpdateState({ status: "done", done: 8, total: 8, updated: 8, failed: 0 });
same(finished, false, 100, "done", "원본상품 8개의 정보를 업데이트했습니다. 실패 0개.");
const partial = masterUpdateState({ status: "done", done: 8, total: 8, updated: 5, failed: 3 });
same(partial, false, 100, "error", "원본상품 5개의 정보를 업데이트했습니다. 실패 3개.");
if (!masterUpdatePath("/api/products/refresh-original")) throw new Error("start path");
if (!masterUpdatePath("/api/product-refresh-jobs/job-1")) throw new Error("poll path");
if (masterUpdatePath("/api/product-refresh-jobs/job-1/cancel")) throw new Error("cancel path");
if (masterUpdatePath("/api/products/refresh-market")) throw new Error("market path");
if (masterUpdateFollowsStatus("원본상품 정보를 업데이트하는 중입니다.", true, false, "") !== "start") throw new Error("start");
if (masterUpdateFollowsStatus("원본상품 정보를 업데이트하는 중입니다.", true, true, "done") !== "start") throw new Error("restart");
if (masterUpdateFollowsStatus("원본상품 정보를 업데이트하는 중입니다.", true, true, "running") !== "keep") throw new Error("do not restart a running update");
if (masterUpdateFollowsStatus("원본상품 정보 업데이트 3/8", true, true, "running") !== "keep") throw new Error("keep running");
if (masterUpdateFollowsStatus("대기", false, true, "done") !== "keep") throw new Error("keep finished");
if (masterUpdateFollowsStatus("저장하는 중입니다.", true, true, "done") !== "clear") throw new Error("clear next job");
if (masterUpdateFollowsStatus("저장하는 중입니다.", true, true, "running") !== "keep") throw new Error("do not clear a running update");
"""
        path = Path("/tmp/master-update-progress-pure.js")
        path.write_text(script, encoding="utf-8")
        subprocess.run(["node", str(path)], check=True)
        full = Path("/tmp/master-update-progress.js")
        full.write_text(patch.MASTER_UPDATE_PROGRESS_JS, encoding="utf-8")
        subprocess.run(["node", "--check", str(full)], check=True)

    def test_patch_appends_bar_after_the_current_screen(self):
        self.assertIn("data-master-update-progress", patch.MASTER_UPDATE_PROGRESS_JS)
        self.assertIn("원본상품 정보 업데이트", patch.MASTER_UPDATE_PROGRESS_JS)
        self.assertIn("#03C75A", patch.MASTER_UPDATE_PROGRESS_CSS)
        self.assertNotIn("100vw", patch.MASTER_UPDATE_PROGRESS_CSS)
        styled = patch.patch_css("/* image-pick-fit1 */\n#imageDialog { width: 90vw; }\n")
        self.assertIn("/* master-update-progress1 */", styled)
        self.assertGreater(styled.rindex("/* master-update-progress1 */"), styled.rindex("/* image-pick-fit1 */"))
        self.assertGreater(styled.rindex("90vw"), styled.rindex("100vw") if "100vw" in styled else 0)
        scripted = patch.patch_answer("function renderImageEditor(){ return 1; }\n")
        self.assertIn("/* master-update-progress1 */", scripted)
        self.assertGreater(scripted.rindex("/* master-update-progress1 */"), scripted.rindex("/* image-pick1 */"))
        self.assertEqual(patch.SCREEN_VERSION, "2026.10.28.76")
        help_html = patch.patch_help("<p>이미지바꾸기: 대표 이미지를 바꾸고, 순서를 정하고, 빼거나 넣습니다.</p>")
        self.assertIn("끝난 개수만큼 진행 막대", help_html)
        again = patch.patch_css(styled)
        self.assertEqual(again.count("/* master-update-progress1 */"), 1)


if __name__ == "__main__":
    unittest.main()
