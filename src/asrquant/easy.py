"""One-import facade for loading, visualizing, saving, and reporting."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import pandas as pd


@dataclass
class PlotHandle:
    """Backend-neutral handle returned by :func:`visualize`."""

    object: Any

    @property
    def raw(self) -> Any:
        """Access the underlying backend object for exceptional advanced use."""
        return self.object

    def show(self) -> "PlotHandle":
        obj = self.object
        if hasattr(obj, "show") and callable(obj.show):
            obj.show()
            return self
        try:
            import matplotlib.pyplot as plt
            plt.show()
        except Exception as exc:  # pragma: no cover - environment dependent
            raise RuntimeError("the current environment cannot display this visualization") from exc
        return self

    def save(self, path: str | Path, **kwargs: Any) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        obj = self.object
        suffix = output.suffix.lower()
        if hasattr(obj, "write_html") and suffix in {".html", ".htm"}:
            obj.write_html(str(output), **kwargs)
        elif hasattr(obj, "write_image") and suffix in {".png", ".jpg", ".jpeg", ".svg", ".pdf", ".webp"}:
            obj.write_image(str(output), **kwargs)
        elif hasattr(obj, "savefig"):
            obj.savefig(output, bbox_inches="tight", **kwargs)
        elif hasattr(obj, "figure") and hasattr(obj.figure, "savefig"):
            obj.figure.savefig(output, bbox_inches="tight", **kwargs)
        else:
            raise TypeError(f"unsupported visualization object: {type(obj).__name__}")
        return output

    def close(self) -> None:
        obj = self.object
        try:
            import matplotlib.pyplot as plt
            figure = obj if hasattr(obj, "savefig") else getattr(obj, "figure", None)
            if figure is not None:
                plt.close(figure)
        except Exception:
            return


def visualize(value: Any, kind: str | None = None, **kwargs: Any) -> PlotHandle:
    """Create or wrap a visualization without importing a plotting library.

    ``value`` may be an ASRQuant result object exposing ``plot()``, or an
    already-created Matplotlib/Plotly figure.  This keeps the one-import API
    consistent for both result-driven and low-level visualization workflows.
    """
    if hasattr(value, "plot") and callable(value.plot):
        if kind is None:
            rendered = value.plot(**kwargs)
        else:
            rendered = value.plot(kind=kind, **kwargs)
        return PlotHandle(rendered)

    # Already-rendered backend object (Matplotlib figure/axes, Plotly figure).
    if any(
        hasattr(value, attribute)
        for attribute in ("savefig", "write_html", "write_image", "figure")
    ):
        if kind is not None or kwargs:
            raise TypeError(
                "kind/plot arguments cannot be applied to an already-rendered figure"
            )
        return PlotHandle(value)

    raise TypeError(
        f"{type(value).__name__} is neither an ASRQuant plottable result nor a figure"
    )


def save(
    value: Any,
    path: str | Path,
    kind: str | None = None,
    *,
    plot_kwargs: dict[str, Any] | None = None,
    save_kwargs: dict[str, Any] | None = None,
    **kwargs: Any,
) -> Path:
    """Visualize and save in one call using the file suffix as the format.

    Common export arguments such as ``dpi`` and ``transparent`` are routed to
    the backend save operation. Plot-specific arguments can be supplied with
    ``plot_kwargs`` and export-specific arguments with ``save_kwargs``.
    """
    plot_options = dict(plot_kwargs or {})
    export_options = dict(save_kwargs or {})
    export_keys = {"dpi", "transparent", "format", "quality", "scale", "width", "height"}
    for key, value_option in kwargs.items():
        (export_options if key in export_keys else plot_options)[key] = value_option
    return visualize(value, kind=kind, **plot_options).save(path, **export_options)


def show(value: Any, kind: str | None = None, **kwargs: Any) -> PlotHandle:
    """Visualize and display in one call."""
    return visualize(value, kind=kind, **kwargs).show()


def report(value: Any, output: str | Path, *, title: str | None = None) -> Path:
    """Create a report from a compatible ASRQuant result object."""
    if not hasattr(value, "report"):
        raise TypeError(f"{type(value).__name__} does not provide a report() method")
    value.report(str(output), title=title)
    return Path(output)


def open_lab(
    source: Any = None,
    *,
    provider: str | None = None,
    symbols: str | Sequence[str] | None = None,
    date_column: str | None = None,
    columns: Sequence[str] | None = None,
    missing_data: str = "raise",
    **kwargs: Any,
):
    """Create a QuantLab from in-memory data, a file, or a market-data provider."""
    from .api import QuantLab

    if provider is not None:
        if symbols is None:
            raise ValueError("symbols are required when provider is specified")
        return QuantLab.from_provider(
            provider,
            symbols,
            missing_data=missing_data,
            **kwargs,
        )
    if source is None:
        raise ValueError("provide in-memory data, a file path, or provider=... with symbols=...")
    if isinstance(source, (str, Path)):
        return QuantLab.from_file(
            source,
            date_column=date_column,
            columns=columns,
            missing_data=missing_data,
            **kwargs,
        )
    return QuantLab(source, missing_data=missing_data)


def fit(
    x: Any,
    y: Any,
    *,
    method: str = "ols",
    degree: int = 2,
    **kwargs: Any,
):
    """Fit a common statistical model from plain Python or pandas inputs.

    Examples
    --------
    >>> model = fit([-2, -1, 0, 1, 2], [4, 1, 0, 1, 4], method="polynomial", degree=2)
    >>> model.coefficients

    The function is intentionally small: it normalizes list/array inputs and
    dispatches to the audited estimators in :mod:`asrquant.statistics`.
    """
    from . import statistics as stats

    if isinstance(x, pd.DataFrame):
        x_frame = x.copy()
    elif isinstance(x, pd.Series):
        x_frame = x.to_frame(name=x.name or "x")
    elif isinstance(x, dict):
        x_frame = pd.DataFrame(x)
    else:
        x_frame = pd.DataFrame({"x": list(x)})

    if isinstance(y, pd.Series):
        y_series = y.copy()
        if not y_series.index.equals(x_frame.index):
            y_series = pd.Series(y_series.to_numpy(), index=x_frame.index, name=y_series.name or "y")
    else:
        y_series = pd.Series(list(y), index=x_frame.index, name="y")

    if len(x_frame) != len(y_series):
        raise ValueError("x and y must contain the same number of observations")

    key = method.lower().strip().replace("-", "_").replace(" ", "_")
    if key in {"ols", "linear", "linear_regression"}:
        return stats.ols(y_series, x_frame, **kwargs)
    if key in {"polynomial", "polynomial_regression", "poly"}:
        return stats.polynomial_regression(
            y_series, x_frame, degree=degree, **kwargs
        )
    if key in {"quantile", "quantile_regression"}:
        return stats.quantile_regression(y_series, x_frame, **kwargs)
    if key in {"logistic", "logistic_regression"}:
        return stats.logistic_regression(y_series, x_frame, **kwargs)
    raise ValueError(
        "method must be ols, polynomial, quantile, or logistic"
    )


def frame(data: Any = None, *, index: Any = None, columns: Any = None) -> pd.DataFrame:
    """Construct a DataFrame through ASRQuant for one-import workflows."""
    return pd.DataFrame(data=data, index=index, columns=columns)


def series(data: Any = None, *, index: Any = None, name: str | None = None) -> pd.Series:
    """Construct a Series through ASRQuant for one-import workflows."""
    return pd.Series(data=data, index=index, name=name)


def read_table(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    """Read a general tabular file without importing pandas directly."""
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix in {".csv", ".txt"}:
        return pd.read_csv(source, **kwargs)
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(source, **kwargs)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(source, **kwargs)
    if suffix == ".json":
        return pd.read_json(source, **kwargs)
    if suffix in {".feather", ".ft"}:
        return pd.read_feather(source, **kwargs)
    raise ValueError(f"unsupported table format: {suffix}")


def date_range(start: Any = None, end: Any = None, periods: int | None = None, freq: str | None = None):
    return pd.date_range(start=start, end=end, periods=periods, freq=freq)


__all__ = [
    "PlotHandle", "visualize", "save", "show", "report", "open_lab", "fit",
    "frame", "series", "read_table", "date_range",
]
