from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import quote

from .conversion import convert_source
from .cost import estimate_tokens
from .media import process_local_media
from .model_pipeline import optimize_text_pack
from .pipeline import build_text_pack
from .platform_media import inspect_platform_media
from .web import prepare_web_url


def _literal_recall(expected: tuple[str, ...], actual: str) -> float | None:
    if not expected:
        return None
    return sum(value in actual for value in expected) / len(expected)


def _normalized_literal_recall(expected: tuple[str, ...], actual: str) -> float | None:
    if not expected:
        return None
    normalized_actual = _normalized_text(actual)
    return sum(_normalized_text(value) in normalized_actual for value in expected) / len(expected)


def _edit_distance(expected: list[str] | str, actual: list[str] | str) -> int:
    previous = list(range(len(actual) + 1))
    for index, expected_item in enumerate(expected, start=1):
        current = [index]
        for other_index, actual_item in enumerate(actual, start=1):
            current.append(min(
                current[-1] + 1,
                previous[other_index] + 1,
                previous[other_index - 1] + (expected_item != actual_item),
            ))
        previous = current
    return previous[-1]


def _normalized_text(value: str) -> str:
    value = re.sub(r"\[\d+(?:\.\d+)?-\d+(?:\.\d+)?\]", " ", value)
    value = re.sub(r"\[\d{1,2}:\d{2}(?::\d{2})?\]", " ", value)
    value = re.sub(r"[^\w\u3400-\u9fff]+", " ", value.casefold(), flags=re.UNICODE)
    return " ".join(value.split())


def _character_error_rate(reference: str, actual: str) -> float | None:
    expected = _normalized_text(reference).replace(" ", "")
    observed = _normalized_text(actual).replace(" ", "")
    return _edit_distance(expected, observed) / len(expected) if expected else None


def _word_error_rate(reference: str, actual: str) -> float | None:
    expected = _normalized_text(reference).split()
    observed = _normalized_text(actual).split()
    return _edit_distance(expected, observed) / len(expected) if expected else None


def _text_case(case: dict[str, Any], manifest_dir: Path) -> dict[str, Any]:
    source_path = (manifest_dir / str(case["source_file"])).resolve()
    source = source_path.read_text(encoding="utf-8")
    started = time.perf_counter()
    protected = tuple(str(value) for value in case.get("protected", ()))
    anchors = tuple(str(value) for value in case.get("expected_anchors", ()))
    safety_class = str(case.get("safety_class", "text"))
    result = build_text_pack(
        source,
        str(case["query"]),
        int(case["budget_tokens"]),
        safety_class=safety_class,
        required_literals=(*protected, *anchors),
    )
    protected_recall = _literal_recall(protected, result.text)
    anchor_recall = _literal_recall(anchors, result.text)
    budget_compliant = result.final_tokens <= int(case["budget_tokens"]) and not result.budget_conflict
    budget_conflict_expected = bool(case.get("expect_budget_conflict", False))
    budget_gate_pass = result.budget_conflict if budget_conflict_expected else budget_compliant
    fidelity_pass = all(value in {None, 1.0} for value in (protected_recall, anchor_recall))
    passed = fidelity_pass and budget_gate_pass
    return {
        "id": str(case["id"]),
        "kind": "text-pack",
        "required": bool(case.get("required", True)),
        "status": "passed" if passed else "failed",
        "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "input_bytes": source_path.stat().st_size,
        "input_tokens_estimated": estimate_tokens(source),
        "output_tokens_estimated": result.final_tokens,
        "token_reduction_ratio": result.reduction_ratio,
        "budget_tokens": int(case["budget_tokens"]),
        "budget_compliant": budget_compliant,
        "budget_conflict_expected": budget_conflict_expected,
        "protected_fact_recall": protected_recall,
        "protected_fact_count": len(protected),
        "anchor_recall": anchor_recall,
        "anchor_count": len(anchors),
        "route": result.mode,
        "optimization_profile": {
            "code": "code-context", "table": "table-context"
        }.get(safety_class, "text-context"),
        "route_evidence": result.evidence,
        "runtime_ms": round((time.perf_counter() - started) * 1000),
        "failure_reason": "" if passed else "budget or declared fidelity gate failed",
    }


