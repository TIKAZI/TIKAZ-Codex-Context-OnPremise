# Full-scenario acceptance benchmark

Token Forge publishes failures and pending evidence alongside passing cases. The v1 suite uses generated, redistribution-safe fixtures and invokes the real local adapters rather than mocked converters.

For the row-by-row result of every acceptance, model, OCR, media, and visual scenario, see [Complete measured results](RESULTS.md).

## Checked result

Run date: 2026-08-20. Host-specific timing is included in the raw cases.

| Gate | Result |
|---|---:|
| Required scenarios | **18 / 18 passed** |
| Full manifest | **20 passed / 0 failed / 0 pending** |
| Protected facts, required cases | **51 / 51 (100%)** |
| Protected facts, all local cases | **53 / 53 (100%)** |
| Expected anchors, required cases | **11 / 11 (100%)** |
| Table cells, required cases | **9 / 9 (100%)** |
| OCR CER, two controlled fixtures | **0.00% mean** |
| Transcript fact recall | **6 / 6 (100%)** |
| ASR WER, generated English audio/video | **5.88% mean** |
| Exact keyframe routing, fixed video | **6 source → 2 selected; 4 exact duplicates skipped (66.67%)** |
| Visual fact recall, separate 12-image suite | **OCR 37 / 37; VLM 37 / 37; combined 37 / 37** |
| Dominant frame-type accuracy, separate visual suite | **10 / 12 (83.33%)** |
| Context reduction, seven measured cases | **89.57% token-weighted / 55.96% macro mean** |

The two small code/table cases intentionally pass through at 0%; they remain in both the macro and weighted denominators. Scale fixtures exercise task-relevant selection without rewriting source evidence:

| Scale fixture | Input → output estimate | Reduction | Integrity gate |
|---|---:|---:|---|
| Deterministic long text | 509 → 94 | **81.53%** | declared facts and rollback evidence retained |
| Python AST dependency slice | 1,117 → 100 | **91.05%** | exact spans, decorators/dependencies retained, syntax compiled |
| CSV reconciled aggregate | 2,943 → 84 | **97.15%** | all 500 rows aggregated; numeric reconciliation passed |

Across the small and scale cases together, token-weighted reduction is 74.15% for deterministic text, 84.19% for code context, 96.00% for table context, and 83.30% for the local-model text case. Token counts are deterministic estimates, not Codex or provider billing telemetry.

## Routes exercised

- Markdown selection and protected-literal budgeting;
- safety pass-through for small code/tables, exact Python AST dependency slicing, and reconciled CSV aggregation;
- BGE-M3 retrieval, BGE reranking, and guarded LLMLingua-2 compression;
- DOCX, PPTX, XLSX, EPUB, and born-digital PDF through MarkItDown;
- EML headers/body/attachment inventory through the standard-library email parser;
- bounded ZIP inventory and selected text reading without extracting members to disk;
- image and scanned-PDF OCR through MinerU;
- localhost Playwright render followed by Defuddle extraction;
- FFmpeg, faster-whisper, PySceneDetect, keyframe extraction, exact SHA-256 frame deduplication, and scene-first visual budgeting.

All 20 scenarios pass their declared gates. The explicit-network Bilibili public-metadata case succeeded in 2.650 seconds with `yt-dlp --dump-single-json`; no subtitle track was available, and no media was downloaded. This validates that checked public URL only, not authenticated content or general platform availability. The fixed video produced six source frames; the visual router selected two distinct scene frames and skipped four byte-identical duplicates. This 66.67% figure measures avoided duplicate frame processing only. Provider image-token usage, perceptual duplicates, decorative-frame precision, and blind downstream answer quality remain `Pending`.

## Local visual benchmark

Run date: 2026-08-22. The separate manifest contains 12 deterministic 1280×720 synthetic images spanning English and Chinese records, settings UI, dashboard, table, bar chart, flow diagram, spatial relation, warning dialog, invoice, timeline, and a schematic warehouse scene. PP-OCRv5 mobile and Qwen3-VL 8B were scored independently against 37 declared literal facts; the combined route was scored separately.

