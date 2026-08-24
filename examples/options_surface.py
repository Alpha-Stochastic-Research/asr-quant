"""One-import volatility and Greek surfaces."""
import asrquant as asr

strikes = asr.math.linspace(70, 130, 31)
maturities = asr.math.linspace(0.05, 2.0, 25)
kk, tt = asr.math.meshgrid(strikes, maturities)
implied_volatility = 0.18 + 0.00007 * (kk - 100) ** 2 + 0.025 * asr.math.exp(-tt)
vol_fig = asr.visuals.derivatives.volatility_surface(strikes, maturities, implied_volatility)
gamma_fig = asr.visuals.derivatives.greek_surface(strikes, maturities, spot=100, rate=0.03, volatility=0.2, greek="gamma")
asr.PlotHandle(vol_fig).save("vol_surface.png", dpi=150)
asr.PlotHandle(gamma_fig).save("gamma_surface.png", dpi=150)
