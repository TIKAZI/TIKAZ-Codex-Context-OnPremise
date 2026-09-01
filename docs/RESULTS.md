# Complete measured results

This page is the human-readable index of every checked scenario in Token Forge's current public result set. It is intentionally complete: successful, safety pass-through, and pending cases are all shown. The machine-readable source of truth remains the linked JSON artifacts.

**Scope.** Results use fixed, redistribution-safe fixtures on the checked Windows host. Token counts are deterministic estimates, not Codex or provider billing telemetry. A `Pending` row is not a failure and is never included in a passing denominator.

## At a glance

| Suite | Checked scenarios | Result | Main evidence |
|---|---:|---|---|
| Full-scenario acceptance v1 | 20 | **20 passed · 0 failed · 0 pending** | 53/53 protected facts; 11/11 anchors; 9/9 table cells |
| Local model routes | 4 | 4 protected-fact gates passed | 3 learned-compression routes; 1 safety pass-through |
| Retrieval hit quality | 14-case Economy v2 + 12-case challenge | both gates passed | v2 100% Recall@5; challenge 94.44% Recall@3 |
| Local visual v1 | 12 images | all required gates passed | 37/37 OCR, 37/37 VLM, 37/37 combined facts; 10/12 types |

## 1. Context preparation and safe compression

All seven rows below are part of the acceptance suite. `Safety pass-through` is intentional: high-risk code and tables are retained unchanged rather than compressed past their safety boundary.

| Scenario | Route | Input → output estimate | Reduction | Facts | Anchors | Budget / note | Runtime |
|---|---|---:|---:|---:|---:|---|---:|
| Release text pack (`text-release-pack`) | Selected evidence | 106 → 65 | 38.68% | 3/3 | 2/2 | 70-token budget passed | 1 ms |
| Code safety pass-through (`code-safety-pass-through`) | Safety pass-through | 91 → 91 | 0% | 3/3 | 1/1 | declared 20-token conflict; source retained | <1 ms |
| Table safety pass-through (`table-safety-pass-through`) | Safety pass-through | 35 → 35 | 0% | 3/3 | — | declared 20-token conflict; source retained | 1 ms |
| Retrieval + learned compression (`model-retrieval-compression`) | Learned-compressed | 509 → 85 | 83.30% | 4/4 | 1/1 | 85-token budget passed | 120.866 s |
| Deterministic long-text selection (`text-long-deterministic`) | Selected evidence | 509 → 94 | 81.53% | 4/4 | 1/1 | 100-token budget passed | <1 ms |
| Python AST dependency slice (`code-large-ast-slice`) | Code-sliced | 1,117 → 100 | 91.05% | 3/3 | 1/1 | syntax valid; 81 source symbols → 1 selected closure | 2 ms |
| Reconciled CSV aggregate (`table-large-reconciled-aggregate`) | Table-aggregated | 2,943 → 84 | 97.15% | 3/3 | — | all 500 rows reconciled | 3 ms |

| Aggregation (same seven cases) | Value |
|---|---:|
| Token-weighted reduction | **89.57%** |
| Macro-average reduction | **55.96%** |
| Text-context weighted reduction | 74.15% |
| Code-context weighted reduction | 84.19% |
| Table-context weighted reduction | 96.00% |
| Model-text-context weighted reduction | 83.30% |

## 2. File conversion, OCR, web, email, and archive routes

`Source-literal` means protected literals were checked against a source-level representation. `Output-only` means the converter output passed the declared fixture checks but no independent source extractor was available for that binary format.

| Scenario | Input | Route | Result | Facts | Anchors / cells | Verification | Runtime |
|---|---|---|---|---:|---:|---|---:|
| Office document (`office-docx`) | DOCX | MarkItDown | Passed | 4/4 | 1/1 anchors · 3/3 cells | Source-literal | 5.984 s |
| Presentation (`office-pptx`) | PPTX | MarkItDown | Passed | 3/3 | 2/2 anchors | Source-literal | 1.846 s |
| Spreadsheet (`office-xlsx`) | XLSX | MarkItDown | Passed | 3/3 | 6/6 cells | Output-only | 1.891 s |
| Born-digital PDF (`pdf-born-digital`) | PDF | MarkItDown | Passed | 3/3 | 1/1 anchors | Output-only | 1.834 s |
| Raster image OCR (`ocr-image`) | Image | MinerU | Passed | 4/4 | CER 0.00% | Output-only | 61.104 s |
| Scanned PDF OCR (`ocr-scanned-pdf`) | Image-only PDF | MinerU | Passed | 4/4 | CER 0.00% | Output-only | 27.946 s |
| E-book (`ebook-epub`) | EPUB | MarkItDown | Passed (optional) | 2/2 | — | Output-only | 1.876 s |
| Email inventory (`email-eml-capability`) | EML | Standard-library parser | Passed | 2/2 | — | Source-literal | 1 ms |
| Safe archive inventory (`archive-zip-capability`) | ZIP | Bounded ZIP reader | Passed | 2/2 | — | Source-literal | 1 ms |
| Dynamic local webpage (`dynamic-web-local`) | Rendered HTML | Playwright → Defuddle | Passed | 3/3 | 1/1 anchors | Rendered local fixture | 9.406 s |

