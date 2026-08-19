"""Interest-rate derivatives lab: curve -> swap -> option -> risk -> model fit."""
import numpy as np
import asrquant as asr

maturities = np.array([0.25, 0.5, 1, 2, 3, 5, 7, 10, 15, 20, 30.0])
zero_rates = np.array([0.020, 0.0205, 0.021, 0.022, 0.023, 0.025, 0.026, 0.027, 0.028, 0.0285, 0.029])

lab = asr.RateQuantLab.from_zero_rates(maturities, zero_rates)
par_5y = lab.par_swap(0, 5, frequency=2)
swap_pv = lab.swap(0, 5, par_5y + 0.001, notional=10_000_000, frequency=2)
swaption = lab.swaption(1, 6, par_5y, 0.20, notional=10_000_000)

fit = asr.calibrate_svensson(maturities, zero_rates)
interp_risk = asr.curve_interpolation_risk(maturities, zero_rates)

print("5Y par swap:", par_5y)
print("Swap PV:", swap_pv)
print("Swaption PV:", swaption)
print("Svensson RMSE:", fit.rmse)
print("Max forward interpolation dispersion:", interp_risk["forward_dispersion"].max())
print(lab.diagnostics())
