# TIKAZ Context On-Premise for Codex

<p align="center"><strong>Local-first multimodal context compilation that optimizes evidence hit quality and context cost together.</strong></p>

<p align="center">
  <a href="README.zh-CN.md">简体中文</a> ·
  <a href="docs/RESULTS.md">Measured results</a> ·
  <a href="docs/BENCHMARK.md">Method</a> ·
  <a href="CONTRIBUTING.md">Contributing</a>
</p>

<p align="center">
  <a href="https://github.com/TIKAZI/TIKAZ-Codex-Context-OnPremise/actions/workflows/validate.yml"><img src="https://github.com/TIKAZI/TIKAZ-Codex-Context-OnPremise/actions/workflows/validate.yml/badge.svg" alt="validation" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-60A5FA.svg" alt="MIT License" /></a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-A78BFA.svg" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/inference-local--first-60A5FA.svg" alt="local-first" />
</p>

| 20 / 20 | 89.57% | 53 / 53 | 37 / 37 |
|---:|---:|---:|---:|
| fixed acceptance scenarios passed | estimated token-weighted reduction on 7 context fixtures | declared protected facts retained | visual facts recovered on 12 synthetic images |

These values belong to versioned repository fixtures. They are not universal accuracy, provider billing telemetry, or a promise of equal savings on other material; failed and Pending evidence remains public.

Designed, integrated, independently implemented, and continuously maintained by **TIKAZ**. The Python engine and CLI retain the internal name **Token Forge**.

