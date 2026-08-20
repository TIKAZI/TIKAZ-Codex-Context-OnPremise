from __future__ import annotations

import hashlib
import json
import math
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .conversion import _run_process
from .cost import estimate_tokens
from .pipeline import build_text_pack
from .protection import extract_protected_literals, protected_recall


HIGH_RISK = {"code", "contract", "table", "financial", "command", "security"}


@dataclass(frozen=True)
class ModelPackResult:
    text: str
    mode: str
    input_tokens: int
    final_tokens: int
    protected_literals: tuple[str, ...]
    protected_recall: float
    reduction_ratio: float
    source_hash: str
    chunk_ids: tuple[str, ...] = field(default_factory=tuple)
    fallback_reason: str = ""
    budget_conflict: bool = False
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _chunks(source: str) -> list[dict[str, object]]:
    blocks = [part.strip() for part in source.replace("\r\n", "\n").split("\n\n") if part.strip()]
    output: list[dict[str, object]] = []
    for index, text in enumerate(blocks):
        digest = hashlib.sha256(f"{index}\0{text}".encode("utf-8")).hexdigest()[:16]
        output.append({"id": digest, "index": index, "text": text})
    return output


def _run_helper(python: str, script: Path, payload: dict[str, object], timeout: int) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="token-forge-model-") as temp:
        root = Path(temp)
        request = root / "request.json"
        response = root / "response.json"
        request.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        outcome = _run_process(
            [python, str(script), "--input", str(request), "--output", str(response)],
            timeout,
            {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"},
        )
        if outcome.returncode != 0:
            error = outcome.stderr.strip() or outcome.stdout.strip() or f"helper exited {outcome.returncode}"
            raise RuntimeError(error[-2000:])
        if not response.is_file():
            raise RuntimeError("model helper did not write a response")
        data = json.loads(response.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise RuntimeError("model helper response must be an object")
        return data


def _fallback(source: str, query: str, budget: int, safety_class: str, reason: str) -> ModelPackResult:
    result = build_text_pack(source, query, budget, safety_class=safety_class)
    mode = (
        result.mode
        if result.mode in {"safety-pass-through", "code-sliced", "table-aggregated"}
        else "deterministic-fallback"
    )
    return ModelPackResult(
        text=result.text,
        mode=mode,
        input_tokens=result.input_tokens,
        final_tokens=result.final_tokens,
        protected_literals=result.protected_literals,
        protected_recall=result.protected_recall,
        reduction_ratio=result.reduction_ratio,
        source_hash=result.source_hash,
        fallback_reason=reason,
        budget_conflict=result.budget_conflict,
        evidence=result.evidence,
    )


def _write_result(output_dir: Path, result: ModelPackResult) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "context.md").write_text(result.text, encoding="utf-8")
    (output_dir / "model-ledger.json").write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def optimize_text_pack(
    source: str,
    query: str,
    budget_tokens: int,
    adapters: Mapping[str, str],
    *,
    safety_class: str = "text",
    output_dir: Path | None = None,
    timeout_seconds: int = 900,
) -> ModelPackResult:
    if budget_tokens <= 0:
        raise ValueError("budget_tokens must be positive")
    if safety_class in HIGH_RISK:
        result = _fallback(source, query, budget_tokens, safety_class, "learned models excluded for high-risk material")
        if output_dir is not None:
            _write_result(output_dir, result)
        return result

    required = ("retrieval_python", "embedding_model", "reranker_model")
    missing = [name for name in required if not adapters.get(name)]
    if missing:
        result = _fallback(source, query, budget_tokens, safety_class, f"missing adapters: {', '.join(missing)}")
        if output_dir is not None:
            _write_result(output_dir, result)
        return result

    input_tokens = estimate_tokens(source)
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    protected = extract_protected_literals(source)
    chunks = _chunks(source)
    script_root = Path(__file__).resolve().parents[2] / "scripts"
    try:
        retrieval = _run_helper(
            adapters["retrieval_python"],
            script_root / "retrieve_local.py",
            {
                "query": query,
                "chunks": chunks,
                "embedding_model": adapters["embedding_model"],
                "reranker_model": adapters["reranker_model"],
            },
            timeout_seconds,
        )
        ranked = retrieval.get("ranked")
        if not isinstance(ranked, list):
            raise RuntimeError("retrieval helper omitted ranked chunks")

        by_index = {int(chunk["index"]): chunk for chunk in chunks}
        mandatory = {
            int(chunk["index"])
            for chunk in chunks
            if any(value in str(chunk["text"]) for value in protected)
        }
        ordered = list(sorted(mandatory))
        for item in ranked:
            index = int(item["index"])
            expected = by_index.get(index)
            if expected is None or str(item.get("id")) != expected["id"]:
                raise RuntimeError("retrieval helper returned an invalid chunk identity")
            if index not in ordered:
                ordered.append(index)

        selection_budget = max(budget_tokens, math.ceil(budget_tokens * 1.25))
        selected: list[int] = list(sorted(mandatory))
        for index in ordered:
            if index in selected:
                continue
            proposal = "\n\n".join(str(by_index[value]["text"]) for value in sorted(selected + [index]))
            if estimate_tokens(proposal) <= selection_budget:
                selected.append(index)
        if not selected and ordered:
            selected.append(ordered[0])
        selected.sort()
        selected_text = "\n\n".join(str(by_index[index]["text"]) for index in selected)

        final_text = selected_text
        mode = "model-retrieved"
        fallback_reason = ""
        if estimate_tokens(selected_text) > budget_tokens:
            compression_required = ("llmlingua_python", "llmlingua_model")
            compression_missing = [name for name in compression_required if not adapters.get(name)]
            if compression_missing:
                raise RuntimeError(f"missing adapters: {', '.join(compression_missing)}")
            mandatory_text = "\n\n".join(
                str(by_index[index]["text"]) for index in selected if index in mandatory
            )
            compressible = [index for index in selected if index not in mandatory]
            remaining_budget = budget_tokens - estimate_tokens(mandatory_text) - 1
            if remaining_budget <= 0 or not compressible:
                raise RuntimeError("protected blocks consume the requested token budget")
            compressible_text = "\n\n".join(
                str(by_index[index]["text"]) for index in compressible
            )
            compressed = _run_helper(
                adapters["llmlingua_python"],
                script_root / "compress_local.py",
                {
                    "context": [compressible_text],
                    "question": query,
                    "model": adapters["llmlingua_model"],
                    "target_token": max(1, math.floor(remaining_budget * 0.55)),
                },
                timeout_seconds,
            )
            compressed_text = str(compressed.get("compressed_prompt", "")).strip()
            rendered: list[str] = []
            compressed_added = False
            for index in selected:
                if index in mandatory:
                    rendered.append(str(by_index[index]["text"]))
                elif not compressed_added:
                    rendered.append(compressed_text)
                    compressed_added = True
            candidate = "\n\n".join(value for value in rendered if value).strip()
            recall = protected_recall(protected, candidate)
            if recall < 1.0:
                raise RuntimeError(f"protected literal recall after compression was {recall:.3f}")
            if not compressed_text:
                raise RuntimeError("learned compressor returned empty text")
            if estimate_tokens(candidate) > budget_tokens:
                raise RuntimeError("learned compressor exceeded the requested token budget")
            final_text = candidate
            mode = "learned-compressed"

        final_tokens = estimate_tokens(final_text)
        result = ModelPackResult(
            text=final_text,
            mode=mode,
            input_tokens=input_tokens,
            final_tokens=final_tokens,
            protected_literals=protected,
            protected_recall=protected_recall(protected, final_text),
            reduction_ratio=max(0.0, 1 - final_tokens / input_tokens) if input_tokens else 0.0,
            source_hash=source_hash,
            chunk_ids=tuple(str(by_index[index]["id"]) for index in selected),
            fallback_reason=fallback_reason,
        )
    except (KeyError, TypeError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        result = _fallback(source, query, budget_tokens, safety_class, str(error))

    if output_dir is not None:
        _write_result(output_dir, result)
    return result
