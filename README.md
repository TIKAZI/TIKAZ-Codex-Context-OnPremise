# TIKAZ Codex Token Forge

Local-first multimodal context compilation for Codex: convert difficult sources, preserve evidence, retrieve only task-relevant material, and optionally compress low-risk prose.

Designed, integrated, independently implemented, and maintained by **TIKAZ**.

Token Forge is the dependency-rich counterpart to the portable Context Economy workflow. It does not promise a fixed reduction percentage. It searches for the best measured quality/cost point for each source and task.

## Pipeline

```text
files / webpages / media / code / conversations
  -> immutable source + content hash
  -> routed converter or transcriber
  -> canonical Markdown + structured evidence
  -> exact/near-duplicate control
  -> BM25 + dense retrieval + reranking
  -> optional LLMLingua-2 for low-risk prose
  -> bounded context pack + omissions + cost ledger
```

## Safety defaults

- Code, commands, errors, versions, URLs, citations, tables, contracts, and financial facts are never rewritten by the compressor.
- Uncertain scans and layouts keep the original source.
- External adapters are explicit and replaceable.
- GPU stages run sequentially on a single 16 GB card unless measured otherwise.
- Estimated token counts are never presented as provider billing telemetry.

## Quick start

```powershell
$env:PYTHONPATH='src'
python -m token_forge doctor --config .token-forge.local.toml
python -m token_forge convert `
  --input path\to\source.pdf `
  --output path\to\result `
  --config .token-forge.local.toml
python -m token_forge optimize `
  --input path\to\canonical.md `
  --query "the task to answer" `
  --budget 2000 `
  --output path\to\context-pack `
  --config .token-forge.local.toml
python -m token_forge benchmark-acceptance `
  --manifest benchmarks\acceptance-manifest.json `
  --output benchmark-acceptance-results `
  --config .token-forge.local.toml
