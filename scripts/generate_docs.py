"""Generate source-derived Markdown used by the ASRQuant documentation site.

The script deliberately depends only on the Python standard library and the
local source tree. GitHub Actions runs it before every documentation build so
that the published API inventory cannot silently drift away from the package
exported by the same commit.
"""
from __future__ import annotations

import inspect
import sys
from collections import defaultdict
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DOCS = ROOT / "docs"
OUTPUT = DOCS / "generated_api_reference.md"

sys.path.insert(0, str(SRC))

import asrquant  # noqa: E402


def _signature(obj: Any) -> str:
    if not callable(obj):
        return ""
    try:
        return str(inspect.signature(obj))
    except (TypeError, ValueError):
        return "(...)"


def _summary(obj: Any) -> str:
    doc = inspect.getdoc(obj) or ""
    if not doc:
        return ""
    line = doc.splitlines()[0].strip()
    return " ".join(line.split())


def _kind(obj: Any) -> str:
    if isinstance(obj, ModuleType):
        return "namespace"
    if inspect.isclass(obj):
        return "class"
    if inspect.isfunction(obj) or inspect.isbuiltin(obj):
        return "function"
    if callable(obj):
        return "callable"
    return "object"


def _render() -> str:
    exported = list(dict.fromkeys(getattr(asrquant, "__all__", [])))
    groups: dict[str, list[tuple[str, Any]]] = defaultdict(list)
    missing: list[str] = []

    for name in exported:
        try:
            obj = getattr(asrquant, name)
        except Exception:
            missing.append(name)
            continue
        groups[_kind(obj)].append((name, obj))

    lines = [
        "# Generated Python API Reference",
        "",
        "!!! info \"Generated from source\"",
        "    This page is regenerated from the current `src/asrquant` tree on every documentation build. "
        "It reflects the exported surface of the same commit deployed to GitHub Pages.",
        "",
        f"**ASRQuant version:** `{asrquant.__version__}`  ",
        f"**Exported names discovered:** `{len(exported)}`",
        "",
    ]

    labels = [
        ("namespace", "Namespaces"),
        ("class", "Classes"),
        ("function", "Functions"),
        ("callable", "Other callables"),
        ("object", "Objects and constants"),
    ]
    for key, title in labels:
        items = groups.get(key, [])
        if not items:
            continue
        lines += [f"## {title}", ""]
        for name, obj in sorted(items, key=lambda x: x[0].lower()):
            signature = _signature(obj)
            summary = _summary(obj)
            lines.append(f"### `{name}`")
            lines.append("")
            lines.append(f"**Kind:** {key}")
            if signature:
                lines += ["", "```python", f"{name}{signature}", "```"]
            if summary:
                lines += ["", summary]
            module = getattr(obj, "__module__", None)
            if module and module.startswith("asrquant"):
                lines += ["", f"Defined in `{module}`."]
            lines.append("")

    if missing:
        lines += [
            "## Export-resolution notes",
            "",
            "The following declared exports could not be resolved while generating this page:",
            "",
        ]
        lines += [f"- `{name}`" for name in missing]
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(_render(), encoding="utf-8")
    print(f"generated {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
