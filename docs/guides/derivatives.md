# Derivatives

## Canonical pricing

```python
price = asr.options.price(
    "black_scholes",
    spot=100,
    strike=100,
    maturity=1.0,
    rate=0.03,
    volatility=0.20,
)
print(price.summary)
```

The derivative layer includes Black-Scholes, Black-76, Bachelier, Cox-Ross-Rubinstein tree pricing, implied volatility and Monte Carlo pricing utilities.

## Model choice is part of the result

Do not compare prices across models without documenting volatility convention, underlying/forward convention, discounting, exercise assumptions and numerical settings.
