import json
import tempfile
import unittest
from pathlib import Path

from token_forge.conversion import ConversionResult, ProcessOutcome
from token_forge.web import prepare_web_url


class WebPreparationTests(unittest.TestCase):
    def test_playwright_render_is_converted_with_traceable_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "output"
            node = root / "node.exe"
            playwright = root / "node_modules" / ".bin" / "playwright.CMD"
            node.write_bytes(b"")
            playwright.parent.mkdir(parents=True)
            playwright.write_bytes(b"")

            def runner(command, timeout):
                self.assertEqual(command[0], str(node))
                self.assertIn("https://example.test/dashboard", command)
                staging = Path(command[command.index("--output") + 1])
                staging.mkdir(parents=True, exist_ok=True)
                (staging / "rendered.html").write_text(
                    "<main>Release v3.4.5 on 2026-08-19</main>", encoding="utf-8"
                )
                (staging / "viewport.png").write_bytes(b"png")
                (staging / "metadata.json").write_text(
                    json.dumps({"title": "Dashboard", "final_url": "https://example.test/dashboard"}),
                    encoding="utf-8",
                )
                return ProcessOutcome(0, "", "")

            def converter(source, destination, adapters, **kwargs):
                self.assertEqual(source.name, "rendered.html")
                canonical = destination / "canonical.md"
                canonical.parent.mkdir(parents=True, exist_ok=True)
                canonical.write_text("Release v3.4.5 on 2026-08-19", encoding="utf-8")
                return ConversionResult(
                    success=True,
                    status="success",
                    source=str(source),
                    source_hash="rendered-hash",
                    family="web",
                    adapter="defuddle",
                    adapter_version="0.19.2",
                    output_path=str(canonical),
                    protected_literals=("v3.4.5", "2026-08-19"),
                    protected_recall=1.0,
                    verification_level="source-literal",
                    elapsed_ms=12,
                )

            result = prepare_web_url(
                "https://example.test/dashboard",
                output,
                {
                    "node": str(node),
                    "playwright": str(playwright),
                    "defuddle": "defuddle.CMD",
                },
                runner=runner,
                converter=converter,
            )

            self.assertTrue(result.success)
            self.assertEqual(result.status, "success")
            self.assertTrue((output / "rendered.html").is_file())
            self.assertTrue((output / "viewport.png").is_file())
            self.assertTrue((output / "web.json").is_file())
            self.assertEqual(result.conversion["adapter"], "defuddle")

    def test_rejects_non_http_urls_without_launching_browser(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                prepare_web_url(
                    "file:///C:/private.txt",
                    Path(temp),
                    {"node": "node", "playwright": "playwright"},
                )


if __name__ == "__main__":
    unittest.main()
