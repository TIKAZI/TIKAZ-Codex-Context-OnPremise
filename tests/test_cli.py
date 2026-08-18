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


class ConvertCliTests(unittest.TestCase):
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
            for status, expected in (("unavailable", 3), ("quality-failed", 2)):
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
