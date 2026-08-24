# ASRQuant 1.1.0 — Local validation report

Date: 2026-08-11  
Software: 1.1.0  
Base: ASRQuant 1.0.0 stable tree

## Scope added

- Research Discovery engine and Friday-to-Friday Weekly Research publication pack.
- Interest-rate curve/convention/multi-curve stack.
- FRA/futures/swap/basis, bond/curve risk, caps/floors and swaptions.
- Black/normal rate-option conventions, implied vol and caplet stripping.
- SABR, Vasicek, CIR, Hull-White, Ho-Lee, Black-Karasinski, HJM and LMM research implementations.
- Nelson-Siegel and Svensson curve calibration.
- PCA, level/slope/curvature, no-arbitrage diagnostics, interpolation risk, carry/roll, curve scenarios and key-rate hedge solving.
- RFR/OIS, bond forwards, FX-forward/CIP, zero-coupon cross-currency/inflation and Bermudan LSM building blocks.
- ECB Data Portal provider and yield-curve helper.
- Interest Rate Derivatives Quant curriculum and 42 exercises.

## Automated tests

- Total collected suite: **197 tests**.
- New rates/discovery/ECB subset: **43 tests passed**.
- **197/197 tests passed across isolated groups**: 43 new Discovery/Rates/ECB tests, 18 paper-contract tests, 62 production-readiness tests, 62 core/surface/research tests and 12 Monte Carlo/statistics/visualization tests.
- Python `compileall` for `src/asrquant`: passed.
- Both new executable examples: passed.

The full sequential suite is longer than the execution window of this validation environment, so the 197 tests were executed in deterministic groups rather than represented as one uninterrupted `pytest` process.

## Distribution validation

- wheel built: `asrquant-1.1.0-py3-none-any.whl`.
- source distribution built: `asrquant-1.1.0.tar.gz`.
- wheel metadata version: 1.1.0.
- wheel installed into a clean target directory with dependencies supplied by the host scientific environment.
- isolated-target import: passed.
- discovery API smoke test: passed.
- rates API smoke test: passed.
- ECB provider registry smoke test: passed.
- CLI reports `ASRQuant 1.1.0`.

## Environment notes

- Ruff is not installed in this local execution environment, so a Ruff result is **not** claimed here. Hosted CI should still run the repository's configured Ruff job on the release commit.
- The host environment has `pypdf 5.9.0`, below ASRQuant's declared runtime requirement `pypdf>=6.14.2,<7`. Paper-contract tests still passed locally, but a clean release environment must install the declared dependency set before publication.
- A global `pip check` also reports an unrelated host-environment MoviePy/Pillow conflict; it is not an ASRQuant dependency relationship and therefore is not treated as release evidence.
- The ECB network client is unit-tested with deterministic CSV parsing/provider behavior; live data availability is external and should be covered by an integration job.

## Release gate remaining outside this container

Before PyPI/GitHub publication, run the exact release commit through hosted CI/security checks and perform a clean dependency-resolved installation of both wheel and sdist. No live-capital authorization follows from a software release.
