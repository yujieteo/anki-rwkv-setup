"""Tests for the card checks in build.py. They need genanki, not Anki."""

import json
import subprocess
import sys
import tempfile
import unittest
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
            {**BASIC, "front": "Q5", "key": "  "},
            {"type": "cloze", "text": None},
            {**BASIC, "front": "Q6", "section": "no-page"},
        ]
        result, out = self.build({"a": [BASIC] + bad})
        self.assertEqual(result.returncode, 1)
        self.assertFalse(out.exists())
        for index in range(1, len(bad) + 1):
            self.assertIn(f"a.json[{index}]: ", result.stderr)
        self.assertNotIn("a.json[0]: ", result.stderr)
        self.assertIn(f"{len(bad)} problem(s)", result.stderr)

    def test_duplicate_question_names_both_cards(self):
        twin = {**BASIC, "front": " what is ONE? ", "back": "Another answer."}
        result, out = self.build({"a": [BASIC], "b": [twin]})
        self.assertEqual(result.returncode, 1)
        self.assertFalse(out.exists())
        self.assertRegex(result.stderr, r"b\.json\[0\]: same question .* as .*a\.json\[0\]")

    def test_broken_card_files_are_reported(self):
        result, out = self.build({"a": [BASIC], "b": {"type": "basic"}})
        (out.parent / "cards" / "c.json").write_text("[{")
        result = self.run_build(out.parent)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(out.exists())
        self.assertIn("b.json: the file must hold a JSON array", result.stderr)
        self.assertIn("c.json: not valid JSON", result.stderr)

    def test_key_counts_as_the_question(self):
        renamed = {**BASIC, "front": "What is the number one?", "key": "What is one?"}
        result, _ = self.build({"a": [BASIC], "b": [renamed]})
        self.assertEqual(result.returncode, 1)
        self.assertIn("b.json[0]: same question", result.stderr)


if __name__ == "__main__":
    unittest.main()
