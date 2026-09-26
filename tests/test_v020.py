import sqlite3

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, LogisticRegression

from asrquant import (
    QuantLab,
    arithmetic_brownian_motion,
    asian_option_mc,
    bachelier_price,
    black76_price,
    black_scholes_price,
    crr_binomial_price,
    european_option_mc,
    geometric_brownian_motion,
    heston_process,
    martingale_diagnostics,
    price_option,
)
from asrquant.data import data_quality_report, load_prices, load_sql, resample_ohlcv
from asrquant.machine_learning import forward_target, technical_features, walk_forward_fit
from asrquant.optimization import (
    black_litterman,
    efficient_frontier,
    estimate_covariance,
    hierarchical_risk_parity,
    maximum_diversification,
)
from asrquant.providers import AlphaVantageProvider, BinanceProvider, FREDProvider, PollingFeed
from asrquant.statistics import (
    cointegration_test,
    factor_regression,
    logistic_regression,
    polynomial_regression,
    quantile_regression,
    regularized_regression,
)


def _prices(n=300):
    rng = np.random.default_rng(42)
    index = pd.bdate_range("2020-01-01", periods=n)
    returns = rng.normal(0.0003, 0.01, size=(n, 3))
    return pd.DataFrame(100 * np.exp(np.cumsum(returns, axis=0)), index=index, columns=["A", "B", "C"])


def test_csv_and_json_loading(tmp_path):
    prices = _prices(30)
    csv = tmp_path / "prices.csv"
    js = tmp_path / "prices.json"
    prices.rename_axis("Date").reset_index().to_csv(csv, index=False)
    prices.rename_axis("Date").reset_index().to_json(js)
    assert load_prices(csv, "Date").shape == prices.shape
    assert load_prices(js, "Date").shape == prices.shape
    assert QuantLab.from_csv(csv, "Date").assets == ["A", "B", "C"]


def test_sql_loading():
    prices = _prices(20).rename_axis("Date").reset_index()
    connection = sqlite3.connect(":memory:")
    prices.to_sql("prices", connection, index=False)
    loaded = load_sql("select * from prices", connection, "Date")
    assert loaded.shape == (20, 3)


def test_data_quality_and_ohlcv_resampling():
    index = pd.date_range("2024-01-01", periods=48, freq="h")
    base = np.linspace(100, 110, 48)
    ohlcv = pd.DataFrame({"Open": base, "High": base + 2, "Low": base - 2, "Close": base + 0.5, "Volume": 10}, index=index)
    daily = resample_ohlcv(ohlcv, "D")
    assert len(daily) == 2
    assert data_quality_report(daily)["rows"] == 2


def test_stochastic_models_shapes_and_positive_prices():
    abm = arithmetic_brownian_motion(paths=50, steps=20)
    gbm = geometric_brownian_motion(paths=50, steps=20)
    heston = heston_process(paths=50, steps=20)
    assert abm.paths.shape == gbm.paths.shape == heston.paths.shape == (21, 50)
    assert (gbm.paths > 0).all().all()
    assert (heston.paths > 0).all().all()


def test_monte_carlo_matches_black_scholes():
    analytic = black_scholes_price(100, 100, 1, 0.03, 0.2)
    mc = european_option_mc(100, 100, 1, 0.03, 0.2, paths=100_000, random_state=1)
    assert abs(mc.price - analytic) < 0.15
    assert mc.confidence_interval[0] < analytic < mc.confidence_interval[1]


def test_asian_mc_and_unified_option_dispatch():
    result = asian_option_mc(100, 100, 1, 0.02, 0.2, paths=4_000, steps=24)
    unified = price_option("asian_mc", spot=100, strike=100, maturity=1, rate=0.02, volatility=0.2, paths=4_000, steps=24)
    assert result.price > 0
    assert unified.price > 0


def test_bachelier_black76_and_crr_consistency():
    bachelier = bachelier_price(100, 100, 1, 10)
    black76 = black76_price(100, 100, 1, 0.02, 0.2)
    bsm = black_scholes_price(100, 100, 1, 0.02, 0.2)
    tree = crr_binomial_price(100, 100, 1, 0.02, 0.2, steps=1000)
    assert bachelier > 0 and black76 > 0
    assert abs(tree - bsm) < 0.02


def test_quantlab_high_level_models():
    prices = _prices(100)[["A"]]
    lab = QuantLab(prices)
    assert lab.monte_carlo("gbm", steps=5, paths=10).paths.shape == (6, 10)
    assert lab.option("black_scholes", strike=100, maturity=1, rate=0.02, volatility=0.2).price > 0
    assert lab.option("bachelier", strike=100, maturity=1, normal_volatility=10).price > 0


def test_martingale_diagnostics_on_brownian_path():
    path = arithmetic_brownian_motion(initial=100, drift=0, volatility=1, steps=600, paths=1, random_state=5).paths.iloc[:, 0]
    path.index = pd.bdate_range("2020-01-01", periods=len(path))
    result = martingale_diagnostics(path, lags=5)
    assert "mean increment p-value" in result.statistics
    assert len(result.increments) == 600


def test_regression_families():
    rng = np.random.default_rng(0)
    index = pd.RangeIndex(300)
    x = pd.DataFrame({"x": rng.normal(size=300)}, index=index)
    y = 1 + 2 * x["x"] + rng.normal(scale=0.2, size=300)
    assert abs(quantile_regression(y, x).coefficients["x"] - 2) < 0.1
    assert polynomial_regression(y, x, degree=2).diagnostics["R2"] > 0.95
    assert regularized_regression(y, x, method="ridge")["r2"] > 0.95
    binary = (y > y.median()).astype(float)
    assert logistic_regression(binary, x).diagnostics["Pseudo R2"] > 0


