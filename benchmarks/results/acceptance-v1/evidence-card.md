# Acceptance evidence: tikaz-token-forge-full-scenario-v1

> Token counts are deterministic estimates, not provider telemetry.

- Cases: 20
- Passed: 20
- Failed: 0
- Pending: 0
- Required gate: PASS
- Weighted context reduction: 89.57%
- Provider token telemetry: Pending

## Efficiency profiles

| Profile | Cases | Macro mean | Token-weighted reduction |
|---|---:|---:|---:|
| code-context | 2 | 45.52% | 84.19% |
| model-text-context | 1 | 83.30% | 83.30% |
| table-context | 2 | 48.57% | 96.00% |
| text-context | 2 | 60.11% | 74.15% |

## Multimodal evidence

- Transcript fact recall: 100.00%
- Mean transcription WER: 5.88%
- Visual frames: 6 source / 2 selected
- Exact duplicate frames skipped: 4 (66.67% of source frames)
- Deferred visual frames: 0
- Resolved visual frames: 1
- Visual understanding: Pending
- Visual fact recall: Pending

> Frame reduction is routing evidence, not provider image-token telemetry.

## Cases

| Case | Kind | Status | Token reduction | Protected recall | Anchor recall | Runtime |
|---|---|---:|---:|---:|---:|---:|
| text-release-pack | text-pack | passed | 38.7% | 100.0% | 100.0% | 1 ms |
| code-safety-pass-through | text-pack | passed | 0.0% | 100.0% | 100.0% | 1 ms |
| table-safety-pass-through | text-pack | passed | 0.0% | 100.0% | N/A | 2 ms |
| model-retrieval-compression | model-pack | passed | 83.3% | 100.0% | 100.0% | 142529 ms |
| text-long-deterministic | text-pack | passed | 81.5% | 100.0% | 100.0% | 0 ms |
| code-large-ast-slice | text-pack | passed | 91.0% | 100.0% | 100.0% | 2 ms |
| table-large-reconciled-aggregate | text-pack | passed | 97.1% | 100.0% | N/A | 3 ms |
| office-docx | conversion | passed | Pending | 100.0% | 100.0% | 8026 ms |
| office-pptx | conversion | passed | Pending | 100.0% | 100.0% | 2199 ms |
| office-xlsx | conversion | passed | Pending | 100.0% | N/A | 2383 ms |
| pdf-born-digital | conversion | passed | Pending | 100.0% | 100.0% | 2148 ms |
| ocr-image | conversion | passed | Pending | 100.0% | N/A | 68755 ms |
| ocr-scanned-pdf | conversion | passed | Pending | 100.0% | N/A | 28646 ms |
| dynamic-web-local | web-local | passed | Pending | 100.0% | 100.0% | 11178 ms |
| audio-transcription | media | passed | Pending | N/A | N/A | 30231 ms |
| video-transcription-scenes | media | passed | Pending | N/A | N/A | 73462 ms |
| ebook-epub | conversion | passed | Pending | 100.0% | N/A | 2084 ms |
| email-eml-capability | conversion | passed | Pending | 100.0% | N/A | 5 ms |
| archive-zip-capability | conversion | passed | Pending | 100.0% | N/A | 5 ms |
| public-platform-metadata | platform-media | passed | Pending | N/A | N/A | 2650 ms |
