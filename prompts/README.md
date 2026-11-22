# Prompts for writing cards with an AI model

The example deck was written by seven AI agents working in parallel. Each
one read the style guide and one part of the source, and wrote one card
file. These are the two prompts, with the specific file names replaced by
placeholders. Fill in the `<...>` parts and give one prompt to each agent.

Split the work so that no two agents read the same part of the source.
Agents that write from a summary should each get a range of sections.
Agents that write from raw sources (transcripts, articles) should each get
a few files of about the same total length.

Before you run them all, write about ten cards yourself, or ask for ten,
and check the style. It is much cheaper to fix the style guide than 600
cards.

- [`from-summary.md`](from-summary.md): cards from your own notes or a summary.
- [`from-sources.md`](from-sources.md): extra cards from raw sources, skipping
  what the summary already covers.

After the agents finish, run `build.py`. Agents that work in parallel
sometimes write the same question twice. The build then lists each pair
and writes no deck, so reword or delete one card of each pair and build
again. Read a random sample of cards before you import the deck.