### Focused bilingual scanned-PDF smoke

| Measure | Result |
|---|---:|
| Page / text layer | 1 page / none |
| Route | MarkItDown empty-output → MinerU pipeline OCR |
| Total CLI time | 33.693 s |
| MinerU time | 27.877 s |
| Character error rate | **0.00%** (0 edits / 100 reference characters) |
| Exact protected facts | **5/5** |
| Surviving adapter processes | 0 |

This is a clear, synthetic bilingual raster scan; it does not generalize to handwriting, degraded pages, complex tables, or diagrams.

## 3. Audio, video, and public-platform boundary

| Scenario | Route | Result | Transcript evidence | Visual evidence | Runtime |
|---|---|---|---|---|---:|
| Audio transcription (`audio-transcription`) | FFmpeg + faster-whisper + scene detection | Passed | 3/3 facts; WER 5.88% | no keyframes expected | 29.532 s |
| Video transcription + scenes (`video-transcription-scenes`) | FFmpeg + faster-whisper + scene detection | Passed | 3/3 facts; WER 5.88% | 6 source → 2 selected; 4 exact duplicates skipped | 4.712 s |
| Public platform metadata (`public-platform-metadata`) | Explicit opt-in platform route | Passed | Metadata retrieved; no subtitles available; no media downloaded | Not applicable | 2.650 s |

The video's 66.67% reduction measures only avoided processing of byte-identical keyframes. It is not visual semantic accuracy, perceptual deduplication, or image-token savings.

## 4. Local retrieval and learned-compression model benchmark

This separate benchmark isolates the local BGE retrieval/reranking and LLMLingua-2 compression route. All protected-fact gates passed.

| Scenario | Mode | Input → final estimate | Reduction | Protected facts | Fallback reason |
|---|---|---:|---:|---:|---|
| Release migration (`model-release-migration`) | Learned-compressed | 106 → 68 | 35.85% | 1.00 | — |
| Long retrieval (`model-long-retrieval`) | Learned-compressed | 509 → 85 | 83.30% | 1.00 | — |
| Code (`model-code-pass-through`) | Safety pass-through | 91 → 91 | 0% | 1.00 | Learned models excluded for high-risk material |
| Low-risk prose (`model-low-risk-compression`) | Learned-compressed | 147 → 55 | 62.59% | 1.00 | — |

## 5. Retrieval hit quality

The same fixed manifest contains 14 synthetic bilingual cases, 112 candidate chunks, and 70 graded relevant chunks. The four indirect-language cases expose the difference between literal overlap and semantic evidence retrieval.

| Route / version | Recall@5 | Precision@5 | MRR | nDCG@5 | Runtime | Gates |
|---|---:|---:|---:|---:|---:|---:|
| ContextEconomy v1 baseline | 88.57% | 88.57% | 94.64% | 89.45% | 0.391 s | Passed |
| **ContextEconomy v2** | **100.00%** | **100.00%** | **100.00%** | **100.00%** | 0.012 s | Passed |
| ContextOnPremise v1 historical | 95.71% | 95.71% | 100.00% | 96.81% | 344.720 s cold run | Historical; passed |
| ContextOnPremise v2 fusion | Pending | Pending | Pending | Pending | 2026-09-02 reruns timed out | Pending; no new claim |

Economy v2's conservative dynamic selection retained all 70/70 relevant chunks at 100% precision and reduced candidate-text tokens by an estimated 28.77%. The separately frozen 12-case adversarial challenge reached 94.44% Recall@3, 94.44% Precision@3, 100% MRR, and 96.09% nDCG@3; its dynamic selection paired 94.44% recall with 39.01% estimated selected-text reduction. Both challenge misses remain public.

Runtime values are checked runs on this host and are not universal latency claims. The v1 OnPremise row is historical; current v2 attempts exceeded their declared timeout, so the repository keeps the failure visible instead of reusing v1 as a v2 claim. These are labeled-fixture retrieval measurements, not final-answer accuracy or Provider Token telemetry.

