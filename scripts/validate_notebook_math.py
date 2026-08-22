"""Validate Markdown math delimiters in the official ASRQuant quickstart notebook.

Policy for the official notebook:
- displayed mathematics uses $$ ... $$ only;
- LaTeX delimiters \\( ... \\) and \\[ ... \\] are forbidden;
- single-dollar inline math is forbidden to avoid inconsistent rendering.
"""

from __future__ import annotations

import json
from pathlib import Path

NOTEBOOK = Path("notebooks/ASRQuant_v1.2.0_Quickstart.ipynb")
FORBIDDEN = (r"\\(", r"\\)", r"\\[", r"\\]")


def main() -> None:
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    errors: list[str] = []
    display_blocks = 0

    for index, cell in enumerate(notebook.get("cells", []), start=1):
        if cell.get("cell_type") != "markdown":
            continue

        source = "".join(cell.get("source", []))

        for token in FORBIDDEN:
            if token in source:
                errors.append(f"Markdown cell {index}: forbidden delimiter {token!r}")

        marker_count = source.count("$$")
        if marker_count % 2:
            errors.append(f"Markdown cell {index}: unbalanced $$ delimiters")
        display_blocks += marker_count // 2

        without_display_math = source.replace("$$", "")
        if "$" in without_display_math:
            errors.append(
                f"Markdown cell {index}: single-dollar math/currency marker found; "
                "official notebook math must use $$ ... $$"
            )

    if display_blocks == 0:
        errors.append("No $$ ... $$ display-math blocks were found")

    if errors:
        raise SystemExit("Notebook math validation failed:\n- " + "\n- ".join(errors))

    print(
        f"Notebook math validation passed: {display_blocks} display blocks, "
        "no forbidden delimiters, no single-dollar math."
    )


if __name__ == "__main__":
    main()
