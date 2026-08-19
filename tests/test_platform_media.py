import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from token_forge.conversion import ProcessOutcome
from token_forge.platform_media import inspect_platform_media


class PlatformMediaTests(unittest.TestCase):
    def test_metadata_and_subtitles_are_explicit_and_download_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                inspect_platform_media("https://example.test/video", Path(temp), {"yt_dlp": "yt-dlp"}, download=True)

    def test_platform_metadata_and_subtitles_write_recoverable_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            calls = []

            def fake(command, timeout, environment=None):
                calls.append(command)
                if "--dump-single-json" in command:
                    return ProcessOutcome(0, json.dumps({"id": "abc", "title": "Fixture"}), "")
                subtitle_dir = Path(command[command.index("-o") + 1]).parent
                (subtitle_dir / "abc.zh.vtt").write_text("WEBVTT\n\n00:00.000 --> 00:01.000\nHello\n", encoding="utf-8")
                return ProcessOutcome(0, "", "")

            with patch("token_forge.platform_media._run_process", side_effect=fake):
                result = inspect_platform_media("https://example.test/video", root / "out", {"yt_dlp": "yt-dlp"})
            self.assertTrue(result.success)
            self.assertTrue(Path(result.metadata_path).is_file())
            self.assertTrue(Path(result.subtitles_path).joinpath("abc.zh.vtt").is_file())
            self.assertEqual(len(calls), 2)
