import unittest

from token_forge.benchmark import run_case


class BenchmarkTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
