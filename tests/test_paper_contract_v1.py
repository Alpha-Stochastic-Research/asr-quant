from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import numpy as np
import pandas as pd

import asrquant as asr


def _prices(rows: int = 320) -> pd.DataFrame:
    index = pd.date_range("2021-01-04", periods=rows, freq="B")
    rng = np.random.default_rng(20260810)
    returns = rng.normal([0.00035, 0.00020], [0.010, 0.009], size=(rows, 2))
    values = 100.0 * np.exp(np.cumsum(returns, axis=0))
    return pd.DataFrame(values, index=index, columns=["VALUE", "GROWTH"])


def test_one_import_polynomial_modelling_and_visualization(tmp_path: Path) -> None:
    x = [-3, -2, -1, 0, 1, 2, 3]
    y = [2 + 3 * value - 0.5 * value**2 for value in x]

    model = asr.fit(x, y, method="polynomial", degree=2, covariance="HC1")

    assert np.isclose(model.coefficients["const"], 2.0)
    assert np.isclose(model.coefficients["x"], 3.0)
    assert np.isclose(model.coefficients["x^2"], -0.5)

    handle = asr.visualize(model, kind="fitted")
    output = handle.save(tmp_path / "polynomial_fit.png")
    assert output.exists() and output.stat().st_size > 0

    # Already-created backend figures remain compatible with the one-import API.
    wrapped = asr.visualize(handle.raw)
    assert wrapped.raw is handle.raw


def test_appendix_csv_to_audited_backtest(tmp_path: Path) -> None:
    prices = _prices()
    path = tmp_path / "prices.csv"
    prices.to_csv(path, index_label="Date")

    lab = asr.QuantLab.from_csv(path, date_column="Date")
    result = lab.backtest("momentum", lookback=126, costs_bps=8)
    report = Path(result.report(tmp_path / "momentum_report.html"))

    assert "Sharpe" in result.metrics.index
    assert report.exists() and report.stat().st_size > 0


def test_appendix_provider_contract_without_network(monkeypatch) -> None:
    prices = _prices(80)[["VALUE"]].rename(columns={"VALUE": "Close"})

    class FakeProvider:
        def history(self, symbol: str, **kwargs):
            assert symbol in {"BTCUSDT", "ETHUSDT"}
            return prices.copy()

    monkeypatch.setattr("asrquant.providers.get_provider", lambda name, **kwargs: FakeProvider())

    lab = asr.QuantLab.from_provider(
        "binance", ["BTCUSDT", "ETHUSDT"], interval="1d", limit=80
    )
    assert lab.assets == ["BTCUSDT", "ETHUSDT"]
    assert lab.source_metadata["source"] == "binance"


def test_appendix_monte_carlo_martingale_and_option_pricing() -> None:
    lab = asr.QuantLab(_prices()[["VALUE"]])

    simulation = lab.monte_carlo(
        "heston",
        drift=0.03,
        paths=300,
        initial_variance=0.04,
        long_variance=0.04,
        random_state=7,
    )
    assert simulation.paths.shape[1] == 300
    assert simulation.plot("fan") is not None

    martingale = lab.martingale_test(rate=0.03)
    assert len(martingale.statistics) > 0

    closed = lab.option(
        "black_scholes", strike=100, maturity=1, rate=0.03, volatility=0.20
    )
    mc = lab.option(
        "monte_carlo", strike=100, maturity=1, rate=0.03, volatility=0.20, paths=5_000,
        random_state=11,
    )
    assert np.isfinite(closed.price)
    assert np.isfinite(mc.price)


def test_appendix_implementation_audit_and_regression() -> None:
    prices = _prices()
    lab = asr.QuantLab(prices)

    audit = lab.audit(
        "sma",
        fast=20,
        slow=100,
        execution_delays=(0, 1, 2),
        linear_costs_bps=(0, 5, 10, 25),
    )
    assert len(audit.summary) == 12
    assert audit.plot() is not None

    strategy_returns = prices["VALUE"].pct_change().dropna()
    factors = asr.frame({"MKT": prices["GROWTH"].pct_change()}).dropna()
    fit = asr.stats.ols(strategy_returns.loc[factors.index], factors, covariance="HAC")
    assert "MKT" in fit.coefficients.index
    assert asr.visualize(fit, kind="residuals").raw is not None


def test_appendix_option_surface_one_import() -> None:
    figure = asr.visuals.derivatives.greek_surface(
        strikes=[80, 90, 100, 110, 120],
        maturities=[0.25, 0.5, 1.0],
        spot=100,
        rate=0.03,
        volatility=0.20,
        greek="gamma",
        interactive=False,
    )
    assert asr.visualize(figure).raw is figure


