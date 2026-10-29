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
        self.assertEqual(patch.SCREEN_VERSION, "2026.10.28.65")
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


    def test_name_dialog_column_stays_wide_beside_keywords(self):
        css = patch.NAME_FORBID_CSS + patch.NAME_COUNT_CSS + patch.NAME_LAYOUT_CSS
        self.assertLess(css.index("max-width: 46vw"), css.index("/* name-layout1 */"))
        self.assertIn("/* name-layout1 */", patch.NAME_LAYOUT_JS)
        self.assertIn("name-has-keywords", patch.NAME_LAYOUT_CSS)
        self.assertIn("min-width: min(760px, 100%)", patch.NAME_LAYOUT_CSS)
        styled = patch.patch_css("/* name-keyword-tags1 */\n/* name-count1 */\n")
        self.assertIn("/* name-layout1 */", styled)
        self.assertGreater(styled.rindex("/* name-layout1 */"), styled.rindex("/* name-count1 */"))
        scripted = patch.patch_answer("function openNameEditor(){ return 1; }\n")
        self.assertIn("/* name-layout1 */", scripted)
        self.assertGreater(scripted.rindex("/* name-layout1 */"), scripted.rindex("/* name-count1 */"))
        layout_js = Path("/tmp/name-layout.js")
        layout_js.write_text(patch.NAME_LAYOUT_JS, encoding="utf-8")
        subprocess.run(["node", "--check", str(layout_js)], check=True)
        self.assertIn("/* dialog-resize1 */", patch.DIALOG_RESIZE_JS)
        self.assertIn("dialog-resize-handle", patch.DIALOG_RESIZE_CSS)
        styled_resize = patch.patch_css(styled)
        self.assertGreater(styled_resize.rindex("/* dialog-resize1 */"), styled_resize.rindex("/* name-layout1 */"))
        start = patch.DIALOG_RESIZE_JS.index("/* resize-pure-start */")
        end = patch.DIALOG_RESIZE_JS.index("/* resize-pure-end */")
        script = patch.DIALOG_RESIZE_JS[start:end] + r"""
const right = dialogResizeBox("right", 100, 400, 80, 1400, 360);
if (right.left !== 100 || right.width !== 480) throw new Error("right " + JSON.stringify(right));
const left = dialogResizeBox("left", 200, 500, -40, 1400, 360);
if (left.left !== 160 || left.width !== 540) throw new Error("left " + JSON.stringify(left));
const clamped = dialogResizeBox("left", 20, 400, -80, 1400, 360);
if (clamped.left !== 8 || clamped.left + clamped.width !== 420) throw new Error("clamp " + JSON.stringify(clamped));
const shrunk = dialogResizeBox("right", 100, 500, -80, 1400, 360);
if (shrunk.width !== 420 || shrunk.left !== 100) throw new Error("shrink " + JSON.stringify(shrunk));
"""
        resize_js = Path("/tmp/dialog-resize-test.js")
        resize_js.write_text(script, encoding="utf-8")
        subprocess.run(["node", str(resize_js)], check=True)
        full_js = Path("/tmp/dialog-resize-full.js")
        full_js.write_text(patch.DIALOG_RESIZE_JS, encoding="utf-8")
        subprocess.run(["node", "--check", str(full_js)], check=True)
        start = patch.MENU_SAVE_CLOSE2_JS.index("/* save-close-pure-start */")
        end = patch.MENU_SAVE_CLOSE2_JS.index("/* save-close-pure-end */")
        save_script = patch.MENU_SAVE_CLOSE2_JS[start:end] + r"""
if (!menuSaveButtonCloses("저장")) throw new Error("save");
if (!menuSaveButtonCloses("배송정보저장")) throw new Error("delivery");
if (!menuSaveButtonCloses("옵션 저장")) throw new Error("option");
if (menuSaveButtonCloses("닫기")) throw new Error("close");
if (menuSaveButtonCloses("저장 위치")) throw new Error("place");
if (!menuSaveRequestCloses("/api/products/1", "PUT")) throw new Error("product");
if (!menuSaveRequestCloses("/api/benefit", "PUT")) throw new Error("benefit");
if (menuSaveRequestCloses("/api/delivery-templates/import", "POST")) throw new Error("import");
if (menuSaveRequestCloses("/api/products/1/name/suggest", "POST")) throw new Error("suggest");
if (menuSaveRequestCloses("/api/benefit", "GET")) throw new Error("get");
if (menuSaveRequestCloses("/api/products/collect", "POST")) throw new Error("collect");
"""
        save_js = Path("/tmp/menu-save-close-test.js")
        save_js.write_text(save_script, encoding="utf-8")
        subprocess.run(["node", str(save_js)], check=True)
        full_save = Path("/tmp/menu-save-close-full.js")
        full_save.write_text(patch.MENU_SAVE_CLOSE2_JS, encoding="utf-8")
        subprocess.run(["node", "--check", str(full_save)], check=True)
        self.assertIn("repeat(5, minmax(0, 1fr))", patch.IMAGE_ROW5_CSS)
        styled_images = patch.patch_css("/* image-work1 */\n/* dialog-resize1 */\n")
        self.assertIn("/* image-row5 */", styled_images)
        self.assertGreater(styled_images.rindex("/* image-row5 */"), styled_images.rindex("/* image-work1 */"))
        self.assertGreater(styled_images.rindex("/* image-row5 */"), styled_images.rindex("/* dialog-resize1 */"))

    def test_list_image_zoom_and_wholesale_shipping(self):
        start = patch.LIST_ZOOM_SHIP_JS.index("/* zoom-ship-pure-start */")
        end = patch.LIST_ZOOM_SHIP_JS.index("/* zoom-ship-pure-end */")
        script = patch.LIST_ZOOM_SHIP_JS[start:end] + r"""
if (listImagePixels(100) !== 500) throw new Error("500 " + listImagePixels(100));
if (listImagePixels(50) !== 250) throw new Error("250 " + listImagePixels(50));
if (zoomByStep(50, 20, 120, 5, 1) !== 55) throw new Error("step");
if (zoomByStep(50, 50, 200, 5, -1) !== 50) throw new Error("floor");
if (zoomByStep(103, 25, 200, 5, 0) !== 105) throw new Error("snap");
if (wholesaleShipAmount({ shipping_fee: 2500 }) !== 2500) throw new Error("fee");
if (wholesaleShipAmount({ shipping_fee: 0 }) !== 0) throw new Error("zero");
if (wholesaleShipAmount({ shipping_type: "F", shipping: 3000 }) !== 0) throw new Error("free");
if (wholesaleShipAmount({ shipping_type: "C", shipping: 4000 }) !== 0) throw new Error("collect");
if (wholesaleShipAmount({ delivery_fee: 3000 }) !== null) throw new Error("template");
if (wholesaleShipAmount({ extra: { shipping_fee: 1500 } }) !== 1500) throw new Error("nested");
if (marginRateWithShip(10000, 6000, 1000, 3000) !== 0) throw new Error("rate");
if (marginRateWithShip(10000, 6000, 1000, 0) !== 30) throw new Error("noship");
if (marginAdjustedForShip(20, 10000, 1000, 3000) !== 0) throw new Error("adjust");
if (shipFromMarginTitle("마켓 (판매가 10000 - 수수료 1000 - 공급가 6000 - 배송비 3000) / 판매가") !== 3000) throw new Error("title");
"""
        path = Path("/tmp/list-zoom-ship-test.js")
        path.write_text(script, encoding="utf-8")
        subprocess.run(["node", str(path)], check=True)
        full = Path("/tmp/list-zoom-ship-full.js")
        full.write_text(patch.LIST_ZOOM_SHIP_JS, encoding="utf-8")
        subprocess.run(["node", "--check", str(full)], check=True)
        styled = patch.patch_css("/* image-row5 */\n")
        self.assertIn("/* list-zoom-ship1 */", styled)
        scripted = patch.patch_answer("function openNameEditor(){ return 1; }\n")
        self.assertIn("/* list-zoom-ship1 */", scripted)
        self.assertGreater(scripted.rindex("/* list-zoom-ship1 */"), scripted.rindex("/* menu-save-close2 */"))
        help_html = patch.patch_help("<p>목록의 그림을 누르면 아래 미리보기에 보입니다.</p>")
        self.assertIn("500×500", help_html)
        self.assertIn("도매처 배송비", help_html)

    def test_name_and_attribute_zoom_steps(self):
        start = patch.DIALOG_ZOOM_JS.index("/* dialog-zoom-pure-start */")
        end = patch.DIALOG_ZOOM_JS.index("/* dialog-zoom-pure-end */")
        script = patch.DIALOG_ZOOM_JS[start:end] + r"""
if (dialogZoomPercent(100, 1) !== 105) throw new Error("plus " + dialogZoomPercent(100, 1));
if (dialogZoomPercent(100, -1) !== 95) throw new Error("minus " + dialogZoomPercent(100, -1));
if (dialogZoomPercent(25, -1) !== 25) throw new Error("floor");
if (dialogZoomPercent(200, 1) !== 200) throw new Error("ceil");
if (dialogZoomPercent(103, 0) !== 105) throw new Error("snap");
if (dialogZoomPercent("nope", 0) !== 100) throw new Error("bad");
"""
        path = Path("/tmp/dialog-zoom-test.js")
        path.write_text(script, encoding="utf-8")
        subprocess.run(["node", str(path)], check=True)
        full = Path("/tmp/dialog-zoom-full.js")
        full.write_text(patch.DIALOG_ZOOM_JS, encoding="utf-8")
        subprocess.run(["node", "--check", str(full)], check=True)
        scripted = patch.patch_answer("function openNameEditor(){ return 1; }\nfunction openAttributeEditor(){ return 1; }\n")
        self.assertIn("/* dialog-zoom1 */", scripted)
        self.assertGreater(scripted.rindex("/* dialog-zoom1 */"), scripted.rindex("/* naver-tag2 */"))
        self.assertIn("nameDetailZoomBar", patch.DIALOG_ZOOM_JS)
        self.assertIn("attributeZoomBar", patch.DIALOG_ZOOM_JS)
        styled = patch.patch_css("/* list-zoom-ship1 */\n")
        self.assertIn("/* dialog-zoom1 */", styled)
        self.assertGreater(styled.rindex("/* dialog-zoom1 */"), styled.rindex("/* list-zoom-ship1 */"))
        help_html = patch.patch_help(
            "<p>누르면 옆에 그 상품의 상세페이지가 함께 열립니다. 속성바꾸기, 속성AI: 카테고리에 맞는 속성을 넣습니다.</p>"
        )
        self.assertIn("상세페이지 크기는 5%씩", help_html)
        self.assertIn("크기 조절은 없습니다", help_html)
        self.assertNotIn("속성 칸 크기는 5%씩", help_html)

    def test_detail_dialog_keeps_intro_and_shrinks(self):
        self.assertIn("상세페이지추가글", patch.DETAIL_FIT_JS)
        self.assertIn("fillDetailIntroInEditor", patch.DETAIL_FIT_JS)
        self.assertIn("width: 70vw", patch.DETAIL_FIT_CSS)
        self.assertIn("height: 70vh", patch.DETAIL_FIT_CSS)
        self.assertNotIn("#imageDialog", patch.DETAIL_FIT_CSS)
        full = Path("/tmp/detail-fit-full.js")
        full.write_text(patch.DETAIL_FIT_JS, encoding="utf-8")
        subprocess.run(["node", "--check", str(full)], check=True)
        scripted = patch.patch_answer("function openDetailEditor(){ return 1; }\n")
        self.assertIn("/* detail-fit1 */", scripted)
        self.assertGreater(scripted.rindex("/* detail-fit1 */"), scripted.rindex("/* tag-dict1 */"))
        styled = patch.patch_css("/* image-work1 */\n#detailDialog { width: 100vw; height: 100vh; }\n")
        self.assertIn("/* detail-fit1 */", styled)
        self.assertGreater(styled.rindex("70vw"), styled.rindex("100vw"))
        help_html = patch.patch_help(
            "<p>상세페이지 바꾸기: 고른 상품의 상세페이지 글과 이미지를 고칩니다. 이미지 URL이나 파일로 그림을 넣을 수 있습니다.</p>"
        )
        self.assertIn("AI추가글", help_html)
        self.assertIn("30% 작습니다", help_html)
        self.assertNotIn("창 안에도 상세페이지추가글", help_html)

    def test_detail_intro_button_is_colored_and_url_is_short(self):
        self.assertIn("AI추가글", patch.DETAIL_INTRO_STYLE_JS)
        self.assertIn('menu.remove()', patch.DETAIL_INTRO_STYLE_JS)
        self.assertIn("#00c73c", patch.DETAIL_INTRO_STYLE_CSS)
        self.assertIn("width: 240px", patch.DETAIL_INTRO_STYLE_CSS)
        self.assertIn("display: none", patch.DETAIL_INTRO_STYLE_CSS)
        full = Path("/tmp/detail-intro-style-full.js")
        full.write_text(patch.DETAIL_INTRO_STYLE_JS, encoding="utf-8")
        subprocess.run(["node", "--check", str(full)], check=True)
        scripted = patch.patch_answer("function openDetailEditor(){ return 1; }\n")
        self.assertIn("/* detail-intro-style1 */", scripted)
        self.assertGreater(scripted.rindex("/* detail-intro-style1 */"), scripted.rindex("/* detail-fit1 */"))
        styled = patch.patch_css("/* detail-fit1 */\n")
        self.assertIn("/* detail-intro-style1 */", styled)
        self.assertGreater(styled.rindex("/* detail-intro-style1 */"), styled.rindex("/* detail-fit1 */"))

    def test_first_screen_shows_spinner_while_loading(self):
        self.assertIn("작업 중", patch.LOAD_SPIN_HTML)
        self.assertIn("/* load-spin1 */", patch.LOAD_SPIN_HTML)
        self.assertIn("/api/products", patch.LOAD_SPIN_HTML)
        self.assertIn("animation: load-spin", patch.LOAD_SPIN_CSS)
        html = patch.patch_html('<p>왼쪽 마켓선택에서 마스터상품과 마켓으로 보낸 상품을 나눠 봅니다.</p><script src="/static/app.js?v=1"></script>')
        self.assertIn("/* load-spin1 */", html)
        self.assertLess(html.index("/* load-spin1 */"), html.index('<script src="/static/app.js'))
        self.assertIn("작업 중 표시가 돕니다", html)
        styled = patch.patch_css("body { margin: 0; }\n")
        self.assertIn("/* load-spin1 */", styled)
        script = patch.LOAD_SPIN_HTML.split("<script>", 1)[1].split("</script>", 1)[0]
        full = Path("/tmp/load-spin1.js")
        full.write_text(script, encoding="utf-8")
        subprocess.run(["node", "--check", str(full)], check=True)

    def test_name_pane_save_keywords_and_image_size(self):
        start = patch.NAME_PANE_LIVE_JS.index("/* name-pane-pure-start */")
        end = patch.NAME_PANE_LIVE_JS.index("/* name-pane-pure-end */")
        script = patch.NAME_PANE_LIVE_JS[start:end] + r"""
if (detailPaneImageWidth(400, 100) !== 400) throw new Error("100 " + detailPaneImageWidth(400, 100));
if (detailPaneImageWidth(400, 105) !== 420) throw new Error("105 " + detailPaneImageWidth(400, 105));
if (detailPaneImageWidth(400, 103) !== 420) throw new Error("snap " + detailPaneImageWidth(400, 103));
if (detailPaneImageWidth(400, 25) !== 100) throw new Error("floor " + detailPaneImageWidth(400, 25));
if (detailPaneImageWidth(400, 200) !== 800) throw new Error("ceil " + detailPaneImageWidth(400, 200));
if (detailPaneImageWidth(333, 100) !== 333) throw new Error("fit " + detailPaneImageWidth(333, 100));
"""
        path = Path("/tmp/name-pane-live-test.js")
        path.write_text(script, encoding="utf-8")
        subprocess.run(["node", str(path)], check=True)
        full = Path("/tmp/name-pane-live-full.js")
        full.write_text(patch.NAME_PANE_LIVE_JS, encoding="utf-8")
        subprocess.run(["node", "--check", str(full)], check=True)
        self.assertIn("#03C75A", patch.NAME_PANE_LIVE_CSS)
        self.assertIn("flex-direction: column", patch.NAME_PANE_LIVE_CSS)
        self.assertIn("zoom: 1 !important", patch.NAME_PANE_LIVE_CSS)
        self.assertIn("font-size", patch.NAME_PANE_LIVE_JS)
        self.assertIn("1.2", patch.NAME_PANE_LIVE_JS)
        self.assertIn("nameSuggestKeywords", patch.NAME_PANE_LIVE_JS)
        scripted = patch.patch_answer("function openNameEditor(){ return 1; }\nfunction widenNameEditorColumn(){ return 1; }\n")
        self.assertIn("/* name-pane-live1 */", scripted)
        self.assertGreater(scripted.rindex("/* name-pane-live1 */"), scripted.rindex("/* prompt-narrow1 */"))
        styled = patch.patch_css("/* prompt-narrow1 */\n")
        self.assertIn("/* name-pane-live1 */", styled)
        self.assertGreater(styled.rindex("/* name-pane-live1 */"), styled.rindex("/* prompt-narrow1 */"))
        self.assertGreater(styled.rindex("max-width: 440px"), styled.rindex("min-width: min(760px, 100%)") if "min-width: min(760px, 100%)" in styled else 0)
        help_html = patch.patch_help("<p>누르면 옆에 그 상품의 상세페이지가 함께 열립니다. 상세페이지 크기는 5%씩 조절합니다.</p>")
        self.assertIn("저장은 네이버 초록색입니다", help_html)
        self.assertIn("검색어는 왼쪽 아래", help_html)
        self.assertIn("상세페이지는 더 넓습니다", help_html)
        self.assertIn("글씨는 20% 큽니다", help_html)
        self.assertIn("그림을 키우거나 줄입니다", help_html)


if __name__ == "__main__":
    unittest.main()
