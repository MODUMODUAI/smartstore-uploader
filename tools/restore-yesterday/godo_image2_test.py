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

    def test_screen_version_replaces_cached_query(self):
        html = """
        <span id="appVersion" class="app-version">v2026.10.28.42</span>
        <link rel="stylesheet" href="/static/styles.css?v=open-login1" />
        <script src="/static/app.js?v=open-login1"></script>
        </body>
        """
        updated = patch.patch_html(html)
        self.assertIn(f"/static/app.js?v={patch.SCREEN_VERSION}", updated)
        self.assertIn(f"/static/styles.css?v={patch.SCREEN_VERSION}", updated)
        self.assertIn(f">v{patch.SCREEN_VERSION}<", updated)
        self.assertIn("/* screen-build1 */", updated)
        self.assertIn(f'const version = "{patch.SCREEN_VERSION}"', updated)
        self.assertNotIn("open-login1", updated)
        self.assertNotIn("2026.10.28.42", updated)
        self.assertEqual(patch.patch_html(updated), updated)
        js = 'const version = "2026.10.28.42";\nconst again = "2026.10.28.43";\n'
        replaced = patch._replace_old_versions(js)
        self.assertNotIn("2026.10.28.42", replaced)
        self.assertNotIn("2026.10.28.43", replaced)
        self.assertEqual(replaced.count(patch.SCREEN_VERSION), 2)

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


