import tempfile
import unittest
from pathlib import Path

from token_forge.pipeline import build_text_pack


class PipelineTests(unittest.TestCase):
    def test_text_uses_minimum_fact_cover_instead_of_every_repeated_fact_block(self):
        source = """# Release evidence
Deploy v3.4.5 after database backup.

# Repeated version note
The decorative launch essay repeats v3.4.5 but has no task evidence.

# Verification
Confirm schema version v3.4.5 and record VERIFY_ANCHOR.

# Decoration
This paragraph is unrelated visual copy for a campaign page.
"""
        result = build_text_pack(
            source,
            "database deployment verification",
            65,
            required_literals=("v3.4.5", "VERIFY_ANCHOR"),
        )
        self.assertEqual(result.mode, "selected")
        self.assertIn("Release evidence", result.text)
        self.assertIn("VERIFY_ANCHOR", result.text)
        self.assertNotIn("decorative launch essay", result.text)
        self.assertEqual(result.protected_recall, 1.0)

    def test_python_code_uses_exact_ast_dependency_slice_for_large_source(self):
        filler = "\n\n".join(
            f"def unrelated_{index}(value):\n    return value.upper()"
            for index in range(80)
        )
        source = f'''import json

API_URL = "https://api.example.com/v1"
RELEASE = "v8.1.0"
ERROR_CODE = "DEPLOY_ERR_81"

def deploy(client):
    response = client.post(API_URL, json={{"release": RELEASE}})
    if response.status_code != 200:
        raise RuntimeError(f"{{ERROR_CODE}}: {{response.text}}")
    return json.loads(response.text)

{filler}
'''
        result = build_text_pack(
            source,
            "review the deployment code",
            180,
            safety_class="code",
            required_literals=("https://api.example.com/v1", "v8.1.0", "DEPLOY_ERR_81"),
        )
        self.assertEqual(result.mode, "code-sliced")
        self.assertIn("def deploy", result.text)
        self.assertIn("API_URL", result.text)
        self.assertNotIn("unrelated_79", result.text)
        compile(result.text, "<slice>", "exec")
        self.assertGreater(result.reduction_ratio, 0.70)
        self.assertTrue(result.evidence["syntax_valid"])

    def test_python_slice_preserves_decorators_and_their_dependency(self):
        filler = "\n\n".join(
            f"def filler_{index}():\n    return 'noise'" for index in range(40)
        )
        source = f'''from __future__ import annotations

def audit_guard(function):
    return function

@audit_guard
def deploy_release():
    return "DEPLOY_ANCHOR"

{filler}
'''
        result = build_text_pack(
            source,
            "deploy release",
            80,
            safety_class="code",
            required_literals=("DEPLOY_ANCHOR",),
        )
        self.assertEqual(result.mode, "code-sliced")
        self.assertIn("@audit_guard", result.text)
        self.assertIn("def audit_guard", result.text)
        self.assertIn("from __future__ import annotations", result.text)

    def test_large_csv_uses_reconciled_aggregate_context(self):
        rows = ["invoice,status,amount"]
        rows.extend(
            f"INV-{index:04d},{'approved' if index % 2 == 0 else 'pending'},10.00"
            for index in range(1, 501)
        )
        source = "\n".join(rows)
        result = build_text_pack(
            source,
            "summarize amount by status",
            160,
            safety_class="table",
            required_literals=("5000.00", "approved", "pending"),
        )
        self.assertEqual(result.mode, "table-aggregated")
        self.assertIn("5000.00", result.text)
        self.assertIn("approved", result.text)
        self.assertIn("pending", result.text)
        self.assertGreater(result.reduction_ratio, 0.80)
        self.assertEqual(result.evidence["source_rows"], 500)
        self.assertTrue(result.evidence["aggregation_reconciled"])

    def test_table_aggregate_escapes_markdown_control_characters(self):
        rows = ["status,amount"]
        rows.extend(f"needs|review,10.00" for _ in range(200))
        source = "\n".join(rows)
        result = build_text_pack(
            source,
            "summarize amount by status",
            120,
            safety_class="table",
            required_literals=("2000.00",),
        )
        self.assertEqual(result.mode, "table-aggregated")
        self.assertIn(r"needs\|review", result.text)

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
