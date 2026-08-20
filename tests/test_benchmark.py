import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from token_forge.benchmark import run_case, run_model_manifest


class BenchmarkTests(unittest.TestCase):
    def test_declared_facts_are_selection_requirements_not_only_posthoc_scores(self):
        case = {
            "id": "declared-anchor",
            "source": (
                "# Database\nMigration steps are ready.\n\n# Audit\nKeep audit trace\n\n"
                + "\n\n".join(
                    f"# Decoration {label}\nCampaign filler words for {label}."
                    for label in ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel")
                )
            ),
            "query": "database migration",
            "budget_tokens": 32,
            "protected": ["Keep audit trace"],
        }
        result = run_case(case)
        self.assertEqual(result["protected_recall"], 1.0)

    def test_reports_efficiency_and_fidelity_separately(self):
        case = {
            "id": "release",
            "source": "# Release\nUse v3.2.1.\n\n# Noise\nRepeated filler.\n\n# Noise\nRepeated filler.",
            "query": "release version",
            "budget_tokens": 50,
            "protected": ["v3.2.1"],
        }
        result = run_case(case)
        self.assertIn("reduction_ratio", result)
        self.assertIn("protected_recall", result)
        self.assertEqual(
            set(result["profiles"]),
            {"raw", "canonical", "retrieved", "learned-compression"},
        )
        self.assertEqual(result["profiles"]["learned-compression"]["status"], "unavailable")
        self.assertEqual(result["protected_recall"], 1.0)
        self.assertGreaterEqual(result["reduction_ratio"], 0.0)

    def test_high_risk_case_reports_pass_through(self):
        case = {
            "id": "contract",
            "source": "Contract v7.4.2 amount 250000.00.\n\n" * 10,
            "query": "summarize",
            "budget_tokens": 20,
            "safety_class": "contract",
            "protected": ["v7.4.2", "250000.00"],
        }
        result = run_case(case)
        self.assertEqual(result["mode"], "safety-pass-through")
        self.assertEqual(result["reduction_ratio"], 0.0)
        self.assertEqual(result["protected_recall"], 1.0)
        self.assertEqual(result["profiles"]["canonical"]["status"], "not-eligible")
        self.assertEqual(result["profiles"]["learned-compression"]["status"], "not-eligible")

    def test_model_report_binds_validation_to_configured_model_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture = root / "fixture.md"
            fixture.write_text("Release context.", encoding="utf-8")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"cases": [{
                "id": "binding",
                "source_file": "fixture.md",
                "query": "release",
                "budget_tokens": 20,
            }]}), encoding="utf-8")
            adapters = {
                "embedding_model": str(root / "embedding"),
                "reranker_model": str(root / "reranker"),
                "llmlingua_model": str(root / "compressor"),
            }
            model_result = SimpleNamespace(
                text="Release context.", mode="model-retrieved",
                input_tokens=4, final_tokens=4, reduction_ratio=0.0,
                fallback_reason="",
            )
            with patch("token_forge.benchmark.optimize_text_pack", return_value=model_result):
                report = run_model_manifest(manifest, root / "output", adapters)
            self.assertEqual(report.get("validated_models"), {
                name: str(Path(path).resolve()) for name, path in adapters.items()
            })


if __name__ == "__main__":
    unittest.main()