## 6. Local visual benchmark — every image

The visual suite uses 12 deterministic 1280×720 images. OCR and VLM fact recall are scored independently against 37 declared literal facts; type classification is a separate route-quality measure.

| # | Scene | Expected → actual type | Type | OCR facts | VLM facts | Combined | Local status | VLM time |
|---:|---|---|---|---:|---:|---:|---|---:|
| 01 | Release verification document (`document-release`) | document → document | ✓ | 3/3 | 3/3 | 3/3 | Resolved locally | 2.545 s |
| 02 | Chinese release record (`document-zh`) | document → document | ✓ | 3/3 | 3/3 | 3/3 | Resolved locally | 2.413 s |
| 03 | Token Forge settings UI (`ui-settings`) | ui → document | × | 3/3 | 3/3 | 3/3 | Resolved locally | 3.117 s |
| 04 | Acceptance dashboard UI (`ui-dashboard`) | ui → document | × | 3/3 | 3/3 | 3/3 | Resolved locally | 3.571 s |
| 05 | Pricing table (`table-pricing`) | table → table | ✓ | 3/3 | 3/3 | 3/3 | Resolved locally | 4.626 s |
| 06 | Bar chart (`chart-bars`) | chart → chart | ✓ | 3/3 | 3/3 | 3/3 | Resolved locally | 7.464 s |
| 07 | Evidence-routing flow (`diagram-flow`) | diagram → diagram | ✓ | 4/4 | 4/4 | 4/4 | Resolved locally | 3.757 s |
| 08 | Spatial relation shapes (`spatial-shapes`) | diagram → diagram | ✓ | 3/3 | 3/3 | 3/3 | Resolved locally | 2.597 s |
| 09 | Warning dialog (`warning-dialog`) | ui → ui | ✓ | 3/3 | 3/3 | 3/3 | Resolved locally | 3.762 s |
| 10 | Invoice (`invoice`) | document → document | ✓ | 3/3 | 3/3 | 3/3 | Resolved locally | 3.400 s |
| 11 | Pipeline timeline (`timeline`) | diagram → diagram | ✓ | 3/3 | 3/3 | 3/3 | Resolved locally | 8.066 s |
| 12 | Warehouse schematic (`warehouse-scene`) | diagram → diagram | ✓ | 3/3 | 3/3 | 3/3 | Resolved locally | 3.459 s |

| Visual aggregate | Result |
|---|---:|
| OCR protected-fact recall | **37/37 (100%)** |
| VLM protected-fact recall | **37/37 (100%)** |
| Combined protected-fact recall | **37/37 (100%)** |
| Locally resolved images | **12/12 (100%)** |
| Dominant frame-type accuracy | **10/12 (83.33%)** |
| Declared quality gates | facts ≥95%; types ≥80%; **passed** |
| Local VLM prompt-evaluation count | 16,236 |
| Aggregate local VLM duration | 48.778 s |
| Codex image-token savings | Pending provider telemetry |

The two type errors are retained above: flat settings and dashboard mockups were classified as `document`. This did not reduce literal-fact recall. The suite does not measure natural photographs, low-quality video, handwritten text, degraded scans, arbitrary charts, provider billing, or downstream-answer correctness.

## Source artifacts and reproducibility

- [Acceptance summary](../benchmarks/results/acceptance-v1/summary.json), [metrics](../benchmarks/results/acceptance-v1/metrics.json), and [all acceptance cases](../benchmarks/results/acceptance-v1/cases.json)
- [Model benchmark results](../benchmarks/results/model-results.json)
- [Bilingual OCR smoke](../benchmarks/results/mineru-bilingual-scan.json)
- [Visual summary](../benchmarks/results/visual-v1/summary.json), [metrics](../benchmarks/results/visual-v1/metrics.json), and [all visual cases](../benchmarks/results/visual-v1/cases.json)
- [Economy v2 retrieval summary](../benchmarks/results/retrieval-economy-v2-dev/summary.json), [challenge summary](../benchmarks/results/retrieval-economy-challenge-v1/summary.json), [historical OnPremise summary](../benchmarks/results/retrieval-onpremise-v1/summary.json), and [retrieval method](RETRIEVAL_QUALITY.md)
- [Benchmark method and claim boundaries](BENCHMARK.md) · [中文说明](BENCHMARK.zh-CN.md)

Do not compare these reduction percentages to another project unless the corpus, task, tokenizer, budget, model settings, and downstream evaluation rubric are the same.
