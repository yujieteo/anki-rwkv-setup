"""Build an Anki deck (.apkg) from a folder of card files.

Usage:
    uv run --with genanki==0.13.1 python build.py examples/joe-hudson

The folder holds:
    deck.json     deck name, output file name, note type ids, subdecks
    cards/*.json  card files (format in docs/card-format.md)

Each note's id comes from its own text, so importing a rebuilt file
updates the notes you already have instead of adding copies.

The build checks deck.json and every card before it writes anything.
If deck.json or a card is malformed, or two cards have the same
question, it prints one line per problem as "file: reason" or
"file[index]: reason" and stops with exit code 1. The old .apkg is then
left as it was.
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

# Each card type and the fields it uses. The first field is the question:
# it gives the note its id, unless the card has a "key".
TYPES = {"basic": ("front", "back"), "cloze": ("text",)}
# The fields of the other card types, which a card must leave empty.
UNUSED = {t: tuple(f for other in TYPES if other != t for f in TYPES[other])
          for t in TYPES}

# Each kind and the label it shows on the card. "idea" shows no label.
# The "kind_labels" map in deck.json can change any of these labels.
KIND_LABEL = {"idea": "", "practice": "try it", "story": "story",
              "safety": "safety", "evidence": "evidence"}
PRIORITIES = (1, 2, 3)

# The keys of deck.json. The two ids are required; the rest are optional.
DECK_IDS = ("basic_model_id", "cloze_model_id")
DECK_TEXT = ("output", "section_url", "section_label", "section_tag",
             "source_tag", "default_subdeck")

# The fields a card may have. Any other field is a spelling mistake.
CARD_FIELDS = {"type", "context", "front", "back", "text", "extra", "kind",
               "priority", "section", "source_title", "source_url", "tags", "key"}


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


def source(c, cfg):
    """Return the card's source link (HTML) and its source tag.

    The link points to the essay section if the card has a "section",
    else to "source_url", else there is no link. The tag says whether the
    card comes from the section page (a "section", or a "source_url" equal
    to "section_url") or from another source.
    """
    section_url = cfg.get("section_url")
    if c.get("section") and section_url:
        label = c["section"].replace("-", " ").capitalize()
        prefix = cfg.get("section_label", "Source")
        href = html.escape(f'{section_url}#{c["section"]}')
        link = f'<a href="{href}">{html.escape(prefix)}: {html.escape(label)}</a>'
    elif c.get("source_url"):
        title = html.escape(c.get("source_title") or "Source")
        link = f'<a href="{html.escape(c["source_url"])}">{title}</a>'
    else:
        link = ""
    from_section = c.get("section") or (section_url and c.get("source_url") == section_url)
    tag = (cfg.get("section_tag", "from::section") if from_section
           else cfg.get("source_tag", "from::source"))
    return link, tag


def deck_problems(cfg):
    """Return the reasons deck.json cannot be used (empty if it is fine)."""
    if not isinstance(cfg, dict):
        return ["must hold a JSON object"]
    out = []
    unknown = sorted(set(cfg) - {"name", "subdecks", "kind_labels", *DECK_IDS, *DECK_TEXT})
    if unknown:
        out.append(f"unknown key(s) {unknown}; check the spelling in docs/card-format.md")
    if not isinstance(cfg.get("name"), str) or not cfg["name"].strip():
        out.append("needs a non-empty 'name'")
    for key in DECK_IDS:
        v = cfg.get(key)
        if key not in cfg:
            out.append(f"needs {key!r}, a large whole number that never changes")
        elif type(v) is not int or not 0 < v < 2**63:
            out.append(f"{key} is {v!r}; it must be a whole number above 0")
    if cfg.get(DECK_IDS[0]) == cfg.get(DECK_IDS[1]) and DECK_IDS[0] in cfg:
        out.append("basic_model_id and cloze_model_id must be different")
    for key in DECK_TEXT:
        if key in cfg and (not isinstance(cfg[key], str) or not cfg[key].strip()):
            out.append(f"{key} must be non-empty text, or left out")
    output = cfg.get("output")
    if isinstance(output, str) and output.strip() and (
            "/" in output or "\\" in output or not output.endswith(".apkg")):
        out.append(f"output is {output!r}; it must be a file name that ends in .apkg")
    subdecks = cfg.get("subdecks", {})
    if not isinstance(subdecks, dict) or not all(
            isinstance(v, str) and v.strip() for v in subdecks.values()):
        out.append("subdecks must map card file names to non-empty subdeck names")
    labels = cfg.get("kind_labels", {})
    if not isinstance(labels, dict) or not all(
            k in KIND_LABEL and isinstance(v, str) for k, v in labels.items()):
        out.append(f"kind_labels must map kinds from {list(KIND_LABEL)} to label text")
    return out


def problems(c, cfg):
    """Return the reasons the card cannot be built (empty if it is fine).

    main() has already filled in the default kind and priority.
    """
    if not isinstance(c, dict):
        return ["a card must be a JSON object"]
    card_type = c.get("type")
    if card_type not in TYPES:
        return [f"type is {card_type!r}; it must be one of {sorted(TYPES)}"]
    out = []
    unknown = sorted(set(c) - CARD_FIELDS)
    if unknown:
        out.append(f"unknown field(s) {unknown}; check the spelling in docs/card-format.md")
    for f in TYPES[card_type]:
        if not isinstance(c.get(f), str) or not c[f].strip():
            out.append(f"a {card_type} card needs a non-empty {f!r}")
    for f in UNUSED[card_type]:
        if c.get(f):
            out.append(f"a {card_type} card must leave {f!r} empty")
    text = c.get("text")
    if card_type == "cloze" and isinstance(text, str) and text.strip() and "{{c1::" not in text:
        out.append("a cloze card's text needs {{c1::...}}")
    if c["kind"] not in KIND_LABEL:
        out.append(f"kind is {c['kind']!r}; it must be one of {list(KIND_LABEL)}")
    p = c["priority"]
    if type(p) is not int or p not in PRIORITIES:
        out.append(f"priority is {p!r}; it must be one of {list(PRIORITIES)}")
    if not isinstance(c.get("tags", []), list):
        out.append("tags must be a list")
    key = c.get("key", "")
    if not isinstance(key, str) or (key and not key.strip()):
        out.append("key must be text: the old question, or empty")
    if c.get("section") and not cfg.get("section_url"):
        out.append("the card has a section, but deck.json has no section_url")
    return out


def identity(c):
    """The text that gives the note its id: "key", else the question."""
    return (c.get("key") or c[TYPES[c["type"]][0]]).strip().lower()


def main(folder):
    folder = Path(folder)
    deck_file = folder / "deck.json"
    try:
        cfg = json.loads(deck_file.read_text())
    except FileNotFoundError:
        sys.exit(f"{deck_file}: not found. No deck was written.")
    except json.JSONDecodeError as e:
        sys.exit(f"{deck_file}: not valid JSON: {e}. No deck was written.")
    bad = deck_problems(cfg)
    if bad:
        print("\n".join(f"{deck_file}: {reason}" for reason in bad), file=sys.stderr)
        sys.exit(f"{len(bad)} problem(s) in deck.json. No deck was written.")
    basic, cloze = models(cfg)
    root = cfg["name"]
    kind_label = {**KIND_LABEL, **cfg.get("kind_labels", {})}

    # Read and check every card. Nothing is written if any card fails.
    cards, errors, first = [], [], {}
    for path in sorted((folder / "cards").glob("*.json")):
        sub = cfg.get("subdecks", {}).get(path.stem, cfg.get("default_subdeck"))
        deck = f"{root}::{sub}" if sub else root
        try:
            content = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            errors.append(f"{path}: not valid JSON: {e}")
            continue
        if not isinstance(content, list):
            errors.append(f"{path}: the file must hold a JSON array of cards")
            continue
        for i, c in enumerate(content):
            where = f"{path}[{i}]"
            if isinstance(c, dict):
                c = {"kind": "idea", "priority": 2, **c}
            bad = problems(c, cfg)
            if not bad:
                key = identity(c)
                if key in first:
                    bad = [f"same question (or key) as {first[key]}; "
                           "reword one of them or delete one"]
                else:
                    first[key] = where
            errors += [f"{where}: {reason}" for reason in bad]
            if not bad:
                cards.append((c["priority"], path.stem, i, deck, c))
    if errors:
        print("\n".join(errors), file=sys.stderr)
        sys.exit(f"{len(errors)} problem(s) in the card files. No deck was written.")

    decks = {}
    # Each new card gets its own queue position (due), priority 1 first.
    # Without it every new card has position 0 and the order is lost.
    for due, (*_, deck, c) in enumerate(sorted(cards, key=lambda x: x[:3]), start=1):
        tags = [slug(t) for t in c.get("tags", []) if t]
        tags += [f"kind::{c['kind']}", f"priority::{c['priority']}"]
        link, source_tag = source(c, cfg)
        tags.append(source_tag)
        kind = html.escape(kind_label[c["kind"]])
        guid = genanki.guid_for(root, identity(c))
        if c["type"] == "basic":
            model = basic
            fields = [c.get("context", ""), c["front"], c["back"], c.get("extra", ""), link, kind]
        else:
            model = cloze
            fields = [c.get("context", ""), c["text"], c.get("extra", ""), link, kind]
        note = genanki.Note(model=model, fields=fields, tags=tags, guid=guid, due=due)
        decks.setdefault(deck, genanki.Deck(deck_id(deck), deck)).add_note(note)

    out = folder / cfg.get("output", "deck.apkg")
    genanki.Package(list(decks.values())).write_to_file(out)
    for name, d in sorted(decks.items()):
        print(f"{len(d.notes):5d}  {name}")
    print(f"{sum(len(d.notes) for d in decks.values()):5d}  notes in {out}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
