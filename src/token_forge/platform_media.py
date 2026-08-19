from __future__ import annotations

import json
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse

from .conversion import ProcessOutcome, _run_process


@dataclass(frozen=True)
class PlatformMediaResult:
    success: bool
    status: str
    url: str
    metadata_path: str | None
    subtitles_path: str | None
    elapsed_ms: int
    error: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def inspect_platform_media(
    url: str,
    output_dir: Path,
    adapters: Mapping[str, str],
    *,
    subtitles: bool = True,
    download: bool = False,
    timeout_seconds: int = 120,
) -> PlatformMediaResult:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("platform input must be an absolute HTTP(S) URL")
    if download:
        raise ValueError("media download is intentionally not enabled by this adapter")
    started = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    ytdlp = adapters.get("yt_dlp") or shutil.which("yt-dlp")
    if not ytdlp:
        return PlatformMediaResult(False, "unavailable", url, None, None,
                                   round((time.perf_counter() - started) * 1000),
                                   "yt-dlp is not configured")
    metadata = output_dir / "metadata.json"
    command = [ytdlp, "--dump-single-json", "--skip-download", "--no-warnings", url]
    outcome = _run_process(command, timeout_seconds)
    if outcome.returncode != 0:
        result = PlatformMediaResult(False, "metadata-failed", url, None, None,
                                     round((time.perf_counter() - started) * 1000),
                                     (outcome.stderr or outcome.stdout).strip()[:2000])
        (output_dir / "platform.json").write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return result
    try:
        data = json.loads(outcome.stdout)
    except json.JSONDecodeError as error:
        result = PlatformMediaResult(False, "invalid-metadata", url, None, None,
                                     round((time.perf_counter() - started) * 1000), str(error))
        (output_dir / "platform.json").write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return result
    metadata.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    subtitle_path: Path | None = None
    if subtitles:
        subtitle_path = output_dir / "subtitles"
        subtitle_path.mkdir(exist_ok=True)
        subtitle_outcome = _run_process(
            [ytdlp, "--skip-download", "--write-subs", "--write-auto-subs",
             "--sub-langs", "all", "--sub-format", "vtt", "-o", str(subtitle_path / "%(id)s.%(ext)s"), url],
            timeout_seconds,
        )
        if subtitle_outcome.returncode != 0 or not list(subtitle_path.glob("*.vtt")):
            subtitle_path = None
    result = PlatformMediaResult(True, "success", url, str(metadata.resolve()),
                                 str(subtitle_path.resolve()) if subtitle_path else None,
                                 round((time.perf_counter() - started) * 1000))
    (output_dir / "platform.json").write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return result
