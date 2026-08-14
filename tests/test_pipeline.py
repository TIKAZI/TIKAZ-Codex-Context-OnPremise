import tempfile
import unittest
from pathlib import Path

from token_forge.pipeline import build_text_pack


class PipelineTests(unittest.TestCase):
    def test_selects_relevant_text_and_preserves_literals(self):
        source = """# Release
Version v2.4.1 must ship on 2026-09-01.

# Unrelated
Decorative copy repeated here.

# Database migration
Run `python migrate.py --target v2.4.1` after backup.

# Unrelated
Decorative copy repeated here.
"""
        result = build_text_pack(source, "prepare database migration", budget_tokens=40)
        self.assertIn("python migrate.py --target v2.4.1", result.text)
        self.assertIn("v2.4.1", result.protected_literals)
        self.assertEqual(result.protected_recall, 1.0)
        self.assertLessEqual(result.final_tokens, 40)
        self.assertLess(result.final_tokens, result.input_tokens)

    def test_small_dense_input_passes_through(self):
        source = "Error E_CONN_42 at https://example.com/log"
        result = build_text_pack(source, "diagnose", budget_tokens=100)
        self.assertEqual(result.mode, "pass-through")
        self.assertEqual(result.text, source)

    def test_writes_a_recoverable_pack(self):
        source = "# Evidence\nVersion v1.2.3 is required.\n\n# Noise\nIgnore decoration."
        with tempfile.TemporaryDirectory() as temp:
            result = build_text_pack(source, "required version", 60, output_dir=Path(temp))
            self.assertTrue((Path(temp) / "context.md").exists())
            self.assertTrue((Path(temp) / "ledger.json").exists())
            self.assertEqual(result.protected_recall, 1.0)

    def test_persistent_cache_hits_only_for_identical_effective_config(self):
        source = "# Evidence\nUse v4.0.1.\n\n# Noise\nDecorative filler for removal."
        with tempfile.TemporaryDirectory() as temp:
            cache_dir = Path(temp) / "cache"
            first = build_text_pack(
                source, "release evidence", 30, cache_dir=cache_dir,
                adapter="text-pack", adapter_version="1",
            )
            second = build_text_pack(
                source, "release evidence", 30, cache_dir=cache_dir,
                adapter="text-pack", adapter_version="1",
            )
            changed_budget = build_text_pack(
                source, "release evidence", 31, cache_dir=cache_dir,
                adapter="text-pack", adapter_version="1",
            )

            self.assertFalse(first.cache_hit)
            self.assertTrue(second.cache_hit)
            self.assertEqual(first.cache_key, second.cache_key)
            self.assertFalse(changed_budget.cache_hit)
            self.assertNotEqual(first.cache_key, changed_budget.cache_key)

    def test_high_risk_material_passes_through_without_reduction(self):
        source = "command,value\n`Remove-Item`,250000.00\n" * 20
        result = build_text_pack(source, "summarize values", 20, safety_class="table")
        self.assertEqual(result.mode, "safety-pass-through")
        self.assertEqual(result.text, source)
        self.assertEqual(result.reduction_ratio, 0.0)


if __name__ == "__main__":
    unittest.main()
