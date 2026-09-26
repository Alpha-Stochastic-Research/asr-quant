import matplotlib
matplotlib.use("Agg")

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def prices():
    rng = np.random.default_rng(42)
    idx = pd.bdate_range("2022-01-03", periods=320)
    rets = rng.normal(0.0003, 0.01, size=(320, 3))
    return pd.DataFrame(100 * np.exp(np.cumsum(rets, axis=0)), index=idx, columns=["A", "B", "C"])


@pytest.fixture
def returns(prices):
    return prices.pct_change(fill_method=None).fillna(0.0)

@pytest.fixture(autouse=True)
def _close_all_figures_after_test():
    """Prevent visualization-state accumulation across the complete suite."""
    yield
    import gc
    import matplotlib.pyplot as plt
    plt.close("all")
    gc.collect()
