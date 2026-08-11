import numpy as np
import pandas as pd
import pytest

import asrquant as asr
from asrquant import interest_rates as ir


def flat_curve(rate=0.03, end=10.0):
    times = np.arange(0.5, end + 0.5, 0.5)
    return ir.DiscountCurve.from_zero_rates(times, np.full_like(times, rate, dtype=float))


def test_discount_zero_roundtrip_continuous():
    t = np.array([0.5, 1.0, 5.0])
    r = np.array([0.02, 0.025, 0.03])
    p = ir.discount_factor(r, t)
    assert np.allclose(ir.zero_rate_from_discount(p, t), r)


def test_forward_identity_flat_curve():
    c = flat_curve(0.03)
    fcc = c.forward_rate(2.0, 3.0, "continuous")
    assert fcc == pytest.approx(0.03, abs=1e-12)
    f_simple = c.forward_rate(2.0, 3.0, "simple")
    assert f_simple == pytest.approx(np.exp(0.03) - 1.0)


def test_day_count():
    assert ir.year_fraction("2026-01-01", "2026-07-01", "ACT/360") == pytest.approx(181/360)
    assert ir.year_fraction("2026-01-01", "2026-07-01", "ACT/365F") == pytest.approx(181/365)
    assert ir.year_fraction("2026-01-30", "2026-07-30", "30/360") == pytest.approx(0.5)


def test_discount_curve_table_and_diagnostics():
    c = flat_curve()
    table = c.table()
    assert {"maturity", "discount_factor", "zero_rate_cc"}.issubset(table.columns)
    diag = ir.no_arbitrage_curve_diagnostics(c)
    assert bool(diag["positive_discounts"])
    assert bool(diag["discounts_nonincreasing"])


def test_bootstrap_deposit_fra():
    deposits = pd.DataFrame({"maturity": [0.5], "rate": [0.02]})
    p05 = 1/(1+0.02*0.5)
    f = 0.025
    fras = pd.DataFrame({"start": [0.5], "end": [1.0], "rate": [f]})
    c = ir.bootstrap_discount_curve(deposits=deposits, fras=fras)
    assert c.df(0.5) == pytest.approx(p05)
    assert c.forward_rate(0.5, 1.0, "simple") == pytest.approx(f)


def test_bootstrap_par_swaps_reprices():
    # annual grid because each earlier node is available
    swaps = pd.DataFrame({"maturity": [1.0, 2.0, 3.0], "rate": [0.02, 0.024, 0.027]})
    c = ir.bootstrap_discount_curve(swaps=swaps, swap_frequency=1)
    for row in swaps.itertuples(index=False):
        assert c.par_swap_rate(0.0, row.maturity, 1) == pytest.approx(row.rate, abs=1e-12)


def test_projection_curve_from_discount():
    c = flat_curve(0.03, 5.0)
    p = ir.projection_curve_from_discount(c, 0.5, name="6M")
    assert len(p.forwards) == 10
    assert p.rate(0.0, 0.5) > 0


def test_projection_curve_bootstrap_from_swaps():
    d = flat_curve(0.02, 3.0)
    swaps = pd.DataFrame({"maturity": [0.5, 1.0, 1.5], "rate": [0.022, 0.023, 0.024]})
    p = ir.bootstrap_projection_curve_from_swaps(d, swaps, tenor=0.5, fixed_frequency=2)
    for row in swaps.itertuples(index=False):
        assert ir.swap_par_rate(d, 0.0, row.maturity, fixed_frequency=2, projection=p) == pytest.approx(row.rate, abs=1e-10)


def test_bond_curve_and_risk():
    c = flat_curve(0.03, 10)
    pv = ir.bond_price_from_curve(c, 100, 0.04, 5, 2)
    assert pv > 100
    pricer = lambda curve: ir.bond_price_from_curve(curve, 100, 0.04, 5, 2)
    assert ir.dv01(pricer, c) > 0
    assert ir.dollar_convexity(pricer, c) > 0
    kr = ir.key_rate_dv01(pricer, c, [2.0, 5.0, 10.0])
    assert len(kr) == 3


def test_clean_dirty_accrued_identity():
    ai = ir.accrued_interest(100, 0.06, 2, 0.25)
    assert ai == pytest.approx(0.75)
    assert ir.dirty_price(ir.clean_price(101.5, ai), ai) == pytest.approx(101.5)


