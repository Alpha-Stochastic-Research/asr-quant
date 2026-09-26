import numpy as np
import pandas as pd
import pytest


def test_release_version():
    import asrquant as asr
    assert asr.__version__ == "1.3.0"


def test_key_rate_hat_partition():
    import asrquant as asr
    pillars=np.array([0.25,0.5,1,2,3,5,7,10,15,20.0]); curve=asr.DiscountCurve.from_zero_rates(pillars,np.full_like(pillars,0.03)); bump=1e-4
    base=np.asarray(curve.zero_rate(pillars)); weights=[]
    for p in pillars:
        z=np.asarray(curve.bump_key_rate(float(p),bump).zero_rate(pillars)); weights.append((z-base)/bump)
    assert np.allclose(np.sum(np.vstack(weights),axis=0),1.0,atol=1e-9)


def test_iv_intrinsic_boundary_refuses():
    import asrquant as asr
    s,k,t,r=120.0,100.0,1.0,0.03; intrinsic=s-k*np.exp(-r*t)
    with pytest.raises(ValueError,match="not identifiable"):
        asr.implied_volatility(intrinsic,s,k,t,r)


def test_psr_scale_invariant_to_annualization_parameter():
    import asrquant.metrics as m
    r=pd.Series([0.01,-0.004,0.006,0.003,-0.002,0.008,-0.001]*20)
    assert m.probabilistic_sharpe_ratio(r,annualization=1) == pytest.approx(m.probabilistic_sharpe_ratio(r,annualization=252),abs=1e-14)


def test_gp_noise_is_contract_not_starting_guess():
    import asrquant as asr
    x=np.linspace(0,1,20); gp=asr.gaussian_process(x,np.sin(x),noise=1e-6)
    assert gp.metadata["noise"] == pytest.approx(1e-6)
    assert gp.metadata["requested_noise"] == pytest.approx(1e-6)


def test_pca_orientation_is_deterministic():
    import asrquant as asr
    rng=np.random.default_rng(42); f=pd.DataFrame(rng.normal(size=(300,5)).cumsum(axis=0)); out=asr.yield_curve_pca(f); arr=out["loadings"].to_numpy().T
    for v in arr:
        assert v[np.argmax(np.abs(v))] >= 0


def test_conventions_schedule_and_daycount():
    from asrquant.conventions import generate_schedule, DayCount
    s=generate_schedule("2026-01-31","2027-01-31",frequency_months=6,end_of_month=True,day_count=DayCount.ACT_365F)
    assert len(s.periods)==2
    assert all(p.accrual_factor>0 for p in s.periods)


def test_credit_bootstrap_reprices():
    from asrquant.credit import bootstrap_hazard_curve, cds_par_spread
    mats=[1,3,5]; spreads=np.array([0.008,0.011,0.014]); curve=bootstrap_hazard_curve(mats,spreads,0.03,recovery=0.4)
    got=np.array([cds_par_spread(curve,0.03,m) for m in mats]); assert np.allclose(got,spreads,atol=1e-9)


def test_research_snapshot_roundtrip(tmp_path):
    from asrquant.research_v130 import DataStore
    frame=pd.DataFrame({"x":[1.0,2.0],"y":[3.0,4.0]},index=pd.date_range("2026-01-01",periods=2))
    store=DataStore(tmp_path); snap=store.put("sample",frame); assert store.verify(snap)


def test_scenario_curve_shock():
    import asrquant as asr
    from asrquant.scenarios import Scenario, shock_discount_curve
    c=asr.DiscountCurve.from_zero_rates([1,2,5],[0.02,0.025,0.03]); b=shock_discount_curve(c,Scenario("up100",rate_parallel_bp=100))
    assert np.allclose(np.asarray(b.zero_rate([1,2,5]))-np.asarray(c.zero_rate([1,2,5])),0.01,atol=1e-10)