def test_appendix_research_project_to_governed_paper_trade() -> None:
    data = _prices(360)
    rng = np.random.default_rng(99)
    data["US10Y"] = 3.0 + np.cumsum(rng.normal(0.0, 0.01, len(data)))

    project = asr.research.from_hypothesis(
        "Rising yields predict value outperformance over growth.",
        predictor="US10Y",
        expected_sign="positive",
        horizon=20,
    )
    project.attach_data(data, tradable_assets=["VALUE", "GROWTH"])
    project.build_features("recommended")
    project.build_signal()
    project.test_hypothesis()
    project.construct_portfolio()
    project.backtest(costs_bps=5, execution_delay=1)
    project.robustness()
    decision = project.decide()

    status_code = decision.status.lower().replace(" ", "-")
    assert status_code in {
        "reject",
        "research-only",
        "collect-more-data",
        "revise-hypothesis",
        "paper-trading-candidate",
        "limited-capital-candidate",
    }

    paper = project.paper_trade(
        commission_bps=1,
        slippage_bps=2,
        policy=asr.RiskPolicy(
            max_gross_leverage=1.0,
            max_position_weight=0.25,
            max_daily_turnover=0.5,
            max_drawdown=0.15,
        ),
    )
    assert isinstance(paper.orders, pd.DataFrame)
    assert isinstance(paper.risk_events, pd.DataFrame)


def test_public_api_catalog_exports_paper_claims() -> None:
    expected = {
        "QuantLab",
        "LiteratureCorpus",
        "EconomicHypothesis",
        "FeatureSpec",
        "SignalSpec",
        "PortfolioSpec",
        "ResearchProject",
        "RiskPolicy",
        "paper_trade",
        "simulate",
        "price_option",
        "stationary_bootstrap",
        "bootstrap_zero_curve",
        "fit",
        "visualize",
        "show",
        "save",
    }
    missing = sorted(name for name in expected if not hasattr(asr, name))
    assert not missing, missing


def test_visualization_catalog_remains_above_one_hundred_public_functions() -> None:
    import ast
    import asrquant.viz as viz

    root = Path(viz.__file__).parent
    count = 0
    for source in root.glob("*.py"):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        count += sum(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and not node.name.startswith("_")
            for node in tree.body
        )
    assert count >= 100


def test_audit_store_query_backup_and_chain_branches(tmp_path: Path) -> None:
    database = tmp_path / "audit.sqlite3"
    backup = tmp_path / "backup" / "audit-copy.sqlite3"

    with asr.SQLiteAuditStore(database) as store:
        first = store.append("order", {"id": 1}, idempotency_key="same")
        repeated = store.append("order", {"id": 999}, idempotency_key="same")
        second = store.append("risk", {"id": 2})
        third = store.append("order", {"id": 3})

        assert repeated.event_id == first.event_id
        assert store.events(limit=0) == []
        assert [event.sequence for event in store.events(limit=2)] == [1, 2]
        assert [event.sequence for event in store.events(event_type="order")] == [1, 3]
        assert [event.sequence for event in store.events(event_type="order", limit=1)] == [1]
        assert [event.sequence for event in store.events(after_sequence=1)] == [2, 3]
        assert store.latest().sequence == third.sequence
        assert store.latest("risk").sequence == second.sequence
        assert store.latest("missing") is None
        assert store.verify_chain() == (True, None)
        store.checkpoint()
        assert store.backup(backup) == backup

    assert backup.exists() and backup.stat().st_size > 0


def test_appendix_in_memory_custom_strategy() -> None:
    prices = _prices()
    lab = asr.QuantLab(prices)
    result = lab.backtest("momentum", lookback=126, costs_bps=8)
    assert np.isfinite(float(result.metrics["Total Return"]))
    assert len(result.equity) == len(prices)


def test_appendix_pdf_to_hypothesis_registry_real_text_pdf() -> None:
    sample = Path(__file__).parent / "data" / "paper_hypothesis_sample.pdf"
    project = asr.research.from_pdfs(
        sample,
        topic="interest rates and equity style returns",
    )
    registry = project.discover_hypotheses()
    frame = registry.to_frame()
    assert len(frame) >= 1
    assert frame["pages"].astype(str).str.contains("p1").any()
    assert "rising long-term interest rates" in frame.iloc[0]["statement"].lower()


