"""One-import leakage-aware walk-forward machine-learning regression."""
from pathlib import Path

import asrquant as asr

DATA = Path(__file__).with_name("sample_prices.csv")
OUTPUT = Path(__file__).with_name("ml_walk_forward.png")

lab = asr.open_lab(DATA, date_column="Date")
features = lab.ml_features("Asset_1", windows=(5, 20, 63)).shift(1)
target = asr.forward_target(lab.prices["Asset_1"], horizon=5)
result = lab.ml_walk_forward(
    "ridge",
    features,
    target,
    train_size=126,
    test_size=42,
    step=42,
    gap=5,
    model_params={"alpha": 1.0},
)
print(result.fold_metrics)
print(result.aggregate_metrics)
asr.save(result, OUTPUT, kind="predictions", dpi=150)
