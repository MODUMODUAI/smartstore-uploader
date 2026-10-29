"""Naver tag dictionary fill and leaf-category search tags."""

import unittest

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
        self.assertEqual(patch.SCREEN_VERSION, "2026.10.28.51")


if __name__ == "__main__":
    unittest.main()
