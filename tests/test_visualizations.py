import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from asrquant import QuantLab
from asrquant.derivatives import simulate_gbm
from asrquant.statistics import ols, rolling_regression
from asrquant.viz import derivatives, general, market, microstructure, ml, portfolio, regression, risk


def _close(fig):
    assert fig is not None
    if hasattr(fig, "savefig"):
        plt.close(fig)


def test_market_and_performance_plots(prices, returns):
    lab = QuantLab(prices)
    result = lab.backtest("sma", fast=10, slow=40)
    figures = [
        market.price_chart(prices), market.returns_chart(returns=returns), market.distribution(returns["A"]),
        market.ecdf(returns["A"]), market.qq_plot(returns["A"]), market.rolling_statistics(returns),
        market.autocorrelation(returns["A"]), market.autocorrelation(returns["A"], pacf=True),
        market.correlation_heatmap(returns), market.rolling_correlation(returns), market.monthly_heatmap(returns["A"]),
        result.plot("dashboard"), result.plot("equity_drawdown"), result.plot("rolling_metrics"),
    ]
    for fig in figures:
        _close(fig)


def test_risk_portfolio_derivative_ml_microstructure_plots(prices, returns):
    cov = returns.cov().to_numpy() * 252
    mu = returns.mean().to_numpy() * 252
    reg = ols(returns["A"], returns[["B"]])
    roll = rolling_regression(returns["A"], returns[["B"]], window=40)
    paths = simulate_gbm(100, 0.05, 0.2, 1, steps=20, paths=50)
    x = np.linspace(80, 120, 15)
    y = np.linspace(0.1, 2.0, 10)
    z = np.outer(np.linspace(0.3, 0.2, len(y)), 1 + 0.0005 * (x - 100) ** 2)
    figures = [
        risk.var_es_plot(returns["A"]), risk.rolling_var_es(returns["A"], window=80), risk.monte_carlo_fan(paths),
        portfolio.efficient_frontier(mu, cov, n_portfolios=100), portfolio.risk_contribution_plot([1/3]*3, cov),
        portfolio.correlation_network(returns, threshold=0.0), regression.regression_scatter(returns["B"], returns["A"], reg),
        regression.residual_diagnostics(reg), regression.coefficient_intervals(reg), regression.rolling_coefficients(roll),
        derivatives.payoff_diagram(x, 100), derivatives.greek_curves(x, 100, 1, 0.02, 0.2),
        derivatives.volatility_surface(x, y, z), general.surface3d(x, y, z),
        ml.feature_importance([0.1, 0.4, -0.2], ["a", "b", "c"]), ml.prediction_path([1,2,3], [1.1,1.9,3.2]),
        microstructure.bid_ask_spread(prices["A"]-0.01, prices["A"]+0.01),
        microstructure.volume_profile(prices["A"], pd.Series(100, index=prices.index)),
    ]
    for fig in figures:
        _close(fig)