def _base_file_metrics(case: dict[str, Any], source_path: Path, actual: str) -> dict[str, Any]:
    protected = tuple(str(value) for value in case.get("protected", ()))
    anchors = tuple(str(value) for value in case.get("expected_anchors", ()))
    table_cells = tuple(str(value) for value in case.get("table_cells", ()))
    return {
        "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "input_bytes": source_path.stat().st_size,
        "output_tokens_estimated": estimate_tokens(actual),
        "protected_fact_recall": _literal_recall(protected, actual),
        "protected_fact_count": len(protected),
        "anchor_recall": _literal_recall(anchors, actual),
        "anchor_count": len(anchors),
        "table_cell_recall": _literal_recall(table_cells, actual),
        "table_cell_count": len(table_cells),
    }


def _declared_fidelity_pass(metrics: Mapping[str, Any]) -> bool:
    return all(
        metrics.get(name) in {None, 1.0}
        for name in ("protected_fact_recall", "anchor_recall", "table_cell_recall", "transcript_fact_recall")
    )


def _conversion_case(
    case: dict[str, Any], manifest_dir: Path, output_dir: Path, adapters: Mapping[str, str]
) -> dict[str, Any]:
    source_path = (manifest_dir / str(case["source_file"])).resolve()
    artifact_dir = output_dir / "artifacts" / str(case["id"])
    result = convert_source(
        source_path,
        artifact_dir,
        adapters,
        requested_adapter=str(case.get("adapter", "auto")),
        timeout_seconds=int(case.get("timeout_seconds", 600)),
        allow_remote=False,
    )
    actual = ""
    if result.output_path and Path(result.output_path).is_file():
        actual = Path(result.output_path).read_text(encoding="utf-8", errors="replace")
    metrics = _base_file_metrics(case, source_path, actual)
    reference_file = case.get("reference_file")
    character_error_rate = None
    if reference_file:
        reference = (manifest_dir / str(reference_file)).read_text(encoding="utf-8")
        character_error_rate = _character_error_rate(reference, actual)
    max_character_error_rate = float(case.get("max_character_error_rate", 0.05))
    error_rate_pass = character_error_rate is None or character_error_rate <= max_character_error_rate
    expected_route = case.get("expected_route")
    route_correct = expected_route is None or result.adapter == expected_route
    passed = bool(result.success) and route_correct and error_rate_pass and _declared_fidelity_pass(metrics)
    return {
        "id": str(case["id"]), "kind": "conversion", "required": bool(case.get("required", True)),
        "status": "passed" if passed else "failed", "route": result.adapter,
        "route_correct": route_correct, "verification_level": result.verification_level,
        "runtime_ms": result.elapsed_ms, "token_reduction_ratio": None,
        "character_error_rate": character_error_rate,
        "max_character_error_rate": max_character_error_rate if reference_file else None,
        "failure_reason": "" if passed else (
            "declared fidelity, error-rate, or route gate failed" if result.success else result.status
        ),
        **metrics,
    }


