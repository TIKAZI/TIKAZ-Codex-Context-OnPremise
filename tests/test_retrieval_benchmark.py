import json
import tempfile
import unittest
from pathlib import Path

from token_forge.retrieval_benchmark import run_retrieval_manifest


class RetrievalBenchmarkTests(unittest.TestCase):
    def test_writes_separate_raw_metrics_summary_and_evidence_card(self):
        manifest = {
            "schema_version": 1,
            "k_values": [1, 3],
            "minimums": {"recall_at_3": 1.0, "evidence_precision": 1.0},
            "cases": [{
                "id": "migration",
                "query": "database rollback backup",
                "chunks": [
                    {"id": "rollback", "text": "database rollback procedure", "relevance": 2},
                    {"id": "backup", "text": "database backup evidence", "relevance": 1},
                    {"id": "noise", "text": "brand campaign colors", "relevance": 0},
                ],
            }],
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            report = run_retrieval_manifest(manifest_path, root / "out", mode="economy")
            self.assertTrue(report["validation"]["all_required_pass"])
            self.assertEqual(report["metrics"]["recall_at_3"], 1.0)
            case = report["cases"][0]
            self.assertEqual(case["selection"]["status"], "matched")
            self.assertEqual(case["selection"]["selected_count"], 2)
            self.assertEqual(case["selection"]["facet_coverage"], 1.0)
            self.assertGreater(case["selection"]["source_tokens_estimated"], 0)
            self.assertLess(
                case["selection"]["selected_tokens_estimated"],
                case["selection"]["source_tokens_estimated"],
            )
            self.assertIn("selected_token_reduction_estimated", report["metrics"])
            for name in ("summary.json", "metrics.json", "cases.json", "evidence-card.md"):
                self.assertTrue((root / "out" / name).is_file())


if __name__ == "__main__":
    unittest.main()
