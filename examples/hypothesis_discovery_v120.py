"""ASRQuant 1.2.0 — data + literature hypothesis discovery example."""
import numpy as np
import pandas as pd
import asrquant as asr

rng = np.random.default_rng(12)
index = pd.date_range("2020-01-01", periods=700, freq="B")
rate_change = rng.normal(0.0, 0.04, len(index))
style_return = np.r_[0.0, 0.25 * rate_change[:-1]] + rng.normal(0.0, 0.01, len(index))
research_panel = pd.DataFrame(
    {"rate_change": rate_change, "value_minus_growth": style_return},
    index=index,
)

papers = [
    (
        "Rates and styles",
        "Future research should test whether changes in interest rates are associated with subsequent differences between value and growth returns.",
    )
]

ideas = asr.hypotheses.discover(
    data=research_panel,
    papers=papers,
    domain="quantitative_finance",
    targets="value_minus_growth",
    horizons=(1,),
    lags=(0,),
    transforms={"rate_change": "raw", "value_minus_growth": "raw"},
    min_observations=120,
)

print(ideas.to_frame().head())
project = ideas.start(0)
print(project.hypothesis.statement)
