# Full-scenario acceptance benchmark

Token Forge publishes failures and pending evidence alongside passing cases. The v1 suite uses generated, redistribution-safe fixtures and invokes the real local adapters rather than mocked converters.

## Checked result

Run date: 2026-08-20. Host-specific timing is included in the raw cases.

| Gate | Result |
|---|---:|
| Required scenarios | **13 / 13 passed** |
| Full manifest | 14 passed / 2 failed / 1 pending |
| Protected facts, required cases | **37 / 37 (100%)** |
| Expected anchors, required cases | **9 / 9 (100%)** |
| Table cells, required cases | **9 / 9 (100%)** |
| OCR CER, two controlled fixtures | **0.00% mean** |
| Transcript fact recall | **6 / 6 (100%)** |
| ASR WER, generated English audio/video | **5.88% mean** |
| Estimated token reduction, four eligible text cases | **30.49% mean** |

The four text cases are not a representative market corpus: two high-risk cases intentionally pass through at 0%, one deterministic retrieval case reduces 38.68%, and one BGE + reranker + LLMLingua-2 case reduces 83.30%. Token counts are deterministic estimates, not Codex or provider billing telemetry.

## Routes exercised

- Markdown selection and protected-literal budgeting;
- safety pass-through for code and structured tables;
- BGE-M3 retrieval, BGE reranking, and guarded LLMLingua-2 compression;
- DOCX, PPTX, XLSX, EPUB, and born-digital PDF through MarkItDown;
- image and scanned-PDF OCR through MinerU;
- localhost Playwright render followed by Defuddle extraction;
- FFmpeg, faster-whisper, PySceneDetect, and keyframe extraction.

EML and ZIP remain visible failed capability probes because no production route is implemented. Public platform metadata remains `Pending` in the stable suite because network and login state are intentionally opt-in. Keyframe extraction is measured, but visual understanding and blind downstream answer quality remain `Pending`.

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
- A smaller context is not considered successful when a protected fact, anchor, table cell, budget, WER, CER, or route gate fails.
- Do not compare reduction percentages with another project unless corpus, task, tokenizer, budgets, model settings, and downstream rubric are identical.

