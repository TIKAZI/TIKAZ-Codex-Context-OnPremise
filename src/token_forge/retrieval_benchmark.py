from __future__ import annotations

import json
import time
from pathlib import Path
from statistics import fmean
from typing import Any, Mapping

from .cost import estimate_tokens
from .model_pipeline import rank_local_chunks
from .retrieval import fuse_and_diversify, query_coverage, retrieval_metrics, select_evidence


def _case_rank(
    case: Mapping[str, Any],
    mode: str,
    adapters: Mapping[str, str],
    timeout_seconds: int,
) -> list[dict[str, object]]:
    chunks = [
        {"id": str(item["id"]), "index": index, "text": str(item["text"])}
        for index, item in enumerate(case["chunks"])
    ]
    if mode == "onpremise":
        return rank_local_chunks(chunks, str(case["query"]), adapters, timeout_seconds=timeout_seconds)
    if mode != "economy":
        raise ValueError("mode must be 'economy' or 'onpremise'")
    return fuse_and_diversify(chunks, str(case["query"]))


def run_retrieval_manifest(
    manifest_path: Path,
    output_dir: Path,
    *,
    mode: str,
    adapters: Mapping[str, str] | None = None,
    timeout_seconds: int = 900,
) -> dict[str, Any]:
    started = time.perf_counter()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    k_values = tuple(int(value) for value in manifest.get("k_values", (1, 3, 5)))
    cases: list[dict[str, Any]] = []
    raw_cases = [dict(item) for item in manifest.get("cases", [])]
    for case_index, raw_case in enumerate(raw_cases):
        case = dict(raw_case)
        chunks = list(case["chunks"])
        relevance = {str(item["id"]): int(item.get("relevance", 0)) for item in chunks}
        ranked = _case_rank(case, mode, adapters or {}, timeout_seconds)
        ranked_ids = [str(item["id"]) for item in ranked]
        metrics = retrieval_metrics(ranked_ids, relevance, k_values=k_values)
        relevant_count = sum(grade > 0 for grade in relevance.values())
        selected_k = min(max(1, relevant_count), len(ranked_ids))
        selected_ids = ranked_ids[:selected_k]
        selected_texts = [
            str(item["text"]) for item in chunks if str(item["id"]) in selected_ids
        ]
        evidence_hits = sum(relevance.get(item_id, 0) > 0 for item_id in selected_ids)
        metrics["evidence_precision"] = evidence_hits / selected_k if selected_k else 1.0
        metrics["query_coverage"] = query_coverage(str(case["query"]), selected_texts)
        dynamic = select_evidence(ranked, str(case["query"]), min_items=1, max_items=5)
        dynamic_ids = [str(item["id"]) for item in dynamic.items]
        dynamic_texts = [
            str(item["text"]) for item in chunks if str(item["id"]) in dynamic_ids
        ]
        source_tokens = estimate_tokens("\n\n".join(str(item["text"]) for item in chunks))
        selected_tokens = estimate_tokens("\n\n".join(dynamic_texts))
        dynamic_hits = sum(relevance.get(item_id, 0) > 0 for item_id in dynamic_ids)
        dynamic_recall = dynamic_hits / relevant_count if relevant_count else 1.0
        dynamic_precision = dynamic_hits / len(dynamic_ids) if dynamic_ids else 1.0
        token_reduction = (
            max(0.0, 1 - selected_tokens / source_tokens) if source_tokens else 0.0
        )
        metrics.update({
            "dynamic_recall": dynamic_recall,
            "dynamic_precision": dynamic_precision,
            "dynamic_facet_coverage": dynamic.facet_coverage,
            "dynamic_selected_count": float(len(dynamic_ids)),
            "selected_token_reduction_estimated": token_reduction,
        })
        cases.append({
            "id": str(case["id"]),
            "mode": mode,
            "query": str(case["query"]),
            "ranked_ids": ranked_ids,
            "relevant_ids": sorted(item_id for item_id, grade in relevance.items() if grade > 0),
            "selection": {
                "status": dynamic.status,
                "selected_ids": dynamic_ids,
                "selected_count": len(dynamic_ids),
                "facet_coverage": dynamic.facet_coverage,
                "confidence": dynamic.confidence,
                "relevant_recall": dynamic_recall,
                "evidence_precision": dynamic_precision,
                "source_tokens_estimated": source_tokens,
                "selected_tokens_estimated": selected_tokens,
                "token_reduction_estimated": token_reduction,
            },
            "metrics": metrics,
        })

    metric_names = sorted({name for case in cases for name in case["metrics"]})
    metrics = {
        name: fmean(float(case["metrics"][name]) for case in cases)
        for name in metric_names
    } if cases else {}
    declared_minimums = manifest.get("minimums_by_mode", {}).get(
        mode, manifest.get("minimums", {})
    )
    minimums = {str(name): float(value) for name, value in declared_minimums.items()}
    gates = {
        name: metrics.get(name, 0.0) >= minimum
        for name, minimum in minimums.items()
    }
    validation = {"gates": gates, "all_required_pass": all(gates.values())}
    summary = {
        "schema_version": 1,
        "measurement": "fixed manifest retrieval ranking; separate from provider token telemetry",
        "mode": mode,
        "case_count": len(cases),
        "elapsed_seconds": round(time.perf_counter() - started, 6),
        "metrics": metrics,
        "minimums": minimums,
        "validation": validation,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    (output_dir / "cases.json").write_text(
        json.dumps(cases, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    lines = [
        f"# Retrieval evidence card — {mode}",
        "",
        f"- Fixed cases: {len(cases)}",
        f"- Required gates passed: {validation['all_required_pass']}",
    ]
    lines.extend(f"- {name}: {value:.4f}" for name, value in metrics.items())
    lines.extend([
        "",
        "These measurements use the declared fixed manifest. They do not establish universal real-world accuracy or downstream answer correctness.",
        "",
    ])
    (output_dir / "evidence-card.md").write_text("\n".join(lines), encoding="utf-8")
    return {**summary, "cases": cases}
