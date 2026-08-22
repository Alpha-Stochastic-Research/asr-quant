#!/usr/bin/env bash
set -euo pipefail

if [ ! -d .git ]; then
  echo "Run this script from the root of your local asr-quant Git repository."
  exit 1
fi

BRANCH="docs/custom-domain-asrquant"

git switch main
git pull --ff-only
git switch -c "$BRANCH"

PATCH_DIR="$(cd "$(dirname "$0")" && pwd)"
cp "$PATCH_DIR/mkdocs.yml" ./mkdocs.yml
cp "$PATCH_DIR/pyproject.toml" ./pyproject.toml
cp "$PATCH_DIR/README.md" ./README.md
cp "$PATCH_DIR/.github/workflows/docs.yml" ./.github/workflows/docs.yml
cp "$PATCH_DIR/docs/deployment.md" ./docs/deployment.md
mkdir -p scripts
cp "$PATCH_DIR/scripts/validate_notebook_math.py" ./scripts/validate_notebook_math.py
cp "$PATCH_DIR/CUSTOM_DOMAIN_SETUP.md" ./CUSTOM_DOMAIN_SETUP.md

python scripts/validate_notebook_math.py

git add mkdocs.yml pyproject.toml README.md .github/workflows/docs.yml docs/deployment.md scripts/validate_notebook_math.py CUSTOM_DOMAIN_SETUP.md
git commit -m "docs: publish ASRQuant at docs.asr-lab.online/asrquant"
git push -u origin "$BRANCH"

echo
echo "Branch pushed: $BRANCH"
echo "Open a pull request into main, then configure Settings > Pages and DNS as described in CUSTOM_DOMAIN_SETUP.md."
