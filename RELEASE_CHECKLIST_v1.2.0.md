# ASRQuant 1.2.0 release checklist

## Version and metadata

- [x] `pyproject.toml` version is 1.2.0
- [x] `asrquant.__version__` is 1.2.0
- [x] `CITATION.cff` is 1.2.0
- [x] repository URLs point to `Alpha-Stochastic-Research/asr-quant`
- [x] README documents the 1.2 API

## Compatibility

- [x] all historical test groups pass on the final source tree
- [x] paper-contract tests pass — 18/18
- [x] production-readiness tests pass — 62/62
- [x] interest-rate / discovery 1.1 regression tests pass — 43/43

## 1.2 functionality

- [x] data sources tests pass
- [x] hypothesis discovery tests pass
- [x] alpha tests pass
- [x] factor tests pass
- [x] risk tests pass
- [x] microstructure tests pass
- [x] canonical API tests pass
- [x] end-to-end research tests pass
- [x] complete grouped suite passes independently — 273/273
- [x] 56-module import sweep passes
- [x] four end-to-end examples execute successfully

## Distribution

- [x] setuptools wheel and source distribution build successfully
- [x] PEP 517 wheel build succeeds with `pip wheel`
- [x] wheel installs in an isolated target environment
- [x] `import asrquant as asr; print(asr.__version__)` returns 1.2.0
- [x] CLI returns 1.2.0
- [x] source distribution installs in an isolated target environment
- [ ] `python -m build` on hosted release runner
- [ ] `python -m twine check --strict dist/*` on hosted release runner
- [ ] Ruff / hosted quality jobs green

## Hosted release gate

- [ ] GitHub CI green on the exact release commit
- [ ] TestPyPI install succeeds
- [ ] create GitHub release tag `v1.2.0`
- [ ] PyPI Trusted Publisher workflow succeeds