def test_fra_zero_at_strike_forward():
    c = flat_curve(0.03)
    f = ir.fra_forward_rate(c, 1.0, 1.5)
    assert ir.fra_pv(c, 1.0, 1.5, f, notional=1e6) == pytest.approx(0.0, abs=1e-8)
    assert ir.fra_pv(c, 1.0, 1.5, f, notional=1e6, settlement="start") == pytest.approx(0.0, abs=1e-8)


def test_swap_zero_at_par_and_payer_sign():
    c = flat_curve(0.03)
    par = ir.swap_par_rate(c, 0.0, 5.0)
    assert ir.swap_pv(c, 0.0, 5.0, par, notional=1e6) == pytest.approx(0.0, abs=1e-7)
    assert ir.swap_pv(c, 0.0, 5.0, par - 0.005, notional=1e6, position="payer") > 0


def test_basis_swap_zero_same_projection():
    c = flat_curve(0.03, 5)
    p = ir.projection_curve_from_discount(c, 0.5)
    assert ir.basis_swap_pv(c, p, p, 0.0, 5.0) == pytest.approx(0.0, abs=1e-12)


def test_rate_future_roundtrip():
    rate = 0.0475
    assert ir.rate_from_future_price(ir.rate_future_price(rate)) == pytest.approx(rate)


def test_caplet_positive_and_floor_parity_direction():
    c = flat_curve(0.03, 5)
    f = ir.fra_forward_rate(c, 1.0, 1.5)
    cap = ir.caplet_price(c, 1.0, 1.5, f, 0.20, notional=1e6)
    floor = ir.caplet_price(c, 1.0, 1.5, f, 0.20, notional=1e6, option="floorlet")
    assert cap > 0 and floor > 0
    assert cap == pytest.approx(floor, rel=1e-10)


def test_bachelier_caplet_works_with_negative_forward():
    c = ir.DiscountCurve.from_zero_rates([0.5, 1.0, 1.5, 2.0], [-0.005]*4)
    price = ir.caplet_price(c, 1.0, 1.5, -0.005, 0.01, model="bachelier")
    assert price > 0


def test_cap_floor_sum_and_strip_vols():
    c = flat_curve(0.03, 5)
    periods = [(0.5, 1.0), (1.0, 1.5), (1.5, 2.0)]
    vols = np.array([0.18, 0.20, 0.22])
    strike = 0.03
    cumulative = []
    for i in range(1, len(periods)+1):
        cumulative.append(ir.cap_floor_price(c, periods[:i], strike, vols[:i], notional=1e6))
    stripped = ir.strip_caplet_volatilities(c, periods, strike, cumulative, notional=1e6)
    assert np.allclose(stripped.to_numpy(), vols, atol=1e-8)


def test_swaption_atm_payer_receiver_match():
    c = flat_curve(0.03, 10)
    k = ir.swap_par_rate(c, 2.0, 7.0)
    payer = ir.swaption_price(c, 2.0, 7.0, k, 0.20, notional=1e6, option="payer")
    receiver = ir.swaption_price(c, 2.0, 7.0, k, 0.20, notional=1e6, option="receiver")
    assert payer == pytest.approx(receiver, rel=1e-10)


def test_implied_vol_roundtrip():
    c = flat_curve(0.03, 5)
    price = ir.caplet_price(c, 1.0, 1.5, 0.03, 0.25)
    vol = ir.implied_rate_volatility(price, lambda sigma: ir.caplet_price(c, 1.0, 1.5, 0.03, sigma))
    assert vol == pytest.approx(0.25, abs=1e-9)


def test_sabr_atm_positive_and_calibration():
    f = 0.03
    strikes = np.array([0.015, 0.02, 0.03, 0.04, 0.05])
    params = dict(alpha=0.03, beta=0.5, rho=-0.25, nu=0.45)
    vols = np.array([ir.hagan_sabr_volatility(f, k, 2.0, **params) for k in strikes])
    cal = ir.calibrate_sabr(strikes, vols, f, 2.0, beta=0.5, initial=(0.025, -0.1, 0.4))
    assert cal.success
    assert cal.rmse < 1e-6


def test_short_rate_bond_prices_are_valid():
    v = ir.vasicek_zero_coupon_bond(0.03, 0.0, 5.0, 0.5, 0.04, 0.01)
    c = ir.cir_zero_coupon_bond(0.03, 0.0, 5.0, 0.5, 0.04, 0.10)
    assert 0 < v < 1.2
    assert 0 < c < 1.2


