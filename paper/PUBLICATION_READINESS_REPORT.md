# ASRQuant 1.3.0 - Final Publication Readiness Review

**Manuscript:** *ASRQuant 1.3.0: Quantitative Research Under Real-World Constraints*  
**Version:** 1.3.0  
**Date reviewed:** September 2026  
**Status:** Final reviewed manuscript, subject only to external deposit/author approval.

## Editorial and visual QA

- Final PDF compiles successfully to 16 A4 pages.
- The abstract was rewritten around the research problem, evaluation design, measured results and scope limitations.
- The five-criterion evidence matrix is a full-width table with separated headers and readable column spacing.
- The final PDF was rendered page-by-page after compilation; no clipped text, black boxes or broken glyphs were observed.
- Author names are standardized as Alpha Kabinet TOURE and Srijan Mishra.
- The title explicitly identifies ASRQuant 1.3.0.

## Scientific/review reconciliation

- Curve, quote-risk, credit and validation figures use corrected deterministic/fixed-seed evidence.
- The 5Y par-swap quote-risk figure is aligned with the calibrating 5Y market quote.
- The CDS example states the 1Y/3Y/5Y tenor set and fixed recovery convention.
- Calibration residuals are represented at numerical-tolerance scale.
- The release-candidate review is described as a separate internal ASR validation workstream, not third-party independent model validation.
- FIND-007--FIND-010 are explicitly disclosed as lacking reproducible closure records and are excluded from the closed-fix total.
- Before/after evidence for uneven-grid key-rate DV01 and PSR/DSR scale corrections is reported.
- External QuantLib/ISDA SW-007 comparison numbers are not claimed because the exact reference output is absent from the supplied artifact.

## Local evidence reported in the paper

The manuscript reports the previously recorded review re-execution for the corrected artifact: 336 passing tests, no pytest skips, and 77.36% statement coverage across `src/asrquant`, together with import/API/release and wheel-smoke controls. These are software-validation results, not investment-performance claims.

For this final packaging pass, the paper contract and the release-integrity signature check were also re-run separately with `PYTHONPATH=src` and passed.

## Hosted/external gates

The public CI configuration defines Linux/macOS/Windows x Python 3.10--3.13 compatibility jobs. The manuscript does not present this matrix as observed for the exact final public release commit until that commit is actually run. The Zenodo DOI is therefore also kept as **Pending Zenodo deposit** until a resolvable record exists.

## Final decision

**READY FOR FINAL AUTHOR APPROVAL AND PUBLIC DEPOSIT.**
