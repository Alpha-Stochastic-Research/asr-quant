# Research Discipline & Reproducibility

ASRQuant's reproducibility layer is intended to make a research decision reviewable rather than merely rerunnable.

## Preserve

- source identifiers and retrieval time;
- data fingerprints;
- feature definitions and lags;
- hypothesis registry and screening settings;
- model parameters and random seeds;
- portfolio construction rules;
- cost and execution assumptions;
- robustness outcomes;
- package version and environment metadata.

## Use manifests and audit storage

The package exposes `build_manifest` and `SQLiteAuditStore` for reproducibility metadata and audit events.

## Fail-closed execution boundary

Paper trading and live-capable broker primitives are intentionally separate from research validation. Installing ASRQuant or passing a research test suite does not constitute authorization to deploy capital.
