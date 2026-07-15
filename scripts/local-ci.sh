#!/bin/sh
set -eu

uv run --locked --no-dev python -m compileall custom_components tests
uv run --locked --group lint ruff check .
uv run --locked --group typecheck ty check
uv run --locked --group test pytest
sh scripts/hacs-validate
sh scripts/hassfest
