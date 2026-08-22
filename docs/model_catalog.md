# Quantitative model catalog

This catalog distinguishes implemented research baselines from models that remain outside version 0.2.0.

## Stochastic processes

| Model | Dispatcher key | Main parameters | Numerical method |
|---|---|---|---|
| Arithmetic Brownian motion | `abm` | drift, normal volatility | Gaussian increments |
| Geometric Brownian motion | `gbm` | drift, lognormal volatility | exact log transition |
| Correlated GBM | lower-level function | vectors + correlation | Cholesky Gaussian shocks |
| Ornstein-Uhlenbeck | `ou` | speed, long mean, volatility | Euler |
| CIR | `cir` | speed, long mean, volatility | full-truncation Euler |
| Vasicek | `vasicek` | speed, long mean, volatility | exact Gaussian transition |
| Heston | `heston` | variance mean reversion, vol-of-vol, correlation | full-truncation Euler |
| Merton jump diffusion | `merton` | diffusion + Poisson-normal jumps | time discretization |

All stochastic APIs expose seeds and return `SimulationResult`, including full paths, terminal values, parameter metadata, summary statistics, and plotting shortcuts.

## Monte Carlo

`monte_carlo_price(...)` accepts a simulation and an arbitrary terminal payoff. Specialized wrappers implement:

- European calls and puts under risk-neutral GBM;
- arithmetic-average Asian calls and puts;
- antithetic sampling for GBM;
- standard error and normal-approximation confidence interval.

Monte Carlo confidence intervals quantify simulation error under the sampled model. They do not include parameter uncertainty or model risk.

## Derivative pricing

| Model | Scope |
|---|---|
| Black-Scholes-Merton | European equity-style calls/puts with continuous dividend yield and analytic Greeks |
| Bachelier | European normal-model calls/puts with forward, normal volatility, and discounting |
| Black-76 | European options on forwards/futures |
| CRR binomial | European and American calls/puts |
| Monte Carlo GBM | European and arithmetic-average Asian calls/puts |

The unified entry point is `price_option(model, ...)` or `lab.option(model, ...)`.

## Martingale diagnostics

`martingale_diagnostics(...)` evaluates selected finite-sample implications of a discounted martingale:

- zero unconditional mean of increments;
- no linear predictability from the lagged level under HAC covariance;
- no increment autocorrelation at a selected Ljung-Box horizon.

Non-rejection is not proof of the conditional-expectation definition.

## Regression and time series

Implemented families:

- OLS with classical, HC0-HC3, or Newey-West/HAC covariance;
- rolling OLS;
- quantile regression;
- polynomial regression;
- Ridge, Lasso, and Elastic Net;
- logistic regression;
- factor regression;
- ADF and KPSS stationarity tests;
- Engle-Granger cointegration test;
- Granger-predictive tests;
- ARIMA and VAR;
- moving-block bootstrap, permutation testing, and Benjamini-Hochberg FDR.

Regression outputs retain aligned fitted values, residuals, confidence intervals, and diagnostics. Statistical significance is not causal identification.

## Machine learning

The package provides:

- explicit lag features;
- technical features based only on current and past prices;
- forward return or direction targets;
- chronological walk-forward fitting;
- expanding or rolling training windows;
- an explicit train-test gap;
- regression and classification metrics;
- fitted models and out-of-sample prediction paths.

The user supplies any scikit-learn-compatible estimator. ASRQuant does not claim that a model is economically useful merely because predictive metrics are positive.

## Portfolio and covariance models

Covariance estimators:

- sample;
- exponentially weighted;
- Ledoit-Wolf;
- Oracle Approximating Shrinkage.

Allocators:

- minimum variance;
- maximum Sharpe;
- equal-risk contribution;
- maximum diversification;
- hierarchical risk parity;
- Black-Litterman posterior construction;
- random efficient-frontier analysis.

## Volatility

- rolling realized volatility;
- Parkinson range estimator;
- Garman-Klass OHLC estimator;
- EWMA volatility;
- optional GARCH forecast through the `arch` extra.

## Fixed income

- zero-coupon pricing;
- fixed-rate bond cash flows and pricing;
- yield to maturity;
- Macaulay and modified duration;
- convexity;
- simple par-instrument zero-curve bootstrapping.

## Not implemented in 0.2.0

Specialist extensions still include local volatility, SABR, Hull-White, affine multi-factor term structures, credit intensity, exotics, adjoint differentiation, calibration frameworks, order-book simulation, event-driven execution, and production broker connectivity.

## Universal Monte Carlo estimators (1.0.0)

The universal engine separates scenario generation, pathwise quantity evaluation and statistical reduction. Built-in reductions are expectation, probability, variance, standard deviation, median, quantile, VaR, Expected Shortfall, minimum and maximum. A custom callable may be used as the reducer.

Scenario utilities include inverse-transform sampling, Gaussian generation, Cholesky-correlated Gaussian vectors and generic Euler-Maruyama dynamics. Pathwise hedging losses include proportional transaction costs.

## Approximation and response surfaces (1.0.0)

- piecewise-linear interpolation;
- bilinear interpolation on regular grids;
- cubic splines;
- Gaussian Nadaraya-Watson kernel regression;
- radial-basis interpolation;
- Gaussian-process regression with predictive uncertainty;
- linear, polynomial, ridge and lasso response regressions;
- controlled extrapolation;
- RMSE, MAE and R-squared validation;
- first- and second-order surface sensitivities.
