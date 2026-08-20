from __future__ import annotations

import hashlib
import json
import re
from dataclasses import replace
from pathlib import Path
from typing import Any

from .cost import estimate_tokens
from .models import PackResult
from .protection import extract_protected_literals, protected_recall


def _blocks(text: str) -> list[str]:
    return [block.strip() for block in re.split(r"\r?\n\s*\r?\n", text) if block.strip()]


def _dedupe(blocks: list[str]) -> list[tuple[int, str]]:
    seen: set[str] = set()
    output: list[tuple[int, str]] = []
    for index, block in enumerate(blocks):
        normalized = re.sub(r"\s+", " ", block).strip().casefold()
        if normalized not in seen:
            seen.add(normalized)
            output.append((index, block))
    return output


def _query_terms(query: str) -> set[str]:
    return {part.casefold() for part in re.findall(r"[A-Za-z0-9_\-]+|[\u3400-\u9fff]+", query) if len(part) > 1}


def _score(block: str, query_terms: set[str]) -> int:
    lowered = block.casefold()
    return sum(lowered.count(term) for term in query_terms)


def _render(blocks: list[str]) -> str:
    return "\n\n".join(blocks).strip()


def canonicalize_text(source: str) -> str:
    """Remove exact normalized duplicate blocks without semantic rewriting."""
    return _render([block for _, block in _dedupe(_blocks(source))])


def _write_result(output_dir: Path, result: PackResult) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "context.md").write_text(result.text, encoding="utf-8")
    (output_dir / "ledger.json").write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _cache_key(source_hash: str, adapter: str, adapter_version: str, config: dict[str, Any]) -> str:
    payload = {
        "source_hash": source_hash,
        "adapter": adapter,
        "adapter_version": adapter_version,
        "config": config,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _read_cache(cache_dir: Path, key: str) -> PackResult | None:
    path = cache_dir / f"{key}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        data["protected_literals"] = tuple(data.get("protected_literals", ()))
        data["omitted_blocks"] = tuple(data.get("omitted_blocks", ()))
        cached = PackResult(**data)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None
    if cached.cache_key != key:
        return None
    return replace(cached, cache_hit=True)


def _write_cache(cache_dir: Path, result: PackResult) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / f"{result.cache_key}.json"
    temporary = cache_dir / f".{result.cache_key}.tmp"
    temporary.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(target)


def build_text_pack(
    source: str,
    query: str,
    budget_tokens: int,
    output_dir: Path | None = None,
    *,
    safety_class: str = "text",
    cache_dir: Path | None = None,
    adapter: str = "text-pack",
    adapter_version: str = "1",
) -> PackResult:
    if budget_tokens <= 0:
        raise ValueError("budget_tokens must be positive")

    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    effective_config = {
        "query": query,
        "budget_tokens": budget_tokens,
        "safety_class": safety_class,
    }
    cache_key = _cache_key(source_hash, adapter, adapter_version, effective_config)
    if cache_dir is not None:
        cached = _read_cache(cache_dir, cache_key)
        if cached is not None:
            if output_dir is not None:
                _write_result(output_dir, cached)
            return cached

    input_tokens = estimate_tokens(source)
    protected = extract_protected_literals(source)

    if safety_class in {"code", "contract", "table", "financial", "command", "security"}:
        result = PackResult(
            text=source,
            mode="safety-pass-through",
            input_tokens=input_tokens,
            final_tokens=input_tokens,
            protected_literals=protected,
            protected_recall=1.0,
            reduction_ratio=0.0,
            source_hash=source_hash,
            budget_conflict=input_tokens > budget_tokens,
            cache_key=cache_key,
        )
        if cache_dir is not None:
            _write_cache(cache_dir, result)
        if output_dir is not None:
            _write_result(output_dir, result)
        return result

    if input_tokens <= budget_tokens or input_tokens <= 32:
        result = PackResult(
            text=source,
            mode="pass-through",
            input_tokens=input_tokens,
            final_tokens=input_tokens,
            protected_literals=protected,
            protected_recall=1.0,
            reduction_ratio=0.0,
            source_hash=source_hash,
            cache_key=cache_key,
        )
        if cache_dir is not None:
            _write_cache(cache_dir, result)
        if output_dir is not None:
            _write_result(output_dir, result)
        return result

    original_blocks = _blocks(source)
    unique_blocks = _dedupe(original_blocks)
    query_terms = _query_terms(query)

    mandatory: list[tuple[int, str]] = []
    candidates: list[tuple[int, str]] = []
    for item in unique_blocks:
        if any(value in item[1] for value in protected):
            mandatory.append(item)
        else:
            candidates.append(item)

    selected = list(mandatory)
    selected_ids = {index for index, _ in selected}
    mandatory_text = _render([block for _, block in sorted(selected)])
    if estimate_tokens(mandatory_text) > budget_tokens:
        result = PackResult(
            text=source,
            mode="budget-conflict",
            input_tokens=input_tokens,
            final_tokens=input_tokens,
            protected_literals=protected,
            protected_recall=1.0,
            reduction_ratio=0.0,
            source_hash=source_hash,
            budget_conflict=True,
            cache_key=cache_key,
        )
        if cache_dir is not None:
            _write_cache(cache_dir, result)
        if output_dir is not None:
            _write_result(output_dir, result)
        return result

    ranked = sorted(candidates, key=lambda item: (-_score(item[1], query_terms), item[0]))
    for index, block in ranked:
        if _score(block, query_terms) <= 0 and selected:
            continue
        proposal = _render([value for _, value in sorted(selected + [(index, block)])])
        if estimate_tokens(proposal) <= budget_tokens:
            selected.append((index, block))
            selected_ids.add(index)

    if not selected and unique_blocks:
        selected.append(unique_blocks[0])
        selected_ids.add(unique_blocks[0][0])

    selected_text = _render([block for _, block in sorted(selected)])
    final_tokens = estimate_tokens(selected_text)
    recall = protected_recall(protected, selected_text)
    mode = "selected" if recall == 1.0 and final_tokens <= budget_tokens else "budget-conflict"
    if mode == "budget-conflict":
        selected_text = source
        final_tokens = input_tokens

    omitted = tuple(index for index in range(len(original_blocks)) if index not in selected_ids)
    reduction = max(0.0, 1 - (final_tokens / input_tokens)) if input_tokens else 0.0
    result = PackResult(
        text=selected_text,
        mode=mode,
        input_tokens=input_tokens,
        final_tokens=final_tokens,
        protected_literals=protected,
        protected_recall=protected_recall(protected, selected_text),
        reduction_ratio=reduction,
        source_hash=source_hash,
        omitted_blocks=omitted,
        budget_conflict=mode == "budget-conflict",
        cache_key=cache_key,
    )
    if cache_dir is not None:
        _write_cache(cache_dir, result)
    if output_dir is not None:
        _write_result(output_dir, result)
    return result
