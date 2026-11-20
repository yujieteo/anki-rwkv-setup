"""Build an Anki deck (.apkg) from a folder of card files.

Usage:
    uv run --with genanki python build.py examples/joe-hudson

The folder holds:
    deck.json     deck name, output file name, note type ids, subdecks
    cards/*.json  card files (format in docs/card-format.md)

Each note's id comes from its own text, so importing a rebuilt file
updates the notes you already have instead of adding copies.
"""

import hashlib
import html
import json
import re
import sys
from pathlib import Path

import genanki

CSS = """
.card { font-family: -apple-system, system-ui, sans-serif; font-size: 20px;
        line-height: 1.45; text-align: left; max-width: 36em; margin: 0 auto;
        padding: 0 16px; color: #1d1d1f; background: #fbfaf7; }
.nightMode .card, .night_mode .card { color: #ece9e2; background: #1c1b19; }
.context { font-size: 14px; letter-spacing: .02em; text-transform: uppercase;
           color: #8a8478; margin-bottom: .6em; }
.kind { font-size: 13px; color: #a0522d; margin-left: .5em; text-transform: none; }
.extra { margin-top: 1em; font-size: 17px; color: #55514a; }
.nightMode .extra, .night_mode .extra { color: #b9b4aa; }
.source { margin-top: 1.2em; font-size: 14px; }
.source a { color: #8a6d3b; }
.cloze { font-weight: 600; color: #a0522d; }
hr#answer { border: 0; border-top: 1px solid #d8d3c8; margin: 1em 0; }
"""

HEAD = '<div class="context">{{Context}}{{#Kind}}<span class="kind">{{Kind}}</span>{{/Kind}}</div>'
TAIL = ('{{#Extra}}<div class="extra">{{Extra}}</div>{{/Extra}}'
        '{{#Source}}<div class="source">{{Source}}</div>{{/Source}}')

KIND_LABEL = {"practice": "try it", "story": "his story", "safety": "safety",
              "evidence": "evidence"}


def models(cfg):
    name = cfg["name"]
    basic = genanki.Model(
        cfg["basic_model_id"], f"{name} Basic", css=CSS,
        fields=[{"name": n} for n in ["Context", "Front", "Back", "Extra", "Source", "Kind"]],
        templates=[{
            "name": "Card 1",
            "qfmt": HEAD + "{{Front}}",
            "afmt": "{{FrontSide}}<hr id=answer>{{Back}}" + TAIL,
        }],
    )
    cloze = genanki.Model(
        cfg["cloze_model_id"], f"{name} Cloze", css=CSS,
        model_type=genanki.Model.CLOZE,
        fields=[{"name": n} for n in ["Context", "Text", "Extra", "Source", "Kind"]],
        templates=[{
            "name": "Cloze",
            "qfmt": HEAD + "{{cloze:Text}}",
            "afmt": HEAD + "{{cloze:Text}}" + TAIL,
        }],
    )
    return basic, cloze


def deck_id(name):
    return int(hashlib.sha1(name.encode()).hexdigest()[:8], 16) | (1 << 30)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def source_html(c, cfg):
    if c.get("section") and cfg.get("section_url"):
        label = c["section"].replace("-", " ").capitalize()
        prefix = cfg.get("section_label", "Source")
        return (f'<a href="{cfg["section_url"]}#{c["section"]}">'
                f'{html.escape(prefix)}: {html.escape(label)}</a>')
    if c.get("source_url"):
        title = html.escape(c.get("source_title") or "Source")
        return f'<a href="{html.escape(c["source_url"])}">{title}</a>'
    return ""


def valid(c):
    if c.get("type") == "basic":
        return bool(c.get("front")) and bool(c.get("back"))
    if c.get("type") == "cloze":
        return "{{c1::" in c.get("text", "")
    return False


def main(folder):
    folder = Path(folder)
    cfg = json.loads((folder / "deck.json").read_text())
    basic, cloze = models(cfg)
    root = cfg["name"]

    cards = []
    for path in sorted((folder / "cards").glob("*.json")):
        sub = cfg.get("subdecks", {}).get(path.stem, cfg.get("default_subdeck"))
        deck = f"{root}::{sub}" if sub else root
        for i, c in enumerate(json.loads(path.read_text())):
            if not valid(c):
                print("skip (malformed):", c.get("front") or c.get("text"), file=sys.stderr)
                continue
            c["_deck"] = deck
            c["_order"] = (int(c.get("priority", 2)), path.stem, i)
            cards.append(c)

    seen, decks = set(), {}
    # Sort inputs for export; Anki determines the study order.
    for c in sorted(cards, key=lambda c: c["_order"]):
        key = (c.get("front") or c.get("text")).strip().lower()
        if key in seen:
            continue
        seen.add(key)
        tags = [slug(t) for t in c.get("tags", []) if t]
        tags += [f"kind::{c.get('kind', 'idea')}", f"priority::{c.get('priority', 2)}"]
        tags.append(cfg.get("section_tag", "from::section") if c.get("section")
                    else cfg.get("source_tag", "from::source"))
        kind = KIND_LABEL.get(c.get("kind"), "")
        guid = genanki.guid_for(root, key)
        if c["type"] == "basic":
            fields = [c.get("context", ""), c["front"], c["back"], c.get("extra", ""),
                      source_html(c, cfg), kind]
            note = genanki.Note(model=basic, fields=fields, tags=tags, guid=guid)
        else:
            fields = [c.get("context", ""), c["text"], c.get("extra", ""),
                      source_html(c, cfg), kind]
            note = genanki.Note(model=cloze, fields=fields, tags=tags, guid=guid)
        name = c["_deck"]
        decks.setdefault(name, genanki.Deck(deck_id(name), name)).add_note(note)

    out = folder / cfg.get("output", "deck.apkg")
    genanki.Package(list(decks.values())).write_to_file(out)
    for name, d in sorted(decks.items()):
        print(f"{len(d.notes):5d}  {name}")
    print(f"{sum(len(d.notes) for d in decks.values()):5d}  notes in {out}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
