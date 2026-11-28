"""Tests for the card checks in build.py. They need genanki, not Anki."""

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import zipfile
from contextlib import closing
from pathlib import Path

BUILD = Path(__file__).resolve().parent.parent / "build.py"

DECK = {"name": "Test", "output": "test.apkg",
        "basic_model_id": 1700000001, "cloze_model_id": 1700000002}
BASIC = {"type": "basic", "front": "What is one?", "back": "One."}
CLOZE = {"type": "cloze", "text": "One plus one is {{c1::two}}."}


class BuildTest(unittest.TestCase):
    def build(self, cards, deck=DECK):
        """Build a deck from {file name: cards}. Return the result and the output path."""
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        folder = Path(work.name)
        (folder / "deck.json").write_text(json.dumps(deck))
        (folder / "cards").mkdir()
        for name, content in cards.items():
            (folder / "cards" / f"{name}.json").write_text(json.dumps(content))
        return self.run_build(folder), folder / deck["output"]

    def run_build(self, folder):
        """Run build.py on a deck folder and return the result."""
        return subprocess.run([sys.executable, str(BUILD), str(folder)],
                              capture_output=True, text=True)

    def test_good_cards_build(self):
        # Unused fields written as "" (as in the example deck) are fine.
        empty = {"front": "", "back": "", "key": "", "section": "", "source_url": ""}
        result, out = self.build({"a": [BASIC, {**CLOZE, **empty}]})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("2  notes in", result.stdout)
        self.assertTrue(out.exists())

    def test_each_bad_card_is_reported_and_nothing_is_written(self):
        bad = [
            "not an object",
            {"type": "image", "front": "Q", "back": "A"},
            {"type": "basic", "front": "Q only"},
            {"type": "basic", "front": "Q", "back": "A", "text": "stray"},
            {"type": "cloze", "text": "No blank here."},
            {"type": "cloze", "text": "A {{c1::blank}}.", "front": "stray"},
            {**BASIC, "front": "Q2", "kind": "joke"},
            {**BASIC, "front": "Q3", "priority": "1"},
            {**BASIC, "front": "Q4", "tags": "one-tag"},
            {**BASIC, "front": "Q4b", "tags": [123]},
            {**BASIC, "front": "Q4c", "source_url": 42},
            {**BASIC, "front": "Q5", "key": "  "},
            {"type": "cloze", "text": None},
            {**BASIC, "front": "Q6", "section": "no-page"},
            {**BASIC, "front": "Q7", "sorce_url": "https://example.org", "colour": ""},
        ]
        result, out = self.build({"a": [BASIC] + bad})
        self.assertEqual(result.returncode, 1)
        self.assertFalse(out.exists())
        for index in range(1, len(bad) + 1):
            self.assertIn(f"a.json[{index}]: ", result.stderr)
        self.assertNotIn("a.json[0]: ", result.stderr)
        self.assertIn(f"{len(bad)} problem(s)", result.stderr)
        self.assertIn(f"a.json[{len(bad)}]: unknown field(s) ['colour', 'sorce_url']",
                      result.stderr)

    def test_duplicate_question_names_both_cards(self):
        twin = {**BASIC, "front": " what is ONE? ", "back": "Another answer."}
        result, out = self.build({"a": [BASIC], "b": [twin]})
        self.assertEqual(result.returncode, 1)
        self.assertFalse(out.exists())
        self.assertRegex(result.stderr, r"b\.json\[0\]: same question .* as .*a\.json\[0\]")

    def test_broken_card_files_are_reported(self):
        result, out = self.build({"a": [BASIC], "b": {"type": "basic"}})
        self.assertEqual(result.returncode, 1)
        (out.parent / "cards" / "c.json").write_text("[{")
        result = self.run_build(out.parent)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(out.exists())
        self.assertIn("b.json: the file must hold a JSON array", result.stderr)
        self.assertIn("c.json: not valid JSON", result.stderr)

    def test_each_deck_json_problem_is_reported(self):
        bad = {"name": " ", "output": "sub/test.apkg", "basic_model_id": "1",
               "cloze_model_id": 0, "section_url": "", "subdecks": {"a": 1},
               "subdeck": "typo"}
        result, out = self.build({"a": [BASIC]}, deck=bad)
        self.assertEqual(result.returncode, 1)
        self.assertFalse((out.parent / "sub").exists())
        for reason in ["unknown key(s) ['subdeck']", "needs a non-empty 'name'",
                       "basic_model_id is '1'", "cloze_model_id is 0",
                       "section_url must be non-empty text",
                       "output is 'sub/test.apkg'", "subdecks must map"]:
            self.assertIn(f"deck.json: {reason}", result.stderr)
        self.assertIn("7 problem(s) in deck.json", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_missing_ids_and_same_ids(self):
        result, _ = self.build({"a": [BASIC]}, deck={"name": "T", "output": "t.apkg"})
        self.assertIn("deck.json: needs 'basic_model_id'", result.stderr)
        self.assertIn("deck.json: needs 'cloze_model_id'", result.stderr)
        same = {**DECK, "cloze_model_id": DECK["basic_model_id"]}
        result, out = self.build({"a": [BASIC]}, deck=same)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(out.exists())
        self.assertIn("must be different", result.stderr)

    def test_broken_or_missing_deck_json(self):
        result, out = self.build({"a": [BASIC]})
        self.assertEqual(result.returncode, 0, result.stderr)
        (out.parent / "deck.json").write_text("{")
        result = self.run_build(out.parent)
        self.assertEqual(result.returncode, 1)
        self.assertIn("deck.json: not valid JSON", result.stderr)
        (out.parent / "deck.json").write_text("[]")
        self.assertIn("deck.json: must hold a JSON object",
                      self.run_build(out.parent).stderr)
        (out.parent / "deck.json").unlink()
        result = self.run_build(out.parent)
        self.assertEqual(result.returncode, 1)
        self.assertIn("deck.json: not found", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_kind_labels(self):
        story = {**BASIC, "kind": "story"}
        result, _ = self.build({"a": [story]}, deck={**DECK, "kind_labels": {"story": "his story"}})
        self.assertEqual(result.returncode, 0, result.stderr)
        for labels in [{"joke": "ha"}, {"story": 1}, ["story"]]:
            result, out = self.build({"a": [story]}, deck={**DECK, "kind_labels": labels})
            self.assertEqual(result.returncode, 1)
            self.assertFalse(out.exists())
            self.assertIn("deck.json: kind_labels must map kinds", result.stderr)

    def test_links_are_escaped(self):
        deck = {**DECK, "section_url": "https://example.org/a?b=1&c=2"}
        cards = [{**BASIC, "section": 'x"y'},
                 {**BASIC, "front": "Q2", "source_url": "https://example.org/?a=1&b=2"}]
        result, out = self.build({"a": cards}, deck=deck)
        self.assertEqual(result.returncode, 0, result.stderr)
        with zipfile.ZipFile(out) as z, tempfile.TemporaryDirectory() as tmp:
            z.extract("collection.anki2", tmp)
            with closing(sqlite3.connect(Path(tmp) / "collection.anki2")) as db:
                fields = " ".join(f for (f,) in db.execute("select flds from notes"))
        self.assertIn('href="https://example.org/a?b=1&amp;c=2#x&quot;y"', fields)
        self.assertIn('href="https://example.org/?a=1&amp;b=2"', fields)

    def test_key_counts_as_the_question(self):
        renamed = {**BASIC, "front": "What is the number one?", "key": "What is one?"}
        result, _ = self.build({"a": [BASIC], "b": [renamed]})
        self.assertEqual(result.returncode, 1)
        self.assertIn("b.json[0]: same question", result.stderr)


if __name__ == "__main__":
    unittest.main()
