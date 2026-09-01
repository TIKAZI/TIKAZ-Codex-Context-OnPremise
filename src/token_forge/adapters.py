from __future__ import annotations

import os
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping


@dataclass(frozen=True)
class AdapterSpec:
    name: str
    candidates: tuple[str, ...]


@dataclass(frozen=True)
class AdapterStatus:
    name: str
    available: bool
    executable: str | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def probe_adapter(spec: AdapterSpec) -> AdapterStatus:
    for candidate in spec.candidates:
        if not candidate:
            continue
        explicit = Path(os.path.expandvars(candidate)).expanduser()
        if explicit.exists():
            if spec.name in {"embedding-model", "reranker-model", "llmlingua-model"}:
                # A partially-created Hugging Face directory is not a usable model.
                has_config = (explicit / "config.json").is_file()
                has_weights = any(
                    path.suffix in {".safetensors", ".bin"} and path.stat().st_size > 1_000_000
                    for path in explicit.glob("*")
                    if path.is_file()
                )
                if not (has_config and has_weights):
                    continue
            return AdapterStatus(spec.name, True, str(explicit.resolve()))
        located = shutil.which(candidate)
        if located:
            return AdapterStatus(spec.name, True, located)
    return AdapterStatus(spec.name, False, None)


def default_adapter_specs(configured: Mapping[str, str] | None = None) -> tuple[AdapterSpec, ...]:
    configured = configured or {}
    return (
        AdapterSpec("node", tuple(filter(None, (configured.get("node"), os.getenv("TOKEN_FORGE_NODE"), "node")))),
        AdapterSpec("ffmpeg", tuple(filter(None, (configured.get("ffmpeg"), os.getenv("TOKEN_FORGE_FFMPEG"), "ffmpeg", "ffmpeg.cmd")))),
        AdapterSpec("markitdown", tuple(filter(None, (configured.get("markitdown"), "markitdown")))),
        AdapterSpec("docling", tuple(filter(None, (configured.get("docling"), "docling")))),
        AdapterSpec("mineru", tuple(filter(None, (configured.get("mineru"), "mineru")))),
        AdapterSpec("paddleocr", tuple(filter(None, (configured.get("paddleocr"), "paddleocr")))),
        AdapterSpec("paddleocr-python", tuple(filter(None, (configured.get("paddleocr_python"),)))),
        AdapterSpec("ollama", tuple(filter(None, (configured.get("ollama"), "ollama")))),
        AdapterSpec("defuddle", tuple(filter(None, (configured.get("defuddle"), "defuddle")))),
        AdapterSpec("playwright", tuple(filter(None, (configured.get("playwright"), "playwright")))),
        AdapterSpec("yt-dlp", tuple(filter(None, (configured.get("yt_dlp"), "yt-dlp")))),
        AdapterSpec("scenedetect", tuple(filter(None, (configured.get("scenedetect"), "scenedetect")))),
        AdapterSpec("retrieval-python", tuple(filter(None, (configured.get("retrieval_python"),)))),
        AdapterSpec("llmlingua-python", tuple(filter(None, (configured.get("llmlingua_python"),)))),
        AdapterSpec("embedding-model", tuple(filter(None, (configured.get("embedding_model"),)))),
        AdapterSpec("reranker-model", tuple(filter(None, (configured.get("reranker_model"),)))),
        AdapterSpec("llmlingua-model", tuple(filter(None, (configured.get("llmlingua_model"),)))),
        AdapterSpec("whisper-python", tuple(filter(None, (configured.get("whisper_python"), os.getenv("TOKEN_FORGE_WHISPER_PYTHON"))))),
        AdapterSpec("whisper-model", tuple(filter(None, (configured.get("whisper_model"), os.getenv("TOKEN_FORGE_WHISPER_MODEL"))))),
    )


def probe_all(
    specs: Iterable[AdapterSpec] | None = None,
    configured: Mapping[str, str] | None = None,
) -> tuple[AdapterStatus, ...]:
    selected = tuple(specs) if specs is not None else default_adapter_specs(configured)
    return tuple(probe_adapter(spec) for spec in selected)
