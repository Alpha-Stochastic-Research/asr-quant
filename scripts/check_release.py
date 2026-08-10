"""Validate that a Git tag matches every declared ASRQuant version."""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
VERSION = ROOT / "src" / "asrquant" / "version.py"


def project_version() -> str:
    text = PYPROJECT.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise RuntimeError("Could not find project.version in pyproject.toml")
    return match.group(1)


def package_version() -> str:
    module = ast.parse(VERSION.read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__version__":
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        return node.value.value
    raise RuntimeError("Could not find asrquant.__version__")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/check_release.py vX.Y.Z", file=sys.stderr)
        return 2

    tag = sys.argv[1]
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:[a-zA-Z0-9.-]+)?", tag):
        print(f"Invalid release tag: {tag!r}; expected vX.Y.Z", file=sys.stderr)
        return 1

    expected = tag.removeprefix("v")
    declared = {
        "pyproject.toml": project_version(),
        "asrquant.__version__": package_version(),
    }
    mismatches = {name: value for name, value in declared.items() if value != expected}

    if mismatches:
        print(f"Release tag declares version {expected}, but found:", file=sys.stderr)
        for name, value in mismatches.items():
            print(f"  - {name}: {value}", file=sys.stderr)
        return 1

    print(f"Release version validated: {expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
