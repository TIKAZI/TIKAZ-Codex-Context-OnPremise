# Retrieval hit quality

Token reduction is useful only when the right evidence survives. Token Forge therefore measures evidence retrieval independently from compression, literal preservation, OCR/VLM facts, and final-answer quality.

## Current validation status

- Context Economy v2 development and frozen challenge results are current and committed below.
- Context On-Premise v1 remains a **historical same-manifest result**. Current v2 fusion reruns on the checked host timed out in both combined-batch and isolated-case attempts on 2026-09-02, so no replacement percentage is claimed.
- Until a clean v2 rerun publishes `summary.json`, `metrics.json`, `cases.json`, and `evidence-card.md` together, On-Premise v2 retrieval quality and runtime are **Pending**. Conversion, OCR/ASR, visual, code, table, and other acceptance evidence remains reported separately.

## Economy v2 result

The committed bilingual manifest contains **14 synthetic cases**, **112 candidate chunks**, and **70 graded relevant chunks**. Ten cases use direct terminology; four use indirect or synonymous task wording. Both routes run the same corpus and labels.

| Economy version | Recall@5 | Precision@5 | MRR | nDCG@5 | Required gates |
|---|---:|---:|---:|---:|---:|
| v1 baseline | 88.57% | 88.57% | 94.64% | 89.45% | Pass |
| **v2** | **100.00%** | **100.00%** | **100.00%** | **100.00%** | Pass |

Economy v2 remains standard-library only. It adds stop-word and plural normalization, BM25 length normalization, bounded semantic bridges, explicit evidence facets, polysemy guards, and facet-aware RRF/MMR selection. Original query wording remains searchable; bridge terms are retrieval hints rather than source facts.

The same 14 cases also exercise conservative dynamic selection. It retained all **70/70** graded relevant chunks with **100% selected-evidence precision**, selecting five chunks per case and reducing candidate-text tokens by an estimated **28.77%**. This reduction compares selected chunk text with all candidate chunk text; it is not Provider billing telemetry or a complete prompt-cost measurement.

The historical OnPremise v1 reference on the same 14 cases was 95.71% Recall@5, 95.71% Precision@5, 100% MRR, and 96.81% nDCG@5. It is not presented as a current v2 comparison until that slower local-model route is rerun against the revised fusion code.

## Adversarial challenge v1

A separate 12-case challenge was created after the original 14-case development set and then run once without tuning against its failures. It is harder than the development set but is **not** an independently authored blind evaluation.

| Measure | Result |
|---|---:|
| Recall@3 | **94.44%** |
| Precision@3 | **94.44%** |
| MRR | **100.00%** |
| nDCG@3 | **96.09%** |
| Dynamic selected-evidence recall | **94.44%** |
| Dynamic selected-evidence precision | **92.50%** |
| Estimated selected-text reduction | **39.01%** |

Both visible misses remain in `cases.json`: the English scanned-document case ranked a print-related distractor over scan detection, and the negative-evidence case did not infer an unstated backup requirement. These are retained limitations, not hidden averages.

Run either route with:

```powershell
python -m token_forge benchmark-retrieval --manifest benchmarks\retrieval-manifest.json --output benchmarks\results\retrieval-economy-v2-dev --mode economy
python -m token_forge benchmark-retrieval --manifest benchmarks\retrieval-challenge-v1.json --output benchmarks\results\retrieval-economy-challenge-v1 --mode economy
python -m token_forge benchmark-retrieval --manifest benchmarks\retrieval-manifest.json --output benchmarks\results\retrieval-onpremise-v1 --mode onpremise --config .token-forge.local.toml
```

Each output includes `summary.json`, `metrics.json`, raw `cases.json`, and `evidence-card.md`. Failed cases remain visible.

## Boundaries

These numbers establish behavior on fixed synthetic manifests only. The 14-case set is a development/regression set, and the 12-case challenge is adversarial but not independently blind. They do not prove universal search accuracy, semantic equivalence, final-answer correctness, or provider Token savings. A downstream independently scored blind-answer suite remains `Pending`. Query coverage is diagnostic rather than an accuracy claim because expanded intent terms may not appear literally in relevant evidence.
