"""The `use` counts the v5 note quotes are what the committed script prints (#3992)."""
import hashlib
import importlib.util
import re
import tempfile
import unittest
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "absence_use_noun_counts.py"
NOTE = ROOT / "notes" / "absence_lexicon_v5_2026-09-30.md"


def _load():
    spec = importlib.util.spec_from_file_location("absence_use_noun_counts", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Count(unittest.TestCase):
    def setUp(self):
        self.mod = _load()

    def test_each_pattern_counts_case_insensitively_across_any_whitespace(self):
        texts = ["The data transfer and Use\n  Agreement governs use of the data.",
                 "Data use is restricted; the record uses the release.",
                 "user, reuse and misuses are not the word."]
        self.assertEqual(self.mod.count(texts), {
            "use/uses": 4, "use agreement(s)": 1, "use of": 1, "data use": 1})

    def test_a_record_whose_bytes_are_not_its_pin_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus = Path(tmp)
            (corpus / "m").mkdir()
            (corpus / "m" / "P_d4d.yaml").write_text("notes: the data use agreement\n", encoding="utf-8")
            raw = (corpus / "m" / "P_d4d.yaml").read_bytes()
            texts, n = self.mod.pinned_texts(corpus, {"m/P_d4d.yaml": hashlib.sha256(raw).hexdigest()})
            self.assertEqual((texts, n), (["the data use agreement"], 1))
            with self.assertRaisesRegex(self.mod.baseline.Stale, "changed m/P_d4d.yaml"):
                self.mod.pinned_texts(corpus, {"m/P_d4d.yaml": "0" * 64})
            with self.assertRaisesRegex(self.mod.baseline.Stale, "gone m/Q_d4d.yaml"):
                self.mod.pinned_texts(corpus, {"m/Q_d4d.yaml": "0" * 64})


@pytest.mark.corpus
class NoteReproduces(unittest.TestCase):
    def test_the_note_quotes_the_counts_the_script_prints(self):
        mod = _load()
        texts, n = mod.pinned_texts()
        totals = mod.count(texts)
        note = " ".join(NOTE.read_text(encoding="utf-8").split())
        quoted = re.search(r"bare `use`/`uses` occurs ([\d,]+) times, overwhelmingly as a noun: "
                           r"\"use agreement\(s\)\" ([\d,]+) times, \"use of\" ([\d,]+), \"data use\" ([\d,]+)\.",
                           note)
        self.assertIsNotNone(quoted, "the note no longer carries the use/uses sentence")
        self.assertEqual([int(g.replace(",", "")) for g in quoted.groups()],
                         [totals[label] for label, _ in mod.PATTERNS])
        self.assertEqual(n, 303)


if __name__ == "__main__":
    unittest.main()