def test_paper_seven_core_stochastic_process_families() -> None:
    models = ("abm", "gbm", "ou", "cir", "vasicek", "heston", "merton")
    for model in models:
        result = asr.simulate(model, steps=8, paths=6, random_state=123)
        assert result.paths.shape == (9, 6), model
        assert np.isfinite(result.paths.to_numpy()).all(), model


def test_paper_derivative_pricing_contract() -> None:
    bsm = float(asr.black_scholes_price(100, 100, 1, 0.03, 0.20))
    black76 = float(asr.black76_price(100, 100, 1, 0.03, 0.20))
    bach = float(asr.bachelier_price(100, 100, 1, 10.0))
    tree = float(asr.crr_binomial_price(100, 100, 1, 0.03, 0.20, steps=500))
    iv = float(asr.implied_volatility(bsm, 100, 100, 1, 0.03))
    european = asr.european_option_mc(100, 100, 1, 0.03, 0.20, paths=4_000, random_state=2)
    asian = asr.asian_option_mc(100, 100, 1, 0.03, 0.20, paths=2_000, steps=24, random_state=2)
    assert bsm > 0 and black76 > 0 and bach > 0 and tree > 0
    assert abs(iv - 0.20) < 1e-7
    assert european.price > 0 and european.standard_error > 0
    assert asian.price > 0 and asian.standard_error > 0


def test_paper_fixed_income_contract() -> None:
    price = asr.bond_price(100, 0.05, 5, 0.04, 2)
    ytm = asr.yield_to_maturity(price, 100, 0.05, 5, 2)
    macaulay = asr.macaulay_duration(100, 0.05, 5, 0.04, 2)
    modified = asr.modified_duration(100, 0.05, 5, 0.04, 2)
    cx = asr.convexity(100, 0.05, 5, 0.04, 2)
    curve = asr.bootstrap_zero_curve(
        asr.frame(
            {
                "maturity": [0.5, 1.0, 1.5, 2.0],
                "par_rate": [0.02, 0.022, 0.024, 0.025],
                "frequency": [2, 2, 2, 2],
            }
        )
    )
    assert abs(float(ytm) - 0.04) < 1e-8
    assert macaulay > 0 and modified > 0 and cx > 0
    assert len(curve) == 4
    assert np.isfinite(curve.to_numpy()).all()


def test_paper_broker_order_types_partial_fill_and_cancellation() -> None:
    broker = asr.PaperBroker(
        initial_cash=10_000,
        commission_bps=1,
        slippage_bps=2,
        participation_rate=0.5,
    )
    order = asr.Order("XYZ", 10, asr.OrderSide.BUY)
    fill = broker.submit_order(order, 100.0)
    assert fill is not None
    assert order.status == asr.OrderStatus.PARTIALLY_FILLED
    assert abs(abs(fill.quantity) - 5.0) < 1e-12

    resting = asr.Order(
        "XYZ",
        2,
        asr.OrderSide.BUY,
        order_type=asr.OrderType.LIMIT,
        limit_price=90.0,
    )
    assert broker.submit_order(resting, 100.0) is None
    assert resting.status == asr.OrderStatus.ACCEPTED
    assert broker.cancel_order(resting.order_id) is True
    assert resting.status == asr.OrderStatus.CANCELLED

    assert {member.value for member in asr.OrderType} == {
        "market", "limit", "stop", "stop_limit"
    }


def test_paper_surface_contract_html_and_gif_export(tmp_path: Path) -> None:
    surface = asr.evaluate_surface_animation(
        lambda x, y, regime: (x - 1.0) ** 2 + y + regime,
        x_values=[0.0, 1.0, 2.0],
        y_values=[0.0, 1.0],
        frame_values=[0.0, 1.0],
        x_name="x",
        y_name="y",
        frame_name="regime",
    )
    assert surface.is_animated
    assert len(surface.best()) > 0
    html = surface.save_animation(tmp_path / "surface.html")
    gif = surface.save_animation(tmp_path / "surface.gif", interval=250)
    assert html.exists() and html.stat().st_size > 0
    assert gif.exists() and gif.stat().st_size > 0


def test_paper_one_import_formula_to_polynomial_model() -> None:
    x = [-3, -2, -1, 0, 1, 2, 3]
    y = [2 + 3 * value - 0.5 * value**2 for value in x]
    model = asr.fit(x, y, method="polynomial", degree=2)
    assert np.isclose(model.coefficients["const"], 2.0)
    assert np.isclose(model.coefficients["x"], 3.0)
    assert np.isclose(model.coefficients["x^2"], -0.5)
    handle = asr.visualize(model, kind="fitted")
    assert handle.raw is not None
    handle.close()
