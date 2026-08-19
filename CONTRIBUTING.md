# Contributing to ASRQuant

ASRQuant uses pull requests, automated tests, and explicit scientific review.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Requirements for a contribution

1. State the quantitative-finance use case and the formula or convention implemented.
2. Document timestamp and execution semantics where relevant.
3. Add deterministic tests, including at least one boundary case.
4. Return pandas objects for calculations and figure objects for plots.
5. Avoid implicit forward filling or silent data coercion.
6. Update the API catalog and changelog.
7. Do not claim profitability from package examples.

## Scientific changes

Changes to metrics, costs, timing, optimization, or statistical tests must include:

- mathematical definition;
- source or derivation;
- units and annualization convention;
- numerical test against a known result;
- limitations and failure modes.
