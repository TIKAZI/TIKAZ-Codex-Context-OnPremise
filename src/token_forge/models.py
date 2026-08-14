from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SourceProfile:
    source: str
    family: str
    suffix: str
    route: str
    adapter_candidates: tuple[str, ...]
    learned_compression_allowed: bool
    fallback: str = "source"


@dataclass(frozen=True)
class PackResult:
    text: str
    mode: str
    input_tokens: int
    final_tokens: int
    protected_literals: tuple[str, ...]
    protected_recall: float
    reduction_ratio: float
    source_hash: str
    omitted_blocks: tuple[int, ...] = field(default_factory=tuple)
    budget_conflict: bool = False
    cache_key: str = ""
    cache_hit: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
