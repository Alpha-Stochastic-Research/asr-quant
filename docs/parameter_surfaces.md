# Parameter surfaces and animations

ASRQuant 0.3.0 treats a surface as a view of a finite parameter experiment.
A surface has two displayed numeric axes. Additional parameters can be fixed or
converted into animation frames.

## Core API

```python
surface = lab.parameter_surface(
    experiment,
    parameter_grid={
        "gamma": [0.5, 1.0, 2.0, 4.0],
        "cost_bps": [0, 2, 5, 10],
        "hedge_every": [1, 5, 20],
        "volatility": [0.15, 0.30],
        "model": ["linear", "neural"],
    },
    x="gamma",
    y="cost_bps",
    animate_by=["hedge_every", "volatility", "model"],
    metric="metrics.utility",
    z_name="utility",
)
```

The callable is invoked once for every point in the finite grid. It may return:

- a scalar;
- a mapping or pandas Series;
- a dataclass or ordinary object;
- an ASRQuant result object;
- any result reducible by `metric=lambda result: ...`.

## Dimensional interpretation

For a parameter grid with dimensions

```text
(gamma, cost_bps, hedge_every, volatility, model)
```

and `x="gamma"`, `y="cost_bps"`, the surface geometry is two-dimensional.
`hedge_every`, `volatility`, and `model` form the animation frame table. The
number of frames is the Cartesian product of their candidate values.

This means ASRQuant can explore an arbitrary number of finite parameters, but
it does not claim to draw a literal geometric surface with more than two axes.
Higher dimensions are represented through slices and animation.

## Metric selection

```python
metric=None                         # callable returns one scalar
metric="Sharpe"                    # mapping or Series key
metric="metrics.Sharpe"            # dotted object path
metric=lambda result: result.cvar  # custom reduction
```

## Fixed parameters

A parameter that is neither an axis nor animated must have one candidate value
or be supplied in `fixed_params`.

```python
surface = lab.parameter_surface(
    option_experiment,
    {"strike": strikes, "maturity": maturities},
    x="strike",
    y="maturity",
    fixed_params={"spot": 100, "rate": 0.03, "volatility": 0.20},
)
```

## Vectorized functions

When the experiment accepts NumPy mesh arrays for the two displayed axes, set
`vectorized=True`. Extra frame parameters remain scalar in each frame.

```python
surface = lab.parameter_surface(
    lambda x, y, theta: np.sin(x + theta) * np.cos(y),
    {"x": x, "y": y, "theta": theta},
    vectorized=True,
)
```

## Parallel evaluation and failures

```python
surface = lab.parameter_surface(
    expensive_experiment,
    grid,
    n_jobs=8,
    error_policy="nan",
    max_evaluations=200_000,
)
```

`n_jobs` uses threads and is most useful for I/O-bound or native-code-backed
experiments. Stateful callables must be thread-safe. `error_policy="nan"`
keeps the remaining grid and records failures in `surface.metadata["errors"]`.

## Backtest parameter exploration

```python
surface = lab.backtest_parameter_surface(
    "sma",
    {
        "fast": [5, 10, 20],
        "slow": [40, 80, 120],
        "costs_bps": [0, 5, 10],
        "execution_delay": [0, 1, 2],
    },
    x="fast",
    y="slow",
    animate_by=["costs_bps", "execution_delay"],
    metric="Sharpe",
)
```

`costs_bps` and `execution_delay` are interpreted as backtest-contract
parameters. Other names are passed to the strategy.

## Existing CSV or DataFrame results

```python
results = pd.read_csv("deep_hedging_results.csv")
surface = lab.surface_from_frame(
    results,
    x="risk_aversion",
    y="cost_bps",
    z="oos_cvar",
    frame_cols=["hedge_every", "volatility", "seed"],
)
```

## Plotting and export

```python
surface.plot("surface", frame=0)
surface.plot("heatmap", frame=0)
surface.plot("contour", frame=0)

surface.save_animation("experiment.html")       # interactive Plotly slider
surface.save_animation("experiment.gif")        # Pillow writer
surface.save_animation("experiment.mp4")        # FFmpeg required
surface.export_frames("frames", kind="surface")
```

HTML is the recommended portable format because it preserves camera controls,
play/pause controls, and the complete parameter label for every frame.

## Research safeguards

- A visually smooth surface is not evidence of statistical validity.
- Parameter grids should be specified before observing out-of-sample results.
- Multiple testing and selection bias remain present when many configurations
  are evaluated.
- Expensive stochastic experiments should use explicit random seeds or common
  random numbers when comparisons require low Monte Carlo noise.
- A large Cartesian product can be computationally expensive; use
  `max_evaluations`, coarse-to-fine grids, or fixed slices.
