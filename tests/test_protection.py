import unittest

from token_forge.protection import extract_protected_literals


class ProtectionTests(unittest.TestCase):
    def test_extracts_literal_evidence_without_rewriting(self):
        text = (
            "Release v2.4.1 costs 19.95 USD. See https://example.com/a?q=1. "
            "Run `python -m tool --limit 8` and keep error E_CONN_42."
        )
        protected = extract_protected_literals(text)
        for value in (
            "v2.4.1",
            "19.95",
            "https://example.com/a?q=1",
            "python -m tool --limit 8",
            "E_CONN_42",
        ):
            self.assertIn(value, protected)


if __name__ == "__main__":
    unittest.main()

