# ASRQuant 1.1.0 — Research Discovery and Interest Rates

ASRQuant 1.1.0 extends the stable 1.0.0 research platform in two directions: **research discovery/weekly publication operations** and a **fixed-income / interest-rate derivatives research stack**. The 1.0.0 paper-contract tests remain in the suite.

## Research Discovery

A Research or Analyst team can now begin from data, literature, model disagreement, robustness results or a curated domain catalogue rather than requiring a pre-written hypothesis. `ResearchBoard.start()` hands the selected candidate to the existing `ResearchProject` workflow.

Automated candidates are deliberately conservative: novelty is `NOT_ESTABLISHED` until the team performs a documented prior-art review.

## Friday-to-Friday operations

`WeeklyResearchCycle` formalizes the ASR cadence from Friday launch to next-Friday publication and generates the research brief, research note, reproducibility checklist, claim audit, plan/status tables and project manifest.

## Interest-rate research

`asr.rates` now covers the major research path from conventions and curve construction to multi-curve valuation, linear rate products, volatility products, smile calibration, short-rate/forward-rate models and curve risk. It also includes RFR/OIS compounding, bond forwards, covered-interest-parity/zero-coupon cross-currency foundations, zero-coupon inflation swaps, curve scenarios/key-rate hedging and a generic Bermudan least-squares Monte Carlo engine. An explicit exercise/curriculum layer lets the same API support training and weekly research.

## ECB data

`ECBProvider` adds direct programmatic access to the ECB Data Portal. The yield-curve helper is tailored to aligned euro-area AAA spot-curve research; generic ECB series remain available through `history()`.

## Compatibility

Legacy fixed-income helpers remain available at the top-level API and through `asr.rates`. Existing 1.0.0 paper-contract tests are retained.

## Safety / model-risk boundary

The new rates models are transparent research/reference implementations. They do not claim to replace a trading desk's complete conventions, holiday-calendar, collateral/CSA, exchange-rule, legal, XVA or independently validated production-pricer infrastructure.
