# ASRQuant 1.3.0 — Final Release Validation Record

Release target: **1.3.0**  
Release date: **2026-09-17**

## Final status

**PASS** in the executed final local release environment.

- **336 tests / 36 test modules** collected.
- **336 passed / 0 failed** across the isolated ASR domain groups.
- Final installed-wheel validation: **6 PASS / 0 SKIP / 0 FAIL**.
- Final wheel version: `1.3.0`.
- Final sdist version: `1.3.0`.
- Top-level public callable signature inventory: **258**.
- Existing canonical public API compatibility gate: PASS.

## SW-001 findings incorporated

- Installed-distribution version verification is mandatory; an importable source tree cannot satisfy the version gate.
- `asrquant.__version__` must agree exactly with distribution metadata.
- Missing required NumPy is a failure, not a PASS.
- Sampling tolerances are derived from sample size: 5σ for the sample mean and 7σ for the sample standard deviation.
- Project-specific checks cannot be represented by a placeholder PASS.
- `closed_form_comparisons` is implemented for the final ASRQuant validator using an independent Black–Scholes formula and CRR convergence.
- The validation report is echoed to stdout as well as written to disk, mitigating ephemeral-runtime evidence loss.
- The 258-callable top-level public signature inventory is stored in `PUBLIC_API_SIGNATURES_v1.3.0.json`.

## Contributor provenance

The ASRQuant 1.3.0 software release recognizes **Alpha Kabinet TOURE** and **Srijan Mishra** as software contributors, with **Alpha Stochastic Research** as institutional maintainer. Contribution roles are detailed in `CONTRIBUTORS.md`; software contribution and manuscript authorship are deliberately tracked separately.

## Platform findings kept separate

P-01 (runtime UID/workspace ownership consistency) and P-02 (cross-command persistence of generated files) concern the governed runtime platform rather than ASRQuant’s Python implementation. The package does not claim to fix platform ownership/persistence. The final validation runner mitigates P-02 for evidence collection by printing the complete report to stdout.

For command-level evidence and build notes, see `FINAL_RELEASE_REPORT.md`.
