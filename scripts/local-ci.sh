#!/bin/sh
set -eu

if [ -z "${REPOSITORY:-}" ]; then
  remote_url="$(git remote get-url origin)"
  REPOSITORY="$(
    printf '%s\n' "$remote_url" \
      | sed -E \
          -e 's#^git@github.com:##' \
          -e 's#^https://github.com/##' \
          -e 's#^ssh://git@github.com/##' \
          -e 's#\.git$##'
  )"
  export REPOSITORY
fi

if [ -z "${GITHUB_TOKEN:-${GH_TOKEN:-}}" ] && command -v gh >/dev/null 2>&1; then
  GITHUB_TOKEN="$(gh auth token 2>/dev/null || true)"
  export GITHUB_TOKEN
fi

uv run --locked --no-dev python -m compileall custom_components tests
uv run --locked --group lint ruff check .
uv run --locked --group typecheck ty check
uv run --locked --group test pytest
sh scripts/hacs-validate
sh scripts/hassfest
