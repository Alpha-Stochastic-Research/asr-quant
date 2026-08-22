"""Generic response surfaces and parameter animations for quantitative research.

The module evaluates any scalar-valued experiment on a finite parameter grid.
Two selected parameters are rendered as the x/y axes. Any number of remaining
parameters may be fixed or flattened into animation frames.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from itertools import product
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import pandas as pd
from matplotlib import animation

from .viz import general


ArrayLike = Sequence[Any] | np.ndarray | pd.Index | pd.Series
MetricSelector = str | Callable[[Any], float] | None
ProgressCallback = Callable[[int, int, Mapping[str, Any], float], None]


def _as_numeric_axis(values: ArrayLike, name: str) -> np.ndarray:
    out = np.asarray(list(values) if not isinstance(values, np.ndarray) else values)
    if out.ndim != 1 or out.size == 0:
        raise ValueError(f"{name} must be a non-empty one-dimensional sequence")
    try:
        return out.astype(float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must contain numeric values for a geometric surface axis") from exc


def _as_parameter_values(values: ArrayLike, name: str) -> list[Any]:
    if isinstance(values, (str, bytes)):
        raise ValueError(f"{name} must be a sequence, not a string")
    out = list(values)
    if not out:
        raise ValueError(f"{name} must be non-empty")
    return out


def _python_scalar(value: Any) -> Any:
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and value.is_integer():
        return int(round(value))
    return value


def _format_value(value: Any) -> str:
    value = _python_scalar(value)
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def _extract_metric(result: Any, selector: MetricSelector) -> float:
    """Extract one scalar from a result object, mapping, pandas object, or callable."""
    if callable(selector):
        return float(selector(result))
    if selector is None:
        if np.isscalar(result):
            return float(result)
        if isinstance(result, np.ndarray) and result.size == 1:
            return float(result.reshape(-1)[0])
        raise TypeError(
            "the experiment returned a non-scalar result; pass metric='name', "
            "metric='metrics.Sharpe', or metric=lambda result: ..."
        )

    current = result
    for part in str(selector).split("."):
        if isinstance(current, Mapping):
            if part not in current:
                raise KeyError(f"metric path component {part!r} was not found")
            current = current[part]
        elif isinstance(current, pd.Series):
            if part not in current.index:
                raise KeyError(f"metric path component {part!r} was not found")
            current = current.loc[part]
        else:
            if not hasattr(current, part):
                raise AttributeError(f"metric path component {part!r} was not found")
            current = getattr(current, part)
    if isinstance(current, pd.Series) and len(current) == 1:
        current = current.iloc[0]
    if isinstance(current, np.ndarray) and current.size == 1:
        current = current.reshape(-1)[0]
    return float(current)


def _frame_label(row: Mapping[str, Any]) -> str:
    return ", ".join(f"{key}={_format_value(value)}" for key, value in row.items())


@dataclass
class SurfaceResult:
    """Static or animated response surface.

    ``x_values`` and ``y_values`` define the displayed surface. ``z_values`` is
    either a matrix ``(n_y, n_x)`` or a tensor ``(n_frames, n_y, n_x)``.
    ``frame_parameters`` stores all parameter combinations represented by the
    animation and may contain several columns.
    """

    x_values: np.ndarray
    y_values: np.ndarray
    z_values: np.ndarray
    x_name: str = "x"
    y_name: str = "y"
    z_name: str = "value"
    frame_values: np.ndarray | None = None
    frame_name: str | None = None
    frame_parameters: pd.DataFrame | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.x_values = _as_numeric_axis(self.x_values, "x_values")
        self.y_values = _as_numeric_axis(self.y_values, "y_values")
        self.z_values = np.asarray(self.z_values, dtype=float)

        if self.frame_parameters is None and self.frame_values is not None:
            values = _as_parameter_values(self.frame_values, "frame_values")
            self.frame_parameters = pd.DataFrame({self.frame_name or "frame": values})
        elif self.frame_parameters is not None:
            self.frame_parameters = pd.DataFrame(self.frame_parameters).reset_index(drop=True)
            if self.frame_parameters.shape[1] == 0:
                self.frame_parameters = None

        if self.frame_parameters is not None:
            if self.frame_name is None and len(self.frame_parameters.columns) == 1:
                self.frame_name = str(self.frame_parameters.columns[0])
            if len(self.frame_parameters.columns) == 1:
                self.frame_values = self.frame_parameters.iloc[:, 0].to_numpy()
            expected = (len(self.frame_parameters), len(self.y_values), len(self.x_values))
            if self.z_values.shape != expected:
                raise ValueError(f"animated z_values must have shape {expected}, got {self.z_values.shape}")
        else:
            self.frame_values = None
            expected = (len(self.y_values), len(self.x_values))
            if self.z_values.shape != expected:
                raise ValueError(f"static z_values must have shape {expected}, got {self.z_values.shape}")

    @property
    def is_animated(self) -> bool:
        return self.frame_parameters is not None

    @property
    def frame_count(self) -> int:
        return int(len(self.frame_parameters)) if self.is_animated else 1

    @property
    def frame_labels(self) -> list[str]:
        if not self.is_animated:
            return [""]
        return [_frame_label(row) for row in self.frame_parameters.to_dict(orient="records")]

    def parameters_at(self, index: int) -> dict[str, Any]:
        if not self.is_animated:
            return {}
        idx = self._normalize_frame_index(index)
        return {str(k): _python_scalar(v) for k, v in self.frame_parameters.iloc[idx].to_dict().items()}

    def _normalize_frame_index(self, index: int) -> int:
        idx = int(index)
        if idx < 0:
            idx += self.frame_count
        if not 0 <= idx < self.frame_count:
            raise IndexError("frame index out of range")
        return idx

    def frame(self, index: int = 0) -> "SurfaceResult":
        if not self.is_animated:
            if index not in {0, -1}:
                raise IndexError("static surface has only one frame")
            return self
        idx = self._normalize_frame_index(index)
        metadata = dict(self.metadata)
        metadata.update({"frame_index": idx, "frame_parameters": self.parameters_at(idx)})
        return SurfaceResult(
            x_values=self.x_values,
            y_values=self.y_values,
            z_values=self.z_values[idx],
            x_name=self.x_name,
            y_name=self.y_name,
            z_name=self.z_name,
            metadata=metadata,
        )

    @property
    def summary(self) -> pd.Series:
        values = self.z_values.reshape(-1)
        finite = values[np.isfinite(values)]
        info: dict[str, Any] = {
            "x_points": len(self.x_values),
            "y_points": len(self.y_values),
            "frames": self.frame_count,
            "evaluations": int(values.size),
            "finite_values": int(finite.size),
            "missing_values": int(values.size - finite.size),
            "z_min": float(np.min(finite)) if finite.size else np.nan,
            "z_max": float(np.max(finite)) if finite.size else np.nan,
            "z_mean": float(np.mean(finite)) if finite.size else np.nan,
            "z_std": float(np.std(finite, ddof=1)) if finite.size > 1 else 0.0,
        }
        if self.is_animated:
            info["frame_parameters"] = ", ".join(map(str, self.frame_parameters.columns))
        return pd.Series(info)

    def to_frame(self, frame: int | None = None) -> pd.DataFrame:
        selected = self.frame(0 if frame is None else frame) if self.is_animated else self
        out = pd.DataFrame(selected.z_values, index=selected.y_values, columns=selected.x_values)
        out.index.name = self.y_name
        out.columns.name = self.x_name
        return out

    def to_long_frame(self) -> pd.DataFrame:
        """Return all evaluated values as a tidy long-form dataframe."""
        rows: list[pd.DataFrame] = []
        frame_indices = range(self.frame_count) if self.is_animated else [0]
        for idx in frame_indices:
            selected = self.frame(idx) if self.is_animated else self
            xx, yy = np.meshgrid(selected.x_values, selected.y_values)
            wide = pd.DataFrame({
                self.x_name: xx.reshape(-1),
                self.y_name: yy.reshape(-1),
                self.z_name: selected.z_values.reshape(-1),
            })
            if self.is_animated:
                for name, value in self.parameters_at(idx).items():
                    wide[name] = value
            rows.append(wide)
        return pd.concat(rows, ignore_index=True)

    def best(self, mode: str = "max", *, frame: int | None = None) -> pd.Series:
        """Return the coordinates and parameters of the best finite point."""
        if mode not in {"max", "min"}:
            raise ValueError("mode must be 'max' or 'min'")
        if frame is not None:
            candidates = self.frame(frame).to_long_frame()
            if self.is_animated:
                for name, value in self.parameters_at(frame).items():
                    candidates[name] = value
        else:
            candidates = self.to_long_frame()
        finite = candidates[np.isfinite(candidates[self.z_name].astype(float))]
        if finite.empty:
            raise ValueError("surface contains no finite values")
        idx = finite[self.z_name].idxmax() if mode == "max" else finite[self.z_name].idxmin()
        return finite.loc[idx]

    def gradient(self, *, frame: int | None = None):
        """Return first-order sensitivity surfaces along the displayed axes."""
        from .approximation import surface_gradient
        return surface_gradient(self, frame=frame)

    def hessian(self, *, frame: int | None = None):
        """Return second-order and cross-curvature surfaces."""
        from .approximation import surface_hessian
        return surface_hessian(self, frame=frame)

    def plot(
        self,
        kind: str = "surface",
        *,
        frame: int = 0,
        title: str | None = None,
        interactive: bool = False,
    ):
        selected = self.frame(frame) if self.is_animated else self
        suffix = f" | {self.frame_labels[self._normalize_frame_index(frame)]}" if self.is_animated else ""
        title = title or f"{self.z_name} surface{suffix}"
        if kind in {"surface", "surface3d", "3d"}:
            return general.surface3d(
                selected.x_values,
                selected.y_values,
                selected.z_values,
                title=title,
                x_label=self.x_name,
                y_label=self.y_name,
                z_label=self.z_name,
                interactive=interactive,
            )
        if kind in {"heatmap", "image"}:
            return general.response_heatmap(
                selected.x_values,
                selected.y_values,
                selected.z_values,
                title=title,
                x_label=self.x_name,
                y_label=self.y_name,
                z_label=self.z_name,
            )
        if kind in {"contour", "contours"}:
            return general.contour(
                selected.x_values,
                selected.y_values,
                selected.z_values,
                title=title,
                x_label=self.x_name,
                y_label=self.y_name,
                z_label=self.z_name,
            )
        raise ValueError("kind must be surface, heatmap, or contour")

    def animate(
        self,
        *,
        kind: str = "surface",
        interval: int = 250,
        repeat: bool = True,
        title: str | None = None,
        stable_scale: bool = True,
        elevation: float = 30.0,
        azimuth: float = -60.0,
        rotate_camera: float = 0.0,
    ):
        if not self.is_animated:
            raise ValueError("surface is static; use plot() instead")
        return general.animate_surface(
            self.x_values,
            self.y_values,
            self.z_values,
            frame_values=self.frame_values,
            frame_labels=self.frame_labels,
            x_label=self.x_name,
            y_label=self.y_name,
            z_label=self.z_name,
            frame_label=self.frame_name or "parameters",
            interval=interval,
            repeat=repeat,
            kind=kind,
            title=title or self.z_name,
            stable_scale=stable_scale,
            elevation=elevation,
            azimuth=azimuth,
            rotate_camera=rotate_camera,
        )

    def to_plotly_animation(self, *, kind: str = "surface", title: str | None = None):
        """Create an interactive Plotly animation with a frame slider."""
        if not self.is_animated:
            return self.plot(kind=kind, interactive=kind in {"surface", "surface3d", "3d"}, title=title)
        import plotly.graph_objects as go

        xx, yy = np.meshgrid(self.x_values, self.y_values)
        kind_key = kind.lower()

        def trace(z: np.ndarray):
            if kind_key in {"surface", "surface3d", "3d"}:
                return go.Surface(x=xx, y=yy, z=z, colorbar={"title": self.z_name})
            if kind_key in {"heatmap", "image"}:
                return go.Heatmap(x=self.x_values, y=self.y_values, z=z, colorbar={"title": self.z_name})
            if kind_key in {"contour", "contours"}:
                return go.Contour(x=self.x_values, y=self.y_values, z=z, colorbar={"title": self.z_name})
            raise ValueError("kind must be surface, heatmap, or contour")

        frames = [
            go.Frame(data=[trace(self.z_values[i])], name=str(i), layout={"title": f"{title or self.z_name} | {self.frame_labels[i]}"})
            for i in range(self.frame_count)
        ]
        fig = go.Figure(data=[trace(self.z_values[0])], frames=frames)
        steps = [
            {
                "method": "animate",
                "label": self.frame_labels[i],
                "args": [[str(i)], {"mode": "immediate", "frame": {"duration": 0, "redraw": True}, "transition": {"duration": 0}}],
            }
            for i in range(self.frame_count)
        ]
        buttons = [{
            "type": "buttons",
            "buttons": [
                {"label": "Play", "method": "animate", "args": [None, {"fromcurrent": True, "frame": {"duration": 250, "redraw": True}}]},
                {"label": "Pause", "method": "animate", "args": [[None], {"mode": "immediate", "frame": {"duration": 0, "redraw": False}}]},
            ],
        }]
        layout: dict[str, Any] = {
            "title": f"{title or self.z_name} | {self.frame_labels[0]}",
            "sliders": [{"steps": steps, "active": 0, "currentvalue": {"prefix": "Parameters: "}}],
            "updatemenus": buttons,
        }
        if kind_key in {"surface", "surface3d", "3d"}:
            layout["scene"] = {"xaxis_title": self.x_name, "yaxis_title": self.y_name, "zaxis_title": self.z_name}
        else:
            layout.update({"xaxis_title": self.x_name, "yaxis_title": self.y_name})
        fig.update_layout(**layout)
        return fig

    def save_animation(
        self,
        path: str | Path,
        *,
        kind: str = "surface",
        interval: int = 250,
        repeat: bool = True,
        fps: int | None = None,
        backend: str = "auto",
        stable_scale: bool = True,
        rotate_camera: float = 0.0,
    ) -> Path:
        """Save an animation as interactive HTML, GIF, or MP4.

        HTML defaults to Plotly because it provides a parameter slider and camera
        controls. GIF and MP4 use Matplotlib writers.
        """
        if not self.is_animated:
            raise ValueError("surface is static; use plot() instead")
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        suffix = destination.suffix.lower()
        selected_backend = "plotly" if backend == "auto" and suffix == ".html" else ("matplotlib" if backend == "auto" else backend)

        if suffix == ".html" and selected_backend == "plotly":
            fig = self.to_plotly_animation(kind=kind)
            fig.write_html(str(destination), include_plotlyjs=True, full_html=True)
            return destination

        anim = self.animate(
            kind=kind,
            interval=interval,
            repeat=repeat,
            stable_scale=stable_scale,
            rotate_camera=rotate_camera,
        )
        effective_fps = fps or max(1, round(1000 / max(interval, 1)))
        if suffix == ".html":
            destination.write_text(anim.to_jshtml(fps=effective_fps), encoding="utf-8")
            return destination
        if suffix == ".gif":
            anim.save(destination, writer=animation.PillowWriter(fps=effective_fps))
            return destination
        if suffix == ".mp4":
            if not animation.writers.is_available("ffmpeg"):
                raise RuntimeError("FFmpeg is required to export MP4; use HTML or GIF when FFmpeg is unavailable")
            anim.save(destination, writer=animation.FFMpegWriter(fps=effective_fps))
            return destination
        raise ValueError("animation path must end with .html, .gif, or .mp4")

    def export_frames(self, directory: str | Path, *, kind: str = "surface", prefix: str = "frame") -> list[Path]:
        """Export each frame as a static image for reports or external video tools."""
        destination = Path(directory)
        destination.mkdir(parents=True, exist_ok=True)
        outputs: list[Path] = []
        frame_indices = range(self.frame_count) if self.is_animated else [0]
        for idx in frame_indices:
            fig = self.plot(kind=kind, frame=idx)
            stem = f"{prefix}_{idx:03d}.png" if self.is_animated else f"{prefix}.png"
            path = destination / stem
            if hasattr(fig, "write_image"):
                fig.write_image(str(path))
            else:
                fig.savefig(path, dpi=150, bbox_inches="tight")
            outputs.append(path)
        return outputs


def _call_experiment(
    function: Callable[..., Any],
    params: Mapping[str, Any],
    *,
    ordered_names: Sequence[str],
    fixed_params: Mapping[str, Any],
    call_style: str,
    metric: MetricSelector,
) -> float:
    merged = dict(fixed_params)
    merged.update(params)
    if call_style == "keyword":
        result = function(**merged)
    elif call_style == "positional":
        positional = [_python_scalar(merged[name]) for name in ordered_names]
        extra = {k: v for k, v in fixed_params.items() if k not in ordered_names}
        result = function(*positional, **extra)
    else:
        raise ValueError("call_style must be keyword or positional")
    return _extract_metric(result, metric)


def evaluate_parameter_surface(
    function: Callable[..., Any],
    parameter_grid: Mapping[str, ArrayLike],
    *,
    x: str | None = None,
    y: str | None = None,
    animate_by: str | Sequence[str] | None = None,
    z_name: str = "value",
    metric: MetricSelector = None,
    fixed_params: Mapping[str, Any] | None = None,
    vectorized: bool = False,
    call_style: str = "keyword",
    n_jobs: int = 1,
    error_policy: str = "raise",
    max_evaluations: int = 1_000_000,
    progress: ProgressCallback | None = None,
) -> SurfaceResult:
    """Evaluate an arbitrary finite parameter experiment as a surface family.

    Parameters
    ----------
    parameter_grid
        Mapping from parameter names to candidate values. At least two parameters
        are required. ``x`` and ``y`` select the displayed axes. Every other grid
        parameter is animated by default; pass ``animate_by=[]`` and put values in
        ``fixed_params`` to obtain a single slice.
    metric
        Scalar selector. It may be a callable, ``"Sharpe"`` for a mapping/Series,
        or a dotted path such as ``"metrics.Sharpe"`` for a result object.
    n_jobs
        Number of threads used for non-vectorized scalar evaluations.
    error_policy
        ``"raise"`` stops at the first failed point; ``"nan"`` records NaN and
        stores error details in ``result.metadata['errors']``.
    """
    if not isinstance(parameter_grid, Mapping) or len(parameter_grid) < 2:
        raise ValueError("parameter_grid must contain at least two named parameters")
    grids = {str(name): _as_parameter_values(values, str(name)) for name, values in parameter_grid.items()}
    names = list(grids)
    x_name = x or names[0]
    y_name = y or names[1]
    if x_name == y_name:
        raise ValueError("x and y must identify different parameters")
    for selected in (x_name, y_name):
        if selected not in grids:
            raise KeyError(f"axis parameter {selected!r} is not present in parameter_grid")

    if animate_by is None:
        frame_names = [name for name in names if name not in {x_name, y_name}]
    elif isinstance(animate_by, str):
        frame_names = [animate_by]
    else:
        frame_names = [str(name) for name in animate_by]
    if len(frame_names) != len(set(frame_names)):
        raise ValueError("animate_by contains duplicate parameter names")
    invalid_frames = [name for name in frame_names if name not in grids or name in {x_name, y_name}]
    if invalid_frames:
        raise ValueError(f"invalid animation parameters: {invalid_frames}")

    fixed = dict(fixed_params or {})
    unused = [name for name in names if name not in {x_name, y_name, *frame_names}]
    for name in unused:
        if name in fixed:
            continue
        if len(grids[name]) == 1:
            fixed[name] = grids[name][0]
        else:
            raise ValueError(
                f"parameter {name!r} has multiple values but is neither an axis nor animated; "
                "add it to animate_by or provide fixed_params"
            )

    x_values = _as_numeric_axis(grids[x_name], x_name)
    y_values = _as_numeric_axis(grids[y_name], y_name)
    frame_rows = [dict(zip(frame_names, values)) for values in product(*(grids[name] for name in frame_names))] if frame_names else [{}]
    total = len(x_values) * len(y_values) * len(frame_rows)
    if total > int(max_evaluations):
        raise ValueError(f"surface requires {total:,} evaluations, above max_evaluations={max_evaluations:,}")
    if n_jobs < 1:
        raise ValueError("n_jobs must be at least 1")
    if error_policy not in {"raise", "nan"}:
        raise ValueError("error_policy must be 'raise' or 'nan'")
    if vectorized and n_jobs != 1:
        raise ValueError("vectorized=True cannot be combined with n_jobs != 1")

    errors: list[dict[str, Any]] = []
    completed = 0
    cube: list[np.ndarray] = []
    ordered_names = [x_name, y_name, *frame_names]

    for frame_idx, frame_params in enumerate(frame_rows):
        if vectorized:
            xx, yy = np.meshgrid(x_values, y_values)
            params = dict(frame_params)
            params[x_name] = xx
            params[y_name] = yy
            try:
                merged = dict(fixed)
                merged.update(params)
                if call_style == "keyword":
                    raw = function(**merged)
                elif call_style == "positional":
                    raw = function(xx, yy, *[_python_scalar(frame_params[name]) for name in frame_names], **fixed)
                else:
                    raise ValueError("call_style must be keyword or positional")
                matrix = np.asarray(raw if metric is None else _extract_metric(raw, metric), dtype=float)
                if matrix.shape != (len(y_values), len(x_values)):
                    raise ValueError(
                        f"vectorized function must return shape {(len(y_values), len(x_values))}, got {matrix.shape}"
                    )
            except Exception as exc:
                if error_policy == "raise":
                    raise
                matrix = np.full((len(y_values), len(x_values)), np.nan)
                errors.append({"frame": frame_idx, **frame_params, "error": repr(exc)})
            cube.append(matrix)
            completed += matrix.size
            if progress is not None:
                progress(completed, total, frame_params, float(np.nanmean(matrix)))
            continue

        jobs: list[tuple[int, int, dict[str, Any]]] = []
        for i, yv in enumerate(y_values):
            for j, xv in enumerate(x_values):
                params = {x_name: _python_scalar(xv), y_name: _python_scalar(yv), **frame_params}
                jobs.append((i, j, params))

        def evaluate(job: tuple[int, int, dict[str, Any]]) -> tuple[int, int, dict[str, Any], float, str | None]:
            i, j, params = job
            try:
                value = _call_experiment(
                    function,
                    params,
                    ordered_names=ordered_names,
                    fixed_params=fixed,
                    call_style=call_style,
                    metric=metric,
                )
                return i, j, params, value, None
            except Exception as exc:  # captured only when error_policy='nan'
                if error_policy == "raise":
                    raise
                return i, j, params, np.nan, repr(exc)

        matrix = np.empty((len(y_values), len(x_values)), dtype=float)

        def consume(iterator):
            nonlocal completed
            for i, j, params, value, error in iterator:
                matrix[i, j] = value
                completed += 1
                if error is not None:
                    errors.append({**params, "error": error})
                if progress is not None:
                    progress(completed, total, params, value)

        if n_jobs == 1:
            consume(map(evaluate, jobs))
        else:
            with ThreadPoolExecutor(max_workers=n_jobs) as executor:
                consume(executor.map(evaluate, jobs))
        cube.append(matrix)

    metadata = {
        "call_style": call_style,
        "vectorized": vectorized,
        "n_jobs": n_jobs,
        "metric": metric if isinstance(metric, str) else getattr(metric, "__name__", None),
        "fixed_params": fixed,
        "parameter_order": names,
        "x_parameter": x_name,
        "y_parameter": y_name,
        "animated_parameters": frame_names,
        "evaluations": total,
        "errors": errors,
    }
    if frame_names:
        frame_table = pd.DataFrame(frame_rows, columns=frame_names)
        return SurfaceResult(
            x_values=x_values,
            y_values=y_values,
            z_values=np.asarray(cube, dtype=float),
            x_name=x_name,
            y_name=y_name,
            z_name=z_name,
            frame_parameters=frame_table,
            frame_name=frame_names[0] if len(frame_names) == 1 else "parameters",
            metadata=metadata,
        )
    return SurfaceResult(
        x_values=x_values,
        y_values=y_values,
        z_values=cube[0],
        x_name=x_name,
        y_name=y_name,
        z_name=z_name,
        metadata=metadata,
    )


def surface_from_dataframe(
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
    agg: str | Callable[[pd.Series], float] = "mean",
) -> SurfaceResult:
    """Build a static or animated surface from long-form experiment results."""
    if frame_col is not None and frame_cols is not None:
        raise ValueError("use frame_col or frame_cols, not both")
    group_cols = list(frame_cols or ([frame_col] if frame_col else []))
    required = [x, y, z, *group_cols]
    missing = [col for col in required if col not in frame.columns]
    if missing:
        raise ValueError(f"missing columns: {missing}")
    x_label = x_name or x
    y_label = y_name or y
    z_label = z_name or z

    x_values = np.sort(pd.to_numeric(frame[x].dropna().unique()))
    y_values = np.sort(pd.to_numeric(frame[y].dropna().unique()))

    def matrix_for(data: pd.DataFrame) -> np.ndarray:
        pivot = data.pivot_table(index=y, columns=x, values=z, aggfunc=agg)
        pivot = pivot.reindex(index=y_values, columns=x_values)
        return np.asarray(pivot.values, dtype=float)

    if not group_cols:
        return SurfaceResult(x_values, y_values, matrix_for(frame), x_name=x_label, y_name=y_label, z_name=z_label)

    grouped = frame.groupby(group_cols, dropna=False, sort=True)
    rows: list[dict[str, Any]] = []
    matrices: list[np.ndarray] = []
    for key, subset in grouped:
        values = key if isinstance(key, tuple) else (key,)
        rows.append(dict(zip(group_cols, values)))
        matrices.append(matrix_for(subset))
    return SurfaceResult(
        x_values=x_values,
        y_values=y_values,
        z_values=np.asarray(matrices, dtype=float),
        x_name=x_label,
        y_name=y_label,
        z_name=z_label,
        frame_parameters=pd.DataFrame(rows, columns=group_cols),
        frame_name=frame_name or (group_cols[0] if len(group_cols) == 1 else "parameters"),
    )


def evaluate_surface(
    function: Callable[..., Any],
    x_values: ArrayLike,
    y_values: ArrayLike,
    *,
    x_name: str = "x",
    y_name: str = "y",
    z_name: str = "value",
    metric: MetricSelector = None,
    fixed_params: Mapping[str, Any] | None = None,
    vectorized: bool = False,
    call_style: str = "keyword",
    n_jobs: int = 1,
    error_policy: str = "raise",
) -> SurfaceResult:
    """Backward-compatible two-dimensional surface evaluator."""
    return evaluate_parameter_surface(
        function,
        {x_name: x_values, y_name: y_values},
        x=x_name,
        y=y_name,
        animate_by=[],
        z_name=z_name,
        metric=metric,
        fixed_params=fixed_params,
        vectorized=vectorized,
        call_style=call_style,
        n_jobs=n_jobs,
        error_policy=error_policy,
    )


def evaluate_surface_animation(
    function: Callable[..., Any],
    x_values: ArrayLike,
    y_values: ArrayLike,
    frame_values: ArrayLike,
    *,
    x_name: str = "x",
    y_name: str = "y",
    frame_name: str = "frame",
    z_name: str = "value",
    metric: MetricSelector = None,
    fixed_params: Mapping[str, Any] | None = None,
    vectorized: bool = False,
    call_style: str = "keyword",
    n_jobs: int = 1,
    error_policy: str = "raise",
) -> SurfaceResult:
    """Backward-compatible one-parameter animation evaluator."""
    return evaluate_parameter_surface(
        function,
        {x_name: x_values, y_name: y_values, frame_name: frame_values},
        x=x_name,
        y=y_name,
        animate_by=[frame_name],
        z_name=z_name,
        metric=metric,
        fixed_params=fixed_params,
        vectorized=vectorized,
        call_style=call_style,
        n_jobs=n_jobs,
        error_policy=error_policy,
    )
