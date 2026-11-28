# Card format

A deck folder holds `deck.json` and a `cards/` folder of JSON files. Each
card file is a JSON array of card objects. `build.py` reads every file in
`cards/` and writes one `.apkg`.

## deck.json

| Key | Meaning |
|---|---|
| `name` | Top-level deck name. Also names the two note types (`<name> Basic`, `<name> Cloze`). |
| `output` | Optional. File name of the `.apkg` to write, inside the deck folder. The default is `deck.apkg`. |
| `basic_model_id`, `cloze_model_id` | Optional. Fixed numbers for the note types; if omitted, derived deterministically from `name`. |
| `section_url` | Optional. A card with a `section` links to `section_url#section`. |
| `section_label` | Optional. Text before the section name in that link, for example `Essay`. The default is `Source`. |
| `section_tag`, `source_tag` | Optional tags. A card with a `section` or a `source_url` matching `section_url` gets `section_tag`; other cards get `source_tag`. The defaults are `from::section` and `from::source`. |
| `kind_labels` | Optional map from a `kind` to the label the card shows, for example `{"story": "his story", "theorem": "theorem"}`. Overrides default labels (`idea`, `practice`, `story`, `safety`, `evidence`) or declares new kinds. An empty label shows nothing. |
| `subdecks` | Optional map from a card file's name (without `.json`) to a subdeck name. |
| `default_subdeck` | Subdeck for card files not named in `subdecks`. Leave it out to put them in the top deck. |

## A card

```json
{
  "type": "basic",
  "context": "Golden Algorithm",
  "front": "What comes back through the way you avoid an emotion?",
  "back": "The same emotion.",
  "extra": "Example: skipping the gym to dodge guilt makes more guilt.",
  "kind": "idea",
  "priority": 1,
  "section": "the-core-method",
  "tags": ["golden-algorithm"]
}
```

| Field | Meaning |
|---|---|
| `type` | `basic` (question and answer) or `cloze` (fill in the blank). |
| `context` | A short cue shown above the question. |
| `front`, `back` | The question and the answer, for `basic`. HTML such as `<br>` and `<b>` is allowed. |
| `text` | For `cloze`: a sentence with `{{c1::hidden part}}`. You can add `{{c2::...}}`. For a list of three or more items, make one basic card per item instead of more blanks. |
| `extra` | More detail, shown under the answer. |
| `kind` | `idea`, `practice`, `story`, `safety`, `evidence`, or any custom kind declared in `kind_labels`. |
| `priority` | Positive integer (1 is highest; default 2). `build.py` numbers new cards in this order. For Anki to follow it across subdecks, set **New card gather order** to "Ascending position" in Deck Options. |
| `section` | An anchor id on the page at `section_url`. |
| `source_title`, `source_url` | Used when there is no `section`: the link shown on the card. |
| `tags` | Extra Anki tags. `kind::` and `priority::` tags are added for you. |
| `key` | Optional. When you reword a card's question, put the old question here. The card keeps its id, so re-importing updates it and keeps its review history. |

## Checks

Run `build.py --check <folder>` to validate `deck.json` and all cards without writing a `.apkg`.

`build.py` checks `deck.json` first and stops if:

- `deck.json` is missing, is not valid JSON, or does not hold a JSON object.
- It has a key that is not in the table above (often a spelling mistake).
- `name` is missing or empty.
- `basic_model_id` or `cloze_model_id` (if given) is not a whole number above 0, or the two are the same.
- An optional text key is not text.
- `output` has a folder in it or does not end in `.apkg`.
- `subdecks` does not map file names to non-empty subdeck names.
- `kind_labels` does not map non-empty kind names to text.

Then `build.py` checks every card before it writes the `.apkg`. If any card fails a check, it prints one line per problem and stops with exit code 1.

A card fails if:

- `type` is not `basic` or `cloze`.
- It has a field that is not in the table above (often a spelling mistake, such as `sorce_url`).
- A `basic` card has no `front` or no `back`, or has non-empty `text`.
- A `cloze` card has no `{{cN::...}}` in `text`, or has non-empty `front` or `back`.
- `kind` is not a built-in kind or declared in `kind_labels`, or `priority` is not a positive integer. Leave them out to get `idea` and 2.
- `tags` is not a list of text, or `key` is not text.
- A card file is not valid JSON, or does not hold a JSON array.
- The card has a `section`, but `deck.json` has no `section_url`.
- Two cards have the same question (or the same cloze text, or the same `key`). Case and spaces at the ends do not count. Reword one of the two cards, or delete one.
