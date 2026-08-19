from __future__ import annotations

import argparse
import json
from pathlib import Path

from .adapters import probe_all
from .benchmark import run_manifest, run_model_manifest
from .config import LocalConfig, load_config
from .conversion import convert_source
from .media import process_local_media
from .model_pipeline import optimize_text_pack
from .platform_media import inspect_platform_media
from .pipeline import build_text_pack
from .router import profile_source
from .web import prepare_web_url


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="token-forge")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="Report optional adapter availability without installing anything")
    doctor.add_argument("--config", type=Path, default=Path(".token-forge.local.toml"))

    profile = sub.add_parser("profile", help="Route a source without processing it")
    profile.add_argument("--input", required=True)
    profile.add_argument("--query", default="")

    convert = sub.add_parser("convert", help="Convert a source into quality-gated canonical Markdown")
    convert.add_argument("--input", required=True, type=Path)
    convert.add_argument("--output", required=True, type=Path)
    convert.add_argument("--config", type=Path, default=Path(".token-forge.local.toml"))
    convert.add_argument("--adapter", choices=("auto", "defuddle", "markitdown", "docling", "mineru"), default="auto")
    convert.add_argument("--timeout", type=int, default=120)

    web = sub.add_parser("web", help="Render a dynamic HTTP(S) page and convert the captured HTML")
    web.add_argument("--url", required=True)
    web.add_argument("--output", required=True, type=Path)
    web.add_argument("--config", type=Path, default=Path(".token-forge.local.toml"))
    web.add_argument("--timeout", type=int, default=120)

    media = sub.add_parser("media", help="Transcribe local audio/video and extract video scene evidence")
    media.add_argument("--input", required=True, type=Path)
    media.add_argument("--output", required=True, type=Path)
    media.add_argument("--config", type=Path, default=Path(".token-forge.local.toml"))
    media.add_argument("--language", default="zh")
    media.add_argument("--timeout", type=int, default=600)

    platform = sub.add_parser("platform-media", help="Inspect platform metadata/subtitles without downloading media")
    platform.add_argument("--url", required=True)
    platform.add_argument("--output", required=True, type=Path)
    platform.add_argument("--config", type=Path, default=Path(".token-forge.local.toml"))
    platform.add_argument("--no-subtitles", action="store_true")
    platform.add_argument("--timeout", type=int, default=120)

    pack = sub.add_parser("pack", help="Build a deterministic text context pack")
    pack.add_argument("--input", required=True, type=Path)
    pack.add_argument("--query", required=True)
    pack.add_argument("--budget", required=True, type=int)
    pack.add_argument("--output", required=True, type=Path)
    pack.add_argument("--cache-dir", type=Path, default=Path(".token-forge/cache"))
    pack.add_argument(
        "--safety-class",
        choices=("auto", "text", "code", "contract", "table", "financial", "command", "security"),
        default="auto",
    )

    optimize = sub.add_parser(
        "optimize", help="Use local retrieval/reranking and guarded prose compression"
    )
    optimize.add_argument("--input", required=True, type=Path)
    optimize.add_argument("--query", required=True)
    optimize.add_argument("--budget", required=True, type=int)
    optimize.add_argument("--output", required=True, type=Path)
    optimize.add_argument("--config", type=Path, default=Path(".token-forge.local.toml"))
    optimize.add_argument(
        "--safety-class",
        choices=("auto", "text", "code", "contract", "table", "financial", "command", "security"),
        default="auto",
    )
    optimize.add_argument("--timeout", type=int, default=900)

    benchmark = sub.add_parser("benchmark", help="Run the fixed context benchmark")
    benchmark.add_argument("--manifest", required=True, type=Path)
    benchmark.add_argument("--output", required=True, type=Path)
    model_benchmark = sub.add_parser("benchmark-models", help="Run fixed cases through local models")
    model_benchmark.add_argument("--manifest", required=True, type=Path)
    model_benchmark.add_argument("--output", required=True, type=Path)
    model_benchmark.add_argument("--config", type=Path, default=Path(".token-forge.local.toml"))
    return parser


