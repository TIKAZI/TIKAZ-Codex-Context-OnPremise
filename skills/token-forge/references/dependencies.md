# Adapter selection

Use repository `docs/DEPENDENCIES.md` as the versioned selection matrix. External executables and models remain optional, isolated, and explicitly configured. Never install them during a Skill run.

Docling additionally requires `adapters.docling_artifacts` to point at pre-cached local model artifacts when `runtime.allow_remote` is `false` (the default). Do not enable remote model fetching merely because the executable is installed.

MinerU requires `adapters.mineru_config` to point at a local `mineru.json` with a valid pipeline model directory when remote access is disabled. The installed PaddleOCR 3.7 CLI exposes Office `doc2md` and cloud API commands; do not route local scanned PDF to it unless a separately verified local OCR entry point is configured.
