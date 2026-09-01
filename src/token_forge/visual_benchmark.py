from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from .visual import build_visual_evidence, resolve_local_visual_evidence


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _contains(text: str, fact: str) -> bool:
    normalized_text = re.sub(r"\s+", " ", text).strip().casefold()
    normalized_fact = re.sub(r"\s+", " ", fact).strip().casefold()
    return normalized_fact in normalized_text


def run_visual_manifest(
    manifest_path: Path,
    frames_dir: Path,
    output_dir: Path,
    adapters: Mapping[str, str],
    *,
    minimum_vlm_confidence: float = 0.75,
    timeout_seconds: int = 180,
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw_cases = manifest.get("cases") if isinstance(manifest, dict) else None
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("visual benchmark manifest requires non-empty cases")
    case_files: set[str] = set()
    for case in raw_cases:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str):
            raise ValueError("every visual benchmark case requires an id")
        filename = str(case.get("file", ""))
        if not filename or filename in case_files:
            raise ValueError("visual benchmark case files must be unique")
        if Path(filename).name != filename:
            raise ValueError("visual benchmark files must be direct children of frames_dir")
        if not (frames_dir / filename).is_file():
            raise FileNotFoundError(frames_dir / filename)
        facts = case.get("protected_facts")
        if not isinstance(facts, list) or not all(isinstance(fact, str) and fact for fact in facts):
            raise ValueError("protected_facts must be non-empty strings")
        case_files.add(filename)

    image_suffixes = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}
    actual_files = {
        path.name
        for path in frames_dir.iterdir()
        if path.is_file() and path.suffix.casefold() in image_suffixes
    }
    if actual_files != case_files:
        raise ValueError("visual benchmark files must exactly match the manifest")

    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = output_dir / "visual-evidence.json"
    build_visual_evidence(frames_dir, evidence_path, max_selected=len(raw_cases))
    resolved = resolve_local_visual_evidence(
        evidence_path,
        dict(adapters),
        minimum_vlm_confidence=minimum_vlm_confidence,
        timeout_seconds=timeout_seconds,
    )
    frame_by_name = {Path(str(frame["path"])).name: frame for frame in resolved.frames}

    total_facts = 0
    combined_matches = 0
    ocr_matches = 0
    vlm_matches = 0
    type_total = 0
    type_matches = 0
    escalated = 0
    resolved_local = 0
    prompt_eval_count = 0
    runtime_ns = 0
    cases: list[dict[str, Any]] = []
    for raw_case in raw_cases:
        frame = frame_by_name.get(str(raw_case["file"]))
        if frame is None:
            raise ValueError(f"frame missing from evidence: {raw_case['file']}")
        observations = frame.get("observations") if isinstance(frame.get("observations"), list) else []
        ocr_text = "\n".join(
            str(item.get("text", "")) for item in observations
            if isinstance(item, dict) and item.get("kind") == "ocr-text"
        )
        vlm_text = "\n".join(
            str(item.get("text", "")) for item in observations
            if isinstance(item, dict) and item.get("kind") != "ocr-text"
        )
        combined_text = "\n".join((ocr_text, vlm_text))
        facts = [str(fact) for fact in raw_case["protected_facts"]]
        fact_results = [{
            "fact": fact,
            "ocr": _contains(ocr_text, fact),
            "vlm": _contains(vlm_text, fact),
            "combined": _contains(combined_text, fact),
        } for fact in facts]
        total_facts += len(facts)
        ocr_matches += sum(item["ocr"] for item in fact_results)
        vlm_matches += sum(item["vlm"] for item in fact_results)
        combined_matches += sum(item["combined"] for item in fact_results)
        inference = frame.get("local_inference") if isinstance(frame.get("local_inference"), dict) else {}
        expected_type = raw_case.get("expected_frame_type")
        type_match: bool | None = None
        if isinstance(expected_type, str) and expected_type:
            type_total += 1
            type_match = inference.get("frame_type") == expected_type
            type_matches += int(type_match)
        status = str(frame.get("semantic_status", ""))
        escalated += int(status == "needs-codex")
        resolved_local += int(status == "resolved-local")
        prompt_eval_count += int(inference.get("prompt_eval_count", 0) or 0)
        runtime_ns += int(inference.get("total_duration", 0) or 0)
        cases.append({
            "id": raw_case["id"],
            "profile": raw_case.get("profile", "unspecified"),
            "file": raw_case["file"],
            "source_sha256": frame.get("frame_sha256"),
            "semantic_status": status,
            "expected_frame_type": expected_type,
            "actual_frame_type": inference.get("frame_type"),
            "frame_type_match": type_match,
            "facts": fact_results,
            "combined_fact_recall": _ratio(sum(item["combined"] for item in fact_results), len(facts)),
            "ocr_fact_recall": _ratio(sum(item["ocr"] for item in fact_results), len(facts)),
            "vlm_fact_recall": _ratio(sum(item["vlm"] for item in fact_results), len(facts)),
            "model_reported_confidence": inference.get("confidence"),
            "local_prompt_eval_count": inference.get("prompt_eval_count"),
            "local_runtime_seconds": (
                inference.get("total_duration", 0) / 1_000_000_000
                if isinstance(inference.get("total_duration"), int) else None
            ),
        })

    metrics = {
        "case_count": len(cases),
        "protected_fact_count": total_facts,
        "combined_fact_recall": _ratio(combined_matches, total_facts),
        "ocr_fact_recall": _ratio(ocr_matches, total_facts),
        "vlm_fact_recall": _ratio(vlm_matches, total_facts),
        "frame_type_accuracy": _ratio(type_matches, type_total),
        "resolved_local_rate": _ratio(resolved_local, len(cases)),
        "codex_escalation_rate": _ratio(escalated, len(cases)),
        "local_prompt_eval_count": prompt_eval_count,
        "local_runtime_seconds": runtime_ns / 1_000_000_000,
        "codex_image_token_savings": "Pending provider telemetry",
    }
    required_recall = float(manifest.get("minimum_combined_fact_recall", 1.0))
    required_type_accuracy = float(manifest.get("minimum_frame_type_accuracy", 0.0))
    visual_facts_pass = (
        metrics["combined_fact_recall"] is not None
        and metrics["combined_fact_recall"] >= required_recall
    )
    frame_types_pass = (
        required_type_accuracy == 0.0
        if metrics["frame_type_accuracy"] is None
        else metrics["frame_type_accuracy"] >= required_type_accuracy
    )
    summary = {
        "schema_version": 1,
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "fixture_scope": manifest.get("fixture_scope", "fixed declared fixtures"),
        "metrics": metrics,
        "validation": {
            "visual_facts": visual_facts_pass,
            "frame_types": frame_types_pass,
            "all_required_pass": visual_facts_pass and frame_types_pass,
            "minimum_combined_fact_recall": required_recall,
            "minimum_frame_type_accuracy": required_type_accuracy,
        },
        "validated_models": {"vlm": adapters.get("ollama_model")},
        "claim_boundary": (
            "Results apply only to this fixed manifest. OCR/VLM confidence is not accuracy. "
            "Local prompt counts are not Codex image-token telemetry."
        ),
    }
    (output_dir / "cases.json").write_text(
        json.dumps({"schema_version": 1, "cases": cases}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    card = (
        "# Visual benchmark evidence\n\n"
        f"- Cases: {len(cases)}\n"
        f"- Combined protected-fact recall: {metrics['combined_fact_recall']}\n"
        f"- OCR protected-fact recall: {metrics['ocr_fact_recall']}\n"
        f"- VLM protected-fact recall: {metrics['vlm_fact_recall']}\n"
        f"- Frame-type accuracy: {metrics['frame_type_accuracy']}\n"
        f"- Codex escalation rate: {metrics['codex_escalation_rate']}\n"
        "- Codex image-token savings: Pending provider telemetry\n\n"
        f"> {summary['claim_boundary']}\n"
    )
    (output_dir / "evidence-card.md").write_text(card, encoding="utf-8")
    return summary
