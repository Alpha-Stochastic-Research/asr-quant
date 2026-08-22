# Fixed Income & Interest Rates

ASRQuant 1.2.0 retains the broad 1.1 interest-rate stack behind `asr.rates` and root-level compatibility functions.

## Build a zero curve

```python
import numpy as np
import asrquant as asr

maturities = np.array([0.25, 0.5, 1, 2, 3, 5, 7, 10, 20, 30.0])
zero_rates = np.array([0.0200, 0.0205, 0.0210, 0.0220, 0.0230,
                       0.0250, 0.0260, 0.0270, 0.0285, 0.0290])

lab = asr.RateQuantLab.from_zero_rates(maturities, zero_rates)
print(asr.rates.analyze(lab.curve).summary)
```

## Swap pricing

```python
par_5y = lab.par_swap(0, 5, frequency=2)
pv = lab.swap(
    0,
    5,
    par_5y + 0.001,
    notional=10_000_000,
    frequency=2,
)
```

## Rate-option and model layer

The package includes caps/floors, caplets, swaptions, SABR, Vasicek, CIR, Hull-White, Ho-Lee, Black-Karasinski, HJM and LMM utilities, together with DV01, key-rate DV01, curve scenarios, hedging, PCA and carry/roll diagnostics.

## Calibration

Canonical calibration is available through:

```python
fit = asr.rates.calibrate("svensson", maturities, zero_rates)
```

Supported canonical names are Nelson-Siegel, Svensson, SABR and Vasicek.
