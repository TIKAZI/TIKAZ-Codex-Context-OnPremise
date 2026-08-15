# Local installation status (2026-08-15)

## Package and command layer

| Adapter | Installed version | Command/import smoke | Model/quality gate |
|---|---:|---|---|
| MarkItDown | 0.1.7 | passed on local HTML | pending representative PDF/Office fixtures |
| Docling | 2.120.1 | command/version passed; HTML model init did not finish in window | pending |
| MinerU | 3.4.5 | command/version passed | model download and complex-PDF gate pending |
| PaddleOCR | 3.7.0 + PaddlePaddle 3.3.1 | command/version passed | model download and OCR gate pending; CPU baseline |
| Defuddle | 0.19.2 | passed on local HTML | dynamic-page gate pending |
| Playwright | 1.62.1 + Chromium 151 | real headless launch passed | dynamic-page fixture pending |
| yt-dlp | 2026.07.04 | version passed | authorized platform fixture pending |
| PySceneDetect | 0.7.1 | version passed | real video fixture pending |
| faster-whisper | existing large-v3 | doctor passed | existing local workflow remains baseline |
| FlagEmbedding / Sentence Transformers | 1.4.0 / 5.7.0 | import passed | embedding weights pending |
| LLMLingua | 0.2.2 | import passed | model and low-risk quality gate pending |

## Model download boundary

The BGE-M3 download was attempted twice on G: and stopped after a stale-lock/no-progress condition. The partial directories are not considered usable and doctor reports the embedding model as unavailable. BM25 remains the measured retrieval fallback. No percentage or retrieval quality claim is made from the partial model.

## Storage policy

- Environments and model weights: `G:\CodexTools\token-forge` and `G:\CodexTools\models\token-forge`.
- Sources, caches, and outputs: `F:\TIKAZ-Token-Forge-Data`.
- Local absolute paths are ignored and are not committed.

## Why “installed” is not “ready”

A package can import while its model weights, OCR language packs, browser runtime, or quality gate is missing. Token Forge exposes these states separately and routes to source preservation until the relevant gate passes.
