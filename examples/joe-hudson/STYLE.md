# Card style for the Joe Hudson deck

The deck follows Piotr Wozniak's SuperMemo rules, "Twenty rules of formulating
knowledge" (1999). The content is Joe Hudson's advice. Where his own advice
touches how to learn, the deck follows it too.

## The SuperMemo rules, as they apply here

1. **Understand before you memorize.** Make a card only for an idea that the
   source explains. Do not make a card for a slogan with no meaning behind it.
2. **Learn before you memorize.** The essay gives the overall picture. Core
   cards come first (priority 1), so later cards build on them.
3. **Build on the basics.** Basic ideas (the Golden Algorithm, Emotional
   Inquiry, VIEW, welcoming resistance) get simple cards with high priority.
4. **Minimum information.** One fact per card. The answer is a few words or one
   short sentence. If an answer needs "and", think about two cards.
5. **Cloze deletion.** Use cloze cards for a key sentence where one word or
   phrase carries the idea: `{{c1::...}}`.
6. **Imagery.** Keep his images: the child looking at a frog, water poured into
   a new container, the actor who plays rage, the horseshoe.
7. **Mnemonics.** Keep his acronyms (VIEW). Do not invent new ones.
8. **Graphic deletion.** Not used (no images).
9. **Avoid sets.** Never ask "name all X". A set is hard to recall and has no order.
10. **Avoid enumerations.** Do not make a cloze card with three or more
    blanks. Such cards are hard to recall: each blank shows you the rest of
    the list, and the items are easy to mix up. For an
    ordered list (the six steps), make one basic card for each step, and
    name the step before it in the question. For an unordered list (the
    five company principles), make one card per item, asking from the
    item's name to its meaning or the other way.
11. **Combat interference.** Similar cards must be easy to tell apart. Put the
    distinguishing word in the question (for example the feeling's name).
12. **Optimize wording.** Short, plain words. Simplified Technical English:
    short sentences, active voice, the same word for the same thing.
13. **Refer to other memories.** Link a card to an idea already in the deck when
    the source does ("This is the Golden Algorithm applied to money").
14. **Personalize and give examples.** Keep his concrete examples. Practice cards
    may ask the learner to use their own life ("Name one 'I can't' from today").
15. **Rely on emotional states.** Keep vivid stories, marked as his stories.
16. **Context cues.** Start each front with a short context in the `context`
    field (for example "Golden Algorithm", "Shame", "Money game"). The build
    script prints it above the question, so the question itself can be short.
17. **Redundancy is allowed.** One idea may get a card from two directions if
    both are useful (term → meaning, situation → term).
18. **Provide sources.** Every card has a source: an essay section anchor, or a
    transcript's title and URL.
19. **Date stamping.** Not needed for most cards. Use only for a claim that
    changes over time (for example "as of 2025, he coaches ...").
20. **Prioritize.** `priority` 1 = core method and safety, 2 = per-feeling
    practices and principles, 3 = extra detail, stories and transcript extras.

## Hudson's own advice, applied to the deck

- **Thinking about a feeling is not feeling it.** So the deck has a few
  `practice` cards. Their front invites a short exercise ("Try now, 1 minute:
  ..."), and the back says what to notice. Keep them few: about one per main
  practice. They are invitations, not tests.
- **Not a "should".** Word practice cards as experiments ("Try ...", "Notice
  ..."), never as orders or guilt ("You should ...").
- **Serious, not literal.** Write his claims as his claims ("Hudson says ...",
  "In his view ..."). He is a coach. His method is not a tested treatment.
- **Stories are stories.** A story from his life gets `kind: "story"` and the
  front says it is his story.
- **Safety.** Keep the safety caveats as their own cards (`kind: "safety"`,
  priority 1): never aim anger at a person without consent; stop and rest if
  flooded; trauma work needs a licensed therapist; crisis line for thoughts of
  harm. Never cut a caveat from a card whose practice needs it.
- Where the essay's evidence section says research points the other way (for
  example on venting anger), make a card that says so.

## Card format (JSON)

Each output file is a JSON array of objects:

```json
{
  "type": "basic",                  // "basic" or "cloze"
  "context": "Golden Algorithm",    // short cue, shown above the question
  "front": "What comes back through the way you avoid an emotion?",
  "back": "The same emotion.",      // basic only. Short. HTML <br> allowed
  "text": "",                       // cloze only: sentence with {{c1::...}}
  "extra": "Example: skipping the gym to dodge guilt makes more guilt.",
  "kind": "idea",                   // idea | practice | story | safety | evidence
  "priority": 1,
  "section": "the-core-method",     // essay anchor id, if from the essay
  "source_title": "",               // transcript title, if from a transcript
  "source_url": "",                 // transcript URL, if from a transcript
  "tags": ["golden-algorithm"],
  "key": ""                         // optional: the old question, if reworded
}
```

Rules for fields: `back` is empty for cloze; `text` is empty for basic. The
build stops if a cloze card has `front` or `back`, if a basic card has `text`,
or if a card has a field that is not shown above. Leave `key` out, or empty,
unless you reword the question of a card that people already have: then put
the old question in `key`, so the card keeps its id and its review history. Keep
`back` to about 25 words; put more detail in `extra`. Do not copy long passages
of a transcript: paraphrase, and quote at most a short phrase. Use plain ASCII
quotes or HTML entities, and escape JSON correctly.
