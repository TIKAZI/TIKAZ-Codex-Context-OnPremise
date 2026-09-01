import tempfile
import unittest
import zipfile
from pathlib import Path

from token_forge.conversion import convert_source
from token_forge.structured import ArchiveLimits, StructuredSourceError, convert_eml, convert_zip


class EmailConversionTests(unittest.TestCase):
    def test_eml_preserves_headers_plain_body_and_attachment_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "message.eml"
            source.write_bytes(
                b"From: benchmark@example.invalid\r\n"
                b"To: tikaz@example.invalid\r\n"
                b"Subject: TIKAZ acceptance EMAIL_ANCHOR_940\r\n"
                b"Date: Thu, 20 Aug 2026 10:00:00 +0800\r\n"
                b"MIME-Version: 1.0\r\n"
                b"Content-Type: multipart/mixed; boundary=outer\r\n\r\n"
                b"--outer\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n"
                b"Release v9.4.0.\r\n"
                b"--outer\r\nContent-Type: application/octet-stream\r\n"
                b"Content-Disposition: attachment; filename=payload.bin\r\n"
                b"Content-Transfer-Encoding: base64\r\n\r\nAAECAw==\r\n"
                b"--outer--\r\n"
            )

            markdown = convert_eml(source)

            self.assertIn("EMAIL_ANCHOR_940", markdown)
            self.assertIn("Release v9.4.0.", markdown)
            self.assertIn("payload.bin", markdown)
            self.assertIn("application/octet-stream", markdown)
            self.assertIn("4 bytes", markdown)
            self.assertNotIn("AAECAw==", markdown)

    def test_eml_uses_visible_html_when_plain_body_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "message.eml"
            source.write_text(
                "Subject: HTML release\nContent-Type: text/html; charset=utf-8\n\n"
                "<main>Release <b>v9.4.0</b>.</main><script>secret()</script>",
                encoding="utf-8",
            )

            markdown = convert_eml(source)

            self.assertIn("Release", markdown)
            self.assertIn("v9.4.0", markdown)
            self.assertNotIn("secret()", markdown)


class ZipConversionTests(unittest.TestCase):
    def test_zip_reads_safe_text_without_extracting_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "archive.zip"
            with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("docs/README.txt", "ARCHIVE_ANCHOR_940 release v9.4.0")
                archive.writestr("assets/logo.bin", b"\x00\x01")

            markdown = convert_zip(source)

            self.assertIn("docs/README.txt", markdown)
            self.assertIn("ARCHIVE_ANCHOR_940 release v9.4.0", markdown)
            self.assertIn("assets/logo.bin", markdown)
            self.assertFalse((root / "docs").exists())

    def test_zip_escapes_pipe_characters_in_markdown_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "archive.zip"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("docs/a|b.txt", "safe")

            markdown = convert_zip(source)

            self.assertIn(r"docs/a\|b.txt", markdown)

    def test_zip_rejects_parent_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "archive.zip"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("../escape.txt", "unsafe")

            with self.assertRaisesRegex(StructuredSourceError, "unsafe path"):
                convert_zip(source)

    def test_zip_rejects_excessive_compression_ratio(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "archive.zip"
            with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("bomb.txt", "A" * 100_000)

            with self.assertRaisesRegex(StructuredSourceError, "compression ratio"):
                convert_zip(source, ArchiveLimits(max_compression_ratio=10.0))

    def test_zip_rejects_symbolic_links(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "archive.zip"
            link = zipfile.ZipInfo("link.txt")
            link.create_system = 3
            link.external_attr = 0o120777 << 16
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr(link, "target.txt")

            with self.assertRaisesRegex(StructuredSourceError, "symbolic link"):
                convert_zip(source)

    def test_zip_rejects_too_many_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "archive.zip"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("one.txt", "1")
                archive.writestr("two.txt", "2")

            with self.assertRaisesRegex(StructuredSourceError, "entry count"):
                convert_zip(source, ArchiveLimits(max_entries=1))

    def test_zip_lists_nested_archive_without_recursing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            nested = root / "nested.zip"
            with zipfile.ZipFile(nested, "w") as archive:
                archive.writestr("secret.txt", "NESTED_SECRET")
            source = root / "archive.zip"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("nested.zip", nested.read_bytes())

            markdown = convert_zip(source)

            self.assertIn("nested.zip", markdown)
            self.assertNotIn("NESTED_SECRET", markdown)


class StructuredConversionIntegrationTests(unittest.TestCase):
    def test_auto_conversion_uses_native_email_route(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "message.eml"
            source.write_text(
                "Subject: EMAIL_ANCHOR_940\n\nRelease v9.4.0.", encoding="utf-8"
            )

            result = convert_source(source, root / "out", adapters={})

            self.assertTrue(result.success)
            self.assertEqual(result.adapter, "email-parser")
            self.assertEqual(result.protected_recall, 1.0)
            self.assertEqual(result.verification_level, "source-literal")

    def test_auto_conversion_uses_bounded_zip_route(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "archive.zip"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("README.txt", "ARCHIVE_ANCHOR_940 release v9.4.0")

            result = convert_source(source, root / "out", adapters={})

            self.assertTrue(result.success)
            self.assertEqual(result.adapter, "bounded-zip")
            self.assertEqual(result.protected_recall, 1.0)

    def test_unsafe_zip_fails_closed_and_keeps_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "archive.zip"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("../escape.txt", "unsafe")
            output = root / "out"

            result = convert_source(source, output, adapters={})

            self.assertFalse(result.success)
            self.assertEqual(result.status, "unsafe-archive")
            self.assertFalse((output / "canonical.md").exists())
            self.assertTrue((output / "conversion.json").is_file())


if __name__ == "__main__":
    unittest.main()
