# Data sources and ingestion

ASRQuant separates data acquisition from numerical research. Remote calls occur only when the user explicitly constructs or invokes a provider.

## Local data

Supported through `QuantLab.from_file(...)` or `asrquant.data.load_prices(...)`:

| Format | Extension | Optional dependency |
|---|---|---|
| CSV/text | `.csv`, `.txt` | none |
| Parquet | `.parquet`, `.pq` | `pyarrow` |
| Excel | `.xlsx`, `.xls` | `openpyxl` or another pandas engine |
| JSON | `.json` | none |
| Feather | `.feather`, `.ft` | `pyarrow` |
| SQL | connection + query | database driver chosen by the user |

The default parser treats the first column as the timestamp unless `date_column` is supplied. It converts selected value columns to floats, sorts timestamps, and rejects duplicate timestamps or infinite values.

## Canonical price-panel contract

A `QuantLab` price panel has:

- a unique `DatetimeIndex`;
- one column per asset;
- positive finite prices;
- a declared missing-data policy: `raise`, `drop`, or `ffill`;
- no implicit network request or hidden field selection.

Use `lab.quality` or `data_quality_report(...)` to inspect row count, date range, missingness, duplicate timestamps, sampling gaps, and constant columns.

## OHLCV data

`validate_ohlcv(...)` checks canonical `Open`, `High`, `Low`, and `Close` columns and optional non-negative `Volume`. `resample_ohlcv(...)` uses finance-consistent aggregation:

- Open: first;
- High: maximum;
- Low: minimum;
- Close: last;
- Volume: sum;
- other fields: last.

## Remote providers

### Alpha Vantage

`AlphaVantageProvider` supports daily, weekly, monthly, and intraday equity time series. Supply an API key through the constructor or `ALPHAVANTAGE_API_KEY`.

```python
lab = QuantLab.from_provider(
    "alpha_vantage",
    "IBM",
    provider_kwargs={"api_key": "..."},
    interval="daily",
)
```

### Binance

`BinanceProvider` retrieves public Spot kline/candlestick data and requires no key for the implemented endpoint.

```python
lab = QuantLab.from_provider("binance", "BTCUSDT", interval="1h", limit=1000)
```

### FRED

`FREDProvider` retrieves economic series. Supply a key through the constructor or `FRED_API_KEY`.

```python
lab = QuantLab.from_provider(
    "fred",
    ["DGS10", "DGS2"],
    field="Value",
    provider_kwargs={"api_key": "..."},
    observation_start="2015-01-01",
)
```

### Yahoo

`YahooProvider` is an optional convenience adapter based on `yfinance`.

```bash
pip install "asrquant[data]"
```

```python
lab = QuantLab.from_provider("yahoo", ["SPY", "QQQ"], start="2018-01-01")
```

## Near-real-time polling

`PollingFeed` repeatedly invokes a provider's latest-observation method at an explicit interval. It stamps each observation with `received_at`.

```python
provider = BinanceProvider()
feed = PollingFeed(provider, "BTCUSDT", interval_seconds=60)
for quote in feed.stream(max_updates=5, interval="1m", limit=2):
    print(quote)
```

Polling is not a WebSocket, exchange gateway, broker connection, or order router. It is suitable for research dashboards and simple data collection, subject to provider limits and terms.

## Reproducibility and licensing

For every remote dataset, record:

- provider and endpoint;
- symbol or series identifier;
- fields and adjustment convention;
- requested interval and date range;
- timezone and timestamp interpretation;
- retrieval timestamp;
- entitlement, redistribution, and citation requirements;
- raw response or immutable snapshot when permitted;
- data fingerprint after normalization.

Provider availability, schemas, prices, entitlements, rate limits, and revision policies are upstream properties and may change independently of ASRQuant.
