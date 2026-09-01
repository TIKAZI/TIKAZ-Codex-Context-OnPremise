from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from token_forge.cli import main
from token_forge.conversion import ConversionResult
from token_forge.models import PackResult
from token_forge.web import WebResult
from token_forge.visual import VisualEvidenceResult


class ConvertCliTests(unittest.TestCase):
    def test_pack_forwards_repeatable_query_variants(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.md"
            source.write_text("database rollback evidence", encoding="utf-8")
            expected = PackResult(
                text="database rollback evidence",
                mode="selected",
                input_tokens=3,
                final_tokens=3,
                protected_literals=(),
                protected_recall=1.0,
                reduction_ratio=0.0,
                source_hash="hash",
            )
            with patch("token_forge.cli.build_text_pack", return_value=expected) as build:
                with contextlib.redirect_stdout(io.StringIO()):
                    code = main([
                        "pack", "--input", str(source), "--query", "recover release",
                        "--budget", "50", "--output", str(root / "out"),
                        "--query-variant", "database backup rollback",
                        "--query-variant", "release owner verification",
                    ])

            self.assertEqual(code, 0)
            self.assertEqual(
                build.call_args.kwargs["query_variants"],
                ("database backup rollback", "release owner verification"),
            )

    def test_retrieval_benchmark_returns_nonzero_when_a_quality_gate_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = root / "manifest.json"
            manifest.write_text('{"cases": []}', encoding="utf-8")
            report = {"validation": {"all_required_pass": False}}
            with patch("token_forge.cli.run_retrieval_manifest", return_value=report) as run:
                with contextlib.redirect_stdout(io.StringIO()):
                    code = main([
                        "benchmark-retrieval", "--manifest", str(manifest),
                        "--output", str(root / "out"), "--mode", "economy",
                    ])
            self.assertEqual(code, 2)
            run.assert_called_once()

    def test_visual_evidence_command_builds_bounded_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            frames = root / "frames"
            frames.mkdir()
            (frames / "clip-Scene-001-01.jpg").write_bytes(b"same")
            (frames / "clip-Scene-001-02.jpg").write_bytes(b"same")
            stream = io.StringIO()

            with contextlib.redirect_stdout(stream):
                code = main([
                    "visual-evidence", "--frames", str(frames),
                    "--output", str(root / "out"), "--max-frames", "1",
                ])

            payload = json.loads(stream.getvalue())
            self.assertEqual(code, 0)
            self.assertEqual(payload["counts"]["selected"], 1)
            self.assertEqual(payload["counts"]["duplicate"], 1)
            self.assertTrue((root / "out" / "visual-evidence.json").is_file())

    def test_visual_analyze_uses_local_config_and_prints_routing_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = root / "visual-evidence.json"
            manifest.write_text('{"frames": []}', encoding="utf-8")
            config = root / "local.toml"
            config.write_text(
                "[adapters]\nollama_host = 'http://127.0.0.1:11434'\n"
                "ollama_model = 'qwen3-vl:8b'\n",
                encoding="utf-8",
            )
            expected = VisualEvidenceResult(
                str(manifest), {"resolved_local": 1, "needs_codex": 0}, tuple()
            )
            stream = io.StringIO()
            with patch("token_forge.cli.resolve_local_visual_evidence", return_value=expected) as resolve:
                with contextlib.redirect_stdout(stream):
                    code = main([
                        "visual-analyze", "--manifest", str(manifest),
                        "--config", str(config), "--minimum-confidence", "0.8",
                    ])

            self.assertEqual(code, 0)
            self.assertEqual(json.loads(stream.getvalue())["counts"]["resolved_local"], 1)
            resolve.assert_called_once_with(
                manifest,
                {"ollama_host": "http://127.0.0.1:11434", "ollama_model": "qwen3-vl:8b"},
                minimum_vlm_confidence=0.8,
                timeout_seconds=180,
            )

    def test_visual_benchmark_uses_manifest_frames_and_local_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = root / "manifest.json"
            frames = root / "frames"
            frames.mkdir()
            manifest.write_text('{"cases": []}', encoding="utf-8")
            config = root / "local.toml"
            config.write_text(
                "[adapters]\nollama_host = 'http://127.0.0.1:11434'\n"
                "ollama_model = 'qwen3-vl:8b'\n",
                encoding="utf-8",
            )
            report = {
                "metrics": {"combined_fact_recall": 1.0},
                "validation": {"all_required_pass": True},
            }
            stream = io.StringIO()
            with patch("token_forge.cli.run_visual_manifest", return_value=report) as run:
                with contextlib.redirect_stdout(stream):
                    code = main([
                        "benchmark-visual", "--manifest", str(manifest),
                        "--frames", str(frames), "--output", str(root / "out"),
                        "--config", str(config),
                    ])

            self.assertEqual(code, 0)
            self.assertEqual(json.loads(stream.getvalue()), report)
            run.assert_called_once()

    def test_visual_benchmark_fails_when_a_required_visual_gate_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = root / "manifest.json"
            frames = root / "frames"
            frames.mkdir()
            manifest.write_text('{"cases": []}', encoding="utf-8")
            report = {"validation": {"all_required_pass": False}}
            with patch("token_forge.cli.run_visual_manifest", return_value=report):
                with contextlib.redirect_stdout(io.StringIO()):
                    code = main([
                        "benchmark-visual", "--manifest", str(manifest),
                        "--frames", str(frames), "--output", str(root / "out"),
                    ])

            self.assertEqual(code, 2)

    def test_acceptance_benchmark_uses_local_config_and_fails_on_required_case(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = root / "manifest.json"
            manifest.write_text('{"schema_version": 1, "cases": []}', encoding="utf-8")
            config = root / "local.toml"
            config.write_text('[adapters]\nmarkitdown = "G:/markitdown.exe"\n', encoding="utf-8")
            report = {
                "case_count": 1,
                "status_counts": {"passed": 0, "failed": 1, "pending": 0},
                "all_required_pass": False,
            }
            stream = io.StringIO()
            with patch("token_forge.cli.run_acceptance_manifest", return_value=report) as run:
                with contextlib.redirect_stdout(stream):
                    code = main([
                        "benchmark-acceptance", "--manifest", str(manifest),
                        "--output", str(root / "out"), "--config", str(config),
                    ])

            self.assertEqual(code, 2)
            self.assertEqual(json.loads(stream.getvalue())["all_required_pass"], False)
            run.assert_called_once_with(manifest, root / "out", {"markitdown": "G:/markitdown.exe"}, allow_network=False)

    def test_web_command_prints_render_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = WebResult(
                success=True,
                status="success",
                url="https://example.test",
                final_url="https://example.test/",
                source_hash="abc",
                rendered_html=str(root / "rendered.html"),
                viewport_image=str(root / "viewport.png"),
                elapsed_ms=5,
                conversion={"adapter": "defuddle"},
            )
            stream = io.StringIO()
            config = root / "local.toml"
            config.write_text("[adapters]\nnode = 'node'\nplaywright = 'playwright'\n", encoding="utf-8")
            with patch("token_forge.cli.prepare_web_url", return_value=result) as prepare:
                with contextlib.redirect_stdout(stream):
                    code = main([
                        "web", "--url", "https://example.test",
                        "--output", str(root / "output"), "--config", str(config),
                    ])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(stream.getvalue())["status"], "success")
            prepare.assert_called_once()

    def test_doctor_separates_installed_commands_from_conversion_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mineru = root / "mineru.exe"
            mineru.write_bytes(b"")
            config = root / "local.toml"
            config.write_text(
                f"[adapters]\nmineru = '{mineru.as_posix()}'\n"
                f"mineru_config = '{(root / 'missing-mineru.json').as_posix()}'\n"
                "[runtime]\nallow_remote = false\n",
                encoding="utf-8",
            )
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                code = main(["doctor", "--config", str(config)])

            payload = json.loads(stream.getvalue())
            self.assertEqual(code, 0)
            self.assertFalse(payload["conversion_gates"]["mineru"]["eligible"])
            self.assertFalse(payload["conversion_gates"]["paddleocr_local_scan"]["eligible"])
            self.assertFalse(payload["model_gates"]["retrieval"]["eligible"])
            self.assertFalse(payload["model_gates"]["learned_compression"]["eligible"])
            self.assertTrue(payload["visual_gates"]["codex_handoff"]["eligible"])
            self.assertFalse(payload["visual_gates"]["automatic_local_vlm"]["eligible"])
            self.assertEqual(payload["visual_gates"]["automatic_local_vlm"]["status"], "not-configured")

    def test_doctor_reports_configured_loopback_visual_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ollama = root / "ollama.exe"
            python = root / "python.exe"
            ollama.write_bytes(b"")
            python.write_bytes(b"")
            config = root / "local.toml"
            config.write_text(
                f"[adapters]\nollama = '{ollama.as_posix()}'\n"
                f"paddleocr_python = '{python.as_posix()}'\n"
                "ollama_host = 'http://127.0.0.1:11434'\n"
                "ollama_model = 'qwen3-vl:8b'\n",
                encoding="utf-8",
            )
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                main(["doctor", "--config", str(config)])

            gate = json.loads(stream.getvalue())["visual_gates"]["automatic_local_vlm"]
            self.assertTrue(gate["eligible"])
            self.assertFalse(gate["validated"])
            self.assertEqual(gate["status"], "configured-unvalidated")

    def test_doctor_does_not_treat_a_loopback_prefix_as_local(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ollama = root / "ollama.exe"
            python = root / "python.exe"
            ollama.write_bytes(b"")
            python.write_bytes(b"")
            config = root / "local.toml"
            config.write_text(
                f"[adapters]\nollama = '{ollama.as_posix()}'\n"
                f"paddleocr_python = '{python.as_posix()}'\n"
                "ollama_host = 'http://localhost.example.test:11434'\n"
                "ollama_model = 'qwen3-vl:8b'\n",
                encoding="utf-8",
            )
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                main(["doctor", "--config", str(config)])

            gate = json.loads(stream.getvalue())["visual_gates"]["automatic_local_vlm"]
            self.assertFalse(gate["eligible"])

    def test_optimize_uses_explicit_local_models(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "notes.md"
            source.write_text("Release v3.2.1 notes.", encoding="utf-8")
            config = root / "local.toml"
            config.write_text(
                "[adapters]\nretrieval_python = 'G:/python.exe'\n"
                "embedding_model = 'G:/bge-m3'\nreranker_model = 'G:/reranker'\n",
                encoding="utf-8",
            )
            expected = type("Result", (), {
                "protected_recall": 1.0,
                "budget_conflict": False,
                "to_dict": lambda self: {"mode": "model-retrieved"},
            })()
            with patch("token_forge.cli.optimize_text_pack", return_value=expected) as optimize:
                with contextlib.redirect_stdout(io.StringIO()):
                    code = main([
                        "optimize", "--input", str(source), "--query", "release",
                        "--budget", "50", "--output", str(root / "out"),
                        "--config", str(config),
                    ])
            self.assertEqual(code, 0)
            self.assertEqual(optimize.call_args.args[3]["embedding_model"], "G:/bge-m3")

    def test_doctor_reads_stage_validation_from_a_local_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            models = {}
            for name in ("embedding_model", "reranker_model", "llmlingua_model"):
                model = root / name
                model.mkdir()
                (model / "config.json").write_text("{}", encoding="utf-8")
                with (model / "model.safetensors").open("wb") as stream:
                    stream.truncate(1_000_001)
                models[name] = model
            report = root / "validation.json"
            report.write_text(
                json.dumps({
                    "validation": {"retrieval": True, "learned_compression": True},
                    "validated_models": {name: str(path.resolve()) for name, path in models.items()},
                }),
                encoding="utf-8",
            )
            config = root / "local.toml"
            config.write_text(
                "[adapters]\nretrieval_python = 'python'\nllmlingua_python = 'python'\n"
                + "\n".join(f"{name} = '{path.as_posix()}'" for name, path in models.items())
                + f"\nmodel_validation = '{report.as_posix()}'\n",
                encoding="utf-8",
            )
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                main(["doctor", "--config", str(config)])
            gates = json.loads(stream.getvalue())["model_gates"]
            self.assertTrue(gates["retrieval"]["validated"])
            self.assertTrue(gates["learned_compression"]["validated"])

    def test_doctor_rejects_validation_report_for_different_model_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            models = {}
            for name in ("embedding_model", "reranker_model", "llmlingua_model"):
                model = root / name
                model.mkdir()
                (model / "config.json").write_text("{}", encoding="utf-8")
                with (model / "model.safetensors").open("wb") as stream:
                    stream.truncate(1_000_001)
                models[name] = model
            report = root / "validation.json"
            report.write_text(json.dumps({
                "validation": {"retrieval": True, "learned_compression": True},
                "validated_models": {
                    "embedding_model": str((root / "different-embedding").resolve()),
                    "reranker_model": str(models["reranker_model"].resolve()),
                    "llmlingua_model": str(models["llmlingua_model"].resolve()),
                },
            }), encoding="utf-8")
            config = root / "local.toml"
            config.write_text(
                "[adapters]\nretrieval_python = 'python'\nllmlingua_python = 'python'\n"
                + "\n".join(f"{name} = '{path.as_posix()}'" for name, path in models.items())
                + f"\nmodel_validation = '{report.as_posix()}'\n",
                encoding="utf-8",
            )
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                main(["doctor", "--config", str(config)])
            gates = json.loads(stream.getvalue())["model_gates"]
            self.assertFalse(gates["retrieval"]["validated"])
            self.assertTrue(gates["learned_compression"]["validated"])

    def test_convert_passes_local_config_and_prints_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "article.html"
            source.write_text("<p>release v1.2.3</p>", encoding="utf-8")
            output = root / "output"
            config = root / "local.toml"
            config.write_text('[adapters]\ndefuddle = "G:/tools/defuddle.cmd"\n', encoding="utf-8")
            result = ConversionResult(
                success=True,
                status="success",
                source=str(source),
                source_hash="abc123",
                family="web",
                adapter="defuddle",
                adapter_version="0.19.2",
                output_path=str(output / "canonical.md"),
                protected_literals=("v1.2.3",),
                protected_recall=1.0,
                verification_level="source-literal",
                elapsed_ms=7,
            )

            stream = io.StringIO()
            with patch("token_forge.cli.convert_source", return_value=result) as convert:
                with contextlib.redirect_stdout(stream):
                    code = main([
                        "convert",
                        "--input", str(source),
                        "--output", str(output),
                        "--config", str(config),
                        "--adapter", "defuddle",
                        "--timeout", "45",
                    ])

            self.assertEqual(code, 0)
            self.assertEqual(json.loads(stream.getvalue())["adapter"], "defuddle")
            convert.assert_called_once_with(
                source,
                output,
                {"defuddle": "G:/tools/defuddle.cmd"},
                requested_adapter="defuddle",
                timeout_seconds=45,
                allow_remote=False,
            )

    def test_convert_uses_distinct_exit_codes_for_unavailable_and_failed(self) -> None:
        base = dict(
            success=False,
            source="article.html",
            source_hash="abc123",
            family="web",
            adapter=None,
            adapter_version=None,
            output_path=None,
            protected_literals=(),
            protected_recall=1.0,
            verification_level="source-literal",
            elapsed_ms=1,
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "article.html"
            source.write_text("<p>text</p>", encoding="utf-8")
            for status, expected in (("unavailable", 3), ("quality-failed", 2), ("needs-ocr", 4)):
                result = ConversionResult(status=status, **base)
                with patch("token_forge.cli.convert_source", return_value=result):
                    with contextlib.redirect_stdout(io.StringIO()):
                        code = main([
                            "convert", "--input", str(source),
                            "--output", str(root / status),
                        ])
                self.assertEqual(code, expected)


if __name__ == "__main__":
    unittest.main()
