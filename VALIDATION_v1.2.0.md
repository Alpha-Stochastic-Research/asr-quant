# ASRQuant 1.2.0 — Final local validation report

Release date: 2026-08-19  
Software: 1.2.0  
Baseline: complete ASRQuant 1.1.0 source tree, upgraded in place and reorganized for 1.2.0.

## Scope

Version 1.2.0 preserves the stable 1.x API, the paper contract, Research Discovery, Interest Rates and production-readiness controls. It adds the structured public namespace layer, data-driven hypothesis discovery, alpha research, factor analytics, portfolio risk and market microstructure functionality.

## Automated test suite

The complete grouped test inventory contains **273 tests** across 30 test modules. Every group passed independently on the final 1.2.0 source tree:

| Group | Result |
|---|---:|
| core | 27 passed |
| quant | 28 passed |
| surfaces | 15 passed |
| api | 4 passed |
| rates | 36 passed |
| discovery | 7 passed |
| v120 | 76 passed |
| paper | 18 passed |
| production | 62 passed |
| **Total** | **273 passed** |

The grouped runner includes every `tests/test_*.py` module. A single monolithic run was not used as the release claim because the local execution environment imposes a wall-clock limit; the package intentionally supports isolated domain groups and all of them passed.

## End-to-end validation

The following examples executed successfully from source:

- `examples/canonical_api_v120.py`
- `examples/quant_research_v120.py`
- `examples/hypothesis_discovery_v120.py`
- `examples/csv_end_to_end.py`

The E2E test suite additionally covers data → hypothesis discovery → project hand-off, factor analysis, alpha analysis, portfolio risk and the standard API facade.

## Import and syntax checks

- `python -m compileall -q src tests examples scripts` — passed.
- package import sweep — **56 importable modules, 0 failures**.
- `python scripts/check_release.py v1.2.0` — passed.
- `python setup.py check --strict` — passed.

## Distribution validation

Both distribution formats were built and installed independently:

- `asrquant-1.2.0-py3-none-any.whl`
- `asrquant-1.2.0.tar.gz`

Wheel smoke checks:

- `import asrquant as asr` — passed;
- `asr.__version__ == "1.2.0"` — passed;
- canonical namespaces available — passed;
- Black-Scholes smoke price (`S=K=100`, `T=1`, `r=5%`, `sigma=20%`) — `10.45058357`;
- CLI — `ASRQuant 1.2.0`.

Source-distribution smoke checks:

- installation — passed;
- import/version — passed;
- `hypotheses` namespace — available;
- `factors` namespace — available.

A PEP 517 wheel build using `pip wheel --no-deps --no-build-isolation` also completed successfully.

## Data contracts validated

Version 1.2.0 supports a consistent data facade for:

- pandas objects;
- CSV, Parquet, Excel, JSON and Feather files;
- public HTTP(S) table URLs;
- Yahoo Finance through the optional `data` extra;
- ECB Data Portal yield-curve history;
- existing FRED, Binance and Alpha Vantage provider adapters.

Data-source tests use controlled/mocked provider and HTTP responses so the release suite is deterministic and does not depend on external network availability.

## Dependency consistency

`requirements/runtime.txt` is synchronized with the runtime dependencies declared in `pyproject.toml`.

The host-level `pip check` is not used as an ASRQuant release claim because the shared execution image contains an unrelated MoviePy/Pillow version conflict. Distribution installation tests were therefore performed in isolated target locations. Hosted release CI performs the authoritative clean-environment checks.

## Local-tooling limitation

The local execution image did not contain `ruff`, `build` or `twine`, and outbound package installation was unavailable. Therefore the final hosted release gate must still run the repository's existing CI / release workflows, including Ruff, `python -m build`, `twine check --strict`, clean wheel installation, TestPyPI and PyPI Trusted Publishing.

## Release status

**Local scientific, API, compatibility and distribution validation: PASSED.**  
**Hosted GitHub/TestPyPI/PyPI release gate: REQUIRED BEFORE PUBLICATION.**
