# Full-scenario format matrix

No converter is universal. Token Forge profiles each source, selects the cheapest eligible adapter, and escalates only when a quality gate fails.

| Family | Inputs | Primary route | Escalation or fallback |
|---|---|---|---|
| Plain and structured text | MD, TXT, RST, JSON, JSONL, YAML, XML | native parser | source preservation |
| Modern Office | DOCX, PPTX, XLSX | MarkItDown | Docling; preserve source |
| Legacy Office | DOC, PPT, XLS, ODT | LibreOffice conversion | preserve source |
| PDF | born-digital PDF 1.x/2.0 | MarkItDown | Docling → MinerU → source |
| Scans and images | PNG, JPEG, WebP, TIFF, BMP | MinerU on the validated host | separately verified local OCR or selected vision crop; preserve source |
| E-books | EPUB | MarkItDown or Pandoc | preserve source |
| Web | URL, HTML, MHTML | Defuddle | Playwright render → Defuddle → HTML source |
| Email | EML | Python email parser: headers, body, attachment inventory | MSG and attachment content remain source-only |
| Archives | ZIP | bounded in-place inventory and selected text read | 7Z/TAR/GZ remain source-only; nested ZIP is inventory-only |
| Subtitles | SRT, VTT, ASS | native parser | source preservation |
| Audio | MP3, WAV, M4A, AAC, FLAC, OGG, OPUS | existing faster-whisper | platform transcript or source |
| Video | MP4, MKV, MOV, WebM, AVI, M4V, TS, MTS | FFmpeg + faster-whisper + PySceneDetect | exact frame dedup + bounded Codex visual handoff; local/remote VLM remains explicit |
| Platforms | URLs supported by configured platform tools | official/platform subtitles first | yt-dlp or existing platform-specific workflow |
| Code and logs | Python plus common source/config/log formats | exact Python AST dependency slice; ripgrep selection elsewhere | source snippets; never learned compression |
| Tables and finance | CSV, TSV, spreadsheets and extracted tables | bounded CSV schema-aware aggregate with reconciliation | source table; never learned compression |

## Explicit non-universal cases

- DRM media, inaccessible private pages, and sources without authorization;
- encrypted files without a password;
- corrupted containers or unsupported codecs;
- handwriting or scans below the declared OCR confidence gate;
- layouts whose reading order, formulas, or table structure cannot be verified.

These cases must fail visibly or retain the source. They must never be represented as successfully compressed.

Python AST slicing is capped at 16 MiB and 200,000 lines; it preserves exact source spans, decorators, `__future__` imports, and selected name dependencies, then compiles the resulting slice. Dynamic imports, runtime registration, reflection, generated code, and cross-language call graphs are outside this gate and must fall back to source selection. CSV aggregation is capped at 64 MiB, 100,000 data rows, 256 columns, and 1 MiB per cell; categorical values are Markdown-escaped and numeric columns must reconcile across every parsed row.

The v1 acceptance manifest verifies native EML and bounded ZIP routes. ZIP members are never written to disk by this route; unsafe paths, symlinks, encrypted entries, more than 256 entries, entries over 16 MiB, totals over 64 MiB, and compression ratios over 100:1 fail closed. Nested archives are listed but never recursively opened.

## Token and quality ledger

Keep file bytes, extracted-text tokens, candidate tokens, final prompt tokens, image or audio usage, and cache savings separate. Pair them with protected-fact recall, anchor recall, OCR CER, transcription WER, table-cell recall, retrieval recall, citation grounding, and downstream answer quality. Provider usage is reported only when real telemetry is available.
