# Full-scenario format matrix

No converter is universal. Token Forge profiles each source, selects the cheapest eligible adapter, and escalates only when a quality gate fails.

| Family | Inputs | Primary route | Escalation or fallback |
|---|---|---|---|
| Plain and structured text | MD, TXT, RST, JSON, JSONL, YAML, XML | native parser | source preservation |
| Modern Office | DOCX, PPTX, XLSX | MarkItDown | Docling; preserve source |
| Legacy Office | DOC, PPT, XLS, ODT | LibreOffice conversion | preserve source |
| PDF | born-digital PDF 1.x/2.0 | MarkItDown | Docling → MinerU → source |
| Scans and images | PNG, JPEG, WebP, TIFF, BMP | PaddleOCR | MinerU or selected vision crop |
| E-books | EPUB | MarkItDown or Pandoc | preserve source |
| Web | URL, HTML, MHTML | Defuddle | Playwright render → Defuddle → HTML source |
| Email | EML, MSG | planned message parser | currently unavailable; preserve source |
| Archives | ZIP, 7Z, TAR, GZ | planned bounded extraction | currently unavailable; inventory/source only |
| Subtitles | SRT, VTT, ASS | native parser | source preservation |
| Audio | MP3, WAV, M4A, AAC, FLAC, OGG, OPUS | existing faster-whisper | platform transcript or source |
| Video | MP4, MKV, MOV, WebM, AVI, M4V, TS, MTS | FFmpeg + faster-whisper | keyframes + OCR/vision |
| Platforms | URLs supported by configured platform tools | official/platform subtitles first | yt-dlp or existing platform-specific workflow |
| Code and logs | repositories and common source/config/log formats | ripgrep + structural selection | source snippets; never learned compression |
| Tables and finance | CSV, TSV, spreadsheets and extracted tables | structure-preserving selection | source table; never learned compression |

## Explicit non-universal cases

- DRM media, inaccessible private pages, and sources without authorization;
- encrypted files without a password;
- corrupted containers or unsupported codecs;
- handwriting or scans below the declared OCR confidence gate;
- layouts whose reading order, formulas, or table structure cannot be verified.

These cases must fail visibly or retain the source. They must never be represented as successfully compressed.

The v1 acceptance manifest keeps EML and ZIP as visible optional failures until production routes and security limits are implemented.

## Token and quality ledger

Keep file bytes, extracted-text tokens, candidate tokens, final prompt tokens, image or audio usage, and cache savings separate. Pair them with protected-fact recall, anchor recall, OCR CER, transcription WER, table-cell recall, retrieval recall, citation grounding, and downstream answer quality. Provider usage is reported only when real telemetry is available.
