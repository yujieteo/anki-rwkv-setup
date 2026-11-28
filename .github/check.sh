#!/usr/bin/env bash
# Run every check of this repository. It needs shellcheck, and a python3
# that has genanki 0.13.1:
#
#   uv run --no-project --with genanki==0.13.1 bash .github/check.sh
#
# It builds the example deck into a temporary copy, so the committed
# .apkg is not changed. It stops at the first check that fails.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
cd "$(dirname "$0")/.."

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "== Shellcheck the shell scripts"
shellcheck install-macos.sh .github/check.sh .claude/hooks/test-build.sh

echo "== Test the installer guard hook"
python3 -I .github/test-block-installer.py

echo "== Test the card checks in build.py"
python3 -I .github/test-build.py

echo "== Test the deck comparison"
python3 -I .github/test-same-deck.py

echo "== Build the example deck into a temporary copy"
cp -R examples/joe-hudson "$WORK/"
python3 -I build.py "$WORK/joe-hudson"

echo "== Committed deck matches the card files"
python3 -I .github/same-deck.py examples/joe-hudson/joe-hudson.apkg "$WORK/joe-hudson/joe-hudson.apkg"
