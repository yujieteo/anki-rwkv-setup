#!/bin/sh
# Claude Code runs this after each Write or Edit. If the file is a card
# file (<deck>/cards/*.json) or a deck file (<deck>/deck.json), it builds
# that deck into a temporary copy. The committed .apkg is not changed.
# If the build fails, the script prints the problems and exits with
# code 2, so Claude sees them.
set -u

file=$(python3 -I -c 'import json, sys; d = json.load(sys.stdin); print((d.get("tool_input") or {}).get("file_path") or (d.get("tool_response") or {}).get("filePath") or "")') || exit 0
case "$file" in
  */cards/*.json) deck=$(dirname "$(dirname "$file")") ;;
  */deck.json) deck=$(dirname "$file") ;;
  *) exit 0 ;;
esac
# Only a folder with both deck.json and cards/ is a deck.
[ -f "$deck/deck.json" ] && [ -d "$deck/cards" ] || exit 0

root=$(cd "$(dirname "$0")/../.." && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cp -R "$deck" "$work/deck"

# The build runs inside the temporary folder on "deck", so each problem
# line starts with "deck/". awk puts the real deck folder there instead.
if ! out=$(cd "$work" && PYTHONDONTWRITEBYTECODE=1 \
             uv run -q --no-project --with genanki==0.13.1 \
             python -I "$root/build.py" deck 2>&1); then
  echo "The test build of $deck failed:" >&2
  printf '%s\n' "$out" |
    awk -v d="$deck" 'index($0, "deck/") == 1 { $0 = d substr($0, 5) } { print }' >&2
  exit 2
fi
