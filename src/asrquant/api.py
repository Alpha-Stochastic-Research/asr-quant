"""High-level five-line research API spanning data, models, backtests, and reports."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Sequence

import pandas as pd

from .audit import implementation_audit
from .backtest import BacktestResult, run_backtest
from .config import BacktestSpec, CostModel
from .data import clean_prices, data_quality_report, load_prices, simple_returns
from . import strategies


_STRATEGIES: dict[str, Callable[..., pd.DataFrame]] = {
    "buy_hold": strategies.buy_and_hold,
    "buy-and-hold": strategies.buy_and_hold,
    "sma": strategies.sma_crossover,
    "sma_crossover": strategies.sma_crossover,
    "momentum": strategies.momentum,
    "mean_reversion": strategies.mean_reversion,
    "vol_target": strategies.volatility_target,
    "volatility_target": strategies.volatility_target,
    "breakout": strategies.breakout,
    "bollinger": strategies.bollinger_mean_reversion,
    "bollinger_mean_reversion": strategies.bollinger_mean_reversion,
    "rsi": strategies.rsi_strategy,
    "pairs": strategies.pairs_zscore,
    "pairs_zscore": strategies.pairs_zscore,
}


class QuantLab:
    """Unified entry point for the end-to-end quantitative research workflow.

    Examples
    --------
    >>> lab = QuantLab.from_csv("prices.csv", date_column="Date")
    >>> result = lab.backtest("sma", fast=20, slow=100, costs_bps=5)
    >>> result.metrics
    >>> result.plot()
    >>> result.report("asrquant_report.html")
    """

    def __init__(self, prices: pd.Series | pd.DataFrame, missing_data: str = "raise"):
        self.prices = clean_prices(prices, missing_data)
        self.returns = simple_returns(self.prices)
        self.last_result: BacktestResult | None = None
        self.last_weights: pd.DataFrame | None = None
        self.source_metadata: dict[str, Any] = {"source": "pandas"}

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        date_column: str | None = None,
        *,
        columns: Sequence[str] | None = None,
        missing_data: str = "raise",
        **kwargs: Any,
    ) -> "QuantLab":
        """Create a lab from CSV, Parquet, Excel, JSON, or Feather."""
        prices = load_prices(path, date_column, columns=columns, **kwargs)
        lab = cls(prices, missing_data=missing_data)
        lab.source_metadata = {"source": "file", "path": str(path), "date_column": date_column}
        return lab

    @classmethod
    def from_csv(
        cls,
        path: str | Path,
        date_column: str | None = None,
        *,
        columns: Sequence[str] | None = None,
        missing_data: str = "raise",
    ) -> "QuantLab":
        """Convenience constructor for CSV price panels."""
        return cls.from_file(path, date_column, columns=columns, missing_data=missing_data)

    @classmethod
    def from_provider(
        cls,
        provider: str,
        symbols: str | Sequence[str],
        *,
        field: str = "Close",
        provider_kwargs: dict[str, Any] | None = None,
        missing_data: str = "drop",
        **history_kwargs: Any,
    ) -> "QuantLab":
        """Download historical or intraday data through a named provider."""
        from .providers import download, get_provider
        source = get_provider(provider, **(provider_kwargs or {}))
        prices = download(source, symbols, field=field, **history_kwargs)
        lab = cls(prices, missing_data=missing_data)
        lab.source_metadata = {"source": provider, "symbols": [symbols] if isinstance(symbols, str) else list(symbols), "field": field}
        return lab

    @property
    def assets(self) -> list[str]:
        return list(self.prices.columns)

    @property
    def quality(self) -> pd.Series:
        return data_quality_report(self.prices)

    def strategy(self, name: str | Callable[..., pd.DataFrame], **kwargs: Any) -> pd.DataFrame:
        """Create target weights from a built-in or user-supplied strategy."""
        if callable(name):
            weights = name(self.prices, **kwargs)
        else:
            key = name.lower()
            if key not in _STRATEGIES:
                raise ValueError(f"unknown strategy {name!r}; available: {sorted(set(_STRATEGIES))}")
            weights = _STRATEGIES[key](self.prices, **kwargs)
        self.last_weights = weights
        return weights

    def backtest(
        self,
        strategy: str | Callable[..., pd.DataFrame] | pd.Series | pd.DataFrame = "buy_hold",
        *,
        spec: BacktestSpec | None = None,
        costs_bps: float | None = None,
        execution_delay: int | None = None,
        **strategy_kwargs: Any,
    ) -> BacktestResult:
        """Construct weights and run the backtest in one call."""
        weights = strategy if isinstance(strategy, (pd.Series, pd.DataFrame)) else self.strategy(strategy, **strategy_kwargs)
        active_spec = spec or BacktestSpec()
        updates: dict[str, Any] = {}
        if costs_bps is not None:
            current = active_spec.costs
            updates["costs"] = CostModel(
                commission_bps=costs_bps,
                spread_bps=current.spread_bps,
                slippage_bps=current.slippage_bps,
                borrow_bps_annual=current.borrow_bps_annual,
                impact_coefficient=current.impact_coefficient,
                impact_exponent=current.impact_exponent,
            )
        if execution_delay is not None:
            updates["execution_delay"] = execution_delay
        if updates:
            active_spec = active_spec.with_updates(**updates)
        result = run_backtest(self.prices, weights, active_spec)
        result.metadata["data_source"] = self.source_metadata
        self.last_result = result
        self.last_weights = pd.DataFrame(weights)
        return result

    def audit(
        self,
        strategy: str | Callable[..., pd.DataFrame] | pd.Series | pd.DataFrame = "buy_hold",
        *,
        spec: BacktestSpec | None = None,
        execution_delays=(0, 1),
        linear_costs_bps=(0.0, 5.0, 10.0),
        rebalances=("bar",),
        **strategy_kwargs: Any,
    ):
        """Measure result dispersion across alternative execution contracts."""
        weights = strategy if isinstance(strategy, (pd.Series, pd.DataFrame)) else self.strategy(strategy, **strategy_kwargs)
        return implementation_audit(
            self.prices,
            weights,
            base_spec=spec,
            execution_delays=execution_delays,
            linear_costs_bps=linear_costs_bps,
            rebalances=rebalances,
        )

    def monte_carlo(self, model: str = "gbm", **kwargs: Any):
        """Simulate ABM, GBM, OU, CIR, Vasicek, Heston, or Merton paths."""
        from .simulation import simulate
        if "initial" not in kwargs and self.prices.shape[1] == 1:
            kwargs["initial"] = float(self.prices.iloc[-1, 0])
        return simulate(model, **kwargs)

    def monte_carlo_experiment(
        self,
        generator,
        quantity=None,
        *,
        n_scenarios: int = 10_000,
        estimator: str | Callable = "mean",
        level: float = 0.95,
        confidence: float = 0.95,
        random_state: int | None = 0,
        parameters: dict[str, Any] | None = None,
        keep_scenarios: bool = True,
    ):
        """Run the universal generate -> transform -> reduce Monte Carlo engine."""
        from .monte_carlo import run_monte_carlo
        return run_monte_carlo(
            generator, quantity, n_scenarios=n_scenarios, estimator=estimator,
            level=level, confidence=confidence, random_state=random_state,
            parameters=parameters, keep_scenarios=keep_scenarios,
        )

    def monte_carlo_surface(
        self,
        generator,
        quantity,
        parameter_grid,
        *,
        x: str,
        y: str,
        animate_by: str | Sequence[str] | None = None,
        estimator: str | Callable = "mean",
        level: float = 0.95,
        confidence: float = 0.95,
        n_scenarios: int = 10_000,
        random_state: int | None = 0,
        fixed_params: dict[str, Any] | None = None,
        z_name: str | None = None,
        n_jobs: int = 1,
    ):
        """Build a static or animated surface from any Monte Carlo statistic."""
        from .monte_carlo import monte_carlo_parameter_surface
        return monte_carlo_parameter_surface(
            generator, quantity, parameter_grid, x=x, y=y, animate_by=animate_by,
            estimator=estimator, level=level, confidence=confidence,
            n_scenarios=n_scenarios, random_state=random_state,
            fixed_params=fixed_params, z_name=z_name, n_jobs=n_jobs,
        )

    def martingale_test(
        self,
        asset: str | None = None,
        *,
        rate: float = 0.0,
        annualization: int = 252,
        lags: int = 10,
    ):
        """Run finite-sample diagnostics on a price or value process."""
        from .martingales import martingale_diagnostics
        selected = asset or self.assets[0]
        return martingale_diagnostics(self.prices[selected], rate=rate, annualization=annualization, lags=lags)

    def regress(
        self,
        y: str | pd.Series,
        x: str | Sequence[str] | pd.Series | pd.DataFrame,
        *,
        method: str = "ols",
        use_returns: bool = True,
        **kwargs: Any,
    ):
        """Run OLS, quantile, polynomial, logistic, or regularized regression."""
        from . import statistics as qs
        source = self.returns if use_returns else self.prices
        y_data = source[y] if isinstance(y, str) else pd.Series(y)
        if isinstance(x, str):
            x_data = source[[x]]
        elif isinstance(x, Sequence) and not isinstance(x, (pd.Series, pd.DataFrame, str, bytes)):
            x_data = source[list(x)]
        else:
            x_data = x
        key = method.lower().replace("-", "_")
        functions = {
            "ols": qs.ols,
            "quantile": qs.quantile_regression,
            "polynomial": qs.polynomial_regression,
            "logistic": qs.logistic_regression,
            "ridge": lambda yy, xx, **kw: qs.regularized_regression(yy, xx, method="ridge", **kw),
            "lasso": lambda yy, xx, **kw: qs.regularized_regression(yy, xx, method="lasso", **kw),
            "elastic_net": lambda yy, xx, **kw: qs.regularized_regression(yy, xx, method="elastic_net", **kw),
        }
        if key not in functions:
            raise ValueError(f"unknown regression method {method!r}")
        return functions[key](y_data, x_data, **kwargs)

    def approximate(self, x, y, *, method: str = "polynomial", **kwargs: Any):
        """Fit interpolation, smoothing, surrogate, or response-regression models."""
        from . import approximation as ap
        key = method.lower().replace("-", "_").replace(" ", "_")
        functions = {
            "linear_interpolation": ap.linear_interpolation,
            "linear_interp": ap.linear_interpolation,
            "spline": ap.cubic_spline,
            "cubic_spline": ap.cubic_spline,
            "kernel": ap.kernel_regression,
            "kernel_regression": ap.kernel_regression,
            "rbf": ap.rbf_interpolation,
            "rbf_interpolation": ap.rbf_interpolation,
            "gaussian_process": ap.gaussian_process,
            "gp": ap.gaussian_process,
            "linear": lambda xx, yy, **kw: ap.response_regression(xx, yy, method="linear", **kw),
            "polynomial": lambda xx, yy, **kw: ap.response_regression(xx, yy, method="polynomial", **kw),
            "ridge": lambda xx, yy, **kw: ap.response_regression(xx, yy, method="ridge", **kw),
            "lasso": lambda xx, yy, **kw: ap.response_regression(xx, yy, method="lasso", **kw),
        }
        if key not in functions:
            raise ValueError(f"unknown approximation method {method!r}")
        return functions[key](x, y, **kwargs)

    def autoregression(
        self,
        asset: str | None = None,
        *,
        lags: int | list[int] = 1,
        use_returns: bool = True,
        trend: str = "c",
    ):
        """Fit an explicit AR(p) model to one asset series."""
        from .statistics import autoregression_fit
        selected = asset or self.assets[0]
        source = self.returns if use_returns else self.prices
        return autoregression_fit(source[selected], lags=lags, trend=trend)

    def garch(
        self,
        asset: str | None = None,
        *,
        p: int = 1,
        q: int = 1,
        horizon: int = 5,
        distribution: str = "t",
    ):
        """Fit GARCH(p,q) through the optional ``arch`` dependency."""
        from .volatility import garch_forecast
        selected = asset or self.assets[0]
        return garch_forecast(self.returns[selected], p=p, q=q, horizon=horizon, distribution=distribution)

    def option(self, model: str = "black_scholes", **kwargs: Any):
        """Price an option with BSM, Bachelier, Black-76, CRR, or Monte Carlo."""
        from .derivatives import price_option
        key = model.lower().replace("-", "_")
        if self.prices.shape[1] == 1:
            latest = float(self.prices.iloc[-1, 0])
            if key in {"bachelier", "normal", "black76", "black_76"} and "forward" not in kwargs:
                kwargs["forward"] = latest
            elif "spot" not in kwargs:
                kwargs["spot"] = latest
        return price_option(model, **kwargs)

    def ml_features(self, asset: str | None = None, **kwargs: Any) -> pd.DataFrame:
        """Generate leakage-aware technical features for one asset."""
        from .machine_learning import technical_features
        selected = asset or self.assets[0]
        return technical_features(self.prices[selected], **kwargs)

    def ml_walk_forward(
        self,
        estimator: Any = "ridge",
        features: pd.DataFrame | None = None,
        target: pd.Series | None = None,
        *,
        model_params: dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        """Run chronological ML evaluation using an ASRQuant model name or estimator."""
        from .machine_learning import walk_forward_fit
        return walk_forward_fit(
            estimator,
            features,
            target,
            model_params=model_params,
            **kwargs,
        )

    def ml(
        self,
        model: Any = "ridge",
        *,
        asset: str | None = None,
        features: pd.DataFrame | None = None,
        target: pd.Series | None = None,
        horizon: int = 1,
        task: str = "regression",
        train_size: int = 252,
        test_size: int = 63,
        model_params: dict[str, Any] | None = None,
        feature_params: dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        """End-to-end feature creation, target creation, and walk-forward ML.

        Examples
        --------
        >>> result = lab.ml("random_forest", task="regression", train_size=252, test_size=63)
        >>> result.aggregate_metrics
        """
        from .machine_learning import forward_target, technical_features, walk_forward_fit
        selected = asset or self.assets[0]
        price = self.prices[selected]
        x = features if features is not None else technical_features(price, **(feature_params or {}))
        classification = task == "classification"
        y = target if target is not None else forward_target(price, horizon=horizon, classification=classification)
        return walk_forward_fit(
            model,
            x,
            y,
            train_size=train_size,
            test_size=test_size,
            task=task,
            model_params=model_params,
            **kwargs,
        )

    def sweep(self, strategy: str, grid: dict[str, list[Any] | tuple[Any, ...]], **kwargs: Any) -> pd.DataFrame:
        """Run a reproducible Cartesian parameter sweep."""
        from .research import parameter_sweep
        return parameter_sweep(self, strategy, grid, **kwargs)



    def parameter_surface(
        self,
        function,
        parameter_grid,
        *,
        x: str | None = None,
        y: str | None = None,
        animate_by: str | Sequence[str] | None = None,
        z_name: str = "value",
        metric=None,
        fixed_params: dict[str, Any] | None = None,
        vectorized: bool = False,
        call_style: str = "keyword",
        n_jobs: int = 1,
        error_policy: str = "raise",
        max_evaluations: int = 1_000_000,
        progress=None,
    ):
        """Evaluate any scalar-valued experiment over an N-dimensional grid.

        Two selected parameters become the displayed axes. All parameters in
        ``animate_by`` are flattened into animation frames, so animations may
        depend on one or several chosen parameters. A result object can be reduced
        with ``metric='metrics.Sharpe'`` or ``metric=lambda result: ...``.
        """
        from .surfaces import evaluate_parameter_surface
        return evaluate_parameter_surface(
            function,
            parameter_grid,
            x=x,
            y=y,
            animate_by=animate_by,
            z_name=z_name,
            metric=metric,
            fixed_params=fixed_params,
            vectorized=vectorized,
            call_style=call_style,
            n_jobs=n_jobs,
            error_policy=error_policy,
            max_evaluations=max_evaluations,
            progress=progress,
        )

    def explore(self, function, parameter_grid, **kwargs: Any):
        """Alias for :meth:`parameter_surface` for experiment exploration."""
        return self.parameter_surface(function, parameter_grid, **kwargs)

    def surface_from_frame(
        self,
        frame: pd.DataFrame,
        *,
        x: str,
        y: str,
        z: str,
        frame_col: str | None = None,
        frame_cols: Sequence[str] | None = None,
        x_name: str | None = None,
        y_name: str | None = None,
        z_name: str | None = None,
        frame_name: str | None = None,
        agg: str | Any = "mean",
    ):
        """Build a static or multi-parameter animated surface from a dataframe."""
        from .surfaces import surface_from_dataframe
        return surface_from_dataframe(
            frame,
            x=x,
            y=y,
            z=z,
            frame_col=frame_col,
            frame_cols=frame_cols,
            x_name=x_name,
            y_name=y_name,
            z_name=z_name,
            frame_name=frame_name,
            agg=agg,
        )

    def surface(
        self,
        function,
        x_values,
        y_values,
        *,
        x_name: str = "x",
        y_name: str = "y",
        z_name: str = "value",
        metric=None,
        fixed_params: dict[str, Any] | None = None,
        vectorized: bool = False,
        call_style: str = "keyword",
        n_jobs: int = 1,
        error_policy: str = "raise",
    ):
        """Evaluate a generic two-dimensional response surface."""
        from .surfaces import evaluate_surface
        return evaluate_surface(
            function,
            x_values,
            y_values,
            x_name=x_name,
            y_name=y_name,
            z_name=z_name,
            metric=metric,
            fixed_params=fixed_params,
            vectorized=vectorized,
            call_style=call_style,
            n_jobs=n_jobs,
            error_policy=error_policy,
        )

    def animate_surface(
        self,
        function,
        x_values,
        y_values,
        frame_values,
        *,
        x_name: str = "x",
        y_name: str = "y",
        frame_name: str = "frame",
        z_name: str = "value",
        metric=None,
        fixed_params: dict[str, Any] | None = None,
        vectorized: bool = False,
        call_style: str = "keyword",
        n_jobs: int = 1,
        error_policy: str = "raise",
    ):
        """Evaluate a one-parameter animated family of response surfaces."""
        from .surfaces import evaluate_surface_animation
        return evaluate_surface_animation(
            function,
            x_values,
            y_values,
            frame_values,
            x_name=x_name,
            y_name=y_name,
            frame_name=frame_name,
            z_name=z_name,
            metric=metric,
            fixed_params=fixed_params,
            vectorized=vectorized,
            call_style=call_style,
            n_jobs=n_jobs,
            error_policy=error_policy,
        )

    def backtest_parameter_surface(
        self,
        strategy: str | Callable[..., pd.DataFrame],
        parameter_grid: dict[str, Sequence[Any]],
        *,
        x: str | None = None,
        y: str | None = None,
        animate_by: str | Sequence[str] | None = None,
        metric: str | Callable[[BacktestResult], float] = "Sharpe",
        strategy_kwargs: dict[str, Any] | None = None,
        spec: BacktestSpec | None = None,
        costs_bps: float | None = None,
        execution_delay: int | None = None,
        n_jobs: int = 1,
        error_policy: str = "raise",
        max_evaluations: int = 100_000,
    ):
        """Explore any number of strategy, cost, and execution parameters.

        Parameters named ``costs_bps`` and ``execution_delay`` are applied to the
        backtest contract; all other parameters are passed to the strategy.
        """
        def experiment(**params):
            kwargs = dict(strategy_kwargs or {})
            kwargs.update(params)
            local_costs_bps = kwargs.pop("costs_bps", costs_bps)
            local_execution_delay = kwargs.pop("execution_delay", execution_delay)
            if callable(strategy):
                weights = strategy(self.prices, **kwargs)
            else:
                key = strategy.lower()
                if key not in _STRATEGIES:
                    raise ValueError(f"unknown strategy {strategy!r}")
                weights = _STRATEGIES[key](self.prices, **kwargs)
            active_spec = spec or BacktestSpec()
            updates: dict[str, Any] = {}
            if local_costs_bps is not None:
                current = active_spec.costs
                updates["costs"] = CostModel(
                    commission_bps=local_costs_bps,
                    spread_bps=current.spread_bps,
                    slippage_bps=current.slippage_bps,
                    borrow_bps_annual=current.borrow_bps_annual,
                    impact_coefficient=current.impact_coefficient,
                    impact_exponent=current.impact_exponent,
                )
            if local_execution_delay is not None:
                updates["execution_delay"] = local_execution_delay
            if updates:
                active_spec = active_spec.with_updates(**updates)
            result = run_backtest(self.prices, weights, active_spec)
            result.metadata["data_source"] = self.source_metadata
            return result

        selector = metric if callable(metric) else f"metrics.{metric}"
        return self.parameter_surface(
            experiment,
            parameter_grid,
            x=x,
            y=y,
            animate_by=animate_by,
            z_name=metric if isinstance(metric, str) else getattr(metric, "__name__", "metric"),
            metric=selector,
            call_style="keyword",
            n_jobs=n_jobs,
            error_policy=error_policy,
            max_evaluations=max_evaluations,
        )

    def backtest_surface(
        self,
        strategy: str | Callable[..., pd.DataFrame],
        *,
        x_param: str,
        x_values,
        y_param: str,
        y_values,
        metric: str = "Sharpe",
        strategy_kwargs: dict[str, Any] | None = None,
        spec: BacktestSpec | None = None,
        costs_bps: float | None = None,
        execution_delay: int | None = None,
    ):
        """Backward-compatible two-parameter backtest surface."""
        return self.backtest_parameter_surface(
            strategy,
            {x_param: x_values, y_param: y_values},
            x=x_param,
            y=y_param,
            animate_by=[],
            metric=metric,
            strategy_kwargs=strategy_kwargs,
            spec=spec,
            costs_bps=costs_bps,
            execution_delay=execution_delay,
        )

    def animate_backtest_surface(
        self,
        strategy: str | Callable[..., pd.DataFrame],
        *,
        x_param: str,
        x_values,
        y_param: str,
        y_values,
        frame_param: str,
        frame_values,
        metric: str = "Sharpe",
        strategy_kwargs: dict[str, Any] | None = None,
        spec: BacktestSpec | None = None,
        costs_bps: float | None = None,
        execution_delay: int | None = None,
    ):
        """Backward-compatible three-parameter animated backtest surface."""
        return self.backtest_parameter_surface(
            strategy,
            {x_param: x_values, y_param: y_values, frame_param: frame_values},
            x=x_param,
            y=y_param,
            animate_by=[frame_param],
            metric=metric,
            strategy_kwargs=strategy_kwargs,
            spec=spec,
            costs_bps=costs_bps,
            execution_delay=execution_delay,
        )

    def to_research_project(
        self,
        hypothesis,
        *,
        name: str = "ASRQuant research project",
        topic: str | None = None,
        extra_data: pd.DataFrame | None = None,
    ):
        """Promote the current lab into an end-to-end research project."""
        from .workflow import EconomicHypothesis, research_project

        project = research_project(hypothesis=hypothesis, name=name, topic=topic)
        data = self.prices.copy()
        if extra_data is not None:
            data = pd.concat([pd.DataFrame(extra_data), data], axis=1).sort_index()
        project.attach_data(data, tradable_assets=self.assets)
        if isinstance(hypothesis, EconomicHypothesis):
            project.set_hypothesis(hypothesis)
        return project

    def paper_trade(
        self,
        weights: pd.Series | pd.DataFrame | None = None,
        *,
        initial_capital: float = 100_000.0,
        commission_bps: float = 0.0,
        slippage_bps: float = 0.0,
        policy=None,
    ):
        """Simulate an order-level paper-trading session from target weights."""
        from .trading import paper_trade

        active_weights = weights if weights is not None else self.last_weights
        if active_weights is None:
            raise RuntimeError("provide weights or generate a strategy before paper trading")
        return paper_trade(
            self.prices,
            pd.DataFrame(active_weights),
            initial_capital=initial_capital,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
            policy=policy,
        )

    def plot(self, kind: str = "prices", **kwargs: Any):
        """Quick data visualization or visualization of the most recent result."""
        from .viz import market
        if kind in {"prices", "price"}:
            return market.price_chart(self.prices, **kwargs)
        if kind in {"returns", "cumulative_returns"}:
            return market.returns_chart(returns=self.returns, cumulative=kind == "cumulative_returns", **kwargs)
        if self.last_result is None:
            raise ValueError("run a backtest before plotting backtest diagnostics")
        return self.last_result.plot(kind=kind, **kwargs)

    def show(self, kind: str = "prices", **kwargs: Any):
        """Display a visualization without importing a plotting backend."""
        from .easy import show
        return show(self, kind=kind, **kwargs)

    def save_plot(self, output: str | Path, kind: str = "prices", **kwargs: Any) -> Path:
        """Save a visualization without importing a plotting backend."""
        from .easy import save
        return save(self, output, kind=kind, **kwargs)
