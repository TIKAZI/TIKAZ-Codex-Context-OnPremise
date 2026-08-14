from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class LocalConfig:
    adapters: dict[str, str] = field(default_factory=dict)
    gpu_serial: bool = True
    allow_remote: bool = False


def load_config(path: Path) -> LocalConfig:
    if not path.is_file():
        return LocalConfig()
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    raw_adapters = data.get("adapters", {})
    raw_runtime = data.get("runtime", {})
    adapters = {
        str(key): str(value)
        for key, value in raw_adapters.items()
        if isinstance(value, str) and value.strip()
    }
    return LocalConfig(
        adapters=adapters,
        gpu_serial=bool(raw_runtime.get("gpu_serial", True)),
        allow_remote=bool(raw_runtime.get("allow_remote", False)),
    )

