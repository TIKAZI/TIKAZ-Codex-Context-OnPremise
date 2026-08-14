# Specification: TIKAZ Codex Token Forge

## Objective

Create a personal, local-first context workflow that may use many external dependencies to reduce the material sent to Codex while preserving task accuracy, literal facts, evidence anchors, and recoverability.

Success is a measured Pareto improvement over raw upload: fewer actual or estimated input tokens without a regression beyond declared thresholds. A fixed 90% saving is not a product promise.

## Initial commands

```powershell
python -m token_forge doctor
python -m token_forge profile --input <path> --query <task>
python -m token_forge pack --input <path> --query <task> --budget 4000 --output <dir> --cache-dir <cache>
python -m token_forge benchmark --manifest benchmarks\manifest.json --output benchmark-results
```

## Architecture

1. Preserve the source and compute a content hash.
2. Profile source type, size, risk, layout, visual content, and available adapters.
3. Route to the lowest-cost adapter that meets the quality gate.
4. Produce canonical Markdown plus structured provenance; never flatten uncertain evidence silently.
5. Remove exact or formatting-only duplication before semantic methods.
6. Retrieve with lexical and dense signals, rerank, and protect literal evidence.
7. Apply learned compression only to low-risk prose and only when its benchmark profile passes.
8. Emit a context pack, omissions, source anchors, adapter versions, timing, and token ledger.

## Direct adapter families

- Documents: MarkItDown, Docling, MinerU, PaddleOCR; Marker remains an evaluated fallback pending version-specific license review.
- Web: Defuddle, Mozilla Readability, Playwright.
- Media: existing FFmpeg + faster-whisper large-v3 CUDA float16; later WhisperX, pyannote, and PySceneDetect.
- Retrieval: SQLite FTS5/BM25, BGE-M3, a domain-tested reranker, and optional Qdrant.
- Compression: exact/near deduplication first; LLMLingua-2 only for eligible prose.

## Testing strategy

- Unit tests: routing, protected literals, deduplication, budgeting, cost ledger.
- Integration tests: adapter discovery and fixed local fixtures without network access.
- Benchmark: raw, converted, retrieved, and retrieved-plus-compressed paths.
- Quality metrics: protected-fact recall, anchor recall, table-cell recall, citation grounding, retrieval recall, downstream answer score, input tokens, latency, and peak VRAM.

## Boundaries

### Always

- Keep original sources and stable anchors.
- Report omissions and unavailable adapters.
- Cache by source hash, adapter version, and configuration.
- Serialize GPU-heavy stages on the verified RTX 5060 Ti 16 GB.

### Ask first

- Downloading model weights or large runtimes.
- Enabling remote APIs or telemetry.
- Changing quality thresholds or benchmark corpora.

### Never

- Rewrite protected literals, code, commands, errors, or approvals.
- Present an unverified conversion as complete.
- Optimize for one aggregate score that hides fidelity failure.
- bundle third-party models, credentials, cookies, or private files in Git.

## MVP acceptance criteria

- The repository and Skill validate successfully.
- Core routing and protected-literal behavior have automated tests.
- `doctor` reports external adapters without installing or invoking heavy jobs.
- A fixed benchmark produces raw case output and separate efficiency/fidelity metrics.
- The benchmark can show pass-through when compression is unsafe or uneconomical.

## Current evidence boundary

The repository benchmark measures estimated text tokens and declared literal-evidence recall. It does not yet measure source-file upload cost, OCR/layout fidelity, image evidence, downstream answer accuracy, or provider-reported prompt usage. Those claims require adapter-specific fixtures and authorized telemetry before publication.
