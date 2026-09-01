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
python -m token_forge benchmark-retrieval --manifest benchmarks\retrieval-manifest.json --output benchmark-retrieval-results --mode economy
python -m token_forge benchmark-acceptance --manifest benchmarks\acceptance-manifest.json --output benchmark-acceptance-results --config .token-forge.local.toml
```

## Architecture

1. Preserve the source and compute a content hash.
2. Profile source type, size, risk, layout, visual content, and available adapters.
3. Route to the lowest-cost adapter that meets the quality gate.
4. Produce canonical Markdown plus structured provenance; never flatten uncertain evidence silently.
5. Remove exact or formatting-only text duplication and exact keyframe duplication before semantic methods.
6. Decompose tasks into evidence facets, retrieve with auditable lexical and dense signals, rerank, diversify, measure hit quality, and protect literal evidence.
7. Apply learned compression only to low-risk prose and only when its benchmark profile passes.
8. Emit a context pack, omissions, source anchors, adapter versions, timing, and token ledger.

## Direct adapter families

- Documents: MarkItDown, Docling, MinerU, PaddleOCR; Marker remains an evaluated fallback pending version-specific license review.
- Web: Defuddle, Mozilla Readability, Playwright.
- Media: existing FFmpeg + faster-whisper large-v3 CUDA float16 + PySceneDetect; bounded hash-anchored Codex visual handoff; automatic local VLM remains unconfigured.
- Retrieval: SQLite FTS5/BM25, BGE-M3, a domain-tested reranker, and optional Qdrant.
- Compression: exact/near deduplication first; LLMLingua-2 only for eligible prose.

## Testing strategy

- Unit tests: routing, protected literals, deduplication, budgeting, cost ledger.
- Integration tests: adapter discovery and fixed local fixtures without network access.
- Benchmark: raw, converted, retrieved, and retrieved-plus-compressed paths.
- Quality metrics: protected-fact recall, anchor recall, table-cell recall, citation grounding, Recall@K, Precision@K, MRR, nDCG@K, task-facet coverage, transcript WER, exact frame-routing counts, independently declared visual-fact recall, downstream answer score, input tokens, latency, and peak VRAM.

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

The v1 full-scenario suite runs 20 cases: 18 required local routes, one optional local EPUB route, and one opt-in network probe. On the checked host all 19 local routes and the explicitly authorized public-platform probe passed, with separate profile-weighted context reduction, protected-fact, anchor, table-cell, aggregate reconciliation, Python syntax, OCR CER, transcript-fact, WER, routing, and runtime measures. The fixed video routed six source frames to two selected scene frames and skipped four exact duplicates. The public-platform probe remains opt-in by design; its checked Bilibili metadata run passed without downloading media.

The suite still does not measure provider-reported prompt/image usage, general OCR/layout fidelity, perceptual frame similarity, real-world decorative or informative visual classification, general diagram understanding, multilingual/noisy ASR, authenticated web extraction, or blind downstream answer quality. Retrieval hit quality and visual facts are scored only on their fixed labeled synthetic manifests. Fixture results must not be generalized beyond the committed corpus and declared thresholds.
