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
            return AdapterStatus(spec.name, True, str(explicit.resolve()))
        located = shutil.which(candidate)
        if located:
            return AdapterStatus(spec.name, True, located)
    return AdapterStatus(spec.name, False, None)


def default_adapter_specs(configured: Mapping[str, str] | None = None) -> tuple[AdapterSpec, ...]:
    configured = configured or {}
    return (
        AdapterSpec("ffmpeg", tuple(filter(None, (configured.get("ffmpeg"), os.getenv("TOKEN_FORGE_FFMPEG"), "ffmpeg", "ffmpeg.cmd")))),
        AdapterSpec("markitdown", ("markitdown",)),
        AdapterSpec("docling", ("docling",)),
        AdapterSpec("mineru", ("mineru",)),
        AdapterSpec("paddleocr", ("paddleocr",)),
        AdapterSpec("defuddle", ("defuddle",)),
        AdapterSpec("playwright", ("playwright",)),
        AdapterSpec("whisper-python", tuple(filter(None, (configured.get("whisper_python"), os.getenv("TOKEN_FORGE_WHISPER_PYTHON"))))),
        AdapterSpec("whisper-model", tuple(filter(None, (configured.get("whisper_model"), os.getenv("TOKEN_FORGE_WHISPER_MODEL"))))),
    )


def probe_all(
    specs: Iterable[AdapterSpec] | None = None,
    configured: Mapping[str, str] | None = None,
) -> tuple[AdapterStatus, ...]:
    selected = tuple(specs) if specs is not None else default_adapter_specs(configured)
    return tuple(probe_adapter(spec) for spec in selected)
