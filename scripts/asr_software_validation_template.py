#!/usr/bin/env python3
"""ASR package-validation runner, hardened for release evidence.

Contract preserved from the shared ASR validation template:
  * --package
  * --expected-version
  * --output (default PACKAGE_TEST_REPORT.md)
  * exit code 1 when any required check fails

Improvements incorporated after ASRQuant v1.3.0 validation:
  * installed distribution metadata is mandatory for version verification;
  * import-level __version__ must agree with distribution metadata;
  * a missing declared NumPy dependency cannot be counted as PASS;
  * normal-sampling bounds are derived from n (5 sigma mean, 7 sigma std);
  * missing project-specific validation is a SKIP/coverage gap, never PASS;
  * ASRQuant executes independent closed-form comparisons;
  * the full Markdown report is echoed to stdout as durable runtime evidence.
"""
from __future__ import annotations

import argparse
import importlib
import json
import math
import os
import platform
import random
import sys
import time
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any, Callable

SEED = int(os.environ.get("ASR_SEED", "42"))


class CoverageGap(RuntimeError):
    """A check could not be executed and must not be counted as PASS."""


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str
    elapsed_ms: float


def run_check(name: str, fn: Callable[[], str]) -> CheckResult:
    start = time.perf_counter()
    try:
        detail = fn()
        status = "PASS"
    except CoverageGap as exc:
        detail = str(exc)
        status = "SKIP"
    except Exception as exc:  # noqa: BLE001 - evidence must record every failure
        detail = f"{type(exc).__name__}: {exc}"
        status = "FAIL"
    elapsed_ms = round((time.perf_counter() - start) * 1000, 3)
    return CheckResult(name, status, detail, elapsed_ms)


def import_package(package_name: str) -> Any:
    return importlib.import_module(package_name.replace("-", "_"))


def installed_distribution(package_name: str):
    try:
        return metadata.distribution(package_name)
    except metadata.PackageNotFoundError as exc:
        raise AssertionError(
            f"distribution {package_name!r} is not installed; an importable source tree is not sufficient"
        ) from exc


def check_import(package_name: str) -> str:
    module = import_package(package_name)
    return f"Imported {module.__name__} from {getattr(module, '__file__', 'unknown path')}"


def check_version(package_name: str, expected_version: str | None) -> str:
    dist = installed_distribution(package_name)
    actual = dist.version
    if expected_version and actual != expected_version:
        raise AssertionError(f"expected distribution {expected_version}, got {actual}")
    module = import_package(package_name)
    module_version = getattr(module, "__version__", None)
    if module_version is None:
        raise AssertionError("imported module does not expose __version__")
    if str(module_version) != actual:
        raise AssertionError(
            f"version drift: distribution={actual}, module.__version__={module_version}"
        )
    name = dist.metadata.get("Name", package_name)
    return f"Distribution {name}=={actual}; module.__version__ agrees"


def check_reproducibility_seed() -> str:
    random.seed(SEED)
    a = [random.random() for _ in range(8)]
    random.seed(SEED)
    b = [random.random() for _ in range(8)]
    if a != b:
        raise AssertionError("Python random seed is not bitwise reproducible")
    return f"Python random seed reproduces bitwise with ASR_SEED={SEED}"


def _requires_numpy(package_name: str) -> bool:
    reqs = installed_distribution(package_name).requires or []
    return any(r.lower().split(";", 1)[0].strip().startswith("numpy") for r in reqs)


def check_numpy(package_name: str) -> str:
    try:
        import numpy as np  # type: ignore
    except Exception as exc:  # noqa: BLE001
        if _requires_numpy(package_name):
            raise AssertionError(f"required NumPy dependency is unavailable: {exc}") from exc
        raise CoverageGap(f"NumPy unavailable and is not a declared required dependency: {exc}") from exc

    n = 10_000
    rng = np.random.default_rng(SEED)
    sample = rng.normal(size=n)
    mean = float(sample.mean())
    std = float(sample.std(ddof=1))
    mean_tol = 5.0 / math.sqrt(n)  # 5 sigma for N(0,1) sample mean
    std_tol = 7.0 / math.sqrt(2.0 * (n - 1))  # asymptotic sigma(s), 7 sigma
    if abs(mean) > mean_tol:
        raise AssertionError(f"normal sample mean {mean:.6g} exceeds derived ±{mean_tol:.6g}")
    if abs(std - 1.0) > std_tol:
        raise AssertionError(f"normal sample std {std:.6g} exceeds derived 1±{std_tol:.6g}")
    return (
        f"NumPy deterministic smoke passed: n={n}, mean={mean:.6f}, std={std:.6f}; "
        f"bounds derived from n: mean 5σ={mean_tol:.6f}, std 7σ={std_tol:.6f}"
    )


def check_math_identity() -> str:
    value = math.exp(math.log(1.2345))
    if not math.isclose(value, 1.2345, rel_tol=1e-12, abs_tol=1e-12):
        raise AssertionError(f"exp(log(x)) mismatch: {value}")
    return "math.exp(math.log(x)) identity passed at 1e-12 tolerance"


