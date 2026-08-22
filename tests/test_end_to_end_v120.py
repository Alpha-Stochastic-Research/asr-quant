"""End-to-end research path for the v1.2 quantitative-research additions."""
import numpy as np
import pandas as pd

import asrquant as asr


def test_signal_to_alpha_to_portfolio_risk_to_execution_diagnostics():
    rng = np.random.default_rng(123)
    index = pd.date_range("2025-01-01", periods=320, freq="B")
    assets = [f"Asset{i:02d}" for i in range(20)]

    # Synthetic panel with persistent cross-sectional structure.
    factor = rng.normal(0.0002, 0.008, size=len(index))
    betas = np.linspace(0.6, 1.4, len(assets))
    idio = rng.normal(0.0, 0.006, size=(len(index), len(assets)))
    asset_returns = factor[:, None] * betas[None, :] + idio
    returns = pd.DataFrame(asset_returns, index=index, columns=assets)
    prices = 100.0 * (1.0 + returns).cumprod()

    # A simple momentum score, deliberately lagged to avoid using the current
    # day's return in the score.
    raw_signal = prices.pct_change(20, fill_method=None).shift(1)
    signal = asr.alpha.cross_sectional_zscore(raw_signal)
    fwd = asr.alpha.forward_returns(prices, 5)[5]
    alpha_report = asr.alpha.analyze_signal(signal, fwd, quantiles=5, min_assets=15)

    # Build one fixed risk snapshot from the latest finite signal weights.
    latest_weights = alpha_report.weights.dropna().iloc[-1]
    risk_report = asr.risk.portfolio_risk_report(
        returns.tail(252),
        latest_weights,
        level=0.95,
    )

    # Execution diagnostics on a synthetic top-of-book stream.
    mid = pd.Series(100 + np.cumsum(rng.normal(0, 0.01, 200)))
    bid = mid - 0.01
    ask = mid + 0.01
    bid_size = pd.Series(rng.integers(10, 100, size=len(mid)), dtype=float)
    ask_size = pd.Series(rng.integers(10, 100, size=len(mid)), dtype=float)
    microprice = asr.microstructure.microprice(bid, ask, bid_size, ask_size)
    ofi = asr.microstructure.order_flow_imbalance(bid, ask, bid_size, ask_size)

    assert len(alpha_report.information_coefficient.dropna()) > 200
    assert risk_report.summary["annualized_volatility"] > 0
    assert abs(risk_report.summary["net_exposure"]) < 1e-10
    assert microprice.between(bid, ask).all()
    assert len(ofi) == len(mid)


def test_quantlab_120_research_convenience_methods():
    rng = np.random.default_rng(321)
    index = pd.date_range("2022-01-03", periods=420, freq="B")
    base = rng.normal(0.0002, 0.008, size=(len(index), 8))
    returns = pd.DataFrame(base, index=index, columns=[f"A{i}" for i in range(8)])
    prices = 100.0 * (1.0 + returns).cumprod()
    lab = asr.QuantLab(prices)

    pca = lab.factor_analysis(n_components=3)
    assert pca.loadings.shape == (8, 3)

    weights = pd.Series(1 / 8, index=prices.columns)
    risk = lab.portfolio_risk(weights, level=0.95)
    assert risk.summary["annualized_volatility"] > 0

    signal = prices.pct_change(20, fill_method=None).shift(1)
    alpha = lab.alpha_analysis(signal, horizon=5, quantiles=4, min_assets=6)
    assert len(alpha.information_coefficient.dropna()) > 100


def test_quantlab_hypothesis_discovery_from_custom_data():
    rng = np.random.default_rng(99)
    index = pd.date_range("2021-01-01", periods=260, freq="B")
    x = rng.normal(size=len(index))
    y = np.roll(x, 1) * 0.4 + rng.normal(scale=0.6, size=len(index))
    prices = pd.DataFrame({"A": 100 * np.exp(np.cumsum(rng.normal(0, 0.01, len(index))))}, index=index)
    lab = asr.QuantLab(prices)
    panel = pd.DataFrame({"x": x, "y": y}, index=index)
    ideas = lab.discover_hypotheses(
        data=panel,
        targets="y",
        horizons=(1,),
        lags=(0, 1),
        transforms={"x": "raw", "y": "raw"},
        min_observations=100,
        include_regime_tests=False,
        include_cointegration=False,
    )
    assert len(ideas) >= 1
