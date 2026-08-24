"""One-import historical downloads and near-real-time polling."""
import asrquant as asr

lab = asr.open_lab(
    provider="binance",
    symbols=["BTCUSDT", "ETHUSDT"],
    interval="1h",
    limit=500,
)
print(lab.prices.tail())

feed = asr.PollingFeed(asr.BinanceProvider(), "BTCUSDT", interval_seconds=60)
for quote in feed.stream(max_updates=3, interval="1m", limit=2):
    print(quote)
