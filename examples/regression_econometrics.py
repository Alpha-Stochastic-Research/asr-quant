"""One-import robust regression from a local multi-asset CSV panel."""
from pathlib import Path

import asrquant as asr

DATA = Path(__file__).with_name("sample_prices.csv")
OUTPUT = Path(__file__).with_name("regression_residuals.png")
lab = asr.open_lab(DATA, date_column="Date")
fit = lab.regress(
    y="Asset_1",
    x=["Asset_2", "Asset_3", "Asset_4"],
    method="ols",
    covariance="HAC",
    maxlags=5,
)
print(fit.coefficients)
print(fit.confidence_intervals)
print(fit.diagnostics)
asr.save(fit, OUTPUT, kind="residuals", dpi=150)
