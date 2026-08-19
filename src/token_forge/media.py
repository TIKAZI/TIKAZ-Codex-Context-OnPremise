from __future__ import annotations

import json
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

from .conversion import ProcessOutcome, _run_process


@dataclass(frozen=True)
class MediaResult:
    success: bool
    status: str
    source: str
    transcript_path: str | None
    scenes_path: str | None
    keyframes_dir: str | None
    elapsed_ms: int
    transcription_runtime_path: str | None = None
    error: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def process_local_media(
    source: Path,
    output_dir: Path,
    adapters: Mapping[str, str],
    *,
    language: str = "zh",
    timeout_seconds: int = 600,
) -> MediaResult:
    if not source.is_file():
        raise FileNotFoundError(source)
    started = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg = adapters.get("ffmpeg") or shutil.which("ffmpeg")
    whisper_python = adapters.get("whisper_python")
    whisper_model = adapters.get("whisper_model")
    scenedetect = adapters.get("scenedetect") or shutil.which("scenedetect")
    def failure(status: str, error: str) -> MediaResult:
        result = MediaResult(False, status, str(source.resolve()), None, None, None,
                             round((time.perf_counter() - started) * 1000), None, error)
        (output_dir / "media.json").write_text(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return result

    if not ffmpeg or not whisper_python or not whisper_model:
        return failure("unavailable", "ffmpeg, whisper_python, and whisper_model are required")

    audio = output_dir / "audio.wav"
    outcome = _run_process(
        [ffmpeg, "-y", "-i", str(source), "-vn", "-ac", "1", "-ar", "16000", str(audio)],
        timeout_seconds,
    )
    if outcome.returncode != 0 or not audio.is_file():
        return failure("audio-failed", (outcome.stderr or outcome.stdout).strip()[:2000])

    transcript = output_dir / "transcript.md"
    transcription_runtime = output_dir / "transcription-runtime.json"
    helper = Path(__file__).resolve().parents[2] / "scripts" / "transcribe_local.py"
    outcome = _run_process(
        [whisper_python, str(helper), "--audio", str(audio), "--model", whisper_model,
         "--language", language, "--output", str(transcript),
         "--metadata", str(transcription_runtime)],
        timeout_seconds,
    )
    if outcome.returncode != 0 or not transcript.is_file() or not transcript.read_text(encoding="utf-8").strip():
        return failure("transcription-failed", (outcome.stderr or outcome.stdout).strip()[:2000])

    scenes_path: Path | None = None
    frames_dir: Path | None = None
    if scenedetect:
        scenes_path = output_dir / "scenes.csv"
        frames_dir = output_dir / "keyframes"
        frames_dir.mkdir(parents=True, exist_ok=True)
        scene_outcome = _run_process(
            [scenedetect, "-i", str(source), "-o", str(frames_dir), "detect-content",
             "list-scenes", "save-images"],
            timeout_seconds,
        )
        candidates = sorted(frames_dir.glob("*.csv"))
        if candidates:
            candidates[0].replace(scenes_path)
        elif scene_outcome.returncode != 0:
            scenes_path = None

    result = MediaResult(True, "success", str(source.resolve()), str(transcript.resolve()),
                         str(scenes_path.resolve()) if scenes_path else None,
                         str(frames_dir.resolve()) if frames_dir else None,
                         round((time.perf_counter() - started) * 1000),
                         str(transcription_runtime.resolve()) if transcription_runtime.is_file() else None)
    (output_dir / "media.json").write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return result