| Measure | Run A | Run B |
|---|---:|---:|
| OCR protected-fact recall | 37 / 37 | 37 / 37 |
| VLM protected-fact recall | 37 / 37 | 37 / 37 |
| Combined protected-fact recall | 37 / 37 | 37 / 37 |
| Locally resolved cases | 12 / 12 | 12 / 12 |
| Dominant frame-type accuracy | 10 / 12 | 10 / 12 |
| Aggregate Ollama-reported VLM duration | 48.852 s | 48.755 s |
| Local prompt-evaluation count | 16,236 | 16,236 |

The per-case fact and type results matched across both identical-setting runs. The two stable type errors were the settings and dashboard flat mockups, both classified as `document` instead of `ui`; fact recall was unaffected. Qwen3-VL ran through loopback Ollama with its 5,793,780,858-byte runtime allocation reported in VRAM on the checked RTX 5060 Ti. Local prompt counts are not Codex input tokens. Codex image-token savings remain `Pending provider telemetry`.

## Reproduce

Generate the public fixtures:

```powershell
python scripts\generate_acceptance_fixtures.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\generate_media_fixture.ps1 `
  -Ffmpeg C:\path\to\ffmpeg.exe
```

Run the suite after configuring local adapters:

```powershell
$env:PYTHONPATH='src'
python -m token_forge benchmark-acceptance `
  --manifest benchmarks\acceptance-manifest.json `
  --output benchmark-acceptance-results `
  --config .token-forge.local.toml
```

The command writes all four required artifacts together:

- `summary.json` — gates and required/full-manifest aggregates;
- `metrics.json` — efficiency, fidelity, and multimodal measures;
- `cases.json` — every raw pass, failure, and pending case;
- `evidence-card.md` — reviewable Markdown evidence card.

Checked raw results are under [`benchmarks/results/acceptance-v1`](../benchmarks/results/acceptance-v1). The versioned source manifest is [`benchmarks/acceptance-manifest.json`](../benchmarks/acceptance-manifest.json).

Generate and run the visual suite with `scripts/generate_visual_fixtures.py`, [`visual-manifest.json`](../benchmarks/visual-manifest.json), and `python -m token_forge benchmark-visual ...`. Checked sanitized results are under [`benchmarks/results/visual-v1`](../benchmarks/results/visual-v1). The original images remain external test data, so the checked result is auditable by hashes and raw case outcomes but requires fixture generation for full reproduction.

## Claim boundaries

- These numbers apply only to the committed fixtures, declared thresholds, local dependency versions, and checked host.
- OCR CER does not prove general layout, handwriting, formula, or diagram understanding.
- ASR WER uses generated English speech and standard written-number normalization; it is not a multilingual or noisy-audio result.
- Exact SHA-256 frame deduplication detects byte-identical files only. The selected-frame ratio is not image-token savings, perceptual similarity, informative-visual recall, or semantic accuracy.
- The 12-image visual set is deterministic, clear, synthetic, and small. Its literal-fact recall and type accuracy do not establish handwriting, degraded scans, natural video, arbitrary charts, real-world OCR, or downstream answer correctness.
- ZIP coverage is limited to non-encrypted ZIP files with safe member paths, at most 256 entries, 16 MiB per entry, 64 MiB total uncompressed size, and at most 100:1 compression ratio. Nested archives are inventory-only.
- EML coverage does not include Outlook MSG, remote content loading, attachment content conversion, S/MIME verification, or malware scanning.
- The scale fixtures are generated and deliberately structured: one Python file with 81 functions and one 500-row CSV. They do not establish arbitrary-language call-graph completeness, SQL correctness, repository-scale answer quality, or performance on malformed real-world data.
- A smaller context is not considered successful when a protected fact, anchor, table cell, budget, WER, CER, or route gate fails.
- Do not compare reduction percentages with another project unless corpus, task, tokenizer, budgets, model settings, and downstream rubric are identical.