def _conversion_gates(config: LocalConfig) -> dict[str, dict[str, object]]:
    docling_artifacts = config.adapters.get("docling_artifacts")
    mineru_config = config.adapters.get("mineru_config")
    docling_local = bool(docling_artifacts and Path(docling_artifacts).exists())
    mineru_local = bool(mineru_config and Path(mineru_config).is_file())
    return {
        "docling": {
            "eligible": docling_local or config.allow_remote,
            "local_artifacts": docling_local,
            "reason": "local artifacts configured" if docling_local else "local artifacts missing",
        },
        "mineru": {
            "eligible": mineru_local or config.allow_remote,
            "local_models": mineru_local,
            "reason": "local model config ready" if mineru_local else "local model config missing",
        },
        "paddleocr_local_scan": {
            "eligible": False,
            "reason": "installed CLI exposes Office doc2md and cloud API, not local scanned-PDF OCR",
        },
    }


def _model_gates(config: LocalConfig) -> dict[str, dict[str, object]]:
    statuses = {status.name: status for status in probe_all(configured=config.adapters)}

    validation: dict[str, object] = {}
    report_path = config.adapters.get("model_validation")
    if report_path and Path(report_path).is_file():
        try:
            report = json.loads(Path(report_path).read_text(encoding="utf-8"))
            if isinstance(report.get("validation"), dict):
                validation = report["validation"]
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            validation = {}

    def gate(stage: str, names: tuple[str, ...]) -> dict[str, object]:
        missing = [name for name in names if not statuses[name].available]
        validated = not missing and validation.get(stage) is True
        return {
            "eligible": not missing,
            "validated": validated,
            "required": list(names),
            "missing": missing,
            "reason": (
                "offline fixture validation passed"
                if validated
                else "required local runtime and model weights detected; run offline validation"
                if not missing
                else f"missing or incomplete: {', '.join(missing)}"
            ),
        }

    return {
        "retrieval": gate("retrieval", ("retrieval-python", "embedding-model", "reranker-model")),
        "learned_compression": gate("learned_compression", ("llmlingua-python", "llmlingua-model")),
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "doctor":
        config = load_config(args.config)
        payload = {
            "config": str(args.config),
            "gpu_serial": config.gpu_serial,
            "allow_remote": config.allow_remote,
            "adapters": [status.to_dict() for status in probe_all(configured=config.adapters)],
            "conversion_gates": _conversion_gates(config),
            "model_gates": _model_gates(config),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if args.command == "profile":
        print(json.dumps(profile_source(args.input).__dict__, ensure_ascii=False, indent=2))
        return 0
    if args.command == "web":
        config = load_config(args.config)
        result = prepare_web_url(
            args.url,
            args.output,
            config.adapters,
            timeout_seconds=args.timeout,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0 if result.success else 3
    if args.command == "media":
        config = load_config(args.config)
        result = process_local_media(
            args.input,
            args.output,
            config.adapters,
            language=args.language,
            timeout_seconds=args.timeout,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0 if result.success else 3
    if args.command == "platform-media":
        config = load_config(args.config)
        result = inspect_platform_media(
            args.url,
            args.output,
            config.adapters,
            subtitles=not args.no_subtitles,
            timeout_seconds=args.timeout,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0 if result.success else 3
    if args.command == "convert":
        config = load_config(args.config)
        result = convert_source(
            args.input,
            args.output,
            config.adapters,
            requested_adapter=args.adapter,
            timeout_seconds=args.timeout,
            allow_remote=config.allow_remote,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        if result.success:
            return 0
        if result.status == "needs-ocr":
            return 4
        return 3 if result.status == "unavailable" else 2
    if args.command == "pack":
        source = args.input.read_text(encoding="utf-8")
        safety_class = profile_source(str(args.input)).family if args.safety_class == "auto" else args.safety_class
        result = build_text_pack(
            source,
            args.query,
            args.budget,
            args.output,
            safety_class=safety_class,
            cache_dir=args.cache_dir,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0 if not result.budget_conflict else 2
    if args.command == "optimize":
        config = load_config(args.config)
        source = args.input.read_text(encoding="utf-8")
        safety_class = profile_source(str(args.input)).family if args.safety_class == "auto" else args.safety_class
        result = optimize_text_pack(
            source,
            args.query,
            args.budget,
            config.adapters,
            safety_class=safety_class,
            output_dir=args.output,
            timeout_seconds=args.timeout,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0 if result.protected_recall == 1.0 and not result.budget_conflict else 2
    if args.command == "benchmark":
        print(json.dumps(run_manifest(args.manifest, args.output), ensure_ascii=False, indent=2))
        return 0
    if args.command == "benchmark-models":
        config = load_config(args.config)
        result = run_model_manifest(args.manifest, args.output, config.adapters)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["all_protected_pass"] else 2
    return 1
