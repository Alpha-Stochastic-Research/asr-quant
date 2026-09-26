# ASRQuant

**Auditable quantitative finance research in Python.**

ASRQuant is the open-source quantitative-finance toolkit developed by **Alpha Stochastic Research (ASR)**. It connects market data, statistical research, fixed income, derivatives, portfolio construction, risk, factor models, backtesting, machine learning, simulation and reproducibility in one research-oriented Python package.

<div class="grid cards" markdown>

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

-   **API reference**

    ---

    Browse the package API generated directly from the current source tree at build time.

    [Generated reference →](generated_api_reference.md)

</div>

## Stable release

The current stable release is **ASRQuant 1.3.0**. The 1.3 series strengthens numerical integrity, point-in-time research contracts, model-selection-risk diagnostics, interest-rate infrastructure, reproducibility and deployment controls.

```bash
pip install asrquant
```

```python
import asrquant as asr
print(asr.__version__)
```

## Documentation lifecycle

This documentation is built from the repository itself. On every relevant push to `main`, GitHub Actions rebuilds the MkDocs site, regenerates the Python API reference from the source tree and deploys the result to GitHub Pages. Pull requests build the documentation in validation mode so broken links, invalid navigation or documentation build failures can be caught before merge.

!!! note "Research software"
    ASRQuant is research infrastructure. It is not investment advice, a broker, or an execution venue.
