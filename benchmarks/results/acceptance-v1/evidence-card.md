# Acceptance evidence: tikaz-token-forge-full-scenario-v1

> Token counts are deterministic estimates, not provider telemetry.

- Cases: 20
- Passed: 19
- Failed: 0
- Pending: 1
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

## Cases

| Case | Kind | Status | Token reduction | Protected recall | Anchor recall | Runtime |
|---|---|---:|---:|---:|---:|---:|
| text-release-pack | text-pack | passed | 38.7% | 100.0% | 100.0% | 1 ms |
| code-safety-pass-through | text-pack | passed | 0.0% | 100.0% | 100.0% | 0 ms |
| table-safety-pass-through | text-pack | passed | 0.0% | 100.0% | N/A | 1 ms |
| model-retrieval-compression | model-pack | passed | 83.3% | 100.0% | 100.0% | 21680 ms |
| text-long-deterministic | text-pack | passed | 81.5% | 100.0% | 100.0% | 1 ms |
| code-large-ast-slice | text-pack | passed | 91.0% | 100.0% | 100.0% | 3 ms |
| table-large-reconciled-aggregate | text-pack | passed | 97.1% | 100.0% | N/A | 6 ms |
| office-docx | conversion | passed | Pending | 100.0% | 100.0% | 2074 ms |
| office-pptx | conversion | passed | Pending | 100.0% | 100.0% | 1926 ms |
| office-xlsx | conversion | passed | Pending | 100.0% | N/A | 1903 ms |
| pdf-born-digital | conversion | passed | Pending | 100.0% | 100.0% | 1914 ms |
| ocr-image | conversion | passed | Pending | 100.0% | N/A | 28990 ms |
| ocr-scanned-pdf | conversion | passed | Pending | 100.0% | N/A | 30932 ms |
| dynamic-web-local | web-local | passed | Pending | 100.0% | 100.0% | 6748 ms |
| audio-transcription | media | passed | Pending | N/A | N/A | 4129 ms |
| video-transcription-scenes | media | passed | Pending | N/A | N/A | 4751 ms |
| ebook-epub | conversion | passed | Pending | 100.0% | N/A | 2134 ms |
| email-eml-capability | conversion | passed | Pending | 100.0% | N/A | 1 ms |
| archive-zip-capability | conversion | passed | Pending | 100.0% | N/A | 1 ms |
| public-platform-metadata | platform-media | pending | Pending | N/A | N/A | 0 ms |

## Failures and pending evidence

- `public-platform-metadata`: network benchmark disabled; run separately with explicit permission