def test_short_rate_path_shapes():
    hw = ir.hull_white_paths(0.03, 0.5, 0.04, 0.01, 1.0, steps=12, paths=100, random_state=1)
    hl = ir.ho_lee_paths(0.03, 0.0, 0.01, 1.0, steps=12, paths=100, random_state=1)
    bk = ir.black_karasinski_paths(0.03, 0.5, np.log(0.04), 0.1, 1.0, steps=12, paths=100, random_state=1)
    assert hw.shape == hl.shape == bk.shape == (13, 100)
    assert (bk.to_numpy() > 0).all()


def test_hjm_lmm_shapes_and_positivity():
    hjm = ir.hjm_one_factor_paths([1, 2, 3], [0.02, 0.025, 0.03], [0.01, 0.012, 0.014], 0.5, steps=5, paths=20)
    assert hjm.shape == (6, 20, 3)
    corr = np.array([[1.0, .5, .3], [.5, 1.0, .5], [.3, .5, 1.0]])
    lmm = ir.lmm_terminal_measure_paths([0.02, 0.025, 0.03], [0.5]*3, [0.2]*3, corr, 0.5, steps=5, paths=20)
    assert lmm.shape == (6, 20, 3)
    assert (lmm > 0).all()


def test_vasicek_calibration_from_simulated_series():
    paths = ir.hull_white_paths(0.03, 0.8, 0.04, 0.01, 4.0, steps=1000, paths=1, random_state=11)
    cal = ir.calibrate_vasicek(paths.iloc[:, 0].to_numpy(), dt=4/1000)
    assert cal.kappa > 0 and cal.sigma > 0


def test_curve_pca_and_factors():
    rng = np.random.default_rng(2)
    idx = pd.date_range("2024-01-01", periods=250, freq="B")
    level = np.cumsum(rng.normal(0, 0.0002, len(idx)))
    slope = np.cumsum(rng.normal(0, 0.0001, len(idx)))
    frame = pd.DataFrame({
        "2Y": .02 + level - slope,
        "5Y": .025 + level,
        "10Y": .03 + level + slope,
        "30Y": .032 + level + 1.2*slope,
    }, index=idx)
    pca = ir.yield_curve_pca(frame)
    assert pca["loadings"].shape == (4, 3)
    factors = ir.level_slope_curvature(frame)
    assert list(factors.columns) == ["level", "slope", "curvature"]


def test_curve_interpolation_risk_and_carry_roll():
    out = ir.curve_interpolation_risk([0.5, 1, 2, 5, 10], [0.02, .021, .023, .028, .03])
    assert "forward_dispersion" in out.columns
    c = flat_curve(0.03, 10)
    cr = ir.carry_roll_down(c, 5.0, 1.0)
    assert "carry_roll_return" in cr.index


def test_rates_curriculum_and_exercises_cover_research():
    curriculum = ir.rates_curriculum()
    exercises = ir.rates_exercises()
    assert len(curriculum) >= 16
    assert len(exercises) >= 32
    assert "Research" in set(exercises["level"])


def test_rate_quant_lab_high_level_api():
    lab = asr.RateQuantLab.from_zero_rates([0.5, 1, 2, 5, 10], [0.02, .021, .023, .028, .03])
    assert lab.par_swap(0, 5) > 0
    assert len(lab.curriculum()) >= 16
    assert len(lab.exercises()) >= 32
    assert "positive_discounts" in lab.diagnostics().index


def test_one_import_rates_alias_contains_legacy_and_new_api():
    assert hasattr(asr.rates, "zero_coupon_price")
    assert hasattr(asr.rates, "DiscountCurve")
    assert hasattr(asr.rates, "swaption_price")


def test_maturity_and_parametric_curve_models():
    import asrquant as asr

    assert np.isclose(asr.maturity_to_years("3M"), 0.25)
    assert np.isclose(asr.maturity_to_years("10Y"), 10.0)

    maturities = np.array([0.25, 0.5, 1, 2, 3, 5, 7, 10, 15, 20, 30.0])
    ns_true = np.asarray(asr.nelson_siegel_yield(maturities, 0.032, -0.018, 0.012, 2.5))
    ns_fit = asr.calibrate_nelson_siegel(maturities, ns_true)
    assert ns_fit.success
    assert ns_fit.rmse < 1e-7
    assert np.max(np.abs(ns_fit.fitted_rates - ns_true)) < 1e-6

    sv_true = np.asarray(asr.svensson_yield(maturities, 0.03, -0.02, 0.015, -0.008, 1.7, 6.5))
    sv_fit = asr.calibrate_svensson(maturities, sv_true)
    assert sv_fit.success
    assert sv_fit.rmse < 5e-6
    curve = sv_fit.discount_curve(maturities)
    assert np.all(curve.discounts > 0)


