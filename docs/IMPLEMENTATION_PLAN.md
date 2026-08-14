# Implementation plan

## Phase 1: verifiable core

- [x] Define source profiles, routes, adapter status, protected literals, and cost ledgers.
- [x] Implement deterministic text packing with pass-through for unsafe inputs.
- [x] Add CLI commands for doctor, profile, pack, and benchmark.

Checkpoint: unit tests pass and no external dependency is required.

## Phase 2: adapters

- [ ] Connect the existing faster-whisper environment through configuration.
- [ ] Add subprocess adapters for MarkItDown, Docling, MinerU, Defuddle, and PaddleOCR.
- [ ] Record commands, versions, timings, failures, and source hashes.

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
