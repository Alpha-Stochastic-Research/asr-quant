# ASRQuant Public API Stability Policy

## 1.x policy

Within the 1.x series, symbols listed in `PUBLIC_API_v1.3.json` are treated as stable public entry points.

- Additive arguments should prefer keyword-only parameters and backward-compatible defaults.
- A public symbol must not disappear without a deprecation period.
- A signature change that breaks an existing valid call is considered a breaking change.
- Internal modules and names that are not declared public may evolve without compatibility guarantees.
- Experimental features should be clearly documented as experimental before they receive the same compatibility promise.

## Deprecation

When a 1.x API must change, retain the old entry point, emit a targeted deprecation warning, document the replacement, and schedule removal for a major release unless a security/correctness defect makes continued support unsafe.

## Automated gate

Run:

```bash
python scripts/check_public_api.py
```

The command resolves the declared public symbols and compares callable/class signatures with the release snapshot.
