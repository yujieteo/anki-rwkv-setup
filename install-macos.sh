#!/usr/bin/env bash
# Install the RWKV build of Anki (JSchoreels/anki) on macOS.
#
#   ./install-macos.sh                  # the tested release
#   ./install-macos.sh latest           # the newest release
#   ./install-macos.sh '<release tag>'  # a release you choose
#
# What it does:
#   1. Downloads the .dmg for your Mac (Apple Silicon or Intel) from
#      github.com/JSchoreels/anki/releases.
#   2. Checks the file's SHA-256 against the hash GitHub reports.
#   3. Moves an existing /Applications/Anki.app to the Trash (not deleted).
#   4. Copies the RWKV build to /Applications/Anki.app.
#
# Your Anki data in ~/Library/Application Support/Anki2 is not touched.
# Needs: curl, python3, shasum, hdiutil (all on macOS by default).
set -euo pipefail

REPO="JSchoreels/anki"
TESTED_TAG="26.09.4+fsrs7.build.115"
TAG="${1:-$TESTED_TAG}"

case "$(uname -m)" in
  arm64) ARCH="mac-apple" ;;
  x86_64) ARCH="mac-intel" ;;
  *) echo "Unsupported CPU: $(uname -m)" >&2; exit 1 ;;
esac

if [ "$TAG" = "latest" ]; then
  API="https://api.github.com/repos/$REPO/releases/latest"
else
  API="https://api.github.com/repos/$REPO/releases/tags/$(python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))' "$TAG")"
fi

stop_if_anki_running() {
  if pgrep -xq anki || pgrep -xq Anki; then
    echo "Anki is running. Quit it, then run this script again." >&2
    exit 1
  fi
}

# Check before the download, so you do not wait for it in vain. The check
# runs again just before the swap, in case Anki was opened meanwhile.
stop_if_anki_running

WORK="$(mktemp -d)"
trap 'hdiutil detach "$WORK/mnt" -quiet 2>/dev/null || true; rm -rf "$WORK"' EXIT

echo "Reading release information..."
curl -fsSL "$API" -o "$WORK/release.json"
read -r NAME URL DIGEST < <(python3 - "$WORK/release.json" "$ARCH" <<'PY'
import json, sys
rel = json.load(open(sys.argv[1]))
want = f"-{sys.argv[2]}.dmg"
for a in rel["assets"]:
    if a["name"].endswith(want) and "portable" not in a["name"]:
        print(a["name"], a["browser_download_url"], (a.get("digest") or "none").removeprefix("sha256:"))
        break
else:
    sys.exit(f"No {want} file in release {rel.get('tag_name')}")
PY
)

echo "Downloading $NAME..."
curl -fL --progress-bar "$URL" -o "$WORK/anki.dmg"

ACTUAL="$(shasum -a 256 "$WORK/anki.dmg" | cut -d' ' -f1)"
if [ "$DIGEST" = "none" ]; then
  echo "Warning: GitHub reports no hash for this file (SHA-256: $ACTUAL)." >&2
elif [ "$ACTUAL" != "$DIGEST" ]; then
  echo "Hash mismatch: expected $DIGEST, got $ACTUAL. Stopping." >&2
  exit 1
else
  echo "Hash OK: $ACTUAL"
fi

stop_if_anki_running

mkdir "$WORK/mnt"
hdiutil attach -nobrowse -readonly -mountpoint "$WORK/mnt" "$WORK/anki.dmg" -quiet

if [ -d /Applications/Anki.app ]; then
  echo "Moving the current Anki to the Trash..."
  if command -v trash >/dev/null 2>&1; then
    trash /Applications/Anki.app
  else
    mv /Applications/Anki.app "$HOME/.Trash/Anki-$(date +%s).app"
  fi
fi

ditto "$WORK/mnt/Anki.app" /Applications/Anki.app
echo "Installed: $(defaults read /Applications/Anki.app/Contents/Info CFBundleShortVersionString)"
echo
echo "Note: this build is not notarized by Apple. A file downloaded with curl"
echo "is not quarantined, so it opens normally. If you downloaded the .dmg in a"
echo "browser instead, macOS may block it; see the README."
