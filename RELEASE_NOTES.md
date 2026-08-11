# ASRQuant 1.1.0

See `RELEASE_NOTES_v1.1.0.md` for the current release. The historical ASRQuant 1.0.0 notes follow below.

---

# ASRQuant 1.0.0

ASRQuant 1.0.0 is the first stable public-API release of the ASRQuant research laboratory and the software artifact corresponding to **manuscript v0.1.0**.

## Paper ↔ package contract

The stable release treats the paper as an executable software contract rather than descriptive documentation. A dedicated 18-test paper-contract suite exercises the public workflows and capability claims used in the manuscript, including:

- one-import formula → polynomial modelling → visualization;
- CSV and in-memory backtesting;
- provider normalization without network dependence in CI;
- PDF literature ingestion and source-linked hypothesis discovery;
- all seven core stochastic-process families;
- Monte Carlo and martingale diagnostics;
- Black–Scholes–Merton, Bachelier, Black–76, CRR, implied volatility and Monte Carlo derivatives;
- fixed-income pricing, yield, duration, convexity and zero-curve bootstrapping;
- implementation audits and regression diagnostics;
- multidimensional surface HTML/GIF export;
- market/limit/stop/stop-limit paper-broker states, partial fills and cancellation;
- research-project governance through paper trading.

## Validation

The release contains **154 automated tests** in total. The major isolated groups pass as follows:

- core: 27;
- quant: 28;
- surfaces: 15;
- one-import API: 4;
- paper contract: 18;
- production boundary: 62.

The stable fixed-income bootstrap now validates coupon frequency and rejects incomplete coupon grids instead of silently constructing an inconsistent curve.

## Release engineering

- Stable package version: `1.0.0`.
- Supported Python versions in CI: 3.10–3.13.
- Direct Coverage.py gate avoids pytest plugin double-loading.
- Runtime dependency audit is isolated from development-tool dependencies.
- SBOM/security evidence is kept outside the PyPI distribution directory.
- GitHub release asset upload targets the repository explicitly.
- CodeQL is an opt-in repository security workflow and is not used to disguise missing repository-level Code Security permissions as a source-code failure.

## Safety boundary

Stable API status does not mean automatic authorization for live capital. Backtests, simulations and paper trading remain research evidence. Guarded live execution is fail-closed and requires deployment-specific authorization, risk limits, reconciliation and operational controls.