def _model_case(
    case: dict[str, Any], manifest_dir: Path, adapters: Mapping[str, str]
) -> dict[str, Any]:
    source_path = (manifest_dir / str(case["source_file"])).resolve()
    source = source_path.read_text(encoding="utf-8")
    started = time.perf_counter()
    result = optimize_text_pack(
        source, str(case["query"]), int(case["budget_tokens"]), adapters,
        safety_class=str(case.get("safety_class", "text")),
        timeout_seconds=int(case.get("timeout_seconds", 900)),
    )
    protected = tuple(str(value) for value in case.get("protected", ()))
    anchors = tuple(str(value) for value in case.get("expected_anchors", ()))
    protected_recall = _literal_recall(protected, result.text)
    anchor_recall = _literal_recall(anchors, result.text)
    budget_compliant = result.final_tokens <= int(case["budget_tokens"]) and not result.budget_conflict
    passed = budget_compliant and all(value in {None, 1.0} for value in (protected_recall, anchor_recall))
    return {
        "id": str(case["id"]), "kind": "model-pack", "required": bool(case.get("required", True)),
        "status": "passed" if passed else "failed", "route": result.mode,
        "optimization_profile": "model-text-context",
        "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "input_bytes": source_path.stat().st_size,
        "input_tokens_estimated": result.input_tokens,
        "output_tokens_estimated": result.final_tokens,
        "token_reduction_ratio": result.reduction_ratio,
        "budget_tokens": int(case["budget_tokens"]), "budget_compliant": budget_compliant,
        "protected_fact_recall": protected_recall, "protected_fact_count": len(protected),
        "anchor_recall": anchor_recall, "anchor_count": len(anchors),
        "runtime_ms": round((time.perf_counter() - started) * 1000),
        "failure_reason": "" if passed else result.fallback_reason or "model fidelity gate failed",
    }


class _SilentHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


@contextmanager
def _fixture_server(root: Path):
    handler = partial(_SilentHandler, directory=str(root))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _web_case(
    case: dict[str, Any], manifest_dir: Path, output_dir: Path, adapters: Mapping[str, str]
) -> dict[str, Any]:
    relative = Path(str(case["source_file"]))
    source_path = (manifest_dir / relative).resolve()
    artifact_dir = output_dir / "artifacts" / str(case["id"])
    with _fixture_server(manifest_dir) as base_url:
        url = f"{base_url}/{quote(relative.as_posix())}"
        result = prepare_web_url(
            url, artifact_dir, adapters, timeout_seconds=int(case.get("timeout_seconds", 180))
        )
    output_path = (result.conversion or {}).get("output_path")
    actual = Path(str(output_path)).read_text(encoding="utf-8", errors="replace") if output_path and Path(str(output_path)).is_file() else ""
    metrics = _base_file_metrics(case, source_path, actual)
    passed = bool(result.success) and _declared_fidelity_pass(metrics)
    return {
        "id": str(case["id"]), "kind": "web-local", "required": bool(case.get("required", True)),
        "status": "passed" if passed else "failed", "route": (result.conversion or {}).get("adapter"),
        "runtime_ms": result.elapsed_ms, "token_reduction_ratio": None,
        "failure_reason": "" if passed else result.status,
        **metrics,
    }


def _media_case(
    case: dict[str, Any], manifest_dir: Path, output_dir: Path, adapters: Mapping[str, str]
) -> dict[str, Any]:
    source_path = (manifest_dir / str(case["source_file"])).resolve()
    artifact_dir = output_dir / "artifacts" / str(case["id"])
    result = process_local_media(
        source_path, artifact_dir, adapters,
        language=str(case.get("language", "zh")),
        timeout_seconds=int(case.get("timeout_seconds", 900)),
    )
    transcript = ""
    if result.transcript_path and Path(result.transcript_path).is_file():
        transcript = Path(result.transcript_path).read_text(encoding="utf-8", errors="replace")
    facts = tuple(str(value) for value in case.get("transcript_facts", ()))
    transcript_recall = _normalized_literal_recall(facts, transcript)
    transcript_reference = case.get("transcript_reference_file")
    word_error_rate = None
    if transcript_reference:
        reference = (manifest_dir / str(transcript_reference)).read_text(encoding="utf-8")
        word_error_rate = _word_error_rate(reference, transcript)
    max_word_error_rate = float(case.get("max_word_error_rate", 0.35))
    keyframes = []
    if result.keyframes_dir and Path(result.keyframes_dir).is_dir():
        keyframes = [path for path in Path(result.keyframes_dir).iterdir() if path.is_file()]
    minimum_keyframes = int(case.get("minimum_keyframes", 0))
    word_error_pass = word_error_rate is None or word_error_rate <= max_word_error_rate
    passed = (
        bool(result.success) and transcript_recall in {None, 1.0}
        and word_error_pass and len(keyframes) >= minimum_keyframes
    )
    return {
        "id": str(case["id"]), "kind": "media", "required": bool(case.get("required", True)),
        "status": "passed" if passed else "failed", "route": "ffmpeg+faster-whisper+scenedetect",
        "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "input_bytes": source_path.stat().st_size,
        "output_tokens_estimated": estimate_tokens(transcript) if transcript else None,
        "token_reduction_ratio": None,
        "protected_fact_recall": None, "protected_fact_count": 0,
        "anchor_recall": None, "anchor_count": 0,
        "transcript_fact_recall": transcript_recall, "transcript_fact_count": len(facts),
        "word_error_rate": word_error_rate,
        "max_word_error_rate": max_word_error_rate if transcript_reference else None,
        "keyframe_count": len(keyframes), "minimum_keyframes": minimum_keyframes,
        "visual_understanding": "Pending",
        "runtime_ms": result.elapsed_ms,
        "failure_reason": "" if passed else (
            "transcript, WER, or keyframe gate failed" if result.success else result.status
        ),
    }


