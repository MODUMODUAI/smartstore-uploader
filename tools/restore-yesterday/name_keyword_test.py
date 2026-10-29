"""Forbidden keywords also leave product tags, and the name dialog shows the detail page."""

import subprocess
import unittest
from pathlib import Path

import patch_inquiry_links as patch


class NameKeywordTest(unittest.TestCase):
    def test_forbidden_words_leave_tags_but_keep_fragments(self):
        start = patch.NAME_FORBID_JS.index("/* forbid-pure-start */")
        end = patch.NAME_FORBID_JS.index("/* forbid-pure-end */")
        script = patch.NAME_FORBID_JS[start:end] + r"""
const words = ["무료배송", "정품", "나이키"];
if (stripForbiddenText("나이키 정품 운동화 무료배송", words) !== "운동화") throw new Error("name");
if (stripForbiddenText("정품인증 무료", words) !== "인증 무료") throw new Error("fragment");
const tags = stripForbiddenTags(["정품", "정품인증", "무료", "무료배송특가", "운동화"], words);
if (tags.join(",") !== "인증,무료,특가,운동화") throw new Error(tags.join(","));
"""
        path = Path("/tmp/name-forbid-test.js")
        path.write_text(script, encoding="utf-8")
        subprocess.run(["node", str(path)], check=True)

    def test_name_dialog_opens_detail_beside_it(self):
        self.assertIn("/* name-keyword-tags1 */", patch.NAME_FORBID_JS)
        self.assertIn("nameDetailPane", patch.NAME_FORBID_JS)
        self.assertIn("상세페이지", patch.NAME_FORBID_JS)
        self.assertIn("stripForbiddenTags", patch.NAME_FORBID_JS)
        self.assertIn("#nameDialog.name-with-detail", patch.NAME_FORBID_CSS)
        html = patch.patch_html(
            '<li>등록금지키워드: 상품명에서 빼야 하는 말을 등록합니다. 등록한 말이 그대로 들어 있을 때만 빠지고, 그 말의 일부는 남습니다.</li>'
            '<li>경쟁강도 낮음 단어는 뺍니다. Claude 키가 있으면 상품명은 Claude로 만들고, 없으면 설정에서 고른 AI를 씁니다.</li>'
            '<span id="appVersion">v2026.10.28.42</span><script src="/static/app.js?v=1"></script></body>'
        )
        self.assertIn("상품명과 상품태그에서 빼야 하는 말", html)
        self.assertIn("옆에 그 상품의 상세페이지가 함께 열립니다", html)
        self.assertEqual(patch.SCREEN_VERSION, "2026.10.28.49")
        self.assertIn("nameCharCount", patch.NAME_COUNT_JS)
        self.assertIn("benefitDialog", patch.NAME_COUNT_JS)
        self.assertIn("nameKeywordDialog", patch.NAME_COUNT_JS)
        self.assertIn("deliveryDialog", patch.NAME_COUNT_JS)
        help_html = patch.patch_help(
            "<li>상품명: 공급처 상품명 그대로입니다. 상품명바꾸기와 상품명AI로 바꾼 뒤에는 그 이름이 저장됩니다.</li>"
        )
        self.assertIn("100자까지이고, 칸 오른쪽에 글자수가 보입니다", help_html)

    def test_name_count_and_menu_save_close(self):
        start = patch.NAME_COUNT_JS.index("function nameCharCount")
        end = patch.NAME_COUNT_JS.index("if (typeof inputCell")
        script = patch.NAME_COUNT_JS[start:end] + r"""
if (nameCharCount("가나다") !== 3) throw new Error("ko");
if (nameCharCount("abc") !== 3) throw new Error("en");
if (menuSaveClosesDialog("/api/benefit", { method: "PUT" }) !== "benefitDialog") throw new Error("benefit");
if (menuSaveClosesDialog("/api/name-keywords", { method: "GET" }) !== "") throw new Error("get keywords");
if (menuSaveClosesDialog("/api/name-keywords", { method: "PUT" }) !== "nameKeywordDialog") throw new Error("keywords");
if (menuSaveClosesDialog("/api/delivery-templates", { method: "POST" }) !== "deliveryDialog") throw new Error("delivery");
if (menuSaveClosesDialog("/api/delivery-templates/import", { method: "POST" }) !== "") throw new Error("import");
if (menuSaveClosesDialog("/api/delivery-templates/abc", { method: "PUT" }) !== "deliveryDialog") throw new Error("delivery put");
"""
        path = Path("/tmp/name-count-test.js")
        path.write_text(script, encoding="utf-8")
        subprocess.run(["node", str(path)], check=True)


if __name__ == "__main__":
    unittest.main()
