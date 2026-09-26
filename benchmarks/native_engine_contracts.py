"""Selected finance-model contracts for ASRQuant's native engines.

This benchmark deliberately avoids external quantitative-finance pricing engines.
It checks mathematical identities and round trips against ASRQuant's own public
interfaces. The release test suite remains the authoritative validation gate.
"""
from __future__ import annotations

import math

import numpy as np

from asrquant.derivatives import black_scholes_price, implied_volatility
from asrquant.interest_rates import DiscountCurve


def _check(name: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"{status:4s}  {name}" + (f"  {detail}" if detail else ""))
    if not condition:
        raise AssertionError(name)


def main() -> int:
    spot, strike, maturity, rate, vol = 100.0, 105.0, 1.25, 0.03, 0.22
    call = float(black_scholes_price(spot, strike, maturity, rate, vol, "call"))
    put = float(black_scholes_price(spot, strike, maturity, rate, vol, "put"))
    parity_error = abs((call - put) - (spot - strike * math.exp(-rate * maturity)))
    _check("Black-Scholes put-call parity", parity_error < 1e-10, f"error={parity_error:.3e}")

    recovered = implied_volatility(call, spot, strike, maturity, rate, option="call")
    _check("Implied-volatility round trip", abs(recovered - vol) < 1e-9, f"error={abs(recovered-vol):.3e}")

    pillars = np.array([0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 15.0, 20.0])
    curve = DiscountCurve.from_zero_rates(pillars, np.full(len(pillars), 0.03))
    dfs = np.asarray(curve.df(pillars), dtype=float)
    expected = np.exp(-0.03 * pillars)
    _check("Flat zero-rate discount factors", np.allclose(dfs, expected, atol=1e-12, rtol=1e-12))

    base = np.asarray(curve.zero_rate(pillars), dtype=float)
    bump = 1e-4
    weights = []
    for pillar in pillars:
        bumped = curve.bump_key_rate(float(pillar), bump=bump)
        weights.append((np.asarray(bumped.zero_rate(pillars), dtype=float) - base) / bump)
    partition = np.sum(np.asarray(weights), axis=0)
    max_error = float(np.max(np.abs(partition - 1.0)))
    _check("Key-rate partition on uneven pillars", max_error < 1e-10, f"max_error={max_error:.3e}")

    print("\nNative ASRQuant engine contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
