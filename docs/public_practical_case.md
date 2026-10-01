# Public practical case

## ECB EUR curve → 5Y IRS → risk → validation → audit trail

This is the recommended public demonstration of ASRQuant 1.3.

The notebook uses one coherent rates case to show the package's main workflows rather than presenting isolated API examples.

### What it covers

1. ECB EUR yield-curve data;
2. data validation and immutable snapshots;
3. PCA of curve changes;
4. explicit curve states and market conventions;
5. a 5Y payer interest-rate swap;
6. DV01 and key-rate DV01;
7. quote-space PV01 through `CurveBuilder`;
8. realized P&L explanation;
9. parallel, steepener and flattener stresses;
10. a simple curve research hypothesis;
11. CPCV, PBO, Reality Check and SPA;
12. `Experiment`, `ExperimentRegistry` and `ResearchReport`.

### Run it

[**Open the notebook on GitHub**](https://github.com/Alpha-Stochastic-Research/asr-quant/blob/main/notebooks/ASRQuant_v1.3.0_Public_Practical_Case.ipynb)

[**Run in Google Colab**](https://colab.research.google.com/github/Alpha-Stochastic-Research/asr-quant/blob/main/notebooks/ASRQuant_v1.3.0_Public_Practical_Case.ipynb)

Install the package first if running locally:

```bash
pip install --upgrade "asrquant[providers,visualization]"
```

### Why this case

The workflow demonstrates the core ASRQuant idea:

> A quantitative result should preserve the path from **data and conventions** to **risk, validation and reproducibility**.

### Data note

The ECB euro-area AAA sovereign spot curve is used as a transparent public research proxy. It is not a substitute for a production EUR IRS multi-curve stack with OIS discounting, projection curves, collateral conventions and live market swap quotes.

### Validation note

The curve-signal section is a research-method demonstration. CPCV, PBO, Reality Check and SPA are evidence filters, not trading guarantees or proof of persistent alpha.
