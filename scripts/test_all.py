"""Run ASRQuant tests in backend-isolated domain groups.

Use one group per process/CI job so BLAS, plotting and solver state cannot leak
between unrelated domains. ``--group all`` is convenient locally, while CI uses
a matrix and invokes each group in its own job.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
GROUPS: dict[str, tuple[str, ...]] = {
    "core": (
        "tests/test_audit_validation.py",
        "tests/test_backtest.py",
        "tests/test_config_data.py",
        "tests/test_metrics.py",
        "tests/test_statistics.py",
        "tests/test_research_pipeline_v050.py",
    ),
    "quant": (
        "tests/test_derivatives_optimization.py",
        "tests/test_v020.py",
        "tests/test_monte_carlo_universal_rc2.py",
    ),
    "surfaces": (
        "tests/test_surface_explorer_v030.py",
        "tests/test_surfaces.py",
        "tests/test_surfaces_parameterized.py",
        "tests/test_approximation_rc2.py",
        "tests/test_visualizations.py",
        "tests/test_visualizations_extended.py",
    ),
    "api": ("tests/test_one_import_api_v040.py",),
    "rates": (
        "tests/test_interest_rates_v110.py",
        "tests/test_ecb_provider_v110.py",
    ),
    "discovery": ("tests/test_discovery_v110.py",),
    "v120": (
        "tests/test_api_consistency_v120.py",
        "tests/test_data_sources_v120.py",
        "tests/test_hypotheses_v120.py",
        "tests/test_hypothesis_discovery_preserved_v120.py",
        "tests/test_alpha_v120.py",
        "tests/test_factors_v120.py",
        "tests/test_risk_v120.py",
        "tests/test_microstructure_v120.py",
        "tests/test_end_to_end_v120.py",
    ),
    "paper": ("tests/test_paper_contract_v1.py",),
    "production": ("tests/test_production_readiness_v1.py",),
}


def _environment() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["MPLBACKEND"] = "Agg"
    env["OPENBLAS_NUM_THREADS"] = "1"
    env["OMP_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    return env


def run_group(name: str) -> int:
    files = GROUPS[name]
    print(f"Running ASRQuant test group: {name}", flush=True)
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *files],
        cwd=ROOT,
        env=_environment(),
        check=False,
    ).returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", choices=[*GROUPS, "all"], default="all")
    args = parser.parse_args()
    selected = list(GROUPS) if args.group == "all" else [args.group]
    failed = [name for name in selected if run_group(name) != 0]
    if failed:
        print("Failed groups: " + ", ".join(failed), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
