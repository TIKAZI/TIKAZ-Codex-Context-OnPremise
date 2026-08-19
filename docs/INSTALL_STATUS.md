# Local installation status (2026-08-19)

## Package and command layer

| Adapter | Installed version | Command/import smoke | Model/quality gate |
|---|---:|---|---|
| MarkItDown | 0.1.7 | HTML fallback and PDF conversion passed | PDF/Office source-literal gate pending |
| Docling | 2.120.1 | command/version passed; PDF smoke timed out while fetching layout model | disabled without local artifacts; remote fetch requires explicit opt-in |
| MinerU | 3.4.5 | local `pipeline + ocr` route passed one fixed clear scan | degraded, rotated, table, figure, and real-document gates pending |
| PaddleOCR | 3.7.0 + PaddlePaddle 3.3.1 | CLI exposes Office `doc2md` and cloud API | installed CLI is not a local scanned-PDF OCR route |
| Defuddle | 0.19.2 | primary CLI adapter passed on fixed local HTML | dynamic-page gate pending |
| Playwright | 1.62.1 + Chromium 1234 local assets | dynamic-page render + Defuddle smoke passed | authenticated/private pages and broader dynamic fixtures pending |
| yt-dlp | 2026.07.04 | version passed | authorized platform fixture pending |
| PySceneDetect | 0.7.1 | real local video produced 7 scenes and 21 keyframes | broader codec/transition fixtures pending |
| faster-whisper | existing large-v3 | local CUDA DLL discovery repaired; full 14.23-second media route passed in 5.486 seconds | broader WER/language fixtures pending |
| FlagEmbedding / Sentence Transformers | 1.4.0 / 5.7.0 | import passed | embedding weights pending |
| LLMLingua | 0.2.2 | import passed | model and low-risk quality gate pending |

## Model download boundary

The three approved local models are downloading to G: with resumable Hugging Face transfers. Partial directories are not considered usable and doctor reports them as unavailable until the config and substantial weight files are complete, followed by an explicit offline load and fixed quality gate. BM25/deterministic selection remains the measured fallback. No percentage or retrieval quality claim is made from partial models.

## Verified conversion slice

The fixed `tests/fixtures/web-article.html` smoke passed through Defuddle 0.19.2. The generated Markdown retained the declared version `v9.2.1`, date `2026-12-01`, and command `python migrate.py --target v9.2.1`; the conversion ledger reported protected-literal recall `1.0`. This proves the checked fixture only. Dynamic pages, arbitrary websites, PDF, Office, OCR, tables, and image fidelity remain separate gates.

The local PDF smoke passed through MarkItDown 0.1.7 in about 2 seconds. Because the current controller has no independent PDF text extractor configured, its ledger correctly reports `verification_level: output-only` and `protected_recall: null`; an independent pypdf check of this synthetic sample matched the generated Markdown, but that check is not generalized into the adapter claim. Docling 2.120.1 was invoked with OCR and table models disabled and timed out after 180 seconds while fetching a layout model, so it remains a fallback candidate rather than an enabled default.

With the default `allow_remote=false`, the controller refuses Docling unless `adapters.docling_artifacts` points to pre-cached local artifacts.

The fixed image-only PDF was rendered and visually inspected, and pypdf confirmed that it had no text layer. MarkItDown returned empty output; Token Forge then returned `needs-ocr` with exit code `4`, wrote only the failure ledger, and did not invoke MinerU because no local `mineru_config` was present. This verifies routing and source preservation, not OCR accuracy.

After local MinerU pipeline models were configured, the bilingual image-only fixture completed through the full automatic route: MarkItDown `empty-output` -> MinerU `pipeline + ocr` -> `canonical.md`. MinerU took 27.877 seconds and the complete command took 33.693 seconds with exit code `0`. The 100-character normalized reference produced edit distance `0` (CER `0.00%`) and exact recall `5/5` for the declared version, date, command, order ID, and amount. The ledger remains correctly marked `verification_level: output-only` and `protected_recall: null` because the controller does not treat OCR output as an independent source oracle. The checked fixture and machine-readable result are committed under `benchmarks/`; this does not establish performance on degraded or real-world scans.

The first real run exposed a Windows process-lifecycle defect: MinerU wrote its Markdown but inherited output pipes prevented the command from completing. The runner now captures output through temporary files and places Windows adapters in a kill-on-close Job Object before resuming them. Regression tests cover both timeout cleanup and the case where a short-lived parent exits before a pipe-inheriting child.

The dynamic-page smoke now uses the cached local Chromium 1234 assets under `G:\CodexTools\models\token-forge\playwright`; the first attempt correctly failed when that browser path was not exported, then passed after the local path was configured. The media smoke used `F:\CodexVideoSummary\data\media\BV1TU3g66Exd.mp4` as a read-only source and wrote its transcript, scene CSV, and keyframes under `F:\TIKAZ-Token-Forge-Data\outputs\media-smoke-cpu2`.

The configured BGE-M3, reranker, and LLMLingua model directories remain unavailable while their approved one-time downloads and fixed local quality gates are incomplete. Runtime optimization itself forces offline mode and cannot fetch a model. BM25/deterministic extraction remains the only publishable retrieval/compression path until those gates pass.

The same local media fixture was rerun after adding Windows DLL discovery for the existing NVIDIA cublas and cuDNN packages in the Whisper environment. The complete media command finished in 5.486 seconds and wrote `transcription-runtime.json` with `device: cuda`, `compute_type: float16`, and `fallback: false`, alongside 10 timestamped transcript segments and 21 keyframes. This supersedes the earlier CPU-fallback diagnosis for the checked host and fixture; it is not a general speed or WER claim.

## Storage policy

- Environments and model weights: `G:\CodexTools\token-forge` and `G:\CodexTools\models\token-forge`.
- Sources, caches, and outputs: `F:\TIKAZ-Token-Forge-Data`.
- Local absolute paths are ignored and are not committed.

## Why “installed” is not “ready”

A package can import while its model weights, OCR language packs, browser runtime, or quality gate is missing. Token Forge exposes these states separately and routes to source preservation until the relevant gate passes.