Context On-Premise is the explicit `ON` route in the TIKAZ context workflow family and the dependency-rich counterpart to portable [Context Economy](https://github.com/TIKAZI/TIKAZ-Codex-Context-Economy). It does not promise a fixed reduction percentage. It searches for the best measured quality/cost point for each source and task.

## Pipeline

```text
files / webpages / media / code / conversations
  -> immutable source + content hash
  -> routed converter or transcriber
  -> canonical Markdown + structured evidence
  -> exact text/frame duplicate control
  -> local PP-OCRv5 + Qwen3-VL visual evidence when needed
  -> low-confidence frames only -> bounded Codex handoff
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
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start_local_vision.ps1
python -m token_forge benchmark-visual `
  --manifest benchmarks\visual-manifest.json `
  --frames F:\TIKAZ-Token-Forge-Data\fixtures\visual-v1 `
  --output F:\TIKAZ-Token-Forge-Data\outputs\visual-benchmark `
  --config .token-forge.local.toml
```

`convert` routes local HTML through Defuddle, and documents/PDF through MarkItDown with Docling available as an explicit fallback. A successful run writes `canonical.md` and `conversion.json`. The ledger records the source SHA-256, selected adapter and version, timings, every attempted fallback, verification level, and protected-literal recall. HTML and DOCX/PPTX can be source-literal checked; binary PDF conversion is currently reported as `output-only` unless an independent source extractor is configured. If a source-literal converter drops a protected version, date, URL, number, or command, Token Forge rejects the Markdown instead of silently presenting it as successful.

`doctor` reports command installation separately from `conversion_gates`, `model_gates`, and `visual_gates`, so an installed executable or partial model directory is not presented as ready. `model_gates.*.eligible` means the configured runtime, model config, and substantial weight file are present; it remains `validated: false` until an explicit offline load test is recorded. `visual_gates` distinguishes `not-configured`, `configured-unvalidated`, and fixture-validated local vision from the always-available hash handoff and opt-in-only remote vision.

`optimize` assigns stable content-derived chunk IDs, runs BGE-M3 dense retrieval and BGE reranking in an isolated local process, and only then considers LLMLingua-2 when selected low-risk prose still exceeds the budget. Learned output is rejected if it is empty, exceeds the budget, or drops a protected number, date, version, URL, command, or citation literal. Code, commands, contracts, tables, financial material, and security evidence bypass learned models. Any model failure falls back visibly to the deterministic selector and records the reason in `model-ledger.json`. Helpers force Hugging Face and Transformers offline mode; they never acquire models during an `optimize` run.

Retrieval quality is measured independently from compression. Dependency-free ContextEconomy v2 reached **100% Recall@5 / 100% Precision@5** on the committed 14-case bilingual development manifest. A separately frozen 12-case adversarial challenge reached **94.44% Recall@3 / 94.44% Precision@3**, with both misses retained in the raw cases. Conservative dynamic selection paired **100% selected-evidence recall** with **28.77% estimated candidate-text reduction** on the development set; the challenge paired **94.44% recall** with **39.01% estimated reduction**. These fixture results are not universal search accuracy, downstream-answer correctness, or Provider Token telemetry. See [`docs/RETRIEVAL_QUALITY.md`](docs/RETRIEVAL_QUALITY.md) and the raw result directories.

The committed Context On-Premise v1 same-manifest retrieval row remains historical. Current v2 fusion reruns timed out on the checked host, so v2 On-Premise retrieval quality and runtime are explicitly **Pending** rather than advertised with the older percentage.

Protected blocks are never sent to LLMLingua-2. They are reattached verbatim around compressed low-risk prose, then the complete output must pass both protected-literal recall and the Token Forge hard budget. This avoids treating the compressor's tokenizer count as equivalent to the project's conservative estimate.

Dynamic pages can be rendered locally with `python -m token_forge web --url <https-url> --output <dir>`. The command stores the rendered HTML, a viewport screenshot, browser metadata, and the Defuddle conversion ledger. It requires configured Playwright browser assets; no remote page content is sent to a service by Token Forge itself.

Local audio/video can be processed with `python -m token_forge media --input <file> --output <dir> --max-visual-frames 12`. The route extracts 16 kHz mono audio with FFmpeg, transcribes with the configured local faster-whisper model, records PySceneDetect scenes/keyframes, suppresses byte-identical frames, and writes a bounded, hash-anchored `visual-evidence.json`. Distinct scenes are covered before extra samples. When loopback Ollama and PP-OCRv5 are configured, selected frames are resolved locally and only low-confidence, empty, ambiguous, or failed results become `needs-codex`; without that pair they remain `pending-vision`. Model-reported confidence is only a routing signal, never an accuracy claim. CUDA is attempted first for ASR; if the configured environment cannot load CUDA libraries, the helper visibly falls back to CPU int8. Platform URLs remain metadata/subtitle workflows and never download media implicitly; use `python -m token_forge platform-media --url <https-url> --output <dir>` for that route. It records `yt-dlp --dump-single-json` metadata and optional subtitles, while media download is intentionally unsupported.

Run local visual resolution directly with `python -m token_forge visual-analyze --manifest <visual-evidence.json> --config .token-forge.local.toml`. Every request is restricted to HTTP loopback, uses structured output, preserves OCR separately, and records the local model's prompt count and duration without calling them Codex savings. If Codex review is still required, save hash-anchored observations and validate them with `python -m token_forge visual-evidence --frames <dir> --output <dir> --annotations <annotations.json>`. The command rejects observations that do not resolve to a selected frame. See [`skills/context-onpremise/references/visual-evidence.md`](skills/context-onpremise/references/visual-evidence.md) for the schema and claim boundary.

Image-only PDF is not treated as an empty success. If MarkItDown finds no text and no local OCR model is eligible, `convert` returns `needs-ocr` with exit code `4`, keeps the source, and does not write `canonical.md`. A configured local MinerU pipeline can then run `pipeline + ocr` in an isolated staging directory. Remote model acquisition remains opt-in.

Adapter processes run in isolated process groups. On Windows they are attached to a kill-on-close Job Object before execution begins, so a converter timeout or a completed parent process cannot leave pipe-inheriting workers behind. Output is captured through temporary files rather than unbounded in-memory pipes.

## Verified acceptance status

> **Browse every measured scenario:** [complete results table](docs/RESULTS.md) · [benchmark method](docs/BENCHMARK.md) · [中文说明](docs/BENCHMARK.zh-CN.md)

The checked full-scenario v1 suite passed all **18 / 18 required scenarios** and **20 / 20 total scenarios**. Across required cases it recovered **51 / 51 protected facts**, **11 / 11 expected anchors**, and **9 / 9 table cells**; across all checked conversion/text cases protected-fact recall was **53 / 53**. Seven context cases measured **89.57% token-weighted reduction** and **55.96% macro mean**, keeping the two intentional small-input safety pass-throughs visible. The fixed scale fixtures measured **81.53%** for deterministic long text, **91.05%** for an exact Python AST dependency slice, and **97.15%** for a reconciled 500-row CSV aggregate. These are deterministic estimates on generated fixtures, not provider telemetry or universal savings.

Two controlled OCR fixtures measured **0.00% mean CER**, while generated English audio/video measured **5.88% mean WER** with **6 / 6 transcript facts** recovered. The fixed video produced six source keyframes; exact SHA-256 deduplication selected two and skipped four duplicates, reducing duplicate frame processing by **66.67%** on that fixture. This is frame-routing evidence, not image-token telemetry or perceptual deduplication.

The separate 12-image visual suite recovered **37 / 37 protected facts** through PP-OCRv5, **37 / 37** independently through Qwen3-VL 8B, and **37 / 37** in the combined route. It resolved **12 / 12** cases locally and classified **10 / 12** dominant frame types correctly. Two identical-setting runs produced the same per-case fact and type results; Ollama reported 48.85 and 48.75 seconds of aggregate local VLM duration. The two stable type errors were flat UI mockups classified as documents. The explicit-network public-platform metadata case also passed in 2.650 seconds; no subtitle track was available, and no media was downloaded. These fixed synthetic fixtures do not establish real-world visual accuracy, downstream answer quality, or Codex image-token savings; provider image-token telemetry remains `Pending`. EML uses the standard-library email parser, while ZIP is read in place through bounded inventory/text extraction without writing archive members to disk.

See the [full benchmark method and claim boundaries](docs/BENCHMARK.md), [中文说明](docs/BENCHMARK.zh-CN.md), [acceptance results](benchmarks/results/acceptance-v1), and [visual results](benchmarks/results/visual-v1). These fixture-specific measurements are not universal accuracy, provider telemetry, or a promise of the same reduction on other material.

## Evidence before claims

The fixed seven-case benchmark currently reports:

| Case | Route | Estimated input → final | Estimated reduction | Declared evidence recall |
|---|---|---:|---:|---:|
| Long redundant brief | Retrieved | 509 → 82 | 83.89% | 1.00 |
| Release migration | Retrieved | 106 → 53 | 50.00% | 1.00 |
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
