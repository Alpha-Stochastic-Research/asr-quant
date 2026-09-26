# ASRQuant 1.3.0 - Final Local Validation Summary

Date: 2026-09-17

- 336 tests collected across 36 test modules.
- Group results: core 27 PASS; quant 28 PASS; surfaces 15 PASS; api 4 PASS; rates 36 PASS; discovery 7 PASS; v120 76 PASS; v130 63 PASS; paper 18 PASS; production 62 PASS.
- 84 package modules imported with zero failures (excluding `asrquant.__main__`, which executes the CLI).
- `scripts/check_public_api.py`: PASS.
- `scripts/check_release.py v1.3.0`: PASS.
- Corrected audit regression file: `tests/test_v130_audit_fixes.py` (12 PASS).
- Wheel rebuilt offline with `pip wheel --no-deps --no-build-isolation`; installed-wheel smoke import reports 1.3.0.
- Source distribution rebuilt locally.
- Native engine contract benchmark: PASS (put-call parity, implied-volatility round trip, flat-curve discount factors, uneven-pillar key-rate partition).
- Paper compiled with XeLaTeX and visually rendered for inspection.
- No registry publication is implied by this local artifact.
