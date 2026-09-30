"""Rewrite generated MkDocs asset URLs to the canonical public Pages host.

Why this exists
---------------
The ASR website links to the documentation through a branded docs route. Some
proxy/CDN configurations can serve the generated HTML while failing to serve
MkDocs' relative CSS/JS/image assets from the same path. The result is a raw,
unstyled document even though the MkDocs build itself is valid.

This post-build step keeps documentation navigation links relative, but rewrites
static theme/package assets and the Material search worker base to the canonical
GitHub Pages origin. That makes the generated site render correctly both on the
canonical Pages URL and when its HTML is exposed through the branded docs route.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

SITE = Path("site")
CANONICAL = "https://alpha-stochastic-research.github.io/asr-quant/"

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
    return CANONICAL + path.lstrip("/")


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
        config["base"] = CANONICAL
        search = str(config.get("search") or "")
        if search:
            config["search"] = absolute_asset(search)
        return (
            match.group(1)
            + json.dumps(config, ensure_ascii=False, separators=(",", ":"))
            + match.group(3)
        )

    source = CONFIG_RE.sub(rewrite_config, source)
    path.write_text(source, encoding="utf-8")


def main() -> None:
    if not SITE.exists():
        raise SystemExit("site/ does not exist; run mkdocs build first")

    pages = list(SITE.rglob("*.html"))
    if not pages:
        raise SystemExit("No generated HTML pages found in site/")

    for page in pages:
        rewrite_html(page)

    index = (SITE / "index.html").read_text(encoding="utf-8")
    required = [
        CANONICAL + "assets/stylesheets/",
        CANONICAL + "assets/javascripts/",
        CANONICAL + "assets/brand/asrquant-mark.svg",
        f'"base":"{CANONICAL}"',
    ]
    missing = [token for token in required if token not in index]
    if missing:
        raise SystemExit("Asset rewrite validation failed: " + ", ".join(missing))

    print(f"Rewrote canonical static asset URLs in {len(pages)} documentation pages.")


if __name__ == "__main__":
    main()
