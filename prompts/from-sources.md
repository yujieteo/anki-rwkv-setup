You write Anki flashcards for a deck about <topic>. The main deck comes
from a summary; your job is to add cards for ideas from raw sources that
the summary does NOT already cover.

First read the style guide in full: <deck folder>/STYLE.md. It gives
SuperMemo's 20 rules as they apply here, any extra rules for this topic,
and the exact JSON format.

The summary (already covered by other writers) is <summary file>. Skim its
headings and main sections so you know what it holds, and search it for key
words before you make a card. Skip an idea the summary already states. Keep
an idea that the summary only names in passing if the source explains it in
a way worth remembering (a new example, a step, a distinction).

Your sources are in <source folder>. Each file has front matter with
`title` and `source` (the URL). Your files:
- <file 1>
- <file 2>
- ...

For each card, set `source_title` to the file's `title` and `source_url` to
its `source`. Leave `section` empty. Use priority 2 for a practice or
principle the learner can use, and 3 for detail and stories. Name ideas from
other speakers as theirs, or skip them. Mark personal stories as
`kind: "story"`. Paraphrase; never copy more than a short phrase.
Transcripts may be auto-generated and contain errors: do not make a card
from a garbled passage.

Write the result as a valid JSON array to <deck folder>/cards/<file name>.json.
Then check that it parses:

    python3 -c "import json,sys;print(len(json.load(open(sys.argv[1]))))" <file>

Do not touch any other file.

Reply with: the card count per source, and a one-line note on anything you
skipped as already in the summary. Keep the reply short.
