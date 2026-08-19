import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from token_forge.conversion import ProcessOutcome
from token_forge.media import process_local_media


class MediaTests(unittest.TestCase):
    def test_local_media_requires_explicit_whisper_model(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "clip.mp4"
            source.write_bytes(b"fixture")
            result = process_local_media(source, root / "out", {"ffmpeg": "ffmpeg"})
            self.assertFalse(result.success)
            self.assertEqual(result.status, "unavailable")

    def test_local_media_runs_audio_transcript_and_scene_stages(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "clip.mp4"
            source.write_bytes(b"fixture")
            calls = []

            def fake(command, timeout, environment=None):
                calls.append(command)
                if command[0] == "ffmpeg":
                    Path(command[-1]).write_bytes(b"wav")
                elif "transcribe_local.py" in str(command[1]):
                    Path(command[command.index("--output") + 1]).write_text("[0.00-1.00] hello\n", encoding="utf-8")
                elif command[0] == "scenedetect":
                    frame_dir = Path(command[command.index("-o") + 1])
                    (frame_dir / "scene_list.csv").write_text("Scene Number,Start Time\n1,0\n", encoding="utf-8")
                return ProcessOutcome(0, "", "")

            with patch("token_forge.media._run_process", side_effect=fake):
                result = process_local_media(
                    source, root / "out",
                    {"ffmpeg": "ffmpeg", "whisper_python": "python", "whisper_model": "G:/model", "scenedetect": "scenedetect"},
                )
            self.assertTrue(result.success)
            self.assertTrue(Path(result.transcript_path).is_file())
            self.assertTrue(Path(result.scenes_path).is_file())
            self.assertEqual(len(calls), 3)
