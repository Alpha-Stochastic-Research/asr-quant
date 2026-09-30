"""Prepare generated MkDocs pages for the ASRQuant custom documentation domain.

The ASRQuant GitHub Pages custom domain is mounted at the host root:
https://docs.asr-lab.online/

Historically the public website also linked to `/asrquant`. Keep that legacy URL
working by publishing an alias page at `site/asrquant/index.html`. The alias is a
copy of the documentation home page with a `<base>` element pointing at the host
root, so its navigation resolves to the real root pages instead of nonexistent
`/asrquant/...` paths.

All static MkDocs assets are rewritten to absolute URLs on the branded domain so
they remain correct from both `/` and `/asrquant/`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

SITE = Path("site")
BRANDED_BASE = "https://docs.asr-lab.online/"
ASSET_BASE = BRANDED_BASE

ATTR_RE = re.compile(
    r'(?P<prefix>\b(?:href|src)=["\'])(?P<path>(?:\.\./)*(?:assets|stylesheets)/[^"\']+)(?P<suffix>["\'])'
)
CONFIG_RE = re.compile(
    r'(<script id="__config" type="application/json">)(?P<json>.*?)(</script>)',
    re.DOTALL,
)


def absolute_asset(path: str) -> str:
    while path.startswith("../"):
        path = path[3:]
    return ASSET_BASE + path.lstrip("/")


def rewrite_html(path: Path) -> None:
    source = path.read_text(encoding="utf-8")

    source = ATTR_RE.sub(
        lambda match: (
            match.group("prefix")
            + absolute_asset(match.group("path"))
            + match.group("suffix")
        ),
        source,
    )

    def rewrite_config(match: re.Match[str]) -> str:
        config = json.loads(match.group("json"))
        config["base"] = BRANDED_BASE
        search = str(config.get("search") or "")
        if search:
            while search.startswith("../"):
                search = search[3:]
            config["search"] = ASSET_BASE + search.lstrip("/")
        return (
            match.group(1)
            + json.dumps(config, ensure_ascii=False, separators=(",", ":"))
            + match.group(3)
        )

    source = CONFIG_RE.sub(rewrite_config, source)
    path.write_text(source, encoding="utf-8")


def build_legacy_alias() -> None:
    index_path = SITE / "index.html"
    alias_dir = SITE / "asrquant"
    alias_dir.mkdir(parents=True, exist_ok=True)
    source = index_path.read_text(encoding="utf-8")
    source = source.replace(
        "<head>",
        f'<head><base href="{BRANDED_BASE}">',
        1,
    )
    source = source.replace(
        '<link rel="canonical" href="https://docs.asr-lab.online/">',
        '<link rel="canonical" href="https://docs.asr-lab.online/">',
        1,
    )
    (alias_dir / "index.html").write_text(source, encoding="utf-8")


def main() -> None:
    if not SITE.exists():
        raise SystemExit("site/ does not exist; run mkdocs build first")

    pages = list(SITE.rglob("*.html"))
    if not pages:
        raise SystemExit("No generated HTML pages found in site/")

    for page in pages:
        rewrite_html(page)

    build_legacy_alias()

    index = (SITE / "index.html").read_text(encoding="utf-8")
    alias = (SITE / "asrquant" / "index.html").read_text(encoding="utf-8")
    required = [
        ASSET_BASE + "assets/stylesheets/",
        ASSET_BASE + "assets/javascripts/",
        ASSET_BASE + "assets/brand/asrquant-mark.svg",
        f'"base":"{BRANDED_BASE}"',
    ]
    missing = [token for token in required if token not in index]
    if missing:
        raise SystemExit("Branded docs rewrite validation failed: " + ", ".join(missing))

    if f'<base href="{BRANDED_BASE}">' not in alias:
        raise SystemExit("Legacy /asrquant alias is missing its root base URL")
    if 'ASRQuant Documentation' not in alias:
        raise SystemExit("Legacy /asrquant alias does not contain the docs home page")

    print(
        f"Prepared {len(pages)} documentation pages for {BRANDED_BASE} and "
        "published the legacy /asrquant/ alias."
    )


if __name__ == "__main__":
    main()
