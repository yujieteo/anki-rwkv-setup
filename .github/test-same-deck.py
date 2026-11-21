"""Offline regression tests for same-deck.py; no Anki profile is needed."""

import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
COMPARATOR = HERE / "same-deck.py"
ORIGINAL = HERE.parent / "examples/joe-hudson/joe-hudson.apkg"


class SameDeckTest(unittest.TestCase):
    def setUp(self):
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.path = Path(work.name)

    def compare(self, left, right):
        return subprocess.run(
            [sys.executable, str(COMPARATOR), str(left), str(right)],
            capture_output=True, text=True,
        )

    def changed_package(self, name, change):
        target = self.path / f"{name}.apkg"
        with ZipFile(ORIGINAL) as old, ZipFile(target, "w") as new:
            db = old.extract("collection.anki2", self.path)
            with closing(sqlite3.connect(db)) as con, con:
                change(con)
            for item in old.namelist():
                data = Path(db).read_bytes() if item == "collection.anki2" else old.read(item)
                new.writestr(item, data)
        return target

    def test_identical_packages(self):
        run = self.compare(ORIGINAL, ORIGINAL)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("Same deck", run.stdout)

    def test_different_clock_ids_and_times(self):
        def shift(con):
            con.execute("update notes set id = 900000000000000 + id, mod = mod + 1")
            con.execute("update cards set id = 900000000000000 + id, nid = 900000000000000 + nid, mod = mod + 1")

        changed = self.changed_package("different-clock", shift)
        run = self.compare(ORIGINAL, changed)
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_duplicate_note_guid(self):
        def duplicate(con):
            note = con.execute("select * from notes order by id limit 1").fetchone()
            new_id = con.execute("select max(id) + 1 from notes").fetchone()[0]
            con.execute("insert into notes values (?,?,?,?,?,?,?,?,?,?,?)", (new_id, *note[1:]))

        changed = self.changed_package("duplicate-note", duplicate)
        run = self.compare(ORIGINAL, changed)
        self.assertEqual(run.returncode, 1)
        self.assertIn(f"{changed}: duplicate note GUID ", run.stderr)

    def test_duplicate_card_ordinal(self):
        def duplicate(con):
            card = con.execute("select * from cards order by id limit 1").fetchone()
            new_id = con.execute("select max(id) + 1 from cards").fetchone()[0]
            con.execute("insert into cards values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (new_id, *card[1:]))

        changed = self.changed_package("duplicate-card", duplicate)
        run = self.compare(changed, ORIGINAL)
        self.assertEqual(run.returncode, 1)
        self.assertIn(f"{changed}: duplicate card for note GUID ", run.stderr)
        self.assertIn(", ordinal ", run.stderr)


if __name__ == "__main__":
    unittest.main()
