import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Sequence

from token_forge.conversion import ProcessOutcome, convert_source


class ConversionTests(unittest.TestCase):
    def test_scanned_pdf_reports_needs_ocr_when_no_local_ocr_adapter_is_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "scan.pdf"
            source.write_bytes(b"%PDF-1.4\nimage-only")

            def runner(command: Sequence[str], timeout: int) -> ProcessOutcome:
                if "--version" in command:
                    return ProcessOutcome(0, "markitdown 0.1.7", "")
                destination = Path(command[command.index("-o") + 1])
                destination.write_text("", encoding="utf-8")
                return ProcessOutcome(0, "", "")

            result = convert_source(
                source,
                root / "output",
                {"markitdown": "markitdown.exe", "mineru": "mineru.exe"},
                runner=runner,
            )

            self.assertFalse(result.success)
            self.assertEqual(result.status, "needs-ocr")
            self.assertEqual([attempt.status for attempt in result.attempts], ["empty-output"])

    def test_scanned_pdf_escalates_to_configured_local_mineru(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "scan.pdf"
            source.write_bytes(b"%PDF-1.4\nimage-only")
            mineru_config = root / "mineru.json"
            mineru_config.write_text('{"models-dir":{"pipeline":"G:/models/mineru"}}', encoding="utf-8")

            def runner(command: Sequence[str], timeout: int) -> ProcessOutcome:
                if "--version" in command:
                    return ProcessOutcome(0, f"{Path(command[0]).stem} 1.0", "")
                if "markitdown" in Path(command[0]).stem:
                    destination = Path(command[command.index("-o") + 1])
                    destination.write_text("", encoding="utf-8")
                    return ProcessOutcome(0, "", "")
                self.assertIn("ocr", command)
                self.assertIn("pipeline", command)
                destination = Path(command[command.index("-o") + 1])
                nested = destination / "scan" / "ocr"
                nested.mkdir(parents=True)
                (nested / "scan.md").write_text(
                    "Version v6.7.8\n\nRelease date 2026-08-18",
                    encoding="utf-8",
                )
                return ProcessOutcome(0, "", "")

            result = convert_source(
                source,
                root / "output",
                {
                    "markitdown": "markitdown.exe",
                    "mineru": "mineru.exe",
                    "mineru_config": str(mineru_config),
                },
                runner=runner,
            )

            self.assertTrue(result.success)
            self.assertEqual(result.adapter, "mineru")
            self.assertEqual([attempt.status for attempt in result.attempts], ["empty-output", "success"])
            self.assertIn("v6.7.8", (root / "output" / "canonical.md").read_text(encoding="utf-8"))

    def test_docling_is_unavailable_without_local_artifacts_when_remote_is_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "report.pdf"
            source.write_bytes(b"%PDF-1.4\nfixture")
            result = convert_source(
                source,
                root / "output",
                {"docling": "docling.exe"},
                requested_adapter="docling",
            )
            self.assertFalse(result.success)
            self.assertEqual(result.status, "unavailable")

    def test_mineru_is_unavailable_without_local_model_config_when_remote_is_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "scan.pdf"
            source.write_bytes(b"%PDF-1.4\nimage-only")
            result = convert_source(
                source,
                root / "output",
                {"mineru": "mineru.exe"},
                requested_adapter="mineru",
            )
            self.assertFalse(result.success)
            self.assertEqual(result.status, "unavailable")

    def test_docling_pdf_conversion_is_explicitly_output_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "report.pdf"
            source.write_bytes(b"%PDF-1.4\nfixture")
            output = root / "output"

            def runner(command: Sequence[str], timeout: int) -> ProcessOutcome:
                if "--version" in command:
                    self.assertEqual(command[1:3], ["convert", "--version"])
                    return ProcessOutcome(0, "Docling version: 2.120.1", "")
                destination = Path(command[command.index("--output") + 1])
                destination.mkdir(parents=True, exist_ok=True)
                (destination / "report.md").write_text("# Verified non-empty output", encoding="utf-8")
                return ProcessOutcome(0, "", "")

            result = convert_source(
                source,
                output,
                {"docling": "docling.exe", "docling_artifacts": str(root / "artifacts")},
                requested_adapter="docling",
                runner=runner,
            )

            self.assertTrue(result.success)
            self.assertEqual(result.adapter, "docling")
            self.assertEqual(result.verification_level, "output-only")
            self.assertIsNone(result.protected_recall)
            self.assertEqual((output / "canonical.md").read_text(encoding="utf-8"), "# Verified non-empty output")

    def test_docx_uses_source_xml_for_protected_literal_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "release.docx"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr(
                    "word/document.xml",
                    '<w:document xmlns:w="urn:test"><w:body><w:p><w:r><w:t>'
                    'Release v7.8.9 on 2026-09-15'
                    '</w:t></w:r></w:p></w:body></w:document>',
                )
            output = root / "output"

            def runner(command: Sequence[str], timeout: int) -> ProcessOutcome:
                if "--version" in command:
                    return ProcessOutcome(0, "markitdown 0.1.7", "")
                destination = Path(command[command.index("-o") + 1])
                destination.write_text("# Release", encoding="utf-8")
                return ProcessOutcome(0, "", "")

            result = convert_source(
                source,
                output,
                {"markitdown": "markitdown.exe"},
                runner=runner,
            )

            self.assertFalse(result.success)
            self.assertEqual(result.verification_level, "source-literal")
            self.assertIn("v7.8.9", result.protected_literals)
            self.assertLess(result.protected_recall, 1.0)

    def test_html_protection_ignores_markup_metadata_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "article.html"
            source.write_text(
                '<meta charset="utf-8"><style>.x{width:8px}</style>'
                '<main>Release v9.2.1 on 2026-12-01.</main>',
                encoding="utf-8",
            )
            output = root / "output"

            def runner(command: Sequence[str], timeout: int) -> ProcessOutcome:
                if "--version" in command:
                    return ProcessOutcome(0, "defuddle 1.0", "")
                destination = Path(command[command.index("--output") + 1])
                destination.write_text("Release v9.2.1 on 2026-12-01.", encoding="utf-8")
                return ProcessOutcome(0, "", "")

            result = convert_source(
                source,
                output,
                {"defuddle": "defuddle"},
                runner=runner,
            )

            self.assertTrue(result.success)
            self.assertNotIn("8", result.protected_literals)

    def test_auto_conversion_falls_back_and_writes_a_traceable_ledger(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "article.html"
            source.write_text(
                "<h1>Release</h1><p>Use v9.2.1 on 2026-12-01.</p>"
                "<code>python migrate.py --target v9.2.1</code>",
                encoding="utf-8",
            )
            output = root / "output"

            def fake_runner(command, timeout_seconds):
                if command[-1] == "--version":
                    return ProcessOutcome(0, f"{Path(command[0]).stem} 1.0", "")
                if "defuddle" in Path(command[0]).stem:
                    return ProcessOutcome(1, "", "parse failed")
                destination = Path(command[command.index("-o") + 1])
                destination.write_text(
                    "# Release\n\nUse v9.2.1 on 2026-12-01.\n\n"
                    "`python migrate.py --target v9.2.1`",
                    encoding="utf-8",
                )
                return ProcessOutcome(0, "", "")

            result = convert_source(
                source,
                output,
                adapters={"defuddle": "defuddle.cmd", "markitdown": "markitdown.exe"},
                runner=fake_runner,
            )

            self.assertTrue(result.success)
            self.assertEqual(result.adapter, "markitdown")
            self.assertEqual(result.protected_recall, 1.0)
            self.assertEqual([attempt.status for attempt in result.attempts], ["failed", "success"])
            self.assertTrue((output / "canonical.md").is_file())
            ledger = json.loads((output / "conversion.json").read_text(encoding="utf-8"))
            self.assertEqual(ledger["source_hash"], result.source_hash)
            self.assertEqual(ledger["adapter"], "markitdown")

    def test_conversion_rejects_output_that_drops_protected_literals(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "report.html"
            source.write_text("Release v4.5.6 at 2026-10-03.", encoding="utf-8")
            output = root / "output"

            def lossy_runner(command, timeout_seconds):
                if command[-1] == "--version":
                    return ProcessOutcome(0, "markitdown 1.0", "")
                destination = Path(command[command.index("-o") + 1])
                destination.write_text("A release is planned.", encoding="utf-8")
                return ProcessOutcome(0, "", "")

            result = convert_source(
                source,
                output,
                adapters={"markitdown": "markitdown.exe"},
                requested_adapter="markitdown",
                runner=lossy_runner,
            )

            self.assertFalse(result.success)
            self.assertEqual(result.status, "quality-failed")
            self.assertLess(result.protected_recall, 1.0)
            self.assertFalse((output / "canonical.md").exists())
            self.assertTrue((output / "conversion.json").is_file())


if __name__ == "__main__":
    unittest.main()
