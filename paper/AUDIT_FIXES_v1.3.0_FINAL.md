# ASRQuant 1.3.0 - Independent Audit Corrections

This record maps the confirmed release-candidate findings to the final source.

| Finding | Final treatment |
|---|---|
| FIND-001 | Heavy optional stacks are no longer imported by `import asrquant`; visualization, ML and HTTP stacks are lazy. |
| FIND-002 | Plotting/reporting, ML, providers and PDF literature dependencies are optional extras. |
| FIND-003 | Uneven-pillar key-rate bumps use asymmetric left/right widths. |
| FIND-004 | Vasicek calibration reports `phi_std_error` and `kappa_std_error`; estimator bias is documented as statistical uncertainty, not relabelled as a numerical bug. |
| FIND-005 | `summary_metrics(..., omega_threshold=...)` exposes the Omega threshold. |
| FIND-006 | GP `WhiteKernel` noise is fixed and requested/fitted values are reported. |
| FIND-011 | PSR/DSR use per-observation Sharpe scaling. |
| FIND-012 | Removed statsmodels keywords are not passed. |
| FIND-013 | RSI uses Wilder smoothing by default; `rsi_method="sma"` preserves the alternate convention. |
| FIND-014 | Implied-volatility inversion refuses a non-identifiable intrinsic-boundary quote. |
| FIND-015 | PCA component signs are oriented deterministically. |

Regression coverage: `tests/test_v130_audit_fixes.py`.

