"""Naver tag dictionary fill and leaf-category search tags."""

import subprocess
import unittest
from pathlib import Path

import patch_inquiry_links as patch


class NaverTagTest(unittest.TestCase):
    def setUp(self):
        self.ns = {"_NAVER_TAG_NO_INSTALL": True}
        exec(compile(patch.NAVER_TAG_SERVICE_PY, "<naver-tag>", "exec"), self.ns)

    def test_search_pages_keep_product_tag_order(self):
        page1 = """
        {"shoppingResult": {"products": [
          {"productName": "보이스캐디 SL2", "manuTag": "보이스캐디,골프,오늘출발"},
          {"productName": "부쉬넬", "manuTag": "부쉬넬,골프,니콘"}
        ]}}
        """
        page2 = '<script>{"manuTag":"알투지,미니,골프"}</script>'
        page3 = """
        {"products": [{"mallProductId": "9", "sellerTags": [
          {"text": "시계형"}, {"text": "미니"}, {"text": "오늘발송"}
        ]}]}
        """
        tags = self.ns["_collect_search_tags"]([page1, page2, page3])
        self.assertEqual(
            tags,
            ["보이스캐디", "골프", "부쉬넬", "니콘", "알투지", "미니", "시계형"],
        )

    def test_dictionary_text_is_kept_as_returned(self):
        rows = self.ns["_dictionary_rows"]([
            {"code": 11, "text": "미니"},
            {"code": 12, "text": "비거리측정"},
            {"code": 13, "text": "가성비 좋은"},
            {"code": 14, "text": "미니"},
        ])
        self.assertEqual([row["text"] for row in rows], ["미니", "비거리측정", "가성비 좋은"])
        self.assertEqual(rows[0]["code"], 11)
        wrapped = self.ns["_dictionary_rows"]({"tags": [{"code": 7, "text": "거리측정기"}]})
        self.assertEqual(wrapped, [{"text": "거리측정기", "code": 7}])

    def test_screen_script_asks_for_three_pages_and_the_dictionary(self):
        self.assertIn("naver-search", patch.NAVER_TAG_JS)
        self.assertIn("naver-dictionary", patch.NAVER_TAG_JS)
        self.assertIn("1–3페이지", patch.NAVER_TAG_JS)
        self.assertIn("태그넣기", patch.NAVER_TAG_JS)
        self.assertEqual(patch.SCREEN_VERSION, "2026.10.28.71")

    def test_search_tags_drop_brands_page_chrome_and_keep_words(self):
        ns = {"_NAVER_TAG_NO_INSTALL": True, "_NAVER_TAG2_NO_INSTALL": True}
        exec(compile(patch.NAVER_TAG_SERVICE_PY, "<naver-tag>", "exec"), ns)
        exec(compile(patch.NAVER_TAG2_SERVICE_PY, "<naver-tag2>", "exec"), ns)
        page = """
        {"shoppingResult": {"products": [
          {"productName": "보이스캐디 SL2", "brand": "보이스캐디", "manuTag": "보이스캐디,골프,1페이지 30개,오늘출발"},
          {"productName": "부쉬넬 A1", "brand": "부쉬넬", "manuTag": "부쉬넬,부쉬넬a1,골프,시계형"},
          {"productName": "니콘 쿨샷", "brand": "니콘", "manuTag": "니콘,미니,골프"},
          {"productName": "캐논 레이저", "brand": "캐논", "manuTag": "캐논,골프"},
          {"productName": "알투지", "maker": "알투지", "manuTag": "알투지,인피테,마이애이밍"},
          {"productName": "도미 레이저", "brand": "도미", "manuTag": "도미,골프"},
          {"productName": "인피테 미니", "brand": "인피테", "manuTag": "인피테,미니"},
          {"productName": "마이애이밍", "brand": "마이애이밍", "manuTag": "마이애이밍,시계형"},
          {"productName": "캐디톡 미니온2", "brand": "캐디톡", "manuTag": "캐디톡미니온2,미니"}
        ]}}
        """
        ns["_naver_tag2_local"].brands = set()
        ns["_naver_tag2_local"].counts = {}
        raw = ns["_collect_search_tags"]([page])
        brands = set(ns["_naver_tag2_local"].brands)
        filtered = ns["_naver_filter_search_tags"](raw, "거리측정기", brands, dict(ns["_naver_tag2_local"].counts))
        self.assertEqual(filtered, ["골프", "미니", "시계형"])
        for brand in ("보이스캐디", "부쉬넬", "니콘", "캐논", "알투지", "도미", "인피테", "마이애이밍", "캐디톡"):
            self.assertIn(brand, brands)
        self.assertNotIn("1페이지30개", filtered)
        self.assertNotIn("부쉬넬a1", filtered)
        self.assertNotIn("캐디톡미니온2", filtered)
        dictionary = ns["_naver_dictionary_before_tag2"]
        ns["_naver_known_brands"].update(brands)

        def fake_dictionary(keyword):
            return [{"text": "골프", "code": 1}, {"text": "부쉬넬", "code": 2}, {"text": "가성비좋은", "code": 3}, {"text": "1페이지 30개", "code": 4}]

        ns["_naver_dictionary_before_tag2"] = fake_dictionary
        # The wrapper closed over the original function object, so call the filter directly.
        kept = ns["_naver_filter_search_tags"](
            ["골프", "부쉬넬", "가성비좋은", "1페이지 30개"],
            "거리측정기",
            brands,
            {},
        )
        self.assertEqual(kept, ["골프", "가성비좋은"])

    def test_screen_drops_unusable_tags_and_keeps_brand_words(self):
        start = patch.NAVER_TAG2_JS.index("/* tag2-pure-start */")
        end = patch.NAVER_TAG2_JS.index("/* tag2-pure-end */")
        script = patch.NAVER_TAG2_JS[start:end] + r"""
if (!naverTagJunk("1페이지 30개")) throw new Error("page");
if (naverTagJunk("골프")) throw new Error("golf junk");
if (naverTagBrandHit("부쉬넬a1", ["부쉬넬"]) !== "부쉬넬") throw new Error("model");
if (naverTagBrandHit("미니", ["부쉬넬", "니콘"]) !== "") throw new Error("mini");
const result = naverTagsToDrop(
  ["골프", "부쉬넬", "부쉬넬a1", "1페이지30개", "미니", "정품인증", "시계형"],
  ["부쉬넬", "니콘", "도미", "인피테"],
  ["정품"],
  [{token: "거리측정기", reason: "카테고리명"}]
);
if (result.kept.join(",") !== "골프,미니,시계형") throw new Error(result.kept.join(","));
if (result.dropped.indexOf("부쉬넬") < 0 || result.dropped.indexOf("정품인증") < 0) throw new Error("drop");
if (!naverTagKeep("시계형", ["부쉬넬"], [], ["거리측정기"])) throw new Error("keep");
if (naverTagKeep("거리측정기", [], [], ["거리측정기"])) throw new Error("category");
"""
        path = Path("/tmp/naver-tag2-test.js")
        path.write_text(script, encoding="utf-8")
        subprocess.run(["node", str(path)], check=True)
        full = Path("/tmp/naver-tag2-full.js")
        full.write_text(patch.NAVER_TAG2_JS, encoding="utf-8")
        subprocess.run(["node", "--check", str(full)], check=True)
        scripted = patch.patch_answer("function openNameEditor(){ return 1; }\n")
        self.assertIn("/* naver-tag2 */", scripted)

    def test_dictionary_suggest_keeps_typed_prefix(self):
        ns = {"_NAVER_TAG_NO_INSTALL": True, "_NAVER_TAG2_NO_INSTALL": True, "_TAG_DICT_NO_INSTALL": True}
        exec(compile(patch.NAVER_TAG_SERVICE_PY, "<naver-tag>", "exec"), ns)
        exec(compile(patch.NAVER_TAG2_SERVICE_PY, "<naver-tag2>", "exec"), ns)
        exec(compile(patch.TAG_DICT_SERVICE_PY, "<tag-dict>", "exec"), ns)
        ns["_naver_known_brands"].update({"부쉬넬"})

        def fake_dictionary(keyword):
            self.assertEqual(keyword, "견고한")
            return [
                {"text": "견고한", "code": 1},
                {"text": "견고한자", "code": 2},
                {"text": "견고한재질", "code": 3},
                {"text": "견고한선반", "code": 4},
                {"text": "견고한텐트", "code": 5},
                {"text": "부쉬넬견고", "code": 6},
                {"text": "선반튼튼", "code": 7},
                {"text": "1페이지 30개", "code": 8},
            ]

        ns["_naver_dictionary_before_tag2"] = fake_dictionary
        rows = ns["_tag_dict_suggest"]("견고한", "선반")
        self.assertEqual(
            [row["text"] for row in rows],
            ["견고한", "견고한자", "견고한재질", "견고한선반", "견고한텐트"],
        )
        blocked = ns["_naver_filter_search_tags"](
            ["견고한", "견고한자", "견고한재질"],
            "견고한",
            set(),
            {},
        )
        self.assertEqual(blocked, [])
        start = patch.TAG_DICT_JS.index("/* tag-dict-pure-start */")
        end = patch.TAG_DICT_JS.index("/* tag-dict-pure-end */")
        script = patch.TAG_DICT_JS[start:end] + r"""
if (tagDictDirectLabel("견고한") !== "직접입력: 견고한") throw new Error("direct");
if (tagDictDirectLabel("  ") !== "") throw new Error("blank");
const parts = tagDictParts("견고한선반", "견고한");
if (parts.length !== 2 || !parts[0].hit || parts[0].text !== "견고한" || parts[1].text !== "선반") throw new Error("parts");
const exact = tagDictParts("견고한", "견고한");
if (exact.length !== 1 || !exact[0].hit) throw new Error("exact");
const texts = tagDictTexts([{text: "견고한"}, "견고한자", {text: "견고한"}, "견고한재질"]);
if (texts.join(",") !== "견고한,견고한자,견고한재질") throw new Error(texts.join(","));
"""
        path = Path("/tmp/tag-dict-test.js")
        path.write_text(script, encoding="utf-8")
        subprocess.run(["node", str(path)], check=True)
        full = Path("/tmp/tag-dict-full.js")
        full.write_text(patch.TAG_DICT_JS, encoding="utf-8")
        subprocess.run(["node", "--check", str(full)], check=True)
        scripted = patch.patch_answer("function openTagEditor(){ return 1; }\n")
        self.assertIn("/* tag-dict1 */", scripted)
        self.assertGreater(scripted.rindex("/* tag-dict1 */"), scripted.rindex("/* dialog-zoom1 */"))
        styled = patch.patch_css("/* dialog-zoom1 */\n")
        self.assertIn("/* tag-dict1 */", styled)

    def test_pages_two_and_three_keep_tags_and_drop_brands(self):
        ns = {"_NAVER_TAG_NO_INSTALL": True, "_NAVER_TAG2_NO_INSTALL": True, "_NAVER_TAG3_NO_INSTALL": True}
        exec(compile(patch.NAVER_TAG_SERVICE_PY, "<naver-tag>", "exec"), ns)
        exec(compile(patch.NAVER_TAG2_SERVICE_PY, "<naver-tag2>", "exec"), ns)
        exec(compile(patch.NAVER_TAG3_SERVICE_PY, "<naver-tag3>", "exec"), ns)
        page1 = """
        {"shoppingResult": {"products": [
          {"productName": "보이스캐디 SL2", "brand": "보이스캐디", "manuTag": "보이스캐디,골프,오늘출발"}
        ]}}
        """
        page2 = """
        <html><script id="__NEXT_DATA__" type="application/json">{"shoppingResult":{"products":[
          {"productName":"부쉬넬 A2","brand":"부쉬넬","manuTag":"부쉬넬,레이저,골프,초정밀부쉬넬"}
        ]}}</script></html>
        """
        page3 = """
        {"products": [{"productTitle": "니콘 쿨샷", "maker": "니콘", "sellerTags": [{"text": "니콘"}, {"text": "미니"}, {"text": "시계형"}]}]}
        """
        flat, page_tags, brands, states = ns["_naver_tag3_collect"]([page1, page2, page3], "거리측정기")
        self.assertEqual(states, ["ok", "ok", "ok"])
        self.assertIn("레이저", page_tags[1])
        self.assertIn("미니", page_tags[2])
        self.assertIn("시계형", page_tags[2])
        self.assertNotIn("부쉬넬", flat)
        self.assertNotIn("초정밀부쉬넬", flat)
        self.assertNotIn("니콘", flat)
        self.assertNotIn("보이스캐디", flat)
        for brand in ("보이스캐디", "부쉬넬", "니콘"):
            self.assertIn(brand, brands)
        self.assertIn('"logic": "PART"', patch.NAVER_TAG3_SERVICE_PY)
        self.assertIn("pagingIndex", patch.NAVER_TAG3_SERVICE_PY)
        blocked = '<html><div class="content_error">쇼핑 서비스 접속이 일시적으로 제한되었습니다.</div></html>'
        _, empty_pages, _, empty_states = ns["_naver_tag3_collect"]([page1, blocked, ""], "거리측정기")
        self.assertEqual(empty_states[1], "blocked")
        self.assertEqual(empty_states[2], "blocked")
        self.assertTrue(empty_pages[0])
        self.assertEqual(empty_pages[1], [])
        scripted = patch.patch_answer("function openTagEditor(){ return 1; }\n")
        self.assertIn("/* tag-page1 */", scripted)
        self.assertGreater(scripted.rindex("/* tag-page1 */"), scripted.rindex("/* naver-tag2 */"))
        full = Path("/tmp/tag-page-full.js")
        full.write_text(patch.TAG_PAGE_JS, encoding="utf-8")
        subprocess.run(["node", "--check", str(full)], check=True)

    def test_image_zoom_moves_right_and_attribute_bar_goes_away(self):
        self.assertIn('range.step = "5"', patch.IMAGE_ZOOM_RIGHT_JS)
        self.assertIn("closeImage", patch.IMAGE_ZOOM_RIGHT_JS)
        self.assertIn("attributeZoomBar", patch.IMAGE_ZOOM_RIGHT_JS)
        self.assertIn("bar.remove()", patch.IMAGE_ZOOM_RIGHT_JS)
        self.assertIn("#attributeZoomBar { display: none", patch.IMAGE_ZOOM_RIGHT_CSS)
        self.assertIn("margin: 0 0 0 auto", patch.IMAGE_ZOOM_RIGHT_CSS)
        full = Path("/tmp/image-zoom-right.js")
        full.write_text(patch.IMAGE_ZOOM_RIGHT_JS, encoding="utf-8")
        subprocess.run(["node", "--check", str(full)], check=True)
        scripted = patch.patch_answer("function openImageEditor(){ return 1; }\n")
        self.assertIn("/* image-zoom-right1 */", scripted)
        styled = patch.patch_css("body{}\n")
        self.assertIn("/* image-zoom-right1 */", styled)
        help_html = patch.patch_help("<p>직접 넣거나 AI 채우기로 만듭니다.</p>")
        self.assertIn("태그사전 후보", help_html)

    def test_image_zoom_changes_slot_by_five_percent(self):
        self.assertIn("const step = 5", patch.IMAGE_ZOOM_LIVE_JS)
        self.assertIn("Math.round(500 * percent / 100)", patch.IMAGE_ZOOM_LIVE_JS)
        self.assertIn('fresh.dataset.zoomLive = "1"', patch.IMAGE_ZOOM_LIVE_JS)
        self.assertIn("stopImmediatePropagation", patch.IMAGE_ZOOM_LIVE_JS)
        self.assertIn("renderImageEditor", patch.IMAGE_ZOOM_LIVE_JS)
        self.assertIn("grid-template-columns", patch.IMAGE_ZOOM_LIVE_JS)
        self.assertIn("repeat(5, var(--image-slot-size, 125px)) !important", patch.IMAGE_ZOOM_LIVE_CSS)
        self.assertIn("width: var(--image-slot-size, 125px) !important", patch.IMAGE_ZOOM_LIVE_CSS)
        full = Path("/tmp/image-zoom-live.js")
        full.write_text(patch.IMAGE_ZOOM_LIVE_JS, encoding="utf-8")
        subprocess.run(["node", "--check", str(full)], check=True)
        scripted = patch.patch_answer("function openImageEditor(){ return 1; }\nfunction renderImageEditor(){ return 1; }\n")
        self.assertIn("/* image-zoom-live1 */", scripted)
        self.assertGreater(scripted.rindex("/* image-zoom-live1 */"), scripted.rindex("/* image-zoom-right1 */"))
        styled = patch.patch_css("/* image-row5 */\n")
        self.assertIn("/* image-zoom-live1 */", styled)
        self.assertGreater(styled.rindex("/* image-zoom-live1 */"), styled.rindex("/* image-row5 */"))
        help_html = patch.patch_help("<p>이미지바꾸기: 대표 이미지를 바꾸고, 순서를 정하고, 빼거나 넣습니다.</p>")
        self.assertIn("그림 칸도 같이 커지거나 작아집니다", help_html)

    def test_product_keywords_come_from_naver_autocomplete(self):
        ns = {"_NAVER_KEYWORD_NO_INSTALL": True}
        exec(compile(patch.NAVER_KEYWORD_SERVICE_PY, "<naver-keyword>", "exec"), ns)
        payload = {
            "items": [[
                ["골프거리측정기", "0"],
                ["거리측정기", "0"],
                ["골프 거리측정기 순위", "0"],
                ["거리측정기 케이스", "0"],
                ["부쉬넬 거리측정기", "0"],
                ["레이저 거리측정기", "0"],
                ["보이스캐디 거리측정기", "0"],
                ["레이저 거리측정기", "0"],
                ["니콘 거리측정기", "0"],
                ["도미 거리측정기", "0"],
            ]]
        }
        words = ns["_naver_keyword_rows"](payload)
        self.assertEqual(words[0], "골프거리측정기")
        self.assertIn("레이저 거리측정기", words)
        self.assertEqual(words.count("레이저 거리측정기"), 1)
        self.assertLessEqual(len(words), 20)
        self.assertIn("부쉬넬 거리측정기", words)
        seen = {}

        def fake_get(url, params, headers):
            seen["url"] = url
            seen["q"] = params.get("q")
            seen["st"] = params.get("st")
            return 200, '{"items":[[["골프거리측정기","0"],["레이저 거리측정기","0"]]]}'

        ns["_naver_http_get"] = fake_get
        got = ns["_naver_product_keywords"]("부쉬넬 거리측정기")
        self.assertEqual(seen["url"], "https://ac.search.naver.com/nx/ac")
        self.assertEqual(seen["q"], "부쉬넬 거리측정기")
        self.assertEqual(seen["st"], "100")
        self.assertEqual(got, ["골프거리측정기", "레이저 거리측정기"])
        self.assertIn("/api/tags/naver-keywords", patch.NAVER_KEYWORD_SERVICE_PY)
        full = Path("/tmp/product-keyword.js")
        full.write_text(patch.PRODUCT_KEYWORD_JS, encoding="utf-8")
        subprocess.run(["node", "--check", str(full)], check=True)
        scripted = patch.patch_answer("function openTagEditor(){ return 1; }\nfunction loadNaverSearchTags(){ return 1; }\n")
        self.assertIn("/* product-keyword1 */", scripted)
        self.assertIn("이 상품 검색어", patch.PRODUCT_KEYWORD_JS)
        self.assertGreater(scripted.rindex("/* product-keyword1 */"), scripted.rindex("/* tag-page1 */"))
        help_html = patch.patch_help("<p>카테고리, 브랜드, 판매자명이 포함된 태그는 등록되지 않습니다.</p>")
        self.assertIn("그 상품 이름의 네이버 검색어", help_html)

    def test_image_dialog_width_is_ten_percent_narrower(self):
        self.assertIn("width: 90vw", patch.IMAGE_NARROW_CSS)
        self.assertIn("max-width: 90vw", patch.IMAGE_NARROW_CSS)
        self.assertIn("box-sizing: border-box", patch.IMAGE_NARROW_CSS)
        self.assertIn("height: 100vh", patch.IMAGE_NARROW_CSS)
        self.assertIn("inset: 0", patch.IMAGE_NARROW_CSS)
        self.assertNotIn("#detailDialog", patch.IMAGE_NARROW_CSS)
        styled = patch.patch_css("#imageDialog { width: 100vw; height: 100vh; }\n")
        self.assertIn("/* image-narrow1 */", styled)
        self.assertGreater(styled.rindex("90vw"), styled.rindex("100vw"))
        help_html = patch.patch_help("<p>이미지바꾸기: 대표 이미지를 바꾸고, 순서를 정하고, 빼거나 넣습니다.</p>")
        self.assertIn("창 가로는 화면보다 10% 좁습니다", help_html)
        self.assertIn("그림 칸도 같이 커지거나 작아집니다", help_html)

    def test_prompt_field_shrinks_and_menu_shifts_left(self):
        self.assertIn("AI실행", patch.PROMPT_NARROW_JS)
        self.assertIn("current * 0.7", patch.PROMPT_NARROW_JS)
        self.assertIn('field.style.setProperty("box-sizing", "border-box", "important")', patch.PROMPT_NARROW_JS)
        self.assertIn("prompt-menu-shift", patch.PROMPT_NARROW_JS)
        self.assertIn("padding-right: 24px", patch.PROMPT_NARROW_CSS)
        full = Path("/tmp/prompt-narrow.js")
        full.write_text(patch.PROMPT_NARROW_JS, encoding="utf-8")
        subprocess.run(["node", "--check", str(full)], check=True)
        scripted = patch.patch_answer("function openImageEditor(){ return 1; }\n")
        self.assertIn("/* prompt-narrow1 */", scripted)
        self.assertGreater(scripted.rindex("/* prompt-narrow1 */"), scripted.rindex("/* product-keyword1 */"))
        styled = patch.patch_css("/* image-narrow1 */\n")
        self.assertIn("/* prompt-narrow1 */", styled)
        self.assertGreater(styled.rindex("/* prompt-narrow1 */"), styled.rindex("/* image-narrow1 */"))
        help_html = patch.patch_help("<p>이미지바꾸기: 대표 이미지를 바꾸고, 순서를 정하고, 빼거나 넣습니다.</p>")
        self.assertIn("프롬프트 칸은 30% 짧습니다", help_html)
        self.assertIn("저장 메뉴는 조금 왼쪽에 있습니다", help_html)

    def test_image_role_zoom_splits_rep_and_detail(self):
        start = patch.IMAGE_ROLE_ZOOM_JS.index("/* image-role-pure-start */")
        end = patch.IMAGE_ROLE_ZOOM_JS.index("/* image-role-pure-end */")
        script = patch.IMAGE_ROLE_ZOOM_JS[start:end] + r"""
if (roleZoomStep(25, 1, 20, 120) !== 30) throw new Error("rep " + roleZoomStep(25, 1, 20, 120));
if (roleZoomStep(100, 1, 25, 200) !== 105) throw new Error("detail " + roleZoomStep(100, 1, 25, 200));
if (roleZoomStep(100, -1, 25, 200) !== 95) throw new Error("down " + roleZoomStep(100, -1, 25, 200));
if (roleZoomStep(25, 1, 20, 120) === 50) throw new Error("jumped 25");
"""
        path = Path("/tmp/image-role-zoom-test.js")
        path.write_text(script, encoding="utf-8")
        subprocess.run(["node", str(path)], check=True)
        full = Path("/tmp/image-role-zoom.js")
        full.write_text(patch.IMAGE_ROLE_ZOOM_JS, encoding="utf-8")
        subprocess.run(["node", "--check", str(full)], check=True)
        self.assertIn("repImageZoomBar", patch.IMAGE_ROLE_ZOOM_JS)
        self.assertIn("상세페이지", patch.IMAGE_ROLE_ZOOM_JS)
        self.assertIn("headerClose.remove()", patch.IMAGE_ROLE_ZOOM_JS)
        self.assertIn("stopImmediatePropagation", patch.IMAGE_ROLE_ZOOM_JS)
        self.assertIn("#03C75A", patch.IMAGE_ROLE_ZOOM_CSS)
        self.assertNotIn("100vw", patch.IMAGE_ROLE_ZOOM_CSS)
        self.assertIn("대표이미지", patch.IMAGE_ROLE_ZOOM_JS)
        scripted = patch.patch_answer("function openImageEditor(){ return 1; }\nfunction renderImageEditor(){ return 1; }\n")
        self.assertIn("/* image-role-zoom1 */", scripted)
        self.assertGreater(scripted.rindex("/* image-role-zoom1 */"), scripted.rindex("/* attribute-foot1 */"))
        styled = patch.patch_css("/* attribute-foot1 */\n#imageDialog { width: 90vw; }\n")
        self.assertIn("/* image-role-zoom1 */", styled)
        self.assertGreater(styled.rindex("/* image-role-zoom1 */"), styled.rindex("/* attribute-foot1 */"))
        self.assertGreater(styled.rindex("90vw"), styled.rindex("100vw") if "100vw" in styled else 0)
        help_html = patch.patch_help("<p>이미지바꾸기: 대표 이미지를 바꾸고, 순서를 정하고, 빼거나 넣습니다.</p>")
        self.assertIn("대표이미지 조절은 이미지 칸 위", help_html)
        self.assertIn("오른쪽 조절은 상세페이지 크기", help_html)
        self.assertIn("오른쪽 닫기는 없고", help_html)
        self.assertIn("저장은 네이버 초록색입니다", help_html)

    def test_naver_option_save_and_manual_ship(self):
        start = patch.NAVER_OPTION_SHIP_JS.index("/* naver-option-pure-start */")
        end = patch.NAVER_OPTION_SHIP_JS.index("/* naver-option-pure-end */")
        script = patch.NAVER_OPTION_SHIP_JS[start:end] + r"""
const marked = markRepresentative([{ id: "a" }, { id: "b" }]);
if (!marked[0].representative || marked[1].representative) throw new Error("rep " + JSON.stringify(marked));
const rows = optionListFromGroups(
  [{ name: "색상", values: ["화이트", "블랙"] }],
  [{ values: ["화이트"], price: 500, stock: 3, code: "W" }],
  9999,
  false
);
if (rows.length !== 2) throw new Error("len " + rows.length);
if (rows[0].price !== 500 || rows[0].stock !== 3 || rows[0].code !== "W") throw new Error("kept " + JSON.stringify(rows[0]));
if (rows[1].values[0] !== "블랙" || rows[1].price !== 0) throw new Error("new " + JSON.stringify(rows[1]));
if (shipAmountFromText("3,000") !== 3000) throw new Error("ship");
if (shipAmountFromText("") !== null) throw new Error("empty");
if (shipAmountFromText("-1") !== null) throw new Error("neg");
"""
        path = Path("/tmp/naver-option-ship-test.js")
        path.write_text(script, encoding="utf-8")
        subprocess.run(["node", str(path)], check=True)
        full = Path("/tmp/naver-option-ship.js")
        full.write_text(patch.NAVER_OPTION_SHIP_JS, encoding="utf-8")
        subprocess.run(["node", "--check", str(full)], check=True)
        self.assertIn("image-slot-delete", patch.NAVER_OPTION_SHIP_JS)
        self.assertIn("직접입력형", patch.NAVER_OPTION_SHIP_JS)
        self.assertIn("옵션번호", patch.NAVER_OPTION_SHIP_JS)
        self.assertIn("manual-ship-input", patch.NAVER_OPTION_SHIP_JS)
        self.assertIn("#03C75A", patch.NAVER_OPTION_SHIP_CSS)
        self.assertIn("#tagDialog .dialog-actions button[type=\"submit\"]", patch.NAVER_OPTION_SHIP_CSS)
        self.assertNotIn("100vw", patch.NAVER_OPTION_SHIP_CSS)
        scripted = patch.patch_answer("function renderImageEditor(){ return 1; }\nfunction renderOptionCombos(){ return 1; }\nfunction openOptionEditor(){ return 1; }\n")
        self.assertIn("/* naver-option-ship1 */", scripted)
        self.assertGreater(scripted.rindex("/* naver-option-ship1 */"), scripted.rindex("/* image-role-zoom1 */"))
        styled = patch.patch_css("/* image-role-zoom1 */\n#imageDialog { width: 90vw; }\n")
        self.assertIn("/* naver-option-ship1 */", styled)
        self.assertGreater(styled.rindex("90vw"), styled.rindex("100vw"))
        help_html = patch.patch_help("<p>이미지바꾸기: 대표 이미지를 바꾸고, 순서를 정하고, 빼거나 넣습니다.</p>")
        self.assertIn("첫 사진이 대표이미지", help_html)
        self.assertIn("이미지 삭제는 첫 화면", help_html)
        self.assertIn("배송비는 칸에 직접", help_html)
        self.assertIn("태그 저장은 네이버 초록색", help_html)
        self.assertIn("옵션 저장은 목록의 모든 줄을 저장합니다", help_html)
        self.assertIn("이미지 삭제는 목록 오른쪽에 보입니다", help_html)
        self.assertIn("배송권역과 제주추가", help_html)
        self.assertIn("상세페이지 크기는 5%씩", help_html)
        self.assertIn("상세페이지 닫기는 하나", help_html)
        self.assertIn("주소록은 고른 마켓", help_html)

    def test_option_combo_read_uses_every_row(self):
        source = """
function $(selector) { return document.querySelector(selector); }
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
function selectedComboRows() {
  return [...$("#optionComboTable tr")].filter((row) => row.querySelector("[data-combo-check]")?.checked);
}
"""
        patched = patch.patch_option_combo_read(source)
        self.assertNotIn('$("#optionComboTable tr")', patched)
        self.assertEqual(patched.count("/* option-combo-read1 */"), 2)
        self.assertIn('document.querySelectorAll("#optionComboTable tr")', patched)
        self.assertIn("/* option-combo-read1 */", patch.patch_answer(source))
        path = Path("/tmp/option-combo-read-test.js")
        path.write_text(patched, encoding="utf-8")
        subprocess.run(["node", "--check", str(path)], check=True)

    def test_image_delete_stays_visible_and_delivery_area_unlocks(self):
        self.assertIn("/* first-screen1 */", patch.FIRST_SCREEN_JS)
        self.assertIn("/* first-screen1 */", patch.FIRST_SCREEN_CSS)
        self.assertNotIn("100vw", patch.FIRST_SCREEN_CSS)
        self.assertIn("image-row-delete", patch.FIRST_SCREEN_CSS)
        self.assertIn("area2_extra_fee", patch.FIRST_SCREEN_JS)
        self.assertIn("deliveryAreaType", patch.FIRST_SCREEN_JS)
        styled = patch.patch_css("/* naver-option-ship1 */\n#imageDialog { width: 90vw; }\n")
        self.assertIn("/* first-screen1 */", styled)
        self.assertGreater(styled.rindex("90vw"), styled.rindex("100vw") if "100vw" in styled else 0)
        scripted = patch.patch_answer("function renderImageEditor(){ return 1; }\nfunction syncDeliveryFields(){ return 1; }\n")
        self.assertIn("/* first-screen1 */", scripted)
        self.assertGreater(scripted.rindex("/* first-screen1 */"), scripted.rindex("/* naver-option-ship1 */"))
        path = Path("/tmp/first-screen.js")
        path.write_text(patch.FIRST_SCREEN_JS, encoding="utf-8")
        subprocess.run(["node", "--check", str(path)], check=True)

    def test_detail_zoom_and_market_address(self):
        start = patch.DETAIL_MARKET_JS.index("/* detail-market-pure-start */")
        end = patch.DETAIL_MARKET_JS.index("/* detail-market-pure-end */")
        script = patch.DETAIL_MARKET_JS[start:end] + r"""
if (detailZoomScale(105) !== 1.05) throw new Error("zoom " + detailZoomScale(105));
if (detailZoomScale(103) !== 1.05) throw new Error("snap " + detailZoomScale(103));
if (detailZoomScale(20) !== 0.25) throw new Error("min " + detailZoomScale(20));
if (detailZoomScale(240) !== 2) throw new Error("max " + detailZoomScale(240));
const markets = [{ id: "wish" }, { id: "baram" }];
if (deliveryMarketChoice("", "baram", "wish", markets) !== "baram") throw new Error("tree");
if (deliveryMarketChoice("wish", "baram", "wish", markets) !== "wish") throw new Error("select");
if (deliveryMarketChoice("smartstore", "smartstore", "wish", markets) !== "wish") throw new Error("channel");
if (deliveryMarketChoice("", "", "", markets) !== "wish") throw new Error("first");
"""
        path = Path("/tmp/detail-market-pure.js")
        path.write_text(script, encoding="utf-8")
        subprocess.run(["node", str(path)], check=True)
        full = Path("/tmp/detail-market.js")
        full.write_text(patch.DETAIL_MARKET_JS, encoding="utf-8")
        subprocess.run(["node", "--check", str(full)], check=True)
        self.assertIn("/* detail-market1 */", patch.DETAIL_MARKET_JS)
        self.assertIn("/* detail-market1 */", patch.DETAIL_MARKET_CSS)
        self.assertNotIn("100vw", patch.DETAIL_MARKET_CSS)
        self.assertIn('bar.id !== "imageZoomBar"', patch.DETAIL_MARKET_JS)
        self.assertIn("/api/addresses", patch.DETAIL_MARKET_JS)
        self.assertIn("deliveryMarketChoice", patch.DETAIL_MARKET_JS)
        styled = patch.patch_css("/* first-screen1 */\n#imageDialog { width: 90vw; }\n")
        self.assertIn("/* detail-market1 */", styled)
        self.assertGreater(styled.rindex("/* detail-market1 */"), styled.rindex("/* first-screen1 */"))
        self.assertGreater(styled.rindex("90vw"), styled.rindex("100vw") if "100vw" in styled else 0)
        scripted = patch.patch_answer("function renderImageEditor(){ return 1; }\nfunction syncDeliveryFields(){ return 1; }\n")
        self.assertIn("/* detail-market1 */", scripted)
        self.assertGreater(scripted.rindex("/* detail-market1 */"), scripted.rindex("/* first-screen1 */"))


if __name__ == "__main__":
    unittest.main()