class GodoImage3Test(unittest.TestCase):
    def setUp(self):
        self.ns = {
            "extract_product": lambda html, page_url="": {
                "gallery_images": [],
                "detail_images": [],
                "images": [],
                "warnings": ["이미지를 찾지 못했습니다"],
            }
        }
        for snippet in (
            patch.GODO_SCRAPER_PY,
            patch.GODO_IMAGE1_SCRAPER_PY,
            patch.GODO_IMAGE2_SCRAPER_PY,
            patch.GODO_IMAGE3_SCRAPER_PY,
        ):
            exec(compile(snippet, "<godo>", "exec"), self.ns)
        self.catalog = {
            "_godomall_products": lambda shop_url, category=None, *args, **kwargs: {"items": []},
            "_godo_known_images": {},
            "_base": lambda url: "http://murray.co.kr",
            "_godo_all_cates": lambda url: [],
            "httpx": None,
            "PAGE_HEADERS": {},
        }
        exec(compile(patch.GODO_IMAGE3_CATALOG_PY, "<catalog>", "exec"), self.catalog)

    def test_detail_slot_is_not_the_list_image(self):
        html = """
        <img src="https://cdn.example/goods/1000000195/image/detail/1000000195_detail_092.jpg">
        <img src="https://cdn.example/goods/1000000195/image/magnify/1000000195_magnify_078.jpg">
        <img src="http://gi.esmplus.com/murraymall/detail/long.jpg">
        """
        data = self.ns["extract_product"](html, "http://murray.co.kr/goods/goods_view.php?goodsNo=1000000195")
        self.assertIn("/image/magnify/", data["gallery_images"][0])
        self.assertFalse(any("/image/detail/" in url for url in data["gallery_images"]))
        self.assertTrue(any("/image/detail/" in url for url in data["detail_images"]))
        self.assertTrue(any("esmplus.com" in url for url in data["detail_images"]))
        self.assertFalse(any("esmplus.com" in url for url in data["gallery_images"]))

    def test_main_photo_leads_the_list(self):
        html = """
        <img src="https://cdn.example/goods/1000000195/image/detail/1000000195_detail_092.jpg">
        <img src="https://cdn.example/goods/1000000195/image/main/1000000195_main_01.jpg">
        <img src="http://gi.esmplus.com/murraymall/detail/long.jpg">
        """
        data = self.ns["extract_product"](html, "http://murray.co.kr/goods/goods_view.php?goodsNo=1000000195")
        self.assertIn("/image/main/", data["gallery_images"][0])
        self.assertEqual(data["images"][0], data["gallery_images"][0])
        self.assertNotIn("/image/detail/", data["gallery_images"][0])

    def test_moderate_strip_moves_behind_square_photo(self):
        product = {
            "source_url": "http://murray.co.kr/goods/goods_view.php?goodsNo=1000000195",
            "images": [
                {
                    "source_url": "http://gi.esmplus.com/murraymall/detail/long.jpg",
                    "kind": "gallery",
                    "representative": True,
                    "width": 800,
                    "height": 1224,
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
        self.assertIn("/image/main/", product["images"][0]["source_url"])
        self.assertTrue(product["images"][0]["representative"])
        self.assertEqual(product["images"][0]["kind"], "gallery")
        self.assertEqual(product["images"][1]["kind"], "detail")
        self.assertFalse(product["images"][1]["representative"])
        self.assertFalse(self.ns["godo_fix_saved_images"](product))

    def test_catalog_replaces_description_with_list_photo(self):
        html = Path("/tmp/murray-list.html").read_text("utf-8", "replace") if Path("/tmp/murray-list.html").is_file() else ""
        if html:
            mains = self.catalog["_godo3_mains_from_html"](html)
            self.assertIn("/image/main/", mains["1000000195"])
        items = [
            {"product_no": "1000000195", "image": "http://gi.esmplus.com/murraymall/detail/long.jpg"},
            {"product_no": "1000000555", "image": "https://cdn.example/goods/1000000555/image/detail/1000000555_detail_054.jpg"},
            {"product_no": "1000000802", "image": "https://cdn.example/goods/1000000802/image/main/1000000802_main_028.jpg"},
        ]
        mains = {
            "1000000195": "https://cdn.example/goods/1000000195/image/main/1000000195_main_01.jpg",
            "1000000555": "https://cdn.example/goods/1000000555/image/main/1000000555_main_014.jpg",
            "1000000802": "https://cdn.example/goods/1000000802/image/main/1000000802_main_028.jpg",
        }
        self.catalog["_godo3_apply_items"](items, mains)
        self.assertIn("/image/main/", items[0]["image"])
        self.assertIn("/image/main/", items[1]["image"])
        self.assertIn("/image/main/1000000802", items[2]["image"])
        self.assertEqual(self.catalog["_godo_known_images"]["1000000195"], items[0]["image"])

    def test_relative_list_photo_is_kept(self):
        html = '<img src="/goods/1000000195/image/main/1000000195_main_01.jpg">'
        mains = self.catalog["_godo3_mains_from_html"](html, "http://murray.co.kr")
        self.assertEqual(
            mains["1000000195"],
            "http://murray.co.kr/goods/1000000195/image/main/1000000195_main_01.jpg",
        )

    def test_saved_detail_page_is_replaced_by_cached_list_photo(self):
        self.ns["_godo3_cached_list"] = lambda number, page_url: (
            "https://cdn.example/goods/1000000195/image/main/1000000195_main_01.jpg"
        )
        product = {
            "source_url": "http://murray.co.kr/goods/goods_view.php?goodsNo=1000000195",
            "images": [
                {
                    "source_url": "http://gi.esmplus.com/murraymall/detail/long.jpg",
                    "kind": "gallery",
                    "representative": True,
                    "width": 800,
                    "height": 1224,
                },
                {
                    "source_url": "https://cdn.example/goods/1000000195/image/detail/1000000195_detail_092.jpg",
                    "kind": "gallery",
                    "representative": False,
                    "width": 500,
                    "height": 500,
                },
            ],
        }
        self.assertTrue(self.ns["godo_fix_saved_images"](product))
        self.assertIn("/image/main/", product["images"][0]["source_url"])
        self.assertTrue(product["images"][0]["representative"])
        self.assertEqual(product["images"][0]["kind"], "gallery")
        self.assertTrue(all(image["kind"] == "detail" for image in product["images"][1:]))
        self.assertFalse(any(image["representative"] for image in product["images"][1:]))
        self.assertFalse(self.ns["godo_fix_saved_images"](product))

    def test_real_goods_page_keeps_detail_slot_out_of_the_list(self):
        html_path = Path("/tmp/murray-goods/1000000195.html")
        if not html_path.is_file():
            self.skipTest("murray goods fixture not downloaded")
        html = html_path.read_text("utf-8", "replace")
        data = self.ns["extract_product"](html, "http://murray.co.kr/goods/goods_view.php?goodsNo=1000000195")
        self.assertIn("/image/magnify/", data["gallery_images"][0])
        self.assertNotIn("/thumb/", data["gallery_images"][0])
        self.assertFalse(any("/image/detail/" in url for url in data["gallery_images"]))
        self.assertTrue(any("/image/detail/" in url for url in data["detail_images"]))
        self.assertFalse(any("esmplus.com" in url for url in data["gallery_images"]))


class _Resp:
    def __init__(self, text, status=200):
        self.text = text
        self.status_code = status


class _Client:
    def __init__(self, get):
        self._get = get

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url, params=None):
        return self._get(url, params or {})


class GodoImage4Test(unittest.TestCase):
    PAGE1 = """
    <a href="./goods_list.php?page=2&amp;cateCd=008">2</a>
    <img src="/goods/1000000195/image/main/1000000195_main_01.jpg">
    <img src="https://godomall-storage.cdn-nhncommerce.com/shop/goods/1000000195/image/main/1000000195_main_01.jpg">
    """
    PAGE2 = """
    <img src="https://godomall-storage.cdn-nhncommerce.com/shop/goods/1000000555/image/main/1000000555_main_014.jpg">
    """
    SEARCH = """
    <img src="https://godomall-storage.cdn-nhncommerce.com/shop/goods/1000000999/image/main/1000000999_main_01.jpg">
    """
    MAIN = "https://godomall-storage.cdn-nhncommerce.com/shop/goods/1000000195/image/main/1000000195_main_01.jpg"

    def setUp(self):
        self.ns = {
            "extract_product": lambda html, page_url="": {
                "gallery_images": [],
                "detail_images": [],
                "images": [],
                "warnings": ["이미지를 찾지 못했습니다"],
            }
        }
        for snippet in (
            patch.GODO_SCRAPER_PY,
            patch.GODO_IMAGE1_SCRAPER_PY,
            patch.GODO_IMAGE2_SCRAPER_PY,
            patch.GODO_IMAGE3_SCRAPER_PY,
            patch.GODO_IMAGE4_SCRAPER_PY,
        ):
            exec(compile(snippet, "<godo>", "exec"), self.ns)
        self.ns["_godo4_lookup"] = lambda page_url, number, name="": ""
        self.catalog = {
            "_godomall_products": lambda shop_url, category=None, *args, **kwargs: {"items": []},
            "_godo_known_images": {},
            "_base": lambda url: "http://murray.co.kr",
            "_godo_all_cates": lambda url: ["008", "021"],
            "httpx": None,
            "PAGE_HEADERS": {},
        }
        exec(compile(patch.GODO_IMAGE3_CATALOG_PY, "<catalog3>", "exec"), self.catalog)
        exec(compile(patch.GODO_IMAGE4_CATALOG_PY, "<catalog4>", "exec"), self.catalog)

    def test_real_goods_page_uses_list_main(self):
        html_path = Path("/tmp/murray-goods/1000000195.html")
        if not html_path.is_file():
            self.skipTest("murray goods fixture not downloaded")
        self.ns["_godo4_lookup"] = lambda page_url, number, name="": self.MAIN
        html = html_path.read_text("utf-8", "replace")
        data = self.ns["extract_product"](html, "http://murray.co.kr/goods/goods_view.php?goodsNo=1000000195")
        self.assertIn("/image/main/", data["gallery_images"][0])
        self.assertFalse(any("/image/detail/" in url for url in data["gallery_images"]))
        self.assertFalse(any("/image/magnify/" in url for url in data["gallery_images"]))
        self.assertTrue(data["images"][0]["representative"])
        self.assertEqual(data["images"][0]["kind"], "gallery")

    def test_saved_magnify_is_replaced_by_list_main(self):
        self.ns["_godo4_lookup"] = lambda page_url, number, name="": self.MAIN
        product = {
            "source_url": "http://murray.co.kr/goods/goods_view.php?goodsNo=1000000195",
            "name": "발열파티션",
            "images": [
                {
                    "source_url": "https://cdn.example/goods/1000000195/image/magnify/1000000195_magnify_078.jpg",
                    "kind": "gallery",
                    "representative": True,
                    "width": 500,
                    "height": 500,
                },
                {
                    "source_url": "https://cdn.example/goods/1000000195/image/detail/1000000195_detail_092.jpg",
                    "kind": "gallery",
                    "representative": False,
                    "width": 500,
                    "height": 500,
                },
                {
                    "source_url": "http://gi.esmplus.com/murraymall/detail/long.jpg",
                    "kind": "gallery",
                    "representative": False,
                    "width": 800,
                    "height": 1224,
                },
            ],
        }
        self.assertTrue(self.ns["godo_fix_saved_images"](product))
        self.assertIn("/image/main/", product["images"][0]["source_url"])
        self.assertTrue(product["images"][0]["representative"])
        self.assertEqual(product["images"][0]["kind"], "gallery")
        self.assertTrue(all(image["kind"] == "detail" for image in product["images"][1:]))
        self.assertFalse(any(image["representative"] for image in product["images"][1:]))
        self.assertFalse(self.ns["godo_fix_saved_images"](product))

    def test_detail_slot_without_list_photo_is_not_representative(self):
        product = {
            "source_url": "http://murray.co.kr/goods/goods_view.php?goodsNo=1000000195",
            "images": [
                {
                    "source_url": "https://cdn.example/goods/1000000195/image/detail/1000000195_detail_092.jpg",
                    "kind": "gallery",
                    "representative": True,
                    "width": 500,
                    "height": 500,
                },
                {
                    "source_url": "http://gi.esmplus.com/murraymall/detail/long.jpg",
                    "kind": "gallery",
                    "representative": False,
                    "width": 800,
                    "height": 1224,
                },
            ],
        }
        self.assertTrue(self.ns["godo_fix_saved_images"](product))
        self.assertFalse(any(image["representative"] for image in product["images"]))
        self.assertTrue(all(image["kind"] == "detail" for image in product["images"]))
        self.assertFalse(self.ns["godo_fix_saved_images"](product))

    def _install_client(self, get):
        self.catalog["httpx"] = type("httpx", (), {"Client": lambda *args, **kwargs: _Client(get)})

    def test_catalog_replaces_detail_page_with_list_main(self):
        pages = {"1": self.PAGE1, "2": self.PAGE2}

        def get(url, params):
            if "goods_search.php" in url:
                if params.get("keyword") == "발열파티션":
                    return _Resp(self.SEARCH)
                return _Resp("")
            page = str(params.get("page") or 1)
            if page in pages:
                return _Resp(pages[page])
            return _Resp("", 404)

        self._install_client(get)
        kept = "https://cdn.example/goods/1000000802/image/main/1000000802_main_028.jpg"
        items = [
            {"product_no": "1000000195", "image": "https://cdn.example/goods/1000000195/image/detail/1000000195_detail_092.jpg"},
            {"product_no": "1000000555", "image": "https://cdn.example/goods/1000000555/image/magnify/1000000555_magnify_06.jpg"},
            {"product_no": "1000000802", "image": kept},
            {"product_no": "1000000999", "name": "발열파티션", "image": "http://gi.esmplus.com/murraymall/detail/long.jpg"},
        ]
        self.catalog["_godomall_products_before_image3"] = lambda *args, **kwargs: {"items": items}
        data = self.catalog["_godomall_products"]("http://murray.co.kr", "008")
        by_no = {item["product_no"]: item["image"] for item in data["items"]}
        self.assertIn("/image/main/1000000195_main_01.jpg", by_no["1000000195"])
        self.assertTrue(by_no["1000000195"].startswith("https://godomall-storage"))
        self.assertIn("/image/main/1000000555", by_no["1000000555"])
        self.assertEqual(by_no["1000000802"], kept)
        self.assertIn("/image/main/1000000999", by_no["1000000999"])

    def test_shop_origin_and_relative_mains_are_dropped(self):
        html = """
        <img src="/goods/1000000195/image/main/1000000195_main_01.jpg">
        <img src="http://murray.co.kr/goods/1000000195/image/main/1000000195_main_01.jpg">
        """
        mains = self.catalog["_godo4_mains_from_html"](html, "http://murray.co.kr")
        self.assertNotIn("1000000195", mains)
        both = html + '<img src="https://godomall-storage.cdn-nhncommerce.com/shop/goods/1000000195/image/main/1000000195_main_01.jpg">'
        mains = self.catalog["_godo4_mains_from_html"](both, "http://murray.co.kr")
        self.assertTrue(mains["1000000195"].startswith("https://godomall-storage"))

    def test_partial_list_crawl_is_not_cached(self):
        calls = {"n": 0}

        def get(url, params):
            calls["n"] += 1
            page = int(params.get("page") or 1)
            if page == 2 and calls["n"] <= 2:
                raise RuntimeError("list page failed")
            if page == 1:
                return _Resp(self.PAGE1)
            if page == 2:
                return _Resp(self.PAGE2)
            return _Resp("", 404)

        self._install_client(get)
        first = self.catalog["_godo4_fetch_mains"]("http://murray.co.kr", "008")
        self.assertIn("1000000195", first)
        self.assertNotIn("1000000555", first)
        self.assertNotIn(("http://murray.co.kr", "008"), self.catalog["_godo4_main_cache"])
        second = self.catalog["_godo4_fetch_mains"]("http://murray.co.kr", "008")
        self.assertIn("1000000555", second)
        self.assertIn(("http://murray.co.kr", "008"), self.catalog["_godo4_main_cache"])

    def test_screen_script_uses_only_main_and_list(self):
        self.assertIn("/* godo-image4 */", patch.GODO_IMAGE4_JS)
        self.assertIn("(main|list)", patch.GODO_IMAGE4_JS)
        rank_js = patch.GODO_IMAGE4_JS.split("function godoListRank", 1)[1].split("function godoApplyRepresentative", 1)[0]
        self.assertNotIn("magnify", rank_js)
        self.assertIn(patch.GODO_IMAGE4_MARKER, patch.frozen_fix_plan()["app.scraper"][-1][0])
        self.assertIn(patch.GODO_IMAGE4_MARKER, patch.frozen_fix_plan()["app.shop_catalog"][-1][0])
        self.assertEqual(patch.SCREEN_VERSION, "2026.10.28.69")


if __name__ == "__main__":
    unittest.main()
