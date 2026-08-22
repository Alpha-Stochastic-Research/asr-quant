# Market Microstructure

The `asr.microstructure` namespace provides reusable diagnostics for top-of-book and transaction data.

```python
mid = asr.microstructure.midquote(bid, ask)
spread = asr.microstructure.quoted_spread(bid, ask)
mp = asr.microstructure.microprice(bid, ask, bid_size, ask_size)
ofi = asr.microstructure.order_flow_imbalance(bid, ask, bid_size, ask_size)
```

Other utilities include effective and realized spread, price impact, Amihud illiquidity, Roll spread and Kyle lambda.

Microstructure measures depend strongly on timestamp alignment, trade classification and sampling convention. Treat those choices as model inputs, not housekeeping details.
