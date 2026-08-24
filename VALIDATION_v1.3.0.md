# ASRQuant 1.3.0 Local Validation Record

This file records checks executed on the 1.3.0 development tree before the hosted release gates. It distinguishes local evidence from checks that still require GitHub Actions/TestPyPI on the exact release commit.

## Environment

- Python: 3.13.5
- NumPy: 2.3.5
- pandas: 2.2.3
- SciPy: 1.17.0
- Matplotlib: 3.10.8
- Plotly: 6.5.2
- statsmodels: 0.14.6
- scikit-learn: 1.8.0
- Platform used for local validation: Linux x86_64

## Automated tests

The test suite collects **319 tests across 34 test modules**.

All isolated groups passed when executed separately:

| Group | Passed |
|---|---:|
| core | 27 |
| quant | 28 |
| surfaces | 15 |
| api | 4 |
| rates | 36 |
| discovery | 7 |
| v120 | 76 |
| v130 | 46 |
| paper | 18 |
| production | 62 |
| **Total** | **319** |

The group isolation is intentional because numerical/plotting/solver backends can otherwise share process state.

## 1.3 numerical / research controls covered

The new 1.3 tests cover, among other checks:

- ACT/ACT ISDA and TARGET schedule behaviour;
- sparse and complete-grid curve construction;
- exact repricing of market curve quotes;
- quote-to-zero Jacobian and quote-space curve risk;
- par-swap zero-PV identity and rate P&L reconciliation;
- CDS hazard bootstrap repricing;
- CPCV, PBO, Reality Check, SPA and consolidated strategy validation;
- observable leakage detection and multiverse/specification execution;
- deterministic data snapshots, cache/offline behaviour and point-in-time revisions;
- Black-Scholes put-call parity over randomized parameter sets;
- discount-factor / zero-rate round trips;
- generic calibration recovery and finite-difference sensitivities;
- cost-model positivity, constrained/cost-aware portfolio construction and risk budgeting;
- EVT tail diagnostics, copula simulation, Sobol/control-variate Monte Carlo;
- experiment fingerprints/registry, research reports and research-artifact lineage;
- covariance estimator positive-semidefinite checks and chronological holdout comparison;
- model comparison, factor attribution, regime diagnostics, alpha capacity and centralized random seeds;
- CLI `info` and non-mutating dataset validation.

## Import / bytecode / API checks

- `compileall`: PASS for `src`, `tests`, `examples`, `scripts`.
- Package import sweep: **83 package modules imported, 0 failures** (excluding `asrquant.__main__`, which intentionally executes the CLI).
- Public API compatibility snapshot: **116 declared symbols**, PASS.
- Four deterministic 1.3 examples executed successfully: market infrastructure, validation, data lineage and credit/scenarios.

## Distribution checks

Because the local environment had no network access to install `build`/`twine`, the following local distribution checks were used:

- PEP 517 wheel build through `pip wheel --no-build-isolation`: PASS.
- Source distribution build through the existing setuptools compatibility entry point: PASS.
- Wheel metadata name/version/Python requirement: PASS.
- Wheel installed into an isolated package environment and imported from the installed wheel: PASS.
- CLI `--version`, `info` and `doctor` from the installed wheel: PASS.
- Source distribution installed into a separate isolated package environment and imported: PASS.

The public release workflow still uses `python -m build` and `twine check --strict` in GitHub Actions. Those hosted checks must pass on the exact release commit before PyPI publication.

## Runtime dependency note

The 1.3 development tree lowers the `pypdf` runtime floor from the previous overly restrictive value to `pypdf>=5.9,<7`, matching the PDF-ingestion API exercised by the local environment and tests. All other declared required dependency ranges matched the locally exercised versions.

A global `pip check` on the container reports an unrelated pre-existing `moviepy`/`Pillow` conflict in the host environment; it is not introduced by ASRQuant. The hosted clean-environment package gate remains authoritative for release.

## Checks still required before public PyPI release

- GitHub Actions compatibility matrix on Python 3.10, 3.11, 3.12, 3.13 and 3.14.
- Linux/macOS/Windows hosted compatibility jobs.
- Hosted Ruff, MyPy production-boundary, security, dependency-audit and SBOM jobs.
- `python -m build` and `twine check --strict` on the exact release tree.
- TestPyPI publish/install on the exact release commit.
- Final release tag/version/date reconciliation.

Until those hosted checks pass, this document should be read as a **local validation record**, not as evidence that every supported OS/Python/dependency combination has been certified.
