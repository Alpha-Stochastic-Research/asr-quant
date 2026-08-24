import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from asrquant.simulation import geometric_brownian_motion
from asrquant.statistics import ols
from asrquant.viz import derivatives, market, microstructure, ml, portfolio, regression, risk, simulation


def _close(fig):
    assert fig is not None
    plt.close(fig)


def test_extended_visualization_catalog_smoke():
    rng = np.random.default_rng(7)
    index = pd.bdate_range("2020-01-01", periods=320)
    returns = pd.DataFrame(
        rng.normal(0.0002, 0.01, size=(320, 4)),
        index=index,
        columns=list("ABCD"),
    )
    prices = 100 * (1 + returns).cumprod()

    _close(market.seasonality_boxplot(returns["A"]))
    _close(market.lag_scatter(returns["A"]))
    _close(market.volatility_cone(returns["A"], windows=(5, 21, 63)))
    _close(market.rolling_beta(returns["A"], returns["B"], window=21))
    _close(market.period_return_ranking(returns, rule="QE"))

    _close(risk.rolling_skew_kurtosis(returns["A"], window=63))
    _close(risk.var_exceedances(returns["A"], window=63))
    _close(risk.drawdown_duration_plot(returns["A"]))
    _close(risk.risk_return_scatter(returns))
    _close(risk.expected_shortfall_contributions(np.repeat(0.25, 4), returns))

    fit = ols(returns["A"], returns[["B", "C"]], covariance="HAC", maxlags=3)
    _close(regression.residual_acf(fit, lags=10))
    _close(regression.influence_plot(fit, top=3))
    _close(regression.prediction_interval(fit))
    _close(regression.partial_residual_plot(fit, variable="B"))

    covariance = returns.cov() * 252
    expected = returns.mean() * 252
    _close(portfolio.covariance_heatmap(covariance))
    _close(portfolio.correlation_dendrogram(returns))
    _close(portfolio.concentration_curve(pd.Series([0.4, 0.3, 0.2, 0.1], index=returns.columns)))
    weights = pd.DataFrame(np.tile([0.4, 0.3, 0.2, 0.1], (20, 1)), index=index[:20], columns=returns.columns)
    _close(portfolio.rolling_risk_contributions(weights, covariance))
    _close(portfolio.frontier_surface(expected, covariance, n_portfolios=100))

    strikes = np.array([80, 90, 100, 110, 120])
    maturities = np.array([0.25, 0.5, 1.0])
    vols = np.array([[0.25, 0.22, 0.20, 0.21, 0.24], [0.24, 0.21, 0.19, 0.20, 0.23], [0.23, 0.20, 0.18, 0.19, 0.22]])
    _close(derivatives.implied_volatility_smile(strikes, vols[1], forward=100))
    _close(derivatives.term_structure_slices(strikes, maturities, vols))
    _close(derivatives.greek_heatmap(strikes, maturities, 100, 0.03, 0.2))
    _close(derivatives.scenario_pnl_surface(strikes, np.array([0.1, 0.2, 0.3]), 100, 1, 0.03, 100, 0.2))

    y = rng.integers(0, 2, 200)
    probability = np.clip(0.2 + 0.6 * y + rng.normal(0, 0.2, 200), 0, 1)
    _close(ml.precision_recall(y, probability))
    _close(ml.learning_curve_plot([50, 100, 150], [0.9, 0.8, 0.75], [0.55, 0.62, 0.66]))
    _close(ml.lift_curve(y, probability, bins=5))
    _close(ml.permutation_importance_plot(rng.normal(size=(8, 5)), names=[f"x{i}" for i in range(8)]))

    bid = prices["A"] - 0.01
    ask = prices["A"] + 0.01
    _close(microstructure.spread_distribution(bid, ask))
    _close(microstructure.order_flow_imbalance(pd.Series(rng.uniform(1, 5, 320), index=index), pd.Series(rng.uniform(1, 5, 320), index=index)))
    intraday_index = pd.date_range("2024-01-01", periods=96, freq="15min")
    _close(microstructure.intraday_seasonality(pd.Series(rng.normal(size=96), index=intraday_index)))
    _close(microstructure.price_impact_scatter(rng.normal(size=200), rng.normal(size=200)))

    sim = geometric_brownian_motion(paths=200, steps=40, random_state=7)
    _close(simulation.quantile_bands(sim))
    _close(simulation.increment_diagnostics(sim))
    _close(simulation.first_passage_distribution(sim, barrier=105))
    _close(simulation.convergence_diagnostics(rng.normal(2, 0.5, 200), reference=2))
