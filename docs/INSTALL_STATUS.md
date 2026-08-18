# Local installation status (2026-08-18)

## Package and command layer

| Adapter | Installed version | Command/import smoke | Model/quality gate |
|---|---:|---|---|
| MarkItDown | 0.1.7 | HTML fallback and PDF conversion passed | PDF/Office source-literal gate pending |
| Docling | 2.120.1 | command/version passed; PDF smoke timed out while fetching layout model | disabled without local artifacts; remote fetch requires explicit opt-in |
| MinerU | 3.4.5 | CLI adapter implemented for `pipeline + ocr` | local pipeline models and OCR quality gate pending |
| PaddleOCR | 3.7.0 + PaddlePaddle 3.3.1 | CLI exposes Office `doc2md` and cloud API | installed CLI is not a local scanned-PDF OCR route |
| Defuddle | 0.19.2 | primary CLI adapter passed on fixed local HTML | dynamic-page gate pending |
| Playwright | 1.62.1 + Chromium 151 | real headless launch passed | dynamic-page fixture pending |
| yt-dlp | 2026.07.04 | version passed | authorized platform fixture pending |
| PySceneDetect | 0.7.1 | version passed | real video fixture pending |
| faster-whisper | existing large-v3 | doctor passed | existing local workflow remains baseline |
| FlagEmbedding / Sentence Transformers | 1.4.0 / 5.7.0 | import passed | embedding weights pending |
| LLMLingua | 0.2.2 | import passed | model and low-risk quality gate pending |

## Model download boundary

The BGE-M3 download was attempted twice on G: and stopped after a stale-lock/no-progress condition. The partial directories are not considered usable and doctor reports the embedding model as unavailable. BM25 remains the measured retrieval fallback. No percentage or retrieval quality claim is made from the partial model.

## Verified conversion slice

The fixed `tests/fixtures/web-article.html` smoke passed through Defuddle 0.19.2. The generated Markdown retained the declared version `v9.2.1`, date `2026-12-01`, and command `python migrate.py --target v9.2.1`; the conversion ledger reported protected-literal recall `1.0`. This proves the checked fixture only. Dynamic pages, arbitrary websites, PDF, Office, OCR, tables, and image fidelity remain separate gates.

The local PDF smoke passed through MarkItDown 0.1.7 in about 2 seconds. Because the current controller has no independent PDF text extractor configured, its ledger correctly reports `verification_level: output-only` and `protected_recall: null`; an independent pypdf check of this synthetic sample matched the generated Markdown, but that check is not generalized into the adapter claim. Docling 2.120.1 was invoked with OCR and table models disabled and timed out after 180 seconds while fetching a layout model, so it remains a fallback candidate rather than an enabled default.

With the default `allow_remote=false`, the controller refuses Docling unless `adapters.docling_artifacts` points to pre-cached local artifacts.

The fixed image-only PDF was rendered and visually inspected, and pypdf confirmed that it had no text layer. MarkItDown returned empty output; Token Forge then returned `needs-ocr` with exit code `4`, wrote only the failure ledger, and did not invoke MinerU because no local `mineru_config` was present. This verifies routing and source preservation, not OCR accuracy.

## Storage policy

- Environments and model weights: `G:\CodexTools\token-forge` and `G:\CodexTools\models\token-forge`.
- Sources, caches, and outputs: `F:\TIKAZ-Token-Forge-Data`.
- Local absolute paths are ignored and are not committed.

## Why “installed” is not “ready”

A package can import while its model weights, OCR language packs, browser runtime, or quality gate is missing. Token Forge exposes these states separately and routes to source preservation until the relevant gate passes.
