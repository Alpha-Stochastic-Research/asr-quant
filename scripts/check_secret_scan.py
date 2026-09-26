"""Fail CI when detect-secrets reports unresolved findings."""
from __future__ import annotations

import json
from pathlib import Path
import sys


def main(path: str = "security-evidence/secrets-baseline.json") -> int:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    results = payload.get("results", {})
    findings = sum(len(items) for items in results.values())
    if findings:
        print(f"detect-secrets found {findings} unresolved candidate(s):", file=sys.stderr)
        for filename, items in sorted(results.items()):
            for item in items:
                print(
                    f"  {filename}:{item.get('line_number', '?')} "
                    f"{item.get('type', 'unknown')}",
                    file=sys.stderr,
                )
        return 1
    print("detect-secrets: no unresolved findings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
