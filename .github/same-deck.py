"""Check that two .apkg files hold the same deck.

Usage:
    python3 same-deck.py committed.apkg built.apkg

genanki gives each note and card an id from the clock, and it stamps
modification times. So two builds of the same cards never have the same
bytes. This script compares the deck content: the note types, the decks,
each note's fields and tags (matched by its stable GUID), each card's
deck, template and queue position, and the media files. It prints the
first differences and exits 1 if there are any, or if a package repeats
a stable note or card identity.
"""

from contextlib import closing
import json
import os
import sqlite3
import sys
import tempfile
import zipfile

# Fields that come from the clock. They change on every build.
CLOCK_KEYS = {"mod"}


class DuplicateDeckIdentity(ValueError):
    """A package has multiple rows for one stable identity."""


def drop_clock(value):
    if isinstance(value, dict):
        return {k: drop_clock(v) for k, v in value.items() if k not in CLOCK_KEYS}
    if isinstance(value, list):
        return [drop_clock(v) for v in value]
    return value


def read(path):
    out = {}
    with zipfile.ZipFile(path) as z, tempfile.TemporaryDirectory() as tmp:
        names = sorted(z.namelist())
        out["files"] = names
        for name in names:
            if name != "collection.anki2":
                out["file " + name] = z.read(name).hex()
        z.extract("collection.anki2", tmp)
        with closing(sqlite3.connect(os.path.join(tmp, "collection.anki2"))) as db:
            col = db.execute("select crt, ver, conf, models, decks, dconf, tags from col").fetchone()
            out["col crt, ver"] = col[:2]
            for name, text in zip(["conf", "models", "decks", "dconf", "tags"], col[2:]):
                out["col " + name] = drop_clock(json.loads(text))
            guid = {}
            for nid, g, mid, tags, flds, sfld, csum, flags, data in db.execute(
                    "select id, guid, mid, tags, flds, sfld, csum, flags, data from notes order by guid, id"):
                key = "note " + g
                if key in out:
                    raise DuplicateDeckIdentity(f"{path}: duplicate note GUID {g!r}")
                guid[nid] = g
                out[key] = [mid, tags, flds, sfld, csum, flags, data]
            for row in db.execute(
                    "select nid, ord, did, type, queue, due, ivl, factor, reps, lapses,"
                    " left, odue, odid, flags, data from cards order by nid, ord, id"):
                g, ordinal = guid[row[0]], row[1]
                key = f"card {g} {ordinal}"
                if key in out:
                    raise DuplicateDeckIdentity(f"{path}: duplicate card for note GUID {g!r}, ordinal {ordinal}")
                out[key] = list(row[2:])
    return out


def main(a, b):
    try:
        left, right = read(a), read(b)
    except DuplicateDeckIdentity as error:
        print(error, file=sys.stderr)
        return 1
    diffs = [k for k in sorted(set(left) | set(right)) if left.get(k) != right.get(k)]
    notes = sum(k.startswith("note ") for k in left)
    cards = sum(k.startswith("card ") for k in left)
    if not diffs:
        print(f"Same deck: {notes} notes and {cards} cards in both files.")
        return 0
    print(f"{len(diffs)} difference(s) between {a} and {b}:")
    for k in diffs[:20]:
        print(f"  {k}\n    {a}: {str(left.get(k))[:300]}\n    {b}: {str(right.get(k))[:300]}")
    return 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2]))
