"""Command-line entry points for data, simulation, pricing, and backtests."""
from __future__ import annotations

import argparse
from dataclasses import fields
import json
from pathlib import Path

from .version import __version__
from .api import QuantLab
from .data import load_prices
from .derivatives import price_option
from .providers import download, get_provider
from .simulation import regime_switching_prices, simulate
from .literature import LiteratureCorpus
from .workflow import FeaturePlan, FeatureSpec, PortfolioSpec, SignalSpec, research_project
from .production import DeploymentEvidence, ProductionReadinessGate
from .audit_store import SQLiteAuditStore


_STRATEGIES = [
    "buy_hold",
    "sma",
    "momentum",
    "mean_reversion",
    "vol_target",
    "breakout",
    "bollinger",
    "rsi",
    "pairs",
]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="asrquant",
        description="Auditable quantitative-finance research from data to reports.",
    )
    parser.add_argument("--version", action="version", version=f"ASRQuant {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="run a synthetic strategy example")
    demo.add_argument("--output", default="asrquant_demo.html")

    run = sub.add_parser("backtest", help="backtest a local price panel")
    run.add_argument("path")
    run.add_argument("--date-column", default=None)
    run.add_argument("--strategy", default="sma", choices=_STRATEGIES)
    run.add_argument("--output", default="asrquant_report.html")
    run.add_argument("--costs-bps", type=float, default=5.0)
    run.add_argument("--execution-delay", type=int, default=1)
    run.add_argument("--fast", type=int, default=20)
    run.add_argument("--slow", type=int, default=100)
    run.add_argument("--lookback", type=int, default=126)

    sim = sub.add_parser("simulate", help="simulate a stochastic process")
    sim.add_argument(
        "--model",
        default="gbm",
        choices=["abm", "gbm", "ou", "cir", "vasicek", "heston", "merton"],
    )
    sim.add_argument("--initial", type=float, default=100.0)
    sim.add_argument("--drift", type=float, default=0.05)
    sim.add_argument("--volatility", type=float, default=0.20)
    sim.add_argument("--maturity", type=float, default=1.0)
    sim.add_argument("--steps", type=int, default=252)
    sim.add_argument("--paths", type=int, default=10_000)
    sim.add_argument("--seed", type=int, default=7)
    sim.add_argument("--speed", type=float, default=2.0)
    sim.add_argument("--mean", type=float, default=0.04)
    sim.add_argument("--initial-variance", type=float, default=0.04)
    sim.add_argument("--long-variance", type=float, default=0.04)
    sim.add_argument("--mean-reversion", type=float, default=2.0)
    sim.add_argument("--vol-of-vol", type=float, default=0.5)
    sim.add_argument("--correlation", type=float, default=-0.7)
    sim.add_argument("--jump-intensity", type=float, default=0.5)
    sim.add_argument("--jump-mean", type=float, default=-0.10)
    sim.add_argument("--jump-volatility", type=float, default=0.20)
    sim.add_argument("--output", default="asrquant_paths.csv")

    price = sub.add_parser("price", help="price a European or tree option")
    price.add_argument(
        "--model",
        default="black_scholes",
        choices=["black_scholes", "bachelier", "black76", "crr", "monte_carlo"],
    )
    price.add_argument("--spot", type=float, default=100.0)
    price.add_argument("--forward", type=float, default=None)
    price.add_argument("--strike", type=float, required=True)
    price.add_argument("--maturity", type=float, required=True)
    price.add_argument("--rate", type=float, default=0.0)
    price.add_argument("--volatility", type=float, default=0.20)
    price.add_argument("--normal-volatility", type=float, default=10.0)
    price.add_argument("--dividend", type=float, default=0.0)
    price.add_argument("--option", choices=["call", "put"], default="call")
    price.add_argument("--steps", type=int, default=1000)
    price.add_argument("--paths", type=int, default=100_000)
    price.add_argument("--seed", type=int, default=7)
    price.add_argument("--american", action="store_true")

    fetch = sub.add_parser("download", help="download a provider-neutral price panel")
    fetch.add_argument("symbols", nargs="+")
    fetch.add_argument(
        "--provider",
        required=True,
        choices=["alpha_vantage", "binance", "fred", "yahoo"],
    )
    fetch.add_argument("--field", default="Close")
    fetch.add_argument("--api-key", default=None)
    fetch.add_argument("--interval", default=None)
    fetch.add_argument("--start", default=None)
    fetch.add_argument("--end", default=None)
    fetch.add_argument("--period", default="max")
    fetch.add_argument("--limit", type=int, default=500)
    fetch.add_argument("--output", default="asrquant_download.csv")

    papers = sub.add_parser("papers", help="extract source-linked hypothesis candidates from PDFs")
    papers.add_argument("path", help="one PDF or a directory of PDFs")
    papers.add_argument("--topic", default=None)
    papers.add_argument("--output", default="asrquant_hypotheses.csv")
    papers.add_argument("--max-candidates", type=int, default=100)

    research = sub.add_parser("research", help="run a hypothesis-to-decision workflow on a local CSV")
    research.add_argument("path", help="CSV containing predictors and tradable price columns")
    research.add_argument("--date-column", default=None)
    research.add_argument("--hypothesis", required=True)
    research.add_argument("--predictor", required=True)
    research.add_argument("--tradable", nargs="+", required=True)
    research.add_argument("--long-asset", default=None)
    research.add_argument("--short-asset", default=None)
    research.add_argument("--feature-window", type=int, default=20)
    research.add_argument("--threshold", type=float, default=0.0)
    research.add_argument("--costs-bps", type=float, default=5.0)
    research.add_argument("--output", default="asrquant_research_report.html")
    research.add_argument("--manifest", default="asrquant_research_manifest.json")

    readiness = sub.add_parser("readiness", help="evaluate a production deployment evidence file")
    readiness.add_argument("evidence", help="JSON file matching DeploymentEvidence fields")
    readiness.add_argument("--output", default="asrquant_readiness_report.json")
    readiness.add_argument("--minimum-tests", type=int, default=100)
    readiness.add_argument("--minimum-coverage", type=float, default=90.0)
    readiness.add_argument("--minimum-paper-days", type=int, default=30)
    readiness.add_argument("--minimum-paper-orders", type=int, default=500)

    audit = sub.add_parser("verify-audit", help="verify a tamper-evident SQLite audit chain")
    audit.add_argument("path", help="path to the SQLite audit database")
    return parser


def _strategy_kwargs(args: argparse.Namespace) -> dict:
    if args.strategy == "sma":
        return {"fast": args.fast, "slow": args.slow}
    if args.strategy in {"momentum", "mean_reversion", "breakout"}:
        return {"lookback": args.lookback}
    return {}


def _simulation_kwargs(args: argparse.Namespace) -> dict:
    common = {
        "initial": args.initial,
        "maturity": args.maturity,
        "steps": args.steps,
        "paths": args.paths,
        "random_state": args.seed,
    }
    if args.model in {"abm", "gbm"}:
        return {**common, "drift": args.drift, "volatility": args.volatility}
    if args.model == "ou":
        return {
            **common,
            "speed": args.speed,
            "mean": args.mean,
            "volatility": args.volatility,
        }
    if args.model in {"cir", "vasicek"}:
        return {
            **common,
            "speed": args.speed,
            "mean": args.mean,
            "volatility": args.volatility,
        }
    if args.model == "heston":
        return {
            **common,
            "drift": args.drift,
            "initial_variance": args.initial_variance,
            "mean_reversion": args.mean_reversion,
            "long_variance": args.long_variance,
            "vol_of_vol": args.vol_of_vol,
            "correlation": args.correlation,
        }
    return {
        **common,
        "drift": args.drift,
        "volatility": args.volatility,
        "jump_intensity": args.jump_intensity,
        "jump_mean": args.jump_mean,
        "jump_volatility": args.jump_volatility,
    }


def _price_kwargs(args: argparse.Namespace) -> dict:
    common = {
        "strike": args.strike,
        "maturity": args.maturity,
        "rate": args.rate,
        "option": args.option,
    }
    if args.model == "bachelier":
        return {
            **common,
            "forward": args.forward if args.forward is not None else args.spot,
            "normal_volatility": args.normal_volatility,
        }
    if args.model == "black76":
        return {
            **common,
            "forward": args.forward if args.forward is not None else args.spot,
            "volatility": args.volatility,
        }
    if args.model == "crr":
        return {
            **common,
            "spot": args.spot,
            "volatility": args.volatility,
            "dividend": args.dividend,
            "steps": args.steps,
            "american": args.american,
        }
    if args.model == "monte_carlo":
        return {
            **common,
            "spot": args.spot,
            "volatility": args.volatility,
            "paths": args.paths,
            "antithetic": True,
            "random_state": args.seed,
        }
    return {
        **common,
        "spot": args.spot,
        "volatility": args.volatility,
        "dividend": args.dividend,
    }


def _download_kwargs(args: argparse.Namespace) -> tuple[object, dict]:
    provider_kwargs = {}
    if args.api_key is not None and args.provider in {"alpha_vantage", "fred"}:
        provider_kwargs["api_key"] = args.api_key
    provider = get_provider(args.provider, **provider_kwargs)
    if args.provider == "yahoo":
        history = {
            "start": args.start,
            "end": args.end,
            "period": args.period,
            "interval": args.interval or "1d",
        }
    elif args.provider == "binance":
        history = {"interval": args.interval or "1d", "limit": args.limit}
    elif args.provider == "alpha_vantage":
        history = {"interval": args.interval or "daily"}
    else:
        history = {"observation_start": args.start, "observation_end": args.end}
    return provider, {k: v for k, v in history.items() if v is not None}


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    if args.command == "demo":
        prices = regime_switching_prices()
        result = QuantLab(prices).backtest("sma", fast=20, slow=100, costs_bps=5)
        path = result.report(args.output, title="ASRQuant synthetic demonstration")
        print(path)
        return 0

    if args.command == "backtest":
        prices = load_prices(args.path, args.date_column)
        result = QuantLab(prices).backtest(
            args.strategy,
            costs_bps=args.costs_bps,
            execution_delay=args.execution_delay,
            **_strategy_kwargs(args),
        )
        path = result.report(args.output)
        print(path)
        return 0

    if args.command == "simulate":
        result = simulate(args.model, **_simulation_kwargs(args))
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        result.paths.to_csv(output, index_label="time")
        print(result.summary.to_string())
        print(output)
        return 0

    if args.command == "price":
        result = price_option(args.model, **_price_kwargs(args))
        print(result.summary.to_string())
        return 0

    if args.command == "papers":
        corpus = LiteratureCorpus.from_pdfs(args.path, topic=args.topic)
        registry = corpus.discover_hypotheses(max_candidates=args.max_candidates)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        registry.to_frame().to_csv(output, index=False)
        print(corpus.paper_table().to_string(index=False))
        print(registry.scope_note)
        print(output)
        return 0

    if args.command == "readiness":
        payload = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
        allowed = {item.name for item in fields(DeploymentEvidence)}
        unknown = sorted(set(payload) - allowed)
        if unknown:
            raise ValueError(f"unknown DeploymentEvidence fields: {unknown}")
        evidence = DeploymentEvidence(**payload)
        gate = ProductionReadinessGate(
            minimum_tests=args.minimum_tests,
            minimum_coverage=args.minimum_coverage,
            minimum_paper_days=args.minimum_paper_days,
            minimum_paper_orders=args.minimum_paper_orders,
        )
        report = gate.evaluate(evidence)
        output = report.save(args.output)
        print(json.dumps(report.to_dict(), indent=2))
        print(output)
        return 0 if report.ready else 2

    if args.command == "verify-audit":
        store = SQLiteAuditStore(args.path)
        try:
            valid, broken_sequence = store.verify_chain()
            print(json.dumps({"valid": valid, "broken_sequence": broken_sequence}, indent=2))
            return 0 if valid else 3
        finally:
            store.close()

    if args.command == "research":
        frame = load_prices(args.path, args.date_column)
        project = research_project(hypothesis=args.hypothesis, name="ASRQuant CLI research project")
        project.hypothesis.predictor = args.predictor
        project.attach_data(frame, tradable_assets=args.tradable)
        feature = FeatureSpec(
            name=f"{args.predictor}_change_{args.feature_window}",
            source=args.predictor,
            transform="diff",
            params={"periods": args.feature_window},
            availability_lag=1,
        )
        project.build_features(FeaturePlan([feature]))
        if len(args.tradable) >= 2:
            signal = SignalSpec(
                feature=feature.name,
                long_asset=args.long_asset or args.tradable[0],
                short_asset=args.short_asset or args.tradable[1],
                upper=args.threshold,
                lower=-args.threshold,
            )
        else:
            signal = SignalSpec(
                feature=feature.name,
                method="threshold_long",
                long_asset=args.tradable[0],
                upper=args.threshold,
            )
        project.build_signal(signal)
        project.test_hypothesis()
        project.construct_portfolio(PortfolioSpec())
        project.backtest(costs_bps=args.costs_bps, execution_delay=1)
        project.robustness(n_boot=200)
        project.decide()
        report_path = project.report(args.output)
        manifest_path = project.save_manifest(args.manifest)
        print(project.decision_result.summary.to_string())
        print(report_path)
        print(manifest_path)
        return 0

    provider, history_kwargs = _download_kwargs(args)
    frame = download(provider, args.symbols, field=args.field, **history_kwargs)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index_label="Date")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
