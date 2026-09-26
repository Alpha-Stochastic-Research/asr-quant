"""One-import robust regression diagnostics."""
import asrquant as asr

returns = asr.regime_switching_prices(periods=800, assets=3).pct_change().dropna()
fit = asr.stats.ols(returns["Asset_1"], returns[["Asset_2", "Asset_3"]], covariance="HAC")
print(fit.coefficients)
print(fit.diagnostics)
asr.PlotHandle(asr.visuals.regression.residual_diagnostics(fit)).save("residual_diagnostics.png", dpi=150)
asr.PlotHandle(asr.visuals.regression.coefficient_intervals(fit)).save("coefficient_intervals.png", dpi=150)
