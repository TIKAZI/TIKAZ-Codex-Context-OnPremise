# Local installation status (2026-08-20)

## Package and command layer

| Adapter | Installed version | Command/import smoke | Model/quality gate |
|---|---:|---|---|
| MarkItDown | 0.1.7 | DOCX, PPTX, XLSX, EPUB, HTML fallback, and born-digital PDF passed | binary PDF remains output-only without an independent source extractor |
| Docling | 2.120.1 | command/version passed; PDF smoke timed out while fetching layout model | disabled without local artifacts; remote fetch requires explicit opt-in |
| MinerU | 3.4.5 | local `pipeline + ocr` route passed one fixed clear scan | degraded, rotated, table, figure, and real-document gates pending |
| PaddleOCR | 3.7.0 + PaddlePaddle 3.3.1 | CLI exposes Office `doc2md` and cloud API | installed CLI is not a local scanned-PDF OCR route |
| Defuddle | 0.19.2 | static HTML and Playwright-rendered dynamic-page fixtures passed | arbitrary/authenticated sites pending |
| Playwright | 1.62.1 + Chromium 1234 local assets | dynamic-page render + Defuddle smoke passed | authenticated/private pages and broader dynamic fixtures pending |
| yt-dlp | 2026.07.04 | version passed | authorized platform fixture pending |
| PySceneDetect | 0.7.1 | real local video produced 7 scenes and 21 keyframes | broader codec/transition fixtures pending |
| faster-whisper | existing large-v3 | CUDA media route and generated English audio/video WER fixtures passed | multilingual, noisy, and long-form WER fixtures pending |
| FlagEmbedding / Sentence Transformers | 1.4.0 / 5.7.0 | BGE-M3 and BGE reranker loaded fully offline | fixed retrieval/reranking fixtures passed |
| LLMLingua | 0.2.2 | local XLM-RoBERTa model loaded and compressed prose offline | fixed low-risk compression fixtures passed |

## Model download boundary

The three approved local models are complete on G: and passed offline loading. BGE-M3 produced 1024-dimensional normalized embeddings; on the checked smoke, migration evidence scored `0.8559` against the migration query and unrelated design background scored `0.3751`. The BGE reranker scored the related pair `0.1691` and the unrelated pair `0.0000229`. These two-pair checks establish loading and ordering direction only, not general retrieval quality.

## Full-scenario acceptance gate

The versioned v1 manifest ran 17 cases. All 15 required local routes passed, and the complete local set passed 16/16. Required-case denominators were 41 protected facts, 9 source anchors, and 9 table cells, each with recall `1.0`. Two controlled OCR fixtures measured mean CER `0.00%`; generated English audio and video measured mean WER `5.88%`, transcript fact recall `6/6`, and the video produced six keyframes. Four comparable text cases averaged `30.49%` deterministic estimated-token reduction, including two intentional 0% high-risk pass-through cases.

EML and bounded ZIP now pass their declared local source-literal gates. The opt-in public-platform case remains `Pending`. See `docs/BENCHMARK.md` and `benchmarks/results/acceptance-v1`. These figures are fixture-specific and do not establish provider billing savings, general OCR/layout fidelity, visual understanding, authenticated-site support, or multilingual/noisy ASR quality.

## Verified conversion slice

The fixed `tests/fixtures/web-article.html` smoke passed through Defuddle 0.19.2. The generated Markdown retained the declared version `v9.2.1`, date `2026-12-01`, and command `python migrate.py --target v9.2.1`; the conversion ledger reported protected-literal recall `1.0`. This proves the checked fixture only. Dynamic pages, arbitrary websites, PDF, Office, OCR, tables, and image fidelity remain separate gates.

The local PDF smoke passed through MarkItDown 0.1.7 in about 2 seconds. Because the current controller has no independent PDF text extractor configured, its ledger correctly reports `verification_level: output-only` and `protected_recall: null`; an independent pypdf check of this synthetic sample matched the generated Markdown, but that check is not generalized into the adapter claim. Docling 2.120.1 was invoked with OCR and table models disabled and timed out after 180 seconds while fetching a layout model, so it remains a fallback candidate rather than an enabled default.

With the default `allow_remote=false`, the controller refuses Docling unless `adapters.docling_artifacts` points to pre-cached local artifacts.

The fixed image-only PDF was rendered and visually inspected, and pypdf confirmed that it had no text layer. MarkItDown returned empty output; Token Forge then returned `needs-ocr` with exit code `4`, wrote only the failure ledger, and did not invoke MinerU because no local `mineru_config` was present. This verifies routing and source preservation, not OCR accuracy.

After local MinerU pipeline models were configured, the bilingual image-only fixture completed through the full automatic route: MarkItDown `empty-output` -> MinerU `pipeline + ocr` -> `canonical.md`. MinerU took 27.877 seconds and the complete command took 33.693 seconds with exit code `0`. The 100-character normalized reference produced edit distance `0` (CER `0.00%`) and exact recall `5/5` for the declared version, date, command, order ID, and amount. The ledger remains correctly marked `verification_level: output-only` and `protected_recall: null` because the controller does not treat OCR output as an independent source oracle. The checked fixture and machine-readable result are committed under `benchmarks/`; this does not establish performance on degraded or real-world scans.

The first real run exposed a Windows process-lifecycle defect: MinerU wrote its Markdown but inherited output pipes prevented the command from completing. The runner now captures output through temporary files and places Windows adapters in a kill-on-close Job Object before resuming them. Regression tests cover both timeout cleanup and the case where a short-lived parent exits before a pipe-inheriting child.

The dynamic-page smoke now uses the cached local Chromium 1234 assets under `G:\CodexTools\models\token-forge\playwright`; the first attempt correctly failed when that browser path was not exported, then passed after the local path was configured. The media smoke used `F:\CodexVideoSummary\data\media\BV1TU3g66Exd.mp4` as a read-only source and wrote its transcript, scene CSV, and keyframes under `F:\TIKAZ-Token-Forge-Data\outputs\media-smoke-cpu2`.

The fixed four-case model benchmark completed three low-risk model routes and one code safety pass-through. Estimated input to final tokens were `106 -> 68`, `509 -> 85`, `147 -> 55`, and `91 -> 91`; declared protected-fact recall was `1.0` for every case. `doctor.model_gates` reports both retrieval and learned compression as `validated: true` when pointed at this local report. See `benchmarks/results/model-results.json`. These are fixture-specific deterministic estimates, not provider telemetry or a universal saving/accuracy claim.

The same local media fixture was rerun after adding Windows DLL discovery for the existing NVIDIA cublas and cuDNN packages in the Whisper environment. The complete media command finished in 5.486 seconds and wrote `transcription-runtime.json` with `device: cuda`, `compute_type: float16`, and `fallback: false`, alongside 10 timestamped transcript segments and 21 keyframes. This supersedes the earlier CPU-fallback diagnosis for the checked host and fixture; it is not a general speed or WER claim.

## Storage policy

- Environments and model weights: `G:\CodexTools\token-forge` and `G:\CodexTools\models\token-forge`.
- Sources, caches, and outputs: `F:\TIKAZ-Token-Forge-Data`.
- Local absolute paths are ignored and are not committed.

## Why “installed” is not “ready”

A package can import while its model weights, OCR language packs, browser runtime, or quality gate is missing. Token Forge exposes these states separately and routes to source preservation until the relevant gate passes.
