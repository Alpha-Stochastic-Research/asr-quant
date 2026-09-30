# PyPI Metadata Notes

## Current observation

The public package line has a patch release on PyPI while parts of the repository still identify the source as 1.3.0.

Before the next package publication, align the release metadata in one dedicated release PR rather than mixing version changes into documentation-only adoption work.

## Next release checklist

- align `pyproject.toml` version;
- align `src/asrquant/version.py`;
- update release-integrity tests;
- update release workflow assertions;
- update README / documentation release references;
- build wheel + sdist;
- run full release regression suite;
- publish through Trusted Publishing;
- verify the PyPI landing page and installation from a clean environment.

This file intentionally does not change package version metadata by itself.