```

`convert` routes local HTML through Defuddle, and documents/PDF through MarkItDown with Docling available as an explicit fallback. A successful run writes `canonical.md` and `conversion.json`. The ledger records the source SHA-256, selected adapter and version, timings, every attempted fallback, verification level, and protected-literal recall. HTML and DOCX/PPTX can be source-literal checked; binary PDF conversion is currently reported as `output-only` unless an independent source extractor is configured. If a source-literal converter drops a protected version, date, URL, number, or command, Token Forge rejects the Markdown instead of silently presenting it as successful.

`doctor` reports command installation separately from `conversion_gates` and `model_gates`, so an installed executable or partial model directory is not presented as ready. `model_gates.*.eligible` means the configured runtime, model config, and substantial weight file are present; it remains `validated: false` until an explicit offline load test is recorded.

`optimize` assigns stable content-derived chunk IDs, runs BGE-M3 dense retrieval and BGE reranking in an isolated local process, and only then considers LLMLingua-2 when selected low-risk prose still exceeds the budget. Learned output is rejected if it is empty, exceeds the budget, or drops a protected number, date, version, URL, command, or citation literal. Code, commands, contracts, tables, financial material, and security evidence bypass learned models. Any model failure falls back visibly to the deterministic selector and records the reason in `model-ledger.json`. Helpers force Hugging Face and Transformers offline mode; they never acquire models during an `optimize` run.

Protected blocks are never sent to LLMLingua-2. They are reattached verbatim around compressed low-risk prose, then the complete output must pass both protected-literal recall and the Token Forge hard budget. This avoids treating the compressor's tokenizer count as equivalent to the project's conservative estimate.

Dynamic pages can be rendered locally with `python -m token_forge web --url <https-url> --output <dir>`. The command stores the rendered HTML, a viewport screenshot, browser metadata, and the Defuddle conversion ledger. It requires configured Playwright browser assets; no remote page content is sent to a service by Token Forge itself.

Local audio/video can be processed with `python -m token_forge media --input <file> --output <dir>`. The route extracts 16 kHz mono audio with FFmpeg, transcribes with the configured local faster-whisper model, and records PySceneDetect scenes/keyframes when available. CUDA is attempted first; if the configured environment cannot load CUDA libraries, the helper visibly falls back to CPU int8. Platform URLs remain metadata/subtitle workflows and never download media implicitly; use `python -m token_forge platform-media --url <https-url> --output <dir>` for that route. It records `yt-dlp --dump-single-json` metadata and optional subtitles, while media download is intentionally unsupported.

Image-only PDF is not treated as an empty success. If MarkItDown finds no text and no local OCR model is eligible, `convert` returns `needs-ocr` with exit code `4`, keeps the source, and does not write `canonical.md`. A configured local MinerU pipeline can then run `pipeline + ocr` in an isolated staging directory. Remote model acquisition remains opt-in.

Adapter processes run in isolated process groups. On Windows they are attached to a kill-on-close Job Object before execution begins, so a converter timeout or a completed parent process cannot leave pipe-inheriting workers behind. Output is captured through temporary files rather than unbounded in-memory pipes.

## Verified acceptance status

The checked full-scenario v1 suite passed all **13 / 13 required scenarios** through real local adapters. Across required cases it recovered **37 / 37 protected facts**, **9 / 9 expected anchors**, and **9 / 9 table cells**; two controlled OCR fixtures measured **0.00% mean CER**, while generated English audio/video measured **5.88% mean WER** with **6 / 6 transcript facts** recovered. The full manifest keeps two unsupported capability probes (EML and ZIP) as failures and one public-platform network case as `Pending`.

See the [full benchmark method and claim boundaries](docs/BENCHMARK.md), [中文说明](docs/BENCHMARK.zh-CN.md), and [raw checked results](benchmarks/results/acceptance-v1). These fixture-specific measurements are not universal accuracy, provider telemetry, or a promise of the same reduction on other material.

## Evidence before claims

The fixed seven-case benchmark currently reports:

| Case | Route | Estimated input → final | Estimated reduction | Declared evidence recall |
|---|---|---:|---:|---:|
| Long redundant brief | Retrieved | 509 → 82 | 83.89% | 1.00 |
| Release migration | Retrieved | 106 → 65 | 38.68% | 1.00 |
| Short dense error | Pass-through | 22 → 22 | 0% | 1.00 |
| Budget conflict | Source fallback | 35 → 35 | 0% | 1.00 |
| Code / contract / table | Safety pass-through | unchanged | 0% | 1.00 |

These are deterministic estimates on repository fixtures, not provider billing telemetry, universal accuracy, or a promise of the same saving on other material. Run the benchmark on your own corpus before enabling an adapter.

The separate four-case local-model benchmark reports:

| Case | Route | Estimated input → final | Estimated reduction | Declared evidence recall |
|---|---|---:|---:|---:|
| Release migration | BGE + reranker + LLMLingua-2 | 106 → 68 | 35.85% | 1.00 |
| Long retrieval | BGE + reranker + LLMLingua-2 | 509 → 85 | 83.30% | 1.00 |
| Low-risk prose | BGE + reranker + LLMLingua-2 | 147 → 55 | 62.59% | 1.00 |
| Code | Safety pass-through | 91 → 91 | 0% | 1.00 |

See [`benchmarks/results/model-results.json`](benchmarks/results/model-results.json). The model run is also fixture-specific and uses deterministic token estimates rather than provider billing telemetry.

The separate scanned-PDF smoke uses a one-page bilingual raster fixture with no text layer. On the checked Windows host, MarkItDown correctly returned empty output and MinerU 3.4.5 completed the OCR fallback in 27.877 seconds; the full command exited successfully in 33.693 seconds. After NFKC normalization and removal of Markdown heading markers and whitespace, the 100-character reference had edit distance `0` (CER `0.00%`), and all five protected facts were recovered exactly. See [`benchmarks/results/mineru-bilingual-scan.json`](benchmarks/results/mineru-bilingual-scan.json). This is evidence for that clear synthetic page only, not a general OCR or token-saving claim.

The local dynamic-page smoke completed through Playwright Chromium 1234 -> Defuddle with source-literal recall `1.0`, leaving rendered HTML, viewport PNG, and metadata. After the helper began discovering the existing local cublas and cuDNN DLL directories, the complete local media smoke processed a 14.23-second video in 5.486 seconds, produced 10 timestamped transcript segments, 7 scene groups, and 21 keyframes, and recorded `cuda`, `float16`, `fallback: false`. This is evidence for the checked host and fixture only, not a general speed or WER claim.

```powershell
$env:PYTHONPATH='src'
python -m token_forge benchmark --manifest benchmarks\manifest.json --output benchmark-results
```
