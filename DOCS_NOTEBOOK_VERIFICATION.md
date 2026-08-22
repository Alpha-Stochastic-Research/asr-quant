# ASRQuant 1.2.0 — Documentation & Notebook Verification

Verification date: 2026-08-22

## Official quickstart notebook

File: `notebooks/ASRQuant_v1.2.0_Quickstart.ipynb`

Status: **PASS**

- Target release: ASRQuant 1.2.0
- Code cells: 15
- Code cells executed: 15
- Execution errors: 0
- Mathematical display delimiters: 26 balanced `$$ ... $$` blocks
- `\\(...\\)` math delimiters: 0
- `\\[...\\]` math delimiters: 0
- Single-dollar inline math delimiters: 0
- External market-data dependency: none
- Random seed fixed for deterministic tutorial data

## Mathematical content reviewed

The notebook now states the core formulas used by the examples before the corresponding code, including:

- single-factor return generation and price compounding;
- simple returns;
- minimum-variance portfolio construction;
- portfolio returns and wealth dynamics;
- Black–Scholes option pricing;
- zero-rate discount factors and par swap rates;
- momentum and information coefficient diagnostics;
- portfolio volatility, Value at Risk and Expected Shortfall;
- midquote and microprice;
- predictive hypothesis screening relation;
- OLS estimation;
- ridge regression and chronological walk-forward validation.

## Writing and notation rules

- Displayed equations use only `$$ ... $$`.
- Variables appearing in explanatory prose are written as code identifiers or plain language rather than mixed delimiter styles.
- Each major section follows the sequence: concept → formula → ASRQuant implementation → interpretation.
- Tutorial results are explicitly separated from empirical or investment claims.
