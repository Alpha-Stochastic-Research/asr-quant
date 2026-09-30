# ASRQuant Launch Posts

Use these as technical launch templates. Keep the tone research-first and avoid engagement bait.

## Post 1 — Real-world rates workflow

**ASRQuant 1.3: from a public EUR curve to reviewable rates risk in one notebook.**

We built a public practical case around a simple question: if the EUR curve moves, what does that mean for a 5Y payer IRS — and how do we preserve the evidence behind the answer?

The notebook goes through:

- ECB EUR yield-curve data;
- data QA + immutable snapshot;
- PCA of curve changes;
- 5Y IRS construction;
- DV01 / key-rate DV01 / quote PV01;
- P&L explanation;
- parallel / steepener / flattener stress;
- CPCV, PBO, Reality Check and SPA;
- experiment lineage + exported research report.

```bash
pip install --upgrade asrquant
```

GitHub: https://github.com/Alpha-Stochastic-Research/asr-quant

Docs: https://docs.asr-lab.online/

The goal is not to hide assumptions behind a compact API. The goal is to make the quantitative path easier to inspect, reproduce and challenge.

---

## Post 2 — Quote-space risk

**A curve-node bump is not necessarily a market-quote bump.**

In fixed-income research, a sensitivity can look precise while still being expressed in the wrong space.

ASRQuant 1.3 exposes both internal curve risk and quote-space risk so a researcher can trace a 5Y IRS from:

**market quotes → calibrated curve → instrument → DV01 / key-rate DV01 / quote PV01 → P&L explanation**

```python
risk = asr.rates.curve_risk(
    swap,
    build.curve,
    build_result=build,
)

print(risk.dv01)
print(risk.key_rate_dv01)
print(risk.quote_pv01)
```

Install:

```bash
pip install --upgrade asrquant
```

Documentation: https://docs.asr-lab.online/

---

## Post 3 — Validation

**A strong backtest is not the same thing as strong evidence.**

If a strategy is selected after trying many variants, its evidential status is different from a strategy specified before looking at the data.

ASRQuant includes research-validation tools such as:

- Combinatorial Purged Cross-Validation;
- Probability of Backtest Overfitting;
- Reality Check;
- SPA;
- leakage diagnostics;
- multiverse analysis.

These are not certificates that a strategy is economically valid. They are evidence filters designed to make selection risk and fragile specifications harder to ignore.

```bash
pip install --upgrade asrquant
```

GitHub: https://github.com/Alpha-Stochastic-Research/asr-quant

---

## Post 4 — Reproducible research

**Can you reproduce a result after the underlying dataset changes?**

ASRQuant treats lineage as part of the research object.

A workflow can preserve:

- a data fingerprint;
- source and schema metadata;
- model configuration;
- random seed;
- validation artifacts;
- experiment identity;
- exported HTML / JSON reports.

The aim is simple: record not only the final result, but also the path that produced it.

```bash
pip install --upgrade asrquant
```

Docs: https://docs.asr-lab.online/
