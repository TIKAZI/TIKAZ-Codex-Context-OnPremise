# TIKAZ Codex Token Forge

Local-first multimodal context compilation for Codex: convert difficult sources, preserve evidence, retrieve only task-relevant material, and optionally compress low-risk prose.

Designed, integrated, independently implemented, and maintained by **TIKAZ**.

Token Forge is the dependency-rich counterpart to the portable Context Economy workflow. It does not promise a fixed reduction percentage. It searches for the best measured quality/cost point for each source and task.

## Pipeline

```text
files / webpages / media / code / conversations
  -> immutable source + content hash
  -> routed converter or transcriber
  -> canonical Markdown + structured evidence
  -> exact/near-duplicate control
  -> BM25 + dense retrieval + reranking
  -> optional LLMLingua-2 for low-risk prose
  -> bounded context pack + omissions + cost ledger
```

## Safety defaults

- Code, commands, errors, versions, URLs, citations, tables, contracts, and financial facts are never rewritten by the compressor.
- Uncertain scans and layouts keep the original source.
- External adapters are explicit and replaceable.
- GPU stages run sequentially on a single 16 GB card unless measured otherwise.
- Estimated token counts are never presented as provider billing telemetry.

## Development status

The dependency-free controller MVP is working. It includes source routing, protected-literal checks, deterministic selection, high-risk pass-through, persistent content-addressed caching, adapter diagnostics, and a reproducible four-profile benchmark. The optional adapter package layer is now installed in isolated G-drive environments; model weights and adapter-specific quality gates remain explicit. See [installation status](docs/INSTALL_STATUS.md) rather than treating package installation as proof of universal readiness.

## Evidence before claims

The fixed seven-case benchmark currently reports:

| Case | Route | Estimated input → final | Estimated reduction | Declared evidence recall |
|---|---|---:|---:|---:|
| Long redundant brief | Retrieved | 509 → 82 | 83.89% | 1.00 |
| Release migration | Retrieved | 106 → 65 | 38.68% | 1.00 |
| Short dense error | Pass-through | 22 → 22 | 0% | 1.00 |
| Budget conflict | Source fallback | 35 → 35 | 0% | 1.00 |
| Code / contract / table | Safety pass-through | unchanged | 0% | 1.00 |

These are deterministic estimates on repository fixtures, not provider billing telemetry, universal accuracy, or a promise of the same saving on other material. Run the benchmark on your own corpus before enabling an adapter.

```powershell
$env:PYTHONPATH='src'
python -m token_forge benchmark --manifest benchmarks\manifest.json --output benchmark-results
```
