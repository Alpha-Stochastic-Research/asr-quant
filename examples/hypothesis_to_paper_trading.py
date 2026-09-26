"""Synthetic full workflow from a stated hypothesis to paper trading."""
import asrquant as asr

rng = asr.math.random_generator(11)
index = asr.date_range("2020-01-01", periods=600, freq="B")
yield_changes = rng.normal(0, 0.04, len(index))
us10y = 2.0 + yield_changes.cumsum()
regime = asr.series(yield_changes, index=index).rolling(20).sum().fillna(0.0)
value_returns = 0.0003 + 0.0015 * (regime > 0.15) + rng.normal(0, 0.006, len(index))
growth_returns = 0.0003 - 0.0012 * (regime > 0.15) + rng.normal(0, 0.006, len(index))
value = 100 * (1 + value_returns).cumprod()
growth = 100 * (1 + growth_returns).cumprod()
data = asr.frame({"US10Y": us10y, "VALUE": value, "GROWTH": growth}, index=index)

project = asr.research.from_hypothesis(
    "Rapid increases in US 10-year yields predict value outperformance relative to growth.",
    predictor="US10Y",
    target="VALUE minus GROWTH",
    expected_sign="positive",
    horizon=20,
    mechanism="Growth cash flows have higher effective duration and are more rate-sensitive.",
)
project.attach_data(data, tradable_assets=["VALUE", "GROWTH"])
project.build_features(asr.FeaturePlan([
    asr.FeatureSpec("yield_change_20", "US10Y", "diff", params={"periods": 20}, availability_lag=1),
    asr.FeatureSpec("yield_z252", "US10Y", "zscore", window=252, availability_lag=1),
]))
project.build_signal(asr.SignalSpec(
    "yield_change_20",
    long_asset="VALUE",
    short_asset="GROWTH",
    upper=0.15,
    lower=-0.15,
))
project.test_hypothesis(horizon=20)
project.construct_portfolio(asr.PortfolioSpec(max_abs_weight=0.5))
project.backtest(costs_bps=2, execution_delay=1)
project.robustness(n_boot=500)
print(project.decide().summary)
print(project.paper_trade(commission_bps=1, slippage_bps=1).summary)
project.report("hypothesis_to_decision.html")
project.save_manifest("hypothesis_to_decision.json")
