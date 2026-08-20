from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import shutil
import subprocess
import tempfile
import time
import zipfile
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Mapping, Sequence
from xml.etree import ElementTree

from .protection import extract_protected_literals, protected_recall
from .router import profile_source
from .structured import StructuredSourceError, convert_eml, convert_zip


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
    protected_recall: float | None
    verification_level: str
    elapsed_ms: int
    attempts: tuple[ConversionAttempt, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


Runner = Callable[[Sequence[str], int], ProcessOutcome]

_CREATE_SUSPENDED = 0x00000004
_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
_JOB_OBJECT_LIMIT_KILL_ON_CLOSE = 0x00002000


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


def _restore_markdown_escaped_literals(text: str, literals: Sequence[str]) -> str:
    markdown_punctuation = frozenset("\\`*_{}[]<>()#+-.!|")
    restored = text.replace("\\_", "_")
    for literal in sorted(set(literals), key=len, reverse=True):
        if not literal or literal in restored:
            continue
        pattern = "".join(
            rf"(?:\\)?{re.escape(character)}"
            if character in markdown_punctuation else re.escape(character)
            for character in literal
        )
        restored = re.sub(pattern, lambda _: literal, restored)
    return restored


def _windows_kill_on_close_job(process: subprocess.Popen[str]) -> int | None:
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    class IoCounters(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_ulonglong),
            ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong),
            ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong),
            ("OtherTransferCount", ctypes.c_ulonglong),
        ]

    class BasicLimitInformation(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class ExtendedLimitInformation(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", BasicLimitInformation),
            ("IoInfo", IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    )
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL

    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        return None
    information = ExtendedLimitInformation()
    information.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_CLOSE
    configured = kernel32.SetInformationJobObject(
        job,
        _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
        ctypes.byref(information),
        ctypes.sizeof(information),
    )
    assigned = configured and kernel32.AssignProcessToJobObject(job, process._handle)
    if not assigned:
        kernel32.CloseHandle(job)
        return None
    return int(job)


def _close_windows_job(job: int | None) -> None:
    if job is None:
        return
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.CloseHandle(wintypes.HANDLE(job))


def _resume_windows_process(process: subprocess.Popen[str]) -> None:
    if os.name != "nt":
        return
    import ctypes
    from ctypes import wintypes

    ntdll = ctypes.WinDLL("ntdll")
    ntdll.NtResumeProcess.argtypes = (wintypes.HANDLE,)
    ntdll.NtResumeProcess.restype = ctypes.c_long
    status = ntdll.NtResumeProcess(process._handle)
    if status != 0:
        raise OSError(f"failed to resume adapter process: NTSTATUS 0x{status & 0xffffffff:08x}")


def _terminate_process_tree(process: subprocess.Popen[str], windows_job: int | None) -> None:
    if os.name == "nt":
        if windows_job is not None:
            _close_windows_job(windows_job)
            return
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            if process.poll() is None:
                process.kill()
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (OSError, ProcessLookupError):
        if process.poll() is None:
            process.kill()


def _run_process(
    command: Sequence[str],
    timeout_seconds: int,
    environment: Mapping[str, str] | None = None,
) -> ProcessOutcome:
    selected: Sequence[str] | str = command
    if os.name == "nt" and Path(command[0]).suffix.lower() in {".cmd", ".bat"}:
        selected = ["cmd.exe", "/d", "/s", "/c", subprocess.list2cmdline(list(command))]
    popen_options: dict[str, object] = {}
    if os.name == "nt":
        popen_options["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP | _CREATE_SUSPENDED
        )
    else:
        popen_options["start_new_session"] = True
    with (
        tempfile.TemporaryFile(mode="w+t", encoding="utf-8", errors="replace") as stdout_file,
        tempfile.TemporaryFile(mode="w+t", encoding="utf-8", errors="replace") as stderr_file,
    ):
        try:
            process = subprocess.Popen(
                selected,
                stdout=stdout_file,
                stderr=stderr_file,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
                env={**os.environ, **(environment or {})},
                **popen_options,
            )
        except OSError as error:
            return ProcessOutcome(127, "", str(error))
        windows_job = _windows_kill_on_close_job(process)
        try:
            _resume_windows_process(process)
        except OSError as error:
            _terminate_process_tree(process, windows_job)
            return ProcessOutcome(127, "", str(error))
        timed_out = False
        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            _terminate_process_tree(process, windows_job)
            windows_job = None
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1)
        finally:
            if windows_job is not None:
                _close_windows_job(windows_job)
            elif os.name != "nt" and process.poll() is not None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except (OSError, ProcessLookupError):
                    pass
        stdout_file.seek(0)
        stderr_file.seek(0)
        stdout = stdout_file.read()
        stderr = stderr_file.read()
    if timed_out:
        return ProcessOutcome(124, stdout, stderr or "adapter timed out")
    return ProcessOutcome(process.returncode, stdout, stderr)


def _version_command(adapter: str, executable: str) -> list[str]:
    if adapter == "docling":
        return [executable, "convert", "--version"]
    return [executable, "--version"]


def _command(
    adapter: str,
    executable: str,
    source: Path,
    destination: Path,
    artifacts_path: str | None = None,
) -> tuple[list[str], Path, Path | None]:
    if adapter == "defuddle":
        return (
            [executable, "parse", str(source), "--markdown", "--output", str(destination)],
            destination,
            None,
        )
    if adapter == "markitdown":
        return [executable, str(source), "-o", str(destination)], destination, None
    if adapter == "docling":
        staging = Path(tempfile.mkdtemp(prefix=".docling-", dir=destination.parent))
        command = [
                executable,
                "convert",
                str(source),
                "--to",
                "md",
                "--output",
                str(staging),
                "--no-ocr",
                "--no-tables",
                "--abort-on-error",
                "--quiet",
            ]
        if artifacts_path:
            command[8:8] = ["--artifacts-path", artifacts_path]
        return (
            command,
            staging / f"{source.stem}.md",
            staging,
        )
    if adapter == "mineru":
        staging = Path(tempfile.mkdtemp(prefix=".mineru-", dir=destination.parent))
        return (
            [
                executable,
                "-p",
                str(source),
                "-o",
                str(staging),
                "-m",
                "ocr",
                "-b",
                "pipeline",
                "-f",
                "false",
                "-t",
                "false",
            ],
            staging,
            staging,
        )
    raise ValueError(f"adapter is not implemented: {adapter}")


def _resolved_output(adapter: str, produced_path: Path, source: Path) -> Path:
    if adapter != "mineru" or not produced_path.is_dir():
        return produced_path
    markdowns = sorted(produced_path.rglob("*.md"))
    matching = [path for path in markdowns if path.stem == source.stem]
    if matching:
        return matching[0]
    if len(markdowns) == 1:
        return markdowns[0]
    return produced_path / f"{source.stem}.md"


def _adapter_is_ready(adapter: str, adapters: Mapping[str, str], allow_remote: bool) -> bool:
    if not adapters.get(adapter):
        return False
    if adapter == "docling":
        return bool(adapters.get("docling_artifacts") or allow_remote)
    if adapter == "mineru":
        config = adapters.get("mineru_config")
        return bool((config and Path(config).is_file()) or allow_remote)
    return True


def _ooxml_text(source: Path) -> str:
    suffix = source.suffix.lower()
    if suffix == ".docx":
        prefixes = ("word/document.xml", "word/header", "word/footer", "word/footnotes.xml", "word/endnotes.xml")
    elif suffix == ".pptx":
        prefixes = ("ppt/slides/slide", "ppt/notesSlides/notesSlide")
    else:
        return ""

    parts: list[str] = []
    try:
        with zipfile.ZipFile(source) as archive:
            for name in sorted(archive.namelist()):
                if not name.endswith(".xml") or not name.startswith(prefixes):
                    continue
                root = ElementTree.fromstring(archive.read(name))
                parts.extend(value for value in root.itertext() if value.strip())
    except (OSError, zipfile.BadZipFile, ElementTree.ParseError):
        return ""
    return "\n".join(parts)


def _source_literals(source: Path) -> tuple[str, ...] | None:
    suffix = source.suffix.lower()
    if suffix in {".docx", ".pptx"}:
        return extract_protected_literals(_ooxml_text(source))
    if suffix == ".eml":
        return extract_protected_literals(convert_eml(source))
    if suffix == ".zip":
        try:
            return extract_protected_literals(convert_zip(source))
        except StructuredSourceError:
            return None
    if suffix not in {".html", ".htm", ".mhtml", ".md", ".txt", ".rst", ".json", ".jsonl", ".yaml", ".yml"}:
        return None
    text = source.read_text(encoding="utf-8", errors="replace")
    if suffix in {".html", ".htm", ".mhtml"}:
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
    allow_remote: bool = False,
) -> ConversionResult:
    if not source.is_file():
        raise FileNotFoundError(source)
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    started = time.perf_counter()
    def invoke(
        command: Sequence[str],
        environment: Mapping[str, str] | None = None,
    ) -> ProcessOutcome:
        if runner is not None:
            return runner(command, timeout_seconds)
        return _run_process(command, timeout_seconds, environment)
    profile = profile_source(str(source))
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    protected_source = _source_literals(source)
    protected = protected_source or ()
    verification_level = "source-literal" if protected_source is not None else "output-only"
    canonical = output_dir / "canonical.md"
    output_dir.mkdir(parents=True, exist_ok=True)

    native_adapters = {".eml": ("email-parser", convert_eml), ".zip": ("bounded-zip", convert_zip)}
    native = native_adapters.get(source.suffix.lower())
    if native is not None:
        adapter, converter = native
        if requested_adapter not in {"auto", adapter}:
            raise ValueError(f"adapter is not implemented: {requested_adapter}")
        attempt_started = time.perf_counter()
        try:
            converted = converter(source)
        except StructuredSourceError as error:
            canonical.unlink(missing_ok=True)
            result = ConversionResult(
                success=False,
                status="unsafe-archive" if source.suffix.lower() == ".zip" else "failed",
                source=str(source.resolve()), source_hash=source_hash, family=profile.family,
                adapter=None, adapter_version=None, output_path=None,
                protected_literals=protected, protected_recall=None,
                verification_level=verification_level,
                elapsed_ms=round((time.perf_counter() - started) * 1000),
                attempts=(ConversionAttempt(adapter, "rejected", None, "stdlib", round((time.perf_counter() - attempt_started) * 1000), str(error)),),
            )
            _write_ledger(output_dir, result)
            return result
        converted = _restore_markdown_escaped_literals(converted, protected)
        recall = protected_recall(protected, converted) if protected_source is not None else None
        if recall is not None and recall < 1.0:
            canonical.unlink(missing_ok=True)
            result = ConversionResult(
                success=False, status="quality-failed", source=str(source.resolve()),
                source_hash=source_hash, family=profile.family, adapter=None,
                adapter_version=None, output_path=None, protected_literals=protected,
                protected_recall=recall, verification_level=verification_level,
                elapsed_ms=round((time.perf_counter() - started) * 1000),
                attempts=(ConversionAttempt(adapter, "protected-literal-loss", 0, "stdlib", round((time.perf_counter() - attempt_started) * 1000)),),
            )
            _write_ledger(output_dir, result)
            return result
        canonical.write_text(converted, encoding="utf-8")
        result = ConversionResult(
            success=True, status="success", source=str(source.resolve()),
            source_hash=source_hash, family=profile.family, adapter=adapter,
            adapter_version="stdlib", output_path=str(canonical.resolve()),
            protected_literals=protected, protected_recall=recall,
            verification_level=verification_level,
            elapsed_ms=round((time.perf_counter() - started) * 1000),
            attempts=(ConversionAttempt(adapter, "success", 0, "stdlib", round((time.perf_counter() - attempt_started) * 1000)),),
        )
        _write_ledger(output_dir, result)
        return result

    implemented = {"defuddle", "markitdown", "docling", "mineru"}
    if requested_adapter == "auto":
        candidates = [
            name for name in profile.adapter_candidates
            if name in implemented and _adapter_is_ready(name, adapters, allow_remote)
        ]
    else:
        if requested_adapter not in implemented:
            raise ValueError(f"adapter is not implemented: {requested_adapter}")
        candidates = [requested_adapter] if _adapter_is_ready(requested_adapter, adapters, allow_remote) else []

    attempts: list[ConversionAttempt] = []
    best_recall: float | None = None if protected_source is None else (1.0 if not protected else 0.0)
    final_status = "unavailable"
    for adapter in candidates:
        executable = adapters[adapter]
        version_outcome = invoke(_version_command(adapter, executable))
        version = (version_outcome.stdout or version_outcome.stderr).strip().splitlines()
        version_text = version[0][:200] if version else None
        canonical.unlink(missing_ok=True)
        attempt_started = time.perf_counter()
        command, produced_path, cleanup_root = _command(
            adapter,
            executable,
            source,
            canonical,
            adapters.get("docling_artifacts"),
        )
        environment = None
        if adapter == "mineru":
            environment = {"MINERU_MODEL_SOURCE": "local"}
            if adapters.get("mineru_config"):
                environment["MINERU_TOOLS_CONFIG_JSON"] = adapters["mineru_config"]
        outcome = invoke(command, environment)
        elapsed_ms = round((time.perf_counter() - attempt_started) * 1000)

        if outcome.returncode != 0:
            final_status = "failed"
            attempts.append(
                ConversionAttempt(
                    adapter, "failed", outcome.returncode, version_text, elapsed_ms,
                    (outcome.stderr or outcome.stdout).strip()[:2000],
                )
            )
            if cleanup_root:
                shutil.rmtree(cleanup_root, ignore_errors=True)
            continue
        produced_path = _resolved_output(adapter, produced_path, source)
        if not produced_path.is_file() or not produced_path.read_text(encoding="utf-8", errors="replace").strip():
            if requested_adapter == "auto" and source.suffix.lower() == ".pdf" and adapter == "markitdown":
                final_status = "needs-ocr"
            else:
                final_status = "quality-failed"
            attempts.append(
                ConversionAttempt(adapter, "empty-output", outcome.returncode, version_text, elapsed_ms)
            )
            canonical.unlink(missing_ok=True)
            if cleanup_root:
                shutil.rmtree(cleanup_root, ignore_errors=True)
            continue

        converted = produced_path.read_text(encoding="utf-8", errors="replace")
        converted = _restore_markdown_escaped_literals(converted, protected)
        recall = protected_recall(protected, converted) if protected_source is not None else None
        if recall is not None:
            best_recall = max(best_recall or 0.0, recall)
        if recall is not None and recall < 1.0:
            final_status = "quality-failed"
            attempts.append(
                ConversionAttempt(
                    adapter, "protected-literal-loss", outcome.returncode,
                    version_text, elapsed_ms,
                )
            )
            canonical.unlink(missing_ok=True)
            if cleanup_root:
                shutil.rmtree(cleanup_root, ignore_errors=True)
            continue

        canonical.write_text(converted, encoding="utf-8")
        if cleanup_root:
            shutil.rmtree(cleanup_root, ignore_errors=True)
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
            verification_level=verification_level,
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
        verification_level=verification_level,
        elapsed_ms=round((time.perf_counter() - started) * 1000),
        attempts=tuple(attempts),
    )
    _write_ledger(output_dir, result)
    return result
