from __future__ import annotations

import hashlib
import json
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence
from urllib.parse import urlparse

from .conversion import ConversionResult, ProcessOutcome, _run_process, convert_source


@dataclass(frozen=True)
class WebResult:
    success: bool
    status: str
    url: str
    final_url: str | None
    source_hash: str | None
    rendered_html: str | None
    viewport_image: str | None
    elapsed_ms: int
    error: str = ""
    conversion: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


WebRunner = Callable[[Sequence[str], int], ProcessOutcome]
WebConverter = Callable[..., ConversionResult]


def _playwright_module_root(executable: str) -> Path:
    path = Path(executable).resolve()
    if path.parent.name.casefold() == ".bin":
        return path.parent.parent
    return path.parent


def prepare_web_url(
    url: str,
    output_dir: Path,
    adapters: Mapping[str, str],
    *,
    timeout_seconds: int = 120,
    runner: WebRunner | None = None,
    converter: WebConverter = convert_source,
) -> WebResult:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("web input must be an absolute HTTP(S) URL")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    started = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    node = adapters.get("node") or shutil.which("node")
    playwright = adapters.get("playwright")
    if not node or not playwright:
        return WebResult(
            False, "unavailable", url, None, None, None, None,
            round((time.perf_counter() - started) * 1000),
            "node and playwright must be configured",
        )

    script = Path(__file__).resolve().parents[2] / "scripts" / "render_page.mjs"
    command = [
        node,
        str(script),
        "--url",
        url,
        "--output",
        str(output_dir),
        "--module-root",
        str(_playwright_module_root(playwright)),
    ]
    environment = None
    if adapters.get("playwright_browsers"):
        environment = {"PLAYWRIGHT_BROWSERS_PATH": adapters["playwright_browsers"]}
    outcome = runner(command, timeout_seconds) if runner else _run_process(
        command, timeout_seconds, environment
    )
    if outcome.returncode != 0:
        return WebResult(
            False, "render-failed", url, None, None, None, None,
            round((time.perf_counter() - started) * 1000),
            (outcome.stderr or outcome.stdout).strip()[:2000],
        )

    rendered = output_dir / "rendered.html"
    viewport = output_dir / "viewport.png"
    metadata_path = output_dir / "metadata.json"
    if not rendered.is_file() or not rendered.read_text(encoding="utf-8", errors="replace").strip():
        return WebResult(
            False, "empty-render", url, None, None, None, None,
            round((time.perf_counter() - started) * 1000),
            "Playwright did not produce non-empty rendered HTML",
        )
    if not viewport.is_file() or not metadata_path.is_file():
        return WebResult(
            False, "incomplete-render", url, None, None, str(rendered.resolve()), None,
            round((time.perf_counter() - started) * 1000),
            "Playwright render is missing viewport.png or metadata.json",
        )

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return WebResult(
            False, "invalid-metadata", url, None, None, str(rendered.resolve()),
            str(viewport.resolve()), round((time.perf_counter() - started) * 1000), str(error),
        )

    conversion = converter(
        rendered,
        output_dir,
        adapters,
        requested_adapter="auto",
        timeout_seconds=timeout_seconds,
        allow_remote=False,
    )
    rendered_bytes = rendered.read_bytes()
    result = WebResult(
        conversion.success,
        "success" if conversion.success else f"conversion-{conversion.status}",
        url,
        str(metadata.get("final_url") or url),
        hashlib.sha256(rendered_bytes).hexdigest(),
        str(rendered.resolve()),
        str(viewport.resolve()),
        round((time.perf_counter() - started) * 1000),
        conversion=conversion.to_dict(),
    )
    (output_dir / "web.json").write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return result
