# Adapter selection

Use repository `docs/DEPENDENCIES.md` as the versioned selection matrix. External executables and models remain optional, isolated, and explicitly configured. Never install them during a Skill run.

Docling additionally requires `adapters.docling_artifacts` to point at pre-cached local model artifacts when `runtime.allow_remote` is `false` (the default). Do not enable remote model fetching merely because the executable is installed.
