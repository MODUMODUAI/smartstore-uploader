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
        self.assertEqual(patch.SCREEN_VERSION, "2026.10.28.58")

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
        help_html = patch.patch_help("<p>직접 넣거나 AI 채우기로 만듭니다.</p>")
        self.assertIn("태그사전 후보", help_html)


if __name__ == "__main__":
    unittest.main()