def _platform_case(
    case: dict[str, Any], output_dir: Path, adapters: Mapping[str, str]
) -> dict[str, Any]:
    artifact_dir = output_dir / "artifacts" / str(case["id"])
    result = inspect_platform_media(
        str(case["url"]), artifact_dir, adapters,
        subtitles=bool(case.get("subtitles", True)),
        download=False,
        timeout_seconds=int(case.get("timeout_seconds", 180)),
    )
    return {
        "id": str(case["id"]), "kind": "platform-media",
        "required": bool(case.get("required", False)),
        "status": "passed" if result.success else "failed",
        "route": "yt-dlp-metadata",
        "protected_fact_recall": None, "protected_fact_count": 0,
        "anchor_recall": None, "anchor_count": 0,
        "token_reduction_ratio": None, "runtime_ms": result.elapsed_ms,
        "subtitles_available": bool(result.subtitles_path),
        "failure_reason": "" if result.success else result.status,
    }


def _pending_case(case: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "id": str(case["id"]),
        "kind": str(case["kind"]),
        "required": bool(case.get("required", True)),
        "status": "pending",
        "protected_fact_recall": None,
        "protected_fact_count": 0,
        "anchor_recall": None,
        "anchor_count": 0,
        "runtime_ms": 0,
        "failure_reason": reason,
    }


