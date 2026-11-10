"""A zipped master keeps this PC's screen and supplier/product data."""

import tempfile
import unittest
from pathlib import Path

import patch_inquiry_links as patch


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class MasterSameScreenTest(unittest.TestCase):
    def test_launcher_does_not_swap_screen_or_data(self):
        text = Path(patch.__file__).with_name("open-yesterday.vbs").read_text(encoding="utf-8")
        for banned in (
            "RestoreYesterday",
            "ConsiderKnownData",
            "robocopy",
            "bak-20261027",
            "MODUMODU-master-oneshot",
        ):
            self.assertNotIn(banned, text)

    def test_other_master_matches_this_pc_and_seller_stays(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "launcher.py", "print('master')\n")
            _write(root / "version.txt", "2026.11.06.28\n")
            _write(root / "app" / "static" / "app.js", "window.SCREEN='this-pc'\n")
            _write(root / "app" / "static" / "index.html", "<p>this-pc</p>\n")
            _write(root / "app" / "static" / "styles.css", ".screen{color:#111}\n")
            _write(root / "app" / "static" / "app.js.bak-20261027-161704", "window.SCREEN='october'\n")
            _write(root / "data" / "wholesalers.json", '{"name":"이 PC 공급처"}\n')
            _write(root / "data" / "products" / "registered.json", '{"name":"등록상품"}\n')
            _write(root / "data" / "launcher.log", "keep-local\n")

            master = root / "배포" / "MODUMODU-마스터"
            _write(master / "launcher.py", "print('old')\n")
            _write(master / "version.txt", "2026.11.06.28\n")
            _write(master / "edition.txt", "test\n")
            _write(master / "app" / "static" / "app.js", "window.SCREEN='sent'\n")
            _write(master / "app" / "static" / "index.html", "<p>sent</p>\n")
            _write(master / "app" / "static" / "styles.css", ".screen{color:#999}\n")
            _write(master / "_internal" / "app" / "static" / "app.js", "window.SCREEN='frozen'\n")
            _write(master / "_internal" / "app" / "static" / "index.html", "<p>frozen</p>\n")
            _write(master / "_internal" / "app" / "static" / "styles.css", ".screen{color:#eee}\n")
            _write(master / "_internal" / "app" / "static" / "styles.css.bak-20261027-164205", "old\n")
            _write(master / "data" / "wholesalers.json", '{"name":"다른 공급처"}\n')
            _write(master / "data" / "products" / "old.json", '{"name":"예전상품"}\n')
            _write(master / "어제오후9시.vbs", "RestoreYesterday\n")

            seller = root / "배포" / "MODUMODU-셀러용"
            _write(seller / "app" / "static" / "index.html", "<p>seller</p>\n")
            _write(seller / "app" / "static" / "app.js", "window.SCREEN='seller'\n")
            _write(seller / "data" / "wholesalers.json", '{"name":"셀러"}\n')

            self.assertTrue(patch.mirror_master_copies(root))

            for static in (
                master / "app" / "static",
                master / "_internal" / "app" / "static",
            ):
                self.assertEqual((static / "app.js").read_text(encoding="utf-8"), "window.SCREEN='this-pc'\n")
                self.assertEqual((static / "index.html").read_text(encoding="utf-8"), "<p>this-pc</p>\n")
                self.assertFalse(list(static.glob("*.bak-20261027*")))
            self.assertFalse((root / "app" / "static" / "app.js.bak-20261027-161704").exists())
            self.assertEqual(
                (master / "data" / "wholesalers.json").read_text(encoding="utf-8"),
                '{"name":"이 PC 공급처"}\n',
            )
            self.assertEqual(
                (master / "data" / "products" / "registered.json").read_text(encoding="utf-8"),
                '{"name":"등록상품"}\n',
            )
            self.assertFalse((master / "data" / "products" / "old.json").exists())
            self.assertFalse((master / "edition.txt").exists())
            self.assertEqual((master / "version.txt").read_text(encoding="utf-8"), "2026.11.06.28\n")
            self.assertNotIn("RestoreYesterday", (master / "어제오후9시.vbs").read_text(encoding="utf-8"))
            self.assertEqual((seller / "app" / "static" / "app.js").read_text(encoding="utf-8"), "window.SCREEN='seller'\n")
            self.assertEqual((seller / "data" / "wholesalers.json").read_text(encoding="utf-8"), '{"name":"셀러"}\n')
            self.assertEqual((root / "data" / "launcher.log").read_text(encoding="utf-8"), "keep-local\n")
            self.assertFalse((master / "data" / "launcher.log").exists())

    def test_empty_pc_data_does_not_wipe_a_master_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "app" / "static" / "app.js", "same\n")
            _write(root / "app" / "static" / "index.html", "<p></p>\n")
            master = root / "배포" / "모두모두AI-마스터"
            _write(master / "app" / "static" / "index.html", "<p></p>\n")
            _write(master / "data" / "products" / "keep.json", "{}\n")
            patch.mirror_master_copies(root)
            self.assertTrue((master / "data" / "products" / "keep.json").is_file())


if __name__ == "__main__":
    unittest.main()
