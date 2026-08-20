# Full-scenario acceptance benchmark

Token Forge publishes failures and pending evidence alongside passing cases. The v1 suite uses generated, redistribution-safe fixtures and invokes the real local adapters rather than mocked converters.

## Checked result

Run date: 2026-08-20. Host-specific timing is included in the raw cases.

| Gate | Result |
|---|---:|
| Required scenarios | **18 / 18 passed** |
| Full manifest | 19 passed / 0 failed / 1 pending |
| Protected facts, required cases | **51 / 51 (100%)** |
| Protected facts, all local cases | **53 / 53 (100%)** |
| Expected anchors, required cases | **11 / 11 (100%)** |
| Table cells, required cases | **9 / 9 (100%)** |
| OCR CER, two controlled fixtures | **0.00% mean** |
| Transcript fact recall | **6 / 6 (100%)** |
| ASR WER, generated English audio/video | **5.88% mean** |
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
- FFmpeg, faster-whisper, PySceneDetect, and keyframe extraction.

All 19 local cases pass their declared gates. Public platform metadata remains `Pending` in the stable suite because network and login state are intentionally opt-in. Keyframe extraction is measured, but visual understanding and blind downstream answer quality remain `Pending`.

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

## Claim boundaries

- These numbers apply only to the committed fixtures, declared thresholds, local dependency versions, and checked host.
- OCR CER does not prove general layout, handwriting, formula, or diagram understanding.
- ASR WER uses generated English speech and standard written-number normalization; it is not a multilingual or noisy-audio result.
- ZIP coverage is limited to non-encrypted ZIP files with safe member paths, at most 256 entries, 16 MiB per entry, 64 MiB total uncompressed size, and at most 100:1 compression ratio. Nested archives are inventory-only.
- EML coverage does not include Outlook MSG, remote content loading, attachment content conversion, S/MIME verification, or malware scanning.
- The scale fixtures are generated and deliberately structured: one Python file with 81 functions and one 500-row CSV. They do not establish arbitrary-language call-graph completeness, SQL correctness, repository-scale answer quality, or performance on malformed real-world data.
- A smaller context is not considered successful when a protected fact, anchor, table cell, budget, WER, CER, or route gate fails.
- Do not compare reduction percentages with another project unless corpus, task, tokenizer, budgets, model settings, and downstream rubric are identical.
