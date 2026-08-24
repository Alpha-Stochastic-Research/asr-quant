"""Fail when the declared stable ASRQuant public API disappears or changes signature.

The snapshot is intentionally restricted to supported public entry points. Internal
helpers are free to evolve without becoming accidental compatibility promises.
"""
from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
import sys
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import asrquant as asr  # noqa: E402


def resolve(path: str):
    obj = asr
    for part in path.split("."):
        obj = getattr(obj, part)
    return obj


def descriptor(obj) -> dict[str, str]:
    if isinstance(obj, ModuleType):
        return {"kind": "namespace"}
    if inspect.isclass(obj):
        return {"kind": "class", "signature": str(inspect.signature(obj))}
    if callable(obj):
        return {"kind": "callable", "signature": str(inspect.signature(obj))}
    return {"kind": "object", "type": type(obj).__name__}


def check(snapshot_path: Path) -> list[str]:
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    for path, expected in payload["symbols"].items():
        try:
            obj = resolve(path)
        except AttributeError:
            failures.append(f"missing: {path}")
            continue
        actual = descriptor(obj)
        if actual.get("kind") != expected.get("kind"):
            failures.append(f"kind changed: {path}: {expected.get('kind')} -> {actual.get('kind')}")
            continue
        if expected.get("signature") is not None and actual.get("signature") != expected.get("signature"):
            failures.append(
                f"signature changed: {path}\n  expected {expected.get('signature')}\n  actual   {actual.get('signature')}"
            )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot", nargs="?", default="PUBLIC_API_v1.3.json")
    args = parser.parse_args()
    failures = check(ROOT / args.snapshot)
    if failures:
        print("ASRQuant public API compatibility check FAILED", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("ASRQuant public API compatibility check PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
