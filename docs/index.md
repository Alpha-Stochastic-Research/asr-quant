<div class="asr-hero" markdown>

<span class="asr-kicker">Alpha Stochastic Research</span>

# ASRQuant 1.2.0

A Python research platform for moving from **data and hypotheses to models, portfolios, risk diagnostics and reproducible backtests** without hiding chronology, assumptions or implementation choices.

[Get started](getting-started/quickstart.md){ .md-button .md-button--primary }
[API reference](api/index.md){ .md-button }

</div>

## One import. Clear research domains.

```python
import asrquant as asr
```

<div class="asr-grid" markdown>

<div class="asr-card" markdown>
**Research discovery**

Data-driven and literature-derived hypotheses, search, ranking and novelty audit.
</div>

<div class="asr-card" markdown>
**Quantitative analytics**

Alpha, factors, statistics, portfolio risk and market microstructure.
</div>

<div class="asr-card" markdown>
**Pricing & rates**

Options, yield curves, swaps, rate options, stochastic models and calibration.
</div>

<div class="asr-card" markdown>
**Backtesting & reproducibility**

Chronology-aware backtests, costs, audit trails, manifests and guarded execution boundaries.
</div>

</div>

## Canonical 1.2 API

| Domain | Canonical entry point | Purpose |
|---|---|---|
| Data | `asr.data.load`, `asr.data.validate` | Load and validate time-series inputs |
| Hypotheses | `asr.hypotheses.discover` | Generate reviewable research candidates |
| Portfolio | `asr.portfolio.optimize` | Construct portfolios through a common result contract |
| Backtesting | `asr.backtesting.run` | Run auditable portfolio backtests |
| Options | `asr.options.price` | Price supported derivatives through one verb |
| Rates | `asr.rates.analyze`, `asr.rates.calibrate` | Inspect curves and calibrate supported rate models |
| Statistics | `asr.stats.regress` | Fit common regression specifications |
| Machine learning | `asr.ml.fit` | Chronology-safe walk-forward model evaluation |

## Research architecture

```text
Question / Literature
        ↓
Data + provenance
        ↓
Hypothesis candidates
        ↓
Statistical / economic diagnostics
        ↓
Signals + factors
        ↓
Portfolio construction
        ↓
Risk decomposition
        ↓
Backtest + costs + robustness
        ↓
Research decision + reproducible output
```

ASRQuant is research software. Installation does **not** authorize live capital deployment, and successful backtests are not evidence of future profitability.
