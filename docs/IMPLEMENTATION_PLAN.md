# Implementation plan

## Phase 1: verifiable core

- [x] Define source profiles, routes, adapter status, protected literals, and cost ledgers.
- [x] Implement deterministic text packing with pass-through for unsafe inputs.
- [x] Add CLI commands for doctor, profile, convert, pack, and benchmark.

Checkpoint: unit tests pass and no external dependency is required.

## Phase 2: adapters

- [x] Connect the existing faster-whisper environment through configuration.
- [x] Install isolated G-drive environments for MarkItDown, Docling, MinerU, Defuddle, Playwright, PaddleOCR, media utilities, retrieval, and prose compression.
- [x] Add quality-gated Defuddle and MarkItDown subprocess adapters for local HTML.
- [x] Record converter versions, timings, failures, fallback attempts, source hashes, and protected-literal recall.
- [ ] Add subprocess adapters for Docling, MinerU, Playwright, PaddleOCR, yt-dlp, and PySceneDetect.

Checkpoint: each adapter passes one fixed fixture before it is eligible for routing.

## Phase 3: retrieval and learned compression

- [ ] Add lexical and dense indexes with deterministic chunk identifiers.
- [ ] Evaluate BGE-M3 and candidate rerankers on personal fixtures.
- [ ] Add LLMLingua-2 behind an eligibility and quality gate.

Checkpoint: no enabled stage worsens protected-fact or grounding thresholds.

## Phase 4: personal production workflow

- [ ] Add GPU job serialization and recovery manifests.
- [x] Add persistent cache keyed by source hash, adapter, adapter version, and effective configuration.
- [ ] Measure actual provider usage when an authorized telemetry source exists.
- [ ] Package the Skill and publish only evidence-backed claims.

## Phase 5: universal routing

- [ ] Cache source acquisition, canonical conversion, indexes, and final query packs separately.
- [ ] Cover modern and legacy Office, born-digital and scanned PDF, webpages, email, archives, images, subtitles, audio, video, and code repositories.
- [ ] Route encrypted, DRM-protected, corrupted, handwritten, or unsupported sources to an explicit source-preservation state.
- [ ] Measure OCR CER, transcription WER, table-cell recall, retrieval recall, grounding, downstream answer quality, latency, VRAM, and provider telemetry separately.
