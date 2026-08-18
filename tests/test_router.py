import unittest

from token_forge.router import profile_source


class RouterTests(unittest.TestCase):
    def test_routes_supported_source_families(self):
        self.assertEqual(profile_source("notes.md").family, "text")
        self.assertEqual(profile_source("report.pdf").family, "document")
        self.assertEqual(profile_source("lecture.mp4").family, "media")
        self.assertEqual(profile_source("main.py").family, "code")

    def test_code_is_not_eligible_for_learned_compression(self):
        profile = profile_source("main.py")
        self.assertFalse(profile.learned_compression_allowed)
        self.assertEqual(profile.fallback, "source")

    def test_csv_routes_as_table_not_free_text(self):
        profile = profile_source("financial-evidence.csv")
        self.assertEqual(profile.family, "table")
        self.assertEqual(profile.route, "table-safe")
        self.assertFalse(profile.learned_compression_allowed)

    def test_local_html_routes_to_web_extraction_not_code(self):
        profile = profile_source("saved-article.html")
        self.assertEqual(profile.family, "web")
        self.assertEqual(profile.route, "extract")
        self.assertEqual(profile.adapter_candidates[:2], ("defuddle", "markitdown"))


if __name__ == "__main__":
    unittest.main()
