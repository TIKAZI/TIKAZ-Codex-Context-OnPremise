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
from token_forge.web import WebResult


class ConvertCliTests(unittest.TestCase):
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
                '{"validation":{"retrieval":true,"learned_compression":true}}', encoding="utf-8"
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
