#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_URL="${1:-https://github.com/Alpha-Stochastic-Research/asrquant.git}"
BRANCH="${2:-main}"

if [[ -d .git ]]; then
  echo "A Git repository already exists in this directory." >&2
  exit 1
fi

python scripts/check_release.py v1.0.0

if [[ "${RUN_TESTS:-0}" == "1" ]]; then
  PYTHONPATH=src python -m pytest -q
fi

git init -b "$BRANCH"
git config user.name "Alpha Stochastic Research"
git config user.email "research@asr-lab.online"
git add .
git commit -m "Initial ASRQuant v1.0.0 release"
git remote add origin "$REPOSITORY_URL"
git push -u origin "$BRANCH"

echo
echo "Repository pushed. Configure the pypi environment and PyPI Trusted Publisher before creating release v1.0.0."
