"""Self-contained HTML tear sheets."""
from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

from jinja2 import Template
import matplotlib.pyplot as plt


_TEMPLATE = Template(
    """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{{ title }}</title>
<style>
body{font-family:Arial,sans-serif;max-width:1200px;margin:36px auto;padding:0 24px;color:#1b1f23}
h1,h2{letter-spacing:-.02em}.meta{background:#f4f6f8;padding:14px;border-radius:8px}
table{border-collapse:collapse;width:100%;margin:16px 0}th,td{border-bottom:1px solid #ddd;padding:8px;text-align:right}th:first-child,td:first-child{text-align:left}
img{max-width:100%;height:auto;border:1px solid #eee;border-radius:8px;margin:8px 0 24px}.warn{color:#9a3412;font-weight:bold}
</style></head><body>
<h1>{{ title }}</h1>
<div class="meta"><b>Experiment fingerprint:</b> {{ fingerprint }}<br>
<b>Observations:</b> {{ observations }} &nbsp; <b>Assets:</b> {{ assets }}<br>
<b>Execution delay:</b> {{ delay }} bar(s) &nbsp; <b>Linear costs:</b> {{ costs }} bps
{% if same_bar %}<div class="warn">Warning: same-bar execution may contain look-ahead bias.</div>{% endif %}</div>
<h2>Performance metrics</h2>{{ metrics|safe }}
<h2>Equity and drawdown</h2><img src="data:image/png;base64,{{ equity }}">
<h2>Rolling diagnostics</h2><img src="data:image/png;base64,{{ rolling }}">
<h2>Monthly returns</h2><img src="data:image/png;base64,{{ monthly }}">
<h2>Cost decomposition</h2>{{ cost_table|safe }}
</body></html>"""
)


def _encode(fig) -> str:
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def create_html_report(result, output: str | None = None, title: str | None = None) -> str:
    """Create a portable HTML report and return its path or HTML string."""
    from .viz.performance import PerformanceVisualizer

    viz = PerformanceVisualizer()
    title = title or result.spec.name
    metrics = result.metrics.to_frame("Value")
    html = _TEMPLATE.render(
        title=title,
        fingerprint=result.fingerprint,
        observations=result.metadata["n_observations"],
        assets=result.metadata["n_assets"],
        delay=result.spec.execution_delay,
        costs=result.spec.costs.linear_bps,
        same_bar=result.spec.execution_delay == 0,
        metrics=metrics.to_html(float_format=lambda x: f"{x:.6f}"),
        equity=_encode(viz.equity_drawdown(result)),
        rolling=_encode(viz.rolling_metrics(result)),
        monthly=_encode(viz.monthly_heatmap(result)),
        cost_table=result.cost_breakdown.describe().T.to_html(float_format=lambda x: f"{x:.6g}"),
    )
    if output is None:
        return html
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return str(path)
