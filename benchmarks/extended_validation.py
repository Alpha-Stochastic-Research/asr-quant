from __future__ import annotations

from pathlib import Path
import sys

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from asrquant.derivatives import black_scholes_price, crr_binomial_price, bachelier_price
from asrquant.martingales import martingale_diagnostics
from asrquant.simulation import arithmetic_brownian_motion, european_option_mc, geometric_brownian_motion
from asrquant.statistics import ols

OUT = ROOT / "benchmarks"
FIG = ROOT / "paper" / "figures"
OUT.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True)

# Numerical convergence table
analytic = float(black_scholes_price(100, 100, 1, 0.03, 0.2))
rows = []
for n in [1_000, 5_000, 20_000, 100_000, 250_000]:
    result = european_option_mc(100, 100, 1, 0.03, 0.2, paths=n, random_state=123)
    rows.append({"paths": n, "estimate": result.price, "standard_error": result.standard_error,
                 "ci_lower": result.confidence_interval[0], "ci_upper": result.confidence_interval[1],
                 "analytic": analytic, "absolute_error": abs(result.price-analytic)})
mc = pd.DataFrame(rows)
mc.to_csv(OUT / "monte_carlo_validation.csv", index=False)

# Binomial convergence
binomial_rows=[]
for steps in [10,25,50,100,250,500,1000]:
    price=crr_binomial_price(100,100,1,0.03,0.2,steps=steps)
    binomial_rows.append({"steps":steps,"price":price,"analytic":analytic,"absolute_error":abs(price-analytic)})
pd.DataFrame(binomial_rows).to_csv(OUT / "binomial_validation.csv", index=False)

# Martingale diagnostics
abm = arithmetic_brownian_motion(initial=100, drift=0, volatility=1, maturity=4, steps=1008, paths=1, random_state=8)
series = abm.paths.iloc[:,0]
series.index = pd.bdate_range("2020-01-01", periods=len(series))
mart = martingale_diagnostics(series, lags=10)
mart.statistics.to_csv(OUT / "martingale_validation.csv", header=["value"])

# Regression coefficient recovery
rng=np.random.default_rng(44)
index=pd.bdate_range("2015-01-01",periods=1500)
x=pd.DataFrame({"market":rng.normal(0,0.01,len(index)),"value":rng.normal(0,0.006,len(index))},index=index)
y=pd.Series(0.0002+1.25*x["market"]-0.40*x["value"]+rng.normal(0,0.003,len(index)),index=index)
fit=ols(y,x,covariance="HAC")
reg=pd.DataFrame({"estimate":fit.coefficients,"lower":fit.confidence_intervals["lower"],"upper":fit.confidence_intervals["upper"],"true":[0.0002,1.25,-0.40]},index=["const","market","value"])
reg.to_csv(OUT / "regression_validation.csv")

# Emblematic architecture figure
fig, ax = plt.subplots(figsize=(14, 8))
ax.set_xlim(0, 14); ax.set_ylim(0, 8); ax.axis("off")
colors = {"data":"#1D4ED8","models":"#0F766E","research":"#7C3AED","outputs":"#C2410C","core":"#111827"}

def box(x,y,w,h,text,color,fs=11):
    patch=FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.04,rounding_size=0.12",facecolor=color,edgecolor="white",linewidth=1.5,alpha=0.96)
    ax.add_patch(patch); ax.text(x+w/2,y+h/2,text,ha="center",va="center",color="white",fontsize=fs,fontweight="bold",wrap=True)

def arrow(x1,y1,x2,y2):
    ax.annotate("",xy=(x2,y2),xytext=(x1,y1),arrowprops=dict(arrowstyle="-|>",lw=2,color="#475569"))

