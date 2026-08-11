# ASRQuant v1.1.0

Use `RELEASE_CHECKLIST_v1.1.0.md` for the current release. The 1.0.0 checklist is retained below for provenance.

---

# ASRQuant v1.0.0 stable release checklist

This checklist validates the software release. It does **not** authorize a live-capital deployment.

## Source and paper contract

- [x] Package version is `1.0.0` in `pyproject.toml`.
- [x] Runtime version is `1.0.0` in `asrquant.version`.
- [x] Manuscript version is `0.1.0` and identifies software release `1.0.0`.
- [x] The paper contains only the final manuscript/software version identifiers and validated test counts.
- [x] Public one-import workflows are covered by `tests/test_paper_contract_v1.py`.
- [x] Fixed-income bootstrap rejects incomplete coupon grids.

## Automated verification

- [x] 154 tests are collected.
- [x] Core: 27 passed.
- [x] Quant: 28 passed.
- [x] Surfaces: 15 passed.
- [x] One-import API: 4 passed.
- [x] Paper contract: 18 passed.
- [x] Production boundary: 62 passed.
- [x] Python source, tests, examples and scripts compile.
- [ ] Hosted Linux/macOS/Windows CI evidence attached to the release commit.
- [ ] Ruff, mypy, Bandit, dependency audit and secret scan pass on the exact release commit.
- [ ] SBOM and artifact provenance attached to the GitHub Release.

## Distribution

- [ ] Build wheel and source archive from the clean stable tree.
- [ ] Verify metadata with `twine check`.
- [ ] Install the wheel into an isolated environment and verify the version/CLI.
- [ ] Tag the reviewed commit `v1.0.0`.
- [ ] Publish GitHub Release `ASRQuant 1.0.0` (not a pre-release).
- [ ] Publish through the PyPI Trusted Publisher.

## Live capital is separate

A stable PyPI release does not satisfy the additional evidence required by `PRODUCTION_READINESS_CHECKLIST.md` for live-capital authorization.
