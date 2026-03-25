#!/usr/bin/env bash

set -eou pipefail

PREFIX="🍰  "
echo "$PREFIX Running $(basename $0)"

# Python environment setup with uv
echo "$PREFIX Setting up Python environment with uv..."
if ! command -v uv &> /dev/null; then
  echo "$PREFIX ❌ ERROR: uv is not installed. The devcontainer feature should have installed it."
  exit 1
fi

uv venv --python 3.11 .venv
echo "$PREFIX ✅ Virtual Python environment created..."

. .venv/bin/activate
echo "$PREFIX ✅ Virtual environment activated..."

uv sync --all-extras
echo "$PREFIX ✅ Python environment synced with uv"

PLAYWRIGHT_CACHE_DIR="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/.cache/ms-playwright}"
echo "$PREFIX Installing Playwright OS dependencies..."
playwright install-deps chromium
echo "$PREFIX ✅ Playwright OS dependencies installed"
if compgen -G "$PLAYWRIGHT_CACHE_DIR/chromium_headless_shell-*/chrome-linux/headless_shell" > /dev/null; then
  echo "$PREFIX ✅ Playwright Chromium browser already installed in cache"
else
  echo "$PREFIX Installing Playwright Chromium browser (first time only)..."
  playwright install chromium
  echo "$PREFIX ✅ Playwright Chromium browser installed"
fi

# GitHub CLI Dependencies
set +e
gh auth status >/dev/null 2>&1
AUTH_OK=$?
set -e
if [ $AUTH_OK -ne 0 ]; then
  echo "$PREFIX ⚠️ Not logged into GitHub CLI"
  echo "$PREFIX    This is not looking good  — we want GitHub CLI to work!"
else
  echo "$PREFIX ✅ GitHub Authentication is working smooth!"
  gh extension install devx-cafe/gh-tt
  echo "$PREFIX ✅ Installed the TakT gh cli extension from devx-cafe/gh-tt "
  gh alias import .devcontainer/.gh_alias.yml --clobber
  echo "$PREFIX ✅ Installed the gh shorthand aliases"    
  
fi

git config --global --add safe.directory $(pwd)
echo "$PREFIX ✅ Setting up safe git repository to prevent dubious ownership errors"

git config --local --get include.path | grep -e ../.gitconfig >/dev/null 2>&1 || git config --local --add include.path ../.gitconfig
echo "$PREFIX ✅ Setting up git configuration to support .gitconfig in repo-root"


echo "$PREFIX ✅ SUCCESS"
exit 0
