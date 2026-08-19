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

# ---------------------------------------------------------------------------
# ASRQuant 1.2 canonical data facade
# ---------------------------------------------------------------------------

def validate(data: pd.Series | pd.DataFrame):
    """Return non-mutating structural diagnostics for a time-series panel.

    This canonical helper records data-quality issues instead of silently fixing
    them. Use :func:`clean_prices` when an explicit cleaning policy is desired.
    """
    from .contracts import DataQualityResult, DataValidationError

    if isinstance(data, pd.Series):
        frame = data.to_frame(data.name or "value")
    elif isinstance(data, pd.DataFrame):
        frame = data.copy()
    else:
        raise DataValidationError("data must be a pandas Series or DataFrame")
    if frame.empty:
        raise DataValidationError("data is empty")

    issues: list[str] = []
    duplicate_timestamps = int(frame.index.duplicated().sum())
    if duplicate_timestamps:
        issues.append(f"duplicate timestamps: {duplicate_timestamps}")

    converted = False
    if not isinstance(frame.index, pd.DatetimeIndex):
        try:
            frame.index = pd.to_datetime(frame.index)
            converted = True
        except Exception as exc:
            raise DataValidationError("index must be convertible to DatetimeIndex") from exc

    monotonic = bool(frame.index.is_monotonic_increasing)
    if not monotonic:
        issues.append("index is not monotonic increasing")

    numeric = frame.apply(pd.to_numeric, errors="coerce")
    newly_missing = int((numeric.isna() & ~frame.isna()).sum().sum())
    if newly_missing:
        issues.append(f"non-numeric values coerced to missing: {newly_missing}")
    values = numeric.to_numpy(dtype=float)
    infinite = int(np.isinf(values).sum())
    if infinite:
        issues.append(f"infinite values: {infinite}")
    missing = int(numeric.isna().sum().sum())
    if missing:
        issues.append(f"missing values: {missing}")
    constant = int((numeric.nunique(dropna=True) <= 1).sum())
    if constant:
        issues.append(f"constant columns: {constant}")

    ordered = pd.DatetimeIndex(frame.index).sort_values()
    deltas = ordered.to_series(index=ordered).diff().dropna()
    metrics = pd.Series(
        {
            "rows": int(len(frame)),
            "columns": int(frame.shape[1]),
            "start": frame.index.min(),
            "end": frame.index.max(),
            "missing_values": missing,
            "missing_fraction": float(numeric.isna().mean().mean()),
            "duplicate_timestamps": duplicate_timestamps,
            "monotonic_index": monotonic,
            "median_spacing": deltas.median() if len(deltas) else pd.NaT,
            "maximum_gap": deltas.max() if len(deltas) else pd.NaT,
            "constant_columns": constant,
            "infinite_values": infinite,
            "non_numeric_values": newly_missing,
        },
        name="value",
    )
    return DataQualityResult(
        metrics=metrics,
        issues=tuple(issues),
        metadata={"index_converted_to_datetime": converted},
    )


def _read_remote_table(
    url: str,
    *,
    date_column: str | None = None,
    columns: Sequence[str] | None = None,
    format: str | None = None,
    sheet_name: str | int = 0,
    timeout: float = 30.0,
    **read_kwargs,
) -> pd.DataFrame:
    """Read a public HTTP(S) table using an explicit, bounded network request."""
    from io import BytesIO, StringIO
    import requests
    from .contracts import ProviderError, DataValidationError

    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ProviderError(f"data URL request failed: {exc}") from exc

    key = (format or Path(url.split("?", 1)[0]).suffix.lstrip(".")).lower()
    content_type = response.headers.get("content-type", "").lower()
    try:
        if key in {"csv", "txt", ""} or "text/csv" in content_type:
            table = pd.read_csv(StringIO(response.text), **read_kwargs)
        elif key in {"json"} or "application/json" in content_type:
            table = pd.read_json(StringIO(response.text), **read_kwargs)
        elif key in {"xlsx", "xls"}:
            table = pd.read_excel(BytesIO(response.content), sheet_name=sheet_name, **read_kwargs)
        elif key in {"parquet", "pq"}:
            table = pd.read_parquet(BytesIO(response.content), **read_kwargs)
        elif key in {"feather", "ft"}:
            table = pd.read_feather(BytesIO(response.content), **read_kwargs)
        else:
            raise DataValidationError(f"unsupported remote table format {key!r}")
    except Exception as exc:
        if isinstance(exc, DataValidationError):
            raise
        raise DataValidationError(f"could not parse remote data from {url!r}: {exc}") from exc

    if table.empty:
        raise DataValidationError("remote data table is empty")
    date_column = date_column or str(table.columns[0])
    if date_column not in table.columns:
        raise DataValidationError(f"date column {date_column!r} not found")
    table[date_column] = pd.to_datetime(table[date_column], errors="raise")
    frame = table.set_index(date_column)
    if columns is not None:
        missing = sorted(set(columns) - set(frame.columns))
        if missing:
            raise DataValidationError(f"columns not found: {missing}")
        frame = frame[list(columns)]
    return as_frame(frame)


