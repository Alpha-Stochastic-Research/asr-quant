# Core Concepts

## Domain namespaces

Version 1.2.0 groups the public surface by research problem rather than by implementation detail. The primary namespaces are:

`data`, `hypotheses`, `alpha`, `factors`, `risk`, `microstructure`, `backtesting`, `portfolio`, `stats`, `ml`, `options`, `rates`, `stochastic`, `mc`, `vol`, `research` and `trading`.

## Canonical verbs

Where appropriate, domain namespaces expose a small vocabulary:

- `load` / `validate`
- `discover`
- `run`
- `optimize`
- `price`
- `analyze` / `calibrate`
- `regress`
- `fit`

These wrappers standardize names and result contracts while preserving the lower-level 1.x functions.

## Result contracts

Structured 1.2 results favor:

- `summary` for compact metrics;
- `to_frame()` for tabular payloads when available;
- `to_dict()` for serializable output when available;
- fingerprints or metadata when the underlying engine supports them.

## Chronology is part of the model

A valid quantitative workflow must make information timing explicit. ASRQuant therefore treats lagging, walk-forward splits, execution delay and data provenance as research mechanics rather than presentation details.

## Research evidence is not a trading claim

Statistical significance, novelty, robust backtesting and implementation correctness answer different questions. ASRQuant keeps those layers separate rather than collapsing them into a single performance score.