def test_rate_quant_lab_from_ecb_compatible_provider():
    import asrquant as asr

    class FakeECB:
        def latest_yield_curve(self, maturities):
            values = [0.02 + 0.0005 * i for i, _ in enumerate(maturities)]
            row = pd.Series(values, index=[str(x).upper() for x in maturities])
            row.name = pd.Timestamp("2026-08-11", tz="UTC")
            return row

    lab = asr.RateQuantLab.from_ecb(("3M", "1Y", "2Y", "5Y", "10Y"), provider=FakeECB())
    assert lab.curve.name.startswith("ECB")
    assert lab.curve.metadata["provider"] == "ECB"
    assert np.isfinite(lab.par_swap(0.0, 5.0, frequency=2))


def test_rfr_ois_and_bond_forward_building_blocks():
    import asrquant as asr

    rates = np.array([0.03, 0.031, 0.029])
    accruals = np.array([1 / 360, 1 / 360, 1 / 360])
    compounded = asr.compounded_overnight_rate(rates, accruals)
    expected = (np.prod(1 + rates * accruals) - 1) / accruals.sum()
    assert np.isclose(compounded, expected)

    curve = asr.DiscountCurve.from_zero_rates([0.5, 1, 2, 3], [0.02, 0.021, 0.023, 0.024])
    par = asr.ois_par_rate(curve, 0, 2)
    assert abs(asr.ois_pv(curve, 0, 2, par, notional=1_000_000)) < 1e-7

    fwd = asr.bond_forward_price(curve, 101.0, 1.0, [0.5, 1.0], [2.0, 2.0])
    expected_fwd = (101.0 - 2.0 * curve.df(0.5) - 2.0 * curve.df(1.0)) / curve.df(1.0)
    assert np.isclose(fwd, expected_fwd)


def test_cross_currency_inflation_and_curve_scenarios():
    import asrquant as asr

    domestic = asr.DiscountCurve.from_zero_rates([1, 2, 5], [0.03, 0.031, 0.032])
    foreign = asr.DiscountCurve.from_zero_rates([1, 2, 5], [0.02, 0.021, 0.022])
    spot = 1.20
    fwd = asr.fx_forward_rate(spot, domestic, foreign, 2.0)
    assert np.isclose(fwd, spot * foreign.df(2.0) / domestic.df(2.0))

    domestic_notional = fwd * 1_000_000
    pv = asr.cross_currency_zero_coupon_pv(
        spot, domestic, foreign, 2.0,
        domestic_notional=domestic_notional,
        foreign_notional=1_000_000,
    )
    assert abs(pv) < 1e-7

    inflation = asr.zero_coupon_inflation_rate(100, 110.25, 2)
    assert np.isclose(inflation, 0.05)
    zc_pv = asr.zero_coupon_inflation_swap_pv(domestic, 2, 0.05, 1.1025, notional=1_000_000)
    assert abs(zc_pv) < 1e-7

    up = asr.curve_scenario(domestic, parallel_bp=10)
    assert np.allclose(up.zero_rate([1, 2, 5]), domestic.zero_rate([1, 2, 5]) + 0.001, atol=1e-10)


def test_key_rate_hedge_and_bermudan_lsm():
    import asrquant as asr

    target = np.array([100.0, -50.0, 25.0])
    hedges = np.eye(3)
    solution = asr.key_rate_hedge(target, hedges)
    assert np.allclose(solution.weights, -target)
    assert solution.residual_norm < 1e-10

    # Deterministic early-exercise toy case: immediate value is always best at t=0.
    immediate = np.array([
        [10.0, 10.0, 10.0, 10.0],
        [8.0, 8.0, 8.0, 8.0],
        [6.0, 6.0, 6.0, 6.0],
    ])
    state = np.array([
        [1.0, 1.1, 1.2, 1.3],
        [1.0, 1.1, 1.2, 1.3],
        [1.0, 1.1, 1.2, 1.3],
    ])
    result = asr.bermudan_lsm(immediate, state, [0.99, 0.99], polynomial_degree=1)
    assert np.isclose(result.price, 10.0)
    assert np.all(result.exercise_time_index == 0)
    assert np.isclose(result.exercise_probability[0], 1.0)
