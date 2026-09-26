from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

import asrquant as asr


def _market_curve():
    deposits = pd.DataFrame({"maturity": [0.5], "rate": [0.025]})
    swaps = pd.DataFrame({"maturity": [1.0, 1.5, 2.0, 2.5, 3.0], "rate": [0.026, 0.027, 0.028, 0.029, 0.030]})
    return asr.rates.CurveBuilder(deposits=deposits, swaps=swaps, swap_frequency=2).build()


def test_act_act_isda_split_years():
    yf = asr.rates.year_fraction("2023-07-01", "2024-07-01", "ACT/ACT ISDA")
    expected = 184 / 365 + 182 / 366
    assert yf == pytest.approx(expected)


def test_target_calendar_good_friday_and_adjustment():
    cal = asr.rates.Calendar.from_name("TARGET", years=[2026])
    assert not cal.is_business_day("2026-04-03")  # Good Friday
    assert cal.adjust("2026-04-04", "following") == date(2026, 4, 7)


def test_schedule_has_fixing_payment_and_accruals():
    schedule = asr.rates.Schedule(
        "2026-01-31",
        "2027-01-31",
        frequency="3M",
        calendar="TARGET",
        end_of_month=True,
        fixing_lag=2,
        payment_lag=2,
        day_count="ACT/360",
    )
    frame = schedule.to_frame()
    assert len(frame) == 4
    assert (frame["payment_date"] >= frame["accrual_end"]).all()
    assert (frame["fixing_date"] <= frame["accrual_start"]).all()
    assert (frame["accrual_fraction"] > 0).all()


def test_curve_builder_exact_repricing_and_jacobian():
    built = _market_curve()
    assert built.validate()["passed"]
    assert built.summary["max_abs_repricing_error"] < 1e-10
    assert built.jacobian.shape == (6, 6)
    assert np.isfinite(built.jacobian.to_numpy()).all()


def test_swap_par_rate_prices_to_zero():
    built = _market_curve()
    curve = built.curve
    par = curve.par_swap_rate(0.0, 3.0, 2)
    swap = asr.rates.InterestRateSwap(maturity=3.0, fixed_rate=par, notional=10_000_000)
    assert swap.price(curve) == pytest.approx(0.0, abs=1e-7)
    assert len(swap.cashflows(curve)) == 12


def test_curve_risk_quote_space():
    built = _market_curve()
    swap = asr.rates.InterestRateSwap(maturity=3.0, fixed_rate=0.028, notional=1_000_000)
    risk = asr.rates.curve_risk(swap, built.curve, build_result=built)
    assert np.isfinite(risk.dv01)
    assert len(risk.quote_delta) == len(built.quotes)
    assert np.isfinite(risk.quote_pv01.to_numpy()).all()


def test_rate_pnl_explain_reconciles_total():
    built = _market_curve()
    curve0 = built.curve
    curve1 = asr.rates.curve_scenario(curve0, parallel_bp=20, slope_bp=10, curvature_bp=-5)
    swap = asr.rates.InterestRateSwap(maturity=3.0, fixed_rate=0.028, notional=1_000_000)
    explain = asr.rates.pnl_explain(swap, curve0, curve1)
    assert explain.contributions["total"] == pytest.approx(swap.price(curve1) - swap.price(curve0))
    assert explain.contributions.drop("total").sum() == pytest.approx(explain.contributions["total"])


def test_credit_bootstrap_reprices_cds_par_quotes():
    discount = asr.rates.DiscountCurve.from_zero_rates([0.5, 1, 1.5, 2, 2.5, 3], [0.02] * 6)
    maturities = [1.0, 2.0, 3.0]
    spreads = [0.008, 0.010, 0.012]
    hazard = asr.credit.bootstrap_hazard_curve(discount, maturities, spreads, recovery=0.4)
    assert np.all(np.diff(hazard.survival(np.array(maturities))) < 0)
    for maturity, spread in zip(maturities, spreads):
        cds = asr.credit.CDS(maturity, spread, recovery=0.4)
        assert cds.price(discount, hazard) == pytest.approx(0.0, abs=5e-9)


def test_credit_analytics_are_finite():
    discount = asr.rates.DiscountCurve.from_zero_rates([1, 2, 3, 5], [0.02, 0.021, 0.022, 0.024])
    hazard = asr.credit.HazardCurve.constant(0.02, maturity=5)
    cds = asr.credit.CDS(5.0, 0.012, notional=5_000_000)
    result = cds.analytics(discount, hazard)
    assert np.isfinite(result.summary.astype(float)).all()


def test_rate_scenario_repricing():
    built = _market_curve()
    swap = asr.rates.InterestRateSwap(maturity=3.0, fixed_rate=0.028, notional=1_000_000)
    scenario = asr.scenarios.parallel_rate_shift(100)
    result = asr.scenarios.run(scenario, instrument=swap, curve=built.curve)
    assert result.pnl == pytest.approx(result.shocked_value - result.base_value)
    assert result.scenario.parallel_rate_bp == 100


def test_curve_builder_sparse_market_quotes_interpolates_coupon_grid_explicitly():
    built = asr.rates.CurveBuilder.from_quotes(
        deposits={0.25: 0.021, 0.50: 0.022},
        swaps={1.0: 0.023, 2.0: 0.024, 5.0: 0.026},
        valuation_date="2026-09-15",
    ).build()
    assert built.validate()["passed"]
    assert built.summary["max_abs_repricing_error"] < 1e-10
    assert built.metadata["grid_policy"] == "interpolate"
    assert 1.5 in built.metadata["synthetic_coupon_nodes"]
    assert built.jacobian.shape[1] == 5  # sensitivities to original market quotes only
