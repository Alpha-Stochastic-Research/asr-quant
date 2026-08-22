# Data & Provenance

## Canonical data interface

```python
import asrquant as asr

data = asr.data.load("prices.csv", date_column="Date")
quality = asr.data.validate(data)
```

`asr.data.load` accepts supported local table formats, public HTTP(S) tables and provider-backed data through the broader data layer. Existing helpers such as `load_prices`, `load_sql`, `clean_prices`, `simple_returns` and `log_returns` remain available.

## Provider surface

The 1.2 package includes provider abstractions for ECB, Yahoo, FRED, Binance and Alpha Vantage. Availability, credentials and external revisions remain provider-specific.

## Recommended research checks

Before downstream modelling, record:

1. source and retrieval timestamp;
2. timestamp semantics and timezone;
3. publication/revision lag when relevant;
4. missing-value policy;
5. corporate-action or instrument adjustments;
6. data fingerprint or equivalent reproducibility metadata.

## Point-in-time principle

A final-vintage dataset can contain information that was not available to the strategy at historical decision time. For empirical research, reconstruct the information set that actually existed at each date whenever revisions or publication lags matter.
