# Methodology

ASRQuant follows a specification-first workflow: data, model, execution, costs, validation, and randomness are explicit inputs rather than hidden notebook state.

## Backtest timing

For target weight `z[t]` and execution delay `d`, the effective weight is:

```text
w[t] = z[t-d]
```

for the asset return ending at `t`. The default `d=1` prevents a close-derived signal from receiving the return that generated it. Same-bar execution remains available only when the user's information and execution timestamps justify it.

## Portfolio return

For asset return vector `r[t]`, cash weight `c[t]`, annual cash rate `r_f`, annualization `A`, and total cost `C[t]`:

```text
R_gross[t] = dot(w[t-1], r[t]) + c[t-1] * r_f / A
R_net[t]   = R_gross[t] - C[t]
```

## Turnover and costs

```text
tau[t] = sum_i abs(w[t,i] - w[t-1,i])
```

The cost model can combine:

- commissions;
- bid-ask spread;
- slippage;
- annualized borrow cost on shorts;
- nonlinear impact as a function of traded notional.

Costs are reported separately from gross returns.

## Stochastic models

Every simulation declares:

- initial state;
- horizon and discretization;
- path count;
- process parameters;
- random seed;
- variance-reduction choice when available.

Research baselines use exact transitions where implemented and documented Euler-style approximations otherwise.

## Monte Carlo

The estimator is the mean discounted payoff. ASRQuant reports the sample standard error and a normal-approximation confidence interval. Reproducible comparisons should preserve the seed, path count, time grid, payoff definition, and model parameters.

## Statistical inference

Regressions align observations before fitting and retain residual diagnostics. HAC covariance is the default for OLS because financial errors often exhibit heteroskedasticity and serial dependence. The appropriate lag length remains a research decision.

## Machine learning

Features must be available at decision time. Forward targets are evaluated with chronological folds, fresh estimator clones, and an optional gap. Hyperparameter selection must be nested or otherwise separated from final evaluation by the researcher.

## Reproducibility

The package fingerprints data, specifications, and experiments. A reproducible artifact should also freeze provider responses when permitted, dependency versions, code revision, all tested alternatives, and rejected experiments.

See the paper for complete equations, empirical validation, and limitations.
