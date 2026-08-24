# ASRQuant 1.0.0 — Paper/Package Contract

This document is the release bridge between **manuscript v0.1.0** and **ASRQuant 1.0.0**.

The rule for the stable release is simple: a capability described as implemented in the manuscript must be represented by an actual public API and an automated test. Future or specialist capabilities must be identified as limitations or roadmap items instead of being implied as implemented.

| Manuscript capability | Stable implementation | Executable evidence |
|---|---|---|
| One-import public API | `import asrquant as asr`; `open_lab`, `fit`, `simulate`, `price_option`, `visualize`, `show`, `save` | `test_one_import_polynomial_modelling_and_visualization`, `test_paper_one_import_formula_to_polynomial_model` |
| PDF literature ingestion and source-linked hypotheses | `asr.research.from_pdfs`, `LiteratureCorpus`, `HypothesisRegistry`, `ResearchProject` | `test_appendix_pdf_to_hypothesis_registry_real_text_pdf` |
| Hypothesis → data → features → signal → portfolio → test → robustness → governed decision | `ResearchProject` workflow | `test_appendix_research_project_to_governed_paper_trade` |
| CSV and in-memory quantitative laboratory | `QuantLab.from_csv`, `QuantLab`, `open_lab` | `test_appendix_csv_to_audited_backtest`, `test_appendix_in_memory_custom_strategy` |
| Provider-neutral market-data contract | provider adapters + `QuantLab.from_provider` | `test_appendix_provider_contract_without_network` |
| Seven core stochastic-process families | ABM, GBM, OU, CIR, Vasicek, Heston, Merton | `test_paper_seven_core_stochastic_process_families` |
| Monte Carlo uncertainty and martingale diagnostics | `monte_carlo.py`, simulation result objects, `martingale_diagnostics` | `test_appendix_monte_carlo_martingale_and_option_pricing` + quant suite |
| Derivative pricing | BSM, Bachelier, Black-76, CRR, implied vol, European/Asian MC | `test_paper_derivative_pricing_contract` |
| Econometrics and polynomial modelling | `asr.fit`, `asr.stats`, robust OLS, polynomial/quantile/logistic methods | paper formula test + statistics suite |
| Leakage-aware ML and chronological validation | `machine_learning.py`, walk-forward, purged/gap-aware split tests | quant/core test groups |
| Portfolio/risk/volatility | `optimization.py`, `metrics.py`, `volatility.py` | quant/core test groups |
| Fixed income | bond price, YTM, duration, convexity, validated zero-curve bootstrap | `test_paper_fixed_income_contract` |
| Implementation-risk audit | `QuantLab.audit`, `implementation_audit` | `test_appendix_implementation_audit_and_regression` |
| N-dimensional parameter surfaces and exports | `surfaces.py` | `test_paper_surface_contract_html_and_gif_export` + surface group |
| 100+ visualization functions | 102 module-level public functions + result plot methods | `test_visualization_catalog_remains_above_one_hundred_public_functions` |
| Paper broker, order states, partial fills and risk controls | `PaperBroker`, `PaperTrader`, `RiskPolicy`, market/limit/stop/stop-limit orders | `test_paper_broker_order_types_partial_fill_and_cancellation`, governed paper-trade test |
| Durable audit and fail-closed deployment controls | `SQLiteAuditStore`, `ProductionReadinessGate`, `DeploymentCertificate`, live safety primitives | production group (62 tests) |

## Stable release validation

ASRQuant 1.0.0 collects **154 automated tests**, including **18 paper-contract tests**. The paper-contract suite is part of the CI domain matrix and must pass before a stable source commit is treated as matching manuscript v0.1.0.

## Deliberate boundaries

The stable release does not claim exchange queue realism, complete point-in-time corporate-action reconstruction, universal broker behavior, guaranteed profitability, causal identification from predictive regressions, or automatic authorization for live capital. These boundaries remain explicit in the manuscript and software documentation.
