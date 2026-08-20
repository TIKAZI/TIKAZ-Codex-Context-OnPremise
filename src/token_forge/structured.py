from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from email import policy
from email.message import Message
from email.parser import BytesParser
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath


class StructuredSourceError(ValueError):
    """Raised when a structured source is malformed or violates a safety bound."""


@dataclass(frozen=True)
class ArchiveLimits:
    max_entries: int = 256
    max_entry_bytes: int = 16 * 1024 * 1024
    max_total_bytes: int = 64 * 1024 * 1024
    max_compression_ratio: float = 100.0


_TEXT_SUFFIXES = {
    ".txt", ".md", ".rst", ".json", ".jsonl", ".yaml", ".yml", ".csv",
    ".tsv", ".xml", ".html", ".htm", ".py", ".js", ".ts", ".toml",
    ".ini", ".cfg", ".log",
}
_NESTED_ARCHIVES = {".zip", ".7z", ".rar", ".tar", ".gz", ".bz2", ".xz"}
_MAX_EMAIL_BYTES = 32 * 1024 * 1024


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ignored = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "template", "noscript"}:
            self.ignored += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "template", "noscript"} and self.ignored:
            self.ignored -= 1

    def handle_data(self, data: str) -> None:
        value = data.strip()
        if value and not self.ignored:
            self.parts.append(value)


def _visible_html(value: str) -> str:
    parser = _VisibleTextParser()
    parser.feed(value)
    parser.close()
    return "\n".join(parser.parts)


def _clean_inline(value: object) -> str:
    return re.sub(r"[\r\n]+", " ", str(value or "")).strip().replace("|", "\\|")


def _decoded_text(part: Message) -> str:
    try:
        content = part.get_content()
        if isinstance(content, str):
            return content
    except (LookupError, UnicodeDecodeError, ValueError):
        pass
    payload = part.get_payload(decode=True) or b""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


def convert_eml(source: Path) -> str:
    if source.stat().st_size > _MAX_EMAIL_BYTES:
        raise StructuredSourceError("email exceeds 32 MiB safety limit")
    try:
        message = BytesParser(policy=policy.default).parsebytes(source.read_bytes())
    except (OSError, ValueError) as error:
        raise StructuredSourceError(f"invalid email: {error}") from error

    lines = ["# Email", "", "## Headers", ""]
    for label, name in (
        ("Subject", "Subject"), ("From", "From"), ("To", "To"),
        ("Cc", "Cc"), ("Date", "Date"), ("Message-ID", "Message-ID"),
    ):
        value = _clean_inline(message.get(name))
        if value:
            lines.append(f"- **{label}:** {value}")

    plain: list[str] = []
    html: list[str] = []
    attachments: list[tuple[str, str, int]] = []
    for part in message.walk() if message.is_multipart() else (message,):
        if part.is_multipart():
            continue
        disposition = part.get_content_disposition()
        filename = _clean_inline(part.get_filename())
        content_type = _clean_inline(part.get_content_type())
        payload = part.get_payload(decode=True) or b""
        if disposition == "attachment" or filename:
            attachments.append((filename or "unnamed", content_type, len(payload)))
            continue
        if content_type == "text/plain":
            value = _decoded_text(part).strip()
            if value:
                plain.append(value)
        elif content_type == "text/html":
            value = _visible_html(_decoded_text(part)).strip()
            if value:
                html.append(value)

    lines.extend(["", "## Body", "", "\n\n".join(plain or html) or "_No readable body._"])
    if attachments:
        lines.extend(["", "## Attachments", "", "| Name | Content type | Decoded size |", "|---|---|---:|"])
        for filename, content_type, size in attachments:
            lines.append(f"| {filename} | {content_type} | {size} bytes |")
    return "\n".join(lines).rstrip() + "\n"


def _safe_member_name(name: str) -> str:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        not normalized
        or normalized.startswith(("/", "//"))
        or re.match(r"^[A-Za-z]:", normalized)
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise StructuredSourceError(f"unsafe path in archive: {name!r}")
    return path.as_posix()


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    return ((info.external_attr >> 16) & 0o170000) == 0o120000


def _decode_text(data: bytes) -> str:
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig", errors="replace")
    return data.decode("utf-8", errors="replace")


def convert_zip(source: Path, limits: ArchiveLimits | None = None) -> str:
    selected = limits or ArchiveLimits()
    if min(selected.max_entries, selected.max_entry_bytes, selected.max_total_bytes) <= 0:
        raise ValueError("archive limits must be positive")
    try:
        with zipfile.ZipFile(source) as archive:
            members = archive.infolist()
            if len(members) > selected.max_entries:
                raise StructuredSourceError("archive entry count exceeds safety limit")
            total = 0
            safe_members: list[tuple[zipfile.ZipInfo, str]] = []
            for info in members:
                name = _safe_member_name(info.filename)
                if info.flag_bits & 0x1:
                    raise StructuredSourceError(f"encrypted archive entry is not allowed: {name}")
                if _is_symlink(info):
                    raise StructuredSourceError(f"symbolic link is not allowed: {name}")
                if info.is_dir():
                    continue
                if info.file_size > selected.max_entry_bytes:
                    raise StructuredSourceError(f"archive entry exceeds size limit: {name}")
                total += info.file_size
                if total > selected.max_total_bytes:
                    raise StructuredSourceError("archive total size exceeds safety limit")
                ratio = info.file_size / max(info.compress_size, 1)
                if info.file_size and ratio > selected.max_compression_ratio:
                    raise StructuredSourceError(f"archive compression ratio exceeds safety limit: {name}")
                safe_members.append((info, name))

            lines = ["# ZIP archive", "", "## Inventory", "", "| Path | Type | Uncompressed size |", "|---|---|---:|"]
            readable: list[tuple[zipfile.ZipInfo, str]] = []
            for info, name in safe_members:
                suffix = Path(name).suffix.lower()
                kind = "nested archive (inventory only)" if suffix in _NESTED_ARCHIVES else ("text" if suffix in _TEXT_SUFFIXES else "binary")
                lines.append(f"| {name.replace('|', '\\|')} | {kind} | {info.file_size} bytes |")
                if kind == "text":
                    readable.append((info, name))

            for info, name in readable:
                with archive.open(info) as stream:
                    data = stream.read(selected.max_entry_bytes + 1)
                if len(data) > selected.max_entry_bytes:
                    raise StructuredSourceError(f"archive entry exceeded read limit: {name}")
                lines.extend(["", f"## `{name.replace('`', '')}`", "", _decode_text(data).rstrip()])
            return "\n".join(lines).rstrip() + "\n"
    except StructuredSourceError:
        raise
    except (OSError, zipfile.BadZipFile, RuntimeError) as error:
        raise StructuredSourceError(f"invalid ZIP archive: {error}") from error
