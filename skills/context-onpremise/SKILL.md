---
name: context-onpremise
description: Use deployed local conversion, OCR, audio/video, visual, retrieval, reranking, and guarded compression to build high-fidelity bounded Codex context. Use only when the request starts with uppercase ON or explicitly invokes this Skill.
---

# TIKAZ Context On-Premise

Designed, integrated, independently implemented, and continuously maintained by **TIKAZ**.

This is the explicit local route in `上下文-ContextOrchestrator`. Trigger only when the first non-empty control word is uppercase `ON` followed by end-of-input, whitespace, `:`, or `：`, or when the user explicitly invokes `$context-onpremise`. Strip the control prefix before processing. Lowercase `on`, `ONLY`, `ON-board`, and `ON` appearing later in a sentence do not trigger this route.

## Core workflow

1. Fix the task and success metric before optimizing context.
2. Preserve the original source, hash it, and profile type, risk, structure, visuals, and available adapters.
3. Select the lowest-cost adapter that passes the relevant quality gate; do not run every dependency blindly.
4. Produce canonical Markdown plus structured provenance. Keep uncertain pages, visuals, tables, and media timestamps as source evidence.
5. Decompose the task into evidence facets, deduplicate exact or formatting-only repetition, then retrieve, rerank, and diversify task-relevant passages so repeated wording cannot displace another required facet. The dependency-free route uses BM25, bounded semantic bridges, polysemy guards, and facet-aware fusion; expansions remain search hints rather than evidence.
6. Protect numbers, URLs, commands, errors, versions, citations, table cells, approvals, and source anchors exactly.
7. Use learned compression only on eligible natural-language prose and only when its declared benchmark profile passes.
8. Return the context pack, omissions, adapter versions, timings, estimated or measured Token ledger, and verification limits.

## Routing rules

- Use fast extraction for simple born-digital documents and escalate to layout/OCR/VLM adapters only when quality gates fail.
- Prefer platform subtitles, then the configured local faster-whisper environment for speech.
- Keep code, commands, logs, contracts, financial data, tables, and security evidence out of learned prose compression.
- For Python, prefer an exact AST name-dependency slice when it preserves declared facts, decorators, dependencies, syntax, and budget; otherwise return the source. For CSV aggregation, include every parsed row in the reconciliation gate and retain the original table as evidence.
- Use auditable intent expansion and lexical coverage for explicit evidence facets. In Economy mode, retain a conservative Top-5 when only surface-term facets exist and stop earlier only when explicit facets are covered. For OnPremise natural semantic phrasing, fuse BGE-M3 and reranker order; prefer the signal that passes the fixed labeled route. Never report hit rate without independent relevance labels.
- Serialize large GPU stages unless the host has measured headroom.

## Commands

Run the repository engine through `python -m token_forge`. Start with `doctor`. Use `convert --input <path> --output <directory> --config .token-forge.local.toml` to create canonical Markdown. Read `verification_level` in `conversion.json`: `source-literal` permits protected-fact gating; `output-only` means the converter produced non-empty output but an independent source extractor is not configured. Treat a nonzero conversion exit as a source-preservation or adapter-remediation state, never as usable Markdown. Read [dependencies.md](references/dependencies.md) when selecting adapters and [output-contract.md](references/output-contract.md) when producing a pack.

For exit code `4` / `needs-ocr`, keep the original PDF and configure a validated local OCR adapter before retrying. Do not enable remote model downloads automatically. MinerU is eligible only with `adapters.mineru_config` or explicit `runtime.allow_remote=true`.

For dynamic HTTP(S) pages, use the repository `web` command so rendered HTML, a viewport image, and browser metadata remain alongside the Defuddle artifact. For local audio/video, use the `media` command; it preserves timestamped Whisper output and scene/keyframe evidence, suppresses exact duplicate frames, covers distinct scenes before extra samples, and writes a bounded `visual-evidence.json`. A CUDA failure may fall back to CPU int8, but the ledger must retain that runtime fact.

When the task depends on the picture rather than speech alone, read [visual-evidence.md](references/visual-evidence.md). Inspect only selected pending frames, keep observations separate from inference, and rebuild the manifest with hash-anchored annotations. Do not call keyframe extraction visual understanding. If the host cannot inspect images, leave `pending-vision` visible instead of guessing.

For platform URLs, use `platform-media`; it records metadata and optional subtitles without downloading the media. Do not turn this into an implicit media downloader or bypass platform authorization.

For EML, use the native `email-parser` route: preserve selected headers and readable plain/HTML body, list attachment name/type/decoded size, and never fetch remote content. For ZIP, use `bounded-zip`: read safe text members in place without extracting to disk; reject traversal paths, symlinks, encrypted entries, excessive entry counts, sizes, totals, or compression ratios. Never recurse into nested archives.

For bounded text context, use `optimize` only after `doctor.model_gates` reports the required local files as eligible and the repository's offline validation has passed. Read `model-ledger.json`; a `deterministic-fallback` mode is a valid source-preserving result, not proof that BGE or LLMLingua ran. Never override high-risk pass-through or the protected-literal and token-budget rejection gates.

For release evidence, run `benchmark-acceptance` with the versioned manifest. Publish `summary.json`, `metrics.json`, `cases.json`, and `evidence-card.md` together. Keep required-case metrics separate from the full manifest, retain optional failures, and leave provider telemetry, public-platform state, and unscored visual understanding as `Pending`. Visual recall is measurable only from resolved hash-anchored observations against independently declared visual facts.

For retrieval evidence, run `benchmark-retrieval` separately in `economy` and `onpremise` modes against the same versioned labeled manifest. Report Recall@K, Precision@K, MRR, and nDCG@K independently from protected-fact recall and context reduction. Also report dynamic-selection count, selected-evidence recall and precision, facet coverage, and estimated selected-token reduction together; never publish reduction without its corresponding selection recall. If a required retrieval gate fails, the route is not validated even when Token reduction is positive.

Treat OCR metrics as fixture-specific. The repository's clear bilingual scan is a smoke gate, not permission to claim universal CER, accuracy, latency, or token savings. Keep scanned-PDF results at `output-only` unless a separate source-derived verification path exists.

Treat code/table scale metrics as fixture-specific too. Python AST compilation does not prove runtime equivalence, and a reconciled CSV aggregate does not prove that a free-form question was interpreted correctly. Preserve the original source and expose the selected symbols, row count, columns, and reconciliation state in the ledger.

## Completion gate

Do not report a successful optimization unless the result includes separate efficiency and fidelity evidence. Pass through the source when a conversion, retrieval, grounding, or protected-fact check fails.
