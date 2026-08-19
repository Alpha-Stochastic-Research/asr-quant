#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_URL="${1:-https://github.com/Alpha-Stochastic-Research/asr-quant.git}"
BRANCH="${2:-main}"

if [[ -d .git ]]; then
  echo "A Git repository already exists in this directory." >&2
  exit 1
fi

VERSION="$(python - <<'PYVER'
import re
from pathlib import Path
text = Path("pyproject.toml").read_text()
print(re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE).group(1))
PYVER
)"
TAG="v${VERSION}"
python scripts/check_release.py "$TAG"

if [[ "${RUN_TESTS:-0}" == "1" ]]; then
  PYTHONPATH=src python -m pytest -q
fi

git init -b "$BRANCH"
git config user.name "Alpha Stochastic Research"
git config user.email "research@asr-lab.online"
git add .
git commit -m "ASRQuant ${VERSION} release"
git remote add origin "$REPOSITORY_URL"
git push -u origin "$BRANCH"

echo
echo "Repository pushed. Configure the pypi environment and PyPI Trusted Publisher before creating release ${TAG}."
