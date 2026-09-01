# Contributing

Thanks for improving TIKAZ Context On-Premise. Contributions should improve measurable behavior, portability, evidence quality, safety, or documentation.

## Development

```powershell
python -m pip install -e .
$env:PYTHONPATH='src'
python -m unittest discover -s tests -v
python -m token_forge benchmark --manifest benchmarks\manifest.json --output benchmark-results
```

Optional model, OCR, browser, and media tests require explicit local paths in `.token-forge.local.toml`. Test runs must not download models or send private material to remote services.

## Pull requests

1. Keep each change focused and explain its evidence boundary.
2. Add or update tests for behavior changes.
3. Preserve failures and Pending results in benchmark output.
4. Do not commit model weights, local configuration, credentials, caches, logs, personal media, or machine-specific absolute paths.
5. Retain third-party notices and upstream licenses when a dependency or adapted work requires them.

Performance claims are accepted only with a versioned manifest, raw per-case results, declared denominators, and separate quality/cost metrics.
