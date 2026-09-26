# ASRQuant 1.2.0 — Release Notes

Release date: 2026-08-19

ASRQuant 1.2.0 is a structural and quantitative-research release. It preserves the 1.0.0 paper contract and 1.1.0 Research Discovery / Interest Rates stack while making the public API more coherent and extending the package with new research domains.

## Public API

Recommended domain namespaces now include:

- `asr.data`
- `asr.hypotheses`
- `asr.alpha`
- `asr.factors`
- `asr.risk`
- `asr.microstructure`
- `asr.backtesting`
- `asr.portfolio`
- `asr.stats`
- `asr.ml`
- `asr.options`
- `asr.rates`

Canonical verbs are `load`, `validate`, `discover`, `run`, `optimize`, `price`, `analyze`, `calibrate`, `regress`, and `fit` where appropriate.

## New: data facade

`asr.data.load(...)` accepts:

- pandas Series/DataFrames;
- CSV, Parquet, Excel, JSON and Feather files;
- public HTTP(S) tables;
- provider-backed market data.

Convenience functions include `asr.data.yahoo(...)` and `asr.data.ecb_yield_curve(...)`. Existing ECB, Yahoo, FRED, Binance and Alpha Vantage provider classes remain available.

## New: hypothesis research

`asr.hypotheses` adds:

- data-driven hypothesis screening;
- literature-derived hypotheses with provenance;
- model-disagreement candidates;
- robustness-instability candidates;
- multi-source discovery;
- hypothesis search;
- conservative novelty audit;
- direct hand-off to `ResearchProject`.

Data support and novelty status are deliberately separated.

## New: alpha research

Cross-sectional winsorization, ranking, z-scores, neutralization, forward returns, Information Coefficient, IC decay, quantile portfolios, long-short spreads, signal weights and turnover diagnostics.

## New: factor research

- PCA factors and reconstruction residuals;
- robust time-series factor exposure estimation;
- rolling beta;
- factor/specific portfolio variance decomposition.

## New: portfolio risk

- historical, Gaussian and Cornish-Fisher VaR;
- Expected Shortfall;
- rolling VaR;
- covariance/Euler risk contributions;
- ES contributions;
- scenario P&L;
- structured portfolio risk report.

## New: market microstructure

- midquote and quoted spread;
- effective / realized spread;
- microprice;
- price impact;
- order-flow imbalance;
- Amihud illiquidity;
- Roll spread;
- Kyle lambda.

## Result and exception contracts

New result objects use consistent `summary`, `to_frame()` and `to_dict()` conventions. Domain-level exceptions live in `asrquant.contracts`.

## Compatibility

The existing 1.x lower-level functions remain available. No intentional deletion of the 1.0.0 paper-contract API or 1.1.0 interest-rate/discovery API is part of this release.

## Security / execution

Live-broker primitives remain fail-closed. Package installation does not authorize capital deployment.
