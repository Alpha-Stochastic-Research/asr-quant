# ASRQuant 1.3.0 — Final Release Report

Release: **1.3.0**  
Release date: **2026-09-16**  
Artifact status: **final stable release package** (not an RC)

## Result

The final ASRQuant 1.3.0 source tree, wheel and source distribution are internally consistent in the executed Linux / Python 3.13 validation environment.

## Contributor and citation reconciliation

The software release metadata now recognizes:

- **Alpha Kabinet TOURE** — creator / lead developer / release integration;
- **Srijan Mishra** — software validation and reproducibility contributor for v1.3.0;
- **Alpha Stochastic Research** — institutional maintainer.

The contributor update is reflected in `pyproject.toml`, `CITATION.cff`, `CONTRIBUTORS.md`, the README and release notes. Manuscript authorship remains tracked separately from software contribution.

## SW-001 corrections incorporated

The final validation workflow incorporates the actionable package/release findings from SW-001:

1. exact installed distribution metadata is required for version verification;
2. `asrquant.__version__` must equal distribution metadata exactly;
3. a missing required NumPy dependency cannot be reported as PASS;
4. normal-sampling tolerances are sample-size-derived (5σ mean, 7σ standard deviation) rather than unexplained constants;
5. project-specific coverage cannot be represented by a placeholder PASS;
6. `closed_form_comparisons` is implemented using an independent Black–Scholes formula plus CRR convergence checks;
7. the full validation report is echoed to stdout as well as written to `PACKAGE_TEST_REPORT.md`;
8. all 258 top-level public callable signatures are recorded in `PUBLIC_API_SIGNATURES_v1.3.0.json`.

## Automated test evidence

The final repository collects **336 tests across 36 test modules**.

All governed domain groups passed:

| Group | Passed | Result |
|---|---:|---|
| core | 27 | PASS |
| quant | 28 | PASS |
| surfaces | 15 | PASS |
| api | 4 | PASS |
| rates | 36 | PASS |
| discovery | 7 | PASS |
| v120 | 76 | PASS |
| v130 | 63 | PASS |
| paper | 18 | PASS |
| production | 62 | PASS |
| **Total** | **336** | **PASS** |

The v1.3.0 group includes five final release-integrity tests covering contributor/citation metadata, the 258-callable signature manifest, strict distribution-version verification, required-NumPy failure semantics, and explicit coverage-gap semantics.

## Installed wheel validation

The rebuilt `asrquant-1.3.0-py3-none-any.whl` was installed into a separate target directory and imported from that installed location rather than from the repository source tree.

Verified:

- distribution metadata version: `1.3.0`;
- `asrquant.__version__`: `1.3.0`;
- version drift: none;
- wheel metadata Author: `Alpha Kabinet TOURE, Srijan Mishra`;
- institutional Author-email: `Alpha Stochastic Research <research@asr-lab.online>`;
- documentation URL: `https://docs.asr-lab.online/asrquant/`;
- CLI `--version`: PASS;
- CLI `info`: PASS;
- CLI `doctor`: PASS.

The hardened installed-package validator returned:

- 6 PASS;
- 0 SKIP / coverage gaps;
- 0 FAIL;
- overall: **PASS**.

The closed-form control executed three independent Black–Scholes comparisons with maximum absolute error `1.421e-14`, and CRR(1000-step) convergence with maximum absolute error about `0.00199947`, below the stated `0.01` tolerance.

## Source-distribution validation

The final `asrquant-1.3.0.tar.gz` was installed independently with build isolation disabled in the local environment and verified to report/import `1.3.0`.

The sdist includes the release provenance files required for review, including:

- `CITATION.cff`;
- `CONTRIBUTORS.md`;
- `PUBLIC_API_SIGNATURES_v1.3.0.json`;
- `VALIDATION_v1.3.0_FINAL.md`;
- `FINAL_RELEASE_REPORT.md`;
- `scripts/asr_software_validation_template.py`.

## Metadata / compatibility validation

- `pyproject.toml`: parsed successfully;
- `CITATION.cff`: parsed successfully as YAML;
- public signature manifest: valid JSON, 258 top-level callables;
- existing canonical public-API compatibility gate: PASS;
- `scripts/check_release.py v1.3.0`: PASS;
- `compileall` for source/tests/examples/scripts: PASS.

## Build note

The current execution environment does not have the `build` or `twine` modules installed and has no external package-install network path. The final distributions were therefore rebuilt locally using the repository-compatible offline path:

- PEP 517 wheel: `python -m pip wheel . --no-deps --no-build-isolation`;
- sdist: `python setup.py sdist`.

The repository's hosted publication workflow should still run `python -m build` and `twine check --strict` on the exact release commit/tag before public PyPI publication.

## Platform findings

SW-001 P-01 (runner UID/workspace ownership inconsistency) and P-02 (generated-file persistence between runtime commands) are platform findings, not ASRQuant Python-package defects. This release does not claim to repair the runner platform. P-02 is mitigated for package-validation evidence by echoing the complete report to stdout.

## Independent RC audit closure

The final artifact includes direct regression coverage for FIND-003, FIND-006, FIND-011, FIND-012, FIND-013, FIND-014 and FIND-015, plus non-breaking improvements for the Vasicek uncertainty and Omega-threshold observations. Heavy optional dependency stacks are separated from the scientific core. Financial pricing, curve, rate-risk and calibration logic remains implemented within ASRQuant and is validated through analytical identities, round-trip checks, invariants and regression tests.

The final import sweep covers **84 package modules with zero failures** in the executed environment.

## Release decision

**ASRQuant 1.3.0 final package: PASS for the locally executed release checks.**

The artifacts in `dist/` are final-version artifacts (`1.3.0`, not `1.3.0rc1`). Public registry publication remains a separate hosted release action.
