import json
import tempfile
import unittest
from pathlib import Path
from typing import Sequence

from token_forge.conversion import ProcessOutcome, convert_source


class ConversionTests(unittest.TestCase):
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
