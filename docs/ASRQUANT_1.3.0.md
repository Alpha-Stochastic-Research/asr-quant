# ASRQuant 1.3.0 — Research Infrastructure

ASRQuant 1.3.0 extends the 1.2 research API without removing the established 1.x entry points. The release focuses on three concerns: stronger market infrastructure, harder research validation, and more explicit experiment/data lineage.

## 1. Market infrastructure

### Conventions

`asr.rates` now exposes reusable calendars, day-count conventions, business-day adjustment, stubs, frequencies and date schedules.

```python
import asrquant as asr

schedule = asr.rates.Schedule(
    start="2026-09-15",
    end="2031-09-15",
    frequency="6M",
    calendar="TARGET",
    business_day="modified_following",
    fixing_lag=2,
    payment_lag=2,
    day_count="ACT/360",
)
print(schedule.to_frame())
```

Built-in calendars cover common TARGET, US federal, UK bank and weekend-only rules. Custom holidays can be supplied when a desk or venue requires a more specific calendar. The built-ins are not presented as exchange-calendar substitutes.

### Rate instruments

The high-level rate instrument layer provides deposits, FRAs, fixed-rate bonds, swaps and OIS objects with explicit pricing, cash-flow and risk methods.

### CurveBuilder

`CurveBuilder` retains market quotes, explicit repricing errors and a quote-to-zero Jacobian.

```python
builder = asr.rates.CurveBuilder.from_quotes(
    deposits={0.25: 0.0210, 0.50: 0.0220},
    swaps={1.0: 0.0230, 2.0: 0.0240, 5.0: 0.0260},
    valuation_date="2026-09-15",
)
result = builder.build()

print(result.summary)
print(result.repricing_errors)
print(result.jacobian)
```

The high-level builder defaults to an explicit `grid_policy="interpolate"` when sparse swap maturities do not determine every coupon-grid node required by the strict low-level bootstrap. Synthetic coupon-grid nodes are recorded in `result.metadata`. Use `grid_policy="strict"` to require a completely supplied coupon grid.

### Quote-space risk

```python
swap = asr.rates.InterestRateSwap(
    maturity=5.0,
    fixed_rate=0.026,
    notional=10_000_000,
)
risk = asr.rates.curve_risk(swap, result.curve, build_result=result)
```

The result separates node sensitivity, key-rate DV01 and quote-space sensitivity. This prevents a calibration-node bump from being silently interpreted as a market-quote bump.

## 2. Credit foundations

`asr.credit` adds piecewise-constant hazard curves, survival/default probabilities, CDS premium/protection legs, par spreads, CS01-style hazard sensitivity, jump-to-default diagnostics and sequential hazard bootstrapping.

The module is intentionally a credit foundation, not a complete credit/XVA system.

## 3. Research validation

`asr.validation` adds:

- combinatorial purged cross-validation split construction;
- Probability of Backtest Overfitting (PBO);
- moving-block White-style Reality Check;
- studentized SPA-style bootstrap;
- conservative leakage diagnostics;
- multiverse/specification-grid execution.

These diagnostics are not certificates of strategy validity. They expose selection risk, dependence on specifications and observable leakage patterns so that weak research is harder to mistake for robust evidence.

## 4. Research data contracts

### `DataSnapshot`

A snapshot records a deterministic data fingerprint, schema, source, creation time and metadata.

### `DataStore`

A local store adds keyed caching, freshness checks and offline replay of previously cached data.

### `PointInTimeFrame`

Point-in-time data separate:

- observation timestamp;
- availability timestamp;
- revision timestamp.

`as_of()` returns only information that was available by the requested decision time and keeps the latest admissible revision.

## 5. Experiments and reporting

`asr.research.Experiment` records configuration hashes, data hashes, seed, optional code hash, package/Python version and an experiment fingerprint. `ExperimentRegistry` provides an append-only local JSONL registry. `ResearchReport` can combine heterogeneous result objects into HTML, Markdown or JSON. `ResearchGraph` records artifact dependencies and identifies downstream artifacts that become stale when an upstream input changes.

## 6. Cross-domain research utilities

1.3 also adds:

- generic calibration with residual/Jacobian/condition diagnostics;
- generic first-, second- and cross-sensitivity estimation;
- reusable fixed, spread, linear-impact and square-root-impact cost models;
- constrained/cost-aware optimization, robust mean-variance and risk budgeting;
- EVT tail modelling, filtered historical simulation and drawdown-at-risk measures;
- Gaussian and Student-t copula research;
- factor/Brinson attribution;
- volatility and structural-break regime diagnostics;
- model comparison and covariance-estimator holdout comparison;
- Monte Carlo antithetic, Sobol, stratified and control-variate helpers;
- rate P&L explanation;
- capacity diagnostics for signal portfolios;
- adapter protocols and registry for internal data/pricing/risk/execution/cost/optimizer components.

## 7. Stability controls

The repository now ships `PUBLIC_API_v1.3.json` and `scripts/check_public_api.py`. The check fails when a declared stable symbol disappears or its callable signature changes unexpectedly.

The release also removes runtime result-method monkey-patching from the canonical API installer: serialization methods are defined natively on result classes.

## 8. CLI

```bash
asrquant info
asrquant doctor
asrquant validate data.csv --date-column Date
```

`doctor` checks required local dependencies and the execution environment without making a market-data network call.

## Scope boundaries

ASRQuant remains a research toolkit. The new market conventions are transparent common implementations, not a replacement for venue-specific legal documentation or a complete exchange-calendar database. Credit support is intentionally foundational. The leakage detector reports observable risks but cannot prove that a dataset is free from economic or vendor-specific look-ahead bias. Live-broker components remain separately guarded and fail-closed.