def _normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _independent_bsm_call(s: float, k: float, t: float, r: float, sigma: float, q: float) -> float:
    d1 = (math.log(s / k) + (r - q + 0.5 * sigma * sigma) * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)
    return s * math.exp(-q * t) * _normal_cdf(d1) - k * math.exp(-r * t) * _normal_cdf(d2)


def check_asrquant_closed_form(package_name: str) -> str:
    module = import_package(package_name)
    bsm = getattr(module, "black_scholes_price", None)
    crr = getattr(module, "crr_binomial_price", None)
    if not callable(bsm) or not callable(crr):
        raise AssertionError("ASRQuant closed-form comparison requires black_scholes_price and crr_binomial_price")
    cases = [
        (100.0, 100.0, 1.0, 0.05, 0.20, 0.00),
        (100.0, 110.0, 2.0, 0.03, 0.25, 0.01),
        (75.0, 60.0, 0.5, 0.01, 0.35, 0.02),
    ]
    max_formula_error = 0.0
    max_crr_error = 0.0
    for s, k, t, r, sigma, q in cases:
        reference = _independent_bsm_call(s, k, t, r, sigma, q)
        package_price = float(bsm(s, k, t, r, sigma, option="call", dividend=q))
        formula_error = abs(package_price - reference)
        max_formula_error = max(max_formula_error, formula_error)
        if formula_error > 1e-10:
            raise AssertionError(
                f"Black-Scholes independent-reference error {formula_error:.3e} exceeds 1e-10"
            )
        tree_price = float(crr(s, k, t, r, sigma, option="call", steps=1000, dividend=q, american=False))
        crr_error = abs(tree_price - reference)
        max_crr_error = max(max_crr_error, crr_error)
        if crr_error > 0.01:
            raise AssertionError(f"CRR-vs-closed-form error {crr_error:.6g} exceeds 0.01")
    return (
        f"3 independent Black-Scholes comparisons passed (max error={max_formula_error:.3e}); "
        f"CRR(1000 steps) convergence passed (max error={max_crr_error:.6g})"
    )


def project_specific_checks(package_name: str) -> list[CheckResult]:
    normalized = package_name.replace("-", "_").lower()
    if normalized == "asrquant":
        return [run_check("closed_form_comparisons", lambda: check_asrquant_closed_form(package_name))]

    def gap() -> str:
        raise CoverageGap(
            "No project-specific checks are defined. Add analytical/reference checks before treating this validation as complete."
        )

    return [run_check("project_specific_checks", gap)]


def environment_block(package_name: str, expected_version: str | None) -> dict[str, Any]:
    dist = None
    try:
        dist = installed_distribution(package_name)
    except Exception:
        pass
    return {
        "package": package_name,
        "expected_version": expected_version or "not specified",
        "installed_distribution_version": getattr(dist, "version", None),
        "python": sys.version.replace("\n", " "),
        "platform": platform.platform(),
        "executable": sys.executable,
        "asr_seed": SEED,
        "cwd": str(Path.cwd()),
    }


def render_markdown_report(env: dict[str, Any], results: list[CheckResult]) -> str:
    passed = sum(r.status == "PASS" for r in results)
    failed = sum(r.status == "FAIL" for r in results)
    skipped = sum(r.status == "SKIP" for r in results)
    overall = "FAIL" if failed else ("PASS WITH COVERAGE GAPS" if skipped else "PASS")
    lines = [
        "# ASR Package Validation Report",
        "",
        "## Summary",
        "",
        f"- Package: `{env['package']}`",
        f"- Expected version: `{env['expected_version']}`",
        f"- Checks passed: **{passed}**",
        f"- Checks skipped / coverage gaps: **{skipped}**",
        f"- Checks failed: **{failed}**",
        f"- Overall status: **{overall}**",
        "",
        "## Environment",
        "",
        "```json",
        json.dumps(env, indent=2, sort_keys=True),
        "```",
        "",
        "## Check results",
        "",
        "| Check | Status | Time ms | Detail |",
        "|---|---:|---:|---|",
    ]
    for r in results:
        detail = r.detail.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| `{r.name}` | **{r.status}** | {r.elapsed_ms:.3f} | {detail} |")
    lines += [
        "",
        "## Evidence rule",
        "",
        "A skipped check is a coverage gap and is never counted as a pass. The report is printed to stdout because governed runtimes may not persist generated files across separate commands.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="ASR package validation runner")
    parser.add_argument("--package", default="asrquant", help="Distribution/import package name")
    parser.add_argument("--expected-version", default=None, help="Exact version expected in the ASR task")
    parser.add_argument("--output", default="PACKAGE_TEST_REPORT.md", help="Markdown report path")
    args = parser.parse_args()

    checks = [
        run_check("import_package", lambda: check_import(args.package)),
        run_check("version_check", lambda: check_version(args.package, args.expected_version)),
        run_check("reproducibility_seed", check_reproducibility_seed),
        run_check("numpy_smoke", lambda: check_numpy(args.package)),
        run_check("math_identity", check_math_identity),
    ]
    checks.extend(project_specific_checks(args.package))
    env = environment_block(args.package, args.expected_version)
    report = render_markdown_report(env, checks)
    output = Path(args.output)
    output.write_text(report, encoding="utf-8")

    print(f"ASR validation report written to {output}")
    print(report)
    failed = [r for r in checks if r.status == "FAIL"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