def from_provider(
    provider: str,
    symbols: str | Sequence[str] | None = None,
    *,
    field: str = "Close",
    provider_kwargs: dict | None = None,
    **history_kwargs,
) -> pd.DataFrame:
    """Load one or more series from an ASRQuant market-data provider.

    Providers include ``yahoo``, ``ecb``, ``fred``, ``alpha_vantage`` and
    ``binance``. For ECB yield curves use :func:`ecb_yield_curve` for a cleaner
    maturity-based interface.
    """
    from .providers import download, get_provider
    from .contracts import ProviderError

    if symbols is None:
        raise ValueError("symbols is required for generic provider downloads")
    try:
        source = get_provider(provider, **(provider_kwargs or {}))
        return download(source, symbols, field=field, **history_kwargs)
    except Exception as exc:
        if isinstance(exc, (ValueError, TypeError, KeyError, ImportError)):
            raise
        raise ProviderError(str(exc)) from exc


def yahoo(
    symbols: str | Sequence[str],
    *,
    start: str | None = None,
    end: str | None = None,
    period: str = "max",
    interval: str = "1d",
    field: str = "Close",
    auto_adjust: bool = True,
) -> pd.DataFrame:
    """Download Yahoo Finance data through the optional ``yfinance`` backend."""
    return from_provider(
        "yahoo",
        symbols,
        field=field,
        provider_kwargs={"auto_adjust": auto_adjust},
        start=start,
        end=end,
        period=period,
        interval=interval,
    )


def ecb_yield_curve(
    maturities: Sequence[str] = ("3M", "6M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "15Y", "20Y", "30Y"),
    *,
    start: str | None = None,
    end: str | None = None,
    data_type: str = "SR",
    last_n: int | None = None,
    provider_kwargs: dict | None = None,
) -> pd.DataFrame:
    """Download aligned ECB euro-area AAA Svensson curve history.

    The returned values are decimal annual rates. Network access is explicit and
    the ECB provider metadata are retained in ``DataFrame.attrs``.
    """
    from .providers import ECBProvider
    provider = ECBProvider(**(provider_kwargs or {}))
    return provider.yield_curve_history(
        maturities=maturities,
        start=start,
        end=end,
        data_type=data_type,
        last_n=last_n,
    )


def load(
    source,
    date_column: str | None = None,
    *,
    columns: Sequence[str] | None = None,
    provider: str | None = None,
    symbols: str | Sequence[str] | None = None,
    field: str = "Close",
    provider_kwargs: dict | None = None,
    format: str | None = None,
    sheet_name: str | int = 0,
    timeout: float = 30.0,
    **kwargs,
) -> pd.DataFrame:
    """Canonical data loader for pandas objects, files, URLs, and providers.

    Examples
    --------
    ``asr.data.load("prices.csv", date_column="Date")``

    ``asr.data.load("https://example.org/data.csv", date_column="DATE")``

    ``asr.data.load("yahoo", symbols=["SPY", "TLT"], start="2020-01-01")``

    ``asr.data.ecb_yield_curve(start="2024-01-01")``
    """
    if isinstance(source, (pd.Series, pd.DataFrame)):
        frame = as_frame(source)
        if columns is not None:
            missing = sorted(set(columns) - set(frame.columns))
            if missing:
                raise ValueError(f"columns not found: {missing}")
            frame = frame[list(columns)]
        return frame

    source_text = str(source)
    provider_name = provider
    known_providers = {"yahoo", "yfinance", "ecb", "fred", "alpha_vantage", "alphavantage", "binance"}
    if provider_name is None and source_text.lower().replace("-", "_") in known_providers:
        provider_name = source_text
    if provider_name is not None:
        if provider_name.lower().replace("-", "_") in {"ecb", "european_central_bank"} and symbols is None:
            maturities = kwargs.pop("maturities", ("3M", "6M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "15Y", "20Y", "30Y"))
            return ecb_yield_curve(
                maturities=maturities,
                provider_kwargs=provider_kwargs,
                **kwargs,
            )
        return from_provider(
            provider_name,
            symbols,
            field=field,
            provider_kwargs=provider_kwargs,
            **kwargs,
        )

    if source_text.startswith(("http://", "https://")):
        return _read_remote_table(
            source_text,
            date_column=date_column,
            columns=columns,
            format=format,
            sheet_name=sheet_name,
            timeout=timeout,
            **kwargs,
        )
    return load_prices(
        source_text,
        date_column=date_column,
        columns=columns,
        sheet_name=sheet_name,
    )
