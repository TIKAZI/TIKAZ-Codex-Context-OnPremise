from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from .models import SourceProfile


TEXT = {".md", ".txt", ".rst", ".json", ".jsonl", ".yaml", ".yml"}
TABLE = {".csv", ".tsv"}
DOCUMENT = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".odt", ".epub"}
MEDIA = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".mp4", ".mov", ".mkv", ".avi", ".webm"}
IMAGE = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
CODE = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".rs", ".go", ".java", ".kt",
    ".c", ".cc", ".cpp", ".h", ".hpp", ".cs", ".php", ".rb", ".swift",
    ".sql", ".sh", ".ps1", ".bat", ".toml", ".xml", ".html", ".css",
}


def profile_source(source: str) -> SourceProfile:
    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"}:
        return SourceProfile(source, "web", "", "extract", ("defuddle", "playwright", "readability"), True)

    suffix = Path(source).suffix.lower()
    if suffix in TABLE:
        return SourceProfile(source, "table", suffix, "table-safe", (), False)
    if suffix in CODE:
        return SourceProfile(source, "code", suffix, "code-safe", ("ripgrep", "tree-sitter"), False)
    if suffix in DOCUMENT:
        return SourceProfile(source, "document", suffix, "convert", ("markitdown", "docling", "mineru", "paddleocr"), True)
    if suffix in MEDIA:
        return SourceProfile(source, "media", suffix, "transcribe", ("platform-subtitles", "faster-whisper", "whisperx"), True)
    if suffix in IMAGE:
        return SourceProfile(source, "image", suffix, "ocr-or-vision", ("paddleocr", "mineru", "vision"), False)
    if suffix in TEXT or not suffix:
        return SourceProfile(source, "text", suffix, "text", (), True)
    return SourceProfile(source, "unknown", suffix, "source", (), False)
