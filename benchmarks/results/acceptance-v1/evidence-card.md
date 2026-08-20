# Acceptance evidence: tikaz-token-forge-full-scenario-v1

> Token counts are deterministic estimates, not provider telemetry.

- Cases: 17
- Passed: 14
- Failed: 2
- Pending: 1
- Required gate: PASS
- Provider token telemetry: Pending

| Case | Kind | Status | Token reduction | Protected recall | Anchor recall | Runtime |
|---|---|---:|---:|---:|---:|---:|
| text-release-pack | text-pack | passed | 38.7% | 100.0% | 100.0% | 1 ms |
| code-safety-pass-through | text-pack | passed | 0.0% | 100.0% | 100.0% | 0 ms |
| table-safety-pass-through | text-pack | passed | 0.0% | 100.0% | N/A | 0 ms |
| model-retrieval-compression | model-pack | passed | 83.3% | 100.0% | 100.0% | 17650 ms |
| office-docx | conversion | passed | Pending | 100.0% | 100.0% | 2039 ms |
| office-pptx | conversion | passed | Pending | 100.0% | 100.0% | 1908 ms |
| office-xlsx | conversion | passed | Pending | 100.0% | N/A | 1913 ms |
| pdf-born-digital | conversion | passed | Pending | 100.0% | 100.0% | 1902 ms |
| ocr-image | conversion | passed | Pending | 100.0% | N/A | 26776 ms |
| ocr-scanned-pdf | conversion | passed | Pending | 100.0% | N/A | 30608 ms |
| dynamic-web-local | web-local | passed | Pending | 100.0% | 100.0% | 2128 ms |
| audio-transcription | media | passed | Pending | N/A | N/A | 4165 ms |
| video-transcription-scenes | media | passed | Pending | N/A | N/A | 4553 ms |
| ebook-epub | conversion | passed | Pending | 100.0% | N/A | 1995 ms |
| email-eml-capability | conversion | failed | Pending | 0.0% | N/A | 0 ms |
| archive-zip-capability | conversion | failed | Pending | 0.0% | N/A | 0 ms |
| public-platform-metadata | platform-media | pending | Pending | N/A | N/A | 0 ms |

## Failures and pending evidence

- `email-eml-capability`: unavailable
- `archive-zip-capability`: unavailable
- `public-platform-metadata`: network benchmark disabled; run separately with explicit permission
