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

## Quick start

```powershell
$env:PYTHONPATH='src'
python -m token_forge doctor --config .token-forge.local.toml
python -m token_forge convert `
  --input path\to\source.pdf `
  --output path\to\result `
  --config .token-forge.local.toml
```

`convert` routes local HTML through Defuddle, and documents/PDF through MarkItDown with Docling available as an explicit fallback. A successful run writes `canonical.md` and `conversion.json`. The ledger records the source SHA-256, selected adapter and version, timings, every attempted fallback, verification level, and protected-literal recall. HTML and DOCX/PPTX can be source-literal checked; binary PDF conversion is currently reported as `output-only` unless an independent source extractor is configured. If a source-literal converter drops a protected version, date, URL, number, or command, Token Forge rejects the Markdown instead of silently presenting it as successful.

## Development status

The dependency-free controller MVP is working. It includes source routing, protected-literal checks, deterministic selection, high-risk pass-through, persistent content-addressed caching, adapter diagnostics, and a reproducible four-profile benchmark. The first document adapter slice now performs local HTML and PDF conversion with explicit verification levels and safe fallback. Other installed packages remain ineligible for automatic routing until their own fixed fixtures and quality gates pass. See [installation status](docs/INSTALL_STATUS.md) rather than treating package installation as proof of universal readiness.

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