def test_factor_and_cointegration():
    rng = np.random.default_rng(1)
    idx = pd.bdate_range("2020-01-01", periods=500)
    factor = pd.Series(rng.normal(0, 0.01, 500), index=idx, name="MKT")
    asset = 0.0001 + 1.3 * factor + rng.normal(0, 0.002, 500)
    result = factor_regression(asset, factor.to_frame())
    assert abs(result.coefficients["MKT"] - 1.3) < 0.05
    x = pd.Series(np.cumsum(rng.normal(size=500)), index=idx)
    y = 2 * x + rng.normal(scale=0.5, size=500)
    assert cointegration_test(y, x)["p_value"] < 0.05


def test_walk_forward_ml_regression_and_classification():
    prices = _prices(350)["A"]
    features = technical_features(prices).shift(1)
    target = forward_target(prices)
    reg = walk_forward_fit(LinearRegression(), features, target, train_size=120, test_size=30, step=30, task="regression")
    assert len(reg.predictions) > 0
    class_target = forward_target(prices, classification=True)
    cls = walk_forward_fit(LogisticRegression(max_iter=1000), features, class_target, train_size=120, test_size=30, step=30, task="classification")
    assert 0 <= cls.aggregate_metrics["accuracy"] <= 1


def test_covariance_and_portfolio_extensions():
    returns = _prices(300).pct_change().dropna()
    cov = estimate_covariance(returns, "ledoit_wolf")
    md = maximum_diversification(cov)
    frontier = efficient_frontier(returns.mean() * 252, cov, points=10)
    hrp = hierarchical_risk_parity(returns)
    posterior_mean, posterior_cov = black_litterman(cov, np.repeat(1/3, 3), 2.5)
    assert np.isclose(md.sum(), 1)
    assert len(frontier) > 0
    assert np.isclose(hrp.sum(), 1)
    assert posterior_mean.shape == (3,) and posterior_cov.shape == (3, 3)


def test_provider_parsers_without_network(monkeypatch):
    class Response:
        def __init__(self, payload): self.payload = payload
        def raise_for_status(self): return None
        def json(self): return self.payload

    alpha_payload = {"Time Series (Daily)": {"2024-01-02": {"1. open": "1", "2. high": "2", "3. low": "0.5", "4. close": "1.5", "5. volume": "10"}}}
    monkeypatch.setattr("requests.get", lambda *a, **k: Response(alpha_payload))
    assert AlphaVantageProvider("key").history("IBM").iloc[0]["Close"] == 1.5

    binance_payload = [[1704067200000, "1", "2", "0.5", "1.5", "10", 1704153599999, "15", 4, "5", "7", "0"]]
    monkeypatch.setattr("requests.get", lambda *a, **k: Response(binance_payload))
    assert BinanceProvider().history("BTCUSDT", limit=1).iloc[0]["Trades"] == 4

    fred_payload = {"observations": [{"date": "2024-01-01", "value": "3.5"}]}
    monkeypatch.setattr("requests.get", lambda *a, **k: Response(fred_payload))
    assert FREDProvider("key").history("DGS10").iloc[0]["Value"] == 3.5


def test_polling_feed_one_update(monkeypatch):
    class Provider:
        def quote(self, symbol, **kwargs):
            return pd.Series({"Close": 100.0}, name=pd.Timestamp("2024-01-01"))
    quote = next(PollingFeed(Provider(), "X", interval_seconds=0).stream(max_updates=1))
    assert quote["Close"] == 100
    assert "received_at" in quote.attrs


def test_fixed_income_and_volatility_extensions():
    from asrquant.fixed_income import bond_price, convexity, macaulay_duration, yield_to_maturity, bootstrap_zero_curve
    from asrquant.volatility import ewma_volatility, parkinson_volatility, realized_volatility
    price = bond_price(100, 0.05, 5, 0.04, 2)
    ytm = yield_to_maturity(price, 100, 0.05, 5, 2)
    assert abs(ytm - 0.04) < 1e-8
    assert macaulay_duration(100, 0.05, 5, 0.04, 2) > 0
    assert convexity(100, 0.05, 5, 0.04, 2) > 0
    curve = bootstrap_zero_curve(pd.DataFrame({"maturity": [1,2,3], "par_rate": [0.03,0.035,0.04]}))
    assert len(curve) == 3
    returns = _prices(100)["A"].pct_change()
    assert realized_volatility(returns).dropna().gt(0).all()
    assert ewma_volatility(returns.fillna(0)).dropna().ge(0).all()
    high = _prices(100)["A"]*1.01; low = _prices(100)["A"]*0.99
    assert parkinson_volatility(high, low).dropna().gt(0).all()


def test_parameter_sweep_and_new_strategies():
    lab = QuantLab(_prices(250))
    sweep = lab.sweep("sma", {"fast": [5, 10], "slow": [30, 60]}, costs_bps=1)
    assert len(sweep) == 4 and "Sharpe" in sweep
    for name in ["breakout", "bollinger", "rsi", "pairs"]:
        kwargs = {"lookback": 30, "exit_lookback": 10} if name == "breakout" else {}
        result = lab.backtest(name, **kwargs)
        assert len(result.net_returns) == len(lab.prices)


def test_cli_version_simulate_and_price(tmp_path, capsys):
    from asrquant.cli import main

    output = tmp_path / "paths.csv"
    assert main([
        "simulate", "--model", "gbm", "--paths", "100", "--steps", "5",
        "--output", str(output),
    ]) == 0
    assert output.exists()
    assert main([
        "price", "--model", "black_scholes", "--spot", "100", "--strike", "100",
        "--maturity", "1", "--rate", "0.03", "--volatility", "0.2",
    ]) == 0
    text = capsys.readouterr().out
    assert "price" in text
