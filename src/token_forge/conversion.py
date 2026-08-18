from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Mapping, Sequence

from .protection import extract_protected_literals, protected_recall
from .router import profile_source


@dataclass(frozen=True)
class ProcessOutcome:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class ConversionAttempt:
    adapter: str
    status: str
    returncode: int | None
    version: str | None
    elapsed_ms: int
    error: str = ""


@dataclass(frozen=True)
class ConversionResult:
    success: bool
    status: str
    source: str
    source_hash: str
    family: str
    adapter: str | None
    adapter_version: str | None
    output_path: str | None
    protected_literals: tuple[str, ...]
    protected_recall: float
    elapsed_ms: int
    attempts: tuple[ConversionAttempt, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


Runner = Callable[[Sequence[str], int], ProcessOutcome]


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "template", "noscript"}:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "template", "noscript"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth and data.strip():
            self.parts.append(data)


def _html_visible_text(source: str) -> str:
    parser = _VisibleTextParser()
    parser.feed(source)
    parser.close()
    return "\n".join(parser.parts)


def _run_process(command: Sequence[str], timeout_seconds: int) -> ProcessOutcome:
    selected: Sequence[str] | str = command
    if os.name == "nt" and Path(command[0]).suffix.lower() in {".cmd", ".bat"}:
        selected = ["cmd.exe", "/d", "/s", "/c", subprocess.list2cmdline(list(command))]
    try:
        completed = subprocess.run(
            selected,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as error:
        return ProcessOutcome(124, error.stdout or "", error.stderr or "adapter timed out")
    except OSError as error:
        return ProcessOutcome(127, "", str(error))
    return ProcessOutcome(completed.returncode, completed.stdout, completed.stderr)


def _command(adapter: str, executable: str, source: Path, destination: Path) -> list[str]:
    if adapter == "defuddle":
        return [executable, "parse", str(source), "--markdown", "--output", str(destination)]
    if adapter == "markitdown":
        return [executable, str(source), "-o", str(destination)]
    raise ValueError(f"adapter is not implemented: {adapter}")


def _source_literals(source: Path) -> tuple[str, ...]:
    if source.suffix.lower() not in {".html", ".htm", ".mhtml", ".md", ".txt", ".rst", ".json", ".jsonl", ".yaml", ".yml"}:
        return ()
    text = source.read_text(encoding="utf-8", errors="replace")
    if source.suffix.lower() in {".html", ".htm", ".mhtml"}:
        text = _html_visible_text(text)
    return extract_protected_literals(text)


def _write_ledger(output_dir: Path, result: ConversionResult) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "conversion.json").write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def convert_source(
    source: Path,
    output_dir: Path,
    adapters: Mapping[str, str],
    requested_adapter: str = "auto",
    timeout_seconds: int = 120,
    runner: Runner | None = None,
) -> ConversionResult:
    if not source.is_file():
        raise FileNotFoundError(source)
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    started = time.perf_counter()
    invoke = runner or _run_process
    profile = profile_source(str(source))
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    protected = _source_literals(source)
    canonical = output_dir / "canonical.md"
    output_dir.mkdir(parents=True, exist_ok=True)

    implemented = {"defuddle", "markitdown"}
    if requested_adapter == "auto":
        candidates = [
            name for name in profile.adapter_candidates
            if name in implemented and adapters.get(name)
        ]
    else:
        if requested_adapter not in implemented:
            raise ValueError(f"adapter is not implemented: {requested_adapter}")
        candidates = [requested_adapter] if adapters.get(requested_adapter) else []

    attempts: list[ConversionAttempt] = []
    best_recall = 1.0 if not protected else 0.0
    final_status = "unavailable"
    for adapter in candidates:
        executable = adapters[adapter]
        version_outcome = invoke([executable, "--version"], timeout_seconds)
        version = (version_outcome.stdout or version_outcome.stderr).strip().splitlines()
        version_text = version[0][:200] if version else None
        canonical.unlink(missing_ok=True)
        attempt_started = time.perf_counter()
        outcome = invoke(_command(adapter, executable, source, canonical), timeout_seconds)
        elapsed_ms = round((time.perf_counter() - attempt_started) * 1000)

        if outcome.returncode != 0:
            final_status = "failed"
            attempts.append(
                ConversionAttempt(
                    adapter, "failed", outcome.returncode, version_text, elapsed_ms,
                    (outcome.stderr or outcome.stdout).strip()[:2000],
                )
            )
            continue
        if not canonical.is_file() or not canonical.read_text(encoding="utf-8", errors="replace").strip():
            final_status = "quality-failed"
            attempts.append(
                ConversionAttempt(adapter, "empty-output", outcome.returncode, version_text, elapsed_ms)
            )
            canonical.unlink(missing_ok=True)
            continue

        converted = canonical.read_text(encoding="utf-8", errors="replace")
        recall = protected_recall(protected, converted)
        best_recall = max(best_recall, recall)
        if recall < 1.0:
            final_status = "quality-failed"
            attempts.append(
                ConversionAttempt(
                    adapter, "protected-literal-loss", outcome.returncode,
                    version_text, elapsed_ms,
                )
            )
            canonical.unlink(missing_ok=True)
            continue

        attempts.append(ConversionAttempt(adapter, "success", outcome.returncode, version_text, elapsed_ms))
        result = ConversionResult(
            success=True,
            status="success",
            source=str(source.resolve()),
            source_hash=source_hash,
            family=profile.family,
            adapter=adapter,
            adapter_version=version_text,
            output_path=str(canonical.resolve()),
            protected_literals=protected,
            protected_recall=recall,
            elapsed_ms=round((time.perf_counter() - started) * 1000),
            attempts=tuple(attempts),
        )
        _write_ledger(output_dir, result)
        return result

    canonical.unlink(missing_ok=True)
    result = ConversionResult(
        success=False,
        status=final_status,
        source=str(source.resolve()),
        source_hash=source_hash,
        family=profile.family,
        adapter=None,
        adapter_version=None,
        output_path=None,
        protected_literals=protected,
        protected_recall=best_recall,
        elapsed_ms=round((time.perf_counter() - started) * 1000),
        attempts=tuple(attempts),
    )
    _write_ledger(output_dir, result)
    return result
