import numpy as np
import pandas as pd
import pytest

from asrquant import alpha


def panel(rows=40, assets=10, seed=7):
    rng = np.random.default_rng(seed)
    index = pd.date_range("2024-01-01", periods=rows, freq="B")
    columns = [f"A{i}" for i in range(assets)]
    values = rng.normal(size=(rows, assets))
    return pd.DataFrame(values, index=index, columns=columns)


def test_cross_sectional_zscore_is_row_centered():
    signal = panel()
    z = alpha.cross_sectional_zscore(signal)
    assert np.allclose(z.mean(axis=1), 0.0, atol=1e-12)
    assert np.allclose(z.std(axis=1, ddof=0), 1.0, atol=1e-12)


def test_winsorize_caps_cross_sectional_outlier():
    signal = panel(rows=4, assets=20)
    signal.iloc[0, 0] = 1e6
    out = alpha.winsorize_cross_section(signal, 0.05, 0.95)
    assert out.iloc[0, 0] < 1e6
    assert out.shape == signal.shape


def test_forward_returns_exact_and_future_aligned():
    prices = pd.DataFrame({"A": [100.0, 101.0, 103.02, 106.1106]})
    fwd = alpha.forward_returns(prices, periods=(1, 2))
    assert fwd[1].iloc[0, 0] == pytest.approx(0.01)
    assert fwd[2].iloc[0, 0] == pytest.approx(0.0302)
    assert np.isnan(fwd[2].iloc[-1, 0])


def test_information_coefficient_recovers_monotone_signal():
    signal = panel(rows=30, assets=12)
    future = signal * 0.02
    ic = alpha.information_coefficient(signal, future, min_assets=5)
    assert (ic.dropna() > 0.999999).all()


def test_neutralization_removes_linear_exposure():
    exposure = panel(rows=25, assets=15)
    rng = np.random.default_rng(2)
    noise = pd.DataFrame(rng.normal(scale=0.01, size=exposure.shape), index=exposure.index, columns=exposure.columns)
    signal = 3.0 * exposure + noise
    residual = alpha.neutralize_cross_section(signal, {"beta": exposure}, min_assets=10)
    correlations = []
    for t in exposure.index:
        pair = pd.concat([residual.loc[t], exposure.loc[t]], axis=1).dropna()
        correlations.append(pair.iloc[:, 0].corr(pair.iloc[:, 1]))
    assert np.nanmax(np.abs(correlations)) < 1e-10


def test_quantile_returns_and_long_short_are_ordered():
    signal = panel(rows=20, assets=20)
    future = signal * 0.01
    qret = alpha.quantile_portfolio_returns(signal, future, quantiles=5, min_assets=20)
    spread = alpha.long_short_return(qret)
    assert (spread.dropna() > 0).all()
    assert qret.columns.tolist() == ["Q1", "Q2", "Q3", "Q4", "Q5"]


def test_signal_weights_have_requested_gross_and_zero_net():
    signal = panel(rows=12, assets=9)
    weights = alpha.signal_to_weights(signal, gross=1.5, dollar_neutral=True)
    assert np.allclose(weights.abs().sum(axis=1), 1.5, atol=1e-12)
    assert np.allclose(weights.sum(axis=1), 0.0, atol=1e-12)


def test_alpha_research_report_end_to_end():
    signal = panel(rows=60, assets=15)
    rng = np.random.default_rng(5)
    future = 0.015 * signal + pd.DataFrame(
        rng.normal(scale=0.002, size=signal.shape),
        index=signal.index,
        columns=signal.columns,
    )
    report = alpha.analyze_signal(signal, future, quantiles=5, min_assets=10)
    assert report.summary["mean_ic"] > 0.9
    assert report.summary["mean_long_short_return"] > 0
    assert report.turnover.ge(0).all()

def test_rank_center_and_zero_dispersion_zscore():
    signal = pd.DataFrame([[2.0, 2.0, 2.0], [1.0, 2.0, 3.0]], columns=list("ABC"))
    z = alpha.cross_sectional_zscore(signal)
    assert z.iloc[0].tolist() == [0.0, 0.0, 0.0]
    ranked = alpha.cross_sectional_rank(signal, pct=True, center=True)
    assert abs(ranked.iloc[1].mean()) < 1e-12


def test_forward_log_returns_and_ic_decay():
    prices = 100 * np.exp(panel(rows=50, assets=8, seed=9).cumsum() * 0.001)
    signal = alpha.forward_returns(prices, 1, log=True)[1]
    decay = alpha.ic_decay(signal, prices, horizons=(1, 2), min_assets=5)
    assert decay.index.tolist() == [1, 2]
    assert {"mean_ic", "ic_ir", "t_stat", "positive_rate", "observations"}.issubset(decay.columns)


def test_weight_turnover_and_weight_cap():
    signal = panel(rows=10, assets=20)
    weights = alpha.signal_to_weights(signal, gross=1.0, max_abs_weight=0.15)
    assert weights.abs().to_numpy().max() <= 0.1500000001
    turnover = alpha.weight_turnover(weights)
    assert turnover.iloc[0] == 0.0
    assert (turnover >= 0).all()


def test_alpha_input_validation():
    signal = panel(rows=5, assets=5)
    with pytest.raises(ValueError):
        alpha.winsorize_cross_section(signal, 0.9, 0.1)
    with pytest.raises(ValueError):
        alpha.cross_sectional_zscore(signal, ddof=-1)
    with pytest.raises(ValueError):
        alpha.cross_sectional_zscore(signal, clip=0)
    with pytest.raises(ValueError):
        alpha.forward_returns(signal.abs() + 1, periods=0)
    with pytest.raises(ValueError):
        alpha.information_coefficient(signal, signal, method="kendall")
    with pytest.raises(ValueError):
        alpha.quantile_portfolio_returns(signal, signal, quantiles=1)
    with pytest.raises(ValueError):
        alpha.signal_to_weights(signal, gross=0)
    with pytest.raises(ValueError):
        alpha.neutralize_cross_section(signal, {})
