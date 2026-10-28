"""Godomall representative image is the goods photo, not the long detail page."""

import unittest
from pathlib import Path

import patch_inquiry_links as patch


class GodoImage2Test(unittest.TestCase):
    def setUp(self):
        self.ns = {
            "extract_product": lambda html, page_url="": {
                "gallery_images": [
                    "http://gi.esmplus.com/murraymall/detail/long.jpg",
                    "https://cdn.example/goods/1000000195/image/magnify/1000000195_magnify_078.jpg",
                ],
                "detail_images": [],
                "images": [
                    {
                        "source_url": "http://gi.esmplus.com/murraymall/detail/long.jpg",
                        "kind": "gallery",
                        "representative": True,
                        "width": 800,
                        "height": 6087,
                    },
                    {
                        "source_url": "https://cdn.example/goods/1000000195/image/magnify/1000000195_magnify_078.jpg",
                        "kind": "gallery",
                        "representative": False,
                        "width": 500,
                        "height": 500,
                    },
                ],
                "warnings": ["이미지를 찾지 못했습니다"],
            }
        }
        code = compile(patch.GODO_SCRAPER_PY, "<godo-login1>", "exec")
        exec(code, self.ns)
        code = compile(patch.GODO_IMAGE2_SCRAPER_PY, "<godo-image2>", "exec")
        exec(code, self.ns)

    def test_snippets_compile(self):
        compile(patch.GODO_IMAGE2_SCRAPER_PY, "<scraper>", "exec")
        compile(patch.GODO_IMAGE2_SERVICE_PY, "<service>", "exec")
        compile(patch.GODO_IMAGE2_CATALOG_PY, "<catalog>", "exec")
        compile(patch.GODO_IMAGE2_JS, "<js>", "exec") if False else None
        self.assertIn("function godoApplyRepresentative", patch.GODO_IMAGE2_JS)

    def test_detail_page_is_not_representative(self):
        html = """
        <img src="https://cdn.example/goods/1000000195/image/detail/thumb/1000000195_detail_092.jpg">
        <img src="https://cdn.example/goods/1000000195/image/detail/1000000195_detail_092.jpg">
        <img src="http://gi.esmplus.com/murraymall/detail/long.jpg">
        <img src="https://cdn.example/goods/1000000195/image/magnify/1000000195_magnify_078.jpg">
        <a href="https://www.pinterest.com/pin/create/button/?media=https://cdn.example/goods/1000000195/image/main/1000000195_main_01.jpg">pin</a>
        """
        data = self.ns["extract_product"](html, "http://murray.co.kr/goods/goods_view.php?goodsNo=1000000195")
        self.assertEqual(
            data["gallery_images"][0],
            "https://cdn.example/goods/1000000195/image/magnify/1000000195_magnify_078.jpg",
        )
        self.assertNotIn("long.jpg", data["gallery_images"][0])
        self.assertTrue(any("long.jpg" in url for url in data["detail_images"]))
        self.assertFalse(any("/thumb/" in url for url in data["gallery_images"]))
        self.assertFalse(any("pinterest" in url for url in data["gallery_images"]))
        images = data["images"]
        rep = [image for image in images if isinstance(image, dict) and image.get("representative")]
        self.assertEqual(len(rep), 1)
        self.assertIn("/image/magnify/", rep[0]["source_url"])
        self.assertEqual(rep[0]["kind"], "gallery")
        detail = next(image for image in images if "long.jpg" in image["source_url"])
        self.assertEqual(detail["kind"], "detail")
        self.assertFalse(detail["representative"])
        self.assertEqual(data["warnings"], [])

    def test_saved_product_flag_moves_to_photo(self):
        product = {
            "source_url": "http://murray.co.kr/goods/goods_view.php?goodsNo=1000000195",
            "images": [
                {
                    "source_url": "http://gi.esmplus.com/murraymall/detail/long.jpg",
                    "kind": "gallery",
                    "representative": True,
                    "width": 800,
                    "height": 6087,
                },
                {
                    "source_url": "https://cdn.example/goods/1000000195/image/main/1000000195_main_01.jpg",
                    "kind": "detail",
                    "representative": False,
                    "width": 400,
                    "height": 400,
                },
            ],
        }
        self.assertTrue(self.ns["godo_fix_saved_images"](product))
        self.assertFalse(product["images"][0]["representative"])
        self.assertEqual(product["images"][0]["kind"], "detail")
        self.assertTrue(product["images"][1]["representative"])
        self.assertEqual(product["images"][1]["kind"], "gallery")
        self.assertFalse(self.ns["godo_fix_saved_images"](product))

    def test_square_fallback_when_photo_url_is_missing(self):
        product = {
            "source_url": "http://murray.co.kr/goods/goods_view.php?goodsNo=1000000195",
            "images": [
                {"file": "long.jpg", "kind": "gallery", "representative": True, "width": 800, "height": 6087},
                {"file": "photo.jpg", "kind": "gallery", "representative": False, "width": 500, "height": 500},
            ],
        }
        self.assertTrue(self.ns["godo_fix_saved_images"](product))
        self.assertFalse(product["images"][0]["representative"])
        self.assertEqual(product["images"][0]["kind"], "detail")
        self.assertTrue(product["images"][1]["representative"])

    def test_real_murray_page_uses_goods_photo(self):
        html_path = Path("/tmp/murray.html")
        if not html_path.is_file():
            self.skipTest("murray fixture not downloaded")
        html = html_path.read_text("utf-8", "replace")
        data = self.ns["extract_product"](html, "http://murray.co.kr/goods/goods_view.php?goodsNo=1000000195")
        self.assertTrue(data["gallery_images"])
        self.assertIn("/goods/1000000195/image/", data["gallery_images"][0])
        self.assertNotIn("/thumb/", data["gallery_images"][0])
        self.assertTrue(any("esmplus.com" in url for url in data["detail_images"]))
        self.assertFalse(any("esmplus.com" in url for url in data["gallery_images"]))


if __name__ == "__main__":
    unittest.main()
