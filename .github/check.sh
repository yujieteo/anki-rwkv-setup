#!/usr/bin/env bash
# Run every check of this repository. It needs shellcheck, and a python3
# that has genanki:
#
#   uv run --no-project --with genanki bash .github/check.sh
#
# It builds the example deck into a temporary copy and stops at the first failure.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
cd "$(dirname "$0")/.."

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "== Shellcheck the shell scripts"
shellcheck install-macos.sh .github/check.sh

echo "== Test the card checks in build.py"
python3 -I .github/test-build.py

echo "== Build the example deck into a temporary copy"
cp -R examples/joe-hudson "$WORK/"
python3 -I build.py --check "$WORK/joe-hudson"
python3 -I build.py "$WORK/joe-hudson"
