import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

from token_forge.conversion import ProcessOutcome
from token_forge.media import process_local_media
from token_forge.visual import VisualEvidenceResult


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
                    Path(command[command.index("--metadata") + 1]).write_text(
                        '{"device":"cuda","compute_type":"float16","fallback":false}', encoding="utf-8"
                    )
                elif command[0] == "scenedetect":
                    frame_dir = Path(command[command.index("-o") + 1])
                    (frame_dir / "scene_list.csv").write_text("Scene Number,Start Time\n1,0\n", encoding="utf-8")
                    (frame_dir / "clip-Scene-001-01.jpg").write_bytes(b"same-frame")
                    (frame_dir / "clip-Scene-001-02.jpg").write_bytes(b"same-frame")
                return ProcessOutcome(0, "", "")

            with patch("token_forge.media._run_process", side_effect=fake):
                result = process_local_media(
                    source, root / "out",
                    {"ffmpeg": "ffmpeg", "whisper_python": "python", "whisper_model": "G:/model", "scenedetect": "scenedetect"},
                )
            self.assertTrue(result.success)
            self.assertTrue(Path(result.transcript_path).is_file())
            self.assertTrue(Path(result.scenes_path).is_file())
            self.assertTrue(Path(result.transcription_runtime_path).is_file())
            self.assertTrue(Path(result.visual_evidence_path).is_file())
            visual = json.loads(Path(result.visual_evidence_path).read_text(encoding="utf-8"))
            self.assertEqual(visual["counts"]["selected"], 1)
            self.assertEqual(visual["counts"]["duplicate"], 1)
            self.assertEqual(len(calls), 3)

    def test_local_media_automatically_resolves_frames_when_local_vlm_is_configured(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "clip.mp4"
            source.write_bytes(b"fixture")

            def fake(command, timeout, environment=None):
                if command[0] == "ffmpeg":
                    Path(command[-1]).write_bytes(b"wav")
                elif "transcribe_local.py" in str(command[1]):
                    Path(command[command.index("--output") + 1]).write_text("hello\n", encoding="utf-8")
                    Path(command[command.index("--metadata") + 1]).write_text("{}", encoding="utf-8")
                elif command[0] == "scenedetect":
                    frame_dir = Path(command[command.index("-o") + 1])
                    (frame_dir / "clip-Scene-001-01.jpg").write_bytes(b"frame")
                return ProcessOutcome(0, "", "")

            adapters = {
                "ffmpeg": "ffmpeg",
                "whisper_python": "python",
                "whisper_model": "G:/model",
                "scenedetect": "scenedetect",
                "ollama_host": "http://127.0.0.1:11434",
                "ollama_model": "qwen3-vl:8b",
            }
            with (
                patch("token_forge.media._run_process", side_effect=fake),
                patch("token_forge.media.resolve_local_visual_evidence") as resolve,
            ):
                resolve.side_effect = lambda manifest, configured, **kwargs: VisualEvidenceResult(
                    str(manifest), {"resolved_local": 1}, tuple()
                )
                result = process_local_media(source, root / "out", adapters)

            self.assertTrue(result.success)
            resolve.assert_called_once()
            self.assertEqual(resolve.call_args.args[1], adapters)
