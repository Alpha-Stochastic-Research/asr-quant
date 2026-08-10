"""Provider-neutral historical and near-real-time market-data connectors.

Network access is always explicit. Providers return canonical pandas objects and
never silently place orders. API keys may be passed directly or through the
provider-specific environment variable.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
import os
import time
from typing import Iterator, Sequence

import pandas as pd
import requests


class DataProviderError(RuntimeError):
    """Raised when a remote provider returns an invalid or failed response."""


class MarketDataProvider(ABC):
    """Minimal interface implemented by all market-data providers."""

    @abstractmethod
    def history(self, symbol: str, **kwargs) -> pd.DataFrame:
        """Return a canonical OHLCV or value table indexed by timestamp."""

    def quote(self, symbol: str, **kwargs) -> pd.Series:
        """Return the latest observation using the provider's history endpoint."""
        data = self.history(symbol, **kwargs)
        if data.empty:
            raise DataProviderError(f"no observations returned for {symbol}")
        row = data.iloc[-1].copy()
        row.name = data.index[-1]
        return row


def _get_json(url: str, params: dict | None = None, timeout: float = 20.0) -> dict | list:
    response = requests.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict):
        message = payload.get("Error Message") or payload.get("Information") or payload.get("Note")
        if message:
            raise DataProviderError(str(message))
    return payload


@dataclass
class AlphaVantageProvider(MarketDataProvider):
    """Alpha Vantage equities/FX/crypto connector.

    The free service is rate-limited by the provider. The connector deliberately
    does not retry aggressively because doing so can worsen throttling.
    """

    api_key: str | None = None
    timeout: float = 20.0

    def _key(self) -> str:
        key = self.api_key or os.getenv("ALPHAVANTAGE_API_KEY")
        if not key:
            raise DataProviderError("Alpha Vantage API key is required")
        return key

    def history(
        self,
        symbol: str,
        *,
        interval: str = "daily",
        adjusted: bool = True,
        outputsize: str = "compact",
    ) -> pd.DataFrame:
        interval_l = interval.lower()
        params: dict[str, str] = {"symbol": symbol, "apikey": self._key(), "outputsize": outputsize}
        if interval_l in {"daily", "1d"}:
            params["function"] = "TIME_SERIES_DAILY_ADJUSTED" if adjusted else "TIME_SERIES_DAILY"
            key_prefix = "Time Series (Daily)"
        elif interval_l in {"weekly", "1wk"}:
            params["function"] = "TIME_SERIES_WEEKLY_ADJUSTED" if adjusted else "TIME_SERIES_WEEKLY"
            key_prefix = "Weekly Adjusted Time Series" if adjusted else "Weekly Time Series"
        elif interval_l in {"monthly", "1mo"}:
            params["function"] = "TIME_SERIES_MONTHLY_ADJUSTED" if adjusted else "TIME_SERIES_MONTHLY"
            key_prefix = "Monthly Adjusted Time Series" if adjusted else "Monthly Time Series"
        else:
            params.update({"function": "TIME_SERIES_INTRADAY", "interval": interval})
            key_prefix = f"Time Series ({interval})"
        payload = _get_json("https://www.alphavantage.co/query", params=params, timeout=self.timeout)
        if not isinstance(payload, dict) or key_prefix not in payload:
            raise DataProviderError(f"unexpected Alpha Vantage response keys: {list(payload) if isinstance(payload, dict) else type(payload)}")
        frame = pd.DataFrame.from_dict(payload[key_prefix], orient="index")
        rename = {
            "1. open": "Open", "2. high": "High", "3. low": "Low", "4. close": "Close",
            "5. adjusted close": "Adjusted Close", "5. volume": "Volume", "6. volume": "Volume",
        }
        frame = frame.rename(columns=rename)
        frame.index = pd.to_datetime(frame.index, utc=True)
        frame = frame.apply(pd.to_numeric, errors="coerce").sort_index()
        return frame


