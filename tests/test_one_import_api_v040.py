from pathlib import Path

import numpy as np
import pandas as pd

import asrquant as asr


def _lab(n: int = 420):
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    rng = np.random.default_rng(7)
    returns = rng.normal(0.0003, 0.01, size=n)
    prices = 100 * np.exp(np.cumsum(returns))
    return asr.open_lab(asr.frame({"SPY": prices}, index=idx))


def test_one_import_namespaces_and_version():
    assert asr.__version__ == "1.0.0"
    assert asr.math.linspace(0, 1, 3).tolist() == [0.0, 0.5, 1.0]
    assert asr.math.normal_cdf(0.0) == 0.5
    assert asr.models.ridge(alpha=2.0).__class__.__name__ == "Ridge"
    assert asr.create_model("random_forest", task="classification", trees=10).__class__.__name__ == "RandomForestClassifier"


def test_end_to_end_ml_by_name():
    lab = _lab()
    result = lab.ml(
        "ridge",
        train_size=252,
        test_size=42,
        gap=1,
        model_params={"alpha": 1.0},
    )
    assert result.estimator_name == "Ridge"
    assert "rmse" in result.aggregate_metrics.index
    assert len(result.predictions) > 0


def test_backend_neutral_visual_save(tmp_path: Path):
    lab = _lab(120)
    result = lab.backtest("sma", fast=5, slow=20, costs_bps=1)
    output = tmp_path / "equity.png"
    saved = asr.save(result, output, kind="equity")
    assert saved == output
    assert output.exists() and output.stat().st_size > 0


def test_general_table_helpers(tmp_path: Path):
    table = asr.frame({"x": [1, 2], "y": [3, 4]})
    path = tmp_path / "table.csv"
    table.to_csv(path, index=False)
    loaded = asr.read_table(path)
    assert loaded.to_dict("list") == {"x": [1, 2], "y": [3, 4]}
