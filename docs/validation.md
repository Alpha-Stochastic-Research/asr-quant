# Validation Strategy for ASRQuant 1.3.0

ASRQuant separates software correctness, numerical correctness and research validity. Passing one layer does not imply the others.

## Software gates

- isolated domain test groups;
- compile/import checks;
- public API signature snapshot;
- clean wheel/source-distribution installation;
- hosted Python/OS matrix;
- security and supply-chain workflow.

## Numerical gates

The 1.3 suite includes deterministic invariants such as:

- Black-Scholes put-call parity;
- discount/zero-rate round trips;
- exact par-swap repricing;
- curve quote repricing;
- quote/Jacobian finite-difference consistency;
- risk/P&L reconciliation;
- calibration recovery on known synthetic models;
- covariance positive-semidefinite checks;
- fixed-seed Monte Carlo reproducibility.

## Research validation

`asr.validation` provides chronology-aware splits plus CPCV, PBO, Reality Check, SPA, leakage diagnostics and multiverse analysis. These are evidence-management tools, not proof that a strategy will remain profitable.

## Data lineage

Use `DataSnapshot`, `DataStore`, `PointInTimeFrame`, `Experiment` and `ResearchGraph` when the exact information set and dependency chain need to be reconstructed later.

## Scope discipline

A clean leakage report does not prove that a vendor dataset is point-in-time correct. A statistically significant multiple-testing diagnostic does not establish economic causality. A calibrated curve/model is not considered valid solely because the numerical solver converged.
