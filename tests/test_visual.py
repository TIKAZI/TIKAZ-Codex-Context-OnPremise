import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from token_forge.visual import _post_ollama, build_visual_evidence, resolve_local_visual_evidence


class VisualEvidenceTests(unittest.TestCase):
    @patch("token_forge.visual.urlopen")
    def test_sends_explicit_frame_type_taxonomy_to_local_vlm(self, urlopen):
        envelope = {
            "message": {
                "content": json.dumps({
                    "frame_type": "diagram",
                    "confidence": 0.9,
                    "needs_codex": False,
                    "uncertainty": "",
                    "observations": [{
                        "kind": "visual-observation",
                        "text": "A timeline connects three stages.",
                        "confidence": "high",
                    }],
                }),
            },
        }
        urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(
            envelope
        ).encode("utf-8")

        with tempfile.TemporaryDirectory() as temp:
            frame = Path(temp) / "frame.png"
            frame.write_bytes(b"image")
            _post_ollama(frame, "http://127.0.0.1:11434", "qwen3-vl:8b", 180)

        request = urlopen.call_args.args[0]
        prompt = json.loads(request.data.decode("utf-8"))["messages"][0]["content"]
        self.assertIn("UI means an interactive software screen", prompt)
        self.assertIn("A timeline without quantitative axes is a diagram", prompt)
        self.assertIn("labeled shapes primarily express spatial relationships", prompt)
        self.assertIn("connected milestones form a timeline", prompt)
        self.assertIn("objects are arranged as a schematic scene", prompt)
        self.assertIn("Settings fields, metric dashboards, and modal warning panels are UI", prompt)
        self.assertIn("Use other only when none of these types applies", prompt)

    @patch("token_forge.visual.urlopen")
    def test_accepts_structured_response_in_thinking_when_content_is_empty(self, urlopen):
        envelope = {
            "message": {
                "content": "",
                "thinking": json.dumps({
                    "frame_type": "document",
                    "confidence": 0.95,
                    "needs_codex": False,
                    "uncertainty": "",
                    "observations": [{
                        "kind": "visual-observation",
                        "text": "Version v4.8.0 is visible.",
                        "confidence": "high",
                    }],
                }),
            },
            "prompt_eval_count": 1093,
            "eval_count": 66,
        }
        response = urlopen.return_value.__enter__.return_value
        response.read.return_value = json.dumps(envelope).encode("utf-8")

        with tempfile.TemporaryDirectory() as temp:
            frame = Path(temp) / "frame.png"
            frame.write_bytes(b"image")

            result = _post_ollama(frame, "http://127.0.0.1:11434", "qwen3-vl:8b", 180)

        self.assertEqual(result["frame_type"], "document")
        self.assertEqual(result["usage"]["prompt_eval_count"], 1093)

    def test_deduplicates_exact_frames_and_covers_scenes_before_extra_samples(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            frames = root / "frames"
            frames.mkdir()
            (frames / "clip-Scene-001-01.jpg").write_bytes(b"scene-one")
            (frames / "clip-Scene-001-02.jpg").write_bytes(b"scene-one")
            (frames / "clip-Scene-001-03.jpg").write_bytes(b"scene-one-extra")
            (frames / "clip-Scene-002-01.jpg").write_bytes(b"scene-two")

            result = build_visual_evidence(frames, root / "visual-evidence.json", max_selected=2)

            self.assertEqual(result.counts["source"], 4)
            self.assertEqual(result.counts["unique"], 3)
            self.assertEqual(result.counts["selected"], 2)
            self.assertEqual(result.counts["duplicate"], 1)
            self.assertEqual(result.counts["deferred"], 1)
            selected = [frame for frame in result.frames if frame["routing_status"] == "selected"]
            self.assertEqual([frame["scene_number"] for frame in selected], [1, 2])
            duplicate = next(frame for frame in result.frames if frame["routing_status"] == "duplicate")
            self.assertEqual(duplicate["duplicate_of"], selected[0]["frame_id"])

    def test_resolves_only_hash_anchored_selected_frame_annotations(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            frames = root / "frames"
            frames.mkdir()
            frame = frames / "clip-Scene-001-01.jpg"
            frame.write_bytes(b"visual-fact")
            digest = hashlib.sha256(frame.read_bytes()).hexdigest()
            annotations = root / "annotations.json"
            annotations.write_text(json.dumps({
                "annotations": [{
                    "frame_sha256": digest,
                    "observations": [{
                        "kind": "visual-observation",
                        "text": "The interface shows release v4.8.0.",
                        "confidence": "high",
                    }],
                }]
            }), encoding="utf-8")

            result = build_visual_evidence(
                frames, root / "visual-evidence.json", max_selected=1,
                annotations_path=annotations,
            )

            self.assertEqual(result.counts["resolved"], 1)
            self.assertEqual(result.counts["pending"], 0)
            self.assertEqual(result.frames[0]["semantic_status"], "resolved")
            self.assertEqual(result.frames[0]["observations"][0]["confidence"], "high")

    def test_rejects_annotation_without_a_selected_frame_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            frames = root / "frames"
            frames.mkdir()
            (frames / "clip-Scene-001-01.jpg").write_bytes(b"known")
            annotations = root / "annotations.json"
            annotations.write_text(json.dumps({
                "annotations": [{
                    "frame_sha256": "0" * 64,
                    "observations": [{"kind": "visual-observation", "text": "unsupported"}],
                }]
            }), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "selected frame"):
                build_visual_evidence(
                    frames, root / "visual-evidence.json", annotations_path=annotations
                )

    def test_rejects_non_loopback_ollama_host(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            frames = root / "frames"
            frames.mkdir()
            (frames / "clip-Scene-001-01.jpg").write_bytes(b"frame")
            manifest = root / "visual-evidence.json"
            build_visual_evidence(frames, manifest)

            with self.assertRaisesRegex(ValueError, "loopback"):
                resolve_local_visual_evidence(
                    manifest,
                    {
                        "ollama_host": "https://vision.example.test",
                        "ollama_model": "qwen3-vl:8b",
                    },
                )

    def test_rejects_a_selected_frame_changed_after_manifest_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            frames = root / "frames"
            frames.mkdir()
            frame = frames / "clip-Scene-001-01.jpg"
            frame.write_bytes(b"original")
            manifest = root / "visual-evidence.json"
            build_visual_evidence(frames, manifest)
            frame.write_bytes(b"changed")

            with self.assertRaisesRegex(ValueError, "SHA-256"):
                resolve_local_visual_evidence(
                    manifest,
                    {
                        "ollama_host": "http://127.0.0.1:11434",
                        "ollama_model": "qwen3-vl:8b",
                    },
                )

    @patch("token_forge.visual._post_ollama")
    @patch("token_forge.visual._run_paddle_ocr")
    def test_resolves_high_confidence_local_vision_with_hash_anchored_ocr(
        self, run_ocr, post_ollama
    ):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            frames = root / "frames"
            frames.mkdir()
            frame = frames / "clip-Scene-001-01.jpg"
            frame.write_bytes(b"frame")
            digest = hashlib.sha256(frame.read_bytes()).hexdigest()
            manifest = root / "visual-evidence.json"
            build_visual_evidence(frames, manifest)
            run_ocr.return_value = {
                digest: {
                    "text": "版本 4.8.0",
                    "confidence": 0.96,
                    "line_count": 1,
                }
            }
            post_ollama.return_value = {
                "frame_type": "ui",
                "confidence": 0.91,
                "needs_codex": False,
                "uncertainty": "",
                "observations": [{
                    "kind": "visual-observation",
                    "text": "设置页显示版本 4.8.0。",
                    "confidence": "high",
                }],
                "usage": {"prompt_eval_count": 412, "eval_count": 48},
            }

            result = resolve_local_visual_evidence(
                manifest,
                {
                    "paddleocr_python": "G:/python.exe",
                    "ollama_host": "http://127.0.0.1:11434",
                    "ollama_model": "qwen3-vl:8b",
                },
            )

            self.assertEqual(result.counts["resolved_local"], 1)
            self.assertEqual(result.counts["needs_codex"], 0)
            self.assertEqual(result.frames[0]["semantic_status"], "resolved-local")
            self.assertEqual(result.frames[0]["frame_sha256"], digest)
            self.assertEqual(result.frames[0]["observations"][0]["kind"], "ocr-text")
            self.assertEqual(result.frames[0]["local_inference"]["model"], "qwen3-vl:8b")
            self.assertEqual(result.frames[0]["local_inference"]["prompt_eval_count"], 412)

    @patch("token_forge.visual._post_ollama")
    @patch("token_forge.visual._run_paddle_ocr")
    def test_routes_low_confidence_local_vision_to_codex_without_dropping_ocr(
        self, run_ocr, post_ollama
    ):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            frames = root / "frames"
            frames.mkdir()
            frame = frames / "clip-Scene-001-01.jpg"
            frame.write_bytes(b"frame")
            digest = hashlib.sha256(frame.read_bytes()).hexdigest()
            manifest = root / "visual-evidence.json"
            build_visual_evidence(frames, manifest)
            run_ocr.return_value = {
                digest: {"text": "模糊文字", "confidence": 0.42, "line_count": 1}
            }
            post_ollama.return_value = {
                "frame_type": "chart",
                "confidence": 0.54,
                "needs_codex": False,
                "uncertainty": "labels are too small",
                "observations": [],
                "usage": {"prompt_eval_count": 300, "eval_count": 20},
            }

            result = resolve_local_visual_evidence(
                manifest,
                {
                    "paddleocr_python": "G:/python.exe",
                    "ollama_host": "http://localhost:11434",
                    "ollama_model": "qwen3-vl:8b",
                },
                minimum_vlm_confidence=0.75,
            )

            self.assertEqual(result.counts["needs_codex"], 1)
            self.assertEqual(result.frames[0]["semantic_status"], "needs-codex")
            self.assertEqual(result.frames[0]["observations"][0]["text"], "模糊文字")
            self.assertEqual(result.frames[0]["local_inference"]["uncertainty"], "labels are too small")


if __name__ == "__main__":
    unittest.main()
