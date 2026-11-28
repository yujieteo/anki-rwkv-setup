You write Anki flashcards for a deck about <topic>.

First read the style guide in full: <deck folder>/STYLE.md. It gives
SuperMemo's 20 rules as they apply here, any extra rules for this topic,
and the exact JSON format.

Your source: <summary file>, lines <start> to <end> only (the sections
<list of section headings>). Section anchor ids are the heading in lowercase
with spaces as hyphens (for example `the-core-method`). Put the anchor of
the section a card comes from in `section`. Leave `source_title` and
`source_url` empty. You may read other lines for context only; other
writers cover them, so do not make cards from them.

Cover every idea in your lines that is worth remembering. For a list
of three or more items, write one basic card per item, and never a cloze
card with three or more blanks. For an ordered list, name the step before
in the question. Keep
every safety caveat as its own card. Add a few practice cards, about one
per main practice. Ignore lines that only list links or sources.

Write the result as a valid JSON array to <deck folder>/cards/<file name>.json.
Then validate the deck:

    uv run --no-project --with genanki python build.py --check <deck folder>

Do not touch any other file.

Reply with: the card count, the count per kind and per priority, and any
idea you left out on purpose and why. Keep the reply short.
