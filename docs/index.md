# ASRQuant

**Auditable quantitative finance research in Python.**

ASRQuant is the open-source quantitative-finance toolkit developed by **Alpha Stochastic Research (ASR)** for reproducible market-data, fixed-income, derivatives, risk, backtesting, validation, simulation and research-lineage workflows.

```bash
pip install --upgrade asrquant
```

<div class="grid cards" markdown>

-   **Run the public practical case**

    ---

    ECB EUR curve → 5Y IRS → DV01 → quote PV01 → stress → PBO / SPA → auditable report.

    [Public practical case →](public_practical_case.md)

-   **Get started**

    ---

    Install ASRQuant and build a first reproducible research workflow.

    [Quickstart →](quickstart.md)

-   **Quant research**

    ---

    Explore validation, risk, Monte Carlo, hypothesis discovery and research infrastructure.

    [Research toolkit →](quant_research_toolkit.md)

-   **Fixed income & derivatives**

    ---

    Curves, conventions, rates risk and derivatives implemented through ASRQuant's native quantitative engines.

    [Interest-rate derivatives →](interest_rate_derivatives.md)

-   **Research validation**

    ---

    CPCV, PBO, Reality Check, SPA, leakage diagnostics and multiverse analysis.

    [Validation →](validation.md)

-   **API reference**

    ---

    Browse the API generated directly from the current source tree.

    [Generated reference →](generated_api_reference.md)

</div>

## What makes ASRQuant different

ASRQuant is designed around a research chain rather than a collection of isolated functions:

**data → assumptions → model → risk → validation → interpretation → reproducibility**

The package keeps quantitative objects and research evidence inspectable: data snapshots, curve diagnostics, quote-space risk, time-series validation, experiment fingerprints and exported research reports.

## ASRQuant 1.3

The 1.3 release line adds and strengthens:

- market conventions and curve-construction contracts;
- rates instruments and quote-space PV01;
- credit foundations and scenarios;
- CPCV, PBO, Reality Check, SPA, leakage and multiverse diagnostics;
- point-in-time data and immutable snapshots;
- experiment lineage, research graphs and reports;
- calibration, sensitivities, transaction costs and cross-domain risk utilities.

## One import

```python
import asrquant as asr
print(asr.__version__)
```

!!! note "Research software"
    ASRQuant is research infrastructure. It is not investment advice, a broker, or an execution venue.
