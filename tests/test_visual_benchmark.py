import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from token_forge.visual import VisualEvidenceResult
from token_forge.visual_benchmark import _contains, run_visual_manifest


class VisualBenchmarkTests(unittest.TestCase):
    def test_fact_matching_normalizes_layout_whitespace_only(self):
        self.assertTrue(_contains("Basic\n$9", "Basic $9"))
        self.assertFalse(_contains("Basic\n$19", "Basic $9"))

    def test_rejects_unmanifested_images_that_could_change_selection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            frames = root / "frames"
            frames.mkdir()
            (frames / "declared.png").write_bytes(b"declared")
            (frames / "extra.png").write_bytes(b"extra")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({
                "cases": [{
                    "id": "declared", "file": "declared.png",
                    "protected_facts": ["fact"],
                }]
            }), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "exactly match"):
                run_visual_manifest(manifest, frames, root / "out", {})

    @patch("token_forge.visual_benchmark.resolve_local_visual_evidence")
    def test_reports_ocr_vlm_combined_recall_and_escalation_separately(self, resolve):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            frames = root / "frames"
            frames.mkdir()
            (frames / "ocr.png").write_bytes(b"ocr")
            (frames / "chart.png").write_bytes(b"chart")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({
                "schema_version": 1,
                "minimum_combined_fact_recall": 1.0,
                "cases": [
                    {
                        "id": "ocr",
                        "file": "ocr.png",
                        "profile": "document",
                        "expected_frame_type": "document",
                        "protected_facts": ["v4.8.0", "2026-08-20"],
                    },
                    {
                        "id": "chart",
                        "file": "chart.png",
                        "profile": "chart",
                        "expected_frame_type": "chart",
                        "protected_facts": ["72%"],
                    },
                ],
            }), encoding="utf-8")

            def fake_resolve(evidence_path, adapters, **kwargs):
                payload = json.loads(evidence_path.read_text(encoding="utf-8"))
                by_name = {Path(frame["path"]).name: frame for frame in payload["frames"]}
                by_name["ocr.png"].update({
                    "semantic_status": "resolved-local",
                    "observations": [
                        {"kind": "ocr-text", "text": "release v4.8.0", "confidence": "high"},
                        {"kind": "visual-observation", "text": "date 2026-08-20", "confidence": "high"},
                    ],
                    "local_inference": {
                        "model": "qwen3-vl:8b", "frame_type": "document",
                        "prompt_eval_count": 400, "total_duration": 2_000_000_000,
                    },
                })
                by_name["chart.png"].update({
                    "semantic_status": "needs-codex",
                    "observations": [],
                    "local_inference": {
                        "model": "qwen3-vl:8b", "frame_type": "chart",
                        "prompt_eval_count": 300, "total_duration": 1_000_000_000,
                    },
                })
                return VisualEvidenceResult(
                    str(evidence_path),
                    {"resolved_local": 1, "needs_codex": 1},
                    tuple(payload["frames"]),
                )

            resolve.side_effect = fake_resolve
            summary = run_visual_manifest(
                manifest, frames, root / "out",
                {"ollama_model": "qwen3-vl:8b", "ollama_host": "http://127.0.0.1:11434"},
            )

            self.assertEqual(summary["metrics"]["combined_fact_recall"], 2 / 3)
            self.assertEqual(summary["metrics"]["ocr_fact_recall"], 1 / 3)
            self.assertEqual(summary["metrics"]["vlm_fact_recall"], 1 / 3)
            self.assertEqual(summary["metrics"]["frame_type_accuracy"], 1.0)
            self.assertEqual(summary["metrics"]["codex_escalation_rate"], 0.5)
            self.assertEqual(summary["metrics"]["local_prompt_eval_count"], 700)
            self.assertEqual(summary["metrics"]["local_runtime_seconds"], 3.0)
            self.assertFalse(summary["validation"]["visual_facts"])
            self.assertTrue(summary["validation"]["frame_types"])
            self.assertFalse(summary["validation"]["all_required_pass"])
            self.assertTrue((root / "out" / "cases.json").is_file())
            self.assertTrue((root / "out" / "visual-evidence.json").is_file())


if __name__ == "__main__":
    unittest.main()
