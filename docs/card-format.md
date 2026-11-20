# Card format

A deck folder holds `deck.json` and a `cards/` folder of JSON files. Each
card file is a JSON array of card objects. `build.py` reads every file in
`cards/` and writes one `.apkg`.

## deck.json

| Key | Meaning |
|---|---|
| `name` | Top-level deck name. Also names the two note types (`<name> Basic`, `<name> Cloze`). |
| `output` | File name of the `.apkg` to write, inside the deck folder. |
| `basic_model_id`, `cloze_model_id` | Fixed numbers for the note types. Pick any two large numbers once and never change them, so that a rebuilt deck updates the old notes. |
| `section_url` | Optional. A card with a `section` links to `section_url#section`. |
| `section_label` | Text before the section name in that link, for example `Essay`. |
| `section_tag`, `source_tag` | Optional tags for cards with and without a `section`. |
| `subdecks` | Optional map from a card file's name (without `.json`) to a subdeck name. |
| `default_subdeck` | Subdeck for card files not named in `subdecks`. Leave it out to put them in the top deck. |

## A card

```json
{
  "type": "basic",
  "context": "Golden Algorithm",
  "front": "What comes back through the way you avoid an emotion?",
  "back": "The same emotion.",
  "text": "",
  "extra": "Example: skipping the gym to dodge guilt makes more guilt.",
  "kind": "idea",
  "priority": 1,
  "section": "the-core-method",
  "source_title": "",
  "source_url": "",
  "tags": ["golden-algorithm"]
}
```

| Field | Meaning |
|---|---|
| `type` | `basic` (question and answer) or `cloze` (fill in the blank). |
| `context` | A short cue shown above the question. |
| `front`, `back` | The question and the answer, for `basic`. HTML such as `<br>` and `<b>` is allowed. |
| `text` | For `cloze`: a sentence with `{{c1::hidden part}}`. Use `c2`, `c3`, ... for overlapping clozes on an ordered list. |
| `extra` | More detail, shown under the answer. |
| `kind` | `idea`, `practice`, `story`, `safety` or `evidence`. The last four show a small label on the card. |
| `priority` | 1, 2 or 3. `build.py` numbers new cards in this order. For Anki to follow it across subdecks, set **New card gather order** to "Ascending position" in Deck Options. |
| `section` | An anchor id on the page at `section_url`. |
| `source_title`, `source_url` | Used when there is no `section`: the link shown on the card. |
| `tags` | Extra Anki tags. `kind::` and `priority::` tags are added for you. |
| `key` | Optional. When you reword a card's question, put the old question here. The card keeps its id, so re-importing updates it and keeps its review history. |

Two cards with the same question (or the same cloze text) are merged, and
only the first is kept.
