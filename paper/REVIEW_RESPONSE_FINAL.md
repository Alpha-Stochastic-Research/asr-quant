# ASRQuant 1.3.0 - final review response

The final manuscript incorporates the release-candidate review before publication.

- Quote-risk and curve/CDS validation figures are regenerated from deterministic package fixtures.
- The 5Y par-swap quote-risk example is aligned with the calibrating 5Y quote rather than an illustrative normalized bar chart.
- The CDS example uses the stated 1Y/3Y/5Y inputs and a 40% recovery assumption.
- Curve repricing is shown at numerical-tolerance scale; the CPCV diagnostic is rendered from the fixed-seed out-of-sample path set.
- FIND-007--FIND-010 are explicitly disclosed as lacking reproducible closure records in the supplied evidence.
- The manuscript includes a before/after numerical table for uneven-grid key-rate DV01 and PSR/DSR scale corrections.
- The five research-question criteria are mapped to tests and primary evidence in a full-width table.
- Local re-execution evidence reports 336/336 passing tests, no pytest skips, and 77.36% statement coverage across `src/asrquant`.
- The review is described as a separate internal release-candidate validation workstream, not third-party independent model validation.
- QuantLib/ISDA SW-007 comparisons are not claimed because the exact reference output is not present in the supplied artifact/public default branch.
- The public CI configuration defines Linux/macOS/Windows x Python 3.10--3.13; the manuscript does not treat that matrix as observed for the exact release commit until it is run.
- The Zenodo DOI remains marked pending until a resolvable deposit is confirmed.
