from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .cost import estimate_tokens
from .pipeline import build_text_pack, canonicalize_text


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    source = str(case["source"])
    safety_class = str(case.get("safety_class", "text"))
    high_risk = safety_class in {"code", "contract", "table", "financial", "command", "security"}
    result = build_text_pack(
        source,
        str(case["query"]),
        int(case["budget_tokens"]),
        safety_class=safety_class,
    )
    declared = tuple(str(value) for value in case.get("protected", ()))
    declared_recall = 1.0 if not declared else sum(value in result.text for value in declared) / len(declared)
    input_tokens = estimate_tokens(source)
    canonical = canonicalize_text(source)
    canonical_tokens = estimate_tokens(canonical)
    canonical_recall = 1.0 if not declared else sum(value in canonical for value in declared) / len(declared)
    profiles = {
        "raw": {
            "status": "measured-estimate",
            "tokens_estimated": input_tokens,
            "reduction_ratio": 0.0,
            "protected_recall": 1.0,
        },
        "canonical": {
            "status": "not-eligible" if high_risk else "measured-estimate",
            "tokens_estimated": input_tokens if high_risk else canonical_tokens,
            "reduction_ratio": 0.0 if high_risk else (max(0.0, 1 - canonical_tokens / input_tokens) if input_tokens else 0.0),
            "protected_recall": 1.0 if high_risk else canonical_recall,
        },
        "retrieved": {
            "status": "measured-estimate",
            "tokens_estimated": result.final_tokens,
            "reduction_ratio": result.reduction_ratio,
            "protected_recall": declared_recall,
        },
        "learned-compression": {
            "status": "not-eligible" if high_risk else "unavailable",
            "tokens_estimated": None,
            "reduction_ratio": None,
            "protected_recall": None,
            "reason": (
                f"Safety class {safety_class!r} is excluded from learned compression."
                if high_risk
                else "No evaluated LLMLingua-2 environment is configured; no result is fabricated."
            ),
        },
    }
    return {
        "id": str(case["id"]),
        "mode": result.mode,
        "input_tokens_estimated": result.input_tokens,
        "final_tokens_estimated": result.final_tokens,
        "reduction_ratio": result.reduction_ratio,
        "protected_recall": declared_recall,
        "budget_conflict": result.budget_conflict,
        "profiles": profiles,
    }


def run_manifest(manifest_path: Path, output_dir: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases: list[dict[str, Any]] = []
    for raw in manifest.get("cases", []):
        case = dict(raw)
        if "source_file" in case:
            source_path = manifest_path.parent / str(case.pop("source_file"))
            case["source"] = source_path.read_text(encoding="utf-8")
        cases.append(run_case(case))

    summary = {
        "schema_version": 1,
        "case_count": len(cases),
        "all_protected_pass": all(case["protected_recall"] == 1.0 for case in cases),
        "cases": cases,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "results.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    return summary
