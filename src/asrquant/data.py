"""Market-data normalization, validation, and hashing."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

from .config import MissingDataPolicy


def as_frame(data: pd.Series | pd.DataFrame, name: str = "asset") -> pd.DataFrame:
    """Return a float DataFrame with a unique, sorted DatetimeIndex."""
    if isinstance(data, pd.Series):
        frame = data.to_frame(data.name or name)
    elif isinstance(data, pd.DataFrame):
        frame = data.copy()
    else:
        raise TypeError("data must be a pandas Series or DataFrame")
    if frame.empty:
        raise ValueError("data is empty")
    if not isinstance(frame.index, pd.DatetimeIndex):
        try:
            frame.index = pd.to_datetime(frame.index)
        except Exception as exc:  # pragma: no cover - pandas provides details
            raise TypeError("index must be convertible to DatetimeIndex") from exc
    if frame.index.has_duplicates:
        raise ValueError("index contains duplicate timestamps")
    frame = frame.sort_index()
    frame = frame.apply(pd.to_numeric, errors="coerce").astype(float)
    if not np.isfinite(frame.to_numpy()[~np.isnan(frame.to_numpy())]).all():
        raise ValueError("data contains infinite values")
    return frame


def clean_prices(
    prices: pd.Series | pd.DataFrame,
    policy: MissingDataPolicy | str = MissingDataPolicy.RAISE,
) -> pd.DataFrame:
    """Validate positive prices and apply the selected missing-data policy."""
    frame = as_frame(prices, "price")
    selected = MissingDataPolicy(policy)
    if selected == MissingDataPolicy.RAISE and frame.isna().any().any():
        missing = int(frame.isna().sum().sum())
        raise ValueError(f"prices contain {missing} missing observations")
    if selected == MissingDataPolicy.DROP:
        frame = frame.dropna(how="any")
    elif selected == MissingDataPolicy.FFILL:
        frame = frame.ffill().dropna(how="any")
    if (frame <= 0).any().any():
        raise ValueError("prices must be strictly positive")
    if len(frame) < 2:
        raise ValueError("at least two observations are required")
    return frame


def align_like(
    values: pd.Series | pd.DataFrame,
    reference: pd.DataFrame,
    fill_value: float = 0.0,
) -> pd.DataFrame:
    """Align a Series/DataFrame to a price panel's index and columns."""
    frame = as_frame(values, "weight")
    if frame.shape[1] == 1 and reference.shape[1] > 1:
        raise ValueError("single-column values cannot be broadcast across multiple assets")
    unknown = frame.columns.difference(reference.columns)
    if len(unknown):
        raise ValueError(f"unknown assets: {list(unknown)}")
    frame = frame.reindex(index=reference.index, columns=reference.columns)
    return frame.fillna(fill_value).astype(float)


def simple_returns(prices: pd.Series | pd.DataFrame) -> pd.DataFrame:
    """Compute simple returns with no implicit forward fill."""
    frame = as_frame(prices, "price")
    return frame.pct_change(fill_method=None).fillna(0.0)


def log_returns(prices: pd.Series | pd.DataFrame) -> pd.DataFrame:
    """Compute log returns."""
    frame = as_frame(prices, "price")
    return np.log(frame).diff().fillna(0.0)


def data_fingerprint(data: pd.Series | pd.DataFrame) -> str:
    """Create a stable SHA-256 fingerprint of values, index, and columns."""
    frame = as_frame(data)
    payload = pd.util.hash_pandas_object(frame, index=True).to_numpy().tobytes()
    payload += "|".join(map(str, frame.columns)).encode("utf-8")
    return sha256(payload).hexdigest()


def load_prices(
    path: str | Path,
    date_column: str | None = None,
    *,
    columns: Sequence[str] | None = None,
    sheet_name: str | int = 0,
) -> pd.DataFrame:
    """Load price/value panels from CSV, Parquet, Excel, JSON, or Feather.

    The first column is used as the date column unless ``date_column`` is
    supplied. Use ``columns`` to select price columns after parsing.
    """
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".csv", ".txt"}:
        data = pd.read_csv(path)
    elif suffix in {".parquet", ".pq"}:
        data = pd.read_parquet(path)
    elif suffix in {".xlsx", ".xls"}:
        data = pd.read_excel(path, sheet_name=sheet_name)
    elif suffix == ".json":
        data = pd.read_json(path)
    elif suffix in {".feather", ".ft"}:
        data = pd.read_feather(path)
    else:
        raise ValueError("supported formats are CSV, Parquet, Excel, JSON, and Feather")
    date_column = date_column or str(data.columns[0])
    if date_column not in data.columns:
        raise ValueError(f"date column {date_column!r} not found")
    data[date_column] = pd.to_datetime(data[date_column])
    frame = data.set_index(date_column)
    if columns is not None:
        missing = set(columns).difference(frame.columns)
        if missing:
            raise ValueError(f"columns not found: {sorted(missing)}")
        frame = frame[list(columns)]
    return as_frame(frame)


def load_sql(query: str, connection, date_column: str, columns: Sequence[str] | None = None) -> pd.DataFrame:
    """Load a price/value panel from any pandas-compatible SQL connection."""
    data = pd.read_sql_query(query, connection)
    if date_column not in data.columns:
        raise ValueError(f"date column {date_column!r} not found")
    data[date_column] = pd.to_datetime(data[date_column])
    frame = data.set_index(date_column)
    if columns is not None:
        frame = frame[list(columns)]
    return as_frame(frame)


def data_quality_report(data: pd.Series | pd.DataFrame) -> pd.Series:
    """Summarize missingness, duplicates, monotonicity, and sampling gaps."""
    frame = as_frame(data)
    deltas = frame.index.to_series().diff().dropna()
    return pd.Series({
        "rows": len(frame),
        "columns": frame.shape[1],
        "start": frame.index.min(),
        "end": frame.index.max(),
        "missing_values": int(frame.isna().sum().sum()),
        "missing_fraction": float(frame.isna().mean().mean()),
        "duplicate_timestamps": int(frame.index.duplicated().sum()),
        "monotonic_index": bool(frame.index.is_monotonic_increasing),
        "median_spacing": deltas.median() if len(deltas) else pd.NaT,
        "maximum_gap": deltas.max() if len(deltas) else pd.NaT,
        "constant_columns": int((frame.nunique(dropna=True) <= 1).sum()),
    })


def resample_ohlcv(data: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Resample canonical OHLCV data with finance-consistent aggregations."""
    frame = validate_ohlcv(data)
    aggregations = {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
    if "Volume" in frame.columns:
        aggregations["Volume"] = "sum"
    for column in frame.columns:
        if column not in aggregations:
            aggregations[column] = "last"
    return frame.resample(rule).agg(aggregations).dropna(subset=["Open", "High", "Low", "Close"])


def validate_ohlcv(data: pd.DataFrame) -> pd.DataFrame:
    """Validate a canonical OHLCV table."""
    required = ["Open", "High", "Low", "Close"]
    missing = [c for c in required if c not in data.columns]
    if missing:
        raise ValueError(f"missing OHLC columns: {missing}")
    out = as_frame(data)
    if (out[required] <= 0).any().any():
        raise ValueError("OHLC prices must be positive")
    if (out["High"] < out[["Open", "Close", "Low"]].max(axis=1)).any():
        raise ValueError("High is inconsistent with Open/Close/Low")
    if (out["Low"] > out[["Open", "Close", "High"]].min(axis=1)).any():
        raise ValueError("Low is inconsistent with Open/Close/High")
    if "Volume" in out and (out["Volume"] < 0).any():
        raise ValueError("Volume must be non-negative")
    return out
