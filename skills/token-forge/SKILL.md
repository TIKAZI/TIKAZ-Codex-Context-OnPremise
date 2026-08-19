---
name: token-forge
description: Build a local, evidence-preserving, token-efficient Codex context pack from large files, folders, webpages, audio, video, code, logs, or long conversations. Use when external document converters, OCR, GPU transcription, retrieval, reranking, caching, or learned prose compression may reduce model input while facts, citations, source anchors, and accuracy must remain verifiable.
---

# Token Forge

Designed, integrated, independently implemented, and continuously maintained by **TIKAZ**.

## Core workflow

1. Fix the task and success metric before optimizing context.
2. Preserve the original source, hash it, and profile type, risk, structure, visuals, and available adapters.
3. Select the lowest-cost adapter that passes the relevant quality gate; do not run every dependency blindly.
4. Produce canonical Markdown plus structured provenance. Keep uncertain pages, visuals, tables, and media timestamps as source evidence.
5. Deduplicate exact or formatting-only repetition, then retrieve and rerank task-relevant passages.
6. Protect numbers, URLs, commands, errors, versions, citations, table cells, approvals, and source anchors exactly.
7. Use learned compression only on eligible natural-language prose and only when its declared benchmark profile passes.
8. Return the context pack, omissions, adapter versions, timings, estimated or measured Token ledger, and verification limits.

## Routing rules

- Use fast extraction for simple born-digital documents and escalate to layout/OCR/VLM adapters only when quality gates fail.
- Prefer platform subtitles, then the configured local faster-whisper environment for speech.
- Keep code, commands, logs, contracts, financial data, tables, and security evidence out of learned prose compression.
- Use lexical plus semantic retrieval; enable a reranker only after it passes a domain-specific fixture.
- Serialize large GPU stages unless the host has measured headroom.

## Commands

Run the repository CLI through `python -m token_forge`. Start with `doctor`. Use `convert --input <path> --output <directory> --config .token-forge.local.toml` to create canonical Markdown. Read `verification_level` in `conversion.json`: `source-literal` permits protected-fact gating; `output-only` means the converter produced non-empty output but an independent source extractor is not configured. Treat a nonzero conversion exit as a source-preservation or adapter-remediation state, never as usable Markdown. Read [dependencies.md](references/dependencies.md) when selecting adapters and [output-contract.md](references/output-contract.md) when producing a pack.

For exit code `4` / `needs-ocr`, keep the original PDF and configure a validated local OCR adapter before retrying. Do not enable remote model downloads automatically. MinerU is eligible only with `adapters.mineru_config` or explicit `runtime.allow_remote=true`.

For dynamic HTTP(S) pages, use the repository `web` command so rendered HTML, a viewport image, and browser metadata remain alongside the Defuddle artifact. For local audio/video, use the `media` command; it preserves timestamped Whisper output and scene/keyframe evidence. A CUDA failure may fall back to CPU int8, but the ledger must retain that runtime fact.

For platform URLs, use `platform-media`; it records metadata and optional subtitles without downloading the media. Do not turn this into an implicit media downloader or bypass platform authorization.

Treat OCR metrics as fixture-specific. The repository's clear bilingual scan is a smoke gate, not permission to claim universal CER, accuracy, latency, or token savings. Keep scanned-PDF results at `output-only` unless a separate source-derived verification path exists.

## Completion gate

Do not report a successful optimization unless the result includes separate efficiency and fidelity evidence. Pass through the source when a conversion, retrieval, grounding, or protected-fact check fails.
