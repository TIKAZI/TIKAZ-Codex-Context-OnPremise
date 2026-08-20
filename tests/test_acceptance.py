import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from token_forge.acceptance import run_acceptance_manifest


class AcceptanceBenchmarkTests(unittest.TestCase):
    def test_platform_case_runs_only_when_network_is_explicitly_enabled(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({
                "schema_version": 1,
                "suite_id": "network-opt-in-test",
                "cases": [{
                    "id": "platform",
                    "kind": "platform-media",
                    "url": "https://example.com/video",
                    "required": False,
                }],
            }), encoding="utf-8")
            result = SimpleNamespace(
                success=True, status="success", elapsed_ms=25,
                metadata_path=str(root / "metadata.json"), subtitles_path=None,
            )

            with patch("token_forge.acceptance.inspect_platform_media", return_value=result) as inspect:
                report = run_acceptance_manifest(
                    manifest, root / "results", {"yt_dlp": "yt-dlp.exe"}, allow_network=True
                )

            self.assertEqual(report["status_counts"], {"passed": 1, "failed": 0, "pending": 0})
            inspect.assert_called_once()

    def test_expected_safety_budget_conflict_is_reported_without_failing_fidelity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture = root / "contract.md"
            fixture.write_text("Contract v7.4.2 amount 250000.00.\n" * 12, encoding="utf-8")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({
                "schema_version": 1,
                "suite_id": "budget-conflict-test",
                "cases": [{
                    "id": "contract",
                    "kind": "text-pack",
                    "source_file": "contract.md",
                    "query": "obligations",
                    "budget_tokens": 10,
                    "safety_class": "contract",
                    "protected": ["v7.4.2", "250000.00"],
                    "expect_budget_conflict": True,
                }],
            }), encoding="utf-8")

            report = run_acceptance_manifest(manifest, root / "results", {})
            case = json.loads((root / "results" / "cases.json").read_text(encoding="utf-8"))[0]

            self.assertTrue(report["all_required_pass"])
            self.assertEqual(case["status"], "passed")
            self.assertFalse(case["budget_compliant"])
            self.assertTrue(case["budget_conflict_expected"])

    def test_writes_public_output_contract_and_keeps_failures_visible(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture = root / "fixture.md"
            fixture.write_text(
                "# Release\nVersion v3.2.1 ships on 2026-09-01.\n\n"
                "Rollback command: python migrate.py --rollback v3.2.1.\n",
                encoding="utf-8",
            )
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "suite_id": "acceptance-test",
                        "cases": [
                            {
                                "id": "text-pass",
                                "kind": "text-pack",
                                "source_file": "fixture.md",
                                "query": "release rollback",
                                "budget_tokens": 80,
                                "protected": ["v3.2.1", "2026-09-01"],
                                "expected_anchors": ["python migrate.py --rollback v3.2.1"],
                            },
                            {
                                "id": "anchor-failure",
                                "kind": "text-pack",
                                "source_file": "fixture.md",
                                "query": "release rollback",
                                "budget_tokens": 80,
                                "protected": ["v3.2.1"],
                                "expected_anchors": ["ANCHOR_THAT_DOES_NOT_EXIST"],
                            },
                            {
                                "id": "network-pending",
                                "kind": "platform-media",
                                "url": "https://example.com/video",
                                "required": False,
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            output = root / "results"
            report = run_acceptance_manifest(manifest, output, {}, allow_network=False)

            self.assertEqual(report["case_count"], 3)
            self.assertEqual(report["status_counts"], {"passed": 1, "failed": 1, "pending": 1})
            self.assertEqual(report["required"]["status_counts"], {"passed": 1, "failed": 1, "pending": 0})
            self.assertFalse(report["all_required_pass"])
            self.assertEqual(report["provider_token_telemetry"], "Pending")
            self.assertNotIn("composite_score", report)
            self.assertEqual(
                {path.name for path in output.iterdir()},
                {"summary.json", "metrics.json", "cases.json", "evidence-card.md"},
            )
            cases = json.loads((output / "cases.json").read_text(encoding="utf-8"))
            self.assertEqual([case["status"] for case in cases], ["passed", "failed", "pending"])
            self.assertEqual(cases[0]["protected_fact_recall"], 1.0)
            self.assertEqual(cases[0]["anchor_recall"], 1.0)
            self.assertEqual(cases[1]["anchor_recall"], 0.0)
            card = (output / "evidence-card.md").read_text(encoding="utf-8")
            self.assertIn("anchor-failure", card)
            self.assertIn("Pending", card)

    def test_cases_without_declared_facts_do_not_inflate_fidelity_denominator(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture = root / "fixture.md"
            fixture.write_text("Dense but fact-free prose.", encoding="utf-8")
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "suite_id": "denominator-test",
                        "cases": [
                            {
                                "id": "no-facts",
                                "kind": "text-pack",
                                "source_file": "fixture.md",
                                "query": "prose",
                                "budget_tokens": 30,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            report = run_acceptance_manifest(manifest, root / "results", {})

            self.assertEqual(report["fidelity"]["protected_fact_cases"], 0)
            self.assertIsNone(report["fidelity"]["protected_fact_recall"])

    def test_rejects_duplicate_case_ids(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture = root / "fixture.md"
            fixture.write_text("hello", encoding="utf-8")
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "suite_id": "invalid-test",
                        "cases": [
                            {"id": "same", "kind": "text-pack", "source_file": "fixture.md", "query": "x", "budget_tokens": 10},
                            {"id": "same", "kind": "text-pack", "source_file": "fixture.md", "query": "x", "budget_tokens": 10},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "duplicate case id"):
                run_acceptance_manifest(manifest, root / "results", {})

    def test_runs_conversion_model_web_and_media_as_separate_routes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "document.docx").write_bytes(b"real-container-placeholder")
            (root / "document-reference.txt").write_text(
                "Document heading DOC_FACT_48", encoding="utf-8"
            )
            (root / "model.md").write_text(
                "Release v4.8.0 on 2026-11-02. Keep rollback evidence.", encoding="utf-8"
            )
            (root / "page.html").write_text("<main>WEB_ANCHOR_48</main>", encoding="utf-8")
            (root / "clip.mp4").write_bytes(b"media-container-placeholder")
            (root / "transcript-reference.txt").write_text(
                "Media fact forty eight MEDIA_FACT_48", encoding="utf-8"
            )
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "suite_id": "routes-test",
                        "cases": [
                            {
                                "id": "office",
                                "kind": "conversion",
                                "source_file": "document.docx",
                                "protected": ["DOC_FACT_48"],
                                "expected_anchors": ["Document heading"],
                                "table_cells": ["DOC_FACT_48"],
                                "reference_file": "document-reference.txt",
                            },
                            {
                                "id": "model",
                                "kind": "model-pack",
                                "source_file": "model.md",
                                "query": "release evidence",
                                "budget_tokens": 40,
                                "protected": ["v4.8.0", "2026-11-02"],
                            },
                            {
                                "id": "web",
                                "kind": "web-local",
                                "source_file": "page.html",
                                "protected": ["WEB_ANCHOR_48"],
                            },
                            {
                                "id": "media",
                                "kind": "media",
                                "source_file": "clip.mp4",
                                "language": "en",
                                "transcript_facts": ["MEDIA_FACT_48"],
                                "transcript_reference_file": "transcript-reference.txt",
                                "minimum_keyframes": 2,
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            def fake_conversion(source, output, adapters, **kwargs):
                output.mkdir(parents=True, exist_ok=True)
                canonical = output / "canonical.md"
                canonical.write_text("# Document heading\nDOC_FACT_48", encoding="utf-8")
                return SimpleNamespace(
                    success=True, status="success", adapter="markitdown",
                    verification_level="source-literal", protected_recall=1.0,
                    elapsed_ms=12, output_path=str(canonical),
                )

            def fake_web(url, output, adapters, **kwargs):
                output.mkdir(parents=True, exist_ok=True)
                canonical = output / "canonical.md"
                canonical.write_text("WEB_ANCHOR_48", encoding="utf-8")
                return SimpleNamespace(
                    success=True, status="success", elapsed_ms=14,
                    conversion={"output_path": str(canonical), "adapter": "defuddle"},
                )

            def fake_media(source, output, adapters, **kwargs):
                output.mkdir(parents=True, exist_ok=True)
                transcript = output / "transcript.md"
                transcript.write_text("[0.00-1.20] Media fact forty eight MEDIA_FACT_48!", encoding="utf-8")
                frames = output / "keyframes"
                frames.mkdir()
                (frames / "one.jpg").write_bytes(b"1")
                (frames / "two.jpg").write_bytes(b"2")
                return SimpleNamespace(
                    success=True, status="success", elapsed_ms=16,
                    transcript_path=str(transcript), keyframes_dir=str(frames),
                    scenes_path=None,
                )

            model_result = SimpleNamespace(
                text="Release v4.8.0 on 2026-11-02.", mode="learned-compressed",
                input_tokens=20, final_tokens=10, reduction_ratio=0.5,
                budget_conflict=False, protected_recall=1.0, fallback_reason="",
            )
            with (
                patch("token_forge.acceptance.convert_source", side_effect=fake_conversion),
                patch("token_forge.acceptance.optimize_text_pack", return_value=model_result),
                patch("token_forge.acceptance.prepare_web_url", side_effect=fake_web),
                patch("token_forge.acceptance.process_local_media", side_effect=fake_media),
            ):
                output = root / "results"
                report = run_acceptance_manifest(manifest, output, {"adapter": "configured"})

            self.assertTrue(report["all_required_pass"])
            self.assertEqual(report["status_counts"], {"passed": 4, "failed": 0, "pending": 0})
            cases = json.loads((output / "cases.json").read_text(encoding="utf-8"))
            self.assertEqual({case["kind"] for case in cases}, {"conversion", "model-pack", "web-local", "media"})
            self.assertEqual(cases[0]["route"], "markitdown")
            self.assertEqual(cases[0]["character_error_rate"], 0.0)
            self.assertEqual(cases[1]["token_reduction_ratio"], 0.5)
            self.assertEqual(cases[2]["protected_fact_recall"], 1.0)
            self.assertEqual(cases[3]["transcript_fact_recall"], 1.0)
            self.assertEqual(cases[3]["keyframe_count"], 2)
            self.assertEqual(cases[3]["word_error_rate"], 0.0)
            metrics = json.loads((output / "metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["fidelity"]["table_cell_recall"], 1.0)
            self.assertEqual(metrics["multimodal"]["transcript_fact_recall"], 1.0)
            self.assertEqual(metrics["multimodal"]["visual_understanding"], "Pending")


if __name__ == "__main__":
    unittest.main()