box(0.4,5.7,2.6,1.35,"DATA\nCSV · Parquet · Excel · SQL\nYahoo · Alpha Vantage\nBinance · FRED",colors["data"],10)
box(0.4,3.45,2.6,1.35,"DATA CONTRACT\nvalidation · alignment\nmissingness · provenance\nfingerprints",colors["data"],10)
box(4.1,4.4,3.5,2.0,"ASRQuant CORE\nQuantLab + explicit research contracts\nreproducible defaults · audit trail\nshort API, visible assumptions",colors["core"],12)
box(8.7,5.85,2.4,1.1,"STOCHASTIC MODELS\nABM · GBM · OU · CIR\nVasicek · Heston · Merton",colors["models"],9)
box(11.3,5.85,2.3,1.1,"DERIVATIVES\nBSM · Bachelier · Black-76\nCRR · Monte Carlo",colors["models"],9)
box(8.7,4.25,2.4,1.1,"STATISTICS\nOLS/HAC · quantile\ncointegration · ARIMA/VAR",colors["research"],9)
box(11.3,4.25,2.3,1.1,"MACHINE LEARNING\nlag-safe features\nwalk-forward validation",colors["research"],9)
box(8.7,2.65,2.4,1.1,"PORTFOLIO & RISK\nHRP · Black-Litterman\nVaR/ES · stress · volatility",colors["research"],9)
box(11.3,2.65,2.3,1.1,"BACKTESTING\ncosts · delays · leverage\nturnover · parameter sweeps",colors["research"],9)
box(4.1,1.05,3.5,1.45,"AUDITABLE OUTPUTS\nmetrics · trade ledger · 2D/3D figures\nimplementation audits · HTML reports\nconfidence intervals · manifests",colors["outputs"],11)
arrow(1.7,5.7,1.7,4.8); arrow(3.0,4.1,4.1,5.0)
for y in [6.4,4.8,3.2]: arrow(7.6,5.4,8.7,y)
for y in [6.4,4.8,3.2]: arrow(7.6,5.0,11.3,y)
arrow(5.85,4.4,5.85,2.5)
ax.text(7,7.6,"ASRQuant v0.3.0 — From Market Data to Multidimensional Quantitative Experiments",ha="center",va="center",fontsize=17,fontweight="bold",color="#0F172A")
ax.text(7,7.15,"One coherent workflow for data, stochastic models, pricing, econometrics, ML, portfolio construction, visualization, and backtesting",ha="center",fontsize=10.5,color="#475569")
fig.tight_layout(); fig.savefig(FIG/"asrquant_architecture_v030.png",dpi=220,bbox_inches="tight"); plt.close(fig)

# Validation figure
fig,axes=plt.subplots(2,2,figsize=(13,9))
axes[0,0].errorbar(mc["paths"],mc["estimate"],yerr=1.96*mc["standard_error"],marker="o",capsize=4,label="MC ± 95% CI")
axes[0,0].axhline(analytic,linestyle="--",label="Black-Scholes")
axes[0,0].set_xscale("log"); axes[0,0].set_title("Monte Carlo convergence"); axes[0,0].set_xlabel("Paths"); axes[0,0].set_ylabel("Call price"); axes[0,0].legend()
gbm=geometric_brownian_motion(100,0.03,0.2,1,252,1000,11)
gbm.paths.iloc[:,:30].plot(ax=axes[0,1],legend=False,alpha=.25)
q=gbm.paths.quantile([.05,.5,.95],axis=1).T
axes[0,1].plot(q.index,q[.5],linewidth=2,label="Median"); axes[0,1].fill_between(q.index,q[.05],q[.95],alpha=.18,label="5%-95%")
axes[0,1].set_title("GBM paths and uncertainty fan"); axes[0,1].legend()
lagged=series.shift(1).reindex(mart.increments.index)
axes[1,0].scatter(lagged,mart.increments,alpha=.28,s=12)
axes[1,0].axhline(0,linestyle="--"); axes[1,0].set_title("Martingale conditional-mean diagnostic"); axes[1,0].set_xlabel("Lagged process level"); axes[1,0].set_ylabel("Next increment")
spot_grid=np.linspace(50,150,250)
axes[1,1].plot(spot_grid,black_scholes_price(spot_grid,100,1,.03,.2),label="Black-Scholes-Merton")
axes[1,1].plot(spot_grid,bachelier_price(spot_grid*np.exp(.03),100,1,20,discount=np.exp(-.03)),label="Bachelier")
axes[1,1].set_title("Closed-form model comparison"); axes[1,1].set_xlabel("Spot"); axes[1,1].set_ylabel("Call value"); axes[1,1].legend()
for ax in axes.ravel(): ax.grid(alpha=.22)
fig.suptitle("Independent numerical validation of core stochastic and pricing components",fontsize=15,fontweight="bold")
fig.tight_layout(); fig.savefig(FIG/"extended_validation_v030.png",dpi=220,bbox_inches="tight"); plt.close(fig)

print("Generated", analytic, mart.statistics.to_dict(), reg.to_dict())
