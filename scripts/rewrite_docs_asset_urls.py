"""Make generated MkDocs pages safe behind the branded ASRQuant docs route.

The branded route is https://docs.asr-lab.online/asrquant/. Its HTML is served
through a proxy/CDN path, while the immutable static MkDocs assets are published
by GitHub Pages. Relative asset URLs can therefore resolve against the branded
path and fail, leaving the page completely unstyled.

Keep navigation and canonical page identity on the branded docs route, but point
static CSS/JS/images and the search index at the GitHub Pages origin. This keeps
the public URL branded without depending on the proxy to mirror every static
asset path.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

SITE = Path("site")
BRANDED_BASE = "https://docs.asr-lab.online/asrquant/"
ASSET_BASE = "https://alpha-stochastic-research.github.io/asr-quant/"

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
        ASSET_BASE + "assets/stylesheets/",
        ASSET_BASE + "assets/javascripts/",
        ASSET_BASE + "assets/brand/asrquant-mark.svg",
        f'"base":"{BRANDED_BASE}"',
    ]
    missing = [token for token in required if token not in index]
    if missing:
        raise SystemExit("Branded docs rewrite validation failed: " + ", ".join(missing))

    if 'href="assets/' in index or 'src="assets/' in index:
        raise SystemExit("Relative root assets remain in generated branded docs index")

    print(
        f"Prepared {len(pages)} documentation pages for {BRANDED_BASE} "
        f"with static assets served from {ASSET_BASE}."
    )


if __name__ == "__main__":
    main()
