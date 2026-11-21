# Anki with the RWKV-P scheduler

This repository sets up Anki with **RWKV-P**, the spaced-repetition model
that leads the [open-spaced-repetition benchmark](https://github.com/open-spaced-repetition/srs-benchmark),
and shows how to build a deck for it from your own notes. The example is a
deck of 641 notes (723 cards) on the coaching advice of Joe Hudson.

It contains:

- `install-macos.sh`: installs the Anki build that runs RWKV.
- `build.py`: turns a folder of card files into an `.apkg` deck.
- `examples/joe-hudson/`: the example deck, its style guide and its card
  files, plus the built `joe-hudson.apkg`.
- `prompts/`: the prompts used to have AI agents write the cards.
- `docs/card-format.md`: the card file format.

## What RWKV-P is

Anki decides when to show each card again. It decides by predicting how
likely you are to remember the card. Older schedulers (SM-2, FSRS) use a
small formula for each card. RWKV is a neural network trained on the review
histories of thousands of Anki users. It looks at your whole review
history: every card, every answer, answer times, the deck structure and the
time of day.

The benchmark has two RWKV models. **RWKV-P** predicts whether you will
recall a card right now. Its newer name is **RWKV-Instant**, and the Anki
build uses that name. **RWKV-Curve** predicts how recall falls over time.
On the benchmark's main table, RWKV-Instant has a log loss of 0.277 and an
AUC of 0.833. FSRS-7 has 0.340 and 0.717 (its "recency" variant has 0.337
and 0.722). These figures are from the table without same-day reviews.
Lower log loss is better, and higher AUC is better. Compared collection by collection, RWKV-P does better
than every other model on 99.6 to 100% of collections.

Two limits:

- The benchmark measures how well a model *predicts* recall, not how much
  you learn.
- RWKV-Instant has no forgetting curve, so it cannot write due dates. It
  picks which cards to show by their recall right now. A second model, the
  "fallback", writes due dates for statistics and for phones.

RWKV runs inside an **unofficial Anki build** by
[JSchoreels](https://github.com/JSchoreels/anki). It is not made by the
Anki developers. The research behind it is in
[JSchoreels/anki-rwkv](https://github.com/JSchoreels/anki-rwkv) and
[Expertium/rwkv-anki-autoresearch](https://github.com/Expertium/rwkv-anki-autoresearch).

## What you need

- A Mac. The build also has Windows and Linux versions on its
  [releases page](https://github.com/JSchoreels/anki/releases), but the
  script here is for macOS.
- An [AnkiWeb](https://ankiweb.net) account, if you want to sync.
- Optional: AnkiMobile on iPhone (paid) or AnkiDroid on Android. Phones run
  the official app, which cannot run RWKV. See [Phone](#phone).
- To build your own deck: Python 3 and [uv](https://docs.astral.sh/uv/).

## 1. Install the RWKV build

Quit Anki, then run:

```bash
./install-macos.sh
```

The script downloads the tested release (`26.09.4+fsrs7.build.115`) for
your Mac, checks its SHA-256 hash against the one GitHub reports, moves
your current `/Applications/Anki.app` to the Trash, and copies in the RWKV
build. Your cards and settings in `~/Library/Application Support/Anki2` are
not touched. Run `./install-macos.sh latest` for the newest release.

The build is not notarized by Apple. A file downloaded with `curl`, as the
script does, opens normally. If you download the `.dmg` in a browser
instead, macOS may refuse to open it. Read the build's own README before you
decide to allow it.

Do not install official Anki updates afterwards: they replace this build.
Get updates from the build's releases page or by running the script again.

## 2. Turn on RWKV-P

To try RWKV-P on the example deck, import it in step 3 first. Then open
Options on the **Joe Hudson** parent deck.

1. Open Anki. On a new install, pick a language, then sign in to AnkiWeb
   with **Sync** if you use it.
2. Click the deck you want to change, then **Options** (or press `o`).
3. Open the drop-down beside **Save** and choose **Clone Preset**. Give the
   new [preset](https://docs.ankiweb.net/manual/deck-options#presets) a
   name such as **Joe Hudson RWKV**. Edit this preset rather than
   **Default** or one shared with unrelated decks.
4. Scroll to **Scheduler**. Under **Review scheduler**, click
   **RWKV-Instant**. This is RWKV-P.
5. Under **Fallback**, keep **FSRS-7** (the build's recommendation). It
   writes the due dates that phones use, and phones schedule their own
   answers with FSRS, so the two stay consistent.
6. Under **RWKV → Advanced → Model size**, pick a size. **Big** is the
   most accurate and needs more memory and a slower first build. For a few
   thousand cards it is small (about 13 MB for 716 cards). **Small** is the
   default.
7. Under **Display Order**, set **New card gather order** to **Ascending
   position**. The default gathers one subdeck at a time, so the deck's
   priority order would be lost across subdecks.
8. For the Joe Hudson example, choose **Save to All Subdecks** in the Save
   drop-down to assign the new preset to the parent and its subdecks. If
   you only want to change the selected deck, use **Save** instead. When
   Anki asks to build the RWKV state, click **Build State Only**. It shows
   "RWKV state cache ready" when done.

To verify the setup, reopen Options on the parent and its subdecks. They
should use the dedicated preset if you applied it to all of them. An
unrelated deck should still show its original preset and scheduler.

## 3. Import the example deck

Download [`examples/joe-hudson/joe-hudson.apkg`](examples/joe-hudson/joe-hudson.apkg)
and double-click it, or use **File → Import** in Anki. Then do step 2 for
the **Joe Hudson** deck.

The deck has four subdecks: the core method, the feelings, problems and
evidence, and extra cards from interviews. Each new card has a queue
position, and priority-1 cards (the core method and the safety cards)
have the lowest positions. When you import the deck for the first time
and set the gather order in item 7 of step 2, the priority-1 cards come
first.

### If you imported an earlier version

The first version of the package gave every new card position 0. An
import never changes the position of a card that is already in your
collection. Only cards that are new to your collection get their
position from the package. So if you imported the first version,
importing the new one does not restore the order. Your existing cards
stay at position 0, and priority-1 cards can come after other cards. To
check, open **Browse**, search for `deck:"Joe Hudson" is:new`, and look
at the **Due** column. If most cards show "New #0", you have this
problem.

To put the priority-1 cards first again, keep your cards and do this
once:

1. Click **Browse** and search for
   `deck:"Joe Hudson" tag:priority::1 is:new`.
2. Select all cards (**Edit → Select All**).
3. Choose **Cards → Reposition**. Set **Start position** to 0 and
   **Step** to 1. Turn off **Randomize order**, and turn on **Shift
   position of existing cards**. Without the shift, the other new cards
   stay at position 0 and mix with the priority-1 cards.
4. Click **OK**.

This keeps your notes and your review history. It puts the priority-1
cards first, but it does not restore the order of the other cards among
themselves. Most of those cards share one position.

To study only the priority-1 cards without changing positions, use
**Custom Study** on the **Joe Hudson** deck. Choose **Study by card
state or tag**, then **New cards only**, and select the tag
`priority::1`. Anki makes a temporary deck with those cards.

## Phone

Phones run the official AnkiMobile or AnkiDroid, which do not load RWKV.
They show cards by the due dates the fallback wrote on the computer, and
schedule your answers with FSRS. The computer reads those answers at the
next sync and updates RWKV.

1. On the computer, click **Sync**.
2. On the phone, sign in to the same AnkiWeb account and sync.

If the phone or the computer says a **full sync** is needed, it asks which
side to keep. **Upload** replaces everything on AnkiWeb with this device's
collection. **Download** replaces this device's collection with AnkiWeb's.
Either one permanently deletes the decks on the other side that are not in
the copy you keep. Export a backup first (**File → Export → Anki Collection
Package**) if you might want them.

## Daily use

1. Open Anki on the computer. It syncs on open.
2. Click the deck, then **Study Now**. RWKV-P shows the cards you are most
   likely to forget first, then the new cards.
3. Answer honestly: **Again** if you forgot, **Good** if you remembered.
   RWKV-P learns from your answers.
4. Close Anki when you finish. It syncs on close.

On days away from the computer, study on the phone and sync. Missing a day
does little harm, because RWKV-P always puts the most-forgotten cards
first. If the daily load feels too heavy, lower **New cards/day** in the
deck options.

## Make your own deck

1. **Collect your source.** A summary you wrote, plus any raw sources such
   as transcripts or articles. Each raw source needs a title and a URL so
   that each card can link back to it.
2. **Write a style guide.** Copy
   [`examples/joe-hudson/STYLE.md`](examples/joe-hudson/STYLE.md). The
   first part applies Piotr Wozniak's
   [twenty rules of formulating knowledge](https://www.supermemo.com/en/blog/twenty-rules-of-formulating-knowledge)
   and works for any topic. Replace the second part (Hudson's own advice)
   with rules for your topic.
3. **Write about ten cards** and check them before you write the rest.
4. **Write the cards.** By hand, or with AI agents and the prompts in
   [`prompts/`](prompts/). The format is in
   [`docs/card-format.md`](docs/card-format.md).
5. **Make a `deck.json`** like the example's. Pick two new large numbers
   for the note type ids.
6. **Build:**

   ```bash
   uv run --with genanki python build.py path/to/your-deck
   ```

7. **Import** the `.apkg`, and turn on RWKV-P (step 2).

To change cards later, edit the card files, build again and import again.
By default, the note's ID is based on the deck name and the question
(or cloze text). To reword a question without changing its ID, put the
original question in the card's [`key` field](docs/card-format.md) before
rebuilding. If the card already has a `key`, leave it unchanged on
later edits. With the same deck name and note type, Anki can update the
existing note on import without starting its review history over.

## The example deck

The cards come from two sources:

- [The Joe Hudson toolkit for the feelings you avoid](https://teoyujie.org/essays/joe-hudson-toolkit/),
  an essay that sorts his practices by the feeling you want to avoid. Cards
  from it link to the matching section.
- 24 interviews and talks by Hudson. Cards from them link to the video or
  post. The transcripts are not included here.

Joe Hudson is an executive coach and the founder of Art of Accomplishment.
This deck is not made or approved by him. The cards paraphrase his public
talks. His method is coaching, not a tested treatment. The deck keeps his
safety advice as its own cards, and some cards say where research points
the other way. If you have trauma, or you feel overwhelmed or outside your
body when you work with feelings, work with a licensed therapist.

## License

The code (`build.py`, `install-macos.sh`) is under the MIT License. See
[LICENSE](LICENSE).
