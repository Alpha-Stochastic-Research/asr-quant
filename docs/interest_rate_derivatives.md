# Fixed Income and Interest Rate Derivatives in ASRQuant

ASRQuant 1.2.0 preserves and exposes the rates stack through one namespace:

```python
import asrquant as asr

asr.rates
```

Rates are decimals (`0.025 == 2.5%`) and times are year fractions unless dates are explicitly supplied.

## Coverage map

| Area | Main concepts | ASRQuant API |
|---|---|---|
| Conventions | ACT/360, ACT/365F, 30/360, 30E/360, maturity conversion | `year_fraction`, `maturity_to_years`, `payment_schedule` |
| Discounting | simple, periodic, continuous compounding | `discount_factor`, `zero_rate_from_discount` |
| Curves | discount, zero, forward, par, instantaneous forward | `DiscountCurve`, `ForwardCurve` |
| Bootstrapping | deposits, FRAs, swaps | `bootstrap_discount_curve` |
| Multi-curve | OIS discounting, tenor projection | `MultiCurve`, `bootstrap_projection_curve_from_swaps` |
| Curve models | Nelson-Siegel, Nelson-Siegel-Svensson | `calibrate_nelson_siegel`, `calibrate_svensson` |
| Bonds | coupon PV, clean/dirty, accrued interest | `bond_price_from_curve`, `clean_price`, `dirty_price` |
| Linear rates | FRA, futures, IRS, basis swap | `fra_pv`, `rate_future_price`, `swap_pv`, `basis_swap_pv` |
| RFR/OIS | overnight compounding, OIS par/PV | `compounded_overnight_rate`, `ois_par_rate`, `ois_pv` |
| Bond forwards | coupon carry and delivery forward value | `bond_forward_price` |
| Cross-currency | covered interest parity and terminal notional exchange | `fx_forward_rate`, `cross_currency_zero_coupon_pv` |
| Inflation | index-ratio annualization and ZC inflation swaps | `zero_coupon_inflation_rate`, `zero_coupon_inflation_swap_pv` |
| Risk | DV01, convexity, key-rate DV01 | `dv01`, `dollar_convexity`, `key_rate_dv01` |
| Caps/floors | Black-76 and normal/Bachelier caplets, cap decomposition | `caplet_price`, `cap_floor_price` |
| Volatility | implied rate vol, caplet stripping | `implied_rate_volatility`, `strip_caplet_volatilities` |
| Swaptions | payer/receiver, Black and normal models | `swaption_price` |
| Smile | SABR/Hagan approximation and calibration | `hagan_sabr_volatility`, `calibrate_sabr` |
| Short-rate models | Vasicek, CIR, Hull-White, Ho-Lee, Black-Karasinski | corresponding model functions |
| Forward-rate models | one-factor HJM, terminal-measure LMM | `hjm_one_factor_paths`, `lmm_terminal_measure_paths` |
| Early exercise | generic scalar-state least-squares Monte Carlo | `bermudan_lsm` |
| Hedging/scenarios | parallel/slope/curvature and key-rate hedge solve | `curve_scenario`, `key_rate_hedge` |
| Calibration | SABR, Vasicek, Nelson-Siegel, Svensson | `calibrate_*` |
| Curve statistics | PCA, level/slope/curvature | `yield_curve_pca`, `level_slope_curvature` |
| Relative value | carry/roll-down | `carry_roll_down` |
| Model/data risk | no-arbitrage diagnostics, interpolation risk | `no_arbitrage_curve_diagnostics`, `curve_interpolation_risk` |
| Training | progressive exercises and curriculum | `rates_curriculum`, `rates_exercises` |

## Simple high-level lab

```python
import asrquant as asr

lab = asr.RateQuantLab.from_zero_rates(
    [0.25, 0.5, 1, 2, 3, 5, 7, 10],
    [0.020, 0.021, 0.022, 0.023, 0.024, 0.026, 0.027, 0.028],
)

par = lab.par_swap(0, 5, frequency=2)
pv = lab.swap(0, 5, fixed_rate=0.025, notional=10_000_000)
checks = lab.diagnostics()
```

The lab is only a convenience layer. Every lower-level curve, convention and model remains directly accessible for research and validation.

## ECB yield-curve data

```python
provider = asr.ECBProvider()
history = provider.yield_curve_history(
    maturities=("3M", "6M", "1Y", "2Y", "5Y", "10Y", "30Y"),
    start="2020-01-01",
)

lab = asr.RateQuantLab.from_ecb()
```

`yield_curve_history()` converts percent-per-annum ECB observations into decimal rates and aligns maturities by timestamp.

## Curve construction and model risk

A rates researcher should never evaluate only the fitted zero rates. ASRQuant exposes the induced forward curve and interpolation dispersion because small zero-rate differences can create large local forward differences.

```python
risk = asr.curve_interpolation_risk(maturities, zero_rates)
print(risk[["maturity", "forward_dispersion"]])
```

For parametric curves:

```python
fit_ns = asr.calibrate_nelson_siegel(maturities, zero_rates)
fit_svensson = asr.calibrate_svensson(maturities, zero_rates)
```

Compare RMSE, forward smoothness, stability through time and downstream pricing/risk—not RMSE alone.

## Multi-curve valuation

Post-crisis rates valuation distinguishes the discount curve from projection curves. `MultiCurve` keeps this explicit. A projection curve can be implied from one curve for educational single-curve checks or bootstrapped separately from tenor swap quotes for multi-curve research.

## Options and volatility

Rate options can be quoted in lognormal or normal volatility conventions. ASRQuant therefore keeps the model argument explicit rather than silently assuming Black.

```python
black = asr.caplet_price(curve, 1.0, 1.5, 0.03, 0.20, model="black")
normal = asr.caplet_price(curve, 1.0, 1.5, 0.03, 0.01, model="normal")
```

The same principle applies to swaptions and implied-volatility inversion.

## Models: what they are for

- **Vasicek / CIR**: tractable short-rate dynamics and term-structure intuition.
- **Hull-White / Ho-Lee / Black-Karasinski**: path simulation and comparative model research.
- **HJM**: forward-curve dynamics under no-arbitrage drift restrictions.
- **LMM**: correlated forward-rate dynamics on a tenor structure.
- **SABR**: smile representation/calibration for rate-option volatility research.

The implementations are transparent research/reference implementations. They are not a replacement for a desk's full conventions engine, collateral agreement model, market-calendar stack, exchange rulebook, or independently validated production pricer.

## Risk and research

Core curve-risk work should include at least:

1. PV and par-rate checks;
2. parallel DV01;
3. key-rate DV01;
4. convexity/nonlinearity;
5. PCA level/slope/curvature shocks;
6. interpolation and curve-construction risk;
7. carry/roll decomposition;
8. model disagreement;
9. historical and scenario stress;
10. cross-currency/inflation/collateral assumptions when relevant;
11. early-exercise/model-regression diagnostics for Bermudan products;
12. reproducibility and convention audit.

## Training path

```python
asr.rates_curriculum()
asr.rates_exercises()
```

The exercise bank progresses from discounting and bootstrapping through multi-curve valuation, caps/floors, swaptions, SABR, short-rate models, HJM/LMM, curve PCA, interpolation risk and a complete ASR weekly publication cycle.
