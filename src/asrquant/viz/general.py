"""Generic 2D/3D response surfaces and parameter landscapes."""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import animation

from .base import finalize


def surface3d(
    x,
    y,
    z,
    title: str = "3D surface",
    x_label: str = "x",
    y_label: str = "y",
    z_label: str = "z",
    interactive: bool = False,
):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    z = np.asarray(z, dtype=float)
    if z.shape == (len(y), len(x)):
        xx, yy = np.meshgrid(x, y)
    elif x.shape == y.shape == z.shape:
        xx, yy = x, y
    else:
        raise ValueError("z must be a matrix shaped (len(y), len(x)) or x, y, z must share a shape")
    if interactive:
        import plotly.graph_objects as go
        fig = go.Figure(data=[go.Surface(x=xx, y=yy, z=z)])
        fig.update_layout(title=title, scene={"xaxis_title": x_label, "yaxis_title": y_label, "zaxis_title": z_label})
        return fig
    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_surface(xx, yy, z, cmap=None, alpha=0.85)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_zlabel(z_label)
    ax.set_title(title)
    return finalize(fig)


def response_heatmap(x, y, z, title: str = "Response heatmap", x_label: str = "x", y_label: str = "y", z_label: str = "z"):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    z = np.asarray(z, dtype=float)
    if z.shape != (len(y), len(x)):
        raise ValueError("z must have shape (len(y), len(x))")
    fig, ax = plt.subplots(figsize=(8.5, 6.5))
    image = ax.imshow(z, aspect="auto", origin="lower", extent=[x.min(), x.max(), y.min(), y.max()])
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title)
    cbar = fig.colorbar(image, ax=ax)
    cbar.set_label(z_label)
    return finalize(fig)


def parameter_heatmap(results: pd.DataFrame, x: str, y: str, metric: str):
    table = results.pivot_table(index=y, columns=x, values=metric, aggfunc="mean")
    fig, ax = plt.subplots(figsize=(8, 6))
    image = ax.imshow(table, aspect="auto")
    ax.set_xticks(range(len(table.columns)), table.columns)
    ax.set_yticks(range(len(table.index)), table.index)
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    ax.set_title(f"{metric} parameter landscape")
    for i in range(len(table)):
        for j in range(len(table.columns)):
            ax.text(j, i, f"{table.iloc[i, j]:.3g}", ha="center", va="center", fontsize=8)
    fig.colorbar(image, ax=ax)
    return finalize(fig)


def contour(x, y, z, title: str = "Contour map", x_label: str = "x", y_label: str = "y", z_label: str = "z"):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    z = np.asarray(z, dtype=float)
    if z.shape != (len(y), len(x)):
        raise ValueError("z must have shape (len(y), len(x))")
    xx, yy = np.meshgrid(x, y)
    fig, ax = plt.subplots(figsize=(8, 6))
    contours = ax.contourf(xx, yy, z)
    fig.colorbar(contours, ax=ax, label=z_label)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title)
    return finalize(fig)


def animate_surface(
    x,
    y,
    z_frames,
    *,
    frame_values=None,
    frame_labels=None,
    x_label: str = "x",
    y_label: str = "y",
    z_label: str = "z",
    frame_label: str = "parameter",
    kind: str = "surface",
    title: str = "Animated surface",
    interval: int = 250,
    repeat: bool = True,
    stable_scale: bool = True,
    elevation: float = 30.0,
    azimuth: float = -60.0,
    rotate_camera: float = 0.0,
):
    """Animate a surface, heatmap, or contour family with stable visual scales."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    z_frames = np.asarray(z_frames, dtype=float)
    if z_frames.ndim != 3 or z_frames.shape[1:] != (len(y), len(x)):
        raise ValueError("z_frames must have shape (n_frames, len(y), len(x))")
    n_frames = z_frames.shape[0]
    if frame_labels is not None:
        labels = [str(label) for label in frame_labels]
        if len(labels) != n_frames:
            raise ValueError("frame_labels must contain one label per frame")
    else:
        values = np.arange(n_frames) if frame_values is None else np.asarray(frame_values, dtype=object)
        if len(values) != n_frames:
            raise ValueError("frame_values must contain one value per frame")
        labels = [f"{frame_label}={value}" for value in values]

    finite = z_frames[np.isfinite(z_frames)]
    z_min = float(np.min(finite)) if finite.size else 0.0
    z_max = float(np.max(finite)) if finite.size else 1.0
    if np.isclose(z_min, z_max):
        margin = max(abs(z_min) * 0.05, 1e-9)
        z_min -= margin
        z_max += margin
    xx, yy = np.meshgrid(x, y)
    kind = kind.lower()

    if kind in {"surface", "surface3d", "3d"}:
        fig = plt.figure(figsize=(10, 7))
        ax = fig.add_subplot(111, projection="3d")

        def draw(i: int):
            ax.clear()
            ax.plot_surface(xx, yy, z_frames[i], cmap=None, alpha=0.85)
            if stable_scale:
                ax.set_zlim(z_min, z_max)
            ax.view_init(elev=elevation, azim=azimuth + rotate_camera * i)
            ax.set_xlabel(x_label)
            ax.set_ylabel(y_label)
            ax.set_zlabel(z_label)
            ax.set_title(f"{title} | {labels[i]}")
            return ax,

    elif kind in {"heatmap", "image"}:
        fig, ax = plt.subplots(figsize=(8.5, 6.5))
        image = ax.imshow(
            z_frames[0],
            aspect="auto",
            origin="lower",
            extent=[x.min(), x.max(), y.min(), y.max()],
            animated=True,
            vmin=z_min if stable_scale else None,
            vmax=z_max if stable_scale else None,
        )
        cbar = fig.colorbar(image, ax=ax)
        cbar.set_label(z_label)

        def draw(i: int):
            image.set_data(z_frames[i])
            if not stable_scale:
                local = z_frames[i][np.isfinite(z_frames[i])]
                if local.size:
                    image.set_clim(float(local.min()), float(local.max()))
            ax.set_xlabel(x_label)
            ax.set_ylabel(y_label)
            ax.set_title(f"{title} | {labels[i]}")
            return image,

    elif kind in {"contour", "contours"}:
        fig, ax = plt.subplots(figsize=(8.5, 6.5))
        levels = np.linspace(z_min, z_max, 20) if stable_scale else 20

        def draw(i: int):
            ax.clear()
            ax.contourf(xx, yy, z_frames[i], levels=levels)
            ax.set_xlabel(x_label)
            ax.set_ylabel(y_label)
            ax.set_title(f"{title} | {labels[i]}")
            return (ax,)

    else:
        raise ValueError("kind must be surface, heatmap, or contour")

    return animation.FuncAnimation(
        fig,
        draw,
        frames=n_frames,
        interval=interval,
        repeat=repeat,
        blit=False,
    )
