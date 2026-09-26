from __future__ import annotations

import importlib
import math
import sys

import numpy as np
import pandas as pd
import pytest

import asrquant as asr
from asrquant.approximation import gaussian_process
from asrquant.derivatives import black_scholes_price, implied_volatility
from asrquant.interest_rates import DiscountCurve, calibrate_vasicek, yield_curve_pca
from asrquant.machine_learning import technical_features
from asrquant.metrics import deflated_sharpe_ratio, probabilistic_sharpe_ratio, summary_metrics


def test_key_rate_bumps_partition_unity_on_uneven_pillars():
    pillars = np.array([0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 15.0, 20.0])
    curve = DiscountCurve.from_zero_rates(pillars, np.full(len(pillars), 0.03))
    bump = 1e-4
    base = curve.zero_rate(pillars)
    weights = []
    for pillar in pillars:
        bumped = curve.bump_key_rate(float(pillar), bump=bump)
        weights.append((bumped.zero_rate(pillars) - base) / bump)
    total = np.sum(np.asarray(weights), axis=0)
    assert np.allclose(total, 1.0, atol=1e-10)


def test_key_rate_requires_pillar_for_automatic_width():
    curve = DiscountCurve.from_zero_rates([1.0, 2.0, 5.0], [0.02, 0.025, 0.03])
    with pytest.raises(ValueError, match="match a curve pillar"):
        curve.bump_key_rate(3.0)


def test_implied_volatility_refuses_intrinsic_boundary():
    spot, strike, maturity, rate = 100.0, 50.0, 1.0, 0.0
    intrinsic = spot - strike
    with pytest.raises(ValueError, match="not identifiable"):
        implied_volatility(intrinsic, spot, strike, maturity, rate, option="call")


def test_implied_volatility_round_trip_interior():
    px = float(black_scholes_price(100, 105, 1.3, 0.025, 0.24, "call"))
    assert implied_volatility(px, 100, 105, 1.3, 0.025, "call") == pytest.approx(0.24, abs=1e-9)


def test_psr_uses_per_observation_sharpe_scale():
    r = pd.Series([0.012, -0.006, 0.009, 0.004, -0.003, 0.011, -0.002] * 40)
    assert probabilistic_sharpe_ratio(r, annualization=252) == pytest.approx(
        probabilistic_sharpe_ratio(r, annualization=1), abs=1e-15
    )
    assert deflated_sharpe_ratio(r, trials=1000, annualization=252) < 1.0


def test_omega_threshold_is_exposed_in_summary_metrics():
    r = pd.Series([0.02, -0.01, 0.015, -0.005, 0.01, -0.008] * 10)
    base = summary_metrics(r)
    shifted = summary_metrics(r, omega_threshold=0.002)
    assert base["Omega"] != shifted["Omega"]


def test_gaussian_process_noise_is_a_fixed_contract():
    x = np.linspace(0, 1, 20)
    result = gaussian_process(x, np.sin(x), noise=0.025)
    assert result.metadata["requested_noise"] == pytest.approx(0.025)
    assert result.metadata["fitted_noise"] == pytest.approx(0.025)


def test_rsi_defaults_to_wilder_and_sma_is_explicit():
    p = pd.Series(np.r_[np.linspace(100, 110, 20), np.linspace(110, 96, 20)])
    wilder = technical_features(p)["rsi_14"]
    sma = technical_features(p, rsi_method="sma")["rsi_14"]
    assert not np.allclose(wilder.dropna().tail(10), sma.dropna().tail(10))


def test_pca_sign_orientation_is_deterministic_for_overlapping_windows():
    rng = np.random.default_rng(42)
    level = rng.normal(scale=0.001, size=320)
    panel = pd.DataFrame({f"{m}Y": level + rng.normal(scale=2e-5, size=320) * i for i, m in enumerate([1,2,3,5,7,10])})
    a = yield_curve_pca(panel.iloc[:250], differences=False)["loadings"].iloc[:, 0].to_numpy()
    b = yield_curve_pca(panel.iloc[20:270], differences=False)["loadings"].iloc[:, 0].to_numpy()
    assert float(np.dot(a, b)) > 0
    assert a[np.argmax(np.abs(a))] > 0
    assert b[np.argmax(np.abs(b))] > 0


def test_vasicek_reports_kappa_uncertainty():
    rng = np.random.default_rng(7)
    phi = math.exp(-0.5 / 252)
    x = np.zeros(2000)
    x[0] = 0.03
    for i in range(1, len(x)):
        x[i] = 0.03 * (1 - phi) + phi * x[i-1] + 0.0005 * rng.normal()
    fit = calibrate_vasicek(x)
    assert fit.phi_std_error is not None and fit.phi_std_error > 0
    assert fit.kappa_std_error is not None and fit.kappa_std_error > 0


def test_black_scholes_put_call_parity_native_engine():
    spot, strike, maturity, rate, vol = 100.0, 105.0, 1.25, 0.03, 0.22
    call = float(black_scholes_price(spot, strike, maturity, rate, vol, "call"))
    put = float(black_scholes_price(spot, strike, maturity, rate, vol, "put"))
    rhs = spot - strike * math.exp(-rate * maturity)
    assert call - put == pytest.approx(rhs, abs=1e-10)


def test_import_does_not_eagerly_load_optional_heavy_stacks():
    import json, os, subprocess
    env = os.environ.copy()
    env["PYTHONPATH"] = str(__import__("pathlib").Path(__file__).parents[1] / "src")
    code = (
        "import sys,json; before=set(sys.modules); import asrquant; after=set(sys.modules)-before; "
        "print(json.dumps({k:any(m==k or m.startswith(k+'.') for m in after) "
        "for k in ['matplotlib','requests','sklearn']}))"
    )
    out = subprocess.check_output([sys.executable, "-c", code], env=env, text=True)
    loaded = json.loads(out.strip())
    assert loaded == {"matplotlib": False, "requests": False, "sklearn": False}