@dataclass
class BinanceProvider(MarketDataProvider):
    """Public Binance Spot market-data connector; no credentials are required."""

    base_url: str = "https://data-api.binance.vision"
    timeout: float = 20.0

    def history(
        self,
        symbol: str,
        *,
        interval: str = "1d",
        limit: int = 500,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> pd.DataFrame:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        params: dict[str, str | int] = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time
        payload = _get_json(f"{self.base_url}/api/v3/klines", params=params, timeout=self.timeout)
        if not isinstance(payload, list):
            raise DataProviderError("unexpected Binance response")
        columns = [
            "Open time", "Open", "High", "Low", "Close", "Volume", "Close time",
            "Quote volume", "Trades", "Taker base volume", "Taker quote volume", "Ignore",
        ]
        frame = pd.DataFrame(payload, columns=columns)
        frame.index = pd.to_datetime(frame.pop("Open time"), unit="ms", utc=True)
        for column in ["Open", "High", "Low", "Close", "Volume", "Quote volume", "Taker base volume", "Taker quote volume"]:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        frame["Trades"] = pd.to_numeric(frame["Trades"], errors="coerce").astype("Int64")
        return frame.drop(columns=["Close time", "Ignore"])


@dataclass
class FREDProvider(MarketDataProvider):
    """Federal Reserve Bank of St. Louis FRED series connector."""

    api_key: str | None = None
    timeout: float = 20.0

    def _key(self) -> str:
        key = self.api_key or os.getenv("FRED_API_KEY")
        if not key:
            raise DataProviderError("FRED API key is required")
        return key

    def history(
        self,
        symbol: str,
        *,
        observation_start: str | None = None,
        observation_end: str | None = None,
        frequency: str | None = None,
    ) -> pd.DataFrame:
        params: dict[str, str] = {
            "series_id": symbol,
            "api_key": self._key(),
            "file_type": "json",
        }
        if observation_start:
            params["observation_start"] = observation_start
        if observation_end:
            params["observation_end"] = observation_end
        if frequency:
            params["frequency"] = frequency
        payload = _get_json(
            "https://api.stlouisfed.org/fred/series/observations",
            params=params,
            timeout=self.timeout,
        )
        if not isinstance(payload, dict) or "observations" not in payload:
            raise DataProviderError("unexpected FRED response")
        frame = pd.DataFrame(payload["observations"])
        frame.index = pd.to_datetime(frame.pop("date"), utc=True)
        frame["Value"] = pd.to_numeric(frame["value"], errors="coerce")
        return frame[["Value"]]


@dataclass
class YahooProvider(MarketDataProvider):
    """Optional yfinance connector for convenient research downloads."""

    auto_adjust: bool = True

    def history(
        self,
        symbol: str,
        *,
        start: str | None = None,
        end: str | None = None,
        period: str = "max",
        interval: str = "1d",
    ) -> pd.DataFrame:
        try:
            import yfinance as yf
        except ImportError as exc:
            raise ImportError("install ASRQuant with `pip install asrquant[data]`") from exc
        frame = yf.download(
            symbol,
            start=start,
            end=end,
            period=None if start else period,
            interval=interval,
            auto_adjust=self.auto_adjust,
            progress=False,
            group_by="column",
        )
        if frame.empty:
            raise DataProviderError(f"no Yahoo Finance data returned for {symbol}")
        if isinstance(frame.columns, pd.MultiIndex):
            frame.columns = frame.columns.get_level_values(0)
        frame.index = pd.to_datetime(frame.index, utc=True)
        return frame


_PROVIDERS = {
    "alpha_vantage": AlphaVantageProvider,
    "alphavantage": AlphaVantageProvider,
    "binance": BinanceProvider,
    "fred": FREDProvider,
    "yahoo": YahooProvider,
    "yfinance": YahooProvider,
}


def get_provider(name: str, **kwargs) -> MarketDataProvider:
    """Instantiate a provider by name."""
    key = name.lower().replace("-", "_")
    if key not in _PROVIDERS:
        raise ValueError(f"unknown provider {name!r}; available: {sorted(_PROVIDERS)}")
    return _PROVIDERS[key](**kwargs)


def download(
    provider: str | MarketDataProvider,
    symbols: str | Sequence[str],
    *,
    field: str = "Close",
    **kwargs,
) -> pd.DataFrame:
    """Download one or more symbols into one aligned price/value panel."""
    source = get_provider(provider) if isinstance(provider, str) else provider
    requested = [symbols] if isinstance(symbols, str) else list(symbols)
    if not requested:
        raise ValueError("at least one symbol is required")
    series = {}
    for symbol in requested:
        frame = source.history(symbol, **kwargs)
        selected = field if field in frame.columns else frame.columns[0]
        series[symbol] = frame[selected].rename(symbol)
    return pd.concat(series, axis=1).sort_index()


@dataclass
class PollingFeed:
    """Simple near-real-time polling iterator for research dashboards.

    This is a data feed, not a brokerage or order-execution component.
    """

    provider: MarketDataProvider
    symbol: str
    interval_seconds: float = 60.0

    def stream(self, *, max_updates: int | None = None, **quote_kwargs) -> Iterator[pd.Series]:
        count = 0
        while max_updates is None or count < max_updates:
            quote = self.provider.quote(self.symbol, **quote_kwargs)
            quote.attrs["received_at"] = datetime.now(timezone.utc).isoformat()
            yield quote
            count += 1
            if max_updates is None or count < max_updates:
                time.sleep(self.interval_seconds)