def _aggregate(cases: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    status_counts = {
        status: sum(case["status"] == status for case in cases)
        for status in ("passed", "failed", "pending")
    }
    def literal_metric(count_key: str, recall_key: str) -> tuple[int, int, float | None]:
        eligible = [case for case in cases if int(case.get(count_key, 0)) > 0]
        denominator = sum(int(case[count_key]) for case in eligible)
        numerator = sum(float(case[recall_key]) * int(case[count_key]) for case in eligible)
        return len(eligible), denominator, numerator / denominator if denominator else None

    protected_case_count, protected_denominator, protected_recall = literal_metric(
        "protected_fact_count", "protected_fact_recall"
    )
    anchor_case_count, anchor_denominator, anchor_recall = literal_metric("anchor_count", "anchor_recall")
    table_case_count, table_denominator, table_recall = literal_metric("table_cell_count", "table_cell_recall")
    transcript_case_count, transcript_denominator, transcript_recall = literal_metric(
        "transcript_fact_count", "transcript_fact_recall"
    )
    cer_cases = [case for case in cases if case.get("character_error_rate") is not None]
    wer_cases = [case for case in cases if case.get("word_error_rate") is not None]
    measured_efficiency = [
        case for case in cases if case.get("token_reduction_ratio") is not None
    ]
    comparable_tokens = [
        case for case in measured_efficiency
        if case.get("input_tokens_estimated") is not None
        and case.get("output_tokens_estimated") is not None
    ]
    profiles: dict[str, dict[str, Any]] = {}
    for profile in sorted({str(case.get("optimization_profile", "unclassified")) for case in measured_efficiency}):
        selected = [
            case for case in measured_efficiency
            if str(case.get("optimization_profile", "unclassified")) == profile
        ]
        selected_tokens = [
            case for case in selected
            if case.get("input_tokens_estimated") is not None
            and case.get("output_tokens_estimated") is not None
        ]
        total_input = sum(int(case["input_tokens_estimated"]) for case in selected_tokens)
        total_output = sum(int(case["output_tokens_estimated"]) for case in selected_tokens)
        profiles[profile] = {
            "case_count": len(selected),
            "mean_token_reduction_ratio": (
                sum(float(case["token_reduction_ratio"]) for case in selected) / len(selected)
                if selected else None
            ),
            "weighted_token_reduction_ratio": (
                1 - total_output / total_input if total_input else None
            ),
        }
    fidelity = {
        "protected_fact_cases": protected_case_count,
        "protected_fact_denominator": protected_denominator,
        "protected_fact_recall": protected_recall,
        "anchor_cases": anchor_case_count,
        "anchor_denominator": anchor_denominator,
        "anchor_recall": anchor_recall,
        "table_cell_cases": table_case_count,
        "table_cell_denominator": table_denominator,
        "table_cell_recall": table_recall,
        "character_error_rate_cases": len(cer_cases),
        "mean_character_error_rate": (
            sum(float(case["character_error_rate"]) for case in cer_cases) / len(cer_cases)
            if cer_cases else None
        ),
    }
    efficiency = {
        "measured_cases": len(measured_efficiency),
        "mean_token_reduction_ratio": (
            sum(float(case["token_reduction_ratio"]) for case in measured_efficiency)
            / len(measured_efficiency)
            if measured_efficiency else None
        ),
        "weighted_token_reduction_ratio": (
            1 - sum(int(case["output_tokens_estimated"]) for case in comparable_tokens)
            / sum(int(case["input_tokens_estimated"]) for case in comparable_tokens)
            if comparable_tokens and sum(int(case["input_tokens_estimated"]) for case in comparable_tokens)
            else None
        ),
        "profiles": profiles,
        "measurement": "deterministic token estimate; not provider telemetry",
    }
    multimodal = {
        "transcript_cases": transcript_case_count,
        "transcript_fact_denominator": transcript_denominator,
        "transcript_fact_recall": transcript_recall,
        "media_cases": sum(case.get("kind") == "media" for case in cases),
        "visual_understanding": "Pending",
        "word_error_rate_cases": len(wer_cases),
        "mean_word_error_rate": (
            sum(float(case["word_error_rate"]) for case in wer_cases) / len(wer_cases)
            if wer_cases else None
        ),
        "note": "keyframe extraction is measured separately and is not evidence of visual understanding",
    }
    return status_counts, {"efficiency": efficiency, "fidelity": fidelity, "multimodal": multimodal}


def _evidence_card(summary: dict[str, Any], cases: list[dict[str, Any]]) -> str:
    efficiency = summary.get("efficiency", {})
    weighted = efficiency.get("weighted_token_reduction_ratio")
    lines = [
        f"# Acceptance evidence: {summary['suite_id']}",
        "",
        "> Token counts are deterministic estimates, not provider telemetry.",
        "",
        f"- Cases: {summary['case_count']}",
        f"- Passed: {summary['status_counts']['passed']}",
        f"- Failed: {summary['status_counts']['failed']}",
        f"- Pending: {summary['status_counts']['pending']}",
        f"- Required gate: {'PASS' if summary['all_required_pass'] else 'FAIL'}",
        f"- Weighted context reduction: {'Pending' if weighted is None else f'{float(weighted):.2%}'}",
        "- Provider token telemetry: Pending",
    ]
    profiles = efficiency.get("profiles", {})
    if profiles:
        lines.extend([
            "", "## Efficiency profiles", "",
            "| Profile | Cases | Macro mean | Token-weighted reduction |",
            "|---|---:|---:|---:|",
        ])
        for name, profile in profiles.items():
            mean = profile.get("mean_token_reduction_ratio")
            profile_weighted = profile.get("weighted_token_reduction_ratio")
            lines.append(
                f"| {name} | {profile.get('case_count', 0)} | "
                f"{'N/A' if mean is None else f'{float(mean):.2%}'} | "
                f"{'N/A' if profile_weighted is None else f'{float(profile_weighted):.2%}'} |"
            )
    lines.extend([
        "", "## Cases", "",
        "| Case | Kind | Status | Token reduction | Protected recall | Anchor recall | Runtime |",
        "|---|---|---:|---:|---:|---:|---:|",
    ])
    for case in cases:
        reduction = case.get("token_reduction_ratio")
        protected = case.get("protected_fact_recall")
        anchors = case.get("anchor_recall")
        lines.append(
            "| {id} | {kind} | {status} | {reduction} | {protected} | {anchors} | {runtime} ms |".format(
                id=case["id"], kind=case["kind"], status=case["status"],
                reduction="Pending" if reduction is None else f"{float(reduction):.1%}",
                protected="N/A" if protected is None else f"{float(protected):.1%}",
                anchors="N/A" if anchors is None else f"{float(anchors):.1%}",
                runtime=case.get("runtime_ms", 0),
            )
        )
    failures = [case for case in cases if case["status"] != "passed"]
    if failures:
        lines.extend(["", "## Failures and pending evidence", ""])
        lines.extend(f"- `{case['id']}`: {case.get('failure_reason') or case['status']}" for case in failures)
    return "\n".join(lines) + "\n"


def run_acceptance_manifest(
    manifest_path: Path,
    output_dir: Path,
    adapters: Mapping[str, str],
    *,
    allow_network: bool = False,
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValueError("unsupported acceptance manifest schema_version")
    raw_cases = list(manifest.get("cases", ()))
    ids = [str(case.get("id", "")) for case in raw_cases]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate case id")

    cases: list[dict[str, Any]] = []
    for raw in raw_cases:
        case = dict(raw)
        kind = str(case.get("kind", ""))
        if kind == "text-pack":
            cases.append(_text_case(case, manifest_path.parent))
        elif kind == "conversion":
            cases.append(_conversion_case(case, manifest_path.parent, output_dir, adapters))
        elif kind == "model-pack":
            cases.append(_model_case(case, manifest_path.parent, adapters))
        elif kind == "web-local":
            cases.append(_web_case(case, manifest_path.parent, output_dir, adapters))
        elif kind == "media":
            cases.append(_media_case(case, manifest_path.parent, output_dir, adapters))
        elif kind == "platform-media" and not allow_network:
            cases.append(_pending_case(case, "network benchmark disabled; run separately with explicit permission"))
        elif kind == "platform-media":
            cases.append(_platform_case(case, output_dir, adapters))
        else:
            cases.append(_pending_case(case, f"benchmark kind not implemented: {kind}"))

    status_counts, metrics = _aggregate(cases)
    required_cases = [case for case in cases if case.get("required", True)]
    required_status_counts, required_metrics = _aggregate(required_cases)
    all_required_pass = all(
        case["status"] == "passed" for case in cases if case.get("required", True)
    )
    summary = {
        "schema_version": 1,
        "suite_id": str(manifest.get("suite_id", manifest_path.stem)),
        "case_count": len(cases),
        "status_counts": status_counts,
        "all_required_pass": all_required_pass,
        "provider_token_telemetry": "Pending",
        "required": {
            "case_count": len(required_cases),
            "status_counts": required_status_counts,
            **required_metrics,
        },
        **metrics,
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
    (output_dir / "evidence-card.md").write_text(_evidence_card(summary, cases), encoding="utf-8")
    return summary
